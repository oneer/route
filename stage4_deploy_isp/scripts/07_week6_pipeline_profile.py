from __future__ import annotations

import argparse
import csv
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


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def preprocess(path: str) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    arr = np.asarray(image, dtype=np.float32) / 255.0
    # Placeholder for ISP preprocess: BLC/LSC/RAW pack would live before this
    # point for RAW-domain models. RGB denoise keeps only normalize + layout.
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)


def postprocess(output: np.ndarray) -> Image.Image:
    out = np.clip(output[0], 0.0, 1.0)
    hwc = np.transpose(out, (1, 2, 0))
    return Image.fromarray((hwc * 255.0 + 0.5).astype(np.uint8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 6 end-to-end pipeline profile.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--output-dir", default="outputs/week6_pipeline")
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--runs", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    out_dir = root / args.output_dir
    (out_dir / "outputs").mkdir(parents=True, exist_ok=True)
    rows = read_manifest(root / args.manifest)
    session = ort.InferenceSession(str(root / args.onnx), providers=["CPUExecutionProvider"])

    records = []
    for row in rows:
        warm_input = preprocess(row["noisy_path"])
        for _ in range(args.warmup):
            session.run(["output"], {"input": warm_input})
        sample_records = []
        last_image = None
        for run_index in range(args.runs):
            t0 = time.perf_counter()
            inp = preprocess(row["noisy_path"])
            t1 = time.perf_counter()
            pred = session.run(["output"], {"input": inp})[0]
            t2 = time.perf_counter()
            last_image = postprocess(pred)
            t3 = time.perf_counter()
            sample_records.append(
                {
                    "id": row["id"],
                    "run": run_index,
                    "preprocess_ms": (t1 - t0) * 1000.0,
                    "inference_ms": (t2 - t1) * 1000.0,
                    "postprocess_ms": (t3 - t2) * 1000.0,
                    "compute_e2e_ms": (t3 - t0) * 1000.0,
                }
            )
        assert last_image is not None
        save_start = time.perf_counter()
        last_image.save(out_dir / "outputs" / f"{row['id']}_pipeline_output.png")
        save_ms = (time.perf_counter() - save_start) * 1000.0
        for record in sample_records:
            record["save_ms_once"] = save_ms
            record["e2e_with_save_once_ms"] = record["compute_e2e_ms"] + save_ms
            record["warmup"] = args.warmup
            record["runs"] = args.runs
        records.extend(sample_records)

    with (out_dir / "week6_pipeline_profile.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    summary = {"samples": len(rows), "warmup_per_image": args.warmup, "runs_per_image": args.runs}
    for key in ("preprocess_ms", "inference_ms", "postprocess_ms", "compute_e2e_ms"):
        values = [r[key] for r in records]
        summary[f"mean_{key}"] = float(np.mean(values))
        summary[f"p50_{key}"] = float(np.percentile(values, 50))
        summary[f"p90_{key}"] = float(np.percentile(values, 90))
    summary["mean_save_ms_once"] = float(np.mean([r["save_ms_once"] for r in records]))
    summary["includes_io"] = "compute_e2e=no; e2e_with_save_once=yes"
    with (out_dir / "week6_pipeline_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(summary)


if __name__ == "__main__":
    main()
