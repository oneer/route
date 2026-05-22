# 阶段 4：端侧 AI-ISP 部署与 CUDA 推理学习路线

> **适用对象**：已经完成阶段 1 的传统 Soft-ISP、阶段 2 的 AI-ISP 图像恢复 baseline、阶段 3 的 C++ ISP 工程化项目，具备 Python / C++ / CUDA 基础，做过简单 CUDA 卷积算子，但还缺少完整的 PyTorch → ONNX → C++ 推理 → 加速 / 量化 / 对齐 / 性能报告闭环。
>
> **阶段周期**：7 周。
>
> **阶段目标**：把阶段 2 训练出的轻量图像恢复模型部署到 C++ 推理链路中，并与阶段 3 的 C++ ISP 前后处理模块串起来；完成 ONNX 导出、ONNX Runtime baseline、TensorRT 或 NCNN/MNN 加速、FP16 / INT8 对比、输入输出对齐、延迟 / 显存 / 画质损失评估和最终系统报告。
>
> **阶段产出**：一个 `deploy_isp_stage4/` 项目，一个可导出的 PyTorch 模型，一个 ONNX 模型，一个 C++ 推理程序，一个 TensorRT / NCNN / MNN / ONNX Runtime 中至少一个高性能后端，一份 FP32 / FP16 / INT8 对比报告，一份端到端 AI-ISP 推理系统报告。

---

## 0. 阶段四的正确学习姿势

阶段四不要学成“我会把模型转成 ONNX”。部署能力真正考察的是：

- **输出是否一致**：PyTorch、ONNX Runtime、TensorRT / NCNN 的输出误差是否可解释。
- **输入输出是否清楚**：NCHW / NHWC、RGB / BGR、RAW 4ch、range、dtype、normalization 是否严格一致。
- **性能是否真实**：是否区分模型推理时间、前后处理时间、H2D / D2H 拷贝时间、端到端时间。
- **量化是否可接受**：INT8 后 PSNR / SSIM / LPIPS 掉多少，哪些场景最容易出问题。
- **部署是否工程化**：配置、日志、benchmark、profile、失败 fallback、固定测试集和版本记录是否完整。

你过去写过 CUDA 卷积算子，这是一块优势。但阶段四的主线不是手写复杂 CUDA 网络算子，而是完成一个可复现、可对齐、可测量、可解释的部署闭环。

---

## 1. 最终项目结构

```text
deploy_isp_stage4/
├── README.md
├── CMakeLists.txt
├── requirements.txt
├── configs/
│   ├── export_onnx.yaml
│   ├── onnxruntime_fp32.yaml
│   ├── tensorrt_fp16.yaml
│   ├── tensorrt_int8.yaml
│   └── ncnn_mobile.yaml
├── models/
│   ├── pytorch/
│   │   └── nafnet_lite.pth
│   ├── onnx/
│   │   ├── nafnet_lite.onnx
│   │   └── nafnet_lite_simplified.onnx
│   ├── trt/
│   │   └── nafnet_lite_fp16.engine
│   └── ncnn/
│       ├── nafnet_lite.param
│       └── nafnet_lite.bin
├── data/
│   ├── calibration/              # INT8 calibration 样本
│   ├── test_inputs/              # 固定测试输入
│   ├── pytorch_outputs/          # PyTorch golden 输出
│   └── references/               # GT / rawpy / 阶段2输出
├── deploy/
│   ├── export_onnx.py
│   ├── validate_onnx.py
│   ├── build_trt_engine.py
│   ├── calibrator.py
│   ├── run_onnxruntime.py
│   └── compare_outputs.py
├── cpp/
│   ├── include/
│   │   ├── image_tensor.hpp
│   │   ├── preprocess.hpp
│   │   ├── postprocess.hpp
│   │   ├── onnxruntime_runner.hpp
│   │   ├── tensorrt_runner.hpp
│   │   ├── ncnn_runner.hpp
│   │   └── benchmark.hpp
│   ├── src/
│   │   ├── preprocess.cpp
│   │   ├── postprocess.cpp
│   │   ├── onnxruntime_runner.cpp
│   │   ├── tensorrt_runner.cpp
│   │   ├── ncnn_runner.cpp
│   │   └── main.cpp
│   └── tests/
├── cuda_kernels/
│   ├── pack_raw.cu
│   ├── normalize.cu
│   └── simple_filter.cu
├── scripts/
│   ├── 01_export_and_check_onnx.py
│   ├── 02_compare_backends.py
│   ├── 03_benchmark_latency.py
│   ├── 04_quantization_eval.py
│   └── 05_visualize_deploy_errors.py
└── reports/
    ├── stage4_report.md
    ├── output_alignment_report.md
    ├── latency_report.md
    ├── quantization_report.md
    └── figures/
```

