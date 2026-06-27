# 阶段 1-4 ISP 项目升级方案报告

> 目标：基于当前 `stage1_soft_isp`、`stage2_ai_isp`、`stage3_cpp_isp`、`stage4_deploy_isp` 四阶段项目，补齐影像算法/ISP 岗位中仍缺少但可以通过个人项目完成的能力证据。
>
> 排除范围：真实公司实习、真实秋招投递、简历润色、LeetCode、通用八股。本报告只讨论 ISP / AI-ISP / 影像工程相关的可建设内容。

## 一、总体判断

当前项目已经有完整主干：

- 阶段 1：传统 Soft-ISP pipeline，覆盖 RAW 读取、BLC、DPC、LSC、Demosaic、AWB、CCM、Gamma、Tone Mapping。
- 阶段 2：AI-ISP / 图像恢复训练闭环，覆盖 toy denoise、SIDD、NAFNet-lite、低照增强、failure case 分析、ONNX 导出。
- 阶段 3：C++ 高性能 ISP 库，覆盖 C++17、CPF32 对齐、denoise、tone mapping、HDR toy、benchmark 和 pipeline 集成。
- 阶段 4：部署链路，覆盖 PyTorch、ONNX、ONNX Runtime C++、TensorRT、INT8、CUDA preprocess、latency profiling。

主干已经能证明“会搭链路、会写模块、会做实验、会做部署”。下一步升级重点不是继续堆普通模块，而是补充更像真实影像岗位的能力：

1. 真实 RAW / 真实设备分析。
2. 工业 IQ 评估。
3. 3A 与场景调试。
4. 标定流程。
5. RAW 域降噪、HDR、多帧和特殊场景。
6. C++ 性能优化证据。
7. stage3 C++ ISP 与 stage4 AI 部署的系统串联。

## 二、当前不足总览

| 能力项 | 当前覆盖 | 不足 | 影响 |
|---|---|---|---|
| 真实 RAW 设备闭环 | 有 FiveK DNG 和开源数据 | 缺自己拍摄的手机 DNG / 暗场 / 平场 / 场景组 | 面试中容易被追问“真实设备怎么调”。 |
| 工业 IQ 评估 | 有 PSNR / SSIM / DeltaE 等学习指标 | 缺 MTF、SNR、动态范围、chart 流程 | 手机厂和消费电子岗位非常看重画质评估。 |
| 3A | 有 Gray World AWB baseline | AE/AF 缺失，AWB 不够接近真实调试 | 3A 是 ISP 高频面试区。 |
| 标定 | LSC/CCM 是学习版 | 缺 flat-field LSC、ColorChecker CCM、噪声标定闭环 | 很难证明理解 tuning 和 calibration。 |
| RAW 域降噪 | 有基础噪声建模、denoise、AI 恢复 | RAW 域 BNF/CNF/NLM/时域降噪不够系统 | 低照、夜景、手机影像会重点追问。 |
| HDR / 多帧 | 有 HDR toy 和 tone mapping | 缺运动对齐、ghosting、真实 HDR 场景分析 | 车载、手机、安防都看重 HDR 和运动场景。 |
| 调试案例 | 有报告和 failure case | 缺“现象-定位-修改-对比”的画质问题案例库 | 面试表达会像学习项目，不像调试经历。 |
| 端侧约束 | 有 latency 和 INT8 | 缺功耗、内存峰值、真实端侧约束；stage3 与 stage4 未串联 | AI-ISP 部署岗位会问效果/延迟/内存/功耗权衡。 |
| 系统集成 | 有算法 pipeline | 缺 sensor/driver/HAL/metadata/control loop 的系统认知图 | 消费电子岗位会问 ISP 在整机链路中的位置。 |

## 三、升级原则

### 1. 不追求大而全

不要把每个 ISP 模块都做成工业级。个人项目更应该选择少数高价值主题，做出可解释、可复现、可对比的证据。

### 2. 每个升级项必须有验收物

每个升级项至少产出：

- 一份报告。
- 一组可复现实验命令。
- 一组指标或对比图。
- 一个可以在面试中讲 3-5 分钟的故事。

### 3. 优先补“面试官会追问”的空白

优先级最高的不是炫技，而是能回答：

