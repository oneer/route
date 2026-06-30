"""Week 4：静态 INT8 QDQ 量化与独立评估。

脚本把固定样本拆成 calibration/evaluation 两部分：前者只用于收集量化范围，
后者才用于质量和延迟评估。这样可以避免“用校准集评估自己”的数据泄漏。
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader, CalibrationMethod, QuantFormat, QuantType, quantize_static
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]


def read_manifest(path: Path) -> list[dict[str, str]]:
    # 读取固定输入集合，之后会显式拆分为校准集和评估集。
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    # 把拆分结果落盘，报告和审计可以追踪每张图属于哪个 split。
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def load_input(path: str) -> np.ndarray:
    # ONNX 模型的输入合同是 NCHW float32，像素范围 [0,1]。
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return np.transpose(arr, (2, 0, 1))[None].astype(np.float32)


def psnr(pred: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    mse = float(np.mean((pred - target) ** 2))
    return float(10.0 * np.log10(1.0 / max(mse, eps)))


def ssim(pred: np.ndarray, target: np.ndarray) -> float:
    # 与 common.simple_ssim 保持同样的全局 SSIM 近似，便于跨周比较。
    x, y = pred.astype(np.float64), target.astype(np.float64)
    c1, c2 = 0.01**2, 0.03**2
    mux, muy = x.mean(), y.mean()
    vx, vy = x.var(), y.var()
    cov = ((x - mux) * (y - muy)).mean()
    return float(((2 * mux * muy + c1) * (2 * cov + c2)) / ((mux**2 + muy**2 + c1) * (vx + vy + c2)))


def to_hwc(array: np.ndarray) -> np.ndarray:
    return np.transpose(np.clip(array[0], 0.0, 1.0), (1, 2, 0))


def to_u8(array: np.ndarray) -> np.ndarray:
    return (to_hwc(array) * 255.0 + 0.5).astype(np.uint8)


def save_diagnostics(sample_id: str, noisy: np.ndarray, clean: np.ndarray, fp32: np.ndarray, int8: np.ndarray, out_dir: Path) -> None:
    # 只保存最差样本的诊断图，突出 INT8 相对 FP32 的主要退化位置。
    err = np.mean(np.abs(int8 - fp32), axis=1)[0]
    scaled = np.clip(err * 32.0, 0.0, 1.0)
    heat = np.stack([scaled, np.sqrt(scaled), np.zeros_like(scaled)], axis=2)
    Image.fromarray((heat * 255.0 + 0.5).astype(np.uint8)).save(out_dir / "error_maps" / f"{sample_id}_int8_vs_fp32_x32.png")

    panels = [to_u8(noisy), to_u8(clean), to_u8(fp32), to_u8(int8), (heat * 255.0 + 0.5).astype(np.uint8)]
    sheet = Image.fromarray(np.concatenate(panels, axis=1))
    draw = ImageDraw.Draw(sheet)
    labels = ["noisy", "clean", "FP32", "INT8", "error x32"]
    width = panels[0].shape[1]
    for index, label in enumerate(labels):
        draw.rectangle((index * width, 0, index * width + 90, 18), fill=(0, 0, 0))
        draw.text((index * width + 3, 3), label, fill=(255, 255, 255))
    sheet.save(out_dir / "failure_cases" / f"{sample_id}_comparison.png")


class Reader(CalibrationDataReader):
    # ORT 静态量化通过 CalibrationDataReader 按需拉取校准样本。
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.rows = iter(rows)

    def get_next(self) -> dict[str, np.ndarray] | None:
        try:
            row = next(self.rows)
        except StopIteration:
            return None
        return {"input": load_input(row["noisy_path"])}


def run(session: ort.InferenceSession, inp: np.ndarray, warmup: int, runs: int) -> tuple[np.ndarray, list[float]]:
    # 返回最后一次输出和每次推理耗时；输出会裁剪到可视化/指标使用的 [0,1]。
    for _ in range(warmup):
        session.run(["output"], {"input": inp})
    timings = []
    output = None
    for _ in range(runs):
        start = time.perf_counter()
        output = session.run(["output"], {"input": inp})[0]
        timings.append((time.perf_counter() - start) * 1000.0)
    assert output is not None
    return np.clip(output, 0.0, 1.0), timings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ORT CPU QDQ INT8 evaluation with isolated calibration/evaluation sets.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--int8-onnx", default="models/onnx/dncnn_sidd_tiny_int8_qdq.onnx")
    parser.add_argument("--output-dir", default="outputs/week4_quantization")
    parser.add_argument("--calibration-count", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--diagnostic-count", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_manifest(ROOT / args.manifest)
    if not 0 < args.calibration_count < len(rows):
        raise ValueError("calibration-count must leave at least one independent evaluation sample.")
    # 校准集和评估集必须互斥，这是本周量化结论可信的关键约束。
    calibration_rows = rows[: args.calibration_count]
    evaluation_rows = rows[args.calibration_count :]
    calibration_ids = {row["id"] for row in calibration_rows}
    evaluation_ids = {row["id"] for row in evaluation_rows}
    if calibration_ids & evaluation_ids:
        raise RuntimeError("Calibration and evaluation manifests overlap.")

    out_dir = ROOT / args.output_dir
    for name in ("int8_outputs", "error_maps", "failure_cases"):
        (out_dir / name).mkdir(parents=True, exist_ok=True)
    write_manifest(ROOT / "data/calibration/week4_calibration_manifest.csv", calibration_rows)
    write_manifest(ROOT / "data/test_inputs/week4_evaluation_manifest.csv", evaluation_rows)

    fp32_model = ROOT / args.onnx
    int8_model = ROOT / args.int8_onnx
    int8_model.parent.mkdir(parents=True, exist_ok=True)
    quantize_static(
        # QDQ 格式保留量化/反量化节点，便于 ORT 执行和模型图审计。
        model_input=str(fp32_model),
        model_output=str(int8_model),
        calibration_data_reader=Reader(calibration_rows),
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        per_channel=True,
        calibrate_method=CalibrationMethod.MinMax,
    )

    fp32_session = ort.InferenceSession(str(fp32_model), providers=["CPUExecutionProvider"])
    int8_session = ort.InferenceSession(str(int8_model), providers=["CPUExecutionProvider"])
    metrics, fp32_times, int8_times = [], [], []
    arrays: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for row in evaluation_rows:
        # 每个评估样本同时跑 FP32 与 INT8，分别比较质量和 INT8 对齐误差。
        inp, clean = load_input(row["noisy_path"]), load_input(row["clean_path"])
        fp32_out, ft = run(fp32_session, inp, args.warmup, args.runs)
        int8_out, it = run(int8_session, inp, args.warmup, args.runs)
        fp32_times.extend(ft)
        int8_times.extend(it)
        diff = int8_out - fp32_out
        fp32_psnr, int8_psnr = psnr(fp32_out, clean), psnr(int8_out, clean)
        fp32_ssim, int8_ssim = ssim(fp32_out, clean), ssim(int8_out, clean)
        metrics.append(
            {
                "id": row["id"],
                "split": "evaluation",
                "fp32_psnr": fp32_psnr,
                "int8_psnr": int8_psnr,
                "psnr_drop": fp32_psnr - int8_psnr,
                "fp32_ssim": fp32_ssim,
                "int8_ssim": int8_ssim,
                "ssim_drop": fp32_ssim - int8_ssim,
                "max_abs_error": float(np.max(np.abs(diff))),
                "mean_abs_error": float(np.mean(np.abs(diff))),
                "rmse": float(np.sqrt(np.mean(diff**2))),
                "alignment_psnr": psnr(int8_out, fp32_out),
            }
        )
        Image.fromarray(to_u8(int8_out)).save(out_dir / "int8_outputs" / f"{row['id']}_int8_output.png")
        arrays[row["id"]] = (inp, clean, fp32_out, int8_out)

    worst = sorted(metrics, key=lambda row: float(row["psnr_drop"]), reverse=True)
    # 按 PSNR drop 排序，保存退化最大的样本，方便报告中解释量化风险。
    for row in worst[: args.diagnostic_count]:
        for directory in ("error_maps", "failure_cases"):
            (out_dir / directory).mkdir(parents=True, exist_ok=True)
        save_diagnostics(row["id"], *arrays[row["id"]], out_dir)

    with (out_dir / "week4_int8_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metrics[0].keys()))
        writer.writeheader()
        writer.writerows(metrics)
    summary = {
        "calibration_images": len(calibration_rows),
        "evaluation_images": len(evaluation_rows),
        "split_overlap": 0,
        "calibration_method": "MinMax",
        "quant_format": "QDQ",
        "activation_type": "QUInt8",
        "weight_type": "QInt8",
        "per_channel": True,
        "fp32_model_bytes": fp32_model.stat().st_size + fp32_model.with_suffix(fp32_model.suffix + ".data").stat().st_size,
        "int8_model_bytes": int8_model.stat().st_size,
        "mean_fp32_psnr": float(np.mean([row["fp32_psnr"] for row in metrics])),
        "mean_int8_psnr": float(np.mean([row["int8_psnr"] for row in metrics])),
        "mean_psnr_drop": float(np.mean([row["psnr_drop"] for row in metrics])),
        "max_psnr_drop": float(worst[0]["psnr_drop"]),
        "worst_sample": worst[0]["id"],
        "mean_ssim_drop": float(np.mean([row["ssim_drop"] for row in metrics])),
        "max_abs_error": max(float(row["max_abs_error"]) for row in metrics),
        "mean_fp32_latency_ms": float(np.mean(fp32_times)),
        "p50_fp32_latency_ms": float(np.percentile(fp32_times, 50)),
        "p90_fp32_latency_ms": float(np.percentile(fp32_times, 90)),
        "mean_int8_latency_ms": float(np.mean(int8_times)),
        "p50_int8_latency_ms": float(np.percentile(int8_times, 50)),
        "p90_int8_latency_ms": float(np.percentile(int8_times, 90)),
        "warmup_per_image": args.warmup,
        "runs_per_image": args.runs,
    }
    with (out_dir / "week4_int8_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(summary)


if __name__ == "__main__":
    main()
