# 高通 3083325 Camera ISP Algorithm System Engineer 定向提升报告

> 适用仓库：`route`
>
> 目标岗位：Qualcomm China，Job ID 3083325，Camera ISP Algorithm System Engineer
>
> 报告目标：在不推翻现有四阶段结构、不虚构量产经历的前提下，把当前作品集从“完整的 AI-ISP 学习仓库”提升为“能够直接支撑 Camera Systems 岗位面试的工程证据包”。

## 一、结论：不新增编号阶段，新增跨阶段 Capstone

不建议把本轮升级简单命名为“阶段五”。原因是本岗位的能力要求不是一个新的单点技术方向，而是阶段一至四能力在真实 Camera 场景中的综合应用：

- IQ 评价、真实 DNG、颜色和噪声属于阶段一；
- ML 画质算法及其评价属于阶段二；
- 多摄算法、高性能 C++ 和可复现验证属于阶段三；
- ISP/AI 联合执行、GPU 数据流、延迟和内存权衡属于阶段四。

如果全部塞进“阶段五”，会复制已有实现、割裂证据链，并让招聘者误以为前四个阶段仍是独立练习。推荐采用“能力回填 + 跨阶段总交付”的结构：

```text
stage1_soft_isp/             <- 真实设备数据、IQ 指标、标定与 tuning
stage2_ai_isp/               <- ML 画质评价、场景分组与失败分析
stage3_cpp_isp/              <- 多摄标定/融合核心、C++ 性能工程
stage4_deploy_isp/           <- GPU 直连推理、内存与延迟分析
camera_system_capstone/      <- 新增；只负责跨阶段数据、编排、验收和岗位展示
```

`camera_system_capstone` 是一个独立可运行的应用项目，但不是新的学习阶段。它不复制四阶段代码，而是通过固定协议调用或消费各阶段产物。

## 二、当前匹配度与目标

当前 `route` 的岗位项目匹配度约为 75%～80%。本轮升级的合理目标是把可由个人项目证明的部分提高到 88%左右。

| 岗位能力 | 当前状态 | 当前评分 | 本轮目标 |
|---|---|---:|---:|
| IQ 评价系统 | 有 PSNR、SSIM、Delta E、ROI、误差图 | 7.5/10 | 9/10 |
| 传统 ISP 评价与 tuning | 有完整学习型 Soft-ISP | 7/10 | 8.5/10 |
| ML 画质功能评价 | 有 SIDD 去噪、FP16/INT8 分析 | 7.5/10 | 8.5/10 |
| 多摄算法 | 只有简化 HDR merge | 2/10 | 7/10 |
| 系统级成像优化 | 有桌面 CPU/GPU profiling | 6/10 | 8/10 |
| 功耗/内存/性能权衡 | 有延迟和模型大小，缺系统数据 | 3/10 | 6/10 |
| 高性能 C++ | 有 C++17、测试、benchmark | 7.5/10 | 8.5/10 |
| 商业化和客户支持 | 无真实量产证据 | 2/10 | 不虚构，只补交付流程证据 |

以下内容不能由个人项目补造：正式工作年限、商业量产经历、高通内部平台经验、真实客户交付。报告和简历必须继续明确能力边界。

## 三、总体目录设计

建议新增如下目录，不移动现有文件：

```text
camera_system_capstone/
├── README.md
├── configs/
│   ├── iq_eval.yaml
│   ├── multicamera.yaml
│   └── system_profile.yaml
├── data/
│   ├── manifests/
│   │   ├── capture_manifest.csv
│   │   ├── iq_eval_manifest.csv
│   │   └── multicamera_manifest.csv
│   └── README.md
├── scripts/
│   ├── 01_validate_assets.py
│   ├── 02_run_iq_evaluation.py
│   ├── 03_run_multicamera_evaluation.py
│   ├── 04_run_system_profile.py
│   └── 05_generate_job_evidence_matrix.py
├── tests/
│   ├── test_manifests.py
│   ├── test_stage_contracts.py
│   └── test_report_schema.py
├── outputs/
│   ├── iq_summary.csv
│   ├── multicamera_summary.csv
│   ├── system_profile_summary.csv
│   └── job_evidence_matrix.csv
└── reports/
    ├── capture_protocol.md
    ├── iq_system_report.md
    ├── multicamera_report.md
    ├── system_optimization_report.md
    ├── failure_case_report.md
    └── qualcomm_3083325_capstone_report.md
```

职责边界：

