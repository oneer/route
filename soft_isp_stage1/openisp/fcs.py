#!/usr/bin/python
# ============================================================================
# fcs.py — 伪色抑制（False Color Suppression）
# ============================================================================
# 用途：
#   在 Demosaic 后抑制伪色（false color）伪影。
#   伪色通常出现在高频纹理区域，表现为与实际场景颜色不符的彩色条纹或斑点。
#
# 原理：
#   利用边缘图（edgemap）判断每个像素是否落在高频/边缘区域：
#     - 平坦区域（|edgemap| ≤ fcs_edge[0]）：保持 UV 增益为 1.0（正常饱和度）
#     - 过渡区域（fcs_edge[0] < |edgemap| < fcs_edge[1]）：UV 增益随边缘强度递减
#     - 强边缘区域（|edgemap| ≥ fcs_edge[1]）：UV 增益降为 0（去色/灰度化）
#
#   核心思想：在强边缘附近暂时降低色彩饱和度，
#   因为人眼对边缘区域的亮度变化更敏感，而对颜色的分辨率较低。
#   降低伪色区域的颜色信息可以有效减少视觉上的彩色伪影。
#
# 公式：
#   yuv_out = uvgain × (yuv_in) / 256 + 128
#   其中 uvgain 是边缘自适应的色彩增益
# ============================================================================

import numpy as np


class FCS:
    """
    伪色抑制 (False Color Suppression)

    利用边缘图自适应降低高频区域的色彩饱和度，
    减少 Demosaic 后可能出现的彩色伪影。
    """

    def __init__(self, img, edgemap, fcs_edge, gain, intercept, slope):
        """
        初始化 FCS 模块。

        参数：
            img:       输入的 YUV 图像（numpy 数组，形状为 (H, W, 3)）
            edgemap:   边缘强度图（由 EE 模块输出的 em_img）
            fcs_edge:  边缘阈值 [低阈值, 高阈值]
                       - 低于低阈值：色彩增益保持正常
                       - 在中间：增益线性递减
                       - 高于高阈值：色彩增益为 0
            gain:      基础色彩增益
            intercept: 线性递减的截距（gain 函数的截距）
            slope:     线性递减的斜率（gain 函数的斜率）
        """
        self.img = img
        self.edgemap = edgemap
        self.fcs_edge = fcs_edge
        self.gain = gain
        self.intercept = intercept
        self.slope = slope

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, 255] 范围内。
        """
        np.clip(self.img, 0, 255, out=self.img)
        return self.img

    def execute(self):
        """
        执行伪色抑制。

        对每个像素：
          1. 读取边缘强度 |edgemap[y,x]|
          2. 根据边缘强度分段计算 UV 增益 (uvgain)：
             - 平坦区：uvgain = gain（保持正常颜色饱和）
             - 过渡区：uvgain = intercept - slope × |edgemap|（线性衰减）
             - 强边缘：uvgain = 0（完全去色）
          3. 应用增益：yuv_out = uvgain × yuv_in / 256 + 128

        乘以 uvgain 后除以 256（定点缩放），加 128 回到无符号范围。

        返回：
            伪色抑制后的 YUV 图像
        """
        img_h = self.img.shape[0]
        img_w = self.img.shape[1]
        img_c = self.img.shape[2]

        # 创建输出数组
        fcs_img = np.empty((img_h, img_w, img_c), np.int16)

        # 逐像素处理
        for y in range(img_h):
            for x in range(img_w):
                # --- 根据边缘强度计算 UV 增益 ---
                if np.abs(self.edgemap[y, x]) <= self.fcs_edge[0]:
                    # 平坦区域：保持完整色彩增益
                    uvgain = self.gain
                elif np.abs(self.edgemap[y, x]) > self.fcs_edge[0] and np.abs(self.edgemap[y, x]) < self.fcs_edge[1]:
                    # 过渡区域：UV 增益随边缘强度线性递减
                    uvgain = self.intercept - self.slope * self.edgemap[y, x]
                else:
                    # 强边缘区域：UV 增益降为 0（完全去色）
                    uvgain = 0

                # 应用 UV 增益到 UV 通道（除以 256 定点缩放，加 128 偏移）
                fcs_img[y, x, :] = uvgain * (self.img[y, x, :]) / 256 + 128

        self.img = fcs_img
        return self.clipping()
