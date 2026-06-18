# 基础理解题

不要查报告，先用自己的话回答。

1. 为什么 validation 不能调用 `optimizer.step()`？
2. 三层 stride=1、kernel=3 的卷积理论感受野是多少？写出推导。
3. DnCNN 的训练 target 是 clean，为什么还能说它在学习 noise residual？
4. 为什么 output 在训练时不一定 clamp，但验证时通常会 clamp？
5. `best_psnr.pth` 为什么不一定是视觉最好的 checkpoint？
6. 为什么 paired 数据即使文件名相同，也仍可能没有像素对齐？
7. sRGB pseudo RGGB 与真实 sensor RAW 至少有哪四个差异？
8. test 指标出来后又继续调参，为什么会造成评估泄漏？

验收：每题能结合本项目中的一个具体文件或实验说明。