- `camera_system_capstone` 不存放算法的第二份实现；
- ISP/IQ 基础算法仍在阶段一；
- AI 模型、训练和评价逻辑仍在阶段二；
- C++ 算法和 benchmark 仍在阶段三；
- CUDA/TensorRT 执行逻辑仍在阶段四；
- Capstone 只固定输入、协议、运行顺序、跨阶段指标和最终结论。

## 四、阶段一升级：真实 Camera IQ 评价与 tuning

### 4.1 归属范围

以下内容加入 `stage1_soft_isp`：

```text
stage1_soft_isp/
├── soft_isp/
│   ├── iq_metrics.py
│   └── calibration.py
├── scripts/
│   ├── 20_evaluate_camera_iq.py
│   ├── 21_calibrate_colorchecker.py
│   └── 22_run_tuning_sweep.py
├── tests/
│   ├── test_iq_metrics.py
│   └── test_calibration.py
└── reports/
    ├── real_camera_iq_evaluation.md
    └── tuning_failure_cases.md
```

脚本编号应在实施时根据仓库实际最大编号调整，避免覆盖现有文件。

### 4.2 数据采集协议

使用 iPhone 17 Pro Max 建立自采数据集。第一版不要求购买高通开发板，也不声称获得 Sensor Driver 或 HAL 权限。

建议场景：

1. 室外日光；
2. 室内暖光；
3. 冷暖混合光；
4. 低照度静态场景；
5. 高动态范围逆光；
6. 细密纹理；
7. 肤色；
8. 高饱和颜色；
9. 运动物体；
10. 广角、超广角和长焦相同场景。

每个样本必须记录：

- 文件哈希；
- 设备和镜头；
- 图像格式；
- ISO、曝光时间、焦距；
- 拍摄模式；
- 场景标签和光照说明；
- 固定 ROI；
- 是否经过系统计算摄影处理。

必须先检查 DNG 的 CFA、PhotometricInterpretation、black/white level 和数据维度，再判断它是 Bayer RAW、线性 DNG 还是经过融合的 ProRAW。不得仅根据扩展名将 ProRAW 描述为未经处理的 Sensor RAW。

### 4.3 IQ 指标

新增指标分为六类：

| 类别 | 指标 | 验收重点 |
|---|---|---|
| 曝光 | 均值、P1/P50/P99、过曝/欠曝比例 | 能定位 clipping 和暗部不足 |
| 白平衡 | 中性 ROI RGB 偏差、色温偏差 | 能比较不同光源和算法 |
| 颜色 | ColorChecker Delta E 2000 | 输出平均值、P95 和最差色块 |
| 噪声 | Flat ROI SNR、亮度/色度噪声 | 按 ISO 和亮度分组 |
| 纹理/分辨率 | Acutance、ESF/LSF、MTF50 近似 | 明确 chart 和算法假设 |
| Artifact | Halo、Banding、Fringing、Clipping proxy | 输出空间位置和失败图 |

### 4.4 Tuning 闭环

至少选择三个参数形成自动 sweep：

- AWB ROI 和饱和/暗区过滤阈值；
- Denoise 强度或 `sigma_range`；
- Tone Mapping 高光压缩参数。

每次实验必须形成：

```text
问题现象
-> 初始假设
-> 影响模块
-> 参数 sweep
-> IQ 指标变化
-> 失败区域
-> 画质/噪声/细节 trade-off
-> 最终选择及拒绝其他方案的原因
```

### 4.5 阶段一验收标准

- 自采数据不少于 8 类场景，每类至少 3 个有效样本；
- IQ 评价命令可由 manifest 一次运行；
- 至少输出曝光、颜色、噪声、锐度四类指标；
- 至少完成 3 个 tuning 案例；
- 至少保留 3 个失败案例；
- 单元测试覆盖合成灰块、斜边、饱和和噪声输入；
- 报告明确区分参考图相似度与绝对 IQ 评价。

## 五、阶段二升级：ML 画质功能的 Camera 场景评价

### 5.1 归属范围

阶段二不继续堆新网络，重点把已有模型变成可解释的 Camera Feature：

```text
stage2_ai_isp/
├── scripts/
│   ├── 24_evaluate_camera_scenes.py
│   └── 25_export_scene_failure_matrix.py
├── reports/
│   ├── camera_scene_ml_evaluation.md
│   └── traditional_vs_ml_tradeoff.md
└── tests/
    └── test_camera_scene_evaluation.py
```

### 5.2 实验设计

固定同一批场景，比较：

1. 无去噪；
2. 阶段一传统去噪；
3. DnCNN FP32；
4. DnCNN FP16；
5. 如已有可靠证据，再加入 INT8。