- 如果给你一个真实 DNG，你怎么分析？
- 如果画面偏色、噪声大、过曝、暗部糊，你怎么定位？
- 如果模型部署后画质下降或延迟太高，你怎么权衡？
- 如果要做 camera tuning，你从哪里开始？

## 四、阶段 1 升级方案：真实 RAW、IQ、3A、标定

阶段 1 是最该升级的地方。它目前已经有完整 Soft-ISP 学习链路，但 README 也明确写了 LSC、DPC、AWB、CCM 是 explainable learning baselines，不是 production calibration。升级重点应从“会实现模块”转向“会分析真实 RAW 并调试画质问题”。

### Stage 1-U1：真实 DNG 采集与 RAW 数据体检

优先级：P0

目标：

- 建立一套自己拍摄的真实 RAW 样本。
- 证明能面对陌生 DNG 做数据 contract、曝光、噪声、白平衡、动态范围分析。

建议数据：

- 手机 Pro 模式 DNG。
- 暗场：盖住镜头，不同 ISO。
- 平场：白墙/均匀光源，不同 ISO。
- 场景：室内暖光、室外日光、低照、逆光、高对比、彩色物体。

建议新增产物：

- `stage1_soft_isp/data/user_raw/manifest.csv`
- `stage1_soft_isp/reports/real_dng_raw_audit.md`
- `stage1_soft_isp/reports/figures/real_dng_audit/`

验收标准：

- 能输出每张 DNG 的 black level、white level、Bayer pattern、bit depth、直方图、饱和比例。
- 能按 ISO 估计噪声水平，并给出暗场/平场统计。
- 能指出至少 3 个真实场景问题，例如偏色、暗部噪声、过曝 clipping、边缘暗角。

面试价值：

- 回答“你有没有处理过真实 RAW？”
- 回答“给你一张 DNG，你第一步看什么？”

### Stage 1-U2：工业 IQ 指标补齐

优先级：P0

目标：

- 从“和参考图像相似”升级到“能做画质诊断”。
- 增加 ISP 岗位更熟悉的 IQ 指标。

建议实现：

- SNR：基于 flat-field ROI 的均值/标准差。
- 动态范围：基于暗场噪声底和饱和点估计。
- MTF 近似：基于斜边或清晰边缘的 ESF/LSF/MTF50。
- 饱和比例、暗部噪声、局部对比度、色偏统计。

建议新增产物：

- `stage1_soft_isp/soft_isp/iq_metrics.py`
- `stage1_soft_isp/scripts/18_evaluate_iq_metrics.py`
- `stage1_soft_isp/reports/industrial_iq_metrics_report.md`

验收标准：

- 对同一张图不同 pipeline 参数输出 SNR / MTF / clipping / color cast 对比表。
- 至少给出 3 个 ROI 级分析案例。
- 报告中明确说明 PSNR/SSIM 与工业 IQ 指标各自能说明什么、不能说明什么。

面试价值：

- 回答“你怎么评价画质？”
- 回答“如果 SNR 或锐度不达标，你怎么定位？”

### Stage 1-U3：AWB 进阶与色温估计

优先级：P0

目标：

- 从 Gray World baseline 升级到可调试的 AWB 实验框架。

建议实现：

- Gray World、White Patch、Gray Edge 或 Shades-of-Gray 对比。
- ROI 加权 AWB。
- 排除过曝、高饱和、极暗区域。
- 简单 CCT / 色温估计。
- 混合光源失败案例。

建议新增产物：

- `stage1_soft_isp/soft_isp/awb_advanced.py`
- `stage1_soft_isp/scripts/19_compare_awb_methods.py`
- `stage1_soft_isp/reports/awb_scene_debug_report.md`

验收标准：

- 至少比较 3 种 AWB 方法。
- 每种方法输出 gain、白点选择、色偏指标、视觉对比。
- 报告中包含一个 Gray World 失败案例，并解释失败原因。

面试价值：

- 回答“Gray World 遇到大面积红墙怎么办？”
- 回答“混合光源下 AWB 为什么难？”

### Stage 1-U4：Histogram-based AE 仿真

优先级：P1

目标：

- 补齐 3A 中 AE 的基础控制逻辑。
- 不要求接真实 sensor，只做仿真闭环。