**项目验收标准**：

- 阶段 2 训练的轻量模型能成功导出 ONNX。
- ONNX Runtime 输出与 PyTorch 输出可对齐，误差有统计表。
- 至少完成一种高性能后端：TensorRT、NCNN、MNN 或 OpenVINO。
- 至少完成 FP32 vs FP16 对比；有条件则完成 INT8 calibration 和量化评估。
- 延迟报告区分 preprocess、inference、postprocess、copy、end-to-end。
- 画质报告包含 PSNR / SSIM / LPIPS 和失败案例。
- C++ 程序能读取固定输入，执行前处理、推理、后处理并保存输出图。

---

## 2. 公开资源调研与使用方式

### 2.1 ONNX / ONNX Runtime

| 资源 | 链接 | 阶段四怎么用 |
|---|---|---|
| PyTorch ONNX Exporter | https://docs.pytorch.org/docs/stable/onnx.html | 学 `torch.onnx.export` / `torch.export`、dynamic axes / dynamic shapes、opset 和导出限制。 |
| ONNX Runtime Python API | https://onnxruntime.ai/docs/api/python/api_summary.html | 用 Python 快速验证 ONNX 输出和 PyTorch 是否一致。 |
| ONNX Runtime C/C++ API | https://onnxruntime.ai/docs/api/c/ | 写 C++ baseline 推理，作为 TensorRT / NCNN 前的稳定参考。 |
| ONNX Runtime Graph Optimizations | https://onnxruntime.ai/docs/performance/model-optimizations/graph-optimizations.html | 理解 constant folding、node fusion、layout 优化。 |
| ONNX Runtime Quantization | https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html | 学动态量化、静态量化、calibration、QDQ / QOperator 格式。 |

**使用要求**：ONNX Runtime 是阶段四的第一后端。先用它验证模型语义，再考虑 TensorRT / NCNN。

### 2.2 TensorRT / NVIDIA 部署

| 资源 | 链接 | 阶段四怎么用 |
|---|---|---|
| TensorRT Documentation | https://docs.nvidia.com/deeplearning/tensorrt/ | 总入口。查 ONNX parser、builder、engine、runtime、plugins。 |
| TensorRT Developer Guide | https://docs.nvidia.com/deeplearning/tensorrt/developer-guide/index.html | 学 engine 构建、dynamic shapes、optimization profile、FP16 / INT8。 |
| TensorRT Best Practices | https://docs.nvidia.com/deeplearning/tensorrt/best-practices/index.html | 学 latency measurement、profile、memory、performance checklist。 |
| TensorRT GitHub | https://github.com/NVIDIA/TensorRT | 参考 samples、plugins、工具链和 issue。 |
| Polygraphy | https://github.com/NVIDIA/TensorRT/tree/main/tools/Polygraphy | 做 ONNX / TensorRT 输出对比、debug 和模型简化。 |
| CUDA C++ Programming Guide | https://docs.nvidia.com/cuda/cuda-c-programming-guide/ | 查 CUDA 编程模型、memory hierarchy、streams。 |
| CUDA Best Practices Guide | https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/ | 学 coalesced access、shared memory、streams、profiling。 |
| Nsight Systems | https://docs.nvidia.com/nsight-systems/UserGuide/index.html | 分析端到端 timeline、CPU/GPU overlap、H2D/D2H 拷贝。 |
| Nsight Compute | https://docs.nvidia.com/nsight-compute/NsightCompute/index.html | 分析具体 CUDA kernel 的访存、occupancy、throughput。 |

