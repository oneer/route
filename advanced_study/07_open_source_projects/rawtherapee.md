# RawTherapee

## 深度阅读目标

RawTherapee 适合学习传统 RAW 处理软件的算法厚度。它比 stage1 复杂得多，因为它要面对真实相机、真实用户、真实参数组合。读它的目标不是复刻，而是理解一个成熟 RAW engine 如何支持多种 demosaic、denoise、sharpen、color management 和 output profile。

## 读代码的具体顺序

建议先围绕 `rtengine/`，不要先读 GUI。

1. 先了解 RawTherapee 的用户处理流程：打开 RAW、选择 profile、调整曝光/白平衡/降噪、输出。
2. 进入 `rtengine/`，找一个与你 stage1 对应的模块，比如 demosaic、white balance 或 tone curve。
3. 看参数从 profile 如何进入 engine。
4. 看算法是否有多种实现，比较为什么要保留多个算法。
5. 最后再看 GUI 如何把用户参数传给 engine。

## 对本项目最有价值的工程点

第一是多算法并存。stage3 已经有 Reinhard、Filmic、ACES、percentile 等 tone mapping，这可以学习 RawTherapee 的方式统一成算法选择和参数 profile。

第二是相机兼容。真实 RAW 不是一个格式，black level、white level、CFA、color matrix 都可能不同。stage1 可以从 RawTherapee 学到：RAW 处理要尊重相机元数据，而不是写死常量。

第三是 profile 思想。处理参数应该可以保存、复用、比较。

## 可迁移练习

1. 为 `stage1_soft_isp/configs/default.yaml` 增加更清楚的模块参数注释文档。
2. 在 stage3 设计统一 tone mapping interface：同一输入、不同算法、同一 metrics 输出。
3. 写一个 RAW 元数据检查表：black level、white level、CFA pattern、color matrix 是否进入处理链。

## 阅读完成标准

你读完后应该能说明：RawTherapee 这类项目的难点不是单个算法，而是大量相机、参数、算法和输出目标共存时，如何保持处理稳定、可复现和可维护。

## 项目信息
- GitHub：https://github.com/Beep6581/RawTherapee
- Star 数或活跃度：长期维护的开源 RAW 处理项目，具体 Star 数以 GitHub 页面为准。
- 主要语言：C++

## 项目解决什么问题

RawTherapee 是专业 RAW 照片处理软件，覆盖 demosaic、曝光、白平衡、降噪、锐化、色彩管理、镜头校正和输出转换。它对学习传统 ISP 和 RAW 后期非常有价值。

## 项目目录结构解读

建议先看：

- `rtengine/`：核心 RAW 处理引擎。
- `rtgui/`：图形界面。
- `tools/`：辅助工具。
- `data/`：配置、profile、资源。

## 核心模块说明

`rtengine` 是重点，它包含 RAW 解码后的大量处理逻辑。和 stage1 的学习项目相比，RawTherapee 更复杂，因为它要支持多相机、多算法、多参数和真实用户交互。

## 如何和当前项目关联

stage1 手写了简化 Soft-ISP，RawTherapee 则展示工业级 RAW 软件如何组织传统图像处理算法。stage3 可以借鉴它的 C++ 模块边界和算法实现风格。

## 值得学习的工程设计

- 大量相机和 RAW 格式兼容。
- 多种 demosaic/denoise 算法并存。
- 参数 profile 和处理队列。
- 颜色管理与输出配置。

## 初学者阅读顺序

1. 先读文档和用户界面，知道有哪些模块。
2. 再读 `rtengine` 中一个小模块，避免一开始追完整 pipeline。
3. 对照 stage1 的同名模块理解差距。
4. 最后看参数如何从 GUI 传到 engine。

## 可迁移到当前项目的功能点

1. 给 stage1 的每个模块增加参数说明和默认值表。
2. 给 stage3 增加多个 tone mapping 算法统一接口。
3. 学习如何为不同输入保留处理 profile。

## 阅读后应该掌握什么

你应该能看到：传统 RAW 软件的工程复杂度来自“真实世界输入很多、用户可调参数很多、输出要求很稳定”。
