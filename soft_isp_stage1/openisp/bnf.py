#!/usr/bin/python
# ============================================================================
# bnf.py — 双边噪声滤波（Bilateral Noise Filtering）
# ============================================================================
# 用途：
#   对 Bayer RAW 图像进行保边去噪。使用 5×5 邻域内的像素做加权平均，
#   权重由两部分组成：空间距离权重 (dw) 和像素值差异权重 (rw)。
#
# 原理（双边滤波）：
#   空间权重 (domain weight):  离中心像素越近，权重越大
#   值域权重 (range weight):   与中心像素值越接近，权重越大
#   两个权重相乘得到最终权重，使得平滑的同时能保留边缘。
#
# 实现方式：
#   - dw (distance weights): 5×5 的空间权重核
#   - rw (range weights):    根据像素值差异分级赋予的权重
#   - rthres:                值域差异的分级阈值
#   - 最终权重 = dw × rw，用加权平均替换中心像素
# ============================================================================

import numpy as np


class BNF:
    """
    双边噪声滤波 (Bilateral Noise Filtering)

    在 Bayer RAW 域进行保边去噪。与普通均值滤波不同，
    双边滤波会根据像素值的相似度调整权重，
    使平坦区域充分平滑而边缘区域得到保留。
    """

    def __init__(self, img, dw, rw, rthres, clip):
        """
        初始化 BNF 模块。

        参数：
            img:    输入的 Bayer RAW 图像（numpy 数组）
            dw:     5×5 的空间距离权重核（domain weights）
            rw:     值域权重列表（range weights），长度为 4
                    与 rthres 配合使用，根据像素差异大小分级赋权
            rthres: 值域阈值列表，长度为 3，定义四个分段区间
            clip:   输出像素值的裁剪上限
        """
        self.img = img
        self.dw = dw          # 空间距离权重（5×5 核）
        self.rw = rw          # 值域权重（4 个等级）
        self.rthres = rthres  # 值域差异阈值（3 个分界点）
        self.clip = clip

    def padding(self):
        """
        边界填充：用镜像反射 (reflect) 模式向外扩展 2 个像素，
        保证 5×5 滤波核在图像边缘也能正常计算。
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
        执行双边噪声滤波。

        对每个像素的 5×5 邻域执行以下操作：
            1. 计算邻域内每个像素与中心像素的绝对差值
            2. 根据差值大小查表确定值域权重（rdiff 分级）
            3. 空间权重 × 值域权重 = 最终权重
            4. 加权平均结果替换中心像素值

        注意：此实现使用逐像素 Python 循环（for y/for x），
        性能较低，适合学习和验证算法逻辑。

        返回：
            滤波后的 RAW 图像
        """
        # 边界填充并转换为 uint16
        img_pad = self.padding()
        img_pad = img_pad.astype(np.uint16)
        raw_h = self.img.shape[0]
        raw_w = self.img.shape[1]

        # 创建输出数组
        bnf_img = np.empty((raw_h, raw_w), np.uint16)

        # 存储 5×5 邻域内各像素的值域权重
        rdiff = np.zeros((5, 5), dtype='uint16')

        # 逐像素处理（注意：嵌套循环性能较低）
        for y in range(img_pad.shape[0] - 4):
            for x in range(img_pad.shape[1] - 4):
                # 打印处理进度（调试用）
                print("[x,y]:[" + str(x) + ',' + str(y) + ']')

                # --- 计算值域权重 ---
                for i in range(5):
                    for j in range(5):
                        # 计算邻域像素与中心像素 (y+2, x+2) 的绝对差值
                        rdiff[i, j] = abs(img_pad[y + i, x + j].astype(int) - img_pad[y + 2, x + 2].astype(int))

                        # 根据差值大小分级赋权（四个等级）
                        if rdiff[i, j] >= self.rthres[0]:
                            rdiff[i, j] = self.rw[0]    # 差异最大 → 最小权重
                        elif rdiff[i, j] < self.rthres[0] and rdiff[i, j] >= self.rthres[1]:
                            rdiff[i, j] = self.rw[1]
                        elif rdiff[i, j] < self.rthres[1] and rdiff[i, j] >= self.rthres[2]:
                            rdiff[i, j] = self.rw[2]
                        elif rdiff[i, j] < self.rthres[2]:
                            rdiff[i, j] = self.rw[3]    # 差异最小 → 最大权重

                # --- 计算最终权重 = 空间权重 × 值域权重 ---
                weights = np.multiply(rdiff, self.dw)

                # --- 加权平均 ---
                # np.multiply(img_pad[y:y+5, x:x+5], weights) → 邻域像素 × 权重
                # np.sum(weights) → 权重和（归一化因子）
                bnf_img[y, x] = np.sum(np.multiply(img_pad[y:y + 5, x:x + 5], weights[:, :])) / np.sum(weights)

        self.img = bnf_img
        return self.clipping()
