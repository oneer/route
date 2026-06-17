#!/usr/bin/python
# ============================================================================
# blc.py — 黑电平补偿（Black Level Compensation）
# ============================================================================
# 用途：
#   在 ISP 管线的最前端，从 Bayer RAW 数据中扣除传感器的暗电流偏置（黑电平），
#   使后续算法（DPC、Demosaic、AWB 等）在真实的"光信号"上工作。
#
# 原理：
#   图像传感器即使在没有光照的情况下也会输出非零电压（暗电流），
#   每个颜色通道的黑电平可能不同（R/Gr/Gb/B 独立），需要分别扣除。
#   此外，绿色通道可能受到相邻红/蓝通道的串扰（crosstalk）影响，
#   通过 alpha/beta 参数施加与 R/B 成正比的修正。
#
# 公式：
#   R'  = R_raw  + bl_r
#   Gr' = Gr_raw + bl_gr + alpha × R' / 256
#   Gb' = Gb_raw + bl_gb + beta  × B' / 256
#   B'  = B_raw  + bl_b
#
# 注：parameter 中存的是偏移量（取负数即为扣除），除以 256 实现定点运算。
# ============================================================================

import numpy as np


class BLC:
    """
    黑电平补偿 (Black Level Compensation)

    在图像传感器中，即使没有光线照射，像素也会输出一个非零的基底电压（黑电平）。
    不同颜色通道（R, Gr, Gb, B）的黑电平可能不同，需要分别减去。
    此外，绿色通道 (G) 还可能受到相邻红/蓝通道的串扰影响，
    因此通过 alpha/beta 参数施加与 R/B 成比例的修正。
    """

    def __init__(self, img, parameter, bayer_pattern, clip):
        """
        初始化 BLC 模块。

        参数说明：
            img:          输入的 RAW 图像（numpy 数组，通常为 uint16）
            parameter:    黑电平补偿参数列表 [bl_r, bl_gr, bl_gb, bl_b, alpha, beta]
                          - bl_r/bl_gr/bl_gb/bl_b: 各通道的偏移量（取负数即为扣除黑电平）
                          - alpha: Gr 通道串扰修正系数（与 R 通道成正比的修正）
                          - beta:  Gb 通道串扰修正系数（与 B 通道成正比的修正）
            bayer_pattern: Bayer 阵列排列，支持 'rggb', 'bggr', 'gbrg', 'grbg'
            clip:         输出像素值的上限，超过该值的像素会被截断
        """
        self.img = img
        self.parameter = parameter
        self.bayer_pattern = bayer_pattern
        self.clip = clip

    def clipping(self):
        """
        限幅：将图像像素值限制在 [0, clip] 范围内，防止溢出。
        操作是原地 (in-place) 的，直接修改 self.img。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def execute(self):
        """
        执行黑电平补偿。

        整体流程：
            1. 根据 Bayer 排列，将每个像素按颜色通道分别加上对应的黑电平偏移值
            2. 对 Gr/Gb 绿色通道额外施加与红/蓝通道成比例的串扰修正
               - Gr' = Gr_raw + bl_gr + alpha × R' / 256
               - Gb' = Gb_raw + bl_gb + beta  × B' / 256
               除以 256 相当于 8-bit 精度的定点增益因子，避免浮点运算
            3. 重建完整的 Bayer 图像到 blc_img 中
            4. 对结果进行限幅裁剪

        返回：
            BLC 校正后的 RAW 图像
        """
        # --- 解包参数 ---
        bl_r = self.parameter[0]    # R  通道黑电平偏移
        bl_gr = self.parameter[1]   # Gr 通道黑电平偏移（与 R 同行）
        bl_gb = self.parameter[2]   # Gb 通道黑电平偏移（与 B 同行）
        bl_b = self.parameter[3]    # B  通道黑电平偏移
        alpha = self.parameter[4]   # Gr 串扰修正系数
        beta = self.parameter[5]    # Gb 串扰修正系数

        raw_h = self.img.shape[0]   # 图像高度
        raw_w = self.img.shape[1]   # 图像宽度

        # 创建输出数组（int16 类型以适应有符号的中间计算）
        blc_img = np.empty((raw_h, raw_w), np.int16)

        # --- 根据 Bayer 排列逐通道处理 ---
        # Bayer 阵列是一个 2×2 的重复单元，四种排列本质上是同一单元的不同旋转/镜像
        # [::2, ::2]   = 从第 0 行 0 列开始，每隔 2 跳 — (偶数行, 偶数列)
        # [::2, 1::2]  = 从第 0 行 1 列开始 — (偶数行, 奇数列)
        # [1::2, ::2]  = 从第 1 行 0 列开始 — (奇数行, 偶数列)
        # [1::2, 1::2] = 从第 1 行 1 列开始 — (奇数行, 奇数列)

        if self.bayer_pattern == 'rggb':
            # Bayer 排列:  R(0,0)  Gr(0,1)
            #              Gb(1,0)  B(1,1)
            r = self.img[::2, ::2] + bl_r                                    # R  通道加偏移
            b = self.img[1::2, 1::2] + bl_b                                  # B  通道加偏移
            gr = self.img[::2, 1::2] + bl_gr + alpha * r / 256               # Gr 受同行的 R 串扰
            gb = self.img[1::2, ::2] + bl_gb + beta * b / 256                # Gb 受同列的 B 串扰
            # 重建到完整 Bayer 图像
            blc_img[::2, ::2] = r
            blc_img[::2, 1::2] = gr
            blc_img[1::2, ::2] = gb
            blc_img[1::2, 1::2] = b

        elif self.bayer_pattern == 'bggr':
            # Bayer 排列:  B(0,0)  Gb(0,1)
            #              Gr(1,0)  R(1,1)
            b = self.img[::2, ::2] + bl_b
            r = self.img[1::2, 1::2] + bl_r
            gb = self.img[::2, 1::2] + bl_gb + beta * b / 256                # Gb 受同行的 B 串扰
            gr = self.img[1::2, ::2] + bl_gr + alpha * r / 256               # Gr 受同列的 R 串扰
            blc_img[::2, ::2] = b
            blc_img[::2, 1::2] = gb
            blc_img[1::2, ::2] = gr
            blc_img[1::2, 1::2] = r

        elif self.bayer_pattern == 'gbrg':
            # Bayer 排列:  Gb(0,0) B(0,1)
            #              R(1,0)  Gr(1,1)
            b = self.img[::2, 1::2] + bl_b
            r = self.img[1::2, ::2] + bl_r
            gb = self.img[::2, ::2] + bl_gb + beta * b / 256                 # Gb 受同行的 B 串扰
            gr = self.img[1::2, 1::2] + bl_gr + alpha * r / 256              # Gr 受同行的 R 串扰
            blc_img[::2, ::2] = gb
            blc_img[::2, 1::2] = b
            blc_img[1::2, ::2] = r
            blc_img[1::2, 1::2] = gr

        elif self.bayer_pattern == 'grbg':
            # Bayer 排列:  Gr(0,0) R(0,1)
            #              B(1,0)  Gb(1,1)
            r = self.img[::2, 1::2] + bl_r
            b = self.img[1::2, ::2] + bl_b
            gr = self.img[::2, ::2] + bl_gr + alpha * r / 256                # Gr 受同行的 R 串扰
            gb = self.img[1::2, 1::2] + bl_gb + beta * b / 256               # Gb 受同行的 B 串扰
            blc_img[::2, ::2] = gr
            blc_img[::2, 1::2] = r
            blc_img[1::2, ::2] = b
            blc_img[1::2, 1::2] = gb

        # 将处理结果赋回 self.img，并执行限幅
        self.img = blc_img
        return self.clipping()
