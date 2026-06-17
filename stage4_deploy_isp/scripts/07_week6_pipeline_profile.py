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
        t0 = time.perf_counter()
        inp = preprocess(row["noisy_path"])
        t1 = time.perf_counter()
        pred = session.run(["output"], {"input": inp})[0]
        t2 = time.perf_counter()
        image = postprocess(pred)
        t3 = time.perf_counter()
        image.save(out_dir / "outputs" / f"{row['id']}_pipeline_output.png")
        t4 = time.perf_counter()
        records.append(
            {
                "id": row["id"],
                "preprocess_ms": (t1 - t0) * 1000.0,
                "inference_ms": (t2 - t1) * 1000.0,
                "postprocess_ms": (t3 - t2) * 1000.0,
                "save_ms": (t4 - t3) * 1000.0,
                "end_to_end_ms": (t4 - t0) * 1000.0,
            }
        )

    with (out_dir / "week6_pipeline_profile.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    summary = {
        "mean_preprocess_ms": float(np.mean([r["preprocess_ms"] for r in records])),
        "mean_inference_ms": float(np.mean([r["inference_ms"] for r in records])),
        "mean_postprocess_ms": float(np.mean([r["postprocess_ms"] for r in records])),
        "mean_save_ms": float(np.mean([r["save_ms"] for r in records])),
        "mean_end_to_end_ms": float(np.mean([r["end_to_end_ms"] for r in records])),
    }
    with (out_dir / "week6_pipeline_summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    print(summary)


if __name__ == "__main__":
    main()

