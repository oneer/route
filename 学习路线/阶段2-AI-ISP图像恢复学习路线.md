# 阶段 2：AI-ISP 图像恢复学习路线

> **适用对象**：已经完成阶段 1，能理解 RAW → RGB 的传统 ISP 主链路，具备 Python / C++ / CUDA / Pipeline 对齐经验，但还缺少系统的 PyTorch 图像恢复训练、RAW 数据建模、真实噪声理解、论文复现和消融分析能力。
>
> **阶段周期**：8 周。
>
> **阶段目标**：从“会调用深度学习模型”升级到“能独立定义 AI-ISP / 图像恢复问题，构建数据集，训练 baseline，评估画质，做消融实验，解释失败案例，并能复现或改造一个主流图像恢复模型”。
>
> **阶段产出**：一个 `ai_isp_stage2/` 项目，一套可复现训练脚本，一份数据集分析报告，一个 RGB denoise baseline，一个 RAW low-light / RAW denoise baseline，一次 NAFNet 或轻量 UNet 复现实验，一份消融报告和一份面试复述笔记。

---

## 0. 阶段二的正确学习姿势

阶段二最容易学偏。不要把目标理解成“找一个 SOTA 网络跑出高 PSNR”。国内 AI-ISP / 图像算法岗更看重的是你能不能讲清：

- 输入数据到底是 RAW、linear RGB、sRGB，还是经过 ISP 的 JPEG？
- 退化来自哪里：噪声、欠曝、模糊、压缩、demosaic 伪影、颜色偏移，还是混合退化？
- GT 是否可信：长曝光参考、burst 平均、ISP 输出、专家修图、合成数据，各自有什么偏差？
- Loss 在哪个域算：RAW 域、linear RGB、sRGB，还是感知特征域？
- 指标是否可靠：PSNR / SSIM 高是否等于主观画质好？
- 模型是否能部署：参数量、FLOPs、显存、patch 推理、量化后的画质损失。

你已有工程优势，阶段二要把它用起来：训练结果不只是“模型好了”，而是要像工程评审一样回答“为什么这个模型、这份数据、这个 loss、这个指标、这个部署取舍是合理的”。

---

## 1. 最终项目结构

```text
ai_isp_stage2/
├── README.md
├── requirements.txt
├── configs/
│   ├── rgb_denoise_unet.yaml
│   ├── sidd_denoise_nafnet.yaml
│   └── sid_raw_lowlight_unet.yaml
├── datasets/
│   ├── README.md                 # 数据下载、目录结构、license 说明
│   ├── sidd/
│   ├── sid/
│   └── toy_rgb_denoise/
├── ai_isp/
│   ├── data/
│   │   ├── rgb_pair_dataset.py
│   │   ├── sidd_dataset.py
│   │   ├── sid_dataset.py
│   │   ├── raw_pack.py
│   │   └── degradations.py
│   ├── models/
│   │   ├── dncnn.py
│   │   ├── unet.py
│   │   ├── nafnet_lite.py
│   │   └── blocks.py
│   ├── losses/
│   │   ├── charbonnier.py
│   │   ├── ssim_loss.py
│   │   └── perceptual.py
│   ├── metrics/
│   │   ├── psnr_ssim.py
│   │   ├── lpips_metric.py
│   │   └── raw_metrics.py
│   ├── engine/
│   │   ├── train.py
│   │   ├── validate.py
│   │   ├── checkpoint.py
│   │   └── logger.py
│   └── utils/
│       ├── seed.py
│       ├── image_io.py
│       ├── visualization.py
│       └── profile.py
├── scripts/
│   ├── 01_prepare_toy_rgb.py
│   ├── 02_train_rgb_denoise.py
│   ├── 03_train_sidd.py
│   ├── 04_train_sid_raw.py
│   ├── 05_eval_checkpoint.py
│   ├── 06_visualize_failures.py
│   └── 07_ablation_summary.py
├── notebooks/
│   ├── 01_dataset_analysis.ipynb
│   ├── 02_loss_metric_behavior.ipynb
│   └── 03_failure_cases.ipynb
└── reports/
    ├── stage2_report.md
    ├── paper_notes/
    ├── ablations/
    └── figures/
```

**项目验收标准**：

