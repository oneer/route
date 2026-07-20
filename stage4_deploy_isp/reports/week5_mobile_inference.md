# Week 5：移动端路径（设计章节，未完成真机部署）

## 1. 为什么需要

桌面 NVIDIA GPU 结果不能代替 Android/ARM 的算子、内存、温度、功耗和启动时间约束。

## 2. 输入输出协议

移动端仍需保持 RGB、range、layout 和 clamp 一致；若框架偏 NHWC，转换必须显式记录，不能静默改变协议。

## 3. 链路角色

NCNN/MNN 面向移动 CPU/Vulkan；TFLite 面向 Android/iOS delegate 生态；OpenVINO 面向 Intel；TensorRT 面向 NVIDIA GPU。当前项目已选择 TensorRT 作为已实践后端，NCNN 作为后续手机岗位实践路径。

## 4. 核心概念/API

模型转换、算子支持、Vulkan、FP16 storage/arithmetic、线程、arm64 交叉编译、benchmark 和 adb。当前均未形成执行证据。

## 5. 对应文件

本章仅有设计文档；仓库没有 NCNN/MNN model、runner、Android 工程或设备日志。

## 6. 运行命令与环境

当前 PATH 无 `onnx2ncnn`、`ncnnoptimize`、`MNNConvert`、`adb`，因此不提供伪装成已验证的命令结果。转换命令应在工具安装后按对应官方版本文档生成。

## 7. 正确输出

未来必须包含 param/bin 或 mnn 模型、raw tensor 对齐、设备 benchmark、设备与温度记录。当前状态：不存在。

## 8. 对齐指标与阈值

未来仍报告 max/mean/RMSE、PSNR/SSIM 和最差 crop；阈值沿用项目 contract，新增设备内存与温度条件。

## 9. 常见失败与排查

unsupported op → converter version → layout/packing → FP16 storage → Vulkan device → thread affinity → 输出 tensor → PNG。

## 10. 性能测量

必须记录设备型号、SoC、OS、backend、线程、CPU/GPU/Vulkan、warmup/runs、温度和是否含 I/O；当前无数据。

## 11. Tradeoff

| 后端 | 目标硬件 | 精度/量化 | 工程特点 |
|---|---|---|---|
| NCNN | ARM CPU/Vulkan | FP32/FP16/INT8 | 轻量、移动友好，需转换与算子核对 |
| MNN | 移动/多后端 | FP32/FP16/INT8 | 后端丰富，工具链与部署包更完整 |
| TFLite | Android/iOS | FP32/FP16/INT8 | delegate 生态强，ONNX 转换链可能更曲折 |
| OpenVINO | Intel CPU/GPU/NPU | FP32/FP16/INT8 | Intel 平台工具成熟 |
| TensorRT | NVIDIA GPU | FP32/FP16/INT8 | 性能强但平台绑定明显 |

## 12. 证据边界

没有真实 Android/ARM、功耗、内存、温度或移动 GPU 证据，不能声称“完成移动端部署”。

## 13. 练习与掌握标准

后续选择 NCNN：在一台真实 arm64 Android 设备完成 CPU/Vulkan on/off、raw tensor 对齐、温度前后和 p50/p90，才将本周状态改为完成。

## 14. 真机部署应从哪里开始

```text
选择目标设备/SoC/OS
  -> 查询 runtime 与算子支持
  -> 转换模型并保存工具版本
  -> 桌面端先做 raw tensor 对齐
  -> arm64 构建 runner
  -> adb 推送 model/input/binary
  -> CPU 单线程 correctness
  -> CPU 多线程、Vulkan/GPU/NPU delegate
  -> 冷启动、steady-state、内存、温度和功耗
  -> 长时间运行与最差 case
```

为什么先做 CPU 单线程：它是最容易定位正确性的路径。直接打开 Vulkan/NPU 后出现误差，很难区分转换、layout、precision、delegate 或驱动问题。