按场景标签输出：

- 噪声改善；
- 纹理损失；
- 边缘损失；
- 色偏；
- Halo/过平滑等失败类型；
- 推理延迟和模型大小。

重点不是证明 ML 始终更好，而是回答：什么场景适合启用 ML、什么场景应降低强度或回退传统算法。

### 5.3 阶段二验收标准

- 评价集按场景分组，不只给全局平均值；
- Calibration、Validation、Test 不混用；
- 至少比较一个传统算法和一个 ML 模型；
- 至少给出 3 类 ML 失败模式；
- 报告明确当前模型是 RGB restoration，不是 Sensor RAW AI-ISP；
- 输出可被 Capstone 读取的 CSV/JSON，而不是只保留图片。

## 六、阶段三升级：多摄算法与高性能 C++

### 6.1 选择范围

JD 对多摄要求是“至少一个相关主题”。本项目选择完成：

> 双目标定、几何校正、对齐、颜色匹配和拼接/融合。

第一版不同时扩展深度估计、时域同步和复杂视频融合，避免形成多个无法验收的 Demo。

### 6.2 归属范围

```text
stage3_cpp_isp/
├── include/cpp_isp/
│   ├── camera_calibration.hpp
│   └── image_fusion.hpp
├── src/
│   ├── camera_calibration.cpp
│   └── image_fusion.cpp
├── tools/
│   ├── run_camera_calibration.cpp
│   └── run_image_fusion.cpp
├── tests/
│   ├── test_camera_calibration.cpp
│   └── test_image_fusion.cpp
├── benchmarks/
│   └── bench_image_fusion.cpp
└── reports/
    └── multicamera_calibration_and_fusion.md
```

如果 OpenCV 已能完成成熟的角点检测和标定求解，可直接使用其经过验证的 API；本项目的原创重点放在数据协议、质量验收、颜色匹配、融合策略、失败诊断和 C++ 系统集成，不重复手写完整标定优化器。

### 6.3 算法流程

```text
标定板图像
-> 角点检测
-> 单目标定与畸变参数
-> 双目外参或静态 Homography
-> 图像去畸变
-> 重叠区域对齐
-> 曝光/颜色匹配
-> Feather 或 Multi-band Blend
-> 质量与性能评价
```

### 6.4 指标与失败案例

必须输出：

- 重投影误差；
- 有效标定图数量；
- 重叠区域对齐误差；
- 重叠区域颜色差；
- 接缝梯度差；
- 运行时间和峰值内存；
- 近景视差、运动和低纹理导致的失败案例。

iPhone 多镜头手动拍摄可以用于静态概念验证，但不能声称实现了硬件级多摄同步。若无法获得同步双流，应明确把项目范围限定为静态标定/拼接。

### 6.5 C++ 性能升级

在多摄融合或现有 Local Tone Mapping 中选择一个主要瓶颈，补充：

- Buffer 复用；
- 避免循环内重复 allocation；
- Tile 划分；
- 多线程；
- 可行时加入 SIMD；
- 1080P/4K 测试；
- p50/p90 或稳定多轮统计；
- 输出正确性与性能的联合验收。

不得只报告加速倍数；必须记录 CPU、编译器、编译参数、线程数、输入尺寸、warm-up、运行次数和是否包含 I/O。

### 6.6 阶段三验收标准

- 至少完成一次可复现标定；
- 平均重投影误差和失败阈值写入配置；
- 至少完成一种融合算法；
- Python/OpenCV reference 与 C++ 输出完成数值或图像指标对齐；
- 至少保留 3 个多摄失败案例；
- 1080P benchmark 可复现；
- 所有新增 C++ 测试接入 CTest。

## 七、阶段四升级：ISP/AI 联合数据流与系统优化

### 7.1 当前问题

阶段四已经证明 CUDA normalize kernel 很快，但 pageable H2D+D2H 使 GPU stage 整体慢于 CPU normalize；同时 CUDA 输出尚未直接绑定到 GPU inference。这一缺口正适合转化为岗位要求的系统优化案例。

### 7.2 归属范围

```text
stage4_deploy_isp/
├── cpp/
│   ├── include/device_pipeline.hpp
│   └── src/device_pipeline.cpp
├── scripts/
│   ├── 13_profile_device_pipeline.py
│   └── 14_generate_quality_latency_memory_matrix.py
├── tests/
│   └── test_device_pipeline_contract.py
└── reports/
    ├── gpu_direct_pipeline.md
    └── quality_latency_memory_tradeoff.md
```

