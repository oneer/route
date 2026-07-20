# Week 12：ONNX / C++ 部署验证

状态：ONNX Runtime Python/C++ 核心推理已实测完成；OpenCV DNN 图片 I/O 样例因本机
未安装 OpenCV C++ SDK，保留为可选验证。

本周解决的问题是：冻结后的 PyTorch 模型能否在 ONNX Runtime Python/C++ 中接收相同
张量并产生数值一致的输出。它验证部署接口，不评价模型是否适合量产端侧。

Week 11 已证明 Python 侧 ONNX 图与 PyTorch 对齐；本周把同一个 ONNX 和 raw float tensor
交给 C++ ORT，隔离 C++ buffer、shape、SDK 和计时问题。输出交给阶段四继续做 GPU、量化、
端侧和完整 pipeline 验证。

## 背景：为什么 C++ 还必须再验一次

Python 与 C++ 可以调用同一 ORT 内核，但外围错误仍可能不同：元素个数算错会越界，临时
buffer 生命周期结束会产生悬空指针，HWC 内存被标成 NCHW 会得到“shape 正确、语义错误”
的输出，SDK/DLL 版本不匹配则可能在加载阶段失败。因此 C++ smoke 的首要目标是合同正确，
不是追求最快数字。

## 输入输出协议

```text
layout: NCHW
input : float32, RGB, [0,1], [1,3,H,W]
output: float32, RGB, [0,1], [1,3,H,W]
mode  : model.eval() + no_grad/inference mode
```

图片解码、HWC→CHW、uint8→float32、RGB 顺序和输出 clamp 必须在所有 backend 中一致。
ONNX 的 opset、静态/动态 shape 以实际导出命令和模型检查结果为准，不从文件名猜测。

## 环境

- CPU：本机 x64 CPU（CPU inference）
- OS：Windows 10 10.0.19045
- PyTorch：2.12.0+cpu
- ONNX Runtime Python：1.27.0
- ONNX Runtime C++ SDK：1.26.0
- 编译器：MSVC 19.51.36248 x64
- 输入图像 I/O：Python Pillow；C++ latency 只统计 ORT `Session::Run`

## 固定输入

- 图片：`datasets/sidd_tiny/test/noisy/pair_00001.png`
- shape：`1×3×512×512`
- checkpoint：`paired_rgb_sidd_tiny_dncnn_l2_2000/checkpoints/best_psnr.pth`
- ONNX：`deployment/onnx/dncnn_sidd_tiny.onnx`，119,763 bytes

## 代码导航与执行层次

```text
deployment/outputs 中的固定 float input/reference
  -> deployment/cpp 的 CMake 配置
  -> Ort::Env / Ort::SessionOptions / Ort::Session
  -> 创建 shape=[1,3,H,W] 的连续 float tensor
  -> Session::Run
  -> 保存 raw float output
  -> Python/脚本计算 max、mean、PSNR 与 preview
```

先运行纯 tensor runner，再接图片 I/O。这样颜色错误时可以判断问题发生在解码/预处理，
还是 ORT 核心。具体构建命令、SDK 路径和产物位置以 `deployment/README.md` 为唯一操作手册；
本报告解释为何这样做以及如何验收。

## 输出对齐

| Backend | Max abs error vs PyTorch | Mean abs error | PSNR vs PyTorch | SSIM vs PyTorch |
|---|---:|---:|---:|---:|
| ONNX Runtime Python CPU | 2.38419e-7 | 2.98436e-8 | 80.0 | 1.0 |
| ONNX Runtime C++ CPU | 2.38419e-7 | 2.98436e-8 | 80.0 | 1.0 |
| OpenCV DNN C++ | 可选，未安装 OpenCV C++ SDK | - | - | - |

对齐顺序应固定为：

```text
同一输入 tensor
  -> PyTorch reference
  -> ONNX Runtime Python
  -> 保存原始 float tensor
  -> ONNX Runtime C++
  -> max/mean absolute error + PSNR
```

PNG 只适合肉眼检查，8-bit 量化会掩盖或引入误差；严格对齐使用 float tensor。

## Latency

所有结果必须包含 warm-up 次数和重复次数。

| Backend | Warm-up | Repeats | Mean ms | P50 ms | P95 ms |
|---|---:|---:|---:|---:|---:|
| ONNX Runtime Python CPU | 5 | 30 | 72.1614 | 71.7367 | 82.2435 |
| ONNX Runtime C++ CPU | 5 | 30 | 70.3157 | 70.4122 | 80.1261 |
| OpenCV DNN C++ | - | - | 可选 | 可选 | 可选 |

## 验收

- [x] ONNX 文件通过 checker。
- [x] PyTorch 和 ONNX 输出图片已保存。
- [x] `alignment.json` 已生成。
- [x] C++ float 输出和 PNG preview 已生成。
- [x] C++ latency 使用 5 次 warm-up、30 次重复。
- [x] 误差为 CPU backend 浮点算子顺序造成的约 `1e-7` 级差异。
- [x] 工程 summary 已加入 test 指标和 latency。

