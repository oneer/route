#!/usr/bin/python
import numpy as np
from scipy.ndimage import correlate

class AAF:
    """
    抗混叠滤波器 (Anti-Aliasing Filter)

    在 Bayer RAW 域对同色通道做低通滤波，抑制高频分量，
    防止后续去马赛克 (CFA 插值) 时产生伪色、拉链效应等混叠伪影。

    kernel 设计中所有 0 位置恰好对应 Bayer 阵列中的异色像素，
    因此这个滤波仅在「同色通道」内部做加权平均，不会混合 R/G/B。
    """

    def __init__(self, img):
        """
        参数：
        - img: 已做完 BLC 的 RAW 图像（numpy 数组，Bayer 格式）
        """
        self.img = img

    def padding(self):
        """
        边界填充：用镜像反射 (reflect) 模式向外扩展 2 个像素，
        保证 5×5 卷积核在图像边缘也能正常计算。
        """
        img_pad = np.pad(self.img, (2, 2), 'reflect')
        return img_pad

    def execute(self):
        """
        执行抗混叠滤波。

        5×5 kernel 的结构与含义（已归一化，除以 16）：

            [1  0  1  0  1]       ─ 对角同色像素，权重各 1/16
            [0  0  0  0  0]       ─ 0 = 异色像素，不参与计算
            [1  0  8  0  1]       ─ 中心权重 8/16 = 0.5（保真）
            [0  0  0  0  0]       ─ 0 = 异色像素，不参与计算
            [1  0  1  0  1]       ─ 对角同色像素，权重各 1/16

        Bayer 阵列中同色像素间隔为 2（隔行隔列），所以：
        - kernel 中取值的 9 个位置均为同一颜色通道（R/G/B 之一）
        - 四周 8 个邻居各贡献 6.25%，中心像素贡献 50%
        - 这是一个温和的低通滤波：主要削弱对角线方向高频，
          水平/垂直方向的高频保留较多（kernel 在行列方向未覆盖相邻同色像素）
        """
        img_pad = self.padding()
        raw_h = self.img.shape[0]
        raw_w = self.img.shape[1]

        # scipy.ndimage.correlate: 将 kernel 与图像做互相关（等价于卷积，只是 kernel 不翻转）
        # 由于 kernel 关于中心对称，这里互相关与卷积结果相同
        aaf_img = correlate(self.img, np.array([[1, 0, 1, 0, 1],
                                                [0, 0, 0, 0, 0],
                                                [1, 0, 8, 0, 1],
                                                [0, 0, 0, 0, 0],
                                                [1, 0, 1, 0, 1]]) / 16)
        self.img = aaf_img
        return self.img