- 至少完成一个 RGB 降噪 baseline 和一个 RAW / low-light 方向 baseline。
- 所有训练都能从配置文件复现。
- 每个实验都记录：数据集、输入域、输出域、模型、loss、指标、patch size、batch size、学习率、训练时长、显存占用。
- 至少做 3 组消融：loss、模型结构、数据退化/输入域。
- 至少整理 20 张失败案例，按“噪声残留、过平滑、偏色、伪纹理、暗部脏、高光异常、边缘伪影”分类。

---

## 2. 公开资源调研与使用方式

### 2.1 官方文档 / 训练工程资料

| 资源 | 链接 | 阶段二怎么用 |
|---|---|---|
| PyTorch AMP 官方文档 | https://docs.pytorch.org/docs/stable/amp.html | 学会 `torch.autocast` 和 `torch.amp.GradScaler`，用于混合精度训练。 |
| PyTorch AMP examples | https://docs.pytorch.org/docs/2.9/notes/amp_examples.html | 参考梯度缩放、梯度裁剪、DDP 场景下 AMP 的正确写法。 |
| PyTorch TensorBoard tutorial | https://docs.pytorch.org/tutorials/recipes/recipes/tensorboard_with_pytorch.html | 用 TensorBoard 记录 loss、PSNR、SSIM、图像对比和学习率。 |
| BasicSR | https://github.com/XPixelGroup/BasicSR | 图像恢复训练工程参考。重点学配置、数据集、训练日志、模型注册和验证流程。 |
| MMagic | https://github.com/open-mmlab/mmagic | 更完整的 OpenMMLab 图像恢复框架参考。阶段二只学习结构，不建议一开始重度依赖。 |
| IQA-PyTorch / pyiqa | https://github.com/chaofengc/IQA-PyTorch | 用于 PSNR、SSIM、LPIPS、NIQE 等指标，阶段二主要用 PSNR / SSIM / LPIPS。 |
| scikit-image metrics | https://scikit-image.org/docs/stable/api/skimage.metrics.html | 轻量计算 PSNR / SSIM，适合自己 baseline 项目。 |

**使用要求**：先自己写一个最小训练框架，再读 BasicSR / MMagic。否则容易变成“会改配置但不知道训练流程为什么这样设计”。

### 2.2 数据集

| 数据集 | 链接 | 任务 | 阶段二怎么用 |
|---|---|---|---|
| SIDD | https://abdokamel.github.io/sidd/ | 真实智能手机图像降噪 | RGB / sRGB 降噪首选。理解真实噪声和合成高斯噪声的差异。 |
| DND | https://noise.visinf.tu-darmstadt.de/ | 真实图像降噪 benchmark | 主要用于理解评测协议。阶段二不强求提交 benchmark。 |
| SID | https://cchen156.github.io/ | RAW 低光增强 | RAW low-light 学习核心数据集。重点学短曝光 RAW、长曝光参考和 4ch pack。 |
| LOL / LOLv2 | https://paperswithcode.com/dataset/lolv2 | 低光照增强 | 用于 sRGB 低光增强。注意它不是 RAW 域，和 SID 的问题定义不同。 |
| LSRW / R2RNet | https://github.com/abcdef2000/R2RNet | 真实低光配对增强 | 用于理解真实低光数据采集和泛化问题。 |
| MIT-Adobe FiveK | https://data.csail.mit.edu/graphics/fivek/ | RAW / 专家修图 | 阶段二可用于 RAW-to-sRGB / tone 风格理解，训练暂不主攻。 |

**数据集选择建议**：

- 第一个 baseline 用小规模 RGB 合成噪声数据，目的是跑通训练工程。
- 第二个 baseline 用 SIDD，目的是接触真实噪声。
- 第三个 baseline 用 SID，目的是进入 AI-ISP 的 RAW 域。
- 不要一开始同时下载所有大数据集；先小样本跑通，再扩大规模。

### 2.3 必读论文

