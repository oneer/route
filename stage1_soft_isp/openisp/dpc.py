#!/usr/bin/python
# ============================================================================
# dpc.py — 坏点校正（Dead Pixel Correction）
# ============================================================================
# 用途：
#   检测并修复 Bayer RAW 图像中的坏点（dead/hot/stuck pixels）。
#   坏点是指传感器上响应异常（始终为 0、始终饱和、或与邻域显著不一致）的像素。
#
# 原理：
#   Bayer RAW 中间隔为 2 的像素属于同一颜色通道，因此也隔行隔列采样。
#   坏点检测在 3×3 的同色邻域（实际图像上为 5×5 窗口）中进行：
#
#     像素排列（以 RGGB 为例，p0 为待检测像素）：
#       p1  .  p2  .  p3     ← 第 y 行
#       .   .  .   .  .
#       p4  .  p0  .  p5     ← 第 y+2 行
#       .   .  .   .  .
#       p6  .  p7  .  p8     ← 第 y+4 行
#
#   如果 p0 与所有 8 个同色邻居的差值都超过阈值，判定为坏点。
#
# 修复策略（两种模式）：
#   - mean:    用水平/垂直方向的 4 个邻居均值替换
#   - gradient: 计算四个方向的梯度，选择最小梯度方向的 2 个邻居均值替换
# ============================================================================

import numpy as np


class DPC:
    """
    坏点校正 (Dead Pixel Correction)

    在 Bayer RAW 域检测并修复坏点。坏点检测在 5×5 图像窗口中
    取 3×3 同色邻域（因 Bayer 模式中间隔为 2）。
    """

    def __init__(self, img, thres, mode, clip):
        """
        初始化 DPC 模块。

        参数：
            img:   输入的 Bayer RAW 图像（numpy 数组）
            thres: 坏点检测阈值（像素值与邻居的差异超过此值才可能被判定为坏点）
            mode:  修复模式，'mean' 或 'gradient'
            clip:  输出像素值的裁剪上限
        """
        self.img = img
        self.thres = thres
        self.mode = mode
        self.clip = clip

    def padding(self):
        """
        边界填充：镜像反射模式向外扩展 2 像素。
        DPC 的 3×3 同色邻域在原始图像上对应 5×5 窗口，
        需要 2 像素填充。
        """
        img_pad = np.pad(self.img, (2, 2), 'reflect')
        return img_pad

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def execute(self):
        """
        执行坏点检测与修复。

        对每个像素：
          1. 提取 3×3 同色邻域（8 个邻居，每个间隔 2 像素）
          2. 判断是否所有邻居都超过阈值 → 标记为坏点
          3. 根据模式修复：
             - 'mean':     取上/下/左/右 4 个邻居的均值
             - 'gradient': 计算水平/垂直/主对角/副对角梯度，
                           取最小梯度方向的 2 个邻居均值

        Pixel array in code is showed above:

            p1  .  p2  .  p3     ← 同色邻域（在 5×5 窗口中，跳一取一）
            .   .  .   .  .
            p4  .  p0  .  p5
            .   .  .   .  .
            p6  .  p7  .  p8

        It makes sense for calculating follow-up gradients of pixel values
        (horizontal, vertical, left/right diagonal).

        返回：
            DPC 修复后的 uint16 RAW 图像
        """
        # 边界填充
        img_pad = self.padding()
        raw_h = self.img.shape[0]
        raw_w = self.img.shape[1]

        # 创建输出数组
        dpc_img = np.empty((raw_h, raw_w), np.uint16)

        # 逐像素处理
        for y in range(img_pad.shape[0] - 4):
            for x in range(img_pad.shape[1] - 4):

                # --- 提取 3×3 同色邻域（在图像上间隔为 2）---
                p0 = img_pad[y + 2, x + 2].astype(int)  # 中心像素（待检测）
                p1 = img_pad[y, x].astype(int)           # 左上
                p2 = img_pad[y, x + 2].astype(int)       # 上
                p3 = img_pad[y, x + 4].astype(int)       # 右上
                p4 = img_pad[y + 2, x].astype(int)       # 左
                p5 = img_pad[y + 2, x + 4].astype(int)   # 右
                p6 = img_pad[y + 4, x].astype(int)       # 左下
                p7 = img_pad[y + 4, x + 2].astype(int)   # 下
                p8 = img_pad[y + 4, x + 4].astype(int)   # 右下

                # --- 坏点判定 ---
                # 如果 p0 与所有 8 个邻居的差值都超过阈值 → 判定为坏点
                if (
                    (abs(p1 - p0) > self.thres)
                    and (abs(p2 - p0) > self.thres)
                    and (abs(p3 - p0) > self.thres)
                    and (abs(p4 - p0) > self.thres)
                    and (abs(p5 - p0) > self.thres)
                    and (abs(p6 - p0) > self.thres)
                    and (abs(p7 - p0) > self.thres)
                    and (abs(p8 - p0) > self.thres)
                ):
                    # --- 修复坏点 ---
                    if self.mode == 'mean':
                        # 均值模式：取上/下/左/右 4 个十字方向邻居的均值
                        p0 = (p2 + p4 + p5 + p7) / 4

                    elif self.mode == 'gradient':
                        # 梯度模式：计算四个方向的梯度，选最小梯度方向
                        dv = abs(2 * p0 - p2 - p7)   # 垂直梯度（上 + 下）
                        dh = abs(2 * p0 - p4 - p5)   # 水平梯度（左 + 右）
                        ddl = abs(2 * p0 - p1 - p8)  # 主对角线梯度（左上 + 右下）
                        ddr = abs(2 * p0 - p3 - p6)  # 副对角线梯度（右上 + 左下）

                        # 选择梯度最小（最平滑）的方向，用该方向两个邻居的均值
                        if min(dv, dh, ddl, ddr) == dv:
                            p0 = (p2 + p7 + 1) / 2    # 垂直方向（+1 做四舍五入）
                        elif min(dv, dh, ddl, ddr) == dh:
                            p0 = (p4 + p5 + 1) / 2    # 水平方向
                        elif min(dv, dh, ddl, ddr) == ddl:
                            p0 = (p1 + p8 + 1) / 2    # 主对角线方向
                        else:
                            p0 = (p3 + p6 + 1) / 2    # 副对角线方向

                # 写入输出数组
                dpc_img[y, x] = p0.astype('uint16')

        self.img = dpc_img
        return self.clipping()
