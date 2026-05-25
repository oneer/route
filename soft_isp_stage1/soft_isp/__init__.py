"""Soft-ISP stage 1 学习包。

本包实现了 ISP（Image Signal Processor）管线的核心模块，按处理顺序排列：
    - stats:      统计工具函数（Bayer 模式推断、数组统计、通道拆分）
    - blc:        黑电平校正（Black Level Correction）
    - dpc:        坏点校正（Defect Pixel Correction）
    - lsc:        镜头阴影校正（Lens Shading Correction）
    - demosaic:   去马赛克（Demosaic），Bayer → RGB
    - awb:        自动白平衡（Auto White Balance）
    - ccm:        颜色校正矩阵（Color Correction Matrix）
    - tone:       Gamma 校正与色调映射
    - orientation: 显示方向处理（旋转/翻转）
"""