| 论文 | 链接 | 阶段二阅读重点 |
|---|---|---|
| DnCNN: Beyond a Gaussian Denoiser | https://github.com/cszn/DnCNN | 残差学习、预测噪声而不是直接预测干净图、传统 CNN denoise baseline。 |
| Learning to See in the Dark | https://arxiv.org/abs/1805.01934 | RAW 低光增强、短曝光/长曝光配对、RAW pack、端到端 RAW→RGB。 |
| Unprocessing Images for Learned Raw Denoising | https://arxiv.org/abs/1811.11127 | 反向 ISP / unprocess，如何从 sRGB 合成接近 RAW 的训练数据。 |
| CycleISP | https://arxiv.org/abs/2003.07761 | RAW ↔ sRGB 循环建模，真实图像恢复的数据合成思路。 |
| NAFNet: Simple Baselines for Image Restoration | https://arxiv.org/abs/2204.04676 | 简洁高效的图像恢复 baseline，SimpleGate、SCA、LayerNorm。 |
| Restormer | https://arxiv.org/abs/2111.09881 | 高分辨率图像恢复中的 Transformer 设计，阶段二了解为主。 |
| MPRNet | https://arxiv.org/abs/2102.02808 | 多阶段渐进恢复思想，了解图像恢复中 coarse-to-fine 的设计。 |
| PyNET | https://arxiv.org/abs/2002.05509 | 用单个模型替代手机 ISP 的端到端思路，了解即可。 |
| DeepISP | https://arxiv.org/abs/1801.06724 | 端到端学习 ISP pipeline 的早期代表，了解 RAW 到最终图像的学习式 pipeline。 |
| AWNet | https://arxiv.org/abs/2008.09228 | 图像 ISP 中小波和注意力的结合，作为 RAW-to-sRGB 方向补充。 |

**论文阅读模板**：

```text
论文要解决的问题：
输入域 / 输出域：
数据集和 GT 如何获得：
模型结构的关键设计：
Loss 和指标：
实验消融说明了什么：
工程部署或泛化风险：
和传统 ISP 哪些模块相关：
我能复现的最小版本：
```

### 2.4 开源项目

| 项目 | 链接 | 阶段二怎么用 |
|---|---|---|
| SID official code | https://github.com/cchen156/Learning-to-See-in-the-Dark | 学 RAW pack、SID 数据组织、低光增强训练流程。代码较旧，重点读思想。 |
| NAFNet official | https://github.com/megvii-research/NAFNet | 主复现项目。重点读模型、配置、SIDD 训练和评估流程。 |
| CycleISP official | https://github.com/swz30/CycleISP | 学 RAW / sRGB 数据合成和测试脚本，不要求完整复现。 |
| Unprocessing reference code | https://github.com/timothybrooks/unprocessing | 学 `random_ccm`、`random_gains`、`random_noise_levels` 等反向 ISP 数据合成思想。 |
| Restormer official | https://github.com/swz30/Restormer | 了解高分辨率 transformer 图像恢复，不作为第一复现目标。 |
| MPRNet official | https://github.com/swz30/MPRNet | 了解多阶段恢复和训练工程。 |
| KAIR | https://github.com/cszn/KAIR | Kai Zhang 的图像恢复工具箱，适合参考 DnCNN、DRUNet 等 baseline。 |
| MAI Learned Smartphone ISP | https://github.com/MediaTek-NeuroPilot/mai21-learned-smartphone-isp | 学移动端 learned ISP challenge 的 baseline 和 RAW→DSLR 风格目标。 |
| AWNet | https://github.com/Charlie0215/AWNet-Attentive-Wavelet-Network-for-Image-ISP | 作为 RAW-to-sRGB / learned ISP 方向参考。 |

### 2.5 博客 / 解读资料

| 资源 | 链接 | 用法 |
|---|---|---|
| NAFNet 中文解读 CSDN | https://blog.csdn.net/qq_41994006/article/details/127859059 | 辅助理解 SimpleGate、SCA、网络结构，不替代原论文。 |
| NAFNet DeepWiki | https://deepwiki.com/megvii-research/NAFNet/1-overview | 快速理解 NAFNet 项目结构和任务配置。 |
| SIDD 解读笔记 | https://youcaijun98.github.io/articles/CV/LLCV/Denoising/SIDD_dataset.html | 辅助理解 SIDD 采集和 GT 生成。 |
| Unprocessing 解读笔记 | https://youcaijun98.github.io/articles/CV/LLCV/Denoising/Unprocessing%20Images%20for%20Learned%20Raw%20Denoising.html | 辅助理解反向 ISP 数据合成。 |
| BasicSR 中文介绍 | https://www.dongaigc.com/p/XPixelGroup/BasicSR | 快速了解 BasicSR 能做什么，具体实现以 GitHub 为准。 |

