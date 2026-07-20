# Qualcomm 3083325 Camera Systems Capstone

## 1. 问题与目标

把四阶段学习产物整理为可重复验收的 Camera Systems 证据链；未实测项目保持 `not_run`。

## 2. Camera 数据流和系统架构

Capstone 只校验 manifest、消费各 Stage 输出并生成证据矩阵，不复制 ISP、ML、C++ 或 CUDA 算法。

## 3. 数据与拍摄协议

当前登记并校验了 14 public DNG sample(s); 3 controlled tuning decisions; clipping, ROI SNR, DR and MTF proxies。自采设备、镜头、曝光、场景、ROI 和计算摄影状态的协议见 `reports/capture_protocol.md`。

## 4. IQ 评价系统

Stage 1 的 manifest IQ 与受控调参 sweep 已接入。曝光统计、clipping、自然图 ROI SNR、动态范围和 MTF50 都是 proxy；完整数值和边界见 `reports/iq_system_report.md`。

## 5. Traditional vs ML tuning

10 frozen public SIDD sRGB sample(s), 30 method rows; DnCNN - bilateral PSNR = 4.043 dB。这是真实公开配对 sRGB 的同输入比较，不等同于 Sensor RAW AI-ISP 或自采 Camera 调参。

## 6. 多摄标定与融合

Synthetic C++/OpenCV homography max difference 3.246e-07; NumPy/C++ fusion max error 2.384e-07。实拍双摄对仍为 `not_run`，不声称硬件同步。

## 7. C++/GPU 系统优化

14/14 CTest passed; synthetic calibration/fusion aligned; fusion p50/p90 = 17.558/18.795 ms at 1080P。ORT CUDA I/O Binding inference p50/p90=3.296/3.754 ms; e2e p50/p90=10.477/11.047 ms; RAM=614.61 MiB; copies=1 H2D / 0 intermediate D2H / 1 final D2H。

## 8. 质量、延迟和内存权衡

Stage 4 已汇总质量、延迟、RAM 与拷贝次数。WDDM 未暴露每进程 VRAM，因此该字段保持空值；历史 backend 中未测的内存/拷贝字段也不作推断。

## 9. 失败案例

受控 IQ sweep、Stage 2 artifact 分类和 Stage 3 几何/运动/低纹理诊断均已记录。剩余证据缺口是标准色卡/斜边、自采 Sensor RAW、实拍双摄和 GPU 自定义预处理直连时间线。

## 10. 已知边界

本项目不代表商业量产、高通内部平台、Snapdragon/NPU、移动端功耗或硬件同步经验。

## 11. Job ID 3083325 能力证据表

| JD requirement | Status | Result | Boundary |
|---|---|---|---|
| IQ evaluation | verified_proxy | 14 public DNG sample(s); 3 controlled tuning decisions; clipping, ROI SNR, DR and MTF proxies | Not self-captured lab IQ; no ColorChecker or standard slanted-edge chart. |
| Traditional vs ML camera-scene tuning | verified_public_rgb | 10 frozen public SIDD sRGB sample(s), 30 method rows; DnCNN - bilateral PSNR = 4.043 dB | Paired public rendered sRGB restoration, not self-captured scenes or Sensor RAW AI-ISP. |
| Multi-camera calibration and fusion | verified_synthetic | Synthetic C++/OpenCV homography max difference 3.246e-07; NumPy/C++ fusion max error 2.384e-07 | Synthetic planar geometry/fusion only; captured camera pair remains not_run, with no hardware synchronization claim. |
| System optimization | verified_partial | ORT CUDA I/O Binding inference p50/p90=3.296/3.754 ms; e2e p50/p90=10.477/11.047 ms; RAM=614.61 MiB; copies=1 H2D / 0 intermediate D2H / 1 final D2H | Input/output tensors are device-bound, but preprocess remains CPU NumPy plus one H2D; per-process VRAM and Nsight timeline are unavailable. |
| C++ system software | verified_learning | 14/14 CTest passed; synthetic calibration/fusion aligned; fusion p50/p90 = 17.558/18.795 ms at 1080P | Learning-oriented library, not a production realtime ISP. |

## 12. 最小复现命令

```powershell
python camera_system_capstone/scripts/06_run_capstone.py --cpu-only
python -m unittest discover -s camera_system_capstone/tests -v
```

## 13. 面试就绪结论

这套 Capstone 足以支撑“请完整介绍一个 Camera/ISP 项目”“如何评价 IQ”“如何定位多摄接缝”“为什么 kernel 快但系统不快”等项目深挖。回答时必须区分三层：

| 层级 | 可以怎样说 | 不能怎样说 |
|---|---|---|
| 已验证 | 在所列数据、环境和命令下给出指标与 failure | 把 public/synthetic/desktop 外推为自采/量产/Snapdragon |
| 概念就绪 | 能画 3A、CAMX/CHI、QNN/HTP、PPA 的设计与验收图 | 声称已接入平台或解决真实客户问题 |
| 待执行 | 能列出自采 IQ、实拍双摄、arm64/HTP、功耗实验 | 把计划项写入简历成果 |

当前强项是证据可追溯、错误边界和跨阶段系统分析；主要差距是自采标准 IQ、连续帧 3A/TNR、实拍同步多摄、ARM/NEON/HVX、Snapdragon QAIRT/QNN/HTP、移动 PPA 及商业客户闭环。完整能力矩阵、十二道闭卷题和优先级见[高通 3083325 定向提升报告](../../study-roadmap/高通3083325-Camera-ISP-Algorithm-System-Engineer定向提升报告.md#十四2026-07-19-面试就绪审计与二次补强)。

推荐的 90 秒开场：

> 我把项目拆成传统 ISP/IQ、ML restoration、C++/多摄和部署系统四层，再用 Capstone 固定 manifest、hash、correctness、quality 和 latency 口径。当前公开 DNG/SIDD、synthetic 多摄与桌面 GPU 证据可复现；我能解释参数、失败和系统 trade-off，同时明确自采标准 IQ、真实同步双摄、Snapdragon HTP 和移动功耗仍需重测。我的重点不是声称量产经验，而是展示拿到新平台后如何建立 golden、定位第一发散点并把问题转成可证伪实验。

## 14. 六步项目回答模板

```text
Claim -> Evidence -> Mechanism -> Trade-off -> Boundary -> Next experiment
```

面试官追问任意数字时，都应能回到 evidence matrix 中的文件、命令、环境和边界；追问未完成能力时，给出最小验证顺序，而不是用概念替代实测。
