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

## 14. PTQ 从校准到评价的完整流程

```text
冻结 FP32 ONNX
  -> 单独 calibration manifest（10 张）
  -> 收集 activation min/max
  -> 计算 scale/zero-point
  -> 插入 QuantizeLinear/DequantizeLinear（QDQ）
  -> 独立 evaluation manifest（10 张）
  -> FP32 与 INT8 同输入推理
  -> quality/latency/model-size/最差 crop 联合验收
```

校准不是训练：它不更新模型权重，只估计把浮点范围映射到有限整数码值所需的量化参数。校准集和评价集必须分开，否则量化范围可能对评价样本过度适配。

## 15. 关键词与参数表

| 关键词/参数 | 定义 | 当前选择/影响 | 验证 |
|---|---|---|---|
| scale | 一个整数步长代表的浮点间隔 | 太大精度粗，太小易饱和 | range coverage 与 error histogram |
| zero-point | 浮点 0 对应的整数码 | asymmetric activation 可更好覆盖偏置范围 | 检查 0 是否可表达和边界 clamp |
| per-channel weight | 每个输出通道独立 scale | 通常减少不同通道范围差异带来的误差 | 与 per-tensor 消融 |
| MinMax calibration | 用观测最小/最大确定范围 | 简单但对 outlier 敏感 | 增加样本/场景并检查最差 ROI |
| QDQ | 图中显式插入量化/反量化节点 | 保留浮点图结构并交给 backend 融合 | 不等同于硬件必然执行全 INT8 |
| average/worst drop | 平均/最差样本质量下降 | 平均可接受仍可能有局部灾难 | 同时设 warning/reject 条件 |

## 16. Week 4 面试五问

1. PTQ 与 QAT 有何区别？前者不重训，后者训练时模拟量化并可适应误差。
2. calibration 为什么不能和 evaluation 用同一集合？避免范围选择对最终样本泄漏。
3. per-channel weight 为什么通常比 per-tensor 精细？各输出通道动态范围可能差异很大。
4. max abs error 大但 PSNR drop 小怎样解释？可能是少数局部 outlier，必须看位置和最差 crop。
5. 本次通过 0.1 dB 平均门槛能否宣称移动 NPU 可用？不能；backend、校准覆盖、算子融合、内存和功耗都未验证。

## 17. 量化公式与参数含义

线性量化把浮点值 `x` 映射到有限整数码值 `q`：

```text
q     = clip(round(x / scale) + zero_point, q_min, q_max)
x_hat = scale * (q - zero_point)
```

`scale` 越大，覆盖范围越宽但步长更粗；越小，分辨率更细但更容易在边界饱和。symmetric 量化通常令 zero-point 接近 0、正负范围对称；asymmetric 允许非零 zero-point，更适合偏置明显的 activation。per-tensor 共用一套参数，per-channel 为不同权重输出通道分别选 scale，通常能减少通道动态范围差异造成的误差，但 backend 支持和实现成本更高。

量化误差来自两类：rounding 把连续值落到离散格点，clipping 把超出校准范围的值压到端点。仅看平均误差可能掩盖暗部或高光中的饱和，因此要保存 error histogram、饱和比例、最差样本和 ROI。

## 18. 校准数据为什么决定结果

calibration 估计部署输入分布中的 activation 范围，evaluation 则检验这些范围能否泛化。两者重叠会使范围选择“看见考题”，同时也无法暴露场景覆盖不足。本项目 10/10 的划分适合演示闭环，却不足以覆盖量产 ISP 的照度、色温、ISO、纹理、运动和 sensor 差异。

建议按元数据或可观测特征建立 coverage 表：暗部/正常/高光、低/高噪声、平坦/高频纹理、颜色极端。增加 calibration 数量时应比较范围、饱和率、平均/最差质量，而不是默认“越多越好”；大量重复场景仍可能缺失关键尾部。

## 19. 代码追踪、消融与失败定位

```text
04_quantize_int8.py
  -> 冻结 FP32 ONNX 与 calibration manifest
  -> CalibrationDataReader 复用 RGB/NCHW/[0,1] 预处理
  -> collect range -> 生成 QDQ ONNX
05_evaluate_int8.py
  -> 独立 evaluation manifest
  -> FP32/QDQ 同输入运行
  -> tensor error + PSNR/SSIM + latency + size + worst crop
```

至少完成三组控制变量实验：5 vs 10 张 calibration、只用亮图 vs 覆盖暗图、per-tensor vs per-channel weight（backend 支持时）。若质量退化，按顺序检查预处理一致性、校准/评价集合、饱和比例、误差最大的层/样本、QDQ 是否被目标 backend 融合。QDQ 文件变小或 ORT CPU 变快，不等于移动 NPU 已运行整数 kernel。

## 20. 本周学习验收清单

- [ ] 能用公式手算一次 quantize/dequantize，并指出 rounding 与 clipping 误差。
- [ ] 能比较 symmetric/asymmetric、per-tensor/per-channel、PTQ/QAT。
- [ ] 能解释 calibration 与 evaluation 必须独立，以及如何检查场景覆盖。
- [ ] 能运行至少一组 calibration 消融并同时比较平均和最差结果。
- [ ] 能从 QDQ graph、backend 日志和 profiling 区分“图中有量化节点”与“硬件全 INT8”。
- [ ] 能说明 `0.1 dB` 门槛是项目决策预算，不是行业通用真理。
- [ ] 能准确陈述边界：当前为小样本 ORT CPU QDQ 证据，不是 TensorRT/NPU INT8 认证。
