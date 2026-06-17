"""显示方向处理模块。

相机在拍摄时可能旋转机身（竖拍/倒拍），这些方向信息记录在 RAW 元数据中。
本模块提供工具函数来应用这些旋转/翻转变换，使预览图与拍摄时的取景方向一致。

LibRaw 用 flip 整数值（0~7）编码 8 种可能的显示方向，对应不同的旋转/镜像组合。

函数列表：
    - apply_rawpy_orientation:       对图像数组应用显示方向变换
    - transform_box_for_orientation: 将边界框坐标变换到显示方向坐标系
"""

from __future__ import annotations

import numpy as np


def apply_rawpy_orientation(image: np.ndarray, flip: int) -> np.ndarray:
    """Apply LibRaw/rawpy display orientation to an image array."""
    if flip == 0:
        return image
    if flip == 1:
        return np.fliplr(image)
    if flip == 2:
        return np.flipud(image)
    if flip == 3:
        return np.rot90(image, 2)
    if flip == 4:
        return np.transpose(image, (1, 0, 2)) if image.ndim == 3 else np.transpose(image)
    if flip == 5:
        return np.rot90(image, 1)
    if flip == 6:
        return np.rot90(image, -1)
    if flip == 7:
        rotated = np.rot90(image, -1)
        return np.fliplr(rotated)
    return image


def transform_box_for_orientation(
    x: float,
    y: float,
    w: float,
    h: float,
    image_shape: tuple[int, int],
    flip: int,
) -> tuple[float, float, float, float]:
    """Transform an axis-aligned box into display-oriented image coordinates."""
    height, width = image_shape
    corners = np.array(
        [
            [x, y],
            [x + w, y],
            [x, y + h],
            [x + w, y + h],
        ],
        dtype=np.float32,
    )

    xs = corners[:, 0]
    ys = corners[:, 1]
    if flip == 0:
        tx, ty = xs, ys
    elif flip == 1:
        tx, ty = width - xs, ys
    elif flip == 2:
        tx, ty = xs, height - ys
    elif flip == 3:
        tx, ty = width - xs, height - ys
    elif flip == 4:
        tx, ty = ys, xs
    elif flip == 5:
        tx, ty = ys, width - xs
    elif flip == 6:
        tx, ty = height - ys, xs
    elif flip == 7:
        tx, ty = height - ys, width - xs
    else:
        tx, ty = xs, ys

    x0 = float(np.min(tx))
    y0 = float(np.min(ty))
    x1 = float(np.max(tx))
    y1 = float(np.max(ty))
    return x0, y0, x1 - x0, y1 - y0