**博客使用原则**：博客适合降低入门成本，但最终结论要回到论文、官方代码和你自己的实验。

---

## 3. 八周详细路线

### Week 0.5：环境、项目骨架和最小训练闭环

**目标**：先跑通训练闭环，不在复杂数据集和大模型上卡住。

**学习内容**：

- PyTorch Dataset / DataLoader / model / loss / optimizer / scheduler。
- checkpoint 保存和恢复。
- TensorBoard 记录 loss、图像、指标。
- 固定随机种子，保证实验可复现。

**具体步骤**：

1. 创建 `ai_isp_stage2/` 项目结构。
2. 实现最小训练脚本：
   - 随机生成输入图 `noisy = clean + gaussian_noise`
   - 模型用 3 层 CNN
   - loss 用 L1
   - 训练 100～500 iteration，确认 loss 下降
3. 增加 checkpoint 保存：
   - `last.pth`
   - `best_psnr.pth`
4. 增加 TensorBoard：
   - train loss
   - val PSNR
   - noisy / output / target 三联图
5. 写 `README.md` 的实验复现命令。

**掌握标准**：

- 能从零解释一次训练中 forward、loss、backward、optimizer、scheduler、validation 的顺序。
- 能恢复 checkpoint 继续训练。
- 能用 TensorBoard 找到训练是否发散、过拟合或指标不涨。
- 能说清为什么阶段二第一步不直接跑 NAFNet。

**交付物**：

- `ai_isp/engine/train.py`
- `ai_isp/engine/validate.py`
- `ai_isp/utils/seed.py`
- `reports/week0_training_loop.md`

### Week 1：RGB 合成噪声 DnCNN / UNet baseline

**目标**：用最简单的数据和模型建立图像恢复直觉。

**学习内容**：

- DnCNN：残差学习，预测噪声或预测干净图。
- UNet：encoder-decoder、skip connection、patch 训练。
- 合成高斯噪声和真实噪声的差异。
- PSNR / SSIM 的基本使用。

**具体步骤**：

1. 准备一个小型 clean RGB 数据集，可以用阶段一处理后的图、FiveK 小样本或公开自然图像。
2. 实现合成退化：
   - 固定 sigma 高斯噪声
   - 随机 sigma 高斯噪声
   - Poisson-Gaussian 简化噪声
3. 实现 DnCNN 或轻量 UNet。
4. 训练两个版本：
   - 直接预测 clean
   - 预测 residual noise
5. 对比两者的收敛速度、PSNR、视觉效果。

**小实验**：

- sigma=15 训练，sigma=25 测试，观察泛化下降。
- L1 vs L2 对比输出平滑程度。
- patch size 64 / 128 / 256 对比显存和效果。

**掌握标准**：

- 能解释 residual learning 为什么适合 denoise。
- 能解释 patch 训练为什么常用于图像恢复。
- 能说明合成高斯噪声和真实 sensor noise 的差别。
- 能独立训练出一个输出明显比 noisy 更干净的 baseline。

**交付物**：

- `ai_isp/models/dncnn.py`
- `ai_isp/models/unet.py`
- `ai_isp/data/degradations.py`
- `reports/week1_rgb_denoise_baseline.md`

### Week 2：SIDD 真实图像降噪 baseline

**目标**：进入真实噪声数据，理解真实数据比合成数据难在哪里。

**学习内容**：

- SIDD 数据结构和真实噪声来源。
- noisy / GT 配对关系。
- sRGB denoise 和 RAW denoise 的区别。
- 数据划分、crop、augmentation、benchmark 注意事项。

**具体步骤**：

1. 下载 SIDD 小版本或选择少量 scene 作为训练子集。
2. 写 `SIDDPairDataset`：
   - 读取 noisy / GT pair
   - random crop
   - flip / rotate
   - normalize 到 `[0, 1]`
3. 用 Week 1 的 UNet baseline 在 SIDD 上训练。
4. 对比合成噪声训练模型和 SIDD 训练模型在真实 noisy 图上的效果。
5. 输出失败案例分类。

