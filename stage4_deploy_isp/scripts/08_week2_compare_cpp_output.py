"""Week 2：比较 C++ runner 与 Python ORT 的裸 float32 输出。

PPM 图片只能证明可视化结果接近，不能证明张量完全对齐。本脚本读取 C++ 输出的
.f32 文件和 Python ORT 参考 .f32 文件，逐元素统计误差并给出 pass/fail。
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


def psnr(pred: np.ndarray, target: np.ndarray, eps: float = 1e-12) -> float:
    # 这里比较的是两个推理后端输出，不是图像质量；eps 取更小以放大极小差异。
    mse = float(np.mean((pred - target) ** 2))
    return float(10.0 * np.log10(1.0 / max(mse, eps)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare C++ ORT raw float outputs with Python ORT.")
    parser.add_argument("--cpp-dir", default="stage4_deploy_isp/outputs/week2_cpp_io/cpp_outputs_f32")
    parser.add_argument("--ref-dir", default="stage4_deploy_isp/outputs/week2_cpp_io/ort_reference_f32")
    parser.add_argument("--output", default="stage4_deploy_isp/outputs/week2_cpp_io/week2_cpp_tensor_alignment.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cpp_dir = Path(args.cpp_dir)
    ref_dir = Path(args.ref_dir)
    rows = []
    for ref_path in sorted(ref_dir.glob("*_ort_reference.f32")):
        # 文件名约定来自 04_week2_prepare_cpp_io.py 和 C++ runner 的输出路径。
        sample_id = ref_path.name.removesuffix("_ort_reference.f32")
        cpp_path = cpp_dir / f"{sample_id}_cpp_output.f32"
        if not cpp_path.exists():
            continue
        ref = np.fromfile(ref_path, dtype=np.float32)
        cpp = np.fromfile(cpp_path, dtype=np.float32)
        if cpp.shape != ref.shape:
            # 张量长度不一致说明输出形状或写文件逻辑错误，不能继续比较数值。
            raise ValueError(f"{sample_id}: tensor size mismatch {cpp.size} != {ref.size}")
        err = np.abs(cpp - ref)
        rows.append(
            {
                "id": sample_id,
                "elements": cpp.size,
                "max_abs_error": float(err.max()),
                "mean_abs_error": float(err.mean()),
                "rmse": float(np.sqrt(np.mean((cpp - ref) ** 2))),
                "psnr": psnr(cpp, ref),
                # 1e-5 是 FP32 CPU 后端之间通常应达到的严格对齐阈值。
                "status": "pass" if float(err.max()) <= 1e-5 else "fail",
            }
        )
    if not rows:
        raise FileNotFoundError("No matching C++ and Python raw tensor outputs were found.")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "samples": len(rows),
        "max_abs_error": max(row["max_abs_error"] for row in rows),
        "mean_abs_error": float(np.mean([row["mean_abs_error"] for row in rows])),
        "all_pass": all(row["status"] == "pass" for row in rows),
    }
    print(summary)


if __name__ == "__main__":
    main()
