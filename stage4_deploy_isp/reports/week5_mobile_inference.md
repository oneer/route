# 第 5 周：NCNN / MNN 移动端推理路径

## 目标

Week 5 用来补齐端侧部署视角。由于你的优先岗位是 AI-ISP / ISP 算法工程师，而不是纯手机端侧部署岗，本周定位为加分项：理解移动端约束，并为后续真实设备验证留下清晰路径。

## 当前工具链探测

当前 PATH 中未找到：

- `onnx2ncnn`
- `ncnnoptimize`
- `MNNConvert`
- `benchmark`
- `adb`

因此本机当前不能完成 NCNN / MNN 转换和 Android 设备实测。

## 当前模型适配性

阶段四主模型 `dncnn_sidd_tiny_fp32.onnx` 的 graph 很简单：

```text
Conv x5
Relu x4
Sub x1
```

这类模型通常适合 NCNN / MNN 转换，因为没有 LayerNorm、GridSample、复杂 attention 或动态 control flow。它比 NAFNet-lite 更适合作为第一条移动端部署闭环。

## 后续转换命令模板

NCNN 路径：

```powershell
onnx2ncnn stage4_deploy_isp/models/onnx/dncnn_sidd_tiny_fp32.onnx ^
  stage4_deploy_isp/models/ncnn/dncnn_sidd_tiny.param ^
  stage4_deploy_isp/models/ncnn/dncnn_sidd_tiny.bin

ncnnoptimize stage4_deploy_isp/models/ncnn/dncnn_sidd_tiny.param ^
  stage4_deploy_isp/models/ncnn/dncnn_sidd_tiny.bin ^
  stage4_deploy_isp/models/ncnn/dncnn_sidd_tiny_opt.param ^
  stage4_deploy_isp/models/ncnn/dncnn_sidd_tiny_opt.bin 65536
```

MNN 路径：

```powershell
MNNConvert -f ONNX ^
  --modelFile stage4_deploy_isp/models/onnx/dncnn_sidd_tiny_fp32.onnx ^
  --MNNModel stage4_deploy_isp/models/mnn/dncnn_sidd_tiny.mnn ^
  --bizCode stage4
```

## AI-ISP / ISP 算法岗应关注什么

端侧后端不是单纯换格式。真正要关注：

- 移动端是否改变输出颜色或动态范围。
- Vulkan / FP16 是否让暗区噪声或纹理更差。
- 内存占用是否允许在 ISP pipeline 中实时处理。
- 输入输出是否仍保持 `RGB / NCHW or NHWC / [0, 1]` 的明确协议。
- 模型是否需要改小，而不是只追求 PC 端指标。

## 当前缺口

如果后续要把阶段四强化成手机厂商端侧岗位项目，需要补：

1. 安装 NCNN 或 MNN 工具链。
2. 准备 Android / arm64 设备和 `adb`。
3. 跑 CPU / Vulkan / FP16 对比。
4. 报告设备型号、SoC、内存、系统版本和温度状态。
5. 与 ORT / PyTorch golden output 做误差对齐。