当前可以写“完成 ONNX Runtime Python/C++ CPU 推理 smoke test 与输出对齐”。不能写成
端侧量产部署、TensorRT 优化或 OpenCV DNN 已验证。

## 练习与掌握标准

1. 故意交换 RGB/BGR，观察 max error 和输出颜色；
2. 故意漏掉 `/255`，解释 range 错误为何不是模型精度问题；
3. 比较固定 `128x128` 与 `512x512` 输入，记录 shape 支持和 latency 口径；
4. 明确 warm-up、repeats、线程、设备和 I/O 是否计时；
5. 能解释“数值对齐通过”不等于“质量、速度、内存和端侧兼容性全部通过”。

## C++/ORT 关键词与参数表

| 关键词/参数 | 定义 | 当前测量口径 | 排错重点 |
|---|---|---|---|
| `Ort::Session` | 加载模型并执行图的 C++ 会话 | CPU Execution Provider | SDK/DLL/模型版本和 provider |
| tensor buffer | 连续 NCHW float 输入输出内存 | `1×3×512×512`、RGB、`[0,1]` | 生命周期、shape、元素数和通道顺序 |
| `Session::Run` | 一次核心图推理调用 | 当前 latency 只统计此调用 | 不包含图片解码、保存和完整 e2e |
| warm-up 5 | 不进入统计的预热次数 | 完成首次初始化和缓存准备 | warm-up 太少会污染首轮结果 |
| repeats 30 | 正式计时样本数 | 报 mean/p50/p95 | 只报 mean 会掩盖尾延迟 |
| p50/p95 | 延迟分布的中位数/95 分位 | 反映典型和尾部表现 | 必须声明样本数、线程、设备和后台负载 |

## Week 12 面试五问

1. Python ORT 与 C++ ORT 对齐通过后，还需要检查哪些图片 I/O 和内存合同？
2. 为什么 `Session::Run` latency 不能称为端到端 Camera latency？
3. warm-up、repeats、mean、p50 和 p95 分别解决什么测量问题？
4. C++ 输出颜色错误但 float shape 正确时，优先检查什么？
5. CPU smoke test 到 TensorRT/INT8/移动端量产之间还缺哪些正确性、性能和稳定性证据？

## C++ 部署流程与边界

```text
同一 ONNX/float input
  -> Python ORT reference
  -> C++ Ort::Session
  -> raw float output
  -> max/mean/PSNR 对齐
  -> warm-up/repeats latency
  -> PNG 仅作观察
```

本周验证的是 x64 CPU ORT 核心推理与 tensor 对齐。图片 I/O 完整性、GPU/TensorRT、量化、峰值内存、ARM/Android、功耗和生产稳定性不在本周证据内。

## 内存、延迟与参数方向

连续 NCHW tensor 的元素数为 `N*C*H*W`，FP32 字节数再乘4。512×512 单张 RGB input
约为 `1*3*512*512*4=3,145,728` bytes；这只是输入 buffer，不含 output、中间 activation、
权重和 ORT workspace。峰值内存不能由 checkpoint 大小推出。

| 变量 | 增大/改变时通常发生什么 | 必须固定或记录 |
|---|---|---|
| H/W | 像素数近似按面积增长，卷积 latency/activation 随之增大 | shape、padding/tiling |
| intra-op threads | 可能加速，也可能因调度/争用变慢 | 线程数、CPU、后台负载 |
| warm-up | 更多可减弱初始化影响，但增加测量时间 | 是否排除、次数 |
| repeats | 分位数更稳定，测试更久 | 样本数与原始分布 |
| I/O scope | 加入 decode/copy/save 后更接近 e2e，数字也更大 | 精确计时边界 |

测量精度、测试时长和服务延迟之间需要权衡。mean 适合总体成本，p50 表示典型请求，p95 暴露尾延迟。30次只是一组 smoke 统计，不能
代表长稳、热限制或实时 Camera 帧调度。C++略快于Python ORT也不能归因于语言，因为两者
可能共享核心 backend，差异还受线程、计时边界和系统噪声影响。

## Failure/Debug 与学习验收

| 现象 | 首查 | 最小验证 |
|---|---|---|
| session 加载失败 | ONNX path、DLL、架构、SDK版本 | 打印 ORT error 与实际依赖版本 |
| shape 正确但误差大 | range/layout/RGB、输入是否同一份 | 逐元素比较输入 tensor |
| 偶发崩溃/NaN | buffer 生命周期、元素数、连续性 | 固定小 tensor + sanitizer/debug build |
| 颜色错但 raw 对齐 | 图片 I/O、BGR/RGB、clamp | 绕过解码直接读 reference tensor |
| latency 抖动 | warm-up、线程、后台任务 | 保存每次样本而非只报 mean |

独立验收：手算 buffer 字节数；故意交换 layout/range 并定位；分别报告 core 与 e2e 计时；
用两个尺寸检查动态 shape；解释 output 对齐、质量通过、性能通过和产品通过为何是四个门。

证据等级为 `verified_partial`：x64 CPU C++ ORT 核心推理和 tensor 对齐已实测；OpenCV
DNN、GPU、INT8、ARM/Snapdragon、功耗与量产稳定性均为 `not_run`。