**使用要求**：TensorRT 适合 NVIDIA GPU 部署。阶段四重点不是写 plugin，而是先掌握 ONNX → engine → C++ inference → profile → FP16/INT8。

### 2.3 NCNN / MNN / 移动端推理

| 资源 | 链接 | 阶段四怎么用 |
|---|---|---|
| NCNN GitHub | https://github.com/Tencent/ncnn | 移动端推理首选之一，学 onnx2ncnn、ncnnoptimize、Vulkan。 |
| NCNN Wiki | https://github.com/Tencent/ncnn/wiki | 查转换、量化、benchmark、Vulkan 选项。 |
| NCNN int8 quantization | https://github.com/Tencent/ncnn/wiki/quantized-int8-inference | 学 calibration table、量化流程和限制。 |
| MNN GitHub | https://github.com/alibaba/MNN | 阿里移动端推理框架，支持模型转换、量化、后端选择。 |
| MNN Docs | https://mnn-docs.readthedocs.io/ | 查转换、推理、量化、benchmark。 |
| Real-ESRGAN ncnn Vulkan | https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan | 图像恢复模型移动端 / Vulkan 部署参考。 |
| waifu2x ncnn Vulkan | https://github.com/nihui/waifu2x-ncnn-vulkan | 图像放大 / 降噪 ncnn Vulkan 部署参考，适合看工程组织。 |

**使用要求**：如果目标岗位偏手机 / 端侧 / 嵌入式，NCNN / MNN 比 TensorRT 更贴近。阶段四至少了解 NCNN 转换流程。

### 2.4 OpenVINO / TFLite / 其他部署路径

| 资源 | 链接 | 阶段四怎么用 |
|---|---|---|
| OpenVINO Documentation | https://docs.openvino.ai/ | Intel 平台部署参考，学 model conversion、benchmark_app、NNCF。 |
| OpenVINO Benchmark Tool | https://docs.openvino.ai/2024/learn-openvino/openvino-samples/benchmark-tool.html | 学如何标准化测 latency / throughput。 |
| TensorFlow Lite Post-training Quantization | https://www.tensorflow.org/lite/performance/post_training_quantization | 学移动端量化概念，代表性数据集思想可迁移到其他框架。 |
| TensorFlow Lite GPU Delegate | https://www.tensorflow.org/lite/performance/gpu | 了解 Android / 移动 GPU delegate 的限制和收益。 |

### 2.5 实用博客 / 工具

| 资源 | 链接 | 阶段四怎么用 |
|---|---|---|
| ONNX Simplifier | https://github.com/daquexian/onnx-simplifier | 简化 ONNX 图，减少转换失败和冗余节点。 |
| Netron | https://netron.app/ | 可视化 ONNX / NCNN / TensorRT 图，检查输入输出、算子、shape。 |
| onnxsim 文档 | https://github.com/daquexian/onnx-simplifier | 导出 ONNX 后必跑一次，但简化前后要验证输出一致。 |
| NVIDIA trtexec | https://docs.nvidia.com/deeplearning/tensorrt/latest/reference/command-line-programs.html | 快速构建 engine、测试 FP16/INT8、测 latency。 |

---

## 3. 七周详细路线

### Week 0.5：固定部署模型和测试基准

**目标**：确定一个可部署的小模型和固定测试集，避免阶段四一边换模型一边调部署。

**学习内容**：

- 部署模型选择原则。
- 固定输入输出协议。
- PyTorch baseline 指标和延迟。

**具体步骤**：