**小实验**：

- 用合成高斯噪声训练的模型直接测试 SIDD。
- 用 SIDD 训练的模型测试合成高斯噪声。
- 分析两者谁更容易过平滑、谁更容易残留彩噪。

**掌握标准**：

- 能说明真实噪声不是 i.i.d. Gaussian。
- 能解释为什么相机、ISO、光照、ISP 处理都会影响噪声分布。
- 能讲清 SIDD 的 GT 不是“天然干净图”，而是通过采集和估计得到。
- 能对真实降噪结果做失败案例分类。

**交付物**：

- `ai_isp/data/sidd_dataset.py`
- `configs/sidd_denoise_unet.yaml`
- `reports/week2_sidd_real_noise.md`

### Week 3：SID / RAW low-light 数据流

**目标**：进入 AI-ISP 核心：RAW 域输入、低光增强、RAW pack、短曝光到长曝光映射。

**学习内容**：

- SID 数据集：Sony / Fuji，短曝光 RAW 与长曝光参考。
- RAW pack：Bayer 2x2 → 4 channel。
- exposure ratio：短曝光图像乘以曝光比例。
- RAW 输入、RGB 输出和 GT 生成方式。

**具体步骤**：

1. 阅读 SID paper 和 official code 的数据读取部分。
2. 实现 `pack_raw()`：
   - RGGB → 4ch
   - 注意 black level 归一化
   - 注意 H/W 减半后 target 尺寸如何对齐
3. 写 `SIDDataset`：
   - input：short exposure RAW pack
   - target：long exposure rawpy postprocess RGB 或论文式 target
   - ratio：long exposure / short exposure
4. 先不训练大模型，只可视化：
   - short RAW pack 四通道
   - 乘 ratio 后的输入
   - target RGB
5. 训练一个极小 UNet，确认网络能 overfit 1～5 张图。

**小实验**：

- 不乘 exposure ratio 训练，观察模型是否难以收敛。
- black level 处理前后对比输入分布。
- 只训练 1 张图，看模型能否过拟合到 target。如果不能，说明数据链路有 bug。

**掌握标准**：

- 能解释 SID 为什么用 RAW 输入而不是 JPEG 输入。
- 能说明 4ch pack 的空间分辨率和通道含义。
- 能解释 exposure ratio 在低光增强中的作用。
- 能用 overfit 小样本验证 Dataset / model / loss 链路是否正确。

**交付物**：

- `ai_isp/data/raw_pack.py`
- `ai_isp/data/sid_dataset.py`
- `configs/sid_raw_lowlight_unet.yaml`
- `reports/week3_sid_raw_pipeline.md`

### Week 4：Loss / Metric / 可视化评估体系

**目标**：建立 AI-ISP 训练结果的评价语言，不只看 loss。

**学习内容**：

- Loss：L1、L2、Charbonnier、SSIM、Perceptual。
- Metrics：PSNR、SSIM、LPIPS、RAW 域误差、RGB 域误差。
- 训练曲线与主观画质的关系。
- ROI 分析：暗部、边缘、高光、肤色、纹理区域。

**具体步骤**：

1. 实现 loss 模块：
   - Charbonnier loss
   - L1 + SSIM
   - 可选 perceptual loss
2. 实现 metric 模块：
   - PSNR
   - SSIM
   - LPIPS
3. 每次 validation 保存：
   - noisy / input
   - output
   - target
   - error map
   - zoomed ROI
4. 用同一模型训练 3 组 loss：
   - L1
   - L2
   - L1 + SSIM
5. 写分析：指标变好是否等于主观变好。

**小实验**：

- 对同一输出加轻微亮度偏移，观察 PSNR 变化。
- 对输出做轻微 blur，观察 PSNR 和主观锐度冲突。
- 对低光图暗部 ROI 单独计算 PSNR / SSIM。

**掌握标准**：

- 能解释 Charbonnier 为什么比 L2 对异常值更鲁棒。
- 能说明感知 loss 可能提升主观效果，也可能牺牲像素级指标。
- 能根据 error map 找到模型主要错误区域。
- 能把失败图按原因分类，而不是只说“效果不好”。

**交付物**：

- `ai_isp/losses/`
- `ai_isp/metrics/`
- `scripts/06_visualize_failures.py`
- `reports/week4_loss_metric_visualization.md`

