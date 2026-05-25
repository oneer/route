#!/usr/bin/python
# ============================================================================
# bcc.py — 亮度与对比度控制（Brightness Contrast Control）
# ============================================================================
# 用途：
#   对 ISP 管线末端的 RGB/YUV 图像进行亮度和对比度调整，
#   属于后处理模块，用于微调最终输出的视觉效果。
#
# 公式：
#   output = input + brightness + (input - 127) × contrast
#   其中 127 是 8-bit 的中点值，表示"中性灰"的参考位置。
#   brightness 做整体平移，contrast 以 127 为中心拉伸/压缩。
# ============================================================================

import numpy as np


class BCC:
    """
    亮度与对比度控制 (Brightness Contrast Control)

    同时调整图像的亮度和对比度：
    - brightness > 0：整体提亮
    - brightness < 0：整体压暗
    - contrast > 0：增强对比度（亮部更亮，暗部更暗）
    - contrast < 0：降低对比度（画面变灰）
    """

    def __init__(self, img, brightness, contrast, clip):
        """
        初始化 BCC 模块。

        参数：
            img:        输入图像（numpy 数组，通常为 RGB 或 YUV）
            brightness: 亮度偏移量
            contrast:   对比度系数
            clip:       输出像素值的裁剪上限（下限固定为 0）
        """
        self.img = img
        self.brightness = brightness
        self.contrast = contrast
        self.clip = clip

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。
        使用 np.clip 的 out 参数做原地操作。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def execute(self):
        """
        执行亮度与对比度调整。

        公式：
            output = input + brightness + (input - 127) × contrast

        其中 127 是 8-bit 域的中点值。以 127 为中心做对比度变换，
        意味着 middle gray 附近的像素基本不变（仅受 brightness 影响），
        而亮部和暗部按 contrast 系数拉伸或压缩。

        返回：
            调整后的图像数组
        """
        img_h = self.img.shape[0]  # 图像高度
        img_w = self.img.shape[1]  # 图像宽度

        # 创建输出数组
        bcc_img = np.empty((img_h, img_w), np.int16)

        # 第一步：整体加上亮度偏移
        bcc_img = self.img + self.brightness

        # 第二步：以 127 为中心做对比度变换
        # (self.img - 127) 提取偏离中点的量，乘以 contrast 系数后叠加回去
        bcc_img = bcc_img + (self.img - 127) * self.contrast

        self.img = bcc_img
        return self.clipping()
