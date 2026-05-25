"""
engine 子包 — 训练与验证引擎。

包含：
    - train.py:      训练主循环（配置驱动的训练入口）
    - validate.py:   验证循环（计算 PSNR/SSIM 并收集首帧可视化）
    - checkpoint.py: 模型保存/恢复（checkpoint）
    - logger.py:     CSV 日志与 TensorBoard 日志（可选）
"""
