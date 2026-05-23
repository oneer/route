from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import imageio.v3 as iio
import matplotlib
import numpy as np
import rawpy

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.blc import apply_blc
from soft_isp.demosaic import bilinear_demosaic, rgb_preview
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def describe_rgb(rgb: np.ndarray) -> dict:
    return {
        "shape": rgb.shape,
        "dtype": str(rgb.dtype),
        "R": describe_array(rgb[:, :, 0]),
        "G": describe_array(rgb[:, :, 1]),
        "B": describe_array(rgb[:, :, 2]),
    }


def save_rgb_preview(raw_path: Path, preview: np.ndarray, out_dir: Path) -> Path:
    out_path = out_dir / f"{raw_path.stem}_demosaic_rgb.png"
    iio.imwrite(out_path, preview)
    return out_path


def make_raw_preview(raw_array: np.ndarray, display_max: float) -> np.ndarray:
    gray = np.clip(raw_array.astype(np.float32) / max(display_max, 1.0), 0.0, 1.0)
    gray8 = (gray * 255).astype(np.uint8)
    return np.repeat(gray8[:, :, None], 3, axis=2)


def save_compare_figure(
    raw_path: Path,
    raw_preview: np.ndarray,
    rgb_preview_image: np.ndarray,
    reference_dir: Path,
    out_dir: Path,
) -> Path:
    out_path = out_dir / f"{raw_path.stem}_demosaic_compare.png"
    reference_path = reference_dir / f"{raw_path.stem}_rawpy_srgb.png"

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.5), constrained_layout=True)
    axes[0].imshow(raw_preview)
    axes[0].set_title("Bayer RAW after BLC + DPC")
    axes[1].imshow(rgb_preview_image)
    axes[1].set_title("Bilinear demosaic RGB")

    if reference_path.exists():
        reference = iio.imread(reference_path)
        axes[2].imshow(reference)
        axes[2].set_title("rawpy reference ISP")
    else:
        axes[2].imshow(np.zeros_like(rgb_preview_image))
        axes[2].set_title("rawpy reference missing")

    for ax in axes:
        ax.set_axis_off()

    fig.suptitle(raw_path.name)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def analyze_one(
    raw_path: Path,
    out_dir: Path,
    reference_dir: Path,
    min_delta: int,
    mad_k: float,
) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        raw_pattern = raw.raw_pattern.copy()
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)
        display_flip = int(raw.sizes.flip)

    out_dir.mkdir(parents=True, exist_ok=True)

    raw_blc = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    detection = detect_defects(raw_blc, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
    raw_dpc = repair_defects(raw_blc, bayer_pattern, detection)
    rgb_linear = bilinear_demosaic(raw_dpc, bayer_pattern)

    display_white = float(np.percentile(rgb_linear, 99.5))
    raw_preview = apply_rawpy_orientation(make_raw_preview(raw_dpc, display_white), display_flip)
    preview = apply_rawpy_orientation(rgb_preview(rgb_linear, white=display_white), display_flip)
    preview_path = save_rgb_preview(raw_path, preview, out_dir)
    compare_path = save_compare_figure(raw_path, raw_preview, preview, reference_dir, out_dir)

    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "display_flip": display_flip,
        "display_white_p995": display_white,
        "raw_blc": describe_array(raw_blc),
        "raw_dpc": describe_array(raw_dpc),
        "rgb_linear": describe_rgb(rgb_linear),
        "preview": str(preview_path),
        "compare": str(compare_path),
    }

    json_path = out_dir / f"{raw_path.stem}_demosaic.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def fmt(value: float) -> str:
    return f"{value:.2f}"


