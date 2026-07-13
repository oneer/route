# 独立结项任务

完成 Week 0-12 后，从一个空目录实现最小 paired RGB denoise 项目，禁止复制
`stage2_ai_isp/ai_isp/`。允许查 PyTorch/ONNX 官方 API，但第一次验收前不对照本仓库正式实现。

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

## 四个里程碑

### M1：数据与最小前向

- 完成 paired Dataset、同步 crop 和 train/validation/test 三分；
- 用1～5张图做 overfit，确认模型、loss 和反向传播能够工作；
- 写数据配对、shape、值域、确定性和 split 隔离测试。

### M2：训练与恢复

- 完成 residual DnCNN、三种 loss、last/best checkpoint 和断点续训；
- 先测 noisy input baseline，再训练模型；
- 证明 resume 后 step 和 metrics 是连续的。

### M3：评估与诊断

- 冻结设计后只评估一次 test；
- 生成 PSNR、标准窗口 SSIM、triplet 和 error map；
- 完成一个单变量消融，并写出“证明什么、不证明什么”。

### M4：导出与报告

- 导出 ONNX，保存 checker 和 PyTorch/ONNX float 对齐证据；
- 报告环境、config、seed、checkpoint、数据边界和失败案例；
- 确认至少8个自动化测试全部通过。

验收标准：

- 模型 test PSNR 超过 noisy input baseline；
- 同 seed 重跑结果误差可解释；
- 修改 residual 开关后测试能够捕获 shape/语义问题；
- 报告明确写出数据、指标和 pseudo RAW 的边界；
- 可以在不看现有项目代码的情况下，白板讲清执行流程。

## 提交清单

```text
[ ] README 含全新环境复现命令
[ ] config 固定数据、模型、loss、seed 和输出目录
[ ] train/val/test manifest 与泄漏检查
[ ] noisy baseline、冻结理由和一次性 test 结果
[ ] metrics.csv、checkpoint、triplet、error map
[ ] 至少 8 个自动化测试及测试输出
[ ] ONNX checker 与 float 对齐 JSON
[ ] 单变量消融、failure case 和结果边界
```

评分细则见 [`acceptance_rubric.md`](acceptance_rubric.md)。
