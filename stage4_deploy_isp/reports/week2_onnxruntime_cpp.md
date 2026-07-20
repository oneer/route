# Week 2：ONNX Runtime C++ 推理

## 1. 为什么需要

C++ runner 验证 Python 之外的 tensor ownership、内存布局、图像 I/O 和 runtime API，给后续原生后端提供 baseline。

## 2. 输入输出协议

PPM P6 RGB uint8 输入；C++ 转为连续 NCHW float32 `[0,1]`。输出先 dump `.f32` raw tensor，再 clamp/round 保存 PPM。

## 3. 链路角色

Python 生成同一输入的 ORT raw reference；C++ runner 读取 PPM、创建 `Ort::Value`、执行 Session、输出 float tensor和可视化图。

## 4. 核心概念/API

`Ort::Session`、SessionOptions、CPU allocator、caller-owned input buffer、runtime-owned output、input/output name、NCHW index。runner 使用 intra-op 1 和 ORT_ENABLE_ALL。

## 5. 对应文件

- `cpp/src/main.cpp`
- `cpp/src/onnxruntime_runner.cpp`
- `cpp/src/image_io.cpp`
- `scripts/04_week2_prepare_cpp_io.py`
- `scripts/08_week2_compare_cpp_output.py`

## 6. 运行命令与环境

```powershell
cmake -S stage4_deploy_isp -B stage4_deploy_isp/build_audit_release -G Ninja `
  -DCMAKE_BUILD_TYPE=Release `
  -DONNXRUNTIME_ROOT=D:/Env/onnxruntime/cpu/onnxruntime-win-x64-1.26.0
cmake --build stage4_deploy_isp/build_audit_release
```

runner：

```powershell
stage4_ort_runner.exe model.onnx input.ppm output.ppm output.f32 3 5
```

## 7. 正确输出

20 个 PPM、20 个 `.f32` 和 `week2_cpp_tensor_alignment.csv`。

## 8. 对齐指标与阈值

raw float tensor 报告 max/mean/RMSE/PSNR；20/20 样本 max `0`，项目阈值 `1e-5`。PNG/PPM 结果不作为 tensor correctness 证据。

## 9. 常见失败与排查

先比 Python preprocess tensor，再比 C++ input；之后比 ORT Python output 与 C++ `.f32`；最后才检查 PPM。Windows 还需确认加载的是目标 ORT DLL。

## 10. 性能测量

每次进程内 warmup 3、runs 5，只计 `Session::Run`；逐图启动新进程约 `143–151 ms`。session creation、读图、写图未计入该数字，不能与 ORT Python session mean直接归因比较。

## 11. Tradeoff

PPM 减少图像库依赖，但不是生产格式；raw `.f32` 文件较大，却能避免 uint8 量化掩盖误差。

## 12. 证据边界

当前仅 CPU EP；未完成 C++ CUDA/TensorRT EP、线程 sweep、batch>1 和完整 C++ E2E benchmark。

## 13. 练习与掌握标准

故意交换 layout 或跳过 `/255`，按“input tensor → output tensor → image”顺序定位；能解释 allocator 和 tensor lifetime 即达标。

## 14. C++ Runner 从输入到输出的完整路径

```text
读取 PPM P6 RGB
  -> 校验 width/height/channel
  -> caller-owned vector<float> 按 NCHW 写入并 /255
  -> Ort::MemoryInfo 描述 CPU 内存
  -> Ort::Value 包装现有输入 buffer
  -> Session::Run
  -> runtime-owned output tensor
  -> 先保存原始 .f32
  -> clamp/round/NCHW→HWC 保存 PPM
  -> Python 对齐脚本比较 input 和 output tensor
```

调试顺序必须从 tensor 开始。若直接看 PPM，图片解码、通道转换、clamp 和量化会把多个问题叠加在一起。

## 15. 关键词与参数表

| 参数/关键词 | 当前设置 | 原因与权衡 | 风险 |
|---|---|---|---|
| intra-op threads | 1 | 降低线程调度差异，建立可比 baseline | 不是 CPU 最快配置，后续需 sweep |
| graph optimization | `ORT_ENABLE_ALL` | 允许 ORT 做完整图优化 | 要记录 ORT 版本并重新对齐 |
| caller-owned input | `Ort::Value` 引用现有 float buffer | 避免一次额外输入复制 | buffer 必须连续且生命周期覆盖 `Run` |
| runtime-owned output | 输出内存由 ORT 管理 | API 简单 | 指针只在 output value 生命周期内有效 |
| warmup/runs | 3/5 | 区分冷启动与 steady-state | 样本较少，不应过度解释尾延迟 |
| `.f32` tensor dump | 原始连续 float 输出 | 保留严格 correctness 证据 | 文件大且不自描述，必须配 shape/manifest |