### Week 5：NAFNet / 轻量图像恢复模型复现

**目标**：复现一个现代图像恢复强 baseline，重点理解模型设计取舍。

**学习内容**：

- NAFNet：SimpleGate、SCA、LayerNorm、U-shaped backbone。
- 为什么图像恢复里 BN 可能不如 LN / no BN 稳定。
- 模型参数量、FLOPs、显存和 patch size。
- 复现策略：先跑官方推理，再训练小模型，再做轻量改造。

**具体步骤**：

1. 阅读 NAFNet paper 和 official repo。
2. 先跑官方 demo 或 pretrained model，确认环境。
3. 实现 `NAFBlockLite`：
   - LayerNorm2d
   - SimpleGate
   - simplified channel attention
   - residual scaling
4. 用 SIDD 小子集训练 NAFNet-lite。
5. 与 Week 2 UNet baseline 对比：
   - PSNR / SSIM / LPIPS
   - 参数量
   - 单张推理耗时
   - 显存占用

**小实验**：

- 去掉 SimpleGate，换 ReLU / GELU。
- 去掉 SCA。
- LN vs BN / no norm。
- 通道数 16 / 32 / 64 对比效果和速度。

**掌握标准**：

- 能解释 NAFNet 为什么说“不需要传统非线性激活”。
- 能说明 SimpleGate 的门控直觉。
- 能讲清模型效果提升和计算代价之间的关系。
- 能完成一个不是复制粘贴的 NAFNet-lite 实现，并跑出对比结果。

**交付物**：

- `ai_isp/models/nafnet_lite.py`
- `configs/sidd_denoise_nafnet.yaml`
- `reports/week5_nafnet_reproduction.md`

### Week 6：RAW 噪声建模与数据合成

**目标**：补 AI-ISP 最关键的能力：数据建模，而不是只换网络。

**学习内容**：

- Poisson-Gaussian 噪声模型。
- shot noise / read noise / gain / ISO。
- Unprocessing：sRGB → linear → camera RGB → RAW-like。
- CycleISP：RAW ↔ sRGB 循环数据合成。
- 真实噪声、合成噪声和 domain gap。

**具体步骤**：

1. 阅读 Unprocessing paper 和 reference code。
2. 实现简化 unprocess：
   - inverse gamma
   - inverse tone mapping 简化
   - inverse color correction
   - inverse white balance
   - mosaic
   - add Poisson-Gaussian noise
3. 用干净 RGB 图合成 RAW-like noisy / clean pair。
4. 用合成数据训练一个 RAW denoise 小模型。
5. 测试在真实 SID / SIDD RAW-like 数据上的泛化。

**小实验**：

- 只加 Gaussian noise vs Poisson-Gaussian。
- 固定 CCM / gain vs random CCM / gain。
- 在 sRGB 域加噪 vs 在 RAW-like 域加噪。

**掌握标准**：

- 能解释为什么直接在 sRGB 上加高斯噪声不够真实。
- 能说明 unprocessing 每一步在反向模拟哪个 ISP 模块。
- 能讲清合成数据带来的 domain gap。
- 能回答“数据建模和网络结构哪个更重要”这类面试问题。

**交付物**：

- `ai_isp/data/degradations.py`
- `notebooks/02_loss_metric_behavior.ipynb`
- `reports/week6_raw_noise_synthesis.md`

### Week 7：消融实验、失败案例和泛化分析

**目标**：把阶段二从“能训练”提升到“能做算法实验”。

**学习内容**：

- 消融实验设计。
- failure case mining。
- cross-dataset evaluation。
- 过拟合、数据泄漏、benchmark 污染、训练/验证分布不一致。

**具体步骤**：

1. 设计至少 5 组消融：
   - UNet vs NAFNet-lite
   - L1 vs Charbonnier vs L1+SSIM
   - Gaussian vs Poisson-Gaussian
   - RGB input vs RAW pack input
   - patch size / channel width 对比
2. 写 `07_ablation_summary.py` 自动汇总表格。
3. 从验证集找 PSNR 最低的 20 张图。
4. 对失败案例分类：
   - 暗部噪声残留
   - 过平滑
   - 颜色偏移
   - 伪纹理
   - 高光异常
   - 边缘伪影
