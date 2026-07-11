# 真实 RAW 到部署端 Capstone 验收规范

## 1. 唯一目标

用一条可复现命令，把固定 manifest 中的真实 sensor RAW 输入处理为 RGB 输出，并保存每个阶段的 correctness、quality、latency 和失败样本证据。

## 2. 强制数据合同

每张 RAW 必须记录：来源、许可证、相机/传感器、bit depth、black level、white level、Bayer pattern、orientation、尺寸、曝光、ISO，以及可用的白平衡和色彩矩阵元数据。缺失字段必须显式标为 unknown，不能静默猜测。

## 3. 最小链路

```text
sensor RAW
  -> unpack/normalize/BLC
  -> 可选 DPC/LSC
  -> 学习型 RAW restoration 或明确的传统 baseline
  -> demosaic/AWB/CCM/tone
  -> C++/ONNX Runtime inference
  -> RGB output
```

Stage 3 与 Stage 4 必须处理同一 manifest 和同一 tensor contract；独立跑通两个 demo 不算串联完成。

## 4. 必须产物

1. 单一入口命令和无交互配置。
2. 输入 manifest、数据集卡和 split 泄漏检查。
3. 每阶段 tensor shape/dtype/range/color/layout。
4. CPU reference、部署输出和 max/mean/RMSE 对齐。
5. PSNR/SSIM 及至少一种颜色或感知指标。
6. preprocess/inference/postprocess/I/O 的独立 latency。
7. 代表图、error map、最差样本和失败原因。
8. 模型、配置、代码版本与资产 hash。

## 5. 完成判定

只有在干净环境按文档单命令复现，并且自动化检查通过后，整改报告中的真实 RAW、Stage 3/4 串联和 CUDA 接入项目才能勾选。
