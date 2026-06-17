"""
metrics 子包 — 图像质量评估指标。

包含：
    - batch_psnr:  批量 PSNR（Peak Signal-to-Noise Ratio，峰值信噪比）
    - batch_ssim:  批量 SSIM（Structural Similarity Index Measure，结构相似度）

两者均在验证阶段使用，默认对 [0, 1] 范围的图像计算。
"""

from ai_isp.metrics.psnr_ssim import batch_psnr, batch_ssim
