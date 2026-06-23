# AI-ISP 部署项目表达

## 三分钟版本

我从阶段二固定了一个 DnCNN RGB 去噪 checkpoint，并冻结 20 张 SIDD tiny 输入和 `RGB/NCHW/float32/[0,1]` 协议。PyTorch 平均 PSNR 是 32.98 dB。

ONNX 导出后，我用 checker 和 ORT Python 做 20 张 raw tensor 对齐，最大误差 `4.17e-7`；随后实现 ORT C++ runner，20 张 C++ float tensor 与 Python ORT reference 完全一致。这里我没有只比较 PNG，因为 uint8 round 会掩盖误差。

GPU 侧用 TensorRT 10.8 在 RTX 4060 Ti 重建 FP32/FP16 engine。FP16 的 `trtexec` compute mean 约 `0.979 ms`，ORT TensorRT EP session mean 约 `7.458 ms`，说明 copy 和 runtime 开销不能忽略。FP16 平均质量 PSNR 只比 ORT CPU 低约 `0.0019 dB`，并保留了最差样本图。

量化使用 ORT CPU QDQ，而不是把它说成 TensorRT INT8。我把 20 张数据拆成 10 张 calibration 和 10 张独立 evaluation，平均 PSNR drop `0.0833 dB`、最差 `0.2403 dB`，并生成 error map/crop。

最后我拆分了 CUDA normalize：kernel 只有 `0.0091 ms`，但 pageable H2D+D2H 后 GPU stage 是 `3.798 ms`，慢于 CPU normalize `2.498 ms`。所以当前不声称 CUDA 端到端加速；下一步应消除 D2H，把 device tensor 直接交给 GPU inference。

## 常见追问

**为什么选 DnCNN？**

当前 checkpoint 稳定，graph 只有 Conv/ReLU/Sub，适合建立第一条正确性闭环。选择它是为了控制部署变量，不代表它是最先进模型。

**为什么 ONNX 成功还要对齐？**

导出只证明图可序列化；layout、range、clamp 和算子语义仍可能错。

**为什么 C++ 不能只比 PNG？**

float 差异经过 clamp 和 uint8 round 后可能消失，造成“完全一致”的假象。

**INT8 结论能否推广到 TensorRT/NPU？**

不能。当前只证明 ORT CPU QDQ 在独立小评价集上的结果；不同后端的 kernel、融合和 scale 处理可能不同。

**为什么 CUDA kernel 快但整体更慢？**

当前前处理需要 pageable H2D 和 D2H；copy 成本远大于 kernel。局部 kernel 时间不能替代 pipeline 时间。

**移动端完成了吗？**

没有。仓库没有 Android/ARM 设备、adb、NCNN/MNN runner、功耗或温度证据，移动端章节明确是设计与后续路径。
