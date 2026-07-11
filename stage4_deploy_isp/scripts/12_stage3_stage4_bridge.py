#!/usr/bin/env python3
"""串联 Stage 3 C++ ISP 与 Stage 4 C++ ONNX Runtime 推理程序。

每个样本先经过 Stage 3 图像处理节点，再以 8 位 PPM 作为两个阶段之间的
实际交付格式。脚本同时运行 Python ORT 参考实现，用于确认 Stage 4 C++
输出与后端基准一致，并记录两个阶段的耗时和图像质量。
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deploy.common import project_root, resolve_path
from deploy.stage3_bridge import hwc_to_nchw, psnr, read_cpf32, write_cpf32


# C++ runner 将平均推理耗时打印到标准输出，正则只提取数值部分。
INFERENCE_MEAN = re.compile(r"inference_mean_ms=([0-9.eE+-]+)")


def run_checked(command: list[str], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """运行 C++ 节点，并在失败时保留退出码和捕获的诊断输出。"""
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    except subprocess.CalledProcessError as error:
        code = error.returncode
        code_text = f"{code} (0x{code:08X})" if code >= 0 else str(code)
        raise RuntimeError(
            f"Command failed with exit code {code_text}: {command[0]}\n"
            f"stdout:\n{error.stdout or '<empty>'}\n"
            f"stderr:\n{error.stderr or '<empty>'}"
        ) from error


def parse_args() -> argparse.Namespace:
    """定义桥接验证所需的输入、可执行文件、输出位置和重复次数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--model", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--stage3-runner", default="../stage3_cpp_isp/out/build/verify/run_pipeline.exe")
    parser.add_argument("--stage4-runner", default="out/build/ort-verify/stage4_ort_runner.exe")
    parser.add_argument("--ort-lib-dir", default="", help="Directory containing onnxruntime.dll on Windows.")
    parser.add_argument("--output-dir", default="out/stage3_stage4_bridge")
    parser.add_argument("--summary", default="reports/stage3_stage4_bridge_summary.csv")
    parser.add_argument("--count", type=int, default=0, help="0 processes the full manifest.")
    parser.add_argument("--runs", type=int, default=3)
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    """读取固定测试清单，保留 CSV 中的字符串字段。"""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def resolve_from_stage4(value: str) -> Path:
    """将相对路径统一解释为相对于 stage4_deploy_isp 根目录。"""
    path = Path(value)
    return path if path.is_absolute() else (project_root() / path).resolve()


def subprocess_environment(ort_lib_dir: str) -> dict[str, str]:
    """构造子进程环境；Windows 下可临时把 ORT 动态库目录加入 PATH。"""
    environment = os.environ.copy()
    if ort_lib_dir:
        library = resolve_from_stage4(ort_lib_dir)
        environment["PATH"] = str(library) + os.pathsep + environment.get("PATH", "")
    return environment


def main() -> None:
    """逐样本运行端到端桥接验证并生成 CSV 汇总。"""
    args = parse_args()
    if args.runs <= 0:
        raise SystemExit("--runs must be positive")
    root = project_root()
    rows = read_manifest(root / args.manifest)
    if args.count > 0:
        rows = rows[: args.count]
    if not rows:
        raise SystemExit("Manifest selected no samples")

    stage3_runner = resolve_from_stage4(args.stage3_runner)
    stage4_runner = resolve_from_stage4(args.stage4_runner)
    model = resolve_from_stage4(args.model)
    for executable in (stage3_runner, stage4_runner):
        if not executable.exists():
            raise SystemExit(f"Missing runner: {executable}")

    out_dir = resolve_from_stage4(args.output_dir)
    summary_path = resolve_from_stage4(args.summary)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    environment = subprocess_environment(args.ort_lib_dir)
    # Python CPU ORT 是对照组，用同一个 ONNX 模型隔离 C++ runner 的实现误差。
    python_session = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])

    results: list[dict[str, object]] = []
    for row in rows:
        sample_id = row["id"]
        sample_dir = out_dir / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)
        noisy = np.asarray(Image.open(resolve_path(row["noisy_path"])).convert("RGB"), dtype=np.float32) / 255.0
        clean = np.asarray(Image.open(resolve_path(row["clean_path"])).convert("RGB"), dtype=np.float32) / 255.0

        input_cpf32 = sample_dir / "input.cpf32"
        stage3_cpf32 = sample_dir / "stage3_output.cpf32"
        stage3_ppm = sample_dir / "stage3_output.ppm"
        stage4_ppm = sample_dir / "stage4_output.ppm"
        stage4_f32 = sample_dir / "stage4_output.f32"
        write_cpf32(input_cpf32, noisy)

        # Stage 3 的 wall time 包含进程启动和 CPF32 文件 I/O，不能与纯推理耗时混用。
        stage3_start = time.perf_counter()
        run_checked(
            [
                str(stage3_runner),
                "single",
                str(input_cpf32),
                str(stage3_cpf32),
                "none",
                "global",
                "reinhard",
                "1.0",
                "1.0",
            ],
            environment,
        )
        stage3_wall_ms = (time.perf_counter() - stage3_start) * 1000.0
        stage3_float = read_cpf32(stage3_cpf32)

        # Stage 4 C++ runner 接收 8 位 PPM。Python 参考也使用同一份量化后图像，
        # 这样 C++/Python 误差只反映 runner 与后端对齐，不混入 PPM 量化误差。
        stage3_u8 = (np.clip(stage3_float, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        Image.fromarray(stage3_u8, mode="RGB").save(stage3_ppm)
        quantized_stage3 = stage3_u8.astype(np.float32) / 255.0
        input_nchw = hwc_to_nchw(quantized_stage3)
        python_reference = python_session.run(["output"], {"input": input_nchw})[0].astype(np.float32)

        # 预热 1 次后重复推理 args.runs 次；runner 另存可视化 PPM 和原始 float32。
        completed = run_checked(
            [
                str(stage4_runner),
                str(model),
                str(stage3_ppm),
                str(stage4_ppm),
                str(stage4_f32),
                "1",
                str(args.runs),
            ],
            environment,
        )
        timing_match = INFERENCE_MEAN.search(completed.stdout)
        if timing_match is None:
            raise RuntimeError(f"Could not parse Stage 4 timing: {completed.stdout}")
        # 原始输出采用小端 float32，可避免 8 位图片保存造成的二次量化误差。
        cpp_output = np.fromfile(stage4_f32, dtype="<f4").reshape(python_reference.shape)
        error = np.abs(cpp_output - python_reference)
        restored_hwc = np.transpose(cpp_output[0], (1, 2, 0))
        results.append(
            {
                "id": sample_id,
                "stage3_node": "none+global_reinhard+gamma1",
                "stage3_wall_ms": stage3_wall_ms,
                "stage3_max_abs_vs_input": float(np.max(np.abs(stage3_float - noisy))),
                "ppm_quantization_max_abs": float(np.max(np.abs(quantized_stage3 - stage3_float))),
                "stage4_cpp_infer_mean_ms": float(timing_match.group(1)),
                "stage4_cpp_vs_python_max_abs": float(error.max()),
                "stage4_cpp_vs_python_mean_abs": float(error.mean()),
                "input_psnr": psnr(noisy, clean),
                "bridge_output_psnr": psnr(np.clip(restored_hwc, 0.0, 1.0), clean),
            }
        )

    # 字段顺序沿用首条结果，便于后续审计脚本稳定读取。
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"stage3_stage4_bridge=pass samples={len(results)} summary={summary_path}")


if __name__ == "__main__":
    main()
