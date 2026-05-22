"""RAW 转 sRGB 基准图像生成器 —— 用 rawpy 默认管线将 DNG 转换为人眼可看的 PNG。

用法:
    python 02_generate_rawpy_references.py [--raw-dir data/raw] [--out-dir data/references]

用途:
    rawpy 内置了完整的 ISP 管线（demosaic / 白平衡 / gamma / 色彩空间转换等）。
    这个脚本用 rawpy 的默认参数生成 sRGB PNG，作为后续自定义 ISP 实现的"参考答案"。
    对比自己 ISP 的输出与 rawpy 的输出，可以快速发现管线中的 bug 和偏差。

参数:
    --raw-dir:   存放 DNG 文件的目录，按文件名排序后逐个处理
    --out-dir:   输出的 sRGB PNG 存放目录，文件名格式为 <原文件名>_rawpy_srgb.png
"""

from __future__ import annotations  # PEP 604: 允许在类型注解中使用管道语法

import argparse  # 命令行参数解析
from pathlib import Path  # 面向对象的文件路径处理

import imageio.v3 as iio  # 图片 I/O 库，用于写出 PNG 等通用图像格式
import rawpy               # libraw 的 Python 绑定，用于读取 RAW/DNG 文件


def main() -> None:
    """遍历 raw-dir 中的 DNG 文件，用 rawpy 默认管线生成 sRGB PNG。"""

    # ---- 命令行参数 ----
    parser = argparse.ArgumentParser(
        description="Generate rawpy sRGB reference outputs for DNG files."
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=Path("data/raw"),
        help="Directory containing DNG files to process.",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=Path("data/references"),
        help="Directory to save output sRGB PNG files.",
    )
    args = parser.parse_args()

    # ---- 创建输出目录 ----
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # ---- 遍历所有 DNG 文件 ----
    # sorted() 确保处理顺序可复现
    for raw_path in sorted(args.raw_dir.glob("*.dng")):
        out_path = args.out_dir / f"{raw_path.stem}_rawpy_srgb.png"

        # 用 rawpy 读取 RAW 文件
        with rawpy.imread(str(raw_path)) as raw:
            # postprocess 是 rawpy 的一键处理函数，内部执行完整的 ISP 管线：
            #   1. 黑电平减法
            #   2. 白平衡校正（use_camera_wb=True 使用相机拍摄时的白平衡）
            #   3. demosaic（去马赛克）
            #   4. 色彩空间转换
            #   5. gamma 校正
            #   6. 量化到 8-bit
            # output_bps=8 表示输出为 uint8 的 RGB 图像（0~255）
            rgb = raw.postprocess(use_camera_wb=True, output_bps=8)

        # 将 numpy 数组写入 PNG 文件
        iio.imwrite(out_path, rgb)
        print(out_path)  # 输出路径到 stdout，便于确认进度


if __name__ == "__main__":
    main()

