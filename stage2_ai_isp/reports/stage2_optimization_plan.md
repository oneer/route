# 阶段二项目优化计划：AI-ISP 图像恢复与工程化基准

## 1. 目标

阶段二当前已经完成了从 toy RGB denoise 到 SIDD paired RGB、DnCNN/UNet/NAFNet-lite 对比、PSNR/SSIM 评估、可视化分析、pseudo RAW bridge 和 ONNX/C++ 部署入口的基础闭环。

下一步优化目标不是盲目堆模型，而是把项目从“能训练、能出指标”的学习项目，升级为更接近三年社招要求的工程项目：

```text
数据可信 -> baseline 清楚 -> 指标完整 -> 失败案例可解释 -> 部署路径可验证 -> 简历表达有边界
```

## 2. 当前状态判断

| 模块 | 当前证据 | 主要短板 |
|---|---|---|
| 数据 | SIDD tiny noisy/clean paired RGB，synthetic low-light，pseudo RAW/RGGB | 数据规模偏小，缺少分场景统计 |
| 模型 | DnCNN residual、UNet、NAFNet-lite | 对比矩阵还不够系统 |
| 指标 | PSNR、SSIM、三联图、error map、failure crop | 缺少感知质量、噪声、锐度、颜色、部署指标 |
| 工程 | 参数量、checkpoint 大小、ONNX/C++ 入口 | 延迟、ONNX 输出一致性、C++ 结果还未形成统一表 |
| 报告 | 周报、总表、升级计划、最终报告 | 需要一份面向社招的优化路线和验收标准 |

阶段二当前可以证明“有 AI-ISP 图像恢复训练闭环”。但如果按三年社招标准包装，还需要证明：

```text
1. 你知道 baseline 为什么重要；
2. 你知道 PSNR/SSIM 的局限；
3. 你能从质量、速度、模型大小、失败场景做工程取舍；
4. 你能把 RGB restoration 连接到 RAW-like / ISP pipeline；
5. 你能把 PyTorch 模型推进到 ONNX/C++ 验证。
```

## 3. 优化原则

1. 先补评估，再补模型。
   如果指标体系不完整，继续训练更复杂模型很容易变成“只看 PSNR 排名”。

2. 先固定 baseline，再做 ablation。
   每个新模型、新 loss、新数据设置都必须和 noisy input、DnCNN residual 进行对比。

3. 先小规模可复现，再扩大数据。
   当前 tiny 数据集适合快速闭环，后续扩展到更大 SIDD 子集时要保留同一套评估脚本。

4. 不夸大项目边界。
   这是 AI-ISP restoration and deployment baseline，不是量产 ISP tuning 项目。

## 4. 第一优先级：重新建立 noisy input baseline

### 目的

在 Week 3 或新一轮训练开始前，先重新测 noisy 输入本身的指标。这样后续所有模型结果都有清楚对照。

### 要补的内容

| 项目 | 说明 | 验收标准 |
|---|---|---|
| noisy input PSNR/SSIM | 直接比较 noisy 与 clean | 生成 baseline CSV |
| noisy input 可视化 | noisy/clean/error map | 生成固定样例图 |
| low-light input baseline | synthetic low-light 输入与 clean 对比 | 与 low-light UNet 结果同表 |
| pseudo RAW input baseline | pseudo RAW pack/demosaic 后与 clean 对比 | 至少记录可视化和 PSNR/SSIM |

### 输出物

```text
reports/figures/week3_noisy_baseline/
reports/week3_noisy_input_baseline.md
```

## 5. 第二优先级：指标体系升级

PSNR 和 SSIM 仍然保留，但不能只靠它们判断模型优劣。建议新增四类轻量指标。

| 指标类别 | 建议指标 | 解决的问题 |
|---|---|---|
| 感知质量 | LPIPS，或先用视觉 crop 近似替代 | PSNR 高但图像发糊的问题 |
| 噪声残留 | flat-region std、error std | 平坦区域是否去干净 |
| 细节保真 | Laplacian variance、edge PSNR | 是否过度平滑边缘和纹理 |
| 颜色稳定 | RGB channel mean、gray-world cast score | 是否产生偏色 |
| 工程成本 | latency、params、checkpoint MB、ONNX size | 是否具备部署讨论价值 |

最低可落地版本：

```text
PSNR / SSIM / flat noise std / Laplacian sharpness / params / checkpoint MB / latency
```

### 验收标准

统一生成一张表：

| Method | PSNR | SSIM | Noise Std | Sharpness | Params | CKPT MB | Latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| Noisy Input | 待测 | 待测 | 待测 | 待测 | - | - | - |
| DnCNN residual | 35.5356 | 0.88367 | 待测 | 待测 | 29507 | 0.351 | 待测 |
| UNet | 30.4453 | 0.88003 | 待测 | 待测 | 118307 | 1.380 | 待测 |
| NAFNet-lite | 33.3269 | 0.86223 | 待测 | 待测 | 104307 | 1.329 | 待测 |

## 6. 第三优先级：实验矩阵补齐

当前已有模型对比，但 ablation 还需要更像工程判断。

### 必做实验

