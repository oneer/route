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

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.blc import apply_blc
from soft_isp.ccm import apply_ccm, ccm_from_rawpy_color_matrix
from soft_isp.demosaic import bilinear_demosaic
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array
from soft_isp.tone import apply_gamma, normalize_by_percentile, reinhard_tone_map, to_uint8


def sample_id(raw_path: Path) -> str:
    return raw_path.name.split("_", 1)[0]


def describe_rgb(rgb: np.ndarray) -> dict:
    return {
        "shape": list(rgb.shape),
        "R": describe_array(rgb[:, :, 0]),
        "G": describe_array(rgb[:, :, 1]),
        "B": describe_array(rgb[:, :, 2]),
    }


def rgb_mean(rgb: np.ndarray) -> list[float]:
    return [float(v) for v in np.mean(rgb.reshape(-1, 3), axis=0)]


def save_compare(path: Path, title: str, panels: list[tuple[str, np.ndarray]]) -> None:
    fig, axes = plt.subplots(1, len(panels), figsize=(5.0 * len(panels), 4.2), constrained_layout=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (panel_title, image) in zip(axes, panels):
        ax.imshow(image)
        ax.set_title(panel_title)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def reference_panel(raw_path: Path, reference_dir: Path, fallback: np.ndarray) -> np.ndarray:
    reference_path = reference_dir / f"{raw_path.stem}_rawpy_srgb.png"
    if reference_path.exists():
        return iio.imread(reference_path)
    return np.zeros_like(fallback)


def analyze_one(
    raw_path: Path,
    out_dir: Path,
    reference_dir: Path,
    min_delta: int,
    mad_k: float,
    gamma_value: float,
    tone_percentile: float,
) -> dict:
    with rawpy.imread(str(raw_path)) as raw:
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        raw_pattern = raw.raw_pattern.copy()
        black_levels = list(raw.black_level_per_channel)
        white_level = int(raw.white_level)
        display_flip = int(raw.sizes.flip)
        ccm = ccm_from_rawpy_color_matrix(raw.color_matrix)

    out_dir.mkdir(parents=True, exist_ok=True)

    raw_blc = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    detection = detect_defects(raw_blc, bayer_pattern, min_delta=min_delta, mad_k=mad_k)
    raw_dpc = repair_defects(raw_blc, bayer_pattern, detection)
    rgb_linear = bilinear_demosaic(raw_dpc, bayer_pattern)
    gains = gray_world_gains(rgb_linear)
    rgb_awb = apply_awb(rgb_linear, gains, white_level=white_level)
    rgb_ccm = apply_ccm(rgb_awb, ccm, white_level=white_level)

    awb_preview = to_uint8(apply_gamma(normalize_by_percentile(rgb_awb, tone_percentile), gamma_value))
    ccm_preview = to_uint8(apply_gamma(normalize_by_percentile(rgb_ccm, tone_percentile), gamma_value))
    linear_display_preview = to_uint8(normalize_by_percentile(rgb_ccm, tone_percentile))
    gamma_preview = to_uint8(apply_gamma(normalize_by_percentile(rgb_ccm, tone_percentile), gamma_value))
    percentile_tone_preview = gamma_preview
    reinhard_preview = to_uint8(apply_gamma(reinhard_tone_map(rgb_ccm, tone_percentile), gamma_value))

    awb_preview = apply_rawpy_orientation(awb_preview, display_flip)
    ccm_preview = apply_rawpy_orientation(ccm_preview, display_flip)
    linear_display_preview = apply_rawpy_orientation(linear_display_preview, display_flip)
    gamma_preview = apply_rawpy_orientation(gamma_preview, display_flip)
    percentile_tone_preview = apply_rawpy_orientation(percentile_tone_preview, display_flip)
    reinhard_preview = apply_rawpy_orientation(reinhard_preview, display_flip)
    reference = reference_panel(raw_path, reference_dir, ccm_preview)

    ccm_compare = out_dir / f"{raw_path.stem}_ccm_compare.png"
    gamma_compare = out_dir / f"{raw_path.stem}_gamma_compare.png"
    tone_compare = out_dir / f"{raw_path.stem}_tone_mapping_compare.png"
    pipeline_compare = out_dir / f"{raw_path.stem}_week4_pipeline_compare.png"

    save_compare(
        ccm_compare,
        raw_path.name,
        [("After AWB", awb_preview), ("After CCM", ccm_preview), ("rawpy reference", reference)],
    )
    save_compare(
        gamma_compare,
        raw_path.name,
        [("Linear display", linear_display_preview), (f"Gamma 1/{gamma_value:.1f}", gamma_preview)],
    )
    save_compare(
        tone_compare,
        raw_path.name,
        [
            (f"Percentile {tone_percentile:g}% + gamma", percentile_tone_preview),
            ("Reinhard + gamma", reinhard_preview),
            ("rawpy reference", reference),
        ],
    )
    save_compare(
        pipeline_compare,
        raw_path.name,
        [
            ("AWB", awb_preview),
            ("CCM", ccm_preview),
            ("Tone + gamma", percentile_tone_preview),
            ("rawpy reference", reference),
        ],
    )

    result = {
        "file": str(raw_path),
        "sample_id": sample_id(raw_path),
        "bayer_pattern": bayer_pattern,
        "black_level_per_channel": black_levels,
        "white_level": white_level,
        "awb_gains": [float(v) for v in gains],
        "ccm": ccm.tolist(),
        "gamma": gamma_value,
        "tone_percentile": tone_percentile,
        "rgb_awb": describe_rgb(rgb_awb),
        "rgb_ccm": describe_rgb(rgb_ccm),
        "mean_awb_rgb": rgb_mean(rgb_awb),
        "mean_ccm_rgb": rgb_mean(rgb_ccm),
        "ccm_compare": str(ccm_compare),
        "gamma_compare": str(gamma_compare),
        "tone_compare": str(tone_compare),
        "pipeline_compare": str(pipeline_compare),
    }

    json_path = out_dir / f"{raw_path.stem}_week4_ccm_gamma_tone.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def fmt(value: float) -> str:
    return f"{value:.3f}"


def rel(path: str, report_path: Path) -> str:
    return Path(os.path.relpath(path, report_path.parent)).as_posix()


def write_ccm_report(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 4-1 CCM 学习报告",
        "",
        "CCM 的全称是 Color Correction Matrix，颜色校正矩阵。它接在 AWB 后面，用一个 `3x3` 矩阵把相机 RGB 映射到更接近目标颜色空间的 RGB。",
        "",
        "这一节要回答的核心问题是：为什么白平衡之后图像还需要颜色校正？为什么一个 `3x3` 矩阵就能改变颜色？",
        "",
        "## CCM 解决什么问题",
        "",
        "AWB 只是在 R/G/B 三个通道上乘增益，让灰色或白色更接近中性。它不能处理颜色之间的串扰关系。比如红色里混了多少绿色、蓝色应该被压多少、绿色是否偏黄，这些都需要通过矩阵混合来修正。",
        "",
        "相机传感器的 R/G/B 不是标准 sRGB 的 R/G/B。传感器的红色滤光片也会收到一部分绿光和蓝光，绿色滤光片也不是理想的纯绿色，所以相机 RGB 本质上是一个设备相关颜色空间。AWB 只能做：",
        "",
        "```text",
        "R_awb = R * gain_R",
        "G_awb = G * gain_G",
        "B_awb = B * gain_B",
        "```",
        "",
        "这一步能修白点，但不能把“传感器红”和“目标红”之间的形状差异修掉。CCM 做的是通道混合：新的 R 不只来自旧的 R，也可以混入旧的 G/B；新的 G/B 同理。",
        "",
        "## 数学形式",
        "",
        "对每个像素都有：",
        "",
        "```text",
        "[R']   [m00 m01 m02] [R]",
        "[G'] = [m10 m11 m12] [G]",
        "[B']   [m20 m21 m22] [B]",
        "```",
        "",
        "代码里对应的是：",
        "",
        "```python",
        "rgb_ccm = rgb_awb @ ccm.T",
        "rgb_ccm = clip(rgb_ccm, 0, white_level)",
        "```",
        "",
        "把第一行展开看，会更直观：",
        "",
        "```text",
        "R' = m00 * R + m01 * G + m02 * B",
        "G' = m10 * R + m11 * G + m12 * B",
        "B' = m20 * R + m21 * G + m22 * B",
        "```",
        "",
        "如果 `m01` 不是 0，就表示输出 R 会使用一部分输入 G；如果 `m12` 是负数，就表示输出 G 会压掉一部分输入 B。这就是 CCM 能修正色偏、色相和饱和度关系的原因。",
        "",
        "## 本周的计算过程",
        "",
        "本周的 CCM 输入不是 RAW Bayer，而是已经完成 Demosaic 和 AWB 的线性 RGB。流程是：",
        "",
        "```text",
        "RAW -> BLC -> DPC -> Demosaic -> AWB -> CCM",
        "```",
        "",
        "具体步骤：",
        "",
        "1. 用 Week3 的 bilinear demosaic 得到线性 RGB。",
        "2. 用 Gray World AWB 得到 `gain_R/gain_G/gain_B`，先把白点拉回中性。",
        "3. 读取 DNG/rawpy 暴露的 `color_matrix`，取前三列作为学习用 `3x3` CCM。",
        "4. 对每个像素做矩阵乘法 `rgb_awb @ ccm.T`。",
        "5. 把结果 clip 到 `0..white_level`，避免负数和超过白电平的值影响后续显示。",
        "",
        "本周为了学习闭环，先使用 DNG/rawpy 暴露的 `color_matrix` 前三列作为学习用 CCM。它能帮助理解矩阵校色流程，但还不是完整产品 ISP 里的色卡拟合和标定流程。",
        "",
        "产品 ISP 里更常见的做法是拍摄标准色卡，在已知光源下拿到多个色块的目标颜色，然后拟合一组矩阵，让相机输出尽量接近目标颜色。真实系统还会按色温准备多套 CCM，并在不同光源之间插值。",
        "",
        "## 结果总表",
        "",
        "| 样张 | R gain | G gain | B gain | AWB mean RGB | CCM mean RGB | 观察 |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for result in results:
        gains = result["awb_gains"]
        awb_mean = "/".join(fmt(v) for v in result["mean_awb_rgb"])
        ccm_mean = "/".join(fmt(v) for v in result["mean_ccm_rgb"])
        lines.append(
            f"| {result['sample_id']} | {fmt(gains[0])} | {fmt(gains[1])} | {fmt(gains[2])} | {awb_mean} | {ccm_mean} | CCM 改变颜色通道混合关系 |"
        )

    lines.extend(
        [
            "",
            "## 怎么看结果",
            "",
            "`AWB mean RGB` 和 `CCM mean RGB` 是整张图三个通道的平均值。它们不是判断颜色是否准确的唯一标准，但可以帮助观察 CCM 是否改变了通道混合关系。",
            "",
            "看对比图时建议关注三件事：",
            "",
            "1. 灰色或白色区域有没有继续保持中性。",
            "2. 红、绿、蓝、肤色、天空、植物这类典型颜色有没有发生色相变化。",
            "3. CCM 后是否出现明显过饱和、偏色或高光被 clip 的问题。",
            "",
            "## CCM 前后对比",
            "",
            "左边是 AWB 后，右边是 CCM 后，第三张是 rawpy 参考。重点看颜色倾向是否发生变化，不要求和 rawpy 完全一致。",
            "",
        ]
    )
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} CCM compare]({rel(result['ccm_compare'], report_path)})", ""])

    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. AWB 是三个通道的独立增益，CCM 是三个通道之间的线性混合。",
            "2. CCM 的输入仍然应该是线性 RGB，不应该先做 gamma。",
            "3. CCM 后可能出现负值或超过白电平的值，所以工程上要 clip 或配合后续 tone mapping。",
            "4. 真正产品中的 CCM 通常来自色卡标定，不是随便调一个看起来舒服的矩阵。",
            "5. 当前结果和 rawpy 不完全一致是正常的，因为 rawpy 还包含更完整的颜色空间转换、曲线、亮度处理和相机 profile 逻辑。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_gamma_report(results: list[dict], report_path: Path) -> None:
    gamma_value = results[0]["gamma"] if results else 2.2
    lines = [
        "# Week 4-2 Gamma 学习报告",
        "",
        "Gamma 是把线性 RGB 映射到更适合显示和人眼感知的非线性 RGB。线性图直接显示通常会显得偏暗，因为显示编码和人眼感知都不是简单的线性关系。",
        "",
        "这一节重点解释两个词：`linear display` 和 `gamma`。你看到的现象是：左边线性 RGB 直接显示更暗，右边加 gamma 后中间调和暗部被抬起来。这个现象是正常的，而且可以用数学直接解释。",
        "",
        "## 背景：什么是线性 RGB",
        "",
        "线性 RGB 的意思是：数值和真实光强成正比。假设一个像素的线性值是 `0.2`，另一个是 `0.4`，后者代表的光强大约是前者的两倍。",
        "",
        "线性空间对 ISP 算法很重要，因为很多物理计算都默认光是线性叠加的。例如 demosaic 插值、AWB 乘增益、CCM 矩阵乘法，都应该尽量在线性空间里完成。",
        "",
        "## 什么是 linear display",
        "",
        "报告图里的 `Linear display` 不是一个新的 ISP 算法，它只是为了对比，把线性 RGB 归一化到 `0..1` 后直接保存成图片：",
        "",
        "```text",
        "rgb_display = clip(rgb_linear / display_white, 0, 1)",
        "```",
        "",
        "问题在于，普通图片文件和普通显示链路通常默认输入已经是类似 sRGB/gamma 编码后的值。如果我们把线性值直接当成显示值，中间调会显得偏暗。",
        "",
        "举个数字例子：线性值 `0.25` 代表 25% 的物理光强。直接显示时它就是 0.25，看起来偏暗；做 gamma 后：",
        "",
        "```text",
        "0.25 ** (1 / 2.2) = 0.533",
        "```",
        "",
        "同一个线性中间调被编码成 0.533，所以视觉上明显变亮。线性值 `0.5` 也会变成：",
        "",
        "```text",
        "0.50 ** (1 / 2.2) = 0.730",
        "```",
        "",
        "这就是你看到“暗部和中间调被拉起来”的根本原因。",
        "",
        "## 数学形式",
        "",
        "本周使用最常见的简化 gamma：",
        "",
        "```text",
        "rgb_gamma = rgb_linear ** (1 / gamma)",
        f"gamma = {gamma_value}",
        "```",
        "",
        "如果输入已经归一化到 `0..1`，并且 `gamma > 1`，那么 `1/gamma < 1`。对 `0..1` 之间的数做小于 1 的幂，会让它变大：",
        "",
        "```text",
        "x = 0.10 -> x ** (1/2.2) = 0.351",
        "x = 0.25 -> x ** (1/2.2) = 0.533",
        "x = 0.50 -> x ** (1/2.2) = 0.730",
        "x = 1.00 -> x ** (1/2.2) = 1.000",
        "```",
        "",
        "所以 gamma 不是平均地把整张图加亮。越靠近黑色的中低亮度区域变化越明显，纯白 `1.0` 仍然是 `1.0`。",
        "",
        "## 本周的计算过程",
        "",
        "本周 gamma 的输入是 CCM 后的线性 RGB。流程是：",
        "",
        "```text",
        "rgb_ccm -> percentile normalize -> gamma encode -> uint8 preview",
        "```",
        "",
        "具体步骤：",
        "",
        "1. 先用 `99.5%` 分位点估计一个显示白点 `display_white`。",
        "2. 用 `rgb_ccm / display_white` 把图像归一化到大致 `0..1`。",
        "3. 对归一化结果做 `rgb ** (1/2.2)`。",
        "4. 乘 255 并转成 `uint8`，保存为可直接查看的 PNG。",
        "",
        "这里的 gamma 是简化版。严格的 sRGB OETF 在暗部有一段线性分段，不完全等于单纯 `1/2.2` 幂函数。本周先用简化公式，是为了看清楚非线性显示编码的核心作用。",
        "",
        "## Gamma 前后对比",
        "",
        "左边是线性 RGB 直接显示，右边是加 gamma 后。重点看中间调和暗部是不是被抬起来了。它们被抬起来不是因为曝光变了，而是同一批线性数值换了一种更适合显示的编码方式。",
        "",
    ]
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} gamma compare]({rel(result['gamma_compare'], report_path)})", ""])
    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. Gamma 不是白平衡，也不是颜色校正，它主要改变亮度编码方式。",
            "2. 大多数 ISP 算法应在线性空间里做，gamma 通常放在接近显示输出的位置。",
            "3. `1/2.2` 会抬高中间调，让线性图更适合普通显示器观看。",
            "4. Gamma 不等于 Tone Mapping。Gamma 主要解决显示编码和感知亮度，Tone Mapping 主要解决动态范围压缩。",
            "5. 看到 linear display 偏暗不是算法错了，而是线性数据还没有进入适合显示的编码状态。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_tone_report(results: list[dict], report_path: Path) -> None:
    percentile = results[0]["tone_percentile"] if results else 99.5
    lines = [
        "# Week 4-3 Tone Mapping 学习报告",
        "",
        "Tone Mapping 解决的是动态范围压缩问题。RAW/线性 RGB 里可能有很亮的高光，如果直接线性压到 `0..1`，暗部和中间调很容易被压得不好看。",
        "",
        "这一节要区分两个概念：归一化和 Tone Mapping。归一化只是选一个白点把数值缩到 `0..1`；Tone Mapping 是设计一条曲线，让暗部、中间调和高光以更合适的方式进入显示范围。",
        "",
        "## 背景：为什么需要动态范围压缩",
        "",
        "RAW 能记录的亮度范围通常比普通 `8-bit` 显示图更宽。线性 RGB 里可能同时有很暗的阴影和很亮的天空、高光、灯光。如果只用一个固定比例缩放，有两个常见问题：",
        "",
        "1. 为了保住高光，整体会被压暗，暗部和中间调不容易看清。",
        "2. 为了让主体正常，高光会很容易被 clip 成一片白，失去层次。",
        "",
        "Tone Mapping 的目标是在这两者之间折中：尽量让主体、中间调、暗部可读，同时让亮部不要过早死白。",
        "",
        "## 本周实现的两个简单版本",
        "",
        "第一种是 percentile clip：",
        "",
        "```text",
        f"display_white = percentile(rgb, {percentile})",
        "rgb_norm = clip(rgb / display_white, 0, 1)",
        "```",
        "",
        "这里的 `display_white` 不是相机传感器的 `white_level`，而是为了显示选择的白点。使用 `99.5%` 分位点的意思是：让最亮的 0.5% 像素允许被压到白色附近，避免极少数异常高光把整张图压暗。",
        "",
        "第二种是全局 Reinhard 曲线：",
        "",
        "```text",
        "rgb_tone = rgb_norm / (1 + rgb_norm)",
        "```",
        "",
        "Reinhard 的特点是输入越大，压缩越强。几个例子：",
        "",
        "```text",
        "0.25 -> 0.25 / 1.25 = 0.200",
        "1.00 -> 1.00 / 2.00 = 0.500",
        "4.00 -> 4.00 / 5.00 = 0.800",
        "```",
        "",
        "可以看到，大亮度值不会直接爆成无限大，而是逐渐接近 1。这就是它能更柔和压高光的原因。但代价是整体可能变灰、对比度下降，需要后续再配合对比度曲线或局部 tone mapping。",
        "",
        "这两个都不是最终产品级 tone mapping，但很适合作为第一版学习闭环。",
        "",
        "## 本周的计算过程",
        "",
        "本周 tone mapping 的输入是 CCM 后的线性 RGB。两条分支分别是：",
        "",
        "```text",
        "方案 A: rgb_ccm -> percentile normalize -> gamma -> preview",
        "方案 B: rgb_ccm -> percentile normalize -> Reinhard -> gamma -> preview",
        "```",
        "",
        "注意 gamma 放在 tone mapping 后面。原因是 tone mapping 的输入应尽量保持线性亮度关系；如果先做 gamma，曲线处理的就不是物理线性光强，后续亮度压缩会变得更难解释。",
        "",
        "## Tone Mapping 对比",
        "",
        "左边是 percentile clip + gamma，中间是 Reinhard + gamma，右边是 rawpy 参考。重点看亮部压缩和整体观感的差异。",
        "",
        "读图时建议这样看：",
        "",
        "1. 如果 percentile 版本更亮、更有冲击力，但亮部容易白掉，说明简单 clip 的高光保护不足。",
        "2. 如果 Reinhard 版本高光更柔和，但整体偏灰或偏暗，说明它压缩亮部的同时也牺牲了局部对比。",
        "3. rawpy reference 通常看起来更自然，因为它内部不只是一个全局 Reinhard，还可能包含相机 profile、曲线、色彩空间转换、曝光补偿和更复杂的高光处理。",
        "",
    ]
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} tone compare]({rel(result['tone_compare'], report_path)})", ""])
    lines.extend(
        [
            "## 今天要记住的结论",
            "",
            "1. Tone Mapping 负责把线性高动态范围压到显示范围。",
            "2. percentile clip 简单直接，但可能丢高光层次。",
            "3. Reinhard 曲线会更柔和地压亮部，但整体可能偏灰或偏暗。",
            "4. Gamma 和 Tone Mapping 经常一起出现在显示输出阶段，但它们解决的问题不同。",
            "5. 一个好的 tone curve 通常要同时考虑高光保护、中间调亮度、暗部可见性和整体对比度。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_summary(results: list[dict], report_path: Path) -> None:
    lines = [
        "# Week 4 总结：CCM / Gamma / Tone Mapping",
        "",
        "Week4 的目标是把 Week3 的 AWB 后 RGB 继续推向可显示图像。三个模块分开理解：CCM 负责颜色空间/颜色混合，Gamma 负责显示编码，Tone Mapping 负责动态范围压缩。",
        "",
        "如果只记一句话：Week3 得到的是“线性相机 RGB”，Week4 开始把它变成“更接近人眼和显示器能正常观看的图像”。",
        "",
        "## 本周流水线",
        "",
        "```text",
        "RAW -> BLC -> DPC -> Demosaic -> AWB -> CCM -> Tone Mapping -> Gamma -> Preview",
        "```",
        "",
        "## 分模块报告",
        "",
        "- [CCM 报告](ccm_report.md)",
        "- [Gamma 报告](gamma_report.md)",
        "- [Tone Mapping 报告](tone_mapping_report.md)",
        "",
        "## 核心概念速查",
        "",
        "| 名词 | 简单理解 | 本周位置 |",
        "|---|---|---|",
        "| 线性 RGB | 数值和真实光强近似成正比 | Demosaic/AWB/CCM 的工作空间 |",
        "| Linear display | 把线性 RGB 直接当显示图看 | 只用于对比，不是最终输出 |",
        "| CCM | 用 `3x3` 矩阵混合 R/G/B，修正相机颜色空间 | AWB 之后 |",
        "| Tone Mapping | 把高动态范围压进显示范围 | CCM 之后、Gamma 之前 |",
        "| Gamma | 把线性亮度编码成更适合显示和视觉感知的非线性值 | 接近最终输出 |",
        "",
        "## 为什么顺序是 CCM -> Tone Mapping -> Gamma",
        "",
        "CCM 需要在线性 RGB 上做矩阵乘法，因为颜色混合默认基于线性光强。Tone Mapping 也最好在线性亮度上做，这样压高光、保中间调的曲线含义更清楚。Gamma 放在最后，是因为它主要是显示编码，不应该提前破坏前面算法需要的线性关系。",
        "",
        "## 综合对比图",
        "",
        "这组图从左到右是 AWB、CCM、Tone+Gamma、rawpy reference，用来快速观察 Week4 之后整体显示效果的变化。",
        "",
    ]
    for result in results:
        lines.extend([f"### {result['sample_id']}", "", f"![{result['sample_id']} Week4 pipeline compare]({rel(result['pipeline_compare'], report_path)})", ""])
    lines.extend(
        [
            "## Week4 学习结论",
            "",
            "1. Demosaic 之后只是有了 RGB 结构，还不是最终显示图。",
            "2. AWB 让白点接近中性，CCM 进一步修正颜色关系。",
            "3. Gamma 会显著影响中间调亮度，所以不能把它和曝光、AWB 混在一起理解。",
            "4. Tone Mapping 是显示输出前非常关键的一步，决定亮部和暗部如何压缩。",
            "5. linear display 偏暗通常不是错，而是线性数据还没经过显示编码。",
            "6. 当前 Week4 是学习版闭环，目标是理解模块作用；产品级 ISP 还会加入色卡标定、sRGB OETF、局部 tone mapping、对比度曲线和更复杂的高光恢复。",
            "",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Week4 CCM, gamma, tone mapping and write separate reports.")
    parser.add_argument("raw_paths", type=Path, nargs="+", help="One or more RAW/DNG files.")
    parser.add_argument("--out-dir", type=Path, default=Path("reports/figures"))
    parser.add_argument("--reference-dir", type=Path, default=Path("data/references"))
    parser.add_argument("--report-dir", type=Path, default=Path("reports/week4"))
    parser.add_argument("--min-delta", type=int, default=1024)
    parser.add_argument("--mad-k", type=float, default=12.0)
    parser.add_argument("--gamma", type=float, default=2.2)
    parser.add_argument("--tone-percentile", type=float, default=99.5)
    args = parser.parse_intermixed_args()

    results = [
        analyze_one(raw_path, args.out_dir, args.reference_dir, args.min_delta, args.mad_k, args.gamma, args.tone_percentile)
        for raw_path in args.raw_paths
    ]
    write_ccm_report(results, args.report_dir / "ccm_report.md")
    write_gamma_report(results, args.report_dir / "gamma_report.md")
    write_tone_report(results, args.report_dir / "tone_mapping_report.md")
    write_summary(results, args.report_dir / "summary.md")
    print(args.report_dir)


if __name__ == "__main__":
    main()
