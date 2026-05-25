"""
data 子包 — 数据集与图像退化模块。

包含：
    - degradations.py:      图像退化函数（当前仅 Gaussian 加噪，后续可扩展模糊、下采样、JPEG 压缩等）
    - toy_rgb_dataset.py:   合成 RGB 去噪数据集（ToyRGBDenoiseDataset），
                           用程序生成的渐变/纹理/矩形块作为 clean target，
                           加噪后形成 clean/noisy 配对数据，用于验证训练管线。
"""