1. 从阶段 2 选择一个模型：
   - 优先 `UNet-lite` 或 `NAFNet-lite`
   - 暂不选 Restormer / 大 Transformer
2. 固定输入协议：
   - `NCHW`
   - `float32`
   - RAW 4ch 或 RGB 3ch
   - range `[0, 1]` 或 normalized range
3. 固定输出协议：
   - RGB 3ch 或 restored RAW 4ch
   - range
   - 是否需要 clamp
4. 准备 20～50 张固定测试输入：
   - 正常光
   - 低光
   - 高 ISO
   - 高频纹理
   - 高动态范围
5. 用 PyTorch 跑 baseline：
   - output
   - PSNR / SSIM / LPIPS
   - latency
   - 显存峰值

**掌握标准**：

- 能说明为什么部署阶段不适合不断换模型。
- 能解释输入输出协议中 shape、layout、dtype、range 的每一项。
- 能用固定测试集作为后续所有后端的 golden baseline。

**交付物**：

- `configs/export_onnx.yaml`
- `data/test_inputs/`
- `data/pytorch_outputs/`
- `reports/week0_deploy_baseline.md`

### Week 1：PyTorch → ONNX 导出与语义对齐

**目标**：稳定导出 ONNX，并证明 ONNX Runtime Python 输出与 PyTorch 一致。

**学习内容**：

- ONNX opset。
- dynamic axes / dynamic shapes。
- ONNX checker。
- onnxsim。
- ONNX Runtime Python 推理。
- 输出误差统计。

**具体步骤**：

1. 写 `deploy/export_onnx.py`：
   - load checkpoint
   - set `eval()`
   - dummy input
   - export ONNX
   - dynamic shape 可选
2. 用 `onnx.checker.check_model()` 检查。
3. 用 Netron 打开模型，检查：
   - input name
   - output name
   - shape
   - unsupported ops
4. 用 onnxsim 简化模型。
5. 用 ONNX Runtime Python 跑固定测试集。
6. 对比 PyTorch 输出：
   - max abs error
   - mean abs error
   - PSNR
   - error map

**小实验**：

- `opset 12 / 17 / 18` 对比导出结果。
- dynamic shape vs fixed shape。
- onnxsim 前后输出对比。
- `torch.no_grad()`、`model.eval()` 忘记设置时输出是否变化。

**掌握标准**：

- 能解释 ONNX 不是模型加速器，而是中间表示。
- 能说明 export 成功不代表输出正确。
- 能定位常见导出问题：unsupported op、dynamic shape、grid_sample、LayerNorm、custom op。
- 能生成 ONNX 与 PyTorch 的对齐报告。

**交付物**：

- `deploy/export_onnx.py`
- `deploy/validate_onnx.py`
- `scripts/01_export_and_check_onnx.py`
- `reports/week1_onnx_alignment.md`

### Week 2：ONNX Runtime C++ 推理 baseline

**目标**：建立 C++ 推理 baseline，作为所有高性能后端的正确性参考。

**学习内容**：

- ONNX Runtime C++ API。
- Tensor shape、allocator、session options。
- CPU EP / CUDA EP 概念。
- C++ 前处理和后处理。
- C++ 输出与 Python 输出对齐。

**具体步骤**：

1. 写 `onnxruntime_runner.hpp/cpp`。
2. 实现 C++ 输入准备：
   - 读取 `.npy` / `.bin` / image
   - NCHW tensor
   - normalization
3. 实现 C++ 输出保存：
   - raw tensor
   - PNG 可视化
4. 跑固定测试集。
5. 对比：
   - PyTorch output
   - ONNX Runtime Python output
   - ONNX Runtime C++ output
6. 初步测量：
   - preprocess
   - inference
   - postprocess
   - end-to-end

**小实验**：

- CPU EP vs CUDA EP。
- intra-op threads 数量对 CPU 推理影响。
- batch=1 vs batch>1。
- fixed shape vs dynamic shape。