建议实现：

- 基于亮度直方图的曝光目标。
- 高光保护权重。
- 简单 EV 调整策略。
- 模拟从欠曝到目标曝光的收敛过程。

建议新增产物：

- `stage1_soft_isp/soft_isp/ae.py`
- `stage1_soft_isp/scripts/20_simulate_ae_loop.py`
- `stage1_soft_isp/reports/ae_control_loop_simulation.md`

验收标准：

- 给出至少 3 个场景的 AE 收敛曲线。
- 对比平均亮度优先和高光保护优先的差异。
- 能解释 AE 与 tone mapping / HDR 的关系。

面试价值：

- 回答“AE 如何收敛？”
- 回答“为什么逆光场景容易过曝或欠曝？”

### Stage 1-U5：Flat-field LSC 与 ColorChecker CCM 标定

优先级：P1

目标：

- 从学习版 LSC/CCM 升级到可解释的标定流程。

建议实现：

- flat-field 估计 mesh gain map。
- R/G/B 或 Bayer 四通道分别标定。
- ColorChecker 或公开 chart 数据的 3x3 CCM 拟合。
- DeltaE 评估。

建议新增产物：

- `stage1_soft_isp/scripts/21_calibrate_lsc_from_flat_field.py`
- `stage1_soft_isp/scripts/22_calibrate_ccm_colorchecker.py`
- `stage1_soft_isp/reports/calibration_workflow_report.md`

验收标准：

- 能从平场图生成 gain map，并展示校正前后亮度均匀性。
- 能拟合 CCM，并展示 DeltaE 改善或失败原因。
- 报告中说明真实标定还需要哪些硬件条件。

面试价值：

- 回答“LSC/CCM 在真实产品里怎么标定？”
- 回答“为什么学习版 LSC/CCM 不能等同于量产标定？”

## 五、阶段 2 升级方案：RAW-aware AI-ISP 与失败场景

阶段 2 已经具备训练、评估、SIDD、NAFNet-lite、低照增强和部署桥接。它的问题不是没有 AI 项目，而是还可以更贴近 ISP：更关注 RAW/pseudo RAW、噪声模型、特殊场景、failure case 和部署前的画质损失。

### Stage 2-U1：RAW-aware 噪声建模与数据构造

优先级：P0

目标：

- 把 AI-ISP 数据构造与 sensor 噪声模型绑定，而不是只做 RGB denoise。

建议实现：

- 使用 Stage 1 的真实暗场/平场估计 noise parameters。
- 构造 Poisson-Gaussian noise 配置。
- 对比 synthetic noise 与 SIDD real noise 的差异。
- 记录不同 ISO 下模型效果变化。

建议新增产物：

- `stage2_ai_isp/reports/raw_aware_noise_modeling.md`
- `stage2_ai_isp/configs/raw_aware_denoise_*.yaml`

验收标准：

- 报告能说明 shot noise、read noise、ISO 对训练数据的影响。
- 至少输出一张 noise level vs metric 曲线。
- 能解释为什么 RGB denoise 不能完全代表 RAW/AI-ISP。

面试价值：

- 回答“训练数据怎么构造？”
- 回答“真实 sensor 噪声和合成噪声差在哪里？”

### Stage 2-U2：特殊场景 failure case 扩展

优先级：P1

目标：

- 把当前 failure case 分析扩展成影像岗位更关心的场景库。

建议场景：

- 低照高 ISO。
- 混合光源。
- 高动态范围。
- 大面积肤色或色块。
- 高频纹理。
- 运动模糊或模型过平滑。

建议新增产物：

- `stage2_ai_isp/reports/scene_failure_taxonomy_extended.md`
- `stage2_ai_isp/reports/figures/scene_failure_taxonomy/`

验收标准：

- 至少 6 类失败场景。
- 每类包含输入、输出、参考、误差图、局部 crop。
- 每类给出原因猜测和下一步修复策略。

面试价值：

- 回答“模型效果不好时你怎么分析？”
- 回答“低照和高频纹理为什么容易失败？”

### Stage 2-U3：AI 模块替换传统 ISP 模块的边界实验

优先级：P1

目标：

- 明确 AI 模型替换传统模块时的输入输出边界和风险。