### 7.3 目标数据流

```text
Host input
-> pinned memory
-> asynchronous H2D
-> CUDA preprocess
-> device tensor
-> ORT CUDA or TensorRT inference
-> GPU postprocess
-> final D2H only when output is required on host
```

分阶段实施，任何一步未实测都不得写成完成：

1. CUDA Event 替换不可靠的 host 计时；
2. pageable 与 pinned memory 对比；
3. 取消 preprocess 后的中间 D2H；
4. Device Tensor 直接绑定推理输入；
5. 使用 CUDA Stream；
6. 使用 Nsight Systems 验证 copy/compute 时间线；
7. 统计峰值 RAM/VRAM；
8. 输出 FP32/FP16/INT8 的质量、延迟、内存矩阵。

### 7.4 验收矩阵

最终报告至少包含：

| Backend | Precision | Quality drop | p50 | p90 | Peak RAM | Peak VRAM | H2D/D2H count |
|---|---|---:|---:|---:|---:|---:|---:|
| ORT CPU | FP32 | baseline | 实测 | 实测 | 实测 | N/A | 0 |
| TensorRT | FP32 | 实测 | 实测 | 实测 | 实测 | 实测 | 实测 |
| TensorRT | FP16 | 实测 | 实测 | 实测 | 实测 | 实测 | 实测 |
| GPU direct | FP16 | 实测 | 实测 | 实测 | 实测 | 实测 | 实测 |

若 INT8 仍然只有 ORT CPU QDQ，不得把它写成 TensorRT INT8 或 NPU 结果。

### 7.5 功耗边界

桌面 GPU 可记录板卡功率作为特定环境下的辅助证据，但不能等价为 Snapdragon Camera 功耗。没有稳定采样、空闲基线和重复实验时，不输出功耗结论。芯片面积属于架构分析题，只能写设计权衡，不声称实测。

### 7.6 阶段四验收标准

- Preprocess device output 真正进入 GPU inference；
- 中间数据不经 D2H 回传；
- CUDA Event 计时与 Nsight 时间线一致；
- 正确性继续对齐 FP32 reference；
- 输出 p50/p90、RAM/VRAM 和拷贝次数；
- 报告同时保留优化失败或收益不明显的方案；
- 不出现移动端、NPU或量产实时性的越界表述。

## 八、Capstone 跨阶段验收

### 8.1 统一数据契约

`camera_system_capstone/configs/` 必须固定：

- 图像格式、通道顺序和数值范围；
- RAW/linear RGB/sRGB 的颜色空间边界；
- 输入尺寸和裁剪规则；
- 相机与镜头标识；
- 场景和 ROI 标签；
- train/calibration/evaluation split；
- reference 和阈值；
- 每个阶段是否包含 I/O。

### 8.2 一键验收顺序

```text
validate assets
-> run stage1 IQ evaluation
-> run stage2 traditional-vs-ML evaluation
-> run stage3 multicamera evaluation
-> run stage4 system profile
-> generate evidence matrix
-> generate final report
```

不要求一个命令重训所有模型，也不要求在无 GPU 环境运行 TensorRT。统一入口应支持 `--cpu-only` 和完整环境两种明确模式，但不要把未运行部分标记为通过。

### 8.3 岗位证据矩阵

`job_evidence_matrix.csv` 至少包含：

| JD requirement | Evidence file | Command | Environment | Result | Boundary |
|---|---|---|---|---|---|
| IQ evaluation | 报告/CSV | 可复现命令 | 设备与版本 | 指标摘要 | 非 Imatest |
| Traditional/ML tuning | 报告/图 | 可复现命令 | 数据集 | trade-off | 非量产 tuning |
| Multi-camera | 标定/融合报告 | 可复现命令 | 相机/数据 | 重投影误差 | 非硬件同步 |
| System optimization | profile 报告 | 可复现命令 | GPU/软件版本 | p50/p90/内存 | 非 Snapdragon |
| C++ system software | tests/bench | CMake/CTest | 编译器 | pass/latency | 学习型库 |

### 8.4 最终总报告结构

`qualcomm_3083325_capstone_report.md` 建议严格控制为以下结构：

1. 问题与目标；
2. Camera 数据流和系统架构；
3. 数据与拍摄协议；
4. IQ 评价系统；
5. Traditional vs ML tuning；
6. 多摄标定与融合；
7. C++/GPU系统优化；
8. 质量、延迟和内存权衡；
9. 失败案例；
10. 已知边界；
11. 对应 Job ID 3083325 的能力证据表；
12. 最小复现命令。