**掌握标准**：

- 能解释 C++ 输入 tensor 的内存布局。
- 能定位 C++ 推理输出不一致的常见原因：layout、normalization、dtype、input name、shape。
- 能区分模型推理时间和端到端时间。

**交付物**：

- `cpp/include/onnxruntime_runner.hpp`
- `cpp/src/onnxruntime_runner.cpp`
- `cpp/src/preprocess.cpp`
- `cpp/src/postprocess.cpp`
- `reports/week2_onnxruntime_cpp.md`

### Week 3：TensorRT FP32 / FP16 部署

**目标**：完成 NVIDIA GPU 上的 TensorRT engine 构建和 C++ 推理，并进行 FP32 / FP16 对比。

**学习内容**：

- TensorRT builder / engine / runtime / execution context。
- ONNX parser。
- optimization profile。
- FP16。
- trtexec。
- CUDA stream。
- H2D / D2H 拷贝。

**具体步骤**：

1. 先用 `trtexec` 构建和 benchmark：
   - FP32
   - FP16
   - fixed shape
   - dynamic shape 可选
2. 写 `build_trt_engine.py` 或 C++ builder。
3. 写 `tensorrt_runner.hpp/cpp`：
   - deserialize engine
   - allocate buffers
   - set input shape
   - enqueue inference
   - copy output
4. 对比 PyTorch / ONNX Runtime / TensorRT 输出。
5. 测量：
   - H2D copy
   - TRT inference
   - D2H copy
   - end-to-end
6. 记录 FP16 画质损失：
   - PSNR / SSIM / LPIPS
   - max abs error
   - 失败案例

**小实验**：

- FP32 engine vs FP16 engine。
- fixed shape engine vs dynamic shape profile。
- CUDA stream 同步位置不同对测时的影响。
- H2D/D2H 拷贝占比。

**掌握标准**：

- 能解释 engine 和 ONNX 模型的区别。
- 能说明 FP16 为什么通常快，但可能带来数值差异。
- 能正确使用 CUDA event 测 GPU inference 时间。
- 能解释为什么端到端时间可能远大于 engine time。

**交付物**：

- `deploy/build_trt_engine.py`
- `cpp/include/tensorrt_runner.hpp`
- `cpp/src/tensorrt_runner.cpp`
- `reports/week3_tensorrt_fp16.md`

### Week 4：INT8 量化、Calibration 与画质损失分析

**目标**：理解 INT8 不是“开个 flag”，而是代表性数据、量化策略和画质评估的组合问题。

**学习内容**：

- PTQ：post-training quantization。
- calibration dataset。
- per-tensor / per-channel。
- symmetric / asymmetric。
- QDQ / QOperator。
- TensorRT INT8 calibrator。
- ONNX Runtime quantization。
- NCNN int8 calibration。

**具体步骤**：

1. 准备 calibration 数据集：
   - 100～500 张代表性 patch 或图像
   - 覆盖低光、正常光、高光、高 ISO、纹理区域
2. 先用 ONNX Runtime quantization 做 CPU / QDQ 实验。
3. 再做 TensorRT INT8 或 NCNN INT8：
   - 构建 calibration cache
   - 构建 INT8 engine / model
4. 对比：
   - FP32
   - FP16
   - INT8
5. 输出量化损失报告：
   - PSNR drop
   - SSIM drop
   - LPIPS change
   - latency change
   - memory change
   - failure cases

**小实验**：

- calibration 数据只用正常光 vs 覆盖低光。
- calibration 数量 20 / 100 / 500 对比。
- 对输入分布极端的图看 INT8 是否 clipping。
- 尝试保留敏感层 FP16 / FP32。

**掌握标准**：

- 能解释为什么 calibration 数据必须覆盖真实场景。
- 能说明 INT8 量化对图像恢复模型比分类模型更敏感。
- 能解释 PSNR 下降 0.1dB、0.5dB、1dB 分别可能意味着什么。
- 能根据失败案例判断量化是否可接受。

