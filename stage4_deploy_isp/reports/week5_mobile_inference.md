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