## 九、实施计划

### Sprint 0：设计与冻结协议，2～3天

- 新建 Capstone 骨架；
- 固定数据契约、manifest schema 和指标口径；
- 检查 iPhone 文件实际格式；
- 写拍摄协议；
- 建立最小合成测试。

停止条件：如果数据格式和颜色空间无法确定，不进入算法比较。

### Sprint 1：真实 IQ 系统，约2周

- 完成自采测试集；
- 实现曝光、WB、颜色、噪声和锐度指标；
- 完成参数 sweep；
- 输出 IQ 报告和失败案例。

成功标准：相同命令可从 manifest 重新生成 CSV 和关键图。

### Sprint 2：多摄标定与融合，约2～3周

- 拍摄标定板和静态场景；
- 完成标定、去畸变、对齐、颜色匹配和融合；
- 移植关键路径到 C++；
- 输出重投影误差、接缝指标和失败案例。

成功标准：至少一组独立测试图不参与参数选择，并通过预先定义的阈值。

### Sprint 3：GPU 直连和系统 profile，约2周

- pinned memory；
- CUDA Event；
- Device Tensor 直连推理；
- Nsight 时间线；
- 质量/延迟/内存矩阵。

成功标准：能用证据解释收益来自哪里；如果最终未加速，也必须能定位瓶颈并给出可信结论。

### Sprint 4：岗位交付，约3～5天

- 生成 Job Evidence Matrix；
- 完成最终报告；
- 更新根 README 的一个入口链接；
- 运行回归测试；
- 准备三分钟项目介绍和五个追问题答案。

总工期约 7～8周。若时间只有一个月，只完成 Sprint 0、1、2，不要同时展开 GPU 深化和新型 Sensor 专题。

### 9.1 本次仓库执行状态（2026-07-16）

本轮实现没有新增“阶段五”。算法、测试和阶段报告均回填到 Stage 1～4；`camera_system_capstone` 只负责 manifest 校验、运行顺序、跨阶段汇总和 Job Evidence Matrix。

| 归属 | 已执行并验证 | 当前证据级别 | 仍未完成的边界 |
|---|---|---|---|
| Stage 1 | 14 个公开 DNG 的 manifest IQ audit；AWB、bilateral、tone/highlight 三组受控 sweep；失败设置记录 | `verified_proxy` | 自采 RAW、ColorChecker、平场和标准斜边仍为 `not_run` |
| Stage 2 | 10 个冻结公开 SIDD sRGB 样本、30 条同输入 traditional/ML 结果、17 条失败聚合；DnCNN 相对 bilateral 平均 PSNR +4.043 dB | `verified_public_rgb` | 自采 Camera 场景、Sensor RAW AI-ISP、完整 FP16 画质集仍为 `not_run` |
| Stage 3 | C++17 标定/逆映射 warp/颜色匹配/feather fusion；OpenCV/NumPy 对齐；近景视差、运动接缝和退化几何诊断；14/14 CTest | `verified_synthetic` / `verified_learning` | 实拍标定双摄、畸变模型、硬件同步仍为 `not_run` |
| Stage 4 | ORT CUDA I/O Binding 的 device input/output；1 H2D、0 intermediate D2H、1 final D2H；推理 p50/p90 3.296/3.754 ms，e2e p50/p90 10.477/11.047 ms，峰值 RAM 614.61 MiB | `verified_partial` | 自定义 CUDA preprocess 直接指针绑定、Nsight、每进程 VRAM、Snapdragon/NPU 和移动功耗仍为 `not_run` |
| Capstone | 一键刷新 CPU-safe 阶段输出、资产/哈希校验、5 条岗位证据、主报告及 IQ/多摄/系统/失败四份分报告 | 汇总层 | 不持有或复制 Stage 1～4 算法 |

统一复现命令：

```powershell
python camera_system_capstone/scripts/06_run_capstone.py --cpu-only
powershell -ExecutionPolicy Bypass -File tools/verify_project.ps1 -SkipCpp
```

上表中的公开数据和合成验证不能改写成自采或量产经验；只有补齐对应硬件与拍摄协议后，才能提升证据级别。

## 十、硬件与软件建议

### 10.1 第一阶段必需

- iPhone 17 Pro Max；
- 稳定手机夹和三脚架；
- 打印棋盘格，先用于流程验证；
- 灰卡；
- 可控制亮度或色温的灯；
- Windows PC 继续运行现有 Python/C++/CUDA 环境。

### 10.2 可选升级

