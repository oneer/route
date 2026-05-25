#!/usr/bin/python
# ============================================================================
# hsc.py — 色相与饱和度控制（Hue Saturation Control）
# ============================================================================
# 用途：
#   对 YUV 色彩空间的 UV 通道进行色相旋转和饱和度调整。
#   属于后处理模块，用于微调最终图像的色彩表现。
#
# 原理：
#   在 YUV 空间中，U 和 V 构成了一个二维色彩平面：
#     - 色相 (Hue):        U/V 向量与 U 轴的角度，旋转 U/V 改变色相
#     - 饱和度 (Saturation): U/V 向量的幅值，缩放 U/V 改变饱和度
#
# 公式：
#   色相旋转：
#     U' = (U - 128) × cos(hue) + (V - 128) × sin(hue) + 128
#     V' = (V - 128) × cos(hue) - (U - 128) × sin(hue) + 128
#   饱和度调整：
#     U' = saturation × (U - 128) / 256 + 128
#     V' = saturation × (V - 128) / 256 + 128
#
#   注意：实现中先减去 128（中性灰偏移），在 (-128, 128) 范围做变换，
#   最后再加回 128。除以 256 做定点缩放（sin/cos 值也 ×256 存储）。
# ============================================================================

import numpy as np


class HSC:
    """
    色相与饱和度控制 (Hue Saturation Control)

    在 YUV 色彩空间对 UV 通道做色相旋转和饱和度调整。
    """

    def __init__(self, img, hue, saturation, clip):
        """
        初始化 HSC 模块。

        参数：
            img:        输入的 YUV 图像（numpy 数组，形状为 (H, W, 3)）
            hue:        色相旋转角度（度，0~359）
            saturation: 饱和度增益（256 = 原始饱和，>256 = 增强，<256 = 减弱）
            clip:       输出像素值的裁剪上限
        """
        self.img = img
        self.hue = hue
        self.saturation = saturation
        self.clip = clip

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def lut(self):
        """
        预计算 sin 和 cos 查找表。

        对所有角度（0~359 度）预先计算 sin 和 cos 值，
        乘以 256 做定点化存储（round 取整），方便后续查表运算。

        返回：
            (lut_sin, lut_cos): 两个字典，键为角度（0~359），值为定点化三角函数值
        """
        # 生成 0~359 的角度数组
        ind = np.array([i for i in range(360)])

        # 计算 sin 和 cos，乘以 256 做定点化
        sin = np.sin(ind * np.pi / 180) * 256
        cos = np.cos(ind * np.pi / 180) * 256

        # 构建字典形式的查找表：{角度: 定点化三角函数值}
        lut_sin = dict(zip(ind, [round(sin[i]) for i in ind]))
        lut_cos = dict(zip(ind, [round(cos[i]) for i in ind]))

        return lut_sin, lut_cos

    def execute(self):
        """
        执行色相旋转和饱和度调整。

        步骤：
          1. 预计算 sin/cos 查找表
          2. 对整个 U/V 通道做向量化色相旋转
          3. 对整个 U/V 通道做向量化饱和度调整

        色相旋转（UV 平面的二维旋转矩阵）：
          U' = (U-128)×cos(h) + (V-128)×sin(h) + 128
          V' = (V-128)×cos(h) - (U-128)×sin(h) + 128

        饱和度调整：
          U' = saturation × (U-128) / 256 + 128

        返回：
            色相/饱和度调整后的图像
        """
        lut_sin, lut_cos = self.lut()

        img_h = self.img.shape[0]
        img_w = self.img.shape[1]
        img_c = self.img.shape[2]

        # 创建输出数组
        hsc_img = np.empty((img_h, img_w, img_c), np.int16)

        # --- 色相旋转（UV 平面旋转）---
        # 注意：通道索引 0=Y, 1=U, 2=V
        # new_U = (U-128)*cos(hue) + (V-128)*sin(hue) + 128
        hsc_img[:, :, 0] = (
            (self.img[:, :, 0] - 128) * lut_cos[self.hue]
            + (self.img[:, :, 1] - 128) * lut_sin[self.hue]
            + 128
        )
        # new_V = (V-128)*cos(hue) - (U-128)*sin(hue) + 128
        hsc_img[:, :, 1] = (
            (self.img[:, :, 1] - 128) * lut_cos[self.hue]
            - (self.img[:, :, 0] - 128) * lut_sin[self.hue]
            + 128
        )

        # --- 饱和度调整（缩放 UV 偏离中性灰的幅度）---
        # U' = saturation × (U-128) / 256 + 128
        hsc_img[:, :, 0] = self.saturation * (self.img[:, :, 0] - 128) / 256 + 128
        # V' = saturation × (V-128) / 256 + 128
        hsc_img[:, :, 1] = self.saturation * (self.img[:, :, 1] - 128) / 256 + 128

        self.img = hsc_img
        return self.clipping()
