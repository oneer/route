# 阶段四总报告：证据、性能与边界

## 系统故事

阶段二训练得到 DnCNN RGB denoise checkpoint；阶段四冻结 checkpoint 和 20 张 SIDD tiny 输入，建立：

```text
PyTorch FP32
→ ONNX + ORT Python
→ ORT C++ raw tensor
→ CUDA / TensorRT FP32/FP16
→ ORT CPU QDQ INT8
→ CPU pipeline + CUDA normalize profile
```

阶段三 C++ ISP 和 Android 真机仍未接入，因此完整故事应表述为“RGB AI denoise 部署闭环”，不能包装成 sensor RAW ISP 或移动端量产部署。

## 资产追踪

机器可读表：`outputs/audit/asset_traceability.csv`。

| 对象 | 固定资产 |
|---|---|
| checkpoint/model | model card + SHA-256：`outputs/audit/model_card.json` |
| ONNX | `dncnn_sidd_tiny_fp32.onnx` + `.onnx.data` |
| engine | TensorRT 10.8 FP32/FP16 plan，仅记录环境可用 |
| input | Week 0 manifest；Week 4 独立 calibration/evaluation manifests |
| output/error | Week 0–6 output、CSV、error map、failure comparison |
| latency | ORT session CSV、trtexec JSON/log、pipeline CSV |

## Correctness matrix

完整表：`outputs/audit/correctness_matrix.csv`。

| Backend | Precision | Reference | 关键结果 | 状态 |
|---|---|---|---|---|
| ORT Python CPU | FP32 | PyTorch | max `4.17e-7` | 已复验 |
| ORT C++ CPU | FP32 | ORT Python raw | 20 张 max `0` | 已复验 |
| ORT CUDA | FP32 | ORT CPU | max `3.58e-7` | 已复验 |
| TensorRT EP | FP32 | ORT CPU | quality `32.98247 dB` | 已复验 |
| TensorRT EP | FP16 | ORT CPU | quality `32.98200 dB` | 已复验，有失败图 |
| ORT CPU QDQ | INT8 | ORT FP32 | 独立集 drop `0.08333 dB` | 已复验，有失败图 |

## Latency matrix

完整表：`outputs/audit/latency_matrix.csv`。核心原则：

- 不同设备、shape、batch、warmup、runs 不合并排名；
- `trtexec compute`、ORT session、C++ run、CPU pipeline 各自保留口径；
- engine build/session creation 与 steady-state 分开；
- GPU 数字说明同步和 copy 是否包含。

## 画质、速度与内存权衡

- FP16：`trtexec` compute 从 `1.968` 降到 `0.979 ms`，平均 PSNR drop 约 `0.00187 dB`；当前样本上值得接受。
- INT8 QDQ：模型资产约从 `132,767` 降到 `46,462 bytes`，CPU p50 从 `149.93` 降到 `121.25 ms`，平均 drop `0.08333 dB`；小样本初步可接受。
- CUDA normalize：kernel `0.0091 ms`，但 pageable H2D+D2H 使 stage E2E `3.798 ms`，慢于 CPU `2.498 ms`；当前不应接入并宣称加速。

## 状态总览

| 周次 | 状态 |
|---|---|
| Week 0 | 完成并复验 |
| Week 1 | 完成并复验 |
| Week 2 | 完成 raw tensor baseline；C++ GPU 未做 |
| Week 3 | 完成固定 shape FP32/FP16；C++ TRT/dynamic/Nsight 未做 |
| Week 4 | 完成 ORT CPU QDQ 独立 split；TRT/NPU INT8 未做 |
| Week 5 | 设计完成，真实移动端未完成 |
| Week 6 | profiling 与 kernel 验证完成，GPU E2E 接入未完成 |

## 当前未复验/未完成

- Android/ARM、NCNN/MNN、功耗、温度、移动端内存；
- 阶段三 C++ BLC/LSC/tone mapping 串联；
- CUDA preprocess → GPU inference 零/少拷贝 pipeline；
- pinned memory、stream overlap、CUDA event、Nsight Systems/Compute；
- TensorRT C++ runner、dynamic profile、TensorRT INT8；
- 更大且有场景标签的 calibration/test set。

## 下一步最值得做的三项

1. 把 CUDA preprocess device output 直接绑定到 ORT CUDA/TensorRT 输入，消除 D2H，并用 CUDA event/Nsight 重测。
2. 扩大并标注 calibration/evaluation 数据，补暗部、高光、纹理、颜色分组和 TensorRT INT8。
3. 若目标是手机影像岗位，选 NCNN，在真实 Android arm64 上完成 CPU/Vulkan/FP16 对齐、p50/p90、内存和温度测试。

## 岗位表达

项目价值不是“转出了 ONNX”，而是建立了可追踪模型资产、raw tensor correctness、独立量化 split、失败样本和多口径 latency；同时能明确拒绝把历史 engine、单 kernel 和桌面模拟包装成通用部署结果。
