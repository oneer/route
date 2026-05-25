"""
ai_isp — Stage 2 AI-ISP 训练实验包。

本包实现了一个简化的深度学习 ISP（Image Signal Processor）训练框架，
用于在合成数据上验证"用 CNN 做 ISP 降噪/增强"的可行性。

核心组件：
    - data/:        合成数据集与图像退化（加噪）模块
    - models/:      三种 CNN backbone（TinyCNN / DnCNN / UNet）
    - metrics/:     PSNR 与 SSIM 评估指标
    - engine/:      训练循环、验证、日志与 checkpoint 管理
    - utils/:       随机种子设置与可视化工具

本包是 Stage 2 的起点：从 Stage 1 的传统 ISP 管线转向用神经网络
端到端处理图像增强任务（目前从 RGB 降噪开始）。
"""
