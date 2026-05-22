from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
import rawpy

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.blc import apply_blc
from soft_isp.dpc import detect_defects, merge_channel_masks, repair_defects
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def make_preview(raw_array: np.ndarray, display_max: float | None = None) -> np.ndarray:
    if display_max is None:
        display_max = max(float(np.percentile(raw_array, 99.5)), 1.0)
    gray = np.clip(raw_array.astype(np.float32) / display_max, 0.0, 1.0)
    gray8 = (gray * 255).astype(np.uint8)
    return np.repeat(gray8[:, :, None], 3, axis=2)


def plot_mask_overlay(raw_path: Path, raw_blc: np.ndarray, mask: np.ndarray, out_dir: Path) -> Path:
    out_path = out_dir / f"{raw_path.stem}_dpc_mask_overlay.png"
    preview = make_preview(raw_blc)
    preview[mask] = np.array([255, 0, 0], dtype=np.uint8)

    fig, ax = plt.subplots(figsize=(10, 7), constrained_layout=True)
    ax.imshow(preview)
    ax.set_title(f"{raw_path.name} DPC candidate mask")
    ax.set_axis_off()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def strongest_candidate(mask: np.ndarray, before: np.ndarray, after: np.ndarray) -> tuple[int, int] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    diff = np.abs(before[ys, xs].astype(np.int32) - after[ys, xs].astype(np.int32))
    index = int(np.argmax(diff))
    return int(y := ys[index]), int(xs[index])


def crop_bounds(center_y: int, center_x: int, shape: tuple[int, int], size: int) -> tuple[int, int, int, int]:
    half = size // 2
    y0 = max(center_y - half, 0)
    x0 = max(center_x - half, 0)
    y1 = min(y0 + size, shape[0])
    x1 = min(x0 + size, shape[1])
    y0 = max(y1 - size, 0)
    x0 = max(x1 - size, 0)
    return y0, y1, x0, x1


def plot_repair_crop(
    raw_path: Path,
    before: np.ndarray,
    after: np.ndarray,
    mask: np.ndarray,
    out_dir: Path,
    crop_size: int,
) -> tuple[Path, dict | None]:
    out_path = out_dir / f"{raw_path.stem}_dpc_repair_crop.png"
    candidate = strongest_candidate(mask, before, after)
    if candidate is None:
        center_y = before.shape[0] // 2
        center_x = before.shape[1] // 2
    else:
        center_y, center_x = candidate

    y0, y1, x0, x1 = crop_bounds(center_y, center_x, before.shape, crop_size)
    before_crop = before[y0:y1, x0:x1]
    after_crop = after[y0:y1, x0:x1]
    mask_crop = mask[y0:y1, x0:x1]
    display_max = max(float(np.percentile(before_crop, 99.5)), float(np.percentile(after_crop, 99.5)), 1.0)

    fig, axes = plt.subplots(1, 3, figsize=(12, 4), constrained_layout=True)
    axes[0].imshow(make_preview(before_crop, display_max))
    axes[0].set_title("Before DPC")
    axes[1].imshow(make_preview(after_crop, display_max))
    axes[1].set_title("After DPC")
    axes[2].imshow(mask_crop, cmap="gray")
    axes[2].set_title("Candidate mask")

    for ax in axes:
        ax.set_axis_off()

    fig.savefig(out_path, dpi=150)
    plt.close(fig)

    crop_info = None
    if candidate is not None:
        crop_info = {
            "candidate_y": center_y,
            "candidate_x": center_x,
            "before": int(before[center_y, center_x]),
            "after": int(after[center_y, center_x]),
            "crop": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        }
    return out_path, crop_info


