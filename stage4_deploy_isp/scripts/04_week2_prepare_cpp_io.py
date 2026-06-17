from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deploy.common import load_yaml, project_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare PPM input and ORT reference for C++ runner.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--output-dir", default="outputs/week2_cpp_io")
    parser.add_argument("--count", type=int, default=3)
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_ppm_from_png(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("RGB").save(dst)


def save_ort_reference(session: ort.InferenceSession, src: Path, dst: Path) -> None:
    image = Image.open(src).convert("RGB")
    arr = np.asarray(image, dtype=np.float32) / 255.0
    nchw = np.transpose(arr, (2, 0, 1))[None, ...]
    out = session.run(["output"], {"input": nchw})[0][0]
    out = np.clip(np.transpose(out, (1, 2, 0)), 0.0, 1.0)
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((out * 255.0 + 0.5).astype(np.uint8)).save(dst)


def main() -> None:
    args = parse_args()
    root = project_root()
    rows = read_manifest(root / args.manifest)[: args.count]
    session = ort.InferenceSession(str(root / args.onnx), providers=["CPUExecutionProvider"])
    out_dir = root / args.output_dir
    for row in rows:
        sample_id = row["id"]
        noisy = Path(row["noisy_path"])
        save_ppm_from_png(noisy, out_dir / "ppm_inputs" / f"{sample_id}.ppm")
        save_ort_reference(session, noisy, out_dir / "ort_reference_png" / f"{sample_id}_ort_reference.png")
    print(f"Wrote C++ I/O fixtures to {out_dir}")


if __name__ == "__main__":
    main()

