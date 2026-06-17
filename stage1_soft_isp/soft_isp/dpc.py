"""坏点校正（Defect Pixel Correction, DPC）模块。

DPC 在 BLC 之后执行，检测并修复 Bayer RAW 中的孤立异常像素。
由于 Bayer 传感器相邻像素颜色不同，检测必须在同色通道上进行。

算法流程：
    1. 按 Bayer 模式将图像拆分为 R/Gr/Gb/B 四个同色平面
    2. 在每个平面上做 3x3 中值检测，使用 MAD（中位数绝对偏差）建立稳健阈值
    3. 将异常像素替换为其同色邻域中值

本模块提供六个函数：
    - _median3x3:              计算 3x3 局部中值（内部工具函数）
    - detect_channel_defects:  在单个同色平面上检测异常点
    - detect_defects:          按 Bayer 通道批量检测
    - repair_defects:          用中值替换检测到的坏点
    - merge_channel_masks:     将逐通道 mask 合并回全分辨率 Bayer 坐标
"""

from __future__ import annotations

import numpy as np

from soft_isp.stats import split_bayer


def _median3x3(channel: np.ndarray) -> np.ndarray:
    """计算单个同色通道的 3x3 局部中值。

    使用 edge padding 处理边界，提取 9 个邻域位置后沿 axis=0 取中值。

    参数:
        channel: 单个 Bayer 通道的二维数组（如 R 通道，shape 为 H/2 x W/2）

    返回:
        与输入同尺寸的局部中值数组
    """
    padded = np.pad(channel, 1, mode="edge")
    neighbors = [
        padded[0:-2, 0:-2],
        padded[0:-2, 1:-1],
        padded[0:-2, 2:],
        padded[1:-1, 0:-2],
        padded[1:-1, 1:-1],
        padded[1:-1, 2:],
        padded[2:, 0:-2],
        padded[2:, 1:-1],
        padded[2:, 2:],
    ]
    return np.median(np.stack(neighbors, axis=0), axis=0)


def detect_channel_defects(
    channel: np.ndarray,
    min_delta: int = 256,
    mad_k: float = 12.0,
) -> tuple[np.ndarray, np.ndarray, float]:
    """在单个同色 Bayer 通道中检测脉冲状异常点。

    使用 MAD（Median Absolute Deviation）建立稳健的异常检测阈值：
        threshold = max(min_delta, residual_median + mad_k * MAD(residual))
    其中 residual = |pixel - local_median|

    MAD 比标准差更稳健，不容易被少数极端值带偏。

    参数:
        channel:   单个 Bayer 通道的二维数组
        min_delta: 最小检测阈值（防止在平坦区域过度标记）
        mad_k:     MAD 倍数系数，越大越保守

    返回:
        (mask, local_median, threshold): 异常点布尔 mask、局部中值、所用阈值
    """
    channel_i32 = channel.astype(np.int32)
    local_median = _median3x3(channel_i32).astype(np.int32)
    residual = np.abs(channel_i32 - local_median)

    residual_median = float(np.median(residual))
    mad = float(np.median(np.abs(residual - residual_median)))
    robust_threshold = residual_median + mad_k * max(mad, 1.0)
    threshold = max(float(min_delta), robust_threshold)

    mask = residual > threshold
    return mask, local_median, threshold


def detect_defects(
    raw_blc: np.ndarray,
    bayer_pattern: str,
    min_delta: int = 256,
    mad_k: float = 12.0,
) -> dict:
    """按 Bayer 通道批量检测坏点候选。

    先将 BLC 后的完整 Bayer 图像拆分为 R/Gr/Gb/B 四个通道，
    再对每个通道独立调用 detect_channel_defects。

    参数:
        raw_blc:       BLC 校正后的 Bayer RAW 图像
        bayer_pattern: Bayer 排列模式（"RGGB"/"BGGR"/"GRBG"/"GBRG"）
        min_delta:     最小检测阈值
        mad_k:         MAD 倍数系数

    返回:
        {"masks": {通道名: 布尔mask}, "local_medians": {通道名: 中值}, "thresholds": {通道名: 阈值}}
    """
    channels = split_bayer(raw_blc, bayer_pattern)
    masks = {}
    medians = {}
    thresholds = {}

    for name, channel in channels.items():
        mask, local_median, threshold = detect_channel_defects(channel, min_delta=min_delta, mad_k=mad_k)
        masks[name] = mask
        medians[name] = local_median
        thresholds[name] = threshold

    return {
        "masks": masks,
        "local_medians": medians,
        "thresholds": thresholds,
    }


def repair_defects(raw_blc: np.ndarray, bayer_pattern: str, detection: dict) -> np.ndarray:
    """用同色局部中值替换检测到的坏点候选。

    遍历每个 Bayer 通道，将 mask 标记为 True 的像素替换为 detect_defects 计算的中值。
    修复后的值 clip 到像素数据类型的有效范围。

    参数:
        raw_blc:       BLC 校正后的 Bayer RAW 图像
        bayer_pattern: Bayer 排列模式
        detection:     detect_defects 的返回结果

    返回:
        修复后的 uint16 图像（坏点位置已被替换）
    """
    repaired = raw_blc.copy()
    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }[bayer_pattern.upper()]

    for name, (y_offset, x_offset) in positions.items():
        channel_view = repaired[y_offset::2, x_offset::2]
        mask = detection["masks"][name]
        median = detection["local_medians"][name]
        channel_view[mask] = np.clip(median[mask], 0, np.iinfo(repaired.dtype).max).astype(repaired.dtype)

    return repaired


def merge_channel_masks(raw_shape: tuple[int, int], bayer_pattern: str, masks: dict[str, np.ndarray]) -> np.ndarray:
    """将逐通道 mask 合并回全分辨率 Bayer 坐标。

    参数:
        raw_shape:     (H, W) 全分辨率 Bayer 图像形状
        bayer_pattern: Bayer 排列模式
        masks:         逐通道的布尔 mask 字典 {"R": mask, "Gr": mask, ...}

    返回:
        全分辨率 (H, W) 的布尔 mask，每个 Bayer 像素位置标记是否为坏点
    """
    full_mask = np.zeros(raw_shape, dtype=bool)
    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }[bayer_pattern.upper()]

    for name, (y_offset, x_offset) in positions.items():
        full_mask[y_offset::2, x_offset::2] = masks[name]
    return full_mask