def write_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 3 Demosaic 学习报告",
        "",
        "本次只做一个小闭环：把 BLC + DPC 后的单通道 Bayer RAW，转换成三通道 RGB 图。这里实现的是最基础的 bilinear demosaic，目标是理解原理，不追求最终颜色好看。",
        "",
        "## Demosaic 要解决什么问题",
        "",
        "Bayer RAW 的每个像素只记录一种颜色：R、G 或 B。也就是说，原始图像不是每个位置都有完整的 RGB 三个值，而是一个马赛克排列。",
        "",
        "以 RGGB 为例：",
        "",
        "```text",
        "R  G  R  G ...",
        "G  B  G  B ...",
        "R  G  R  G ...",
        "```",
        "",
        "Demosaic 的任务就是：在每一个像素位置，把缺失的另外两个颜色估计出来。做完以后，图像形状会从 `(H, W)` 变成 `(H, W, 3)`。",
        "",
        "## 本次 bilinear 的核心思想",
        "",
        "对某个颜色通道来说，已经采到的位置保留原值，没采到的位置用周围同色像素做加权平均。越近的像素权重越大。",
        "",
        "```text",
        "1 2 1",
        "2 4 2",
        "1 2 1",
        "```",
        "",
        "代码里对 R、G、B 分别做一次插值，然后 stack 成 RGB。注意 G 有两个 Bayer 位置，但它们都属于绿色通道，所以会合并成一个 G 平面。",
        "",
        "## 从数学上怎么理解 Bayer RAW",
        "",
        "可以把理想彩色图像写成三个完整通道：",
        "",
        "```text",
        "RGB(y, x) = [R(y, x), G(y, x), B(y, x)]",
        "```",
        "",
        "但 Bayer 传感器在每个像素位置只采一种颜色，所以 RAW 是二维数组，不是三通道数组：",
        "",
        "```text",
        "RAW(y, x) = R(y, x)  如果该位置是 R 像素",
        "RAW(y, x) = G(y, x)  如果该位置是 G 像素",
        "RAW(y, x) = B(y, x)  如果该位置是 B 像素",
        "```",
        "",
        "为了描述这个采样过程，可以给每个颜色定义一个 mask：",
        "",
        "```text",
        "M_R(y, x) = 1 表示这个位置真实采到了 R，否则为 0",
        "M_G(y, x) = 1 表示这个位置真实采到了 G，否则为 0",
        "M_B(y, x) = 1 表示这个位置真实采到了 B，否则为 0",
        "```",
        "",
        "于是 Bayer RAW 可以写成：",
        "",
        "```text",
        "RAW = M_R * R + M_G * G + M_B * B",
        "```",
        "",
        "这里的 `*` 是逐像素相乘。每个位置只会有一个 mask 等于 1，所以 RAW 里每个像素只保存一个颜色值。",
        "",
        "Demosaic 的目标是从这个不完整采样里估计出完整的三个通道：",
        "",
        "```text",
        "R_hat(y, x), G_hat(y, x), B_hat(y, x)",
        "RGB_hat(y, x) = [R_hat(y, x), G_hat(y, x), B_hat(y, x)]",
        "```",
        "",
        "`hat` 表示估计值。也就是说，Demosaic 输出里的很多颜色值不是传感器直接测到的，而是算法根据邻域推出来的。",
        "",
        "## Bayer 位置关系",
        "",
        "以 RGGB 为例，2x2 周期是：",
        "",
        "```text",
        "(0,0) R    (0,1) G",
        "(1,0) G    (1,1) B",
        "```",
        "",
        "也就是：",
        "",
        "```text",
        "偶数行、偶数列 -> R",
        "偶数行、奇数列 -> G，通常记作 Gr",
        "奇数行、偶数列 -> G，通常记作 Gb",
        "奇数行、奇数列 -> B",
        "```",
        "",
        "因此每个位置都会缺两个颜色：R 位置缺 G/B，G 位置缺 R/B，B 位置缺 R/G。Demosaic 不是简单地把图变彩色，而是在每个像素位置补两个缺失通道。",
        "",
        "## Bilinear 插值公式",
        "",
        "Bilinear demosaic 的基本假设是：局部区域内，同一个颜色通道变化比较平滑。一个没采到 R 的位置，它的 R 值可以用附近真实采到的 R 像素估计。",
        "",
        "通用的加权平均公式是：",
        "",
        "```text",
        "C_hat(y, x) = sum(w_i * C_i) / sum(w_i)",
        "```",
        "",
        "其中 `C` 可以是 R/G/B，`C_i` 是附近真实采到的同色像素，`w_i` 是权重。越近的同色像素，权重越大。",
        "",
        "本次代码用 3x3 加权核：",
        "",
        "```text",
        "1 2 1",
        "2 4 2",
        "1 2 1",
        "```",
        "",
        "用 mask + 卷积可以统一写成：",
        "",
        "```text",
        "weighted_sum = conv(raw * mask, kernel)",
        "weight_sum   = conv(mask,       kernel)",
        "C_hat        = weighted_sum / weight_sum",
        "```",
        "",
        "为什么要除以 `weight_sum`？因为 Bayer 图上不是每个 3x3 邻域都有相同数量的同色采样点。除以有效权重和以后，结果才是真正的局部加权平均。",
        "",
        "最后还要把真实采样位置改回原值：",
        "",
        "```text",
        "C_hat(y, x) = RAW(y, x)  如果 mask_C(y, x) = 1",
        "```",
        "",
        "真实采到的值比插值估计更可信，所以不能被卷积结果覆盖。",
        "",
        "## 一个 5x5 小例子",
        "",
        "只看 RGGB 里的 R 通道，R 真实存在的位置是：",
        "",
        "```text",
        "R  .  R  .  R",
        ".  .  .  .  .",
        "R  .  R  .  R",
        ".  .  .  .  .",
        "R  .  R  .  R",
        "```",
        "",
        "点号表示这个位置没有 R，需要估计。两个 R 中间的位置可以理解为：",
        "",
        "```text",
        "R_hat = (左边 R + 右边 R) / 2",
        "```",
        "",
        "四个 R 中间的位置可以理解为：",
        "",
        "```text",
        "R_hat = (左上 R + 右上 R + 左下 R + 右下 R) / 4",
        "```",
        "",
        "G 通道更密，因为 Bayer 中有两个 G，所以绿色插值通常比 R/B 更稳定。这也是 Bayer 设计中绿色像素最多的原因：人眼对亮度细节更敏感，而亮度信息很大程度来自绿色通道。",
        "",
        "## 本次算法完整流程",
        "",
        "```text",
        "读取 DNG",
        "  -> 取 raw_image_visible",
        "  -> 从 metadata 推断 Bayer pattern",
        "  -> BLC：扣 black level",
        "  -> DPC：修复坏点候选",
        "  -> Bilinear Demosaic：补齐 RGB 三通道",
        "  -> Preview：为了保存 PNG 做显示缩放",
        "  -> 写 JSON、PNG、Markdown 报告",
        "```",
        "",
        "严格来说，真正属于 Demosaic 的只有：",
        "",
        "```text",
        "raw_dpc -> bilinear_demosaic(raw_dpc, bayer_pattern) -> rgb_linear",
        "```",
        "",
        "`rgb_preview()` 只是为了把线性 RGB 映射成方便肉眼看的 8-bit PNG，不属于 Demosaic 算法本身。",
        "",
        "## Bilinear 的优点和缺点",
        "",
        "优点：原理直观、实现简单、速度快，适合作为第一个 baseline。",
        "",
        "缺点：它不判断边缘方向，只做局部平均，所以边缘容易变糊；在高频纹理区可能出现假彩色、拉链边等伪影。后续更高级的 demosaic 方法会根据边缘方向选择插值方向，避免跨边缘平均。",
        "",
        "## 它和 rawpy reference 为什么不一样",
        "",
        "下面的左图是我们自己的结果，右图是 rawpy 的完整 ISP 参考图。两者不能直接按颜色好坏比较，因为 rawpy reference 通常还做了白平衡、颜色矩阵、gamma、亮度映射等步骤。本次输出只验证 demosaic 是否把图像结构补出来，颜色偏绿或偏暗是正常现象。",
        "",
        "## 结果总表",
        "",
        "| 样张 | Bayer | RAW shape | RGB shape | display white p99.5 | R mean | G mean | B mean | 观察 |",
        "|---|---|---|---|---:|---:|---:|---:|---|",
    ]

    for result in results:
        rgb_stats = result["rgb_linear"]
        observation = "结构正常，颜色还不是最终 ISP 颜色"
        lines.append(
            "| {sid} | {pattern} | {raw_shape} | {rgb_shape} | {white} | {r} | {g} | {b} | {obs} |".format(
                sid=result["sample_id"],
                pattern=result["bayer_pattern"],
                raw_shape=tuple(result["raw_dpc"]["shape"]),
                rgb_shape=tuple(rgb_stats["shape"]),
                white=fmt(float(result["display_white_p995"])),
                r=fmt(float(rgb_stats["R"]["mean"])),
                g=fmt(float(rgb_stats["G"]["mean"])),
                b=fmt(float(rgb_stats["B"]["mean"])),
                obs=observation,
            )
        )

    lines.extend(
        [
            "",
            "## 对比图",
            "",
            "这组图从左到右展示模块前后关系：左边是 Demosaic 之前的单通道 Bayer RAW，中间是我们用 bilinear 算法补齐后的 RGB，右边是 rawpy 的完整 ISP 参考。这里重点看结构是否从“灰度马赛克采样”变成“完整 RGB 图像”，不要直接用颜色好不好看来评价 demosaic 本身。",
            "",
        ]
    )

    for result in results:
        compare_rel = Path(os.path.relpath(result["compare"], report_path.parent)).as_posix()
        lines.extend(
            [
                f"### {result['sample_id']}",
                "",
                f"![{result['sample_id']} demosaic compare]({compare_rel})",
                "",
            ]
        )

    lines.extend(
        [
            "## 代码怎么读",
            "",
            "本次新增的核心代码在 `soft_isp/demosaic.py`，可以按这条线看：",
            "",
            "1. `bayer_positions()`：根据 RGGB/BGGR/GRBG/GBRG 找到 R、G、B 在 2x2 Bayer block 里的位置。",
            "2. `_known_mask()`：生成一个 mask，标记某个颜色真实存在的位置。比如 R mask 只在 R 像素位置为 1。",
            "3. `_interpolate_channel()`：先算 `conv(raw * mask, kernel)`，再除以 `conv(mask, kernel)`，得到缺失位置的同色加权平均值，并把真实采样位置改回原值。",
            "4. `bilinear_demosaic()`：分别补 R/G/B，再合成 `(H, W, 3)`。",
            "5. `rgb_preview()`：只是为了保存 PNG 做显示缩放，不属于严格意义上的 demosaic。",
            "",
            "## 今天要记住的结论",
            "",
            "1. BLC 和 DPC 仍然在单通道 Bayer 上工作；Demosaic 是第一次把 RAW 变成 RGB 三通道。",
            "2. Demosaic 本质是估计缺失颜色，不是调色。",
            "3. bilinear 很容易理解，但边缘容易糊，也可能产生彩色伪影；后面更高级的方法会重点改善边缘。",
            "4. Demosaic 后的图还不是最终照片，因为还缺 AWB、CCM、gamma/tone mapping。",
            "",
            "## 下一步",
            "",
            "下一步最自然的是 AWB，也就是白平衡。因为现在已经有 RGB 三个通道了，我们可以开始估计每个通道应该乘多少增益，让灰色物体重新接近灰色。",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply BLC + DPC + bilinear demosaic and write a learning report.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report", type=Path, default=Path("reports/week3/demosaic_report.md"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    args = parser.parse_intermixed_args()

    results = [
        analyze_one(raw_path, args.out_dir, args.reference_dir, args.min_delta, args.mad_k)
        for raw_path in args.raw_paths
    ]
    write_report(results, args.report)
    print(args.report)


if __name__ == "__main__":
    main()