- 正规 ColorChecker，用于颜色评价；
- 更平整、尺寸准确的标定板；
- 简易照度计，用于记录光照；
- 两个可固定的相机，用于真实双目同步实验；
- Android/Snapdragon设备，用于后续移动端验证。

不建议一开始购买昂贵的高通开发板。这个岗位首先看 IQ、算法和系统权衡；开发板若缺少 Camera 驱动、Sensor 模组和平台权限，投入不一定转化成有效证据。

## 十一、简历与面试产出

完成 P0～P2 后，可按实际结果形成以下类型的项目描述，数字必须由最终实验替换：

- 基于自采多场景 Camera 数据建立自动 IQ 评价系统，覆盖曝光、白平衡、颜色、噪声、纹理、MTF 和 Artifact，并通过 manifest 固定场景、镜头、元数据和 ROI，实现参数 sweep 与失败样本追踪。
- 完成双目标定、畸变校正、几何对齐、颜色匹配和图像融合，使用重投影误差、重叠区域色差和接缝梯度评价质量，并在近景视差和低纹理场景中建立失败分类。
- 将传统 ISP、ML 去噪和 TensorRT FP16 串为可复现系统链路，拆分 H2D、预处理、推理、后处理和 D2H，消除中间 Host 回传，并以画质、p50/p90 延迟和峰值内存分析系统 trade-off。

面试必须能够回答：

1. 为什么这些 IQ 指标足以定位问题，又有哪些盲区？
2. ProRAW、线性 DNG 和 Bayer RAW 的边界是什么？
3. 多摄标定误差如何传递到拼接接缝？
4. ML 去噪在什么场景下会损失纹理，如何设计回退策略？
5. CUDA kernel 很快但端到端不快的原因是什么？
6. 如果换到 Snapdragon ISP/NPU，哪些结论可以迁移，哪些必须重测？

## 十二、明确不做的事情

本轮升级不做以下扩张：

- 不继续复现大量新网络；
- 不重写成熟的 OpenCV 标定求解器；
- 不同时实现完整 AE、AF、AWB、Depth 和视频同步；
- 不把静态多镜头拍摄描述为硬件同步多摄；
- 不把桌面 TensorRT 数据描述为移动端或 Snapdragon 数据；
- 不把个人项目描述为商业量产；
- 不为了目录好看复制阶段一至四代码到 Capstone；
- 不在没有测量协议时输出功耗和实时性结论。

## 十三、最终优先级

| 优先级 | 内容 | 归属 | 对岗位价值 |
|---|---|---|---|
| P0 | 自采 Camera 数据与 IQ 评价系统 | Stage 1 + Capstone | 最高，直接对应职责1、2 |
| P0 | 双目标定与静态融合 | Stage 3 + Capstone | 补齐最大算法缺口 |
| P1 | Traditional vs ML 场景评价 | Stage 2 + Capstone | 对应现代 ML Feature |
| P1 | GPU device tensor 直连推理 | Stage 4 + Capstone | 对应系统优化和PPA思维 |
| P1 | C++ Buffer/Tile/Thread优化 | Stage 3 | 强化高性能系统软件证据 |
| P2 | AWB/Exposure 深化 | Stage 1 | 提升 tuning 说服力 |
| P2 | Staggered HDR/Quad Bayer专题 | Stage 1/3 | 对应新型 Sensor，但非首要 |
| P3 | Android/Snapdragon实机 | Stage 4 | 有设备和权限后再做 |

最终推荐路线：

```text
真实 IQ 系统
-> 双目标定与融合
-> Traditional vs ML 场景权衡
-> GPU 直连与系统 profile
-> Qualcomm 3083325 Evidence Matrix
```

这条路线完成后，`route` 的核心叙事应从“我学习了四阶段 ISP/AI-ISP 技术”转变为：

> 我建立了一套从真实 Camera 数据、IQ 评价和多摄算法，到 C++/GPU 系统优化的可复现验证系统；能够用量化证据定位画质与性能问题，并明确个人项目与量产 Snapdragon Camera 系统之间仍需重新验证的边界。

## 十四、2026-07-19 面试就绪审计与二次补强

### 14.1 结论：可以面试，但要选对表述层级

完成四阶段教程化和 Capstone 后，仓库已经足够支撑以下面试环节：

- 用一条完整链路讲清 RAW/ISP、RGB restoration、C++ 重写、模型部署和系统 profiling；
- 对项目中的公式、参数、数据合同、失败案例、性能边界进行深挖；
- 用公开/合成/代理/部分实测证据回答“为什么这样做、结果说明什么、哪里还不能下结论”；
- 针对多摄、传统/ML 权衡、GPU copy bottleneck 做白板设计和故障定位。