**交付物**：

- `deploy/calibrator.py`
- `configs/tensorrt_int8.yaml`
- `scripts/04_quantization_eval.py`
- `reports/week4_int8_quantization.md`

### Week 5：NCNN / MNN 移动端推理路径

**目标**：补齐国内端侧岗位常见移动端部署工具链，至少跑通一个 NCNN 或 MNN 推理链路。

**学习内容**：

- ONNX → NCNN / MNN 转换。
- 模型简化和算子支持。
- Vulkan compute。
- FP16 storage / arithmetic。
- NCNN / MNN benchmark。
- Android / arm64 交叉编译概念。

**具体步骤**：

1. 用 onnxsim 简化 ONNX。
2. 跑 `onnx2ncnn` 或 MNN converter。
3. 用 Netron 检查转换后模型。
4. 写 C++ runner：
   - load param / bin
   - prepare input Mat / Tensor
   - run inference
   - save output
5. 跑桌面端 benchmark。
6. 有 Android 设备则选做：
   - arm64 编译
   - Vulkan 打开/关闭对比

**小实验**：

- Vulkan on / off。
- FP16 storage on / off。
- 输入尺寸不同对延迟影响。
- 和 ONNX Runtime / TensorRT 输出误差对比。

**掌握标准**：

- 能解释 NCNN / MNN 和 TensorRT 的目标平台差异。
- 能说明移动端部署为什么更关注内存、功耗、启动时间和算子支持。
- 能处理常见转换问题：unsupported op、reshape、transpose、LayerNorm、PixelShuffle。
- 能讲清模型为了移动端需要如何改小。

**交付物**：

- `cpp/include/ncnn_runner.hpp` 或 `mnn_runner.hpp`
- `cpp/src/ncnn_runner.cpp` 或 `mnn_runner.cpp`
- `configs/ncnn_mobile.yaml`
- `reports/week5_mobile_inference.md`

### Week 6：CUDA 前后处理、Pipeline 串联与 Profiling

**目标**：把模型推理接入阶段 3 的 C++ ISP 前后处理，形成端到端 pipeline，并用 profiling 找瓶颈。

**学习内容**：

- CUDA stream。
- H2D / D2H 拷贝。
- pinned memory。
- basic CUDA kernels：normalize、pack raw、clamp、layout transform。
- Nsight Systems timeline。
- Nsight Compute kernel profiling。

**具体步骤**：

1. 串联端到端流程：
   - C++ BLC / LSC 或 CUDA preprocess
   - AI model inference
   - C++ / CUDA postprocess
   - save RGB output
2. 写基础 CUDA kernel：
   - RAW 4ch pack / unpack
   - normalize
   - clamp
   - NCHW / NHWC transpose 可选
3. 对比 CPU preprocess 和 CUDA preprocess。
4. 用 Nsight Systems 分析：
   - CPU 前处理
   - H2D
   - inference
   - D2H
   - postprocess
5. 用 Nsight Compute 分析一个简单 kernel：
   - memory throughput
   - occupancy
   - coalescing

**小实验**：

- pageable memory vs pinned memory。
- 同步拷贝 vs async copy + stream。
- CPU preprocess vs GPU preprocess。
- 多张图串行处理 vs pipeline overlap。

**掌握标准**：

- 能解释为什么 GPU 推理快，但端到端未必快。
- 能说明 H2D / D2H 拷贝在图像任务里可能成为瓶颈。
- 能用 Nsight Systems 看懂大致 timeline。
- 能解释 shared memory、coalesced access、occupancy 的基本意义。

**交付物**：

- `cuda_kernels/pack_raw.cu`
- `cuda_kernels/normalize.cu`
- `cpp/src/main.cpp`
- `reports/week6_pipeline_profile.md`

### Week 7：最终系统报告、面试表达和部署交付

**目标**：把阶段四整理成一个能展示的部署项目。

