"""黑电平校正（Black Level Correction, BLC）模块。

BLC 是 ISP 管线的第一步，功能是从 RAW 数据中减去传感器的暗电流偏置。
传感器即使在没有光照的情况下也会产生非零信号（暗电流），这个偏置称为 black level。
必须先扣除 black level 才能让后续算法在真实光信号上工作。

本模块提供三个函数：
    - make_black_level_map:   构建逐像素的黑电平偏移图
    - apply_blc:              执行黑电平减法并 clip 到有效范围
    - normalized_after_blc:   返回 0~1 归一化后的 BLC 结果
"""

from __future__ import annotations

import numpy as np


def make_black_level_map(raw_shape: tuple[int, int], raw_pattern: np.ndarray, black_levels: list[int]) -> np.ndarray:
    """根据 rawpy 元数据构建逐像素的黑电平偏移图。

    参数:
        raw_shape:     RAW 图像形状 (H, W)
        raw_pattern:   rawpy 的 raw_pattern 属性，shape 为 (2, 2)
        black_levels:  各颜色通道的黑电平列表，索引对应 raw_pattern 中的数字

    返回:
        与 raw_shape 同尺寸的 int32 数组，每个像素位置为对应的黑电平值
        通过将 black_levels 按 raw_pattern 组装成 2x2 tile，再平铺到全图尺寸
    """
    pattern = np.asarray(raw_pattern)
    if pattern.shape != (2, 2):
        raise ValueError(f"Unsupported raw_pattern shape: {pattern.shape}")

    black_levels_array = np.asarray(black_levels, dtype=np.int32)
    if black_levels_array.size <= int(pattern.max()):
        raise ValueError("black_levels does not cover all entries in raw_pattern")

    black_tile = black_levels_array[pattern]
    tile_rows = (raw_shape[0] + 1) // 2
    tile_cols = (raw_shape[1] + 1) // 2
    return np.tile(black_tile, (tile_rows, tile_cols))[: raw_shape[0], : raw_shape[1]]


def apply_blc(
    raw_visible: np.ndarray,
    raw_pattern: np.ndarray,
    black_levels: list[int],
    white_level: int,
) -> np.ndarray:
    """按 Bayer 位置扣除黑电平并 clip 到有效信号范围。

    BLC 的核心公式：
        corrected = clip(raw - black_level, 0, white_level - black_level)

    参数:
        raw_visible: 去除光学黑边后的有效像素区域
        raw_pattern:  rawpy 的 raw_pattern，用于按 Bayer 位置分配黑电平
        black_levels: 各通道黑电平列表
        white_level:  传感器饱和白电平

    返回:
        BLC 校正后的 uint16 数组，形状与 raw_visible 相同
    """
    black_map = make_black_level_map(raw_visible.shape, raw_pattern, black_levels)
    corrected = raw_visible.astype(np.int32) - black_map
    corrected_white_map = np.maximum(int(white_level) - black_map, 0)
    corrected = np.minimum(np.maximum(corrected, 0), corrected_white_map)
    return corrected.astype(np.uint16)


def normalized_after_blc(
    raw_visible: np.ndarray,
    raw_pattern: np.ndarray,
    black_levels: list[int],
    white_level: int,
) -> np.ndarray:
    """返回 BLC 校正后归一化到 0~1 的 float32 结果。

    与 apply_blc 的区别：返回值为浮点且归一化，适合后续数学运算和显示。
    归一化公式：corrected / (white_level - black_level_per_pixel)

    参数:
        raw_visible, raw_pattern, black_levels, white_level: 同 apply_blc

    返回:
        0~1 范围的 float32 数组
    """
    corrected = apply_blc(raw_visible, raw_pattern, black_levels, white_level)
    black_map = make_black_level_map(raw_visible.shape, raw_pattern, black_levels)
    corrected_white_map = np.maximum(float(white_level) - black_map.astype(np.float32), 1.0)
    return corrected.astype(np.float32) / corrected_white_map
