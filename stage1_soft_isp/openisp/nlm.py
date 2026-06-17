#!/usr/bin/python
# ============================================================================
# nlm.py — 非局部均值去噪（Non-Local Means Denoising）
# ============================================================================
# 用途：
#   对图像进行高质量去噪。与普通局部滤波（如高斯滤波、双边滤波）不同，
#   NLM 利用整幅图像中相似块（patch）的加权平均来估计每个像素的真实值。
#
# 原理（Non-Local Means）：
#   核心思想：图像中相距很远的区域可能包含相似的纹理/结构。
#   与其只用邻域像素做平均，不如在整个搜索窗口中寻找相似的 patch，
#   用这些相似 patch 的中心像素加权平均来估计当前像素。
#
#   对每个像素：
#     1. 在搜索窗口（Ds 半径）内遍历所有可能的参考像素
#     2. 以参考像素为中心的邻域窗口（ds 半径）与以当前像素为中心的邻域窗口做比较
#     3. 计算两个邻域块的加权欧氏距离 → d
#     4. 权重 w = exp(-d / h²)，h 控制相似度衰减速度
#     5. 所有参考像素中心值的加权平均 = 去噪结果
#
# 参数说明：
#   ds (neighbour window): 邻域窗口半径，定义 patch 大小（实际窗口 2×ds+1）
#   Ds (search window):    搜索窗口半径（实际窗口 2×Ds+1）
#   h (filtering param):   滤波强度参数，越大去噪越强但细节损失也越多
# ============================================================================

import numpy as np


class NLM:
    """
    非局部均值去噪 (Non-Local Means Denoising)

    利用全局相似块加权平均实现保边去噪。
    相比局部滤波，NLM 能更好地保留重复纹理和结构。
    """

    def __init__(self, img, ds, Ds, h, clip):
        """
        初始化 NLM 模块。

        参数：
            img:  输入图像（numpy 数组）
            ds:   邻域窗口半径（neighbour window size - 1）/ 2
                 实际邻域窗口大小为 2×ds+1
            Ds:   搜索窗口半径（search window size - 1）/ 2
                 实际搜索窗口大小为 2×Ds+1
            h:    滤波强度参数（越大去噪越强）
            clip: 输出像素值的裁剪上限
        """
        self.img = img
        self.ds = ds
        self.Ds = Ds
        self.h = h
        self.clip = clip

    def padding(self):
        """
        边界填充：以搜索窗口半径 Ds 用镜像反射模式扩展边界，
        保证搜索窗口在图像边缘也能正常运作。
        """
        img_pad = np.pad(self.img, (self.Ds, self.Ds), 'reflect')
        return img_pad

    def clipping(self):
        """
        限幅裁剪：将图像像素值限制在 [0, clip] 范围内。
        """
        np.clip(self.img, 0, self.clip, out=self.img)
        return self.img

    def calWeights(self, img, kernel, y, x):
        """
        计算搜索窗口内所有参考像素的权重和加权平均值。

        对搜索窗口内每个有效参考位置：
          1. 提取以该位置为中心的邻域块 (neighbour_w)
          2. 提取以当前像素为中心的邻域块 (center_w)
          3. 计算两个邻域块的加权欧氏距离平方
             dist = Σ kernel × (neighbour_w - center_w)²
          4. 权重 w = exp(-dist / h²)
          5. 累加加权和 sweight 和加权像素值 average

        参数：
            img:    填充后的图像
            kernel: 邻域块的权重核（通常为均匀核）
            y, x:   当前像素在填充后图像中的坐标

        返回：
            (sweight, average, wmax): 权重总和、加权像素值总和、最大权重
        """
        wmax = 0       # 记录最大权重（用于后续处理）
        sweight = 0    # 所有权重之和
        average = 0    # 加权像素值之和

        # 遍历搜索窗口内的所有参考像素
        # 搜索窗口的有效范围 = (2*Ds+1) - (2*ds+1)（考虑邻域窗口的边界约束）
        for j in range(2 * self.Ds + 1 - 2 * self.ds - 1):
            for i in range(2 * self.Ds + 1 - 2 * self.ds - 1):
                # 当前参考像素的坐标
                start_y = y - self.Ds + self.ds + j
                start_x = x - self.Ds + self.ds + i

                # 提取以参考像素为中心的邻域块
                neighbour_w = img[start_y - self.ds:start_y + self.ds + 1, start_x - self.ds:start_x + self.ds + 1]
                # 提取以当前像素为中心的邻域块
                center_w = img[y - self.ds:y + self.ds + 1, x - self.ds:x + self.ds + 1]

                # 排除自身比较（自身距离为 0，权重最大）
                if j != y or i != x:
                    # 计算两个邻域块的加权欧氏距离
                    sub = np.subtract(neighbour_w, center_w)  # 逐元素差值
                    dist = np.sum(np.multiply(kernel, np.multiply(sub, sub)))  # kernel × diff² 的和

                    # 计算权重：w = exp(-dist / h²)
                    # 注释提示可替换为 LUT 加速（实际未实现）
                    w = np.exp(-dist / pow(self.h, 2))

                    # 跟踪最大权重
                    if w > wmax:
                        wmax = w

                    # 累加
                    sweight = sweight + w
                    average = average + w * img[start_y, start_x]

        return sweight, average, wmax

    def execute(self):
        """
        执行非局部均值去噪。

        对每个像素：
          1. 在搜索窗口中计算所有参考块的权重
          2. 将自身以最大权重加入（确保自身贡献不低于最相似的其他块）
          3. 加权平均 = (average + wmax × center) / (sweight + wmax)

        返回：
            NLM 去噪后的图像
        """
        # 边界填充并转换为 uint16
        img_pad = self.padding()
        img_pad = img_pad.astype(np.uint16)
        raw_h = self.img.shape[0]
        raw_w = self.img.shape[1]

        # 创建输出数组
        nlm_img = np.empty((raw_h, raw_w), np.uint16)

        # 邻域块权重核（均匀核，权重和为 1）
        # 实际为全 1 核除以元素数 → 每个位置权重相等
        kernel = np.ones((2 * self.ds + 1, 2 * self.ds + 1)) / pow(2 * self.ds + 1, 2)

        # 遍历每个像素
        for y in range(img_pad.shape[0] - 2 * self.Ds):
            for x in range(img_pad.shape[1] - 2 * self.Ds):
                # 当前像素在填充后图像中的坐标
                center_y = y + self.Ds
                center_x = x + self.Ds

                # 计算搜索窗口内的权重和
                sweight, average, wmax = self.calWeights(img_pad, kernel, center_y, center_x)

                # 将自身以最大权重加入（保证自身贡献至少等于最相似的其他块）
                average = average + wmax * img_pad[center_y, center_x]
                sweight = sweight + wmax

                # 加权平均
                nlm_img[y, x] = average / sweight

        self.img = nlm_img
        return self.clipping()