## 15. 移动端关键词与参数表

| 关键词/参数 | 含义 | 为什么要记录 | 常见陷阱 |
|---|---|---|---|
| arm64 ABI | Android 64-bit ARM 二进制接口 | 决定 runner/库是否可加载 | x64 桌面结果不能代替 arm64 |
| thread count/affinity | CPU 线程数及绑定的大/小核 | 影响 latency、功耗和稳定性 | 线程越多不一定越快，温度会改变频率 |
| FP16 storage/arithmetic | 权重/激活存储与计算精度 | 两者可能独立配置 | 只开 storage 不等于全程 FP16 compute |
| Vulkan/delegate | 把支持的图节点下放到 GPU/NPU | 可能提速也可能部分 fallback | 必须检查实际 partition 和 copy |
| cold start | 加载、编译/cache 和首次推理 | 影响相机首帧体验 | 不能拿 warm steady-state 代替 |
| RSS/thermal/power | 进程内存、温度、功耗 | 决定长时间可用性 | 一次短 benchmark 看不到降频 |

## 16. Week 5 面试五问

1. 为什么桌面 TensorRT 结果不能证明 Android 部署能力？硬件、runtime、算子、内存和功耗环境不同。
2. CPU/Vulkan/NPU 比较怎样保证公平？同输入、精度、线程/频率条件、warmup 和计时范围。
3. delegate 部分 fallback 为什么可能更慢？额外分区和 host/device tensor 转换会抵消算子收益。
4. p50/p90、cold start、thermal steady-state 分别回答什么体验问题？
5. 没有设备时这周能完成什么？只能完成设计、合同和验收清单；结果状态必须保持 `not_run`。

## 17. 面向高通 ISP 岗位的端侧路径

本周现有 NCNN 路径适合作为 vendor-neutral 的 Android CPU/Vulkan 学习入口；若目标是高通岗位，还应增加 Qualcomm 专用分支，但两者不能混为同一证据：

```text
通用路径：ONNX -> NCNN/TFLite/ORT Mobile -> ARM CPU / Vulkan / delegate
高通路径：ONNX -> QAIRT/QNN 工具链 -> CPU/GPU/HTP backend -> Snapdragon 真机
相机产品路径：camera buffer/metadata -> vendor camera framework/ISP -> AI node -> downstream
```

- **QAIRT/QNN**：高通模型转换、图准备和 runtime/backend 工具链；具体可用能力受 SDK、SoC、版本和算子支持约束。
- **HTP**：Hexagon Tensor Processor 相关加速 backend；“选择 HTP”不代表整图都成功下放，仍要检查 partition、fallback 和数据转换。
- **HVX**：Hexagon Vector eXtensions，常涉及 DSP 向量化；不能把 HTP/NPU 结果自动表述为手写 HVX 优化。
- **Adreno**：高通 GPU；GPU delegate 的收益取决于算子支持、图分区和 buffer copy。
- **CAMX/Camera framework**：相机请求、buffer 和 metadata 流水线相关产品域。仓库没有厂商内部源码、设备或接入证据，因此只学习接口思想，不声称完成集成。

截至报告所载工具链版本，学习者应以已安装 SDK 内文档和 Qualcomm 官方 AI Hub/QAIRT 文档为准，并在报告中冻结访问日期、SDK/SoC/Android 版本。岗位价值不在背缩写，而在能解释 tensor 如何从 camera buffer 到 runtime、在哪些边界复制、失败时如何证明实际执行 backend。

## 18. 真机实验矩阵与计量协议

同一设备至少建立以下矩阵：CPU 1 线程、CPU 多线程、GPU/Vulkan、HTP/NPU（实际支持时）；每格保持同一模型、输入、精度目标和输出验收。记录 cold start、warmup 次数、steady-state p50/p90、RSS/峰值内存、机身/SoC 温度、功耗采样方法、运行时长和降频点。