**具体步骤**：

1. 整理 README：
   - 架构图
   - 支持后端
   - 模型转换流程
   - 构建方法
   - 运行命令
   - benchmark 表格
   - 画质对比
2. 写最终报告：
   - 模型选择
   - ONNX 导出
   - 后端对齐
   - FP16 / INT8 对比
   - latency breakdown
   - memory usage
   - failure cases
   - known limitations
3. 准备部署面试讲述：
   - 如何保证 PyTorch / ONNX / TensorRT 输出一致
   - 如何选择 calibration 数据
   - 如何定位端到端瓶颈
   - 如何权衡画质、速度、内存、功耗
4. 固定版本信息：
   - CUDA
   - cuDNN
   - TensorRT
   - ONNX Runtime
   - NCNN / MNN
   - GPU / CPU 型号

**掌握标准**：

- 能讲清一个模型从 PyTorch 训练到 C++ 部署的完整链路。
- 能拿出清楚的表格证明速度提升和画质损失。
- 能解释部署失败或输出不一致时的排查路径。
- 能把阶段 1～4 串成完整 AI-ISP 工程闭环。

**最终交付物**：

- `deploy_isp_stage4/`
- `reports/stage4_report.md`
- `reports/output_alignment_report.md`
- `reports/latency_report.md`
- `reports/quantization_report.md`
- `reports/stage4_interview_notes.md`

---

## 4. 每个能力点的掌握标准

| 能力 | 入门 | 掌握 | 面试可讲 |
|---|---|---|---|
| ONNX 导出 | 能 export 成功 | 能 checker、simplify、Netron 检查、ORT 对齐 | 能解释 unsupported op、dynamic shape、opset 问题 |
| ONNX Runtime | 能 Python 推理 | 能 C++ 推理并对齐输出 | 能作为跨后端 correctness baseline |
| TensorRT | 能 trtexec 跑 engine | 能 C++ runtime、FP16、dynamic profile | 能解释 engine、profile、stream、H2D/D2H 测时 |
| INT8 量化 | 能打开 INT8 | 能 calibration、评估画质损失 | 能解释 calibration 数据和图像恢复量化敏感性 |
| NCNN / MNN | 能完成模型转换 | 能 C++ 推理、Vulkan/FP16 对比 | 能解释移动端部署约束和算子支持问题 |
| CUDA 前后处理 | 能写简单 kernel | 能优化 pack/normalize/layout transform | 能解释 coalescing、shared memory、copy bottleneck |
| Profiling | 能测 latency | 能拆 preprocess/infer/postprocess/copy | 能用 Nsight / benchmark 定位端到端瓶颈 |
| 输出对齐 | 能肉眼对比 | 能 max/mean error、PSNR、error map | 能定位 layout、dtype、normalization、backend precision 差异 |

---

## 5. 阶段四面试问题清单

1. PyTorch 模型导出 ONNX 时最常见的问题有哪些？
2. ONNX opset 是什么？为什么不同 opset 会影响部署？
3. dynamic shape 和 fixed shape 部署各有什么利弊？
4. 为什么 ONNX 导出成功不代表模型正确？
5. 如何验证 PyTorch 和 ONNX Runtime 输出一致？
6. TensorRT engine 和 ONNX 模型有什么区别？
7. TensorRT optimization profile 是什么？
8. FP16 为什么能加速？它可能带来什么画质问题？
9. INT8 calibration 为什么需要代表性数据集？
10. 图像恢复模型为什么比分类模型更怕 INT8 量化？
11. QDQ 格式和普通量化有什么区别？
12. 如何判断 INT8 后画质损失是否可接受？
13. H2D / D2H 拷贝为什么会影响端到端延迟？
14. 模型 inference time 和 end-to-end latency 有什么区别？
15. 如何用 CUDA event 正确测 GPU 推理时间？
16. Nsight Systems 和 Nsight Compute 分别看什么？
17. NCNN / MNN 和 TensorRT 适用平台有什么不同？
18. 移动端部署为什么关注内存和功耗？
19. Vulkan compute 在 NCNN 中起什么作用？
20. 如果 NCNN 转换失败，你会怎么排查？
21. 如果部署输出偏色，可能有哪些原因？
22. 如果部署后 PSNR 下降但主观看不明显，如何判断是否接受？
23. 如果 TensorRT 比 ONNX Runtime 快但端到端没变快，可能为什么？
24. 如何选择 calibration 数据？
25. 你的 AI-ISP 部署系统如何和传统 ISP 前后处理衔接？