| 实验 | 目的 | 预期结论 |
|---|---|---|
| DnCNN L1 vs L2 | 比较损失函数对噪声和细节的影响 | L2 通常 PSNR 更稳，L1 可能视觉更自然 |
| patch 64 vs 128 | 比较局部上下文大小 | patch 太小可能影响结构恢复 |
| 300/1000/2000 steps | 判断训练是否收敛 | 避免短训结果误导 |
| DnCNN vs UNet vs NAFNet-lite | 基础 CNN、encoder-decoder、现代 block 对比 | 说明模型复杂度和数据规模的关系 |
| RGB vs pseudo RGGB | 连接 AI-ISP 输入形态 | 证明 RAW-like 路径可训练 |

### 可选实验

| 实验 | 触发条件 |
|---|---|
| Charbonnier loss | 如果 L1/L2 视觉差异明显 |
| 更大 SIDD 子集 | 如果 tiny 结果已经稳定 |
| 暗光/正常光分桶评估 | 如果 low-light 结果要写进简历 |

## 7. 第四优先级：部署闭环补齐

部署方向要形成可复现链路：

```text
PyTorch checkpoint
-> ONNX export
-> ONNXRuntime 或 OpenCV DNN 推理
-> 输出图保存
-> PyTorch/ONNX 输出一致性检查
-> latency 统计
```

### 验收标准

| 项目 | 验收 |
|---|---|
| ONNX 导出 | `dncnn_sidd_tiny.onnx` 生成成功 |
| 一致性 | 同一输入下 PyTorch 与 ONNX 输出 MAE 可接受 |
| C++ 推理 | 能读入 noisy 图并保存 output |
| 延迟 | 记录 CPU 单张 128x128 或原图 crop latency |
| 报告 | 将 latency 加入 engineering summary |

## 8. 第五优先级：失败案例分析升级

当前已经有 failure crop。下一步要把失败案例从“看图”升级成“分类解释”。

| 失败类型 | 可能原因 | 应对方向 |
|---|---|---|
| 纹理被抹平 | MSE/L2 倾向平均解 | L1/Charbonnier，加入感知或边缘指标 |
| 暗部残噪 | low-light 噪声分布更复杂 | 分亮度区间训练和评估 |
| 边缘伪影 | patch/context 不足或模型过浅 | 增大 patch，换 UNet/NAFNet-lite |
| 颜色偏移 | RGB 通道统计不稳定 | 加颜色一致性指标 |
| 泛化弱 | tiny 数据太小 | 扩大 SIDD 子集 |

输出格式建议：

```text
case id
-> noisy/output/clean crop
-> PSNR/SSIM/local noise/local sharpness
-> 失败类型
-> 工程判断
-> 下一步实验
```

## 9. 三年社招版本里程碑

| 阶段 | 目标 | 验收 |
|---|---|---|
| M1 | 重新测 noisy baseline | baseline CSV + 报告 |
| M2 | 扩展指标 | 工程评估表包含质量和成本指标 |
| M3 | 完成 ablation | 至少 5 组实验可对比 |
| M4 | 跑通 ONNX/C++ | 有模型、输出图、latency |
| M5 | 升级 failure analysis | 失败类型可解释 |
| M6 | 更新最终报告和简历表达 | 一页项目总结 + 面试问答 |

## 10. 推荐执行顺序

```text
1. Week 3 开始前：重新测 noisy input baseline
2. Week 3-4：统一评估表，补 Noise Std / Sharpness / Params / CKPT MB
3. Week 4-5：补 DnCNN L1/L2、patch、steps ablation
4. Week 5-6：跑 pseudo RGGB 训练并纳入总表
5. Week 6-7：完成 ONNX export 和 C++ inference smoke test
6. Week 8：整理 failure case taxonomy
7. Week 9：更新最终报告、简历表达、面试讲述
```

## 11. 简历表达边界

可以写：

```text
基于 PyTorch 构建 AI-ISP 图像恢复与部署验证基准，完成 SIDD paired RGB 去噪、DnCNN/UNet/NAFNet-lite 对比、noisy input baseline、PSNR/SSIM/局部噪声/锐度评估、failure case 分析，并扩展 pseudo RAW/RGGB 与 ONNX/C++ 推理验证。
```

不要写：

```text
负责量产 ISP tuning
熟悉高通/MTK/海思 ISP 平台调试
完成工业级 RAW ISP 全链路
达到 SOTA 去噪效果
```

## 12. 最终验收标准

阶段二优化完成后，项目应能回答下面这些问题：

1. noisy input baseline 是多少，模型相比它提升了多少？
2. 为什么 DnCNN 在当前 tiny 数据上强于更复杂模型？
3. PSNR/SSIM 高低和视觉观感不一致时怎么判断？
4. 模型在平坦区、纹理区、暗部区域分别有什么问题？
5. 模型参数量、checkpoint 大小、推理延迟是否适合部署讨论？
6. pseudo RAW/RGGB 路径和普通 RGB denoise 有什么区别？
7. ONNX/C++ 推理是否和 PyTorch 输出基本一致？
8. 如果继续优化，下一步是扩大数据、换 loss，还是换模型？

如果这些问题都能用项目数据回答，阶段二就可以从“训练 demo”升级为“社招可讲的 AI-ISP 工程 baseline 项目”。
