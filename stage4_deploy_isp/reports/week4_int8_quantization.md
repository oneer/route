# Week 4：INT8 PTQ/QDQ 与校准

## 1. 为什么需要

图像恢复要求逐像素颜色与纹理正确；INT8 不能只看 max error 或模型能否运行。

## 2. 输入输出协议

FP32 与 INT8 使用相同 RGB/NCHW/[0,1] 协议。前 10 张仅用于 calibration，后 10 张仅用于 evaluation；两份 manifest 无交集。

## 3. 链路角色

ORT `quantize_static` 生成 CPU QDQ 模型；本实验不是 TensorRT INT8，也不是动态量化。

## 4. 核心概念/API

PTQ、QDQ、scale/zero-point、activation QUInt8、weight QInt8、per-channel weight、MinMax calibration。当前 activation asymmetric、weight signed；不同后端融合和 kernel 可能得到不同结果。

## 5. 对应文件

- `scripts/06_week4_quantization_eval.py`
- `data/calibration/week4_calibration_manifest.csv`
- `data/test_inputs/week4_evaluation_manifest.csv`
- `models/onnx/dncnn_sidd_tiny_int8_qdq.onnx`
- `outputs/week4_quantization/error_maps/`
- `outputs/week4_quantization/failure_cases/`

## 6. 运行命令与环境

```powershell
python stage4_deploy_isp/scripts/06_week4_quantization_eval.py
```

ORT CPU；每图 warmup 3、runs 10。

## 7. 正确输出

独立 split manifest、QDQ model、10 张 INT8 output、逐样张 CSV、最差 3 张 error map/comparison。

## 8. 对齐指标与阈值

| 指标 | 结果 |
|---|---:|
| split overlap | `0` |
| FP32 / INT8 平均 PSNR | `32.98396 / 32.90063 dB` |
| 平均 / 最差 PSNR drop | `0.08333 / 0.24030 dB` |
| 最差样本 | `pair_00016` |
| 平均 SSIM drop | `4.93e-5` |
| max abs error | `0.04343` |

项目标准：平均 drop `<0.1 dB` 为初步可接受；最差 drop `>0.5 dB` 必须拒绝或专项分析。当前通过项目门槛，但仍仅代表该小评价集。

## 9. 常见失败与排查

先查 split overlap，再查 calibration 场景覆盖、range、QDQ/QOperator、per-channel、敏感层和 backend kernel；最后结合暗区、高光、饱和色和纹理 crop。

## 10. 性能测量

FP32 p50/p90 `149.93/254.46 ms`；INT8 `121.25/218.19 ms`。同一 ORT CPU、同一独立评价集和口径。模型文件由 `132,767` bytes（ONNX+external data）降至 `46,462` bytes。

## 11. Tradeoff

本次 INT8 有文件大小和 CPU latency 收益，平均画质损失较小；但 10 张 calibration 无法充分覆盖真实暗部、高光、纹理和噪声分布。

## 12. 证据边界

不是 TensorRT/NPU INT8；没有 100–500 张代表性 calibration、功耗、峰值内存或真实设备结果。当前结论为“小样本 ORT CPU QDQ 初步可接受”。

## 13. 练习与掌握标准

只用亮图校准并在暗图评价；比较 5/10 张 calibration；能区分 QDQ、TensorRT INT8 和动态量化即达标。
