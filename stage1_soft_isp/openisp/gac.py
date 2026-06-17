#!/usr/bin/python
# ============================================================================
# gac.py — Gamma 校正（Gamma Correction）
# ============================================================================
# 用途：
#   将线性 RGB/YUV 图像通过 Gamma LUT（查找表）映射到显示编码空间。
#   Gamma 校正是 ISP 管线接近末端的步骤，负责将线性光强值转换
#   为符合显示设备和人类视觉感知的非线性编码。
#
# 原理：
#   显示设备（如 LCD/OLED）的输入-输出响应近似为幂函数：
#     L_display ≈ V_input ^ gamma
#   为了在显示端获得正确的线性亮度，需要预先做反幂函数编码：
#     V_encode = L_linear ^ (1 / gamma)
#   典型 gamma 值为 2.2（sRGB 标准）。
#
# 实现方式：
#   使用预先计算好的 LUT 做查表映射，避免逐像素计算幂函数。
#   支持两种模式：
#     - 'rgb': 三个通道共用同一个 LUT
#     - 'yuv': Y 通道用 luma LUT，UV 通道用 chroma LUT
# ============================================================================

import numpy as np


class GC:
    """
    Gamma 校正 (Gamma Correction)

    使用预先计算的查找表 (LUT) 将线性图像映射到 gamma 编码空间。
    """

    def __init__(self, img, lut, mode):
        """
        初始化 Gamma 校正模块。

        参数：
            img:  输入图像（numpy 数组，形状为 (H, W, 3)）
            lut:  Gamma 查找表（mode='rgb' 时为单 LUT 数组，
                  mode='yuv' 时为 [luma_lut, chroma_lut] 列表）
            mode: 校正模式，'rgb' 或 'yuv'
        """
        self.img = img
        self.lut = lut
        self.mode = mode

    def execute(self):
        """
        执行 Gamma 校正。

        遍历每个像素，用查表方式将线性值映射为 gamma 编码值：
          - 'rgb' 模式：三个通道各查同一个 LUT，结果除以 4
          - 'yuv' 模式：Y 通道查 luma LUT，UV 通道查 chroma LUT

        返回：
            Gamma 校正后的图像
        """
        img_h = self.img.shape[0]
        img_w = self.img.shape[1]
        img_c = self.img.shape[2]

        # 创建输出数组
        gc_img = np.empty((img_h, img_w, img_c), np.uint16)

        # 逐像素查表
        for y in range(self.img.shape[0]):
            for x in range(self.img.shape[1]):

                if self.mode == 'rgb':
                    # RGB 模式：三个通道查同一个 LUT，结果除以 4
                    gc_img[y, x, 0] = self.lut[self.img[y, x, 0]]  # R 通道查表
                    gc_img[y, x, 1] = self.lut[self.img[y, x, 1]]  # G 通道查表
                    gc_img[y, x, 2] = self.lut[self.img[y, x, 2]]  # B 通道查表
                    gc_img[y, x, :] = gc_img[y, x, :] / 4          # 定点缩放

                elif self.mode == 'yuv':
                    # YUV 模式：Y 用亮度 LUT，UV 用色度 LUT
                    gc_img[y, x, 0] = self.lut[0][self.img[y, x, 0]]  # Y  通道 → luma LUT
                    gc_img[y, x, 1] = self.lut[1][self.img[y, x, 1]]  # U  通道 → chroma LUT
                    gc_img[y, x, 2] = self.lut[1][self.img[y, x, 2]]  # V  通道 → chroma LUT

        self.img = gc_img
        return self.img