5. 写每类失败的可能原因和下一步改进。

**掌握标准**：

- 能提出一个清晰假设，再设计实验验证它。
- 能区分训练集指标提升和泛化能力提升。
- 能解释为什么某些模型在一个数据集上好，在另一个数据集上差。
- 能从失败案例反推数据、模型、loss 或后处理的问题。

**交付物**：

- `reports/ablations/`
- `notebooks/03_failure_cases.ipynb`
- `reports/week7_ablation_failure_analysis.md`

### Week 8：阶段报告、作品集和面试表达

**目标**：把阶段二整理成可展示、可面试、可接阶段三部署的项目。

**具体步骤**：

1. 整理 `README.md`：
   - 项目目标
   - 数据集
   - 模型结构
   - 训练命令
   - 结果表格
   - 可视化结果
   - 消融实验
   - 失败案例
2. 写 `reports/stage2_report.md`：
   - 为什么选择 SIDD / SID
   - RGB denoise 和 RAW low-light 的差别
   - UNet / NAFNet-lite 对比
   - loss / metric 观察
   - 数据建模实验
   - 下一阶段部署计划
3. 准备 15 个面试问题和答案。
4. 准备一个 10 分钟项目讲述：
   - 1 分钟背景
   - 2 分钟数据和任务定义
   - 2 分钟模型和训练
   - 2 分钟结果和消融
   - 2 分钟失败案例
   - 1 分钟工程落地思考

**掌握标准**：

- 能解释自己的 AI 项目不是“套模型”，而是围绕数据域、退化、loss、metric 和工程约束设计。
- 能把阶段一传统 ISP 知识和阶段二 AI 模型连接起来。
- 能说明模型若部署到端侧，最先要压缩或改造哪里。
- 能回答“为什么你的模型输出比传统 ISP 好，代价是什么”。

**最终交付物**：

- 可复现训练项目：`ai_isp_stage2/`
- 阶段报告：`reports/stage2_report.md`
- 消融报告：`reports/ablations/summary.md`
- 面试笔记：`reports/stage2_interview_notes.md`

---

## 4. 每个能力点的掌握标准

| 能力 | 入门 | 掌握 | 面试可讲 |
|---|---|---|---|
| PyTorch 训练工程 | 能跑通训练循环 | 能配置化、保存 checkpoint、记录 TensorBoard | 能定位 loss 不降、显存爆、验证指标异常 |
| Dataset | 能读取图片 pair | 能处理 crop、augment、normalize、RAW pack | 能解释输入/输出域、GT 来源和数据偏差 |
| RGB denoise | 能训练 UNet / DnCNN | 能对比合成噪声和真实噪声 | 能说明真实噪声为什么难 |
| RAW low-light | 能读取 SID RAW | 能正确 pack、乘 ratio、对齐 target | 能解释 RAW 输入对 AI-ISP 的价值 |
| Loss | 会用 L1 / L2 | 能实现 Charbonnier / SSIM / perceptual | 能解释 loss 与主观画质的冲突 |
| Metrics | 会算 PSNR / SSIM | 能加入 LPIPS、ROI、error map | 能说明指标适用范围和误导性 |
| NAFNet | 能跑官方代码 | 能实现 NAFNet-lite 并训练 | 能解释 SimpleGate、SCA、LN 和效率优势 |
| 数据建模 | 会加 Gaussian noise | 能做 Poisson-Gaussian / unprocess | 能解释 domain gap 和真实退化建模 |
| 消融 | 能改参数跑实验 | 能自动汇总表格和失败案例 | 能从实验反推算法改进方向 |

---

## 5. 阶段二面试问题清单

