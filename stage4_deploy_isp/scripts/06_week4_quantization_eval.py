from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
from PIL import Image

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deploy.common import project_root


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_input(path: str) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)


def psnr_np(pred: np.ndarray, target: np.ndarray, eps: float = 1e-8) -> float:
    mse = float(np.mean((pred - target) ** 2))
    return float(10.0 * np.log10(1.0 / max(mse, eps)))


def global_ssim_np(pred: np.ndarray, target: np.ndarray) -> float:
    x = pred.astype(np.float64)
    y = target.astype(np.float64)
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2
    mux = x.mean()
    muy = y.mean()
    vx = x.var()
    vy = y.var()
    cov = ((x - mux) * (y - muy)).mean()
    return float(((2 * mux * muy + c1) * (2 * cov + c2)) / ((mux * mux + muy * muy + c1) * (vx + vy + c2)))


class FixedSetCalibrationReader(CalibrationDataReader):
    def __init__(self, rows: list[dict[str, str]], input_name: str = "input") -> None:
        self.rows = rows
        self.input_name = input_name
        self.index = 0

    def get_next(self) -> dict[str, np.ndarray] | None:
        if self.index >= len(self.rows):
            return None
        row = self.rows[self.index]
        self.index += 1
        return {self.input_name: load_input(row["noisy_path"])}


def run_latency(session: ort.InferenceSession, inp: np.ndarray, runs: int) -> tuple[np.ndarray, list[float]]:
    for _ in range(3):
        session.run(["output"], {"input": inp})
    timings = []
    output = None
    for _ in range(runs):
        start = time.perf_counter()
        output = session.run(["output"], {"input": inp})[0]
        timings.append((time.perf_counter() - start) * 1000.0)
    assert output is not None
    return np.clip(output, 0.0, 1.0), timings


def save_png(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    hwc = np.transpose(array[0], (1, 2, 0))
    Image.fromarray((np.clip(hwc, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)).save(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 4 INT8 quantization eval.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--int8-onnx", default="models/onnx/dncnn_sidd_tiny_int8_qdq.onnx")
    parser.add_argument("--output-dir", default="outputs/week4_quantization")
    parser.add_argument("--calibration-count", type=int, default=10)
    parser.add_argument("--runs", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    rows = read_manifest(root / args.manifest)
    fp32_model = root / args.onnx
    int8_model = root / args.int8_onnx
    int8_model.parent.mkdir(parents=True, exist_ok=True)
    out_dir = root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    quantize_static(
        model_input=str(fp32_model),
        model_output=str(int8_model),
        calibration_data_reader=FixedSetCalibrationReader(rows[: args.calibration_count]),
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        per_channel=True,
    )

    fp32_session = ort.InferenceSession(str(fp32_model), providers=["CPUExecutionProvider"])
    int8_session = ort.InferenceSession(str(int8_model), providers=["CPUExecutionProvider"])

    metric_rows = []
    fp32_times_all = []
    int8_times_all = []
    for row in rows:
        inp = load_input(row["noisy_path"])
        clean = load_input(row["clean_path"])
        fp32_out, fp32_times = run_latency(fp32_session, inp, args.runs)
        int8_out, int8_times = run_latency(int8_session, inp, args.runs)
        fp32_times_all.extend(fp32_times)
        int8_times_all.extend(int8_times)
        metric_rows.append(
            {
                "id": row["id"],
                "fp32_psnr": psnr_np(fp32_out, clean),
                "int8_psnr": psnr_np(int8_out, clean),
                "psnr_drop": psnr_np(fp32_out, clean) - psnr_np(int8_out, clean),
                "fp32_ssim": global_ssim_np(fp32_out, clean),
                "int8_ssim": global_ssim_np(int8_out, clean),
                "ssim_drop": global_ssim_np(fp32_out, clean) - global_ssim_np(int8_out, clean),
                "int8_vs_fp32_max_abs_error": float(np.max(np.abs(int8_out - fp32_out))),
                "int8_vs_fp32_mean_abs_error": float(np.mean(np.abs(int8_out - fp32_out))),
            }
        )
        save_png(int8_out, out_dir / "int8_outputs" / f"{row['id']}_int8_output.png")

    with (out_dir / "week4_int8_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(metric_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metric_rows)

    worst = max(metric_rows, key=lambda r: float(r["psnr_drop"]))
    summary = {
        "num_images": len(rows),
        "calibration_count": args.calibration_count,
        "mean_fp32_psnr": float(np.mean([r["fp32_psnr"] for r in metric_rows])),
        "mean_int8_psnr": float(np.mean([r["int8_psnr"] for r in metric_rows])),
        "mean_psnr_drop": float(np.mean([r["psnr_drop"] for r in metric_rows])),
        "max_psnr_drop": float(worst["psnr_drop"]),
        "worst_sample": worst["id"],
        "mean_fp32_latency_ms": float(np.mean(fp32_times_all)),
        "mean_int8_latency_ms": float(np.mean(int8_times_all)),
        "p50_fp32_latency_ms": float(np.percentile(fp32_times_all, 50)),
        "p50_int8_latency_ms": float(np.percentile(int8_times_all, 50)),
    }
    with (out_dir / "week4_int8_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(summary)


if __name__ == "__main__":
    main()

