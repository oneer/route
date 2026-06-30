"""Week 3：CUDA / TensorRT 后端 benchmark 与数值对齐。

脚本同时覆盖两条证据链：一条用 trtexec 生成 TensorRT engine 并读取官方计时，
另一条用 ONNX Runtime 的 CPU、CUDA、TensorRT provider 跑同一批输入，比较
GPU/FP16 输出相对 ORT CPU FP32 的误差和质量指标。
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def project_root() -> Path:
    # 本脚本不依赖 deploy.common，直接把 stage4_deploy_isp 当作工程根目录。
    return SCRIPT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 3 TensorRT/CUDA benchmark and output alignment.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--output-dir", default="outputs/week3_backend")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--trtexec", default=r"D:\Env\TensorRT\TensorRT-10.8.0.43\bin\trtexec.exe")
    parser.add_argument("--cuda-bin", default=r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin")
    parser.add_argument("--tensorrt-bin", default=r"D:\Env\TensorRT\TensorRT-10.8.0.43\bin")
    parser.add_argument("--tensorrt-lib", default=r"D:\Env\TensorRT\TensorRT-10.8.0.43\lib")
    parser.add_argument("--cudnn-bin", default=r"C:\Program Files\NVIDIA\CUDNN\v9.23\bin\12.9\x64")
    return parser.parse_args()


def preload_gpu_dlls(extra_dirs: list[str]) -> None:
    # Windows 下 ORT/TensorRT/CUDA DLL 搜索容易失败，运行前显式加入常见 bin 目录。
    site_packages = Path(sys.executable).resolve().parents[1] / "Lib" / "site-packages"
    bin_dirs = [str(path) for path in glob.glob(str(site_packages / "nvidia" / "*" / "bin"))]
    bin_dirs.append(str(site_packages / "onnxruntime" / "capi"))
    bin_dirs.extend(extra_dirs)
    existing = os.environ.get("PATH", "")
    os.environ["PATH"] = ";".join(bin_dirs) + ";" + existing
    for bin_dir in bin_dirs:
        if os.path.isdir(bin_dir):
            os.add_dll_directory(bin_dir)


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_input(path: str) -> np.ndarray:
    # 所有后端共用 NCHW float32 输入，避免把布局差异误判为后端数值误差。
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)


def abs_error(pred: np.ndarray, target: np.ndarray) -> tuple[float, float, float]:
    # 返回最大误差、平均误差和对齐 PSNR，三者共同描述后端输出是否接近 CPU FP32。
    err = np.abs(pred - target)
    mse = float(np.mean((pred - target) ** 2))
    psnr = float(10.0 * np.log10(1.0 / max(mse, 1e-8)))
    return float(err.max()), float(err.mean()), psnr


def quality_psnr(pred: np.ndarray, target: np.ndarray) -> float:
    mse = float(np.mean((pred - target) ** 2))
    return float(10.0 * np.log10(1.0 / max(mse, 1e-8)))


def quality_ssim(pred: np.ndarray, target: np.ndarray) -> float:
    # 与前几周保持同样的全局 SSIM 近似，只用于相对比较。
    x, y = pred.astype(np.float64), target.astype(np.float64)
    c1, c2 = 0.01**2, 0.03**2
    mux, muy = x.mean(), y.mean()
    vx, vy = x.var(), y.var()
    cov = ((x - mux) * (y - muy)).mean()
    return float(((2 * mux * muy + c1) * (2 * cov + c2)) / ((mux**2 + muy**2 + c1) * (vx + vy + c2)))


def to_u8(array: np.ndarray) -> np.ndarray:
    hwc = np.transpose(np.clip(array[0], 0.0, 1.0), (1, 2, 0))
    return (hwc * 255.0 + 0.5).astype(np.uint8)


def save_failure_diagnostic(
    sample_id: str,
    cpu: np.ndarray,
    fp16: np.ndarray,
    clean: np.ndarray,
    out_dir: Path,
) -> None:
    # 诊断图只针对 FP16 最差样本，用 x1000 误差热图放大半精度带来的细微差异。
    error = np.mean(np.abs(fp16 - cpu), axis=1)[0]
    scaled = np.clip(error * 1000.0, 0.0, 1.0)
    heat = np.stack([scaled, np.sqrt(scaled), np.zeros_like(scaled)], axis=2)
    error_dir = out_dir / "fp16_error_maps"
    failure_dir = out_dir / "fp16_failure_cases"
    error_dir.mkdir(parents=True, exist_ok=True)
    failure_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray((heat * 255.0 + 0.5).astype(np.uint8)).save(error_dir / f"{sample_id}_fp16_vs_fp32_x1000.png")
    panels = [to_u8(clean), to_u8(cpu), to_u8(fp16), (heat * 255.0 + 0.5).astype(np.uint8)]
    sheet = Image.fromarray(np.concatenate(panels, axis=1))
    draw = ImageDraw.Draw(sheet)
    width = panels[0].shape[1]
    for index, label in enumerate(("clean", "ORT CPU FP32", "TRT FP16", "error x1000")):
        draw.rectangle((index * width, 0, index * width + 110, 18), fill=(0, 0, 0))
        draw.text((index * width + 3, 3), label, fill=(255, 255, 255))
    sheet.save(failure_dir / f"{sample_id}_fp16_comparison.png")


def make_session(onnx_path: Path, backend: str, cache_dir: Path) -> ort.InferenceSession:
    # provider 顺序表示优先级；后面的 CPU provider 是不支持算子的兜底。
    if backend == "cpu":
        providers: list[object] = ["CPUExecutionProvider"]
    elif backend == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif backend == "trt_fp32":
        # 打开 TensorRT engine cache，避免重复构建 engine 影响后续运行。
        providers = [
            (
                "TensorrtExecutionProvider",
                {
                    "trt_engine_cache_path": str(cache_dir / "ort_trt_fp32"),
                    "trt_engine_cache_enable": "True",
                    "trt_fp16_enable": "False",
                },
            ),
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
    elif backend == "trt_fp16":
        # trt_fp16_enable=True 让 TensorRT 尽量用半精度执行，速度更快但需检查质量退化。
        providers = [
            (
                "TensorrtExecutionProvider",
                {
                    "trt_engine_cache_enable": "True",
                    "trt_engine_cache_path": str(cache_dir / "ort_trt_fp16"),
                    "trt_fp16_enable": "True",
                },
            ),
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
    else:
        raise ValueError(f"Unknown backend: {backend}")
    return ort.InferenceSession(str(onnx_path), providers=providers)


def benchmark_session(session: ort.InferenceSession, inp: np.ndarray, runs: int) -> tuple[np.ndarray, list[float]]:
    # 预热 5 次让 provider 完成 kernel/engine 初始化，计时阶段只统计稳定运行。
    for _ in range(5):
        output = session.run(["output"], {"input": inp})[0]
    timings = []
    for _ in range(runs):
        start = time.perf_counter()
        output = session.run(["output"], {"input": inp})[0]
        timings.append((time.perf_counter() - start) * 1000.0)
    return output, timings


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    # 统一 CSV 写法，确保父目录存在并使用首行字段顺序。
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_trtexec(args: argparse.Namespace, root: Path, out_dir: Path, precision: str) -> dict[str, object]:
    # trtexec 是 TensorRT 官方 benchmark 工具，用于获得独立于 ORT 的 engine 计时。
    trtexec = Path(args.trtexec)
    engine = out_dir / f"dncnn_sidd_tiny_{precision}_trt108.plan"
    log_path = out_dir / f"week3_trtexec_{precision}.log"
    times_path = out_dir / f"week3_trtexec_{precision}_times.json"
    if engine.exists():
        # 删除旧 engine，确保本次日志和 times 文件对应当前 ONNX/precision。
        engine.unlink()
    cmd = [
        str(trtexec),
        f"--onnx={root / args.onnx}",
        f"--saveEngine={engine}",
        "--duration=3",
        "--warmUp=200",
        f"--exportTimes={times_path}",
    ]
    if precision == "fp16":
        cmd.append("--fp16")
    env = os.environ.copy()
    env["PATH"] = f"{args.tensorrt_lib};{args.tensorrt_bin};{args.cudnn_bin};{args.cuda_bin};{env.get('PATH', '')}"
    result = subprocess.run(cmd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log_path.write_text(result.stdout, encoding="utf-8")

    # 优先解析 exportTimes JSON；如果 JSON 不存在，则退回解析 stdout 中的均值/中位数。
    gpu_mean_ms = ""
    gpu_median_ms = ""
    h2d_mean_ms = ""
    d2h_mean_ms = ""
    latency_mean_ms = ""
    match = re.search(r"GPU Compute Time:.*?mean\s*=\s*([0-9.]+)\s*ms.*?median\s*=\s*([0-9.]+)\s*ms", result.stdout, re.S)
    if match:
        gpu_mean_ms = match.group(1)
        gpu_median_ms = match.group(2)
    if times_path.exists():
        try:
            data = json.loads(times_path.read_text(encoding="utf-8"))
            values = [float(item["computeMs"]) for item in data if "computeMs" in item]
            if values:
                gpu_mean_ms = f"{float(np.mean(values)):.6f}"
                gpu_median_ms = f"{float(np.percentile(values, 50)):.6f}"
                h2d_mean_ms = f"{float(np.mean([item['h2dMs'] for item in data])):.6f}"
                d2h_mean_ms = f"{float(np.mean([item['d2hMs'] for item in data])):.6f}"
                latency_mean_ms = f"{float(np.mean([item['latencyMs'] for item in data])):.6f}"
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    return {
        "precision": precision,
        "returncode": result.returncode,
        "engine_path": str(engine),
        "engine_exists": engine.exists(),
        "log_path": str(log_path),
        "times_path": str(times_path) if times_path.exists() else "",
        "gpu_compute_mean_ms": gpu_mean_ms,
        "gpu_compute_p50_ms": gpu_median_ms,
        "h2d_mean_ms": h2d_mean_ms,
        "d2h_mean_ms": d2h_mean_ms,
        "latency_mean_ms": latency_mean_ms,
    }


def main() -> None:
    args = parse_args()
    preload_gpu_dlls([args.cuda_bin, args.cudnn_bin, args.tensorrt_bin, args.tensorrt_lib])
    root = project_root()
    out_dir = root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "ort_engine_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    rows = read_manifest(root / args.manifest)
    onnx_path = root / args.onnx
    tools = {
        "trtexec": str(Path(args.trtexec)) if Path(args.trtexec).exists() else (shutil.which("trtexec") or "missing"),
        "nvcc": shutil.which("nvcc") or "missing",
        "nvidia_smi": shutil.which("nvidia-smi") or "missing",
    }
    trtexec_rows = [
        # 分别生成/测试 FP32 与 FP16 engine，便于比较 TensorRT 精度模式。
        run_trtexec(args, root, out_dir, "fp32"),
        run_trtexec(args, root, out_dir, "fp16"),
    ]
    write_csv(out_dir / "week3_trtexec_summary.csv", trtexec_rows)

    sessions = {
        # 四个 session 使用同一 ONNX，同一输入；只改变执行 provider。
        "cpu": make_session(onnx_path, "cpu", cache_dir),
        "cuda": make_session(onnx_path, "cuda", cache_dir),
        "trt_fp32": make_session(onnx_path, "trt_fp32", cache_dir),
        "trt_fp16": make_session(onnx_path, "trt_fp16", cache_dir),
    }
    alignment_rows = []
    fp16_diagnostics: list[tuple[float, str, np.ndarray, np.ndarray, np.ndarray]] = []
    all_times: dict[str, list[float]] = {name: [] for name in sessions}
    for row in rows:
        # CPU FP32 输出作为本脚本内所有 GPU 后端的数值参考。
        inp = load_input(row["noisy_path"])
        clean = load_input(row["clean_path"])
        cpu_out, cpu_times = benchmark_session(sessions["cpu"], inp, args.runs)
        all_times["cpu"].extend(cpu_times)
        for backend in ("cuda", "trt_fp32", "trt_fp16"):
            output, times = benchmark_session(sessions[backend], inp, args.runs)
            all_times[backend].extend(times)
            max_err, mean_err, align_psnr = abs_error(output, cpu_out)
            cpu_quality_psnr = quality_psnr(np.clip(cpu_out, 0.0, 1.0), clean)
            backend_quality_psnr = quality_psnr(np.clip(output, 0.0, 1.0), clean)
            cpu_quality_ssim = quality_ssim(np.clip(cpu_out, 0.0, 1.0), clean)
            backend_quality_ssim = quality_ssim(np.clip(output, 0.0, 1.0), clean)
            alignment_rows.append(
                {
                    "id": row["id"],
                    "backend": backend,
                    "active_providers": ";".join(sessions[backend].get_providers()),
                    "max_abs_error_vs_ort_cpu": max_err,
                    "mean_abs_error_vs_ort_cpu": mean_err,
                    "psnr_vs_ort_cpu": align_psnr,
                    "quality_psnr": backend_quality_psnr,
                    "quality_psnr_drop_vs_ort_cpu": cpu_quality_psnr - backend_quality_psnr,
                    "quality_ssim": backend_quality_ssim,
                    "quality_ssim_drop_vs_ort_cpu": cpu_quality_ssim - backend_quality_ssim,
                    "latency_mean_ms": float(np.mean(times)),
                    "latency_p50_ms": float(np.percentile(times, 50)),
                    "latency_p90_ms": float(np.percentile(times, 90)),
                }
            )
            if backend == "trt_fp16":
                # 后面按质量下降排序，保存 FP16 相对 CPU FP32 最明显的样本。
                fp16_diagnostics.append(
                    (cpu_quality_psnr - backend_quality_psnr, row["id"], cpu_out.copy(), output.copy(), clean.copy())
                )

    write_csv(out_dir / "week3_gpu_alignment_latency.csv", alignment_rows)
    for _, sample_id, cpu_out, fp16_out, clean in sorted(fp16_diagnostics, reverse=True)[:3]:
        save_failure_diagnostic(sample_id, cpu_out, fp16_out, clean, out_dir)
    summary_rows = []
    for backend, values in all_times.items():
        # latency summary 聚合所有样本的 run 级计时，用于最终审计矩阵。
        summary_rows.append(
            {
                "backend": backend,
                "available_providers": ";".join(ort.get_available_providers()),
                "active_providers": ";".join(sessions[backend].get_providers()),
                "trtexec": tools["trtexec"],
                "nvcc": tools["nvcc"],
                "nvidia_smi": tools["nvidia_smi"],
                "latency_mean_ms": float(np.mean(values)),
                "latency_p50_ms": float(np.percentile(values, 50)),
                "latency_p90_ms": float(np.percentile(values, 90)),
            }
        )
    write_csv(out_dir / "week3_backend_summary.csv", summary_rows)
    print(f"Wrote {out_dir / 'week3_backend_summary.csv'}")
    print(f"Wrote {out_dir / 'week3_gpu_alignment_latency.csv'}")
    print(f"Wrote {out_dir / 'week3_trtexec_summary.csv'}")


if __name__ == "__main__":
    main()
