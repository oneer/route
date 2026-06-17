"""颜色校正矩阵（Color Correction Matrix, CCM）模块。

CCM 在 AWB 之后执行，用 3x3 矩阵将相机 RGB 映射到目标颜色空间的 RGB。
与 AWB 的对角增益不同，CCM 允许通道间混合（如 R' = m00*R + m01*G + m02*B），
从而修正相机传感器光谱响应与标准颜色空间之间的差异。

函数列表：
    - apply_ccm:                   将 3x3 CCM 应用到 HxWx3 线性 RGB 图像
    - ccm_from_rawpy_color_matrix: 从 rawpy 元数据提取学习用 3x3 CCM
"""

from __future__ import annotations

import numpy as np


def apply_ccm(rgb_linear: np.ndarray, matrix: np.ndarray, white_level: float | None = None) -> np.ndarray:
    """将 3x3 颜色校正矩阵应用到 HxWx3 线性 RGB 图像。

    公式：rgb_corrected = rgb @ CCM.T（矩阵乘法，每个像素独立变换）
    即 R' = m00*R + m01*G + m02*B，以此类推。

    参数:
        rgb_linear:  (H, W, 3) 的线性 RGB 图像
        matrix:      3x3 颜色校正矩阵
        white_level: 若不为 None，将结果 clip 到 [0, white_level]

    返回:
        CCM 校正后的 float32 线性 RGB 图像

    异常:
        ValueError: rgb_linear 的 shape 不是 (H, W, 3) 或 matrix 不是 (3, 3)
    """
    rgb = np.asarray(rgb_linear, dtype=np.float32)
    ccm = np.asarray(matrix, dtype=np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb_linear must have shape (H, W, 3), got {rgb.shape}")
    if ccm.shape != (3, 3):
        raise ValueError(f"matrix must have shape (3, 3), got {ccm.shape}")

    corrected = rgb @ ccm.T
    if white_level is not None:
        corrected = np.clip(corrected, 0.0, float(white_level))
    return corrected.astype(np.float32)


def ccm_from_rawpy_color_matrix(color_matrix: np.ndarray) -> np.ndarray:
    """从 rawpy 的 color_matrix 元数据提取学习用 3x3 CCM。

    rawpy 的 color_matrix 通常大于 3x3（含多个光源校准矩阵），
    本函数取前 3 行 3 列作为简化学习用矩阵。
    若矩阵无效（非有限值或全零），返回单位矩阵（无校正效果）。

    参数:
        color_matrix: rawpy 返回的 color_matrix 属性

    返回:
        3x3 float32 颜色校正矩阵
    """
    matrix = np.asarray(color_matrix, dtype=np.float32)
    if matrix.shape[0] < 3 or matrix.shape[1] < 3:
        return np.eye(3, dtype=np.float32)
    ccm = matrix[:3, :3].astype(np.float32)
    if not np.all(np.isfinite(ccm)) or np.max(np.abs(ccm)) == 0:
        return np.eye(3, dtype=np.float32)
    return ccm