1. 图像恢复和分类检测任务在训练目标上有什么不同？
2. 为什么图像恢复常用 patch 训练？
3. DnCNN 为什么预测 noise residual？
4. UNet 的 skip connection 对图像恢复有什么帮助？
5. 为什么真实噪声不等于高斯噪声？
6. SIDD 的 noisy / GT 是怎么来的？有什么偏差？
7. SID 为什么用短曝光 RAW 和长曝光参考？
8. RAW pack 的 4 个通道分别是什么？空间分辨率如何变化？
9. exposure ratio 在低光增强里起什么作用？
10. L1、L2、Charbonnier loss 有什么区别？
11. SSIM loss 为什么可能改善结构，但不一定提升所有主观效果？
12. PSNR 高但图像发糊，可能是什么原因？
13. LPIPS 和 PSNR 的关注点有什么不同？
14. NAFNet 的 SimpleGate 为什么有效？
15. 为什么图像恢复里 BatchNorm 有时不合适？
16. NAFNet 和 UNet 相比，优势和代价是什么？
17. Unprocessing 为什么要反向模拟 ISP？
18. 在 sRGB 域加噪和 RAW 域加噪有什么差异？
19. 真实数据少时，如何构造训练数据？
20. 如何判断模型过拟合？
21. 如何做 failure case analysis？
22. 如果模型暗部噪声残留严重，你会怎么改？
23. 如果模型输出偏色，你会从数据、loss、模型哪些方面排查？
24. 如果模型部署后 PSNR 下降，可能是什么原因？
25. 你的 AI-ISP 模型替代或增强了传统 ISP 的哪个模块？

---

## 6. 阶段二结束后的自检

如果下面问题能回答清楚，阶段二就算真正完成：

- 我能不能从零搭一个可复现 PyTorch 图像恢复训练工程？
- 我能不能说清 SIDD、SID、DND、LOL 这些数据集分别解决什么问题？
- 我能不能解释 RAW 域训练和 sRGB 域训练的差异？
- 我能不能实现并训练一个 UNet / DnCNN baseline？
- 我能不能实现一个 NAFNet-lite，并讲清它和普通 UNet 的差别？
- 我能不能设计至少 3 组有明确假设的消融实验？
- 我能不能根据失败案例判断是数据、模型、loss、metric 还是后处理的问题？
- 我能不能把阶段一传统 ISP 的模块知识，映射到阶段二 AI 模型的输入输出和退化建模？

---

## 7. 阶段二不要做什么

- 不要一开始就追 Restormer / diffusion / 大模型。
- 不要只看论文结构图，不跑数据、不看失败案例。
- 不要用 benchmark 指标代替自己的实验分析。
- 不要把所有数据都 resize 到很小后得出画质结论。
- 不要只保存最终输出图，必须保存 input / output / target / error map / ROI。
- 不要把 BasicSR / MMagic 当黑盒；先写自己的最小训练框架。
- 不要忽视 license 和数据集协议，尤其是 SIDD、DND、SID 这类 benchmark。

---

## 8. 推荐执行顺序摘要

```text
Week 0.5  最小训练闭环
  -> 能训练一个 tiny CNN，并保存 checkpoint / TensorBoard

Week 1    RGB 合成噪声 baseline
  -> 能训练 DnCNN / UNet，理解 residual denoise

Week 2    SIDD 真实噪声
  -> 能训练真实图像降噪模型，理解真实噪声和合成噪声差异

Week 3    SID RAW low-light
  -> 能读取 RAW、pack 4ch、乘 exposure ratio，并 overfit 小样本

Week 4    Loss / Metric / 可视化
  -> 能用 PSNR / SSIM / LPIPS / error map / ROI 分析模型

Week 5    NAFNet-lite 复现
  -> 能解释 SimpleGate / SCA / LayerNorm，并和 UNet 对比

Week 6    RAW 噪声建模
  -> 能实现简化 unprocess / Poisson-Gaussian 数据合成

Week 7    消融与失败案例
  -> 能从实验和失败图反推算法问题

Week 8    阶段报告与面试表达
  -> 能把 AI-ISP 项目讲成数据、算法、指标、工程闭环
```

---

## 9. 阶段二与阶段三的衔接

阶段二结束时不要急着继续换模型。进入阶段三前，先从阶段二项目里选一个最小可部署模型：

- 优先选择 NAFNet-lite / UNet-lite，而不是 Restormer。
- 输入分辨率、通道数和 patch 推理方式要固定。
- 保存一组固定测试图，用于后续 ONNX / TensorRT / NCNN 输出对齐。
- 记录 PyTorch FP32 baseline 的 PSNR / SSIM / LPIPS / latency，作为部署阶段的基准。

阶段三的目标不是重新训练更强模型，而是把这个模型导出、对齐、加速、量化，并解释画质损失。
