"""RAW/DNG 直方图绘制工具 —— 生成 raw 整体与 Bayer 四通道的灰度分布图。

用法:
    python 04_plot_raw_histogram.py <raw_path>... [--out-dir reports/figures] [--bins 512]

输出为 PNG 格式的双栏直方图：
    - 上图：所有 Bayer 像素合在一起的全局直方图（带黑/白电平标线）
    - 下图：按 R / Gr / Gb / B 四通道分开的 step 直方图（叠加显示）
"""

from __future__ import annotations  # PEP 604: 允许在类型注解中使用管道语法（如 `Path | None`）

import argparse  # 命令行参数解析
import sys      # 系统路径操作，用于将项目根目录加入 import 路径
from pathlib import Path  # 面向对象的文件路径处理

import matplotlib

# 设置 Matplotlib 后端为无 GUI 的 "Agg"，这样在无显示器环境（如服务器、CI）也能正常输出图片
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # Matplotlib 的 pyplot 接口，用于绘图
import numpy as np               # 数值计算库
import rawpy                     # libraw 的 Python 绑定，用于读取 RAW/DNG 文件的原始数据

# 将项目根目录（scripts/ 的父目录）加入 sys.path，以便导入 soft_isp 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# bayer_pattern_from_rawpy: 根据 rawpy 的 raw_pattern/color_desc 推断 RGGB/BGGR 等 Bayer 字符串
# split_bayer:  将 Bayer 格式的 raw 图像按颜色通道拆分为独立的子数组
from soft_isp.stats import bayer_pattern_from_rawpy, split_bayer


# 四个 Bayer 通道对应的绘图颜色，取自 Tableau 10 调色板
CHANNEL_COLORS = {
    "R": "#d62728",   # 红色通道 —— 红
    "Gr": "#2ca02c",  # 绿色通道（与 R 同行）—— 深绿
    "Gb": "#1f9d55",  # 绿色通道（与 B 同行）—— 浅绿，与 Gr 区分
    "B": "#1f77b4",   # 蓝色通道 —— 蓝
}


def plot_histogram(raw_path: Path, out_dir: Path, bins: int) -> Path:
    """为单个 RAW 文件生成直方图并保存为 PNG，返回输出文件路径。"""

    # ---- 读取 RAW 数据 ----
    # rawpy.imread() 返回 RawPy 对象，with 语句确保资源自动释放
    with rawpy.imread(str(raw_path)) as raw:
        # raw_image_visible 是去除光学黑边后的有效像素区域，类型为 uint16
        # .copy() 避免后续操作影响 raw 对象的内部缓冲区
        raw_visible = raw.raw_image_visible.copy()

        # color_desc 是色彩描述字符串（如 "RGBG"），来自 libraw 的元数据
        # 原始值为 bytes，decode 转为 str；errors="replace" 防止非 UTF-8 字节导致崩溃
        color_desc = raw.color_desc.decode(errors="replace")

        # 根据 raw_pattern 和 color_desc 推断标准 Bayer 排列字符串（如 "RGGB"）
        bayer_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)

        # 按 Bayer 模式将 raw_visible 拆分为四个通道：
        #   {"R": ndarray, "Gr": ndarray, "Gb": ndarray, "B": ndarray}
        # 每个通道的像素数约为全图的 1/4
        channels = split_bayer(raw_visible, bayer_pattern)

        # 各通道的黑电平（暗电流偏移），通常是 4 个值对应 R/G1/G2/B
        # 可能有多通道共享同一值的情况，绘图前用 set 去重
        black_levels = list(raw.black_level_per_channel)

        # 白电平（饱和阈值）：超出此值的像素被视为过曝/clipped
        white_level = raw.white_level

    # ---- 创建输出目录 ----
    out_dir.mkdir(parents=True, exist_ok=True)

    # 输出文件名格式：<原文件名>_histogram.png
    out_path = out_dir / f"{raw_path.stem}_histogram.png"

    # ---- 创建图形 ----
    # 2 行 1 列的子图布局，constrained_layout=True 自动调整间距避免重叠
    fig, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    fig.suptitle(f"{raw_path.name} RAW histogram ({bayer_pattern})")

    # ========== 上图：全局直方图（所有 Bayer 像素混在一起） ==========
    # ravel() 将二维数组展平为一维，bins 控制直方图柱数
    # log=True 使 y 轴对数缩放，因为暗部像素数量远大于亮部
    axes[0].hist(raw_visible.ravel(), bins=bins, color="#444444", log=True)

    # 标出白电平线（红色虚线）—— 过曝分界线
    axes[0].axvline(white_level, color="#d62728", linestyle="--", linewidth=1.2, label="white level")

    # 标出黑电平线（黑色点线）—— 去重后为每个不同的 black level 画一条
    for black_level in sorted(set(black_levels)):
        axes[0].axvline(black_level, color="#222222", linestyle=":", linewidth=1.0,
                        label=f"black level {black_level}")

    axes[0].set_title("All Bayer samples")
    axes[0].set_xlabel("RAW value")
    axes[0].set_ylabel("Pixel count (log)")
    axes[0].legend()
    axes[0].grid(alpha=0.25)  # 半透明网格线

    # ========== 下图：分通道直方图（R / Gr / Gb / B 叠加显示） ==========
    # histtype="step" 只画轮廓线而不填充，避免多个通道互相遮挡
    for name in ("R", "Gr", "Gb", "B"):
        axes[1].hist(
            channels[name].ravel(),
            bins=bins,
            histtype="step",       # 只画轮廓
            linewidth=1.2,         # 线宽
            color=CHANNEL_COLORS[name],  # 每通道用不同颜色区分
            label=name,
            log=True,              # y 轴对数缩放
        )

    # 在白电平处也标注一条垂直线，用于判断各通道是否过曝
    axes[1].axvline(white_level, color="#d62728", linestyle="--", linewidth=1.2, label="white level")

    axes[1].set_title("Bayer channel samples")
    axes[1].set_xlabel("RAW value")
    axes[1].set_ylabel("Pixel count (log)")
    axes[1].legend()
    axes[1].grid(alpha=0.25)

    # ---- 保存并清理 ----
    # dpi=150 在清晰度与文件大小之间取平衡
    fig.savefig(out_path, dpi=150)
    plt.close(fig)  # 显式关闭图形，释放内存，避免大量循环时内存泄漏
    return out_path


def main() -> None:
    """解析命令行参数，对每个 RAW 文件调用 plot_histogram。"""

    parser = argparse.ArgumentParser(
        description="Plot RAW and Bayer-channel histograms for DNG files."
    )
    parser.add_argument(
        "raw_paths", type=Path, nargs="+",
        help="One or more RAW/DNG files.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("reports/figures"),
        help="Directory to save histogram PNGs.",
    )
    parser.add_argument(
        "--bins", type=int, default=512,
        help="Number of histogram bins.",
    )
    args = parser.parse_args()

    # 遍历所有输入的 RAW 文件，逐个生成直方图
    for raw_path in args.raw_paths:
        out_path = plot_histogram(raw_path, args.out_dir, args.bins)
        print(out_path)  # 输出保存路径到 stdout，便于脚本调用者确认


if __name__ == "__main__":
    main()
