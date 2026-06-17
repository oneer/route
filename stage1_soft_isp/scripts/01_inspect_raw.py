"""RAW/DNG 文件检查工具 —— 打印元数据与 Bayer 通道统计信息。

用法:
    python 01_inspect_raw.py <raw_path> [--pattern RGGB]

输出为 JSON 格式，包含：
    - raw: 整幅 raw 图像的统计描述（shape, dtype, min/max/mean/std 等）
    - black_level_per_channel: 每个通道的黑电平
    - camera_white_level_per_channel: 每个通道的相机白电平
    - white_level: 全局白电平
    - color_desc: 色彩描述字符串（如 "RGBG"）
    - raw_pattern: Bayer 模式矩阵
    - bayer_pattern: 从 metadata 推断出的常见 Bayer 字符串
    - channels: 按 Bayer 通道拆分后的逐通道统计描述
"""

from __future__ import annotations  # PEP 604: 允许在类型注解中使用管道语法（如 `Path | None`）

import argparse  # 命令行参数解析
import json     # JSON 序列化输出
import sys      # 系统路径操作，用于将项目根目录加入 import 路径
from pathlib import Path  # 面向对象的文件路径处理

import rawpy   # libraw 的 Python 绑定，用于读取 RAW/DNG 文件的原始数据

# 将项目根目录（scripts/ 的父目录）加入 sys.path，以便导入 soft_isp 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# bayer_pattern_from_rawpy: 根据 rawpy 的 raw_pattern/color_desc 推断 RGGB/BGGR 等 Bayer 字符串
# describe_array: 计算 numpy 数组的统计描述（shape, dtype, min, max, mean, std, percentile 等）
# split_bayer:  将 Bayer 格式的 raw 图像按颜色通道拆分为独立的子数组（如 R, G1, G2, B）
from soft_isp.stats import bayer_pattern_from_rawpy, describe_array, split_bayer


def main() -> None:
    """解析命令行参数，读取 RAW 文件，输出元数据与通道统计的 JSON 到 stdout。"""

    # ---- 命令行参数定义 ----
    parser = argparse.ArgumentParser(
        description="Inspect RAW/DNG metadata and basic Bayer statistics."
    )
    parser.add_argument(
        "raw_path", type=Path,
        help="Path to a RAW/DNG file.",
    )
    parser.add_argument(
        "--pattern", default=None,
        help="Override Bayer pattern used for channel statistics. Defaults to metadata.",
    )
    args = parser.parse_args()

    # ---- 读取 RAW 文件 ----
    # rawpy.imread() 返回一个 RawPy 对象，使用 with 语句确保资源自动释放
    with rawpy.imread(str(args.raw_path)) as raw:
        # raw_image_visible 是去除光学黑边（optical black）后的有效像素区域
        # .copy() 确保后续操作不会影响 raw 对象内部的缓冲区
        raw_visible = raw.raw_image_visible.copy()
        color_desc = raw.color_desc.decode(errors="replace")
        bayer_pattern = args.pattern or bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)

        # ---- 组装输出字典 ----
        result: dict = {
            # 原始文件路径，方便识别输出属于哪个文件
            "file": str(args.raw_path),

            # 整幅 raw 图像的全局统计信息（包含所有 Bayer 像素混在一起的总览）
            "raw": describe_array(raw_visible),

            # 每个通道的黑电平（black level），即传感器的暗电流偏移量
            # 原始信号减去黑电平才是真正的光信号
            "black_level_per_channel": list(raw.black_level_per_channel),

            # 每个通道的相机白电平：传感器饱和前的最大像素值（可能因通道而异）
            # 若相机未提供此值则为空列表
            "camera_white_level_per_channel": list(raw.camera_white_level_per_channel or []),

            # 全局白电平：统一的最大像素值，超出此值的像素被视为过曝/饱和
            "white_level": raw.white_level,

            # 色彩描述字符串，如 "RGBG" / "RGBG" 等
            # libraw 返回 bytes，decode 转为 str；errors="replace" 防止非 UTF-8 字节导致崩溃
            "color_desc": color_desc,

            # Bayer 模式矩阵，描述传感器上每个像素位置对应的颜色通道排列
            # 例如 RGGB 模式对应 [[0, 1], [1, 2]]（R=0, G1=1, G2=1, B=2）
            "raw_pattern": raw.raw_pattern.tolist(),

            # 常见 Bayer 字符串，后续拆通道和报告记录都以这个字段为准
            "bayer_pattern": bayer_pattern,

            # 按 Bayer 通道拆分后，每个通道（R, G1, G2, B）各自的统计描述
            # split_bayer 返回 {"R": np.ndarray, "G1": np.ndarray, "G2": np.ndarray, "B": np.ndarray}
            # 对每个通道分别调用 describe_array 得到分布的统计信息
            "channels": {
                name: describe_array(channel)
                for name, channel in split_bayer(raw_visible, bayer_pattern).items()
            },
        }

    # ---- 输出 ----
    # ensure_ascii=False 保留非 ASCII 字符（如中文文件名）
    # indent=2 生成可读的缩进 JSON
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