它**不能单独证明**候选人具有量产 Snapdragon Camera、OEM 客户支持、Sensor bring-up、高通内部 Camera framework 或多年商业项目经验。更准确的定位是：

> 已达到“可以参加并支撑项目型技术面试”的作品集水平；尚未达到“无需培养即可承担量产平台 owner”的证据水平。

旧版 `75%～80%` 是升级前的项目覆盖估计，不等于录用概率。当前也不再给出虚假的单一百分比，因为学历、工作年限、实际职责、英文沟通和岗位级别无法由仓库推断。后续按“已验证、概念可答、必须实测、经历不可补造”四层判断。

目标岗位的公开职位页截至 2026-07-19 已不能稳定返回完整 JD，因此本审计以仓库保存的 Job ID 3083325 能力映射为基线；投递前应重新核对当时有效职位描述，避免把旧关键词当成新职位的硬要求。

### 14.2 能力—证据—差距矩阵

| 能力域 | 当前能拿出的证据 | 面试就绪度 | 主要差距 |
|---|---|---|---|
| RAW/传统 ISP | DNG metadata、BLC/DPC/LSC/Demosaic/AWB/CCM/Tone、模块测试与 first-divergence | 已验证/可深挖 | 无自采 Sensor RAW、dark/flat/ColorChecker/标准斜边 |
| IQ 与 tuning | manifest、ROI、PSNR/SSIM/DeltaE proxy、MTF/SNR/DR proxy、参数 sweep 和拒绝方案 | 可用于方法论面试 | 标准实验室 IQ、主观 panel、跨 CCT/ISO/曝光覆盖不足 |
| ML Camera feature | SIDD paired sRGB、DnCNN/UNet/NAFNet-lite、failure taxonomy、FP16/INT8 | 已验证公开 RGB | 非 Sensor RAW AI-ISP；无视频时序、肤色/人脸、真实 Camera scene fallback |
| 多摄 | C++ homography/warp/color/fusion、Python/OpenCV 对齐、失败诊断、1080P benchmark | 合成学习证据 | 无真实内外参/畸变、同步帧、rolling shutter、视差/depth、EIS |
| C++ 系统能力 | C++17、CMake/CTest、golden、layout/stride/ownership、tile/thread benchmark | 可深挖 | 无 ARM64/NEON/HVX、实时 allocator/buffer pool、Linux perf/trace 证据 |
| GPU/部署 | ONNX/ORT C++、TensorRT FP16、INT8、I/O Binding、copy/latency/RAM 矩阵 | 桌面部署证据较强 | custom preprocess 直绑未完成；无 Nsight、可信 VRAM peak、长跑功耗 |
| Qualcomm 平台 | QAIRT/QNN/HTP/HVX/Adreno/CAMX 概念和真机验收设计 | 只能做架构回答 | 无 SDK/SoC/ADB 真机、graph partition、HTP profile、Camera 接入 |
| 3A 与时序 | Gray World/ROI AWB、曝光/直方图基础可迁移 | 概念补强后可答基础题 | AE/AF state machine、stats delay、flicker/oscillation、PDAF/CAF 未实现 |
| HDR/新 Sensor | Toy HDR、曝光融合和 failure 思路 | 只够基础设计题 | Staggered HDR、Quad Bayer/remosaic、motion/ghost、row timing 未验证 |
| PPA/实时系统 | p50/p90、copy count、模型大小、RAM、质量权衡 | performance 可答 | 移动功耗/温度/带宽、端到端 deadline、芯片 area 均无实测 |
| 产品/客户闭环 | 可复现命令、RCA、failure card、证据矩阵 | 可模拟问题处理流程 | 商业化、客户沟通、版本交付和量产责任属于经历缺口，不能用文档冒充 |

### 14.3 二次补强落点

本轮不新增算法代码，先把面试知识和证据边界补回最相关报告：

| 补强主题 | 落点 | 面试目标 |
|---|---|---|
| 3A 时序、Staggered HDR、Quad Bayer、TNR/MFNR | Stage 1 Week 6 | 能解释离线 ISP 与连续 Camera 控制的差别 |
| ML feature 场景准入、fallback、时序与发布门槛 | Stage 2 Week 10 | 把“模型分数”升级为“可上线 Camera feature 决策” |
| 多摄实拍差距、实时 C++、ARM SIMD 与 buffer pool | Stage 3 Week 8 | 能画系统图并明确 synthetic 到 production 的升级路径 |
| CAMX/CHI/QNN/HTP、buffer/fence、真机验收 | Stage 4 Week 5 | 能回答高通端侧执行链而不冒充平台经验 |
| deadline、queue/backpressure、power/thermal/PPA | Stage 4 Week 6 | 能从单 kernel 进入实时 Camera 系统分析 |

