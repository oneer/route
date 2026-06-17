#!/usr/bin/python
# ============================================================================
# eeh.py — 边缘增强（Edge Enhancement）
# ============================================================================
# 用途：
#   对图像进行边缘/细节增强，使图像看起来更锐利。
#   通常放在色彩空间转换（CSC）之后，在亮度通道（Y）上操作。
#
# 原理：
#   1. 用边缘检测滤波器（edge_filter）提取高频细节
#   2. 通过增益 LUT（emlut）对提取的细节进行非线性映射
#      - 小幅度的细节被放大（增强纹理）
#      - 中等幅度的细节被抑制（避免噪声放大）
#      - 大幅度的边缘被增强（强化轮廓）
#   3. 将处理后的细节加回原图
#
# 增益 LUT 结构（emlut）：
#   输入值 val 的绝对值属于不同区间时使用不同增益：
#     - |val| < thres[0]:  用 gain[0]（死区，可能设为 0）
#     - thres[0] < |val| < thres[1]: 用 gain[1]（增强区）
#     - |val| > thres[1]:  用 gain[1]（大幅值增强）
# ============================================================================

import numpy as np


class EE:
    """
    边缘增强 (Edge Enhancement)

    对图像亮度通道做细节提取和非线性增益映射，增强边缘和纹理。
    """

    def __init__(self, img, edge_filter, gain, thres, emclip):
        """
        初始化边缘增强模块。

        参数：
            img:         输入图像（numpy 数组，通常为 Y 通道）
            edge_filter: 边缘检测/高通滤波器核（3×5）
            gain:        增益列表 [小幅度增益, 大幅度增益]
            thres:       阈值列表 [低阈值, 高阈值]，定义死区和增强区
            emclip:      输出裁切范围 [最小值, 最大值]
        """
        self.img = img
        self.edge_filter = edge_filter
        self.gain = gain
        self.thres = thres
        self.emclip = emclip

    def padding(self):
        """
        边界填充：垂直 1 像素、水平 2 像素的镜像反射填充，
        匹配 3×5 滤波器核的尺寸。
        """
        img_pad = np.pad(self.img, ((1, 1), (2, 2)), 'reflect')
        return img_pad

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, 255] 范围内。
        """
        np.clip(self.img, 0, 255, out=self.img)
        return self.img

    def emlut(self, val, thres, gain, clip):
        """
        边缘增强查找表 (Edge Map LUT)。

        根据细节值 val 的大小分段赋予不同的增益：
          - |val| < thres[0]:                    用 gain[0]（死区/去噪）
          - thres[0] < |val| < thres[1]:         0（过渡区，不处理）
          - |val| > thres[1]:                    用 gain[1]（增强大边缘）

        参数：
            val:   提取到的边缘/细节值
            thres: 阈值 [低阈值, 高阈值]
            gain:  增益 [小幅度增益, 大幅度增益]
            clip:  输出裁剪范围

        返回：
            增益映射后的细节值（除以 256 做定点缩放）
        """
        lut = 0
        if val < -thres[1]:
            lut = gain[1] * val               # 负大幅值 → 大幅度增益
        elif val < -thres[0] and val > -thres[1]:
            lut = 0                           # 过渡区 → 抑制
        elif val < thres[0] and val > -thres[1]:
            lut = gain[0] * val               # 小幅值 → 小幅度增益
        elif val > thres[0] and val < thres[1]:
            lut = 0                           # 过渡区 → 抑制
        elif val > thres[1]:
            lut = gain[1] * val               # 正大幅值 → 大幅度增益

        # 裁剪到指定范围，除以 256 做定点缩放
        lut = max(clip[0], min(lut / 256, clip[1]))
        return lut

    def execute(self):
        """
        执行边缘增强。

        步骤：
          1. 用 edge_filter 对图像做卷积 → 提取高频细节图 (em_img)
          2. 对细节图的每个像素通过 emlut 做非线性映射
          3. 映射后的细节叠加回原图 → ee_img = img + enhanced_detail

        返回：
            (增强后的图像, 细节图)
        """
        # 边界填充后转为 int16
        img_pad = self.padding().astype(np.int16)
        img_h = self.img.shape[0]
        img_w = self.img.shape[1]

        # 创建输出数组
        ee_img = np.empty((img_h, img_w), np.int16)  # 增强后的图像
        em_img = np.empty((img_h, img_w), np.int16)  # 细节图

        # 逐像素处理
        for y in range(img_pad.shape[0] - 2):
            for x in range(img_pad.shape[1] - 4):
                # 3×5 卷积提取边缘/细节：将滤波器核与对应图像区域逐元素乘加
                em_img[y, x] = np.sum(np.multiply(img_pad[y:y + 3, x:x + 5], self.edge_filter[:, :])) / 8

                # 原图 + 增强后的细节
                ee_img[y, x] = img_pad[y + 1, x + 2] + self.emlut(em_img[y, x], self.thres, self.gain, self.emclip)

        self.img = ee_img
        return self.clipping(), em_img