## 16. Week 2 面试五问

1. `Ort::Value` 包装 caller-owned buffer 时最重要的生命周期条件是什么？
2. 为什么 C++ 与 Python 20/20 bit-exact 仍不能证明图片 I/O 正确？
3. intra-op 线程为什么固定为 1，何时应做 thread sweep？
4. 逐图新进程的 143–151 ms 为什么不能直接与 Python session mean 比较？
5. Windows 下如何证明加载了目标 ORT DLL，而不是 PATH 中另一个同名版本？

## 17. 内存布局、索引公式与生命周期

对 shape 为 `N×C×H×W` 的连续 NCHW tensor，元素地址为：

```text
index_nchw(n,c,y,x) = ((n*C + c)*H + y)*W + x
index_hwc(y,x,c)    = (y*W + x)*C + c
```

“维度数值一样”不代表内存语义一样。把 HWC 的连续字节直接交给要求 NCHW 的模型，buffer 大小和 dtype 都可能合法，但像素与通道会被系统性错读。因此 C++ runner 应在写入后用一个 `2×2×3` 手工样例检查索引，而不是只检查总元素数。

本实现中，`vector<float>` 拥有输入内存，`Ort::Value` 只是包装这块内存；所以 vector 不能在 `Session::Run` 前析构、扩容或移动。输出 buffer 由 ORT 的 output value 拥有，取出的指针不能在该 value 析构后继续使用。`Ort::Env`、`SessionOptions`、`Session`、input buffer、input value、output value 的存活区间应在代码评审时明确标注。

## 18. 延迟边界与可比较性

```text
T_process = T_process_start + T_model_load + T_decode + T_pre + T_run + T_post + T_write
T_session = 仅已创建 Session 上的 Session::Run 区间
```

逐图启动新进程得到的 `143–151 ms` 包含进程、DLL 和模型/session 初始化，不能与复用 session 的 Python mean 直接比较。公平 thread sweep 应冻结输入、模型、build 类型、ORT 版本和计时边界，对每个 thread 数独立 warmup，再报告 p50/p90，而不是只保留最快一次。

Windows 排查 DLL 时要同时记录：可执行文件链接目标、运行时实际加载模块的绝对路径、ORT 版本字符串和 `PATH`。仅仅“程序能启动”无法证明用了预期 DLL。

## 19. 代码追踪与故障定位实验

```text
main.cpp
  -> parse args / read PPM header and RGB bytes
  -> HWC u8 -> NCHW f32 /255
  -> create Env + SessionOptions + Session
  -> query input/output metadata
  -> wrap input buffer as Ort::Value
  -> Session::Run
  -> dump raw NCHW f32
  -> clamp/round -> PPM
Python alignment
  -> 比较 C++ input、Python input、C++ output、Python output
```

建议依次注入：交换 R/B、删掉 `/255`、把 HWC index 当 NCHW、在 output value 销毁后访问指针、把 PATH 中 DLL 顺序改变。前三项验证 tensor contract，第四项验证 ownership，第五项验证运行环境。每次只改一处，并在“第一处不同的 float buffer”停止排查。

## 20. 面试五问参考回答

1. caller-owned buffer 必须连续、地址稳定，且生命周期覆盖 tensor 使用和 `Session::Run`；包装它的 `Ort::Value` 不接管 vector 所有权。
2. bit-exact 只证明已比较的 float 输入/输出路径一致；PPM 解码、输出 clamp、round、通道还原仍可能独立出错。
3. 固定 1 线程用于建立低调度干扰的 correctness baseline；性能阶段再按相同数据、warmup 和计时边界 sweep，并报告尾延迟。
4. 新进程数字混入加载和初始化，而 Python session mean 通常复用进程/session；边界不同，不能归因给语言或 backend。
5. 检查进程实际加载模块的绝对路径并记录 ORT 版本、build/link 配置与 PATH；仅检查目录里“有一个 DLL”不够。

## 21. 本周学习验收清单

- [ ] 能手算 HWC 与 NCHW 索引，并用小图验证转换。
- [ ] 能画出 Env、Session、input vector、Ort::Value 和 output value 的 ownership/lifetime。
- [ ] 能从 raw input tensor 开始定位一次 layout 或 range 错误。
- [ ] 能区分 process、session、compute 与 e2e 延迟边界。
- [ ] 能证明实际加载的 ORT DLL 路径和版本。
- [ ] 能复现 20/20 float 对齐，并说明它没有覆盖哪些图片 I/O 风险。
- [ ] 能准确陈述边界：当前仅 C++ ORT CPU fixed-shape runner，未验证 CUDA/TRT EP 和完整生产 I/O。
