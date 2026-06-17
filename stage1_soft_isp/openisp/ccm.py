#!/usr/bin/python
# ============================================================================
# ccm.py — 颜色校正矩阵（Color Correction Matrix）
# ============================================================================
# 用途：
#   用 3×4 矩阵将相机 RGB 映射到目标颜色空间（如 sRGB）。
#   矩阵的前三列为 3×3 线性变换，第四列为偏移量（bias/offset）。
#
# 原理：
#   CCM 用于修正相机传感器光谱响应与标准颜色空间之间的差异。
#   与 AWB 的对角增益不同，CCM 允许通道间混合：
#     R' = m00×R + m01×G + m02×B + offset_0
#     G' = m10×R + m11×G + m12×B + offset_1
#     B' = m20×R + m21×G + m22×B + offset_2
#
# 实现细节：
#   - 逐像素矩阵乘法（性能较低，适合学习验证）
#   - 结果除以 1024 做定点缩放
#   - 输出转换为 uint8
# ============================================================================

import numpy as np


class CCM:
    """
    颜色校正矩阵 (Color Correction Matrix)

    将相机 RGB 通过 3×4 矩阵变换到目标颜色空间。
    矩阵格式为 [R_coeffs, G_coeffs, B_coeffs]，每行 4 个值：
      - 前 3 个为乘法系数（3×3 线性变换）
      - 第 4 个为偏移量（bias）
    """

    def __init__(self, img, ccm):
        """
        初始化 CCM 模块。

        参数：
            img: 输入 RGB 图像（numpy 数组，形状为 (H, W, 3)）
            ccm: 3×4 颜色校正矩阵
        """
        self.img = img
        self.ccm = ccm

    def execute(self):
        """
        执行颜色校正矩阵变换。

        对每个像素执行矩阵乘法：
            RGB' = ccm[:, 0:3] × RGB + ccm[:, 3]
        结果除以 1024 做缩放后转为 uint8。

        注意：此实现使用嵌套 Python for 循环（逐行逐列），
        性能较低，适合学习和验证算法逻辑。

        返回：
            CCM 校正后的 uint8 RGB 图像
        """
        img_h = self.img.shape[0]  # 图像高度
        img_w = self.img.shape[1]  # 图像宽度
        img_c = self.img.shape[2]  # 通道数（固定为 3）

        # 创建输出数组（uint32 防止中间计算溢出）
        ccm_img = np.empty((img_h, img_w, img_c), np.uint32)

        # 逐像素处理
        for y in range(img_h):
            for x in range(img_w):
                # ccm[:, 0:3] 取 3×3 线性部分，与当前像素 RGB 做逐元素乘法
                mulval = self.ccm[:, 0:3] * self.img[y, x, :]

                # 计算输出各通道 = 线性部分之和 + 偏移量
                ccm_img[y, x, 0] = np.sum(mulval[0]) + self.ccm[0, 3]  # R' = Σ(R_coeffs × RGB) + offset_R
                ccm_img[y, x, 1] = np.sum(mulval[1]) + self.ccm[1, 3]  # G' = Σ(G_coeffs × RGB) + offset_G
                ccm_img[y, x, 2] = np.sum(mulval[2]) + self.ccm[2, 3]  # B' = Σ(B_coeffs × RGB) + offset_B

                # 定点缩放：除以 1024（相当于右移 10 位）
                ccm_img[y, x, :] = ccm_img[y, x, :] / 1024

        # 转换为 uint8 输出
        self.img = ccm_img.astype(np.uint8)
        return self.img
