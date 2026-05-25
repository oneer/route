#!/usr/bin/python
# ============================================================================
# csc.py — 色彩空间转换（Color Space Conversion）
# ============================================================================
# 用途：
#   将 RGB 图像通过 3×4 矩阵转换到另一个色彩空间（如 sRGB → YUV）。
#   结构与 CCM 类似，但语义不同：CSC 做色彩空间映射，CCM 做颜色校正。
#
# 公式：
#   对每个像素的 RGB 三通道值，用矩阵做线性变换：
#     Y  = csc[0,0]×R + csc[0,1]×G + csc[0,2]×B + csc[0,3]
#     U  = csc[1,0]×R + csc[1,1]×G + csc[1,2]×B + csc[1,3]
#     V  = csc[2,0]×R + csc[2,1]×G + csc[2,2]×B + csc[2,3]
#   结果除以 1024 做定点缩放后转为 uint8。
#
# 性能说明：
#   本实现使用 numpy 向量化操作（一次处理整个通道），
#   而非像素级循环，性能远优于 CCM 模块的逐像素实现。
# ============================================================================

import numpy as np
from scipy.ndimage import correlate  # 注意：此处导入但实际未使用


class CSC:
    """
    色彩空间转换 (Color Space Conversion)

    用 3×4 矩阵将 RGB 图像转换到目标色彩空间（如 YUV）。
    矩阵格式与 CCM 相同：[3×3 线性变换 | 偏移量]。
    """

    def __init__(self, img, csc):
        """
        初始化 CSC 模块。

        参数：
            img: 输入 RGB 图像（numpy 数组，形状为 (H, W, 3)）
            csc: 3×4 颜色空间转换矩阵
        """
        self.img = img
        self.csc = csc

    def execute(self):
        """
        执行色彩空间转换。

        使用 numpy 向量化操作对整个通道做矩阵乘法，避免逐像素循环：
          csc_img[:,:,0] = R×m00 + G×m01 + B×m02 + offset_0
          csc_img[:,:,1] = R×m10 + G×m11 + B×m12 + offset_1
          csc_img[:,:,2] = R×m20 + G×m21 + B×m22 + offset_2

        返回：
            CSC 转换后的 uint8 图像
        """
        img_h = self.img.shape[0]  # 图像高度
        img_w = self.img.shape[1]  # 图像宽度
        img_c = self.img.shape[2]  # 通道数

        # 创建输出数组（uint32 防止中间溢出）
        csc_img = np.empty((img_h, img_w, img_c), np.uint32)

        # --- 向量化矩阵乘法（一次处理整个通道）---
        # 通道 0 输出 = R×csc[0,0] + G×csc[0,1] + B×csc[0,2] + csc[0,3]
        csc_img[:, :, 0] = (
            self.img[:, :, 0] * self.csc[0, 0]
            + self.img[:, :, 1] * self.csc[0, 1]
            + self.img[:, :, 2] * self.csc[0, 2]
            + self.csc[0, 3]
        )

        # 通道 1 输出
        csc_img[:, :, 1] = (
            self.img[:, :, 0] * self.csc[1, 0]
            + self.img[:, :, 1] * self.csc[1, 1]
            + self.img[:, :, 2] * self.csc[1, 2]
            + self.csc[1, 3]
        )

        # 通道 2 输出
        csc_img[:, :, 2] = (
            self.img[:, :, 0] * self.csc[2, 0]
            + self.img[:, :, 1] * self.csc[2, 1]
            + self.img[:, :, 2] * self.csc[2, 2]
            + self.csc[2, 3]
        )

        # 定点缩放：除以 1024
        csc_img = csc_img / 1024

        # 转换为 uint8 输出
        self.img = csc_img.astype(np.uint8)
        return self.img