### 14.4 仍需真正执行的优先级

报告知识补齐后，证据缺口不会自动消失。按岗位收益排序：

1. **P0：自采 Camera IQ。** 同设备冻结 exposure/ISO/CCT/scene，补 dark、flat、ColorChecker、slanted-edge 和连续序列；这是从 proxy 到真实 IQ 的最大跃迁。
2. **P0：真实静态双摄。** 完成内外参、畸变、重投影误差、重叠颜色、接缝和近景视差；若无硬件同步，必须继续写静态/软件对齐。
3. **P1：连续帧与 3A/TNR 思维。** 即使不实现完整算法，也应保存 stats→decision→metadata→frame 的时序图和一个振荡/迟滞实验。
4. **P1：Android/Snapdragon 验证。** 用实际 QAIRT/QNN/AI Hub 能力完成 raw tensor 对齐、backend partition、CPU/GPU/HTP profile、冷/热/长跑内存与功耗。
5. **P1：ARM C++ 性能。** 在 arm64 设备建立 scalar baseline，再做 NEON/线程/allocator 消融；HVX 只有获得相应工具链并实际运行后才能升级证据。
6. **P2：GPU direct pipeline。** 把 custom preprocess device pointer/stream 直接交给 runtime，用 timeline 证明无隐式 staging。

### 14.5 面试回答协议

每个项目问题使用同一套六步结构，避免只背概念或只报数字：

```text
Claim：我实际完成了什么
Evidence：数据、命令、指标和环境是什么
Mechanism：为什么会得到该结果
Trade-off：质量、速度、内存、功耗或复杂度如何交换
Boundary：哪些没有验证，不能外推什么
Next experiment：如果给设备/时间，下一步如何证伪或升级证据
```

例如“是否会高通 NPU 部署”的合格回答不是简单说会或不会，而是：当前在桌面 ORT/TensorRT 建立了 tensor correctness 和 copy 计数；公开知识层面理解 QAIRT/QNN backend/graph/tensor/profile 流程；没有 Snapdragon HTP 实测，因此不能声称平台经验；若获得设备，会先 CPU correctness，再检查 HTP partition/fallback，最后测 cold/warm/thermal、内存和功耗。

### 14.6 必须闭卷回答的十二题

1. black level、white level、linearization、WB gain 和 CCM 的顺序错了会出现什么现象？
2. 为什么自然图 ROI 的 SNR/MTF 只能是 proxy？标准 dark/flat/slanted-edge 怎样补证？
3. AE/AWB 的统计延迟为什么可能造成振荡，迟滞和滤波怎样取舍？
4. Staggered HDR 的运动、饱和、read noise 和行时序如何影响融合权重？
5. ML 去噪怎样建立 scene gate、artifact reject、fallback 和 regression set？
6. 多摄 homography 在近景为什么失效？完整内外参、畸变、深度和同步分别解决什么？
7. 30 fps 的 `33.3 ms` 为什么不是每个节点都可使用的独立预算？
8. C++ tensor 的 stride、alignment、ownership、lifetime 错误怎样在第一发散点定位？
9. SIMD/多线程提速后，怎样证明数值、边界、尾延迟和内存仍满足合同？
10. CUDA kernel 很快但 e2e 不快，怎样用字节量、copy 和同步位置解释？
11. QNN/HTP 选择成功为什么不等于整图都在目标单元执行？怎样验证 fallback？
12. 哪些桌面结论可迁移到 Snapdragon，哪些 correctness/performance/power 必须重测？

### 14.7 最终就绪条件

投递前至少做到：

- [ ] 能在 10 分钟内从 Stage 1 讲到 Capstone，不依赖逐字读报告；
- [ ] 每个数字都能指出 manifest、命令、环境、计时/指标边界；
- [ ] 对四个最差案例完成 symptom→hypothesis→experiment→regression；
- [ ] 能白板画出 RAW ISP、双摄、ML feature 和 host/device 四张数据流；
- [ ] 能明确说出 public/synthetic/proxy/partial/not_run 的区别；
- [ ] 不把 CAMX/CHI/QNN/HTP 概念学习写成高通内部或真机经验；
- [ ] 重新核对当前有效 JD，并把简历关键词映射到已验证证据，而不是映射到计划项。