```text
T_camera_e2e = T_buffer_acquire + T_format/resize + T_copy_or_import
             + T_inference + T_post + T_buffer_release
```

若只测 `runtime.run()`，必须标作 session latency，不能称 camera e2e。zero-copy 也不能只看 API 名称：需要画出每个 buffer 的 owner、format、stride、memory domain 和 import/export 次数，并用 profiler 或 trace 证明没有隐式 staging。

## 19. 失败定位与证据升级条件

| 现象 | 第一检查 | 可能原因 |
|---|---|---|
| delegate/HTP 比 CPU 慢 | partition 与 copy 次数 | 小图、多分区、fallback 或转换开销 |
| 首帧很慢 | 模型加载/编译/cache | cold start 被 steady-state 隐藏 |
| 长跑逐渐变慢 | 温度/频率/线程亲和性 | thermal throttling |
| 桌面一致、真机错误 | layout/range/precision/op support | 转换或 backend 语义不同 |
| RSS/功耗异常 | buffer 生命周期与重复分配 | cache、内存泄漏或 staging |
| 声称 zero-copy 但延迟无改善 | trace 中的隐式 copy | format/stride 不兼容导致回退 |

状态从 `not_run` 升级为 `verified_real` 至少需要：设备与环境可追溯、raw float correctness 对齐、实际 backend/partition 证据、冷/热/长跑性能、内存与功耗数据、失败样本和复现命令。只有设计表和命令草案时必须继续标记 `not_run`。

## 20. 本周学习验收清单

- [ ] 能比较 vendor-neutral 与 Qualcomm 专用部署路径的作用和证据边界。
- [ ] 能解释 QAIRT/QNN、HTP、HVX、Adreno、CAMX 各自处在哪一层，不混用概念。
- [ ] 能设计 CPU/GPU/HTP 公平实验矩阵并定义 cold、warm、thermal 指标。
- [ ] 能画出 camera buffer 到模型输出的 owner、format、stride、copy 和同步点。
- [ ] 能识别部分 fallback、隐式 copy 和降频造成的“加速失败”。
- [ ] 能列出从 `not_run` 升级为 `verified_real` 所需的最小证据包。
- [ ] 能准确陈述当前边界：仓库只有移动端执行设计，没有 Snapdragon 真机结果。

## 21. 高通官方学习入口（2026-07-19 核对）

