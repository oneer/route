# 阶段四调试练习与 Capstone

## 调试练习

每个练习都要先制造错误，再用 raw tensor、error map 和 latency 日志定位。

1. RGB/BGR：交换通道，观察偏色；修复标准是 raw input tensor 与 Python reference 一致。
2. NCHW/NHWC：取消 transpose；记录 shape 和首个像素三通道值。
3. `[0,1]`/`[0,255]`：移除 `/255`；解释激活范围为何失真。
4. PNG 掩盖误差：给 float output 加 `1e-4`，证明保存成 uint8 后可能仍相同。
5. FP16 overflow：构造高幅值 tensor；检查非有限值并定位敏感层。
6. dynamic profile：让输入超出 TensorRT profile；区分 parser、build 和 runtime shape 错误。
7. 虚假 latency：移除 GPU 同步；比较 host enqueue 与真实完成时间。
8. calibration 偏差：只用亮图校准，再评价暗图；比较最差样本和 error map。

## 掌握标准

- 能先确认协议和输入，再检查模型与后端。
- 能解释 max/mean/RMSE、alignment PSNR 与对 clean GT 的 PSNR/SSIM不是同一指标。
- 能区分 session、engine compute、copy 和包含文件 I/O 的端到端 latency。
- 能说明 INT8 阈值是本项目门槛，不是行业统一结论。

## Capstone

从固定 checkpoint 独立完成：

1. 生成 checkpoint hash 和固定 manifest。
2. 导出 ONNX，运行 checker、shape inspection 和 ORT Python 对齐。
3. 完成 ORT C++ raw float tensor 对齐，禁止只比 PNG。
4. 选择 FP16 或 INT8，给出数值误差、PSNR/SSIM drop、最差 crop/error map。
5. 拆分 pre/H2D/infer/D2H/post/save，并注明 warmup、runs、同步与 I/O。
6. 写出一项拒绝上线的失败条件。

交付验收：`correctness_matrix.csv`、`latency_matrix.csv`、环境记录、失败案例和未复验边界缺一不可。
