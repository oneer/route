# Camera Systems Capstone

这是面向 Qualcomm 3083325 Camera ISP Algorithm System Engineer 的跨阶段验收层，不是“阶段五”。它不复制四阶段算法，只负责固定数据契约、校验资产、汇总已验证指标和暴露未完成项。

## 当前可证明的内容

- Stage 1：14 个公开 DNG 的 IQ proxy，以及 AWB、传统降噪、tone/highlight 三组受控调参决策。
- Stage 2：10 个冻结公开 SIDD sRGB 样本上，传统 bilateral 与 DnCNN 的同输入质量和失败分类对比，标记为 `verified_public_rgb`。
- Stage 3：C++17 14/14 CTest、OpenCV/NumPy 合成对齐和 1080P/4K benchmark，标记为 `verified_synthetic` / 学习型工程证据。
- Stage 4：ORT CUDA I/O Binding 的 device input/output、质量、p50/p90、RAM 和拷贝次数，标记为 `verified_partial`。
- 自采标准 IQ、Sensor RAW ML、多摄实拍/硬件同步、GPU 自定义 preprocess 直接绑定、每进程 VRAM 和移动端功耗仍为 `not_run`。

## 一键运行

在仓库根目录执行：

```powershell
python camera_system_capstone/scripts/06_run_capstone.py --cpu-only
python -m unittest discover -s camera_system_capstone/tests -v
```

该命令先调用 Stage 1/2/4 自己的 CPU-safe 生成脚本，再由 Capstone 校验并汇总；不会复制阶段算法、重训模型或启动 TensorRT。Stage 3 的已验证 Release/CTest 产物以跟踪的 CSV/报告接入。输出位于 `outputs/`，最终岗位报告和 IQ、多摄、系统优化、失败案例四份分报告位于 `reports/`。

## 添加真实数据

1. 按 `reports/capture_protocol.md` 采集并记录数据。
2. 将资产登记到 `data/manifests/capture_manifest.csv`，填写真实 SHA-256。
3. 在 Stage 1/2/3/4 中运行算法，将产物路径登记到对应 manifest。
4. 重新运行 Capstone。缺失字段必须保持为空或 `unknown`，未运行结果必须保持 `not_run`。
