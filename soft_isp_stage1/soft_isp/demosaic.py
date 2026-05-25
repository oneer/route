"""去马赛克（Demosaic）模块。

Demosaic 是 ISP 管线中将单通道 Bayer RAW 转换为三通道 RGB 的关键步骤。
Bayer 传感器的每个像素只记录一种颜色（R/G/B），Demosaic 的任务是在每个像素位置
估计缺失的另外两个颜色通道。

本模块实现的是最基础的 bilinear（双线性）插值方案：
    - 对 R/G/B 分别构建已知像素 mask
    - 用 3x3 加权卷积核做局部插值
    - 除以有效权重和保证正确归一化
    - 保留真实采样位置的原始值不被插值覆盖

函数列表：
    - bayer_positions:     根据 Bayer 模式返回各通道在 2x2 块中的坐标
    - _known_mask:          生成标记已知像素位置的二值 mask
    - _interpolate_channel: 对单个通道做加权插值
    - bilinear_demosaic:    主函数，单通道 Bayer → 三通道线性 RGB
    - rgb_preview:          将线性 RGB 映射为 8-bit 显示预览（gamma 编码）
"""

from __future__ import annotations

import cv2
import numpy as np


def bayer_positions(pattern: str) -> dict[str, tuple[int, int]]:
    """根据 Bayer 模式返回各通道在 2x2 块中的坐标。

    参数:
        pattern: Bayer 排列模式，支持 "RGGB"/"BGGR"/"GRBG"/"GBRG"（不区分大小写）
                注意 G1 和 G2 分别表示两个绿色采样位置（物理位置不同但同属绿通道）

    返回:
        {"R": (y, x), "G1": (y, x), "G2": (y, x), "B": (y, x)}

    异常:
        ValueError: 不支持的 Bayer 模式
    """
    pattern = pattern.upper()
    positions = {
        "RGGB": {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "G1": (0, 1), "G2": (1, 0), "R": (1, 1)},
        "GRBG": {"G1": (0, 0), "R": (0, 1), "B": (1, 0), "G2": (1, 1)},
        "GBRG": {"G1": (0, 0), "B": (0, 1), "R": (1, 0), "G2": (1, 1)},
    }
    if pattern not in positions:
        raise ValueError(f"Unsupported Bayer pattern: {pattern}")
    return positions[pattern]


def _known_mask(shape: tuple[int, int], offsets: list[tuple[int, int]]) -> np.ndarray:
    """生成标记已知像素位置的二值 float32 mask。

    参数:
        shape:   图像形状 (H, W)
        offsets: 已知像素在 2x2 块中的位置列表，如 [(0,0)] 表示只有左上角

    返回:
        形状为 (H, W) 的 float32 数组，已知位置为 1.0，其余为 0.0
    """
    mask = np.zeros(shape, dtype=np.float32)
    for y_offset, x_offset in offsets:
        mask[y_offset::2, x_offset::2] = 1.0
    return mask


def _interpolate_channel(raw: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """对单个颜色通道做加权双线性插值。

    核心公式：
        weighted_sum = conv(raw * mask, kernel)
        weight_sum   = conv(mask, kernel)
        result       = weighted_sum / weight_sum

    除以 weight_sum 是为了处理边界位置（邻域内同色采样点数量不同），
    确保每个位置的插值结果都是正确的局部加权平均。
    最后将已知采样位置还原为原始值（已知值比插值估计更可信）。

    参数:
        raw:  完整的 Bayer RAW 图像
        mask: 该通道已知像素的 float32 mask

    返回:
        插值后的 float32 数组，已知位置保留原值
    """
    raw_f32 = np.asarray(raw, dtype=np.float32)
    kernel = np.array(
        [
            [1.0, 2.0, 1.0],
            [2.0, 4.0, 2.0],
            [1.0, 2.0, 1.0],
        ],
        dtype=np.float32,
    )
    weighted_sum = cv2.filter2D(raw_f32 * mask, -1, kernel, borderType=cv2.BORDER_REFLECT_101)
    weight = cv2.filter2D(mask, -1, kernel, borderType=cv2.BORDER_REFLECT_101)
    interpolated = weighted_sum / np.maximum(weight, 1e-6)
    interpolated[mask > 0] = raw_f32[mask > 0]
    return interpolated


def bilinear_demosaic(raw_bayer: np.ndarray, bayer_pattern: str) -> np.ndarray:
    """将单通道 Bayer RAW 图像转换为线性 RGB float32 图像。

    步骤：
        1. 根据 bayer_pattern 确定 R/G/B 在 2x2 块中的位置
        2. 对 G 通道合并两个 Bayer 位置（G1, G2）的 mask
        3. 分别对 R/G/B 做双线性插值
        4. stack 成 (H, W, 3) 的 RGB 数组

    参数:
        raw_bayer:     二维 uint16 Bayer RAW 图像
        bayer_pattern: Bayer 排列模式（"RGGB"/"BGGR"/"GRBG"/"GBRG"）

    返回:
        (H, W, 3) 形状的 float32 线性 RGB 图像

    异常:
        ValueError: raw_bayer 不是二维数组
    """
    positions = bayer_positions(bayer_pattern)
    raw = np.asarray(raw_bayer)
    if raw.ndim != 2:
        raise ValueError(f"raw_bayer must be 2D, got shape {raw.shape}")

    r_mask = _known_mask(raw.shape, [positions["R"]])
    g_mask = _known_mask(raw.shape, [positions["G1"], positions["G2"]])
    b_mask = _known_mask(raw.shape, [positions["B"]])

    rgb = np.stack(
        [
            _interpolate_channel(raw, r_mask),
            _interpolate_channel(raw, g_mask),
            _interpolate_channel(raw, b_mask),
        ],
        axis=-1,
    )
    return rgb.astype(np.float32)


def rgb_preview(
    rgb_linear: np.ndarray,
    black: float = 0.0,
    white: float | None = None,
    gamma: float = 2.2,
) -> np.ndarray:
    """将线性 RGB 数据映射为 8-bit 显示预览。

    处理流程：减去黑点 → 归一化（除以白点）→ clip → gamma 编码 → 量化到 uint8。

    参数:
        rgb_linear: (H, W, 3) 的线性 RGB 图像
        black:      黑点偏移量
        white:      白点值，None 时自动取 p99.5
        gamma:      显示 gamma 值，默认 2.2

    返回:
        uint8 RGB 预览图像（0~255）
    """
    rgb = rgb_linear.astype(np.float32) - float(black)
    if white is None:
        white = float(np.percentile(rgb, 99.5))
    white = max(float(white), 1.0)
    preview = np.clip(rgb / white, 0.0, 1.0)
    if gamma > 0:
        preview = np.power(preview, 1.0 / gamma)
    return (preview * 255.0 + 0.5).astype(np.uint8)