- [Qualcomm AI Hub 文档](https://app.aihub.qualcomm.com/docs/index.html)：用于理解模型编译、真实设备 profile、推理输出验证与可交付模型的闭环；云端真机结果仍要记录 device/runtime/job 配置。
- [QAIRT/QNN 文档入口](https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-4/developing-apps-qualcomm-neural-processing-sdk.html)：用于按当前 SDK 查看 backend、tensor/memory layout、HTP、GPU、profiling 和 API；报告里的命令必须以实际安装版本为准。
- [QAIRT Converter](https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-10/qairt_converter.html)：用于理解输入输出配置、转换资产和 backend 相关准备；“转换成功”之后仍要做 raw tensor correctness。
- [AI Engine Direct HTP delegate 教程](https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-10/tutorial_qtld_net_run.html)：用于理解 Android/ADB、stub/skel 库与 HTP backend 的实际运行依赖；库名和架构必须匹配目标 SoC/SDK。

这些入口会随 SDK 发布变化，不把网页示例版本硬编码成仓库的已验证版本；真实实验应保存安装包版本、离线文档版本或访问日期。

## 22. 高通岗位补强：Camera request、CAMX/CHI 与 QNN/HTP 白板模型

本节只建立公开信息层面的系统心智模型。CAMX/CHI 的具体接口、节点名、可用 metadata 和版本行为依赖平台/客户权限；仓库没有高通内部源码或合作伙伴 SDK，不能把概念学习写成平台接入经验。

### 22.1 从 Camera request 看数据与控制

一个便于面试白板表达的抽象是：

```text
application capture request
  -> settings/controls metadata + output stream buffers
  -> camera graph nodes consume/produce buffers
  -> sensor/ISP/stats/3A/feature processing
  -> result metadata + output buffers
  -> application/display/encoder
```

算法节点不能只关心 `float*`。每个输入还可能带有 width/height、pixel format、plane/row stride、crop/rotation、timestamp/frame id、exposure/gain/WB、color space、memory handle 和 acquire fence；输出要定义 owner、release fence 和 result metadata。metadata 与 buffer 的 frame id 错配，会产生看似算法不稳定的系统错误。

CAMX 可理解为高通 Camera pipeline/framework 语境，CHI 是扩展/集成相关语境；面试中应描述“request、node、port、buffer、metadata、fence、dependency”的通用关系，而不是编造某版本私有 API。实际工作首先阅读目标平台随附文档、sample 和日志工具。

### 22.2 QNN/HTP 推理生命周期

公开 QAIRT/QNN 文档中的常见对象可按以下顺序理解：

```text
log/profile
  -> backend/device
  -> context
  -> graph + tensors/op config
  -> finalize/prepare
  -> bind buffers
  -> execute + signal/fence
  -> inspect profile/output
  -> destroy in reverse ownership order
```

HTP backend 的 stub/skel、SoC 架构、库版本和 context binary 必须匹配。backend 创建成功或 delegate 名称出现，只证明入口可用；仍需检查算子支持、graph partition、fallback、转换节点、量化参数和实际 profiling。CPU/GPU/HTP 的输出要回到同一 raw float/quantized contract 对齐。

### 22.3 Zero-copy 的充分证据

“使用 AHardwareBuffer/dma-buf/device tensor”不是 zero-copy 结论。至少要证明：

- producer 与 consumer 支持相同 pixel/tensor format、stride、alignment 和 memory handle；
- import 没有触发 format conversion 或 staging allocation；
- acquire/release fence 正确，且没有为等待方便而做全局同步；
- profiler/trace 中 copy count、bytes 和 memory domain 与设计图一致；
- buffer lifetime 覆盖异步执行，多 in-flight request 不会复用覆盖。

若 Camera 输出是 YUV/UBWC 等格式，而模型要求 RGB/NCHW float，颜色转换、去压缩、resize、layout 和 normalize 很可能仍需要计算或新 buffer。正确目标是减少不必要 copy 和 domain crossing，不是为了简历强行宣称“全链路零拷贝”。

### 22.4 真机最小验收顺序

1. 在 host/CPU path 用固定 tensor 建立 correctness golden；
2. 在目标 Android/SoC 确认 SDK、ABI、库依赖和模型 hash；
3. 单独运行 QNN CPU backend，对齐输入输出；
4. 切换 GPU/HTP，检查 graph partition/fallback 和量化合同；
5. 记录 cold load/finalize、warm execute、p50/p90、RSS、温度和功耗；
6. 接入 Camera buffer 后重新核对 format/stride/frame id/fence/copy；
7. 做多帧、超时、OOM、backend failure 与 fallback 测试；
8. 才能把状态从 `not_run` 提升为对应设备/版本的 `verified_real`。

### 22.5 系统面试五问

1. Camera metadata 与 image buffer 为什么必须用同一个 frame/request identity 关联？
2. acquire/release fence 各保护什么，错误同步会出现 correctness 还是 latency 问题？
3. QNN backend 创建成功为什么不能证明整图在 HTP 上执行？
4. Camera buffer 与 NPU tensor format 不一致时，zero-copy 目标应怎样重新定义？
5. 如果 HTP 比 CPU 慢，怎样区分小图开销、fallback、partition、量化、copy 和 thermal 原因？

当前能回答的是架构、合同和验收方法；CAMX/CHI 接口、QNN context 构建、Snapdragon HTP profile、Camera buffer import 和真机 fallback 都未运行。
