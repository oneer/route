# advanced_study：先进论文与优秀开源项目学习模块

这个模块补齐当前项目偏实践的一侧：stage1-stage4 已经能让你把 Soft-ISP、AI-ISP、C++ ISP、ONNX/TensorRT 部署跑起来，但如果只停留在实现，会容易变成“知道怎么改代码，却不知道研究问题为什么这样演进”。`advanced_study/` 的目标是把论文、开源项目和当前代码练习连接起来：每读一篇论文，都要知道它解决了什么痛点；每读一个项目，都要知道哪些工程设计能迁移到自己的 ISP 学习仓库。

## 学习路线

建议按“传统 ISP -> AI-ISP -> 去噪增强 -> HDR/计算摄影 -> 基础模型 -> 部署 -> 开源项目”的顺序推进。这样先建立相机成像链路的物理和算法背景，再进入深度学习图像恢复，最后回到工程化部署和大型项目阅读。

## 模块目录说明

| 目录 | 方向 | 首批条目 |
|---|---|---|
| `isp_module_tutorials/` | 当前先进 ISP 模块教程 | RAW 前端、联合 Demosaic+Denoise、颜色、HDR/Tone、AI-ISP、端侧部署、画质验证 |
| `01_classic_isp_and_camera_pipeline/` | 传统 ISP、Camera Pipeline、计算摄影基线 | Karaimer & Brown 相机管线平台；HDR+ Burst Photography |
| `02_ai_isp_and_raw_restoration/` | RAW 到 RGB、AI-ISP、低光 RAW 恢复 | DeepISP；Learning to See in the Dark |
| `03_image_denoising_and_enhancement/` | 去噪、增强、现代图像恢复网络 | DnCNN；NAFNet |
| `04_hdr_tone_mapping_and_computational_photography/` | HDR、Tone Mapping、实时增强 | HDRNet；Deep HDR Imaging via Alignment and Fusion Network |
| `05_foundation_models_for_image_restoration/` | Transformer、Prompt、Diffusion、基础模型图像恢复 | PromptIR；DiffBIR |
| `06_efficiency_deployment_and_edge_ai/` | ONNX Runtime、TensorRT、端侧推理、高性能部署 | ONNX Runtime；NVIDIA TensorRT |
| `07_open_source_projects/` | 优秀开源 ISP/RAW/图像处理项目 | darktable；RawTherapee；Halide；KAIR |

## 推荐使用方式

如果目标是“学习当前比较先进的 ISP 模块”，先从 `isp_module_tutorials/` 开始。那里不是学习路线，而是按模块写的教程：每篇都讲这个模块在 pipeline 的位置、传统做法、先进做法、工程坑和本项目练习。

论文目录适合作为进一步精读材料：当你读完某个模块教程，再回到对应论文文档深入看具体方法。

## 推荐阅读顺序

1. 先读 `01_classic_isp_and_camera_pipeline/karaimer_brown_camera_pipeline.md`，理解为什么 ISP 管线需要可控、可替换、可观察。
2. 再读 `02_ai_isp_and_raw_restoration/learning_to_see_in_the_dark.md`，把 stage1 的 RAW 理解迁移到深度学习低光恢复。
3. 接着读 `03_image_denoising_and_enhancement/nafnet.md`，对照 stage2 的 NAFNet 复现实验，理解现代恢复网络为什么不一定需要复杂激活。
4. 然后读 `04_hdr_tone_mapping_and_computational_photography/hdrnet.md`，把 stage3 的 tone mapping 和高性能近似联系起来。
5. 再进入 `05_foundation_models_for_image_restoration/`，理解 Prompt 和 Diffusion 如何把单任务恢复扩展到多退化、真实退化。
6. 最后读 `06_efficiency_deployment_and_edge_ai/` 与 `07_open_source_projects/`，把研究模型落到可部署、可维护的工程形态。

## 和 stage1/stage2/stage3/stage4 的对应关系

| 当前阶段 | advanced_study 的补充作用 |
|---|---|
| stage1_soft_isp | 用论文解释传统模块顺序、RAW 数据假设、HDR+ 多帧思想和真实相机管线可控性。 |
| stage2_ai_isp | 用 SID、DeepISP、DnCNN、NAFNet、PromptIR 等材料解释训练数据、网络结构、损失函数和失败案例。 |
| stage3_cpp_isp | 用 HDRNet、Halide、darktable/RawTherapee 学习高性能图像处理、缓存友好算法和模块化管线设计。 |
| stage4_deploy_isp | 用 ONNX Runtime、TensorRT 学习模型导出、图优化、后端选择、FP16/INT8、profiling 和端侧约束。 |

## 每周学习建议

| 周次 | 建议任务 | 产出 |
|---|---|---|
| Week A | 精读 1 篇传统 ISP 或 RAW 论文 | 写 1 页“它和 stage1 哪个模块有关” |
| Week B | 精读 1 篇 AI-ISP/去噪论文 | 在 stage2 做一个最小复现实验或消融 |
| Week C | 阅读 1 个开源项目 | 画出目录结构和核心数据流 |
| Week D | 做一次工程迁移 | 把一个思想移植成小脚本、C++ 算子或部署检查项 |

## 使用规则

- 每篇论文或项目独立成文，不把资料堆在一个大表里。
- 每篇文档必须回答三个问题：为什么出现、怎么解决、我在当前项目里怎么练。
- 链接、年份、代码仓库和项目状态需要定期核对。当前首批条目按 2026-06-29 可访问资料整理。

## 文档质量标准

后续新增或扩写条目时，不能只写摘要。每篇论文至少要达到下面标准：

1. 讲清楚论文出现前的旧方法和痛点。
2. 讲清楚核心模块的输入、输出和直觉。
3. 说明实验结果应该怎么看，尤其是失败案例。
4. 明确对应到 stage1/stage2/stage3/stage4 的哪个练习。
5. 给出“面试级复述”，确保读者能用自己的话讲出来。

每个开源项目至少要达到下面标准：

1. 说明读这个项目要学习哪类工程能力。
2. 给出初学者阅读顺序，避免一上来陷入大仓库。
3. 指出最值得迁移到当前项目的功能点。
4. 定义阅读完成标准，而不是泛泛地说“了解项目”。
