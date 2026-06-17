# AI-ISP / ISP 算法工程师项目表达

## 3 分钟讲述

我做了一个阶段四 AI-ISP 部署闭环项目。前面阶段二已经训练过 SIDD paired RGB 去噪模型，阶段四我选择 DnCNN 作为第一部署模型，因为它结构简单、指标稳定，并且残差学习可以解释为 AI denoise 模块：网络预测噪声，再从输入中减掉噪声。

我先固定 20 张 SIDD tiny validation paired 图作为部署测试集，明确输入输出协议是 RGB、NCHW、float32、range `[0,1]`。PyTorch baseline 上，模型把平均 PSNR 从 26.57 dB 提升到 32.98 dB。

然后我把模型导出 ONNX，用 ONNX checker 检查 graph，并用 ONNX Runtime 跑同一批固定测试集。ORT 和 PyTorch 的最大误差约 4.17e-7，说明部署语义是一致的。

接着我做了 INT8 QDQ 静态量化。用 10 张图做 calibration，在 20 张图上评估，平均 PSNR drop 约 0.091 dB，最大 drop 约 0.337 dB，没有超过 0.5 dB 警戒线。对图像算法岗来说，我不会只说 INT8 更快，而是会看它是否带来暗区噪声、颜色偏移、纹理过平滑或高光问题。

最后我做了端到端 pipeline profiling，把 preprocess、inference、postprocess、save 分开计时。结果说明模型 inference 只是端到端的一部分，后续如果接 TensorRT 或 CUDA preprocess，也要看整体收益。

## 面试官可能追问

**为什么先选 DnCNN，不选 NAFNet-lite？**

DnCNN 当前 checkpoint 指标更稳定，ONNX graph 只有 Conv / Relu / Sub，更适合作为第一条部署闭环。NAFNet-lite 更现代，但涉及 LayerNorm、PixelShuffle 和 padding，对第一轮部署来说风险更高。

**为什么 ONNX 导出成功还要做对齐？**

导出成功只说明 graph 可以序列化，不说明数值语义一致。图像任务里 layout、range、clamp、normalization 的小错误会直接表现为偏色或画质异常。

**INT8 为什么对图像恢复更敏感？**

分类任务只需要类别不变，图像恢复要求每个像素、颜色和纹理都合理。量化误差可能表现为 banding、暗区噪声残留、颜色偏移或纹理过平滑。

