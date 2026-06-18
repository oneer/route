"""
data 子包 — 数据集与图像退化模块。

包含：
    - degradations.py:      Gaussian 与简化 shot/read noise
    - toy_rgb_dataset.py:   合成 RGB 去噪数据集（ToyRGBDenoiseDataset），
                           用程序生成的渐变/纹理/矩形块作为 clean target，
                           加噪后形成 clean/noisy 配对数据，用于验证训练管线。
    - paired_image_dataset.py: 真实 paired RGB 与同步 crop/augmentation
    - pseudo_raw.py:        sRGB 到 pseudo RGGB 的受控 shape bridge
"""
