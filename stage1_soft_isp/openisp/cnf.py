#!/usr/bin/python
# ============================================================================
# cnf.py — 色度噪声滤波（Chroma Noise Filtering）
# ============================================================================
# 用途：
#   对 Demosaic 后的 RGB 图像进行色度（chroma）噪声抑制。
#   色度噪声在视觉上表现为彩色斑点，比亮度噪声更令人不悦。
#
# 原理：
#   CNF 在 Bayer RAW 域操作，利用同色和异色像素的关系检测色度噪声。
#   核心分为两步：
#     1. CND (Chroma Noise Detection):    检测某像素是否为色度噪声
#     2. CNC (Chroma Noise Correction):   对检测到的噪声像素进行修正
#
# 检测逻辑（CND）：
#   在 9×9 邻域内，将像素按 Bayer 位置分为三类：
#     - 两个 G 位置（Gr/Gb）→ 统计亮度基准 avgG
#     - 一种颜色位置（如 R） → 统计同色均值 avgC1
#     - 另一种颜色位置（如 B）→ 统计异色均值 avgC2
#   如果中心像素显著偏离 avgG 和 avgC2，且 avgC1 也显著偏离，
#   则认为该位置存在色度噪声。
#
# 修正逻辑（CNC）：
#   用 dampFactor 控制修正力度（增益越高，修正越保守），
#   结合 signalMeter（亮度信号水平）和邻域统计做 fade 混合。
# ============================================================================

import numpy as np