建议实验：

- AI denoise 放在 demosaic 前后对比。
- AI low-light 放在 tone mapping 前后对比。
- 对比 RGB 域、linear RGB 域、pseudo RAW 域的效果差异。

建议新增产物：

- `stage2_ai_isp/reports/ai_module_in_pipeline_boundary.md`

验收标准：

- 至少比较 2 种插入位置。
- 输出画质、指标、失败案例和推理成本对比。
- 明确说明模型替换了 pipeline 中哪一段，以及没有替换哪一段。

面试价值：

- 回答“AI-ISP 的 AI 模块应该放在哪里？”
- 回答“为什么模型输入的数据域很重要？”

## 六、阶段 3 升级方案：C++ 性能证据、RAW 域模块、多帧

阶段 3 已经很强，是本仓库最适合支撑工程化面试的部分。继续升级时，不要只加算法名，而要强化“工程优化证据”和“真实 ISP 任务相似度”。

### Stage 3-U1：性能优化故事化

优先级：P0

目标：

- 把已有 benchmark 升级为面试可讲的优化故事。

建议整理：

- baseline vs optimized。
- 单线程 vs 多线程。
- direct vs LUT。
- cache-friendly layout vs naive layout。
- 1080P / 4K latency 和吞吐。

建议新增产物：

- `stage3_cpp_isp/reports/performance_optimization_story.md`
- `stage3_cpp_isp/reports/figures/performance_story/`

验收标准：

- 每个优化点都有修改前后数据。
- 每个优化点都解释为什么变快，代价是什么。
- 至少形成 3 个可讲故事：例如 bilateral LUT、tone LUT、pipeline memory layout。

面试价值：

- 回答“你做过什么 C++ 性能优化？”
- 回答“如何判断优化有效，而不是测量误差？”

### Stage 3-U2：RAW 域降噪模块补强

优先级：P1

目标：

- 把降噪从 RGB/通用图像处理进一步贴近 RAW ISP。

建议实现：

- Bayer pattern aware denoise。
- RAW 域 bilateral / NLM 对比。
- 简化 BNF/CNF 思路说明。
- 与 demosaic 后 RGB denoise 对比。

建议新增产物：

- `stage3_cpp_isp/include/cpp_isp/raw_denoise.hpp`
- `stage3_cpp_isp/src/raw_denoise.cpp`
- `stage3_cpp_isp/reports/raw_domain_denoise_report.md`

验收标准：

- 同一 RAW 样本对比 demosaic 前后降噪差异。
- 输出保边、伪彩、噪声残留、性能对比。
- 说明 RAW 域降噪的优势和风险。

面试价值：

- 回答“为什么很多降噪要放在 RAW 域？”
- 回答“RAW 域处理和 RGB 域处理有什么不同？”

### Stage 3-U3：多帧 HDR 与 ghosting 分析

优先级：P2

目标：

- 把已有 HDR toy 升级为更接近真实多帧问题的实验。

建议实现：

- 简单平移对齐。
- 运动区域 mask。
- short/long exposure fusion。
- ghosting 失败案例。

建议新增产物：

- `stage3_cpp_isp/reports/multiframe_hdr_ghosting_report.md`

验收标准：

- 至少有静态场景和运动场景对比。
- 能展示 ghosting 的产生和缓解。
- 能说明多帧 HDR 的画质收益与失败边界。

面试价值：

- 回答“多帧 HDR 为什么难？”
- 回答“运动场景如何避免鬼影？”

## 七、阶段 4 升级方案：系统串联、内存/功耗约束、部署边界

阶段 4 已经有比较完整的模型部署链路，但 README 里也明确写了两个边界：当前链路还是 RGB normalize 到 AI denoise，尚未完成与阶段 3 C++ ISP 串联；移动端/ARM 未完成。升级重点是把它从“模型部署实验”推进到“AI-ISP pipeline 部署设计”。

### Stage 4-U1：串联 Stage 3 C++ ISP 与 Stage 4 AI 模型

优先级：P0

目标：

- 形成一个更完整的端到端 AI-ISP pipeline：传统 ISP 前后处理 + AI 模型推理 + 质量/性能评估。

建议链路：