def analyze_one(raw_path: Path, out_dir: Path, min_delta: int, mad_k: float, crop_size: int) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        raw_pattern = raw.raw_pattern.copy()
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)

    out_dir.mkdir(parents=True, exist_ok=True)

    raw_blc = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    detection = detect_defects(raw_blc, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
    repaired = repair_defects(raw_blc, bayer_pattern, detection)
    full_mask = merge_channel_masks(raw_blc.shape, bayer_pattern, detection["masks"])

    overlay_path = plot_mask_overlay(raw_path, raw_blc, full_mask, out_dir)
    crop_path, crop_info = plot_repair_crop(raw_path, raw_blc, repaired, full_mask, out_dir, crop_size)

    channel_counts = {name: int(mask.sum()) for name, mask in detection["masks"].items()}
    total_count = int(full_mask.sum())
    changed_abs = np.abs(repaired.astype(np.int32) - raw_blc.astype(np.int32))
    changed_values = changed_abs[full_mask]

    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "min_delta": min_delta,
        "mad_k": mad_k,
        "raw_blc": describe_array(raw_blc),
        "dpc": describe_array(repaired),
        "candidate_count": total_count,
        "candidate_ratio": float(total_count / raw_blc.size),
        "channel_counts": channel_counts,
        "thresholds": {name: float(value) for name, value in detection["thresholds"].items()},
        "changed_abs_mean": float(np.mean(changed_values)) if total_count else 0.0,
        "changed_abs_max": float(np.max(changed_values)) if total_count else 0.0,
        "mask_overlay": str(overlay_path),
        "repair_crop": str(crop_path),
        "crop_info": crop_info,
    }

    json_path = out_dir / f"{raw_path.stem}_dpc.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def fmt(value: float) -> str:
    return f"{value:.4f}" if value < 1 else f"{value:.2f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 2-2 DPC 学习报告",
        "",
        "本次在 BLC 后继续做 DPC，也就是 Dead Pixel Correction，坏点检测与修复。这里先做一个保守版本：只寻找和同色邻域明显不一致的孤立异常点。",
        "",
        "## 为什么 DPC 要在 BLC 后做",
        "",
        "BLC 扣掉的是传感器基线偏置。DPC 判断的是某个像素是否相对邻域异常。如果不先做 BLC，像素值里还带着 black level 偏置，暗部异常的判断会不干净。所以顺序通常是：RAW -> BLC -> DPC -> 后续 Demosaic/AWB。",
        "",
        "## 本次算法",
        "",
        "Bayer RAW 相邻像素不是同一种颜色，所以不能直接拿上下左右像素比较。脚本先把 RAW 按 Bayer pattern 拆成 R / Gr / Gb / B 四个同色平面，然后在每个同色平面上做 3x3 中值检测。",
        "",
        "```text",
        "local_median = median(同色 3x3 邻域)",
        "residual = abs(pixel - local_median)",
        "threshold = max(min_delta, median(residual) + mad_k * MAD(residual))",
        "如果 residual > threshold，就标记为坏点候选",
        "修复值 = local_median",
        "```",
        "",
        "这里输出的是“坏点候选”，不是最终工厂标定意义上的永久坏点表。高光边缘、强纹理和噪声也可能被少量误检，所以后面要结合局部 crop 图判断。",
        "",
        "## 结果总表",
        "",
        "| 样张 | Bayer | 候选数 | 占比 | R | Gr | Gb | B | 最大修复幅度 | 观察 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]

    for result in results:
        counts = result["channel_counts"]
        observation = "候选点很少，符合保守检测预期" if result["candidate_ratio"] < 0.001 else "候选点偏多，需要看 mask 是否落在强边缘或高光区域"
        lines.append(
            "| {sid} | {pattern} | {count} | {ratio} | {r} | {gr} | {gb} | {b} | {max_change} | {obs} |".format(
                sid=result["sample_id"],
                pattern=result["bayer_pattern"],
                count=result["candidate_count"],
                ratio=fmt(float(result["candidate_ratio"])),
                r=counts.get("R", 0),
                gr=counts.get("Gr", 0),
                gb=counts.get("Gb", 0),
                b=counts.get("B", 0),
                max_change=fmt(float(result["changed_abs_max"])),
                obs=observation,
            )
        )

    lines.extend(
        [
            "",
            "## Mask 预览",
            "",
            "红色点表示 DPC 候选点。由于坏点通常很稀疏，全图上可能只看到少量红点；这恰好是正常现象。",
            "",
        ]
    )

    for result in results:
        overlay_rel = Path(result["mask_overlay"]).relative_to(report_path.parent).as_posix()
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                f"![{result['sample_id']} DPC mask]({overlay_rel})",
                "",
            ]
        )

    lines.extend(
        [
            "## 局部修复对比",
            "",
            "每张图选一个修复幅度最大的候选点附近做 crop。左边是 DPC 前，中间是 DPC 后，右边是候选 mask。",
            "",
        ]
    )

    for result in results:
        crop_rel = Path(result["repair_crop"]).relative_to(report_path.parent).as_posix()
        crop_info = result["crop_info"]
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} DPC repair crop]({crop_rel})", ""])
        if crop_info is None:
            lines.extend(["这张图没有检测到候选点，所以 crop 使用图像中心区域。", ""])
        else:
            lines.extend(
                [
                    f"- 候选坐标：x `{crop_info['candidate_x']}`，y `{crop_info['candidate_y']}`",
                    f"- 修复前后：`{crop_info['before']}` -> `{crop_info['after']}`",
                    "",
                ]
            )

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. DPC 的关键不是“看起来把图变漂亮”，而是避免单个异常像素污染后面的 Demosaic。",
            "2. Bayer RAW 里必须按同色像素比较，不能直接用相邻像素判断坏点。",
            "3. 中值适合修复孤立异常点，因为它不容易被单个极端值带偏。",
            "4. 当前版本是学习用的保守候选检测；真正产品里通常还会结合暗场/亮场标定、温度、曝光和固定坏点表。",
            "",
            "## 下一步",
            "",
            "DPC 做完后，下一步可以进入最有成就感的一步：Demosaic。先实现 bilinear demosaic，把 Bayer RAW 变成第一张 RGB 图。",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply BLC + DPC and write a learning report.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--report", type=Path, default=Path("reports/week2_dpc_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--crop-size", type=int, default=160)
    args = parser.parse_intermixed_args()

    results = [
        analyze_one(raw_path, args.out_dir, args.min_delta, args.mad_k, args.crop_size)
        for raw_path in args.raw_paths
    ]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