class CNF:
    """
    色度噪声滤波 (Chroma Noise Filtering)

    在 Bayer RAW 域检测并修正色度噪声。
    仅处理 R 和 B 位置的像素（G 位置保持不变），
    因为色度噪声主要表现为 R/B 通道的异常波动。
    """

    def __init__(self, img, bayer_pattern, thres, gain, clip):
        """
        初始化 CNF 模块。

        参数：
            img:           输入的 Bayer RAW 图像（numpy 数组）
            bayer_pattern: Bayer 排列，支持 'rggb', 'bggr', 'gbrg', 'grbg'
            thres:         色度噪声检测阈值（R/B 偏离 G 的程度）
            gain:          四个通道的白平衡增益 [r_gain, gr_gain, gb_gain, b_gain]
            clip:          输出像素值的裁剪上限
        """
        self.img = img
        self.bayer_pattern = bayer_pattern
        self.thres = thres
        self.gain = gain
        self.clip = clip

    def padding(self):
        """
        边界填充：用镜像反射模式向外扩展 4 个像素。
        CNF 使用 9×9 邻域（4 像素半径），所以需要 4 像素填充。
        """
        img_pad = np.pad(self.img, ((4, 4), (4, 4)), 'reflect')
        return img_pad

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def cnc(self, is_color, center, avgG, avgC1, avgC2):
        """
        色度噪声修正 (Chroma Noise Correction)。

        基于以下因素确定修正量：
          1. dampFactor: 由白平衡增益决定（增益越高 → 噪声被放大越多 → 修正更保守）
          2. signalMeter: 亮度信号水平（暗部需要更强修正）
          3. fade1: 亮度信号 fade（暗部更强，亮部几乎不修正）
          4. fade2: 同色均值 fade（低信号时更强）

        修正策略：
          chromaCorrected = max(avgG, avgC2) + dampFactor × signalGap
          然后用 fadeTot 在原始值和修正值之间混合。

        参数：
            is_color: 颜色类型 'r' 或 'b'
            center:   当前像素的原始值
            avgG:     邻域 G 通道均值（亮度基准）
            avgC1:    邻域同色通道均值（R 的邻域 R 均值）
            avgC2:    邻域异色通道均值（R 的邻域 B 均值）

        返回：
            修正后的像素值
        """
        # --- 解包白平衡增益 ---
        r_gain = self.gain[0]
        gr_gain = self.gain[1]
        gb_gain = self.gain[2]
        b_gain = self.gain[3]

        # --- 根据白平衡增益确定 dampFactor（衰减因子）---
        # 增益越高，噪声放大越严重，修正应越保守（dampFactor 越小）
        dampFactor = 1.0
        if is_color == 'r':
            if r_gain <= 1.0:
                dampFactor = 1.0
            elif r_gain > 1.0 and r_gain <= 1.2:
                dampFactor = 0.5
            elif r_gain > 1.2:
                dampFactor = 0.3
        elif is_color == 'b':
            if b_gain <= 1.0:
                dampFactor = 1.0
            elif b_gain > 1.0 and b_gain <= 1.2:
                dampFactor = 0.5
            elif b_gain > 1.2:
                dampFactor = 0.3

        # --- 计算修正目标值 ---
        # signalGap: 当前像素值高出 max(avgG, avgC2) 的量
        signalGap = center - max(avgG, avgC2)
        # chromaCorrected = 基准值 + 衰减后的差值
        chromaCorrected = max(avgG, avgC2) + dampFactor * signalGap

        # --- 计算亮度信号水平 (signalMeter) ---
        # 使用 ITU-R BT.601 亮度系数估算亮度
        if is_color == 'r':
            # R 位置：(R, G, B) ≈ (avgC1, avgG, avgC2)
            signalMeter = 0.299 * avgC1 + 0.587 * avgG + 0.114 * avgC2
        elif is_color == 'b':
            # B 位置：(R, G, B) ≈ (avgC2, avgG, avgC1)
            signalMeter = 0.299 * avgC2 + 0.587 * avgG + 0.114 * avgC1

        # --- fade1: 亮度信号衰减 ---
        # 亮度越高，色度噪声越不明显 → 修正力度越小
        if signalMeter <= 30:
            fade1 = 1.0      # 最暗 → 最强修正
        elif signalMeter > 30 and signalMeter <= 50:
            fade1 = 0.9
        elif signalMeter > 50 and signalMeter <= 70:
            fade1 = 0.8
        elif signalMeter > 70 and signalMeter <= 100:
            fade1 = 0.7
        elif signalMeter > 100 and signalMeter <= 150:
            fade1 = 0.6
        elif signalMeter > 150 and signalMeter <= 200:
            fade1 = 0.3
        elif signalMeter > 200 and signalMeter <= 250:
            fade1 = 0.1
        else:
            fade1 = 0         # 最亮 → 不修正

        # --- fade2: 同色均值衰减 ---
        # 同色均值越低，信号越弱 → 修正力度越大
        if avgC1 <= 30:
            fade2 = 1.0
        elif avgC1 > 30 and avgC1 <= 50:
            fade2 = 0.9
        elif avgC1 > 50 and avgC1 <= 70:
            fade2 = 0.8
        elif avgC1 > 70 and avgC1 <= 100:
            fade2 = 0.6
        elif avgC1 > 100 and avgC1 <= 150:
            fade2 = 0.5
        elif avgC1 > 150 and avgC1 <= 200:
            fade2 = 0.3
        elif avgC1 > 200:
            fade2 = 0

        # --- 混合原始值和修正值 ---
        fadeTot = fade1 * fade2
        center_out = (1 - fadeTot) * center + fadeTot * chromaCorrected
        return center_out

    def cnd(self, y, x, img):
        """
        色度噪声检测 (Chroma Noise Detection)。

        在 9×9 邻域（4 像素半径）内统计三类像素的均值：
          - avgG:  G 位置（Gr 和 Gb）的均值，作为亮度基准
          - avgC1: 同色位置均值（检测 R 时统计 R 位置，检测 B 时统计 B 位置）
          - avgC2: 异色位置均值

        判断条件：
          如果 center > avgG + thres AND center > avgC2 + thres，说明当前像素
          在两个方向上都显著偏高，可能是色度噪声。
          额外检查 avgC1 > avgG + thres AND avgC1 > avgC2 + thres，
          确认识别为同色通道的异常而非真实边缘。

        参数：
            y, x: 当前像素在填充后图像中的坐标
            img:  填充后的 Bayer RAW 图像

        返回：
            (is_noise, avgG, avgC1, avgC2): 是否为噪声、三个基准均值
        """
        avgG = 0
        avgC1 = 0
        avgC2 = 0
        is_noise = 0

        # 遍历 9×9 邻域（半径 4）
        for i in range(y - 4, y + 4, 1):
            for j in range(x - 4, x + 4, 1):
                # 根据 Bayer 位置分类像素
                if i % 2 == 1 and j % 2 == 0:
                    avgG = avgG + img[i, j]       # Gr 位置 → G 类
                elif i % 2 == 0 and j % 2 == 1:
                    avgG = avgG + img[i, j]       # Gb 位置 → G 类
                elif i % 2 == 0 and j % 2 == 0:
                    avgC1 = avgC1 + img[i, j]     # (偶, 偶) 位置 → C1 类
                elif i % 2 == 1 and j % 2 == 1:
                    avgC2 = avgC2 + img[i, j]     # (奇, 奇) 位置 → C2 类

        # 归一化：9×9=81 像素中，G 占 40 个，C1 占 25 个，C2 占 16 个
        # （C1 和 C2 的数量取决于 Bayer 模式，此处按 RGGB 硬编码）
        avgG = avgG / 40
        avgC1 = avgC1 / 25
        avgC2 = avgC2 / 16

        center = img[y, x]

        # 色度噪声判定条件
        if center > avgG + self.thres and center > avgC2 + self.thres:
            if avgC1 > avgG + self.thres and avgC1 > avgC2 + self.thres:
                is_noise = 1   # 确认为色度噪声
            else:
                is_noise = 0
        else:
            is_noise = 0

        return is_noise, avgG, avgC1, avgC2

    def cnf(self, is_color, y, x, img):
        """
        色度噪声滤波入口：先检测，如果确认为噪声则修正，否则保留原值。

        参数：
            is_color: 颜色类型 'r' 或 'b'
            y, x:     当前像素坐标
            img:      填充后的图像

        返回：
            处理后的像素值
        """
        is_noise, avgG, avgC1, avgC2 = self.cnd(y, x, img)
        if is_noise:
            pix_out = self.cnc(is_color, img[y, x], avgG, avgC1, avgC2)
        else:
            pix_out = img[y, x]  # 非噪声像素保持原值
        return pix_out

    def execute(self):
        """
        执行色度噪声滤波。

        遍历每个 2×2 Bayer block，对 R 和 B 位置调用 CNF 检测和修正，
        G 位置（Gr/Gb）保持不变（G 通道噪声在亮度域处理，不在此模块负责）。

        返回：
            CNF 处理后的 RAW 图像
        """
        img_pad = self.padding()
        raw_h = self.img.shape[0]
        raw_w = self.img.shape[1]

        # 创建输出数组
        cnf_img = np.empty((raw_h, raw_w), np.uint16)

        # 遍历 2×2 Bayer block
        for y in range(0, img_pad.shape[0] - 8 - 1, 2):
            for x in range(0, img_pad.shape[1] - 8 - 1, 2):

                if self.bayer_pattern == 'rggb':
                    r = img_pad[y + 4, x + 4]     # 中心 R 像素
                    gr = img_pad[y + 4, x + 5]    # 中心 Gr 像素
                    gb = img_pad[y + 5, x + 4]    # 中心 Gb 像素
                    b = img_pad[y + 5, x + 5]     # 中心 B 像素

                    cnf_img[y, x] = self.cnf('r', y + 4, x + 4, img_pad)     # R 位置做色度噪声检测
                    cnf_img[y, x + 1] = gr                                    # Gr 不变
                    cnf_img[y + 1, x] = gb                                    # Gb 不变
                    cnf_img[y + 1, x + 1] = self.cnf('b', y + 5, x + 5, img_pad)  # B 位置做色度噪声检测

                elif self.bayer_pattern == 'bggr':
                    b = img_pad[y + 4, x + 4]
                    gb = img_pad[y + 4, x + 5]
                    gr = img_pad[y + 5, x + 4]
                    r = img_pad[y + 5, x + 5]

                    cnf_img[y, x] = self.cnf('b', y + 4, x + 4, img_pad)
                    cnf_img[y, x + 1] = gb
                    cnf_img[y + 1, x] = gr
                    cnf_img[y + 1, x + 1] = self.cnf('r', y + 5, x + 5, img_pad)

                elif self.bayer_pattern == 'gbrg':
                    gb = img_pad[y + 4, x + 4]
                    b = img_pad[y + 4, x + 5]
                    r = img_pad[y + 5, x + 4]
                    gr = img_pad[y + 5, x + 5]

                    cnf_img[y, x] = gb                                          # Gb 不变
                    cnf_img[y, x + 1] = self.cnf('b', y + 4, x + 5, img_pad)  # B 位置检测
                    cnf_img[y + 1, x] = self.cnf('r', y + 5, x + 4, img_pad)  # R 位置检测
                    cnf_img[y + 1, x + 1] = gr                                 # Gr 不变

                elif self.bayer_pattern == 'grbg':
                    gr = img_pad[y + 4, x + 4]
                    r = img_pad[y + 4, x + 5]
                    b = img_pad[y + 5, x + 2]
                    gb = img_pad[y + 5, x + 5]

                    cnf_img[y, x, :] = gr                                       # Gr 不变
                    cnf_img[y, x + 1, :] = self.cnf('r', y + 4, x + 5, img_pad)  # R 位置检测
                    cnf_img[y + 1, x, :] = self.cnf('b', y + 5, x + 4, img_pad)  # B 位置检测
                    cnf_img[y + 1, x + 1, :] = gb                               # Gb 不变

        self.img = cnf_img
        return self.clipping()