```text
RAW / pseudo RAW
  -> Stage 3 C++ preprocessing
  -> AI denoise / enhancement model
  -> Stage 3 C++ postprocessing
  -> image quality + latency report
```

建议新增产物：

- `stage4_deploy_isp/reports/stage3_stage4_pipeline_integration.md`
- `stage4_deploy_isp/configs/isp_ai_pipeline_contract.yaml`

验收标准：

- 明确每一段的数据格式、range、layout、dtype。
- 输出端到端 latency breakdown。
- 输出画质指标和失败案例。
- 能解释传统模块与 AI 模块的职责边界。

面试价值：

- 回答“AI-ISP 如何和传统 ISP pipeline 结合？”
- 回答“部署时最容易出错的数据 contract 是什么？”

### Stage 4-U2：内存峰值与端侧资源预算

优先级：P1

目标：

- 从 latency 扩展到内存和资源约束。

建议实现：

- 统计输入 tensor、输出 tensor、中间 buffer、模型权重大小。
- 对比 FP32 / FP16 / INT8 的内存占用。
- 估算 1080P / 4K 下 buffer size。
- 记录 batch=1 steady-state 资源预算。

建议新增产物：

- `stage4_deploy_isp/reports/memory_budget_report.md`

验收标准：

- 给出每个 backend 的模型大小、输入输出 buffer、主要中间数据。
- 给出 512、1080P、4K 三档估算。
- 报告中说明哪些数据是实测，哪些是估算。

面试价值：

- 回答“端侧部署除了速度，还要看什么？”
- 回答“为什么 4K 和 512 patch 的部署难度不同？”

### Stage 4-U3：功耗与移动端替代验证

优先级：P2

目标：

- 在没有真实手机 NPU 的情况下，建立合理的功耗/移动端约束表达。

可行方案：

- 如果有 Windows 笔记本电源监控工具，只做粗粒度功耗趋势，不夸大。
- 如果没有设备，做“功耗评估设计文档”，说明真实设备上如何采集。
- 增加 NCNN/MNN 的设计边界，不强行声称完成移动端。

建议新增产物：

- `stage4_deploy_isp/reports/mobile_power_evaluation_plan.md`

验收标准：

- 明确说明未完成真实移动端实测。
- 给出真实实测需要的设备、工具、指标和流程。
- 给出当前 PC/GPU 环境下能证明什么、不能证明什么。

面试价值：

- 回答“你怎么评估功耗？”
- 避免被追问时把 PC latency 误说成移动端能力。

## 八、跨阶段升级：调试案例库

优先级：P0

目标：

- 形成一套贯穿 stage1-stage4 的“影像问题诊断案例库”。
- 这是最像真实工作的升级项。

建议案例类型：

1. 偏色：AWB/CCM 问题。
2. 暗角：LSC 问题。
3. 暗部噪声：RAW noise / denoise 问题。
4. 过曝：AE / tone mapping / clipping 问题。
5. 边缘伪彩：demosaic 问题。
6. 锐化光晕或局部对比异常：LTM / tone 问题。
7. AI 过平滑：模型 loss / training data 问题。
8. INT8 画质损失：量化校准分布问题。

建议新增产物：

- `study-roadmap/影像问题调试案例库建设方案.md`
- 或分阶段放入：
  - `stage1_soft_isp/reports/debug_cases/`
  - `stage2_ai_isp/reports/debug_cases/`
  - `stage3_cpp_isp/reports/debug_cases/`
  - `stage4_deploy_isp/reports/debug_cases/`

单个案例模板：

```markdown
# Case: 低照场景暗部噪声过强

## 现象

## 输入条件

## 初步判断

## 定位过程

## 修改方案

## 指标变化

## 视觉对比

## 副作用

## 面试表达
```

验收标准：

- 至少 8 个案例。
- 每个案例都有图、指标、原因、修改和副作用。
- 每个案例都能映射到一个 ISP 模块或部署环节。

面试价值：

- 回答“你调过什么问题？”
- 回答“你怎么定位画质问题？”

## 九、建议执行顺序

### 第一轮：最小高价值升级，约 2-3 周

目标：快速补上最影响可信度的空白。

