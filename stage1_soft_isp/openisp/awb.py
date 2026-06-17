#!/usr/bin/python
# ============================================================================
# awb.py — 自动白平衡增益控制（Auto White Balance Gain Control）
# ============================================================================
# 用途：
#   在 Bayer RAW 域对四个颜色通道（R, Gr, Gb, B）分别施加增益，
#   校正光源色偏，使白色/灰色物体在各通道上恢复相近的像素值。
#
# 原理：
#   不同光源（日光、钨丝灯、荧光灯等）具有不同的光谱分布，
#   导致相机传感器各通道的响应比例不同。AWB 通过给各通道乘以
#   不同的增益来补偿这种差异。
#
# 与 soft_isp/awb.py 的区别：
#   - 本模块在 Bayer RAW 域操作（Demosaic 之前），直接修改原始像素
#   - soft_isp/awb.py 在 Demosaic 之后的线性 RGB 域操作
#   - RAW 域的 AWB 需要区分 Gr 和 Gb（物理位置不同，增益可能不同）
# ============================================================================

import numpy as np


class WBGC:
    """
    自动白平衡增益控制 (Auto White Balance Gain Control)

    在 Bayer RAW 域对 R/Gr/Gb/B 四个通道分别乘以对应增益。
    增益值由外部传入（parameter 参数），不在此模块内自动估计。
    """

    def __init__(self, img, parameter, bayer_pattern, clip):
        """
        初始化白平衡增益控制。

        参数：
            img:           输入的 Bayer RAW 图像（numpy 数组）
            parameter:     四个通道的增益值 [r_gain, gr_gain, gb_gain, b_gain]
                          注意 Gr 和 Gb 使用独立增益（传感器上物理位置不同）
            bayer_pattern: Bayer 排列方式，支持 'rggb', 'bggr', 'gbrg', 'grbg'
            clip:          输出像素值的裁剪上限
        """
        self.img = img
        self.parameter = parameter
        self.bayer_pattern = bayer_pattern
        self.clip = clip

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。

        使用 np.clip 的 out 参数做原地操作，避免额外内存分配。
        返回：
            裁剪后的图像数组
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def execute(self):
        """
        执行白平衡增益校正。

        步骤：
            1. 解包四个通道的增益值
            2. 根据 Bayer 排列模式，用切片语法定位各通道像素
            3. 各通道分别乘以对应增益
            4. 重建完整的 Bayer 图像
            5. 对结果进行限幅裁剪

        Bayer 切片语法说明（以 RGGB 为例）：
            - img[::2, ::2]  → R   (偶数行, 偶数列)
            - img[::2, 1::2] → Gr  (偶数行, 奇数列)
            - img[1::2, ::2] → Gb  (奇数行, 偶数列)
            - img[1::2, 1::2] → B   (奇数行, 奇数列)

        返回：
            白平衡校正后的 RAW 图像
        """
        # --- 解包四个通道的增益值 ---
        r_gain = self.parameter[0]    # R  通道增益
        gr_gain = self.parameter[1]   # Gr 通道增益（与 R 同行）
        gb_gain = self.parameter[2]   # Gb 通道增益（与 B 同行）
        b_gain = self.parameter[3]    # B  通道增益

        raw_h = self.img.shape[0]  # 图像高度
        raw_w = self.img.shape[1]  # 图像宽度

        # 创建输出数组（int16 以支持增益乘法后的值范围）
        awb_img = np.empty((raw_h, raw_w), np.int16)

        # --- 根据 Bayer 排列逐通道应用增益 ---
        if self.bayer_pattern == 'rggb':
            # Bayer 排列:  R(0,0)  Gr(0,1)
            #              Gb(1,0)  B(1,1)
            r = self.img[::2, ::2] * r_gain     # R  通道 × R 增益
            b = self.img[1::2, 1::2] * b_gain   # B  通道 × B 增益
            gr = self.img[::2, 1::2] * gr_gain  # Gr 通道 × Gr 增益
            gb = self.img[1::2, ::2] * gb_gain  # Gb 通道 × Gb 增益
            # 重建完整 Bayer 图像
            awb_img[::2, ::2] = r
            awb_img[::2, 1::2] = gr
            awb_img[1::2, ::2] = gb
            awb_img[1::2, 1::2] = b

        elif self.bayer_pattern == 'bggr':
            # Bayer 排列:  B(0,0)  Gb(0,1)
            #              Gr(1,0)  R(1,1)
            b = self.img[::2, ::2] * b_gain
            r = self.img[1::2, 1::2] * r_gain
            gb = self.img[::2, 1::2] * gb_gain
            gr = self.img[1::2, ::2] * gr_gain
            awb_img[::2, ::2] = b
            awb_img[::2, 1::2] = gb
            awb_img[1::2, ::2] = gr
            awb_img[1::2, 1::2] = r

        elif self.bayer_pattern == 'gbrg':
            # Bayer 排列:  Gb(0,0) B(0,1)
            #              R(1,0)  Gr(1,1)
            b = self.img[::2, 1::2] * b_gain
            r = self.img[1::2, ::2] * r_gain
            gb = self.img[::2, ::2] * gb_gain
            gr = self.img[1::2, 1::2] * gr_gain
            awb_img[::2, ::2] = gb
            awb_img[::2, 1::2] = b
            awb_img[1::2, ::2] = r
            awb_img[1::2, 1::2] = gr

        elif self.bayer_pattern == 'grbg':
            # Bayer 排列:  Gr(0,0) R(0,1)
            #              B(1,0)  Gb(1,1)
            r = self.img[::2, 1::2] * r_gain
            b = self.img[1::2, ::2] * b_gain
            gr = self.img[::2, ::2] * gr_gain
            gb = self.img[1::2, 1::2] * gb_gain
            awb_img[::2, ::2] = gr
            awb_img[::2, 1::2] = r
            awb_img[1::2, ::2] = b
            awb_img[1::2, 1::2] = gb

        # 保存结果并执行限幅
        self.img = awb_img
        return self.clipping()
