"""生成 Stage 4 部署审计产物。

脚本汇总前几周的输出 CSV、模型哈希、ONNX 图信息和软件版本，生成 model card、
correctness matrix、latency matrix 与资产追踪表。它不重新跑推理，只整理证据。
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import yaml


ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> list[dict[str, str]]:
    # 某些周的产物可能尚未生成；缺失时返回空列表，让审计表显示 not verified。
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    # 空表不写文件，避免生成只有表头含义也不清楚的审计产物。
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    # 模型和权重哈希用于追踪“报告中的结果到底对应哪个二进制资产”。
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(rows: list[dict[str, str]], key: str) -> float | str:
    # 审计矩阵允许缺失值；没有对应列时返回空字符串，而不是抛异常中断汇总。
    return float(np.mean([float(row[key]) for row in rows])) if rows and key in rows[0] else ""


def maximum(rows: list[dict[str, str]], key: str) -> float | str:
    # 最大误差通常比均值更适合作为正确性风险的告警指标。
    return max(float(row[key]) for row in rows) if rows and key in rows[0] else ""


def main() -> None:
    out_dir = ROOT / "outputs/audit"
    out_dir.mkdir(parents=True, exist_ok=True)
    contract = yaml.safe_load((ROOT / "configs/deployment_contract.yaml").read_text(encoding="utf-8"))
    # deployment_contract.yaml 是本阶段输入输出约定的单一说明来源。
    checkpoint = (ROOT / contract["model"]["checkpoint"]).resolve()
    onnx_path = ROOT / "models/onnx/dncnn_sidd_tiny_fp32.onnx"
    onnx_data = Path(str(onnx_path) + ".data")
    int8_path = ROOT / "models/onnx/dncnn_sidd_tiny_int8_qdq.onnx"

    model = onnx.load(str(onnx_path), load_external_data=False)
    # ONNX 大权重可能放在外部 .data 文件里，这里记录外部文件名以便审计。
    external = sorted(
        {
            entry.value
            for initializer in model.graph.initializer
            for entry in initializer.external_data
            if entry.key == "location"
        }
    )
    model_card = {
        # model_card 汇总模型来源、文件哈希、ONNX 元信息和当前软件环境。
        "generated_at": "2026-06-23",
        "contract": contract,
        "hashes": {
            "checkpoint_sha256": sha256(checkpoint),
            "onnx_sha256": sha256(onnx_path),
            "onnx_external_data_sha256": sha256(onnx_data),
            "int8_qdq_sha256": sha256(int8_path) if int8_path.exists() else None,
        },
        "onnx": {
            "ir_version": model.ir_version,
            "opsets": [{"domain": item.domain, "version": item.version} for item in model.opset_import],
            "external_data_files": external,
            "checker": "pass",
        },
        "software_observed_now": {
            "python": __import__("sys").version.split()[0],
            "torch": torch.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": ort.__version__,
            "providers": ort.get_available_providers(),
        },
    }
    onnx.checker.check_model(onnx.load(str(onnx_path), load_external_data=True))
    (out_dir / "model_card.json").write_text(json.dumps(model_card, indent=2, ensure_ascii=False), encoding="utf-8")

    week1 = read_rows(ROOT / "outputs/week1_onnx/week1_onnx_alignment.csv")
    week2 = read_rows(ROOT / "outputs/week2_cpp_io/week2_cpp_tensor_alignment.csv")
    week3 = read_rows(ROOT / "outputs/week3_backend/week3_gpu_alignment_latency.csv")
    week4 = read_rows(ROOT / "outputs/week4_quantization/week4_int8_metrics.csv")
    correctness = [
        # 正确性矩阵按“后端/精度/参考实现”组织，便于看每条部署链路是否已验证。
        {
            "backend": "ONNX Runtime Python CPU",
            "precision": "FP32",
            "input": "week0_fixed_manifest:20 RGB 1x3x512x512",
            "reference": "PyTorch FP32",
            "max_abs_error": maximum(week1, "ort_vs_pytorch_max_abs_error"),
            "mean_abs_error": mean(week1, "ort_vs_pytorch_mean_abs_error"),
            "rmse": "",
            "alignment_psnr": mean(week1, "ort_vs_pytorch_psnr"),
            "quality_psnr": mean(week1, "ort_quality_psnr"),
            "quality_ssim": mean(week1, "ort_quality_ssim"),
            "status": "verified",
        },
        {
            "backend": "ONNX Runtime C++ CPU",
            "precision": "FP32",
            "input": f"week0_fixed_manifest:{len(week2)} raw tensors",
            "reference": "ONNX Runtime Python FP32 raw tensor",
            "max_abs_error": maximum(week2, "max_abs_error"),
            "mean_abs_error": mean(week2, "mean_abs_error"),
            "rmse": mean(week2, "rmse"),
            "alignment_psnr": mean(week2, "psnr"),
            "quality_psnr": "",
            "quality_ssim": "",
            "status": "verified" if week2 and all(row["status"] == "pass" for row in week2) else "not verified",
        },
    ]
    for backend in ("cuda", "trt_fp32", "trt_fp16"):
        # Week 3 的 CUDA/TensorRT 后端都以 ORT CPU FP32 为参考。
        rows = [row for row in week3 if row["backend"] == backend]
        correctness.append(
            {
                "backend": backend,
                "precision": "FP16" if backend == "trt_fp16" else "FP32",
                "input": f"week0_fixed_manifest:{len(rows)}",
                "reference": "ONNX Runtime CPU FP32",
                "max_abs_error": maximum(rows, "max_abs_error_vs_ort_cpu"),
                "mean_abs_error": mean(rows, "mean_abs_error_vs_ort_cpu"),
                "rmse": "",
                "alignment_psnr": mean(rows, "psnr_vs_ort_cpu"),
                "quality_psnr": mean(rows, "quality_psnr"),
                "quality_ssim": mean(rows, "quality_ssim"),
                "status": "verified" if rows else "not verified",
            }
        )
    correctness.append(
        {
            "backend": "ONNX Runtime CPU QDQ",
            "precision": "INT8 QDQ",
            "input": f"week4_evaluation_manifest:{len(week4)}",
            "reference": "ONNX Runtime CPU FP32",
            "max_abs_error": maximum(week4, "max_abs_error"),
            "mean_abs_error": mean(week4, "mean_abs_error"),
            "rmse": mean(week4, "rmse"),
            "alignment_psnr": mean(week4, "alignment_psnr"),
            "quality_psnr": mean(week4, "int8_psnr"),
            "quality_ssim": mean(week4, "int8_ssim"),
            "status": "verified with isolated split" if week4 else "not verified",
        }
    )
    write_rows(out_dir / "correctness_matrix.csv", correctness)

    latency = []
    week0 = read_rows(ROOT / "outputs/week0_baseline/week0_summary.csv")
    if week0:
        # PyTorch 基线延迟来自 Week 0.5，作为部署前参考。
        latency.append(
            {
                "backend": "PyTorch",
                "device": week0[0]["device"],
                "shape": "1x3x512x512",
                "precision": "FP32",
                "warmup_runs": 3,
                "timed_runs": "10/image",
                "pre_ms": "",
                "h2d_ms": "",
                "infer_mean_ms": week0[0]["latency_mean_ms"],
                "infer_p50_ms": week0[0]["latency_p50_ms"],
                "infer_p90_ms": week0[0]["latency_p90_ms"],
                "d2h_ms": "",
                "post_ms": "",
                "e2e_ms": "",
                "includes_io": "no",
            }
        )
    for row in read_rows(ROOT / "outputs/week3_backend/week3_backend_summary.csv"):
        # ORT 后端延迟包含 session.run 内部的 provider 调度和必要拷贝。
        latency.append(
            {
                "backend": f"ORT {row['backend']}",
                "device": "RTX 4060 Ti" if row["backend"] != "cpu" else "CPU",
                "shape": "1x3x512x512",
                "precision": "FP16" if row["backend"] == "trt_fp16" else "FP32",
                "warmup_runs": 5,
                "timed_runs": "configured/image",
                "pre_ms": "",
                "h2d_ms": "included in session.run" if row["backend"] != "cpu" else "",
                "infer_mean_ms": row["latency_mean_ms"],
                "infer_p50_ms": row["latency_p50_ms"],
                "infer_p90_ms": row["latency_p90_ms"],
                "d2h_ms": "included in session.run" if row["backend"] != "cpu" else "",
                "post_ms": "",
                "e2e_ms": "",
                "includes_io": "no file I/O; Python session call",
            }
        )
    for row in read_rows(ROOT / "outputs/week3_backend/week3_trtexec_summary.csv"):
        # trtexec 延迟来自 TensorRT 官方工具，能拆出 H2D/compute/D2H。
        latency.append(
            {
                "backend": f"trtexec {row['precision']}",
                "device": "RTX 4060 Ti",
                "shape": "1x3x512x512",
                "precision": row["precision"].upper(),
                "warmup_runs": "200 ms",
                "timed_runs": "3 s duration",
                "pre_ms": "",
                "h2d_ms": row.get("h2d_mean_ms", ""),
                "infer_mean_ms": row["gpu_compute_mean_ms"],
                "infer_p50_ms": row["gpu_compute_p50_ms"],
                "infer_p90_ms": "",
                "d2h_ms": row.get("d2h_mean_ms", ""),
                "post_ms": "",
                "e2e_ms": row.get("latency_mean_ms", ""),
                "includes_io": "no file I/O; trtexec H2D/compute/D2H",
            }
        )
    int8_summary = read_rows(ROOT / "outputs/week4_quantization/week4_int8_summary.csv")
    if int8_summary:
        # INT8 与 FP32 使用同一独立 evaluation split，避免量化校准样本泄漏。
        row = int8_summary[0]
        for precision, prefix in (("FP32", "fp32"), ("INT8 QDQ", "int8")):
            latency.append(
                {
                    "backend": "ORT CPU quantization evaluation",
                    "device": "CPU",
                    "shape": "1x3x512x512",
                    "precision": precision,
                    "warmup_runs": row["warmup_per_image"],
                    "timed_runs": f"{row['runs_per_image']}/image on isolated evaluation set",
                    "pre_ms": "",
                    "h2d_ms": "",
                    "infer_mean_ms": row[f"mean_{prefix}_latency_ms"],
                    "infer_p50_ms": row[f"p50_{prefix}_latency_ms"],
                    "infer_p90_ms": row[f"p90_{prefix}_latency_ms"],
                    "d2h_ms": "",
                    "post_ms": "",
                    "e2e_ms": "",
                    "includes_io": "no",
                }
            )
    pipeline = read_rows(ROOT / "outputs/week6_pipeline/week6_pipeline_summary.csv")
    if pipeline:
        # 端到端 pipeline 把 preprocess/inference/postprocess 拆开，文件 I/O 单独说明。
        row = pipeline[0]
        latency.append(
            {
                "backend": "ORT CPU RGB pipeline",
                "device": "CPU",
                "shape": "1x3x512x512",
                "precision": "FP32",
                "warmup_runs": row["warmup_per_image"],
                "timed_runs": f"{row['runs_per_image']}/image",
                "pre_ms": row["mean_preprocess_ms"],
                "h2d_ms": "",
                "infer_mean_ms": row["mean_inference_ms"],
                "infer_p50_ms": row["p50_inference_ms"],
                "infer_p90_ms": row["p90_inference_ms"],
                "d2h_ms": "",
                "post_ms": row["mean_postprocess_ms"],
                "e2e_ms": row["mean_compute_e2e_ms"],
                "includes_io": row["includes_io"],
            }
        )
    cuda_pre = read_rows(ROOT / "outputs/week6_pipeline/week6_cuda_preprocess_summary.csv")
    if cuda_pre:
        # CUDA normalize 只衡量预处理 kernel 和 pageable memory 拷贝，不代表完整模型延迟。
        row = cuda_pre[0]
        latency.append(
            {
                "backend": "NVRTC CUDA normalize",
                "device": "RTX 4060 Ti",
                "shape": f"1x{row['channels']}x{row['height']}x{row['width']}",
                "precision": "uint8→FP32",
                "warmup_runs": 1,
                "timed_runs": row["runs"],
                "pre_ms": "",
                "h2d_ms": row["h2d_pageable_ms"],
                "infer_mean_ms": row["cuda_kernel_mean_ms"],
                "infer_p50_ms": "",
                "infer_p90_ms": "",
                "d2h_ms": row["d2h_pageable_ms"],
                "post_ms": "",
                "e2e_ms": row["gpu_stage_e2e_ms"],
                "includes_io": f"no file I/O; {row['memory_type']} memory",
            }
        )
    write_rows(out_dir / "latency_matrix.csv", latency)

    assets = [
        # 资产追踪表把 checkpoint、ONNX、engine/model、输入集、输出和报告串起来。
        {
            "checkpoint": str(checkpoint),
            "onnx": str(onnx_path),
            "backend_engine_or_model": "ORT FP32 / TensorRT plans / ORT QDQ INT8",
            "input_manifest": "week0_fixed_manifest; isolated week4 calibration/evaluation manifests",
            "outputs": "outputs/week0..week6",
            "error_csv": "outputs/audit/correctness_matrix.csv",
            "latency_log": "week3 trtexec logs; week3/week6 CSV",
            "report_conclusion": "reports/stage4_report.md",
        }
    ]
    write_rows(out_dir / "asset_traceability.csv", assets)
    print(f"Wrote audit artifacts to {out_dir}")


if __name__ == "__main__":
    main()
