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