1. Stage 1-U1：真实 DNG 采集与 RAW 数据体检。
2. Stage 1-U2：工业 IQ 指标补齐。
3. Stage 1-U3：AWB 进阶与色温估计。
4. Stage 3-U1：性能优化故事化。
5. Stage 4-U1：Stage 3 C++ ISP 与 Stage 4 AI 模型串联设计。
6. 跨阶段调试案例库先完成 3 个案例。

验收物：

- 3-5 份报告。
- 一组真实 RAW 数据分析图。
- 一张性能优化对比表。
- 一张端到端 pipeline contract 图。
- 3 个可面试讲述的调试案例。

### 第二轮：标定与 3A，约 3-4 周

目标：补消费电子 / 手机厂更关心的 tuning 能力。

1. Stage 1-U4：Histogram-based AE 仿真。
2. Stage 1-U5：Flat-field LSC 与 ColorChecker CCM 标定。
3. Stage 2-U1：RAW-aware 噪声建模与数据构造。
4. 调试案例库扩展到 6 个案例。

验收物：

- AE 收敛报告。
- LSC/CCM 标定报告。
- RAW-aware noise modeling 报告。
- 6 个调试案例。

### 第三轮：多帧与端侧约束，约 4-6 周

目标：提升差异化，但不是最急。

1. Stage 2-U2：特殊场景 failure case 扩展。
2. Stage 2-U3：AI 模块替换传统 ISP 模块边界实验。
3. Stage 3-U2：RAW 域降噪模块补强。
4. Stage 3-U3：多帧 HDR 与 ghosting 分析。
5. Stage 4-U2：内存峰值与端侧资源预算。
6. Stage 4-U3：功耗与移动端替代验证。

验收物：

- RAW 域降噪报告。
- 多帧 HDR / ghosting 报告。
- AI module boundary 报告。
- memory budget 报告。
- mobile power evaluation plan。

## 十、阶段升级清单

| 阶段 | 当前强项 | 最值得升级 | 优先级 |
|---|---|---|---|
| Stage 1 | Soft-ISP pipeline、RAW 基础、模块报告 | 真实 DNG、IQ 指标、AWB/AE、LSC/CCM 标定 | 最高 |
| Stage 2 | AI-ISP 训练评估、SIDD、NAFNet-lite、failure case | RAW-aware 数据构造、特殊场景、AI 模块边界 | 中高 |
| Stage 3 | C++17、对齐测试、benchmark、HDR toy、pipeline | 性能故事化、RAW 域降噪、多帧 ghosting | 高 |
| Stage 4 | ONNX/ORT/TensorRT/INT8/CUDA、latency | stage3-stage4 串联、内存预算、功耗设计 | 高 |
| 跨阶段 | 已有报告体系 | 调试案例库 | 最高 |

## 十一、最终目标状态

升级完成后，这个项目应当能支撑如下表达：

> 我做过一个从真实 RAW 分析、传统 ISP pipeline、AI-ISP 图像恢复、C++ 性能优化，到 ONNX/TensorRT/INT8/CUDA 部署的完整影像算法作品集。项目里不仅有模块实现，还有真实 DNG 分析、IQ 指标、AWB/AE 调试、LSC/CCM 标定、RAW-aware 数据构造、性能优化对比、部署 contract 和失败案例库。它不是量产手机 ISP 项目，但它证明我具备进入消费电子/手机厂/解决方案公司后快速参与真实 tuning、算法评估和工程落地的基础。

需要避免的表达：

- 不要说已经有量产 ISP tuning 经验。
- 不要说项目等同于终端厂真实业务。
- 不要把开源数据上的 PSNR/SSIM 当作完整画质评价。
- 不要把 PC/GPU latency 当作移动端功耗或 NPU 性能。

## 十二、结论

当前项目最应该升级的不是通用算法题，也不是再堆更多普通课程，而是把已有四阶段主干进一步变成“影像岗位证据链”。

优先级最高的 5 件事：

1. 真实 DNG 采集与 RAW 体检。
2. 工业 IQ 指标和 ROI 画质分析。
3. AWB/AE/LSC/CCM 的调试与标定报告。
4. C++ 性能优化故事化。
5. 跨阶段影像问题调试案例库。

这些完成后，项目会从“系统学习作品集”升级为“可以拿去争取影像算法实习和秋招面试的工程证据集”。
