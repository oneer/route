#!/usr/bin/python
# ============================================================================
# cfa.py — 颜色滤波阵列插值（Color Filter Array Interpolation）
# ============================================================================
# 用途：
#   将单通道 Bayer RAW 图像转换为三通道 RGB 图像（即去马赛克/Demosaic）。
#   这是 ISP 管线中最关键的步骤之一，负责在每个像素位置估计缺失的颜色。
#
# 原理（Malvar 插值法）：
#   Malvar 等人提出的 high-quality linear interpolation 方法，
#   在 bilinear 基础上加入了梯度/拉普拉斯修正项，
#   相比纯 bilinear 插值能更好地抑制伪色（false color）和拉链效应（zipper）。
#
#   核心思想：对于缺失的颜色通道，不仅要看同色邻居的均值，
#   还要利用已知颜色通道的二阶导数信息来修正估计值。
#   例如在 R 位置估计 G 和 B 时：
#     G_hat = bilinear_G + k × Laplacian_R  （用 R 的边缘信息修正 G）
#     B_hat = bilinear_B + k × Laplacian_R  （用 R 的边缘信息修正 B）
# ============================================================================

import numpy as np


class CFA:
    """
    颜色滤波阵列插值 (Color Filter Array Interpolation)

    将 Bayer RAW 图像通过 Malvar 算法插值为完整的三通道 RGB 图像。
    支持四种 Bayer 排列模式：RGGB / BGGR / GBRG / GRBG。
    """

    def __init__(self, img, mode, bayer_pattern, clip):
        """
        初始化 CFA 插值模块。

        参数：
            img:           输入的 Bayer RAW 图像（numpy 数组）
            mode:          插值模式，当前仅支持 'malvar'
            bayer_pattern: Bayer 排列，支持 'rggb', 'bggr', 'gbrg', 'grbg'
            clip:          输出像素值的裁剪上限
        """
        self.img = img
        self.mode = mode
        self.bayer_pattern = bayer_pattern
        self.clip = clip

    def padding(self):
        """
        边界填充：用镜像反射 (reflect) 模式向外扩展 2 个像素，
        保证插值核在图像边缘也能正常计算。
        """
        img_pad = np.pad(self.img, ((2, 2), (2, 2)), 'reflect')
        return img_pad

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def malvar(self, is_color, center, y, x, img):
        """
        Malvar 插值核心算法 —— 在 Bayer RAW 的某个位置估计 R/G/B 三个颜色值。

        根据中心像素的颜色类型（R / Gr / Gb / B），使用不同的公式
        来估计完整的 RGB 三通道值。每个公式都考虑了同色邻居的均值
        和跨通道的拉普拉斯修正项。

        参数：
            is_color: 中心像素的颜色类型，取值为 'r', 'gr', 'gb', 'b'
            center:   中心像素的原始值
            y, x:     中心像素在填充后图像中的坐标
            img:      填充后的 Bayer RAW 图像

        返回：
            [r, g, b] 三通道估计值列表

        公式解读（以 R 位置为例）：
            - G 的估计：使用 R 像素的水平/垂直四个 G 邻居，加上 R 的二阶导数修正
            - B 的估计：使用 R 像素的对角四个 B 邻居，加上 R 的二阶导数修正
            - R 保持为 center（已知值）
            所有结果除以 8 做归一化
        """
        if is_color == 'r':
            # --- 中心像素是 R：已知 R，需要估计 G 和 B ---
            r = center  # R 直接使用已知值

            # G 估计：4 邻域 G 的平均 + 用 R 的二阶导数修正
            # 4×img[y,x] 近似某种平滑，减去水平/垂直邻居做拉普拉斯
            # 最后加上水平/垂直方向上 G 邻居的信息
            g = 4 * img[y, x] - img[y - 2, x] - img[y, x - 2] - img[y + 2, x] - img[y, x + 2] \
                + 2 * (img[y + 1, x] + img[y, x + 1] + img[y - 1, x] + img[y, x - 1])

            # B 估计：4 对角 B 邻居的平均 + 用 R 的二阶导数修正
            b = 6 * img[y, x] - 3 * (img[y - 2, x] + img[y, x - 2] + img[y + 2, x] + img[y, x + 2]) / 2 \
                + 2 * (img[y - 1, x - 1] + img[y - 1, x + 1] + img[y + 1, x - 1] + img[y + 1, x + 1])

            g = g / 8
            b = b / 8

        elif is_color == 'gr':
            # --- 中心像素是 Gr（与 R 同行的 G）：已知 G，需要估计 R 和 B ---
            # R 估计：利用水平方向的 R 邻居和 G 的二阶导数信息
            r = 5 * img[y, x] - img[y, x - 2] - img[y - 1, x - 1] - img[y + 1, x - 1] - img[y - 1, x + 1] - img[y + 1, x + 1] - img[y, x + 2] \
                + (img[y - 2, x] + img[y + 2, x]) / 2 + 4 * (img[y, x - 1] + img[y, x + 1])

            g = center  # G 直接使用已知值

            # B 估计：利用垂直方向的 B 邻居和 G 的二阶导数信息
            b = 5 * img[y, x] - img[y - 2, x] - img[y - 1, x - 1] - img[y - 1, x + 1] - img[y + 2, x] - img[y + 1, x - 1] - img[y + 1, x + 1] \
                + (img[y, x - 2] + img[y, x + 2]) / 2 + 4 * (img[y - 1, x] + img[y + 1, x])

            r = r / 8
            b = b / 8

        elif is_color == 'gb':
            # --- 中心像素是 Gb（与 B 同行的 G）：已知 G，需要估计 R 和 B ---
            # R 估计：利用垂直方向的 R 邻居和 G 的导数信息
            r = 5 * img[y, x] - img[y - 2, x] - img[y - 1, x - 1] - img[y - 1, x + 1] - img[y + 2, x] - img[y + 1, x - 1] - img[y + 1, x + 1] \
                + (img[y, x - 2] + img[y, x + 2]) / 2 + 4 * (img[y - 1, x] + img[y + 1, x])

            g = center  # G 直接使用已知值

            # B 估计：利用水平方向的 B 邻居和 G 的导数信息
            b = 5 * img[y, x] - img[y, x - 2] - img[y - 1, x - 1] - img[y + 1, x - 1] - img[y - 1, x + 1] - img[y + 1, x + 1] - img[y, x + 2] \
                + (img[y - 2, x] + img[y + 2, x]) / 2 + 4 * (img[y, x - 1] + img[y, x + 1])

            r = r / 8
            b = b / 8

        elif is_color == 'b':
            # --- 中心像素是 B：已知 B，需要估计 R 和 G ---
            # R 估计：4 对角 R 邻居的平均 + 用 B 的二阶导数修正
            r = 6 * img[y, x] - 3 * (img[y - 2, x] + img[y, x - 2] + img[y + 2, x] + img[y, x + 2]) / 2 \
                + 2 * (img[y - 1, x - 1] + img[y - 1, x + 1] + img[y + 1, x - 1] + img[y + 1, x + 1])

            # G 估计：4 邻域 G 的平均 + 用 B 的二阶导数修正
            g = 4 * img[y, x] - img[y - 2, x] - img[y, x - 2] - img[y + 2, x] - img[y, x + 2] \
                + 2 * (img[y + 1, x] + img[y, x + 1] + img[y - 1, x] + img[y, x - 1])

            b = center  # B 直接使用已知值

            r = r / 8
            g = g / 8

        return [r, g, b]

    def execute(self):
        """
        执行 CFA 插值，将 Bayer RAW 转换为三通道 RGB 图像。

        处理流程：
            1. 边界填充（2 像素 reflect padding）
            2. 转换为 int32 防止溢出
            3. 按 2×2 Bayer block 遍历（步长为 2）
            4. 对每个 2×2 block 的四个像素分别调用 malvar 插值
            5. 限幅裁剪后输出

        注意：此实现使用嵌套 Python for 循环，性能较低，适合学习验证。

        返回：
            形状为 (H, W, 3) 的 int16 RGB 图像
        """
        # 边界填充并转换为 int32（防止中间计算溢出）
        img_pad = self.padding()
        img_pad = img_pad.astype(np.int32)

        raw_h = self.img.shape[0]  # 图像高度
        raw_w = self.img.shape[1]  # 图像宽度

        # 创建输出 RGB 数组（形状 H×W×3）
        cfa_img = np.empty((raw_h, raw_w, 3), np.int16)

        # 遍历 2×2 Bayer block（步长为 2）
        # 边界减 4 对应 padding 后的有效区域
        for y in range(0, img_pad.shape[0] - 4 - 1, 2):
            for x in range(0, img_pad.shape[1] - 4 - 1, 2):

                if self.bayer_pattern == 'rggb':
                    # 提取 2×2 block 的四个像素值
                    r = img_pad[y + 2, x + 2]    # (偶, 偶) → R
                    gr = img_pad[y + 2, x + 3]   # (偶, 奇) → Gr
                    gb = img_pad[y + 3, x + 2]   # (奇, 偶) → Gb
                    b = img_pad[y + 3, x + 3]    # (奇, 奇) → B

                    if self.mode == 'malvar':
                        # 对 2×2 block 的四个位置分别插值
                        cfa_img[y, x, :] = self.malvar('r', r, y + 2, x + 2, img_pad)      # R 位置插出 RGB
                        cfa_img[y, x + 1, :] = self.malvar('gr', gr, y + 2, x + 3, img_pad)  # Gr 位置插出 RGB
                        cfa_img[y + 1, x, :] = self.malvar('gb', gb, y + 3, x + 2, img_pad)  # Gb 位置插出 RGB
                        cfa_img[y + 1, x + 1, :] = self.malvar('b', b, y + 3, x + 3, img_pad) # B 位置插出 RGB

                elif self.bayer_pattern == 'bggr':
                    b = img_pad[y + 2, x + 2]
                    gb = img_pad[y + 2, x + 3]
                    gr = img_pad[y + 3, x + 2]
                    r = img_pad[y + 3, x + 3]

                    if self.mode == 'malvar':
                        cfa_img[y, x, :] = self.malvar('b', b, y + 2, x + 2, img_pad)
                        cfa_img[y, x + 1, :] = self.malvar('gb', gb, y + 2, x + 3, img_pad)
                        cfa_img[y + 1, x, :] = self.malvar('gr', gr, y + 3, x + 2, img_pad)
                        cfa_img[y + 1, x + 1, :] = self.malvar('r', r, y + 3, x + 3, img_pad)

                elif self.bayer_pattern == 'gbrg':
                    gb = img_pad[y + 2, x + 2]
                    b = img_pad[y + 2, x + 3]
                    r = img_pad[y + 3, x + 2]
                    gr = img_pad[y + 3, x + 3]

                    if self.mode == 'malvar':
                        cfa_img[y, x, :] = self.malvar('gb', gb, y + 2, x + 2, img_pad)
                        cfa_img[y, x + 1, :] = self.malvar('b', b, y + 2, x + 3, img_pad)
                        cfa_img[y + 1, x, :] = self.malvar('r', r, y + 3, x + 2, img_pad)
                        cfa_img[y + 1, x + 1, :] = self.malvar('gr', gr, y + 3, x + 3, img_pad)

                elif self.bayer_pattern == 'grbg':
                    gr = img_pad[y + 2, x + 2]
                    r = img_pad[y + 2, x + 3]
                    b = img_pad[y + 3, x + 2]
                    gb = img_pad[y + 3, x + 3]

                    if self.mode == 'malvar':
                        cfa_img[y, x, :] = self.malvar('gr', gr, y + 2, x + 2, img_pad)
                        cfa_img[y, x + 1, :] = self.malvar('r', r, y + 2, x + 3, img_pad)
                        cfa_img[y + 1, x, :] = self.malvar('b', b, y + 3, x + 2, img_pad)
                        cfa_img[y + 1, x + 1, :] = self.malvar('gb', gb, y + 3, x + 3, img_pad)

        # 保存结果并限幅
        self.img = cfa_img
        return self.clipping()
