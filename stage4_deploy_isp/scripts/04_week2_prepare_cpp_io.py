"""Week 2：为最小 C++ ONNX Runtime runner 准备输入和参考输出。

C++ runner 故意只依赖 PPM P6 和裸 float32 文件，避免引入图像库差异。该脚本
把 PNG 输入转成 PPM，同时用 Python ORT 生成 PNG 可视化参考和 .f32 张量参考，
用于验证 C++ 输出是否逐元素对齐。
"""

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
    parser.add_argument("--count", type=int, default=0, help="0 means all manifest rows.")
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    # manifest 来自 Week 0.5，保证 C++ I/O 测试不偷偷更换样本。
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_ppm_from_png(src: Path, dst: Path) -> None:
    # PPM P6 格式简单，C++ 端可以用少量代码读写，适合部署教学样例。
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.open(src).convert("RGB").save(dst)


def save_ort_reference(session: ort.InferenceSession, src: Path, dst: Path) -> None:
    # 保存 PNG 参考图用于肉眼检查 C++ runner 输出是否合理。
    image = Image.open(src).convert("RGB")
    arr = np.asarray(image, dtype=np.float32) / 255.0
    nchw = np.transpose(arr, (2, 0, 1))[None, ...]
    out = session.run(["output"], {"input": nchw})[0][0]
    out = np.clip(np.transpose(out, (1, 2, 0)), 0.0, 1.0)
    dst.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((out * 255.0 + 0.5).astype(np.uint8)).save(dst)


def save_ort_tensor_reference(session: ort.InferenceSession, src: Path, dst: Path) -> None:
    # 保存原始 float32 输出用于严格数值比较，避免 PNG 量化掩盖误差。
    image = Image.open(src).convert("RGB")
    arr = np.asarray(image, dtype=np.float32) / 255.0
    nchw = np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)
    out = session.run(["output"], {"input": nchw})[0].astype(np.float32)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.tofile(dst)


def main() -> None:
    args = parse_args()
    root = project_root()
    rows = read_manifest(root / args.manifest)
    if args.count > 0:
        # count 用于快速冒烟测试；默认 0 表示处理 manifest 中全部样本。
        rows = rows[: args.count]
    session = ort.InferenceSession(str(root / args.onnx), providers=["CPUExecutionProvider"])
    out_dir = root / args.output_dir
    for row in rows:
        sample_id = row["id"]
        noisy = Path(row["noisy_path"])
        save_ppm_from_png(noisy, out_dir / "ppm_inputs" / f"{sample_id}.ppm")
        save_ort_reference(session, noisy, out_dir / "ort_reference_png" / f"{sample_id}_ort_reference.png")
        save_ort_tensor_reference(session, noisy, out_dir / "ort_reference_f32" / f"{sample_id}_ort_reference.f32")
    print(f"Wrote C++ I/O fixtures to {out_dir}")


if __name__ == "__main__":
    main()
