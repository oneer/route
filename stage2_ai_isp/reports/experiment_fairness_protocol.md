# 模型公平对比协议

过去的 DnCNN、UNet、NAFNet-lite 结果属于“已有工程配置的综合表现”，不是只改变模型结构的
严格消融，因为 loss、batch size、steps 和模型宽度并未全部相同。

以后比较架构时使用 `configs/fair_compare_*.yaml`，固定：

```text
SIDD tiny train/val split
seed=42
patch=128
steps=1000
batch=4
loss=mse
learning_rate=0.001
validation interval=200
```

必须同时报告：

| Model | Params | Total train patches | Best val PSNR | Best val SSIM | Test PSNR | Test SSIM | CPU latency |
|---|---:|---:|---:|---:|---:|---:|---:|

如果某模型因内存不能使用相同 batch，应保持总训练 patch 数一致，并在结论中标明例外。
至少使用 3 个 seed 才能讨论结果稳定性；单 seed 只能称为初步观察。