---

## 6. 阶段四结束后的自检

如果下面问题能回答清楚，阶段四就算真正完成：

- 我能不能固定一个模型并从 PyTorch 导出 ONNX？
- 我能不能证明 ONNX Runtime 和 PyTorch 输出一致？
- 我能不能写 C++ 推理程序，而不是只在 Python 里跑？
- 我能不能至少跑通 TensorRT / NCNN / MNN / OpenVINO 其中一个部署后端？
- 我能不能拆分端到端 latency，而不是只报模型时间？
- 我能不能解释 FP16 和 INT8 带来的画质变化？
- 我能不能用固定测试集比较不同后端的输出误差？
- 我能不能把阶段 3 的 C++ 前后处理接到模型推理前后？
- 我能不能用报告说明“速度提升是否值得画质损失”？

---

## 7. 阶段四不要做什么

- 不要一开始就做大模型部署；先用轻量模型跑通全链路。
- 不要只跑 `trtexec`，不写 C++ 推理。
- 不要只测 engine time，不测 preprocess、copy、postprocess。
- 不要没有 PyTorch golden 输出就做后端对比。
- 不要 INT8 只看速度，不看画质损失和失败案例。
- 不要忽略 input layout / dtype / range，这些是部署偏色和输出异常的高发原因。
- 不要把 CUDA kernel 优化放在模型部署之前；先定位瓶颈，再决定是否手写 kernel。

---

## 8. 推荐执行顺序摘要

```text
Week 0.5  固定模型和测试基准
  -> PyTorch baseline、固定测试集、输入输出协议

Week 1    ONNX 导出和 Python 对齐
  -> checker、Netron、onnxsim、ORT Python 输出对齐

Week 2    ONNX Runtime C++ baseline
  -> C++ 推理、pre/postprocess、端到端初测

Week 3    TensorRT FP32 / FP16
  -> trtexec、engine、C++ runtime、输出误差和延迟报告

Week 4    INT8 量化
  -> calibration、FP32/FP16/INT8 画质和速度对比

Week 5    NCNN / MNN 移动端路径
  -> ONNX 转换、C++ 推理、Vulkan/FP16 对比

Week 6    CUDA 前后处理和 profiling
  -> pack/normalize kernel、pipeline 串联、Nsight timeline

Week 7    最终交付
  -> README、系统报告、benchmark、量化报告、面试表达
```

---

## 9. 阶段四与完整求职项目的衔接

阶段四结束后，你应该能把四个阶段串成一个完整故事：

1. **阶段一**：我理解传统 ISP，从 RAW 到 RGB 有完整 Soft-ISP。
2. **阶段二**：我训练了 AI 图像恢复模型，理解数据、loss、metric 和失败案例。
3. **阶段三**：我能把 ISP 模块工程化到 C++，并做对齐、定点化、四通道和性能优化。
4. **阶段四**：我能把 AI 模型部署到 C++ / GPU / 移动端推理链路，并量化评估速度和画质损失。

面试时不要把阶段四讲成“我会 TensorRT”。更有价值的表达是：

> 我能以固定测试集为基准，保证 PyTorch、ONNX Runtime、TensorRT / NCNN 输出一致；能拆解端到端延迟；能评估 FP16 / INT8 对画质的影响；能把模型接入传统 C++ ISP 前后处理，形成可验证的 AI-ISP 推理系统。
