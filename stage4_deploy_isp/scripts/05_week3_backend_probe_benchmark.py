from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deploy.common import project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 3 backend probe and ORT FP32 benchmark.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--output-dir", default="outputs/week3_backend")
    parser.add_argument("--runs", type=int, default=20)
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_input(path: str) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)


def benchmark(session: ort.InferenceSession, inp: np.ndarray, runs: int) -> list[float]:
    for _ in range(3):
        session.run(["output"], {"input": inp})
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        session.run(["output"], {"input": inp})
        times.append((time.perf_counter() - start) * 1000.0)
    return times


def main() -> None:
    args = parse_args()
    root = project_root()
    out_dir = root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_manifest(root / args.manifest)

    providers = ort.get_available_providers()
    tools = {
        "trtexec": shutil.which("trtexec"),
        "nvcc": shutil.which("nvcc"),
        "nvidia-smi": shutil.which("nvidia-smi"),
        "cmake": shutil.which("cmake"),
    }

    session = ort.InferenceSession(str(root / args.onnx), providers=["CPUExecutionProvider"])
    result_rows = []
    all_times = []
    for row in rows:
        inp = load_input(row["noisy_path"])
        times = benchmark(session, inp, args.runs)
        all_times.extend(times)
        result_rows.append(
            {
                "id": row["id"],
                "mean_ms": float(np.mean(times)),
                "std_ms": float(np.std(times)),
                "p50_ms": float(np.percentile(times, 50)),
                "p90_ms": float(np.percentile(times, 90)),
            }
        )

    with (out_dir / "week3_ort_cpu_latency.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result_rows[0].keys()))
        writer.writeheader()
        writer.writerows(result_rows)

    summary = {
        "available_providers": ";".join(providers),
        "trtexec": tools["trtexec"] or "missing",
        "nvcc": tools["nvcc"] or "missing",
        "nvidia_smi": tools["nvidia-smi"] or "missing",
        "cmake": tools["cmake"] or "missing",
        "ort_cpu_mean_ms": float(np.mean(all_times)),
        "ort_cpu_std_ms": float(np.std(all_times)),
        "ort_cpu_p50_ms": float(np.percentile(all_times, 50)),
        "ort_cpu_p90_ms": float(np.percentile(all_times, 90)),
    }
    with (out_dir / "week3_backend_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(summary)


if __name__ == "__main__":
    main()

