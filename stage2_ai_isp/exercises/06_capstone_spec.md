# 独立结项任务

从一个空目录实现最小 paired RGB denoise 项目，禁止复制 `ai_isp/`。

必须包含：

```text
dataset.py
model.py
train.py
evaluate.py
tests/
config.yaml
README.md
```

功能要求：

1. paired noisy/clean Dataset 和同步随机 crop；
2. residual DnCNN；
3. L1、MSE、Charbonnier 三种 loss；
4. train/validation/test 三分；
5. PSNR 和标准窗口 SSIM；
6. last/best checkpoint 和断点续训；
7. triplet 与 error map；
8. 至少 8 个自动化测试；
9. 一个单变量消融；
10. ONNX 导出和 PyTorch/ONNX 输出误差。

验收标准：

- 模型 test PSNR 超过 noisy input baseline；
- 同 seed 重跑结果误差可解释；
- 修改 residual 开关后测试能够捕获 shape/语义问题；
- 报告明确写出数据、指标和 pseudo RAW 的边界；
- 可以在不看现有项目代码的情况下，白板讲清执行流程。

