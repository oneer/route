# AI-ISP 图像算法工程师 · 社招完整学习路线

> **适用背景**：软件工程专业，1.5年工作经验，掌握C++（含底层内存/多线程）、Python，目标岗位：AI-ISP 图像算法工程师（社招）
>
> **个人背景补充**：本科与研究生均为软件工程专业，主要接受软件开发、工程架构、C++/Python 编程训练，暂缺数字电路、模拟电路、图像传感器硬件等系统背景，但具备继续补齐硬件与成像物理知识的学习意愿。
>
> **已有 ISP 工程经验**：入职半导体公司后，参与既有 ISP Pipeline 的 Python 参考模型与 C++ 工程实现维护，主要承担 Python/C++ 双栈输出对齐、浮点逻辑定点化改造、量化参数与舍入策略适配、跨语言精度差异排查等工作；维护 Python 端 ISP Pipeline，梳理模块数据流与调用关系，确保 Python 与 C++ 输出一致。
>
> **已有性能与 GPU 经验**：编写过多个 CUDA 卷积算子，在 Python 端完成 GPU 调用链路接入，涉及基础卷积核实现、显存分配、线程块划分与原型验证加速。
>
> **已有 C++ Pipeline 重构经验**：参与 ISP 核心模块从单通道架构向四通道并行架构迁移，覆盖 HDR、AWB、RDN、AST 以及 RGB2YUV、YUV2RGB 等色彩处理模块。主要工作包括四通道数据流改造、内存布局与数据排布适配、通道状态隔离、Padding 与边界像素同步、跨版本输出一致性验证。
>
> **已有框架与验证经验**：扩展过四通道、4K、交替行、交替帧、混合模式等多条 Pipeline 框架，处理模式切换、状态保存、上下文恢复与边界异常问题；维护 Star Detect 框架，开发 Wrapper 封装层、FB（Frame/Line Buffer）、TPG（Test Pattern Generator）、HMIR（Horizontal Mirror）等模块；为重构模块和新模块搭建测试环境、编写自动化比对脚本，覆盖常规数据流、边界条件、多模式切换与跨版本对齐场景。
>
> **当前主要短板**：已有较强的软件工程、Pipeline 改造、结果对齐和验证经验，但过去更多是在既有算法模块基础上做工程迁移与适配，对 ISP 各模块的物理依据、数学推导、画质指标、调参逻辑、AI-ISP 数据建模与端侧部署取舍理解还不够系统。本路线应重点从“会改代码、会对齐结果”升级到“能解释算法、能设计实验、能独立评估画质与性能”。
>
> **国内岗位调研结论**：国内 ISP / AI-ISP 算法工程师招聘要求的高频交集是：数字图像处理基础、完整 ISP Pipeline 理解、AE/AWB/AF/3A、Demosaic、色彩校正、锐化、降噪、HDR/WDR、图像质量评价、C/C++/Python 工程能力、PyTorch 图像恢复、模型压缩和端侧部署。结合当前背景，本路线不按“零基础入门”设计，而按“已有 ISP 工程经验 → 补算法解释力 → 补画质评估与调参 → 补 AI-ISP 建模 → 补部署闭环”的顺序设计。
>
> **十个月总目标**：10 个月后形成 3 个可面试项目：1）传统 Soft-ISP Pipeline，能解释每个模块的物理含义、数学依据、调参影响和失败场景；2）RAW/RGB 降噪或暗光增强 AI 项目，能讲清数据、网络、Loss、指标、失败案例和消融；3）C++ / 定点化 / 部署闭环项目，能展示 Python-C++ 对齐、四通道/4K 数据流、性能优化、ONNX/TensorRT/NCNN/ONNX Runtime 之一的推理链路。
>
> **整体周期**：10 个月系统学习
>
> **核心理念**：以项目为驱动，扔掉一切与图像处理无关的包袱，用 "物理理解 → 代码验证 → AI替换 → 工程部署" 四步闭环建立核心竞争力

---

## 目录

1. [知识点优先级总览](#一知识点优先级总览)
2. [教程资源取舍清单](#二教程资源取舍清单)
3. [阶段一：物理地基 —— ISP Pipeline 全流程](#阶段一物理地基--isp-pipeline-全流程4-6-周)
4. [阶段二：AI 灵魂 —— 深度学习图像重构](#阶段二ai-灵魂--深度学习图像重构6-8-周)
5. [阶段三：工程利刃 —— C++ 高性能图像处理](#阶段三工程利刃--c-高性能图像处理4-5-周)
6. [阶段四：部署闭环 —— CUDA 加速与端侧 AI 推理](#阶段四部署闭环--cuda-加速与端侧-ai-推理4-6-周)
7. [10 个月执行路线](#五10-个月执行路线)
8. [必读论文精选列表](#六必读论文精选列表)
9. [必看开源项目清单](#七必看开源项目清单)
10. [公开课推荐](#八公开课推荐)
11. [面试高频考点与答题框架](#九面试高频考点与答题框架)
12. [GitHub 作品集搭建指南](#十github-作品集搭建指南)
13. [技术栈全景图](#十一技术栈全景图)

---

## 一、知识点优先级总览

### 1.0 国内 ISP / AI-ISP 岗位要求映射

| 国内招聘高频要求 | 你已有基础 | 当前缺口 | 本路线对应训练 |
|---|---|---|---|
| C/C++ / Python 工程能力 | 已做 Python/C++ 双栈对齐、C++ Pipeline 改造、自动化比对脚本 | 需要把工程经验沉淀成可展示项目和方法论 | Month 8、Month 10 |
| ISP Pipeline 熟悉度 | 已维护 Python ISP Pipeline，做过 C++ 多模式 Pipeline 集成 | 过去更多关注数据对齐和功能迁移，对模块物理含义与调参影响理解不足 | Month 1、Month 2、Month 3 |
| Demosaic / 色彩 / 锐化 / 降噪 / 宽动态 | 接触过 HDR、AWB、RDN、AST、RGB/YUV 色彩模块改造 | 需要补算法原理、失败场景、画质评价和参数取舍 | Month 2、Month 4、Month 5 |
| 3A：AE / AWB / AF | 接触过 AWB 和 Pipeline 状态/模式切换 | AE/AF 控制闭环、AWB 色温估计、HDR 场景联动理解不足 | Month 4 |
| 图像质量评价与 IQ 调试 | 有输出一致性验证经验 | 缺少主客观画质指标、ROI 分析、问题归因与调参报告能力 | Month 3、Month 5 |
| AI 图像增强 / 降噪 / 超分 / 暗光增强 | 有 Python、CUDA 算子、基础 GPU 调用经验 | 需要补 PyTorch 训练、RAW 数据建模、Loss 和消融实验 | Month 6、Month 7 |
| 模型压缩与端侧部署 | 有 CUDA 卷积算子经验 | 需要补 ONNX / TensorRT / NCNN / ONNX Runtime、量化和部署后画质评估 | Month 9 |
| 硬件与成像物理理解 | 半导体公司工作环境，接触 ISP 数据流 | 缺数字/模拟电路和 Sensor 物理背景，但不需要按芯片设计深度学习 | Month 1、Month 4 |

**学习优先级判断**：你的短板不是“不会写代码”，而是“算法解释力、画质判断、数据建模、方案设计”。因此学习时不要把重点放在刷 C++ 语法、泛泛看深度学习课或堆论文数量，而要持续追问：这个模块解决什么画质问题？输入输出是什么数据域？参数怎么影响画质？如何验证它真的变好？工程部署后会损失什么？

| 知识模块                    | 优先级      | 学习深度要求                                 | 备注                     |
| ----------------------- | -------- | -------------------------------------- | ---------------------- |
| 传统 ISP Pipeline 理论      | **S 级**  | 能口述每个模块数学原理 + 手写代码实现                   | 所有算法的物理依据，面试必考         |
| PyTorch & 深度学习图像恢复      | **S 级**  | 能独立复现顶会论文，改动网络结构                       | AI-ISP 核心竞争力           |
| Python / NumPy / OpenCV | **S 级**  | 熟练矩阵操作、图像 I/O、可视化                      | 已有基础，继续强化              |
| C++ 高级（内存/并发/SIMD）      | **A 级**  | 写出 Cache 友好 + 多线程 + SIMD 优化的代码         | 决定薪资天花板                |
| CUDA 并行计算               | **A 级**  | 能写 Kernel、用 Shared Memory 优化、掌握 Stream | 端侧部署核心                 |
| 图像质量评价（IQ Evaluation）   | **A 级**  | 能用代码计算 PSNR/SSIM/LPIPS/MTF             | 算法效果量化基准               |
| Sensor 物理噪声模型           | **A 级**  | 理解泊松-高斯噪声模型，写出噪声合成代码                   | 训练数据合成的依据              |
| TensorRT / ONNX 部署      | **A 级**  | 独立完成模型→TensorRT→C++ 推理完整链路             | 高薪岗必备                  |
| 3A 算法控制逻辑               | **B 级**  | 理解统计学模型和状态机设计                          | ISP 系统层理解              |
| Halide 图像优化语言           | **B 级**  | 了解算法与调度分离的思想，能看懂示例                     | 大厂 ISP 常用              |
| ARM NEON / SIMD 内联汇编    | **B 级**  | 了解基本 Intrinsics 用法                     | 移动端优化                  |
| GAMES101 图形学            | **C 级** | 不系统学，只补相机模型/色彩/成像相关内容                 | 图形渲染主线与 ISP 不同，避免跑偏        |
| OpenCL / Vulkan Compute | **C 级** | 暂不主攻，了解移动/嵌入式异构计算中的位置                 | 若目标平台要求再补，不要一开始投入过深 |
| Go / 后端框架 / 网络库         | **❌ 放弃** | 不学                                     | 与图像算法方向完全无关            |

---

## 二、教程资源取舍清单

### ✅ 保留精读（立即开始）

| 教程/资源                   | 重点章节                         | 学习方式          |
| ----------------------- | ---------------------------- | ------------- |
| **大话成像（全系列）**           | Sensor 物理、Pipeline 全流程、IQ 评价 | 视频 + 代码同步验证   |
| **侯捷 C++ 全系列**          | 内存管理、STL 源码剖析                | 精读，配合写 ISP 代码 |
| **多线程原理讲解**             | 线程池、互斥锁、条件变量                 | 精读，结合图像并行处理   |
| **现代 C++ 实战 / C++20**   | 智能指针、move语义、并发库              | 选读，按需查阅       |
| **51CTO OpenCV C++ 实战** | 图像读写、颜色空间转换、几何变换             | 边学边用          |

### ⏸ 暂缓（等到阶段三之后）

| 教程/资源 | 暂缓原因 | 何时启动 |
|---|---|---|
| **音视频流媒体开发** | 编解码是 ISP 下游内容 | 阶段四完成后 |

### ❌ 立即删除 / 暂不投入（避免主线跑偏）

| 教程/资源 | 删除原因 |
|---|---|
| GAMES101 图形学 | 不系统学；只在需要相机模型、色彩、成像几何时查相关章节 |
| Linux 后台开发架构师 | 分布式系统，毫无关联 |
| Go 语言全系列 | ISP/图像算法工程链路不使用 Go |
| Muduo / Reactor 网络库 | 高并发后端，完全偏离方向 |
| KV 存储 / 分布式云盘 | 存储系统方向 |
| Django 快速开发 | Web 后端，无关 |
| C++ 全栈聊天项目 | 业务逻辑开发，无关 |

---

> **阅读说明**：下面的阶段一到阶段四是“能力模块说明”，用于解释每类知识该学什么；真正的执行节奏以第五章的“10 个月执行路线”为准。不要按阶段标题里的周数硬赶进度，尤其不要为了赶进度跳过每月产出和掌握标准。

## 阶段一：物理地基 — ISP Pipeline 全流程（4-6 周）

> **目标**：搞懂光子到像素的完整链路，建立图像数据流直觉，能用代码跑通基础 Pipeline
>
> **核心问题**：不懂这个，你的 AI 降噪网络就是无本之木，因为你不知道输入数据的物理含义

---

### 1.1 Sensor 物理基础

#### 必须掌握的知识点

**光电转换过程**
- 光子打到硅晶格，激发电子-空穴对（光电效应）
- 满阱容量（Full Well Capacity, FWC）：每个像素最多能存储的电荷数
- 量子效率（Quantum Efficiency, QE）：入射光子到电子的转化率

**Bayer 阵列**
- 排列方式：RGGB（最常见）/ BGGR / GRBG / GBRG
- 为什么 G 点是 R/B 的两倍：模拟人眼对亮度的感知（亮度通道以绿色为主）
- CFA（Color Filter Array）的物理本质：每个像素只感知单一颜色

**Sensor 噪声模型（重点！训练数据合成的基础）**

```
总噪声 = 散粒噪声 + 读出噪声 + 暗电流 + 固定模式噪声

散粒噪声（Shot Noise）：
  - 服从泊松分布：Var(X) = E(X) = μ
  - 换算到 DN 值：σ²_shot = k × μ  （k = 转换增益 e-/DN）

读出噪声（Read Noise）：
  - 服从高斯分布：N(0, σ²_read)
  - 由 ADC 电路引入，与信号强度无关

完整 Poisson-Gaussian 噪声模型：
  y = Poisson(x/k) × k + N(0, σ²_read)
  
等价近似（信号较强时）：
  y = x + N(0, k·x + σ²_read)
```

**噪声标定方法**
```python
# 拍摄不同曝光时间的平场（均匀照明）帧
# 统计每帧的均值 mu 和方差 sigma²
# 线性拟合：sigma² = k * mu + sigma²_read
# 斜率即转换增益 k，截距即读出噪声方差

import numpy as np

def calibrate_noise(frames_at_different_exposures):
    mus, vars_ = [], []
    for frame in frames_at_different_exposures:
        mus.append(np.mean(frame))
        vars_.append(np.var(frame))
    k, sigma_read_sq = np.polyfit(mus, vars_, 1)
    return k, sigma_read_sq
```

**深度要求**：能写出噪声合成函数，给干净图像加真实 Sensor 噪声

---

#### 推荐学习资源

| 资源类型 | 资源名称 | 地址/来源 | 重点内容 |
|---|---|---|---|
| 课程 | 大话成像 - Sensor 篇 | 已购 | Bayer 阵列、噪声模型 |
| 论文 | A Practical Model for the Sensitivity of a Camera | Hasinoff 2014 | 泊松噪声模型推导 |
| 论文 | Noise Flow: Noise Modeling with Conditional Normalizing Flows | ICCV 2019 | 高级噪声建模 |
| 开源 | rawpy (Python) | `pip install rawpy` | 读取 .dng/.raw 文件 |
| 数据集 | EMVD Noise Dataset | 论文附带 | 多 ISO 真实噪声标定数据 |

---

### 1.2 ISP 核心模块算法

#### 完整 Pipeline 顺序及每个模块详解

**Step 0：RAW 数据读取**
```python
import rawpy
import numpy as np

raw = rawpy.imread('input.dng')
raw_array = raw.raw_image_visible.astype(np.float32)
# 注意：raw_array 是 Bayer 阵列，形状为 (H, W)，值范围通常 0-4095（12-bit）
```

---

**Step 1：黑电平扣除（BLC - Black Level Correction）**

原理：Sensor 在完全黑暗时仍有漏电流，输出不为零。需减去这个偏置值。

```python
def black_level_correction(raw, black_level, white_level):
    """
    black_level: 通常从 Sensor Datasheet 或 OTP 读取，如 64
    white_level: 通常为 4095（12-bit）
    """
    raw_blc = (raw - black_level) / (white_level - black_level)
    return np.clip(raw_blc, 0, 1)
```

**面试考点**：黑电平值从哪里来？（Sensor Datasheet / 标定 / OTP 烧录）

---

**Step 2：坏点校正（DPC - Defect Pixel Correction）**

原理：制造缺陷导致部分像素永远过亮（Hot Pixel）或过暗（Dead Pixel）

```python
def detect_hot_pixels(raw, threshold=0.95):
    """用局部均值检测坏点"""
    from scipy.ndimage import uniform_filter
    local_mean = uniform_filter(raw, size=5)
    hot_mask = (raw > local_mean * threshold * 2)  # 显著高于邻域均值
    return hot_mask

def correct_defect_pixels(raw, defect_map):
    """用 Median 替换坏点"""
    from scipy.ndimage import median_filter
    corrected = raw.copy()
    median = median_filter(raw, size=5)
    corrected[defect_map] = median[defect_map]
    return corrected
```

---

**Step 3：镜头暗角校正（LSC - Lens Shading Correction）**

原理：镜头边缘透光率低于中心（cos⁴θ 定律），导致图像四角偏暗偏色

```python
def compute_lsc_gain_map(H, W, center_gain=1.0, edge_gain=1.6):
    """
    生成简化的 LSC 增益图（实际工程中从积分球标定数据拟合得到）
    真实的 LSC 是对每个颜色通道（R/Gr/Gb/B）分别标定
    """
    cy, cx = H / 2, W / 2
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt((x - cx)**2 + (y - cy)**2) / np.sqrt(cx**2 + cy**2)
    gain = center_gain + (edge_gain - center_gain) * r**2
    return gain

def apply_lsc(raw_bayer, gain_map_r, gain_map_g, gain_map_b):
    # 实际按 RGGB 通道分别施加不同增益
    pass
```

**面试考点**：LSC 增益图是如何标定的？（积分球 / 均匀灰板，计算与理论值的偏差）

---

**Step 4：去马赛克（Demosaicing）**

原理：Bayer 阵列每个位置只有一个颜色，需要从邻域插值恢复完整 RGB

```python
# 方法一：双线性插值（简单，有伪彩色）
def bilinear_demosaic(raw_bayer, H, W):
    """
    RGGB 排列：
    R G R G ...
    G B G B ...
    """
    R  = raw_bayer[0::2, 0::2]   # (H/2, W/2)
    Gr = raw_bayer[0::2, 1::2]
    Gb = raw_bayer[1::2, 0::2]
    B  = raw_bayer[1::2, 1::2]
    
    # 用 scipy 上采样到全分辨率
    from scipy.ndimage import zoom
    R_full  = zoom(R,  2, order=1)
    Gr_full = zoom(Gr, 2, order=1)
    Gb_full = zoom(Gb, 2, order=1)
    G_full  = (Gr_full + Gb_full) / 2
    B_full  = zoom(B,  2, order=1)
    
    return np.stack([R_full, G_full, B_full], axis=-1)

# 方法二：AHD（Adaptive Homogeneity-Directed，工业常用）
# 思路：在水平和垂直方向分别做插值，用同质度（homogeneity）指标选更优方向
# 参考实现：rawpy 内部使用 LibRaw 的 AHD 实现
```

**深度要求**：
- 能实现双线性插值版本
- 能解释 AHD 为什么比双线性好（方向自适应，减少边缘伪彩）
- 了解 MLRI、LMMSE 等更先进算法的思路

---

**Step 5：自动白平衡（AWB - Auto White Balance）**

```python
# 方法一：灰度世界假设
def gray_world_awb(rgb):
    mean_r = np.mean(rgb[:,:,0])
    mean_g = np.mean(rgb[:,:,1])
    mean_b = np.mean(rgb[:,:,2])
    
    gain_r = mean_g / mean_r
    gain_b = mean_g / mean_b
    
    balanced = rgb.copy()
    balanced[:,:,0] *= gain_r
    balanced[:,:,2] *= gain_b
    return np.clip(balanced, 0, 1)

# 方法二：完美反射假设（取最亮点为白色参考）
def white_patch_awb(rgb, percentile=99):
    ref_r = np.percentile(rgb[:,:,0], percentile)
    ref_g = np.percentile(rgb[:,:,1], percentile)
    ref_b = np.percentile(rgb[:,:,2], percentile)
    
    gain_r = ref_g / ref_r
    gain_b = ref_g / ref_b
    
    balanced = rgb.copy()
    balanced[:,:,0] *= gain_r
    balanced[:,:,2] *= gain_b
    return np.clip(balanced, 0, 1)
```

**面试考点**：
- 灰度世界假设在什么场景下失效？（大面积纯色场景：红墙、绿草坪）
- 工程中如何做色温估计？（Gamut Map 统计方法）

---

**Step 6：色彩校正矩阵（CCM - Color Correction Matrix）**

原理：Sensor 的 CFA 滤色片响应曲线与标准观察者（CIE 1931）不一致，需矩阵线性变换校正

```python
def compute_ccm(sensor_colors, reference_colors):
    """
    sensor_colors:    (N, 3) Sensor 拍摄的 24 色卡 RGB 值
    reference_colors: (N, 3) 标准色卡的 sRGB 参考值
    
    求解 3x3 矩阵 M 使得 sensor_colors @ M.T ≈ reference_colors
    用最小二乘法
    """
    M, _, _, _ = np.linalg.lstsq(sensor_colors, reference_colors, rcond=None)
    return M.T  # shape: (3, 3)

def apply_ccm(rgb, ccm_matrix):
    """rgb: (H, W, 3)，应用 3x3 CCM"""
    h, w, _ = rgb.shape
    rgb_flat = rgb.reshape(-1, 3)  # (H*W, 3)
    corrected = (ccm_matrix @ rgb_flat.T).T  # (H*W, 3)
    return np.clip(corrected.reshape(h, w, 3), 0, 1)
```

---

**Step 7：Gamma 校正**

原理：人眼对亮度的感知是非线性的（韦伯-费希纳定律），sRGB 标准定义了标准 Gamma 曲线

```python
def apply_srgb_gamma(linear):
    """线性光强度 → sRGB 编码值"""
    gamma_corrected = np.where(
        linear <= 0.0031308,
        12.92 * linear,
        1.055 * np.power(linear, 1.0/2.4) - 0.055
    )
    return np.clip(gamma_corrected, 0, 1)
```

---

**Step 8：图像评价指标计算**

```python
def compute_psnr(img1, img2, max_val=1.0):
    """Peak Signal-to-Noise Ratio（越高越好，30dB以上为可接受）"""
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')
    return 20 * np.log10(max_val / np.sqrt(mse))

def compute_ssim(img1, img2):
    """Structural Similarity Index（越接近1越好）"""
    from skimage.metrics import structural_similarity
    return structural_similarity(img1, img2, channel_axis=-1, data_range=1.0)

def compute_delta_e(lab1, lab2):
    """色彩偏差（CIE Delta E 2000，<2为人眼不可分辨）"""
    # 需要先将 RGB 转换到 Lab 色彩空间
    pass
```

---

#### 阶段一：里程碑项目

> **项目名称**：Python 版极简 Soft-ISP Pipeline

**项目要求**：
1. 读取真实相机拍摄的 `.dng` 文件（可用 Sony A7系列/Pixel 手机 ProRAW）
2. 依次实现 BLC → LSC → Demosaic → AWB → CCM → Gamma 全流程
3. 每个模块前后计算并打印图像统计（均值/方差/直方图）
4. 与 Adobe Lightroom 默认渲染输出对比，分析差距

**验收标准**：能把一张 RAW 黑白马赛克数据，转换为有色彩的 RGB 图像，并知道每个差距的原因

---

#### 阶段一公开课推荐

| 课程名 | 机构 | 地址 | 重点 |
|---|---|---|---|
| Computational Photography | Georgia Tech (Udacity) | https://www.udacity.com/course/computational-photography--ud955 | RAW 图像处理基础 |
| CS194-26 Computational Photography | UC Berkeley | https://inst.eecs.berkeley.edu/~cs194-26/ | 图像形成与处理 |
| Digital Photography | Stanford EE367 | https://stanford.edu/class/ee367/ | 图像质量分析 |
| Image and Video Processing | Duke (Coursera) | https://www.coursera.org/learn/image-processing | Matlab/Python 实现 |

---

### 1.3 3A 算法控制逻辑

#### AE 自动曝光

**核心指标**：
- EV（曝光值）= log₂(N² / t)，N为光圈，t为快门
- Metering（测光）：分区测光、中央重点测光、点测光
- 收敛策略：PI 控制器（比例-积分），防止曝光来回震荡

```python
class AutoExposureController:
    def __init__(self, target_brightness=0.18, Kp=0.3, Ki=0.05):
        self.target = target_brightness
        self.Kp = Kp
        self.Ki = Ki
        self.integral = 0
    
    def update(self, current_brightness):
        error = self.target - current_brightness
        self.integral += error
        ev_delta = self.Kp * error + self.Ki * self.integral
        return ev_delta  # 正值：增加曝光；负值：减少曝光
```

---

### 1.4 噪声模型合成（训练数据的基础）

```python
def synthesize_sensor_noise(clean_image, k=0.003, sigma_read=5.0, iso=1600):
    """
    合成真实 Sensor 噪声用于 AI-ISP 训练数据增强
    
    clean_image: 干净的图像，值域 [0, 1]
    k: 转换增益（shot noise 系数），从噪声标定得到
    sigma_read: 读出噪声标准差（DN），从噪声标定得到
    iso: ISO 感光度（高 ISO → 高增益 → 更多噪声）
    """
    iso_gain = iso / 100.0
    k_eff = k * iso_gain
    sigma_read_eff = sigma_read * iso_gain
    
    # Shot noise (Poisson)
    shot_noise = np.random.poisson(clean_image / k_eff) * k_eff - clean_image
    
    # Read noise (Gaussian)  
    read_noise = np.random.normal(0, sigma_read_eff / 255.0, clean_image.shape)
    
    noisy = clean_image + shot_noise + read_noise
    return np.clip(noisy, 0, 1)
```

---

## 阶段二：AI 灵魂 — 深度学习图像重构（6-8 周）

> **目标**：用神经网络替代和增强传统 ISP 模块，达到复现顶会论文的水平
>
> **核心问题**：招聘需求明确要求"深度学习图像增强/超分/降噪"，这是你与传统 ISP 调试工程师的核心差异化竞争力

---

### 2.1 PyTorch 工程化能力

#### 必须掌握的进阶用法

**自定义 Dataset（处理 RAW 图像）**

```python
import torch
from torch.utils.data import Dataset
import rawpy
import numpy as np

class SIDDataset(Dataset):
    """See-in-the-Dark 数据集加载器"""
    
    def __init__(self, input_dir, target_dir, patch_size=256, augment=True):
        self.input_paths = sorted(glob.glob(f"{input_dir}/*.ARW"))
        self.target_paths = sorted(glob.glob(f"{target_dir}/*.ARW"))
        self.patch_size = patch_size
        self.augment = augment
    
    def pack_raw(self, raw_image):
        """将 Bayer 阵列打包成 4 通道（RGGB → 4 channel）"""
        # 这是 SID 论文的关键技巧！
        H, W = raw_image.shape
        packed = np.zeros((H//2, W//2, 4), dtype=np.float32)
        packed[:,:,0] = raw_image[0::2, 0::2]  # R
        packed[:,:,1] = raw_image[0::2, 1::2]  # Gr
        packed[:,:,2] = raw_image[1::2, 0::2]  # Gb
        packed[:,:,3] = raw_image[1::2, 1::2]  # B
        return packed
    
    def __getitem__(self, idx):
        # 读取短曝光 RAW（有噪声）
        input_raw = rawpy.imread(self.input_paths[idx])
        input_array = self.pack_raw(input_raw.raw_image_visible.astype(np.float32))
        
        # 读取长曝光 RAW（参考）
        target_raw = rawpy.imread(self.target_paths[idx])
        target_rgb = target_raw.postprocess(use_camera_wb=True, half_size=False,
                                             no_auto_bright=True, output_bps=16)
        target_array = (target_rgb / 65535.0).astype(np.float32)
        
        # 数据增强
        if self.augment:
            input_array, target_array = self.random_crop_and_flip(
                input_array, target_array, self.patch_size)
        
        return torch.from_numpy(input_array).permute(2,0,1), \
               torch.from_numpy(target_array).permute(2,0,1)
```

**自定义 Loss 函数**

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class CharbonnierLoss(nn.Module):
    """比 L2 更鲁棒，对异常值不那么敏感"""
    def __init__(self, eps=1e-3):
        super().__init__()
        self.eps = eps
    
    def forward(self, pred, target):
        diff = pred - target
        return torch.mean(torch.sqrt(diff**2 + self.eps**2))

class SSIMLoss(nn.Module):
    def __init__(self, window_size=11):
        super().__init__()
        self.window_size = window_size
    
    def forward(self, pred, target):
        # pytorch-msssim 库提供高效实现
        from pytorch_msssim import ssim
        return 1 - ssim(pred, target, data_range=1.0)

class CombinedLoss(nn.Module):
    """实际工程中常用的组合损失"""
    def __init__(self, l1_weight=1.0, ssim_weight=0.1):
        super().__init__()
        self.l1 = CharbonnierLoss()
        self.ssim = SSIMLoss()
        self.l1_w = l1_weight
        self.ssim_w = ssim_weight
    
    def forward(self, pred, target):
        return self.l1_w * self.l1(pred, target) + \
               self.ssim_w * self.ssim(pred, target)
```

**混合精度训练（大幅提速）**

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

for batch in dataloader:
    optimizer.zero_grad()
    
    with autocast():  # 自动选择 FP16/FP32
        output = model(input)
        loss = criterion(output, target)
    
    scaler.scale(loss).backward()
    scaler.unscale_(optimizer)
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=0.01)
    scaler.step(optimizer)
    scaler.update()
```

---

### 2.2 核心网络架构精讲

#### UNet（图像恢复基础架构）

```python
import torch
import torch.nn as nn

class DoubleConv(nn.Module):
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )
    def forward(self, x): return self.conv(x)

class UNet(nn.Module):
    def __init__(self, in_ch=4, out_ch=3, features=[64, 128, 256, 512]):
        super().__init__()
        self.downs = nn.ModuleList()
        self.ups = nn.ModuleList()
        self.pool = nn.MaxPool2d(2, 2)
        
        # Encoder
        for f in features:
            self.downs.append(DoubleConv(in_ch, f))
            in_ch = f
        
        # Bottleneck
        self.bottleneck = DoubleConv(features[-1], features[-1]*2)
        
        # Decoder（注意跳跃连接 Concat，所以输入是 2x）
        for f in reversed(features):
            self.ups.append(nn.ConvTranspose2d(f*2, f, 2, 2))
            self.ups.append(DoubleConv(f*2, f))
        
        self.final = nn.Conv2d(features[0], out_ch, 1)
    
    def forward(self, x):
        skip_connections = []
        for down in self.downs:
            x = down(x)
            skip_connections.append(x)
            x = self.pool(x)
        
        x = self.bottleneck(x)
        skip_connections = skip_connections[::-1]
        
        for i in range(0, len(self.ups), 2):
            x = self.ups[i](x)
            skip = skip_connections[i // 2]
            x = torch.cat([skip, x], dim=1)
            x = self.ups[i+1](x)
        
        return self.final(x)
```

---

#### NAFNet（2022 SOTA，必须复现）

**核心设计思想**：
1. 去掉 GELU 激活函数，用 SimpleGate 替代
2. 用 LayerNorm 替代 BatchNorm
3. Channel Attention 用简化版

```python
class SimpleGate(nn.Module):
    """NAFNet 的核心创新：用乘法门控替代非线性激活"""
    def forward(self, x):
        x1, x2 = x.chunk(2, dim=1)
        return x1 * x2  # 一半特征作为门，控制另一半

class NAFBlock(nn.Module):
    def __init__(self, channels, DW_Expand=2, FFN_Expand=2):
        super().__init__()
        dw_ch = channels * DW_Expand
        ffn_ch = channels * FFN_Expand
        
        self.norm1 = nn.LayerNorm(channels)
        self.norm2 = nn.LayerNorm(channels)
        
        # Self-Attention 部分（简化版 Channel Attention）
        self.conv1 = nn.Conv2d(channels, dw_ch, 1)
        self.conv2 = nn.Conv2d(dw_ch//2, channels, 1)
        self.dw_conv = nn.Conv2d(dw_ch//2, dw_ch//2, 3, padding=1, groups=dw_ch//2)
        self.gate = SimpleGate()
        self.sca = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(channels//2, channels//2, 1),
        )
        
        # FFN 部分
        self.ffn_conv1 = nn.Conv2d(channels, ffn_ch, 1)
        self.ffn_conv2 = nn.Conv2d(ffn_ch//2, channels, 1)
        self.ffn_gate = SimpleGate()
        
    def forward(self, inp):
        x = inp
        # LayerNorm（需要转置，因为 PyTorch LayerNorm 作用在最后一维）
        B, C, H, W = x.shape
        x = self.norm1(x.permute(0,2,3,1)).permute(0,3,1,2)
        
        x = self.conv1(x)
        x, gate = x.chunk(2, dim=1)
        x = self.dw_conv(x)
        x = self.gate(torch.cat([x, gate], dim=1))  # SimpleGate
        x = x * self.sca(x)
        x = self.conv2(x)
        y = inp + x
        
        # FFN
        x = self.norm2(y.permute(0,2,3,1)).permute(0,3,1,2)
        x = self.ffn_conv1(x)
        x = self.ffn_gate(x)
        x = self.ffn_conv2(x)
        return y + x
```

---

#### Restormer（Transformer 在图像恢复中的里程碑）

**核心创新**：
- Multi-Dconv Head Transposed Attention（MDTA）：在 Channel 维度做 Attention，避免空间复杂度 O(H²W²)
- Gated-Dconv Feed-Forward Network（GDFN）

**面试要能解释**：
- 为什么在 Channel 维度做 Attention？（计算复杂度从 O(H²W²) 降到 O(C²HW)，高分辨率图像必须这样做）
- Transposed Attention 的物理含义是什么？（每个通道描述图像的一种"特征模式"，通道间的相关性等价于捕捉全局上下文）

---

### 2.3 必读论文精选（按重要性排序）

详见[第六章：必读论文精选列表](#六必读论文精选列表)

---

### 2.4 阶段二：里程碑项目

> **项目名称**：AI 驱动的暗光 RAW 降噪 + 增强系统

**步骤**：
1. 下载 SID 数据集（Sony 和 Fuji 子集），理解短曝光/长曝光配对结构
2. 克隆 BasicSR 框架，阅读 NAFNet 网络实现
3. 实现自定义 Dataset 类，支持 Bayer RAW 的 4 通道打包
4. 修改 Loss 函数：L1 + 0.05 × (1 - SSIM)
5. 训练 50 epoch，用 TensorBoard 监控 loss 曲线
6. 在验证集上计算 PSNR/SSIM，与论文对比
7. 可视化失败案例（PSNR 最低的图像），分析原因

**验收标准**：训练出的模型在 SID Sony 测试集上 PSNR > 28 dB（论文约 30 dB，初次复现能做到 28 dB 说明理解正确）

---

## 阶段三：工程利刃 — C++ 高性能图像处理（4-5 周）

> **目标**：把 Python 算法翻译为能在端侧设备上以高帧率运行的 C++ 代码
>
> **核心问题**：招聘方会直接让你手写 C++ 图像处理代码，考察内存管理和性能意识

---

### 3.1 图像内存模型与 Cache 优化

#### Cache 基础知识

```
CPU Cache 层级（典型值）：
  L1 Cache: ~32 KB, 延迟 ~4 cycles
  L2 Cache: ~256 KB, 延迟 ~12 cycles
  L3 Cache: ~8 MB, 延迟 ~40 cycles
  RAM: 无限制, 延迟 ~200 cycles

Cache Line 大小: 64 bytes
一个 Cache Line 可以存储: 16 个 float32 像素值 或 64 个 uint8 像素值
```

#### 图像遍历：行优先 vs 列优先

```cpp
#include <chrono>
#include <vector>

// 正确：行优先遍历（Cache 友好）
// 因为图像数据按行存储：row0[0],row0[1],...,row1[0],row1[1],...
void process_row_major(float* img, int H, int W) {
    for (int y = 0; y < H; y++) {          // 外层：行
        for (int x = 0; x < W; x++) {      // 内层：列
            img[y * W + x] = img[y * W + x] * 1.1f;  // 连续内存访问 ✓
        }
    }
}

// 错误：列优先遍历（Cache 不友好，速度慢 5-10 倍）
void process_col_major(float* img, int H, int W) {
    for (int x = 0; x < W; x++) {          // 外层：列
        for (int y = 0; y < H; y++) {      // 内层：行
            img[y * W + x] = img[y * W + x] * 1.1f;  // 跨行跳跃 ✗
        }
    }
}

// 测量两者速度差异
void benchmark() {
    int H = 4000, W = 6000;
    std::vector<float> img(H * W, 0.5f);
    
    auto t1 = std::chrono::high_resolution_clock::now();
    process_row_major(img.data(), H, W);
    auto t2 = std::chrono::high_resolution_clock::now();
    process_col_major(img.data(), H, W);
    auto t3 = std::chrono::high_resolution_clock::now();
    
    auto dt_row = std::chrono::duration_cast<std::chrono::milliseconds>(t2-t1).count();
    auto dt_col = std::chrono::duration_cast<std::chrono::milliseconds>(t3-t2).count();
    
    printf("Row-major: %ld ms, Col-major: %ld ms, Speedup: %.2fx\n",
           dt_row, dt_col, (float)dt_col/dt_row);
}
```

#### Tile-based 图像处理（大图处理的标准方式）

```cpp
// 将 4K 图像分成小块，确保每块的工作集能装入 L2 Cache
void process_tiled(float* img, int H, int W, int tile_h=64, int tile_w=64) {
    for (int ty = 0; ty < H; ty += tile_h) {
        for (int tx = 0; tx < W; tx += tile_w) {
            int end_y = std::min(ty + tile_h, H);
            int end_x = std::min(tx + tile_w, W);
            
            // 处理当前 Tile 内的像素
            for (int y = ty; y < end_y; y++) {
                for (int x = tx; x < end_x; x++) {
                    img[y * W + x] = process_pixel(img[y * W + x]);
                }
            }
        }
    }
}
```

---

### 3.2 多线程图像并行处理

```cpp
#include <thread>
#include <vector>

// 方法一：手动线程分块
void parallel_process(float* img, int H, int W) {
    int num_threads = std::thread::hardware_concurrency();
    std::vector<std::thread> threads;
    
    for (int t = 0; t < num_threads; t++) {
        int start_row = t * H / num_threads;
        int end_row = (t + 1) * H / num_threads;
        
        threads.emplace_back([=]() {
            for (int y = start_row; y < end_row; y++) {
                for (int x = 0; x < W; x++) {
                    img[y * W + x] = gamma_correct(img[y * W + x]);
                }
            }
        });
    }
    
    for (auto& t : threads) t.join();
}

// 方法二：OpenMP（推荐，更简洁）
// 编译时加 -fopenmp
#include <omp.h>

void openmp_process(float* img, int H, int W) {
    #pragma omp parallel for schedule(dynamic) num_threads(8)
    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {
            img[y * W + x] = gamma_correct(img[y * W + x]);
        }
    }
}
```

---

### 3.3 SIMD 向量化加速

```cpp
// ARM NEON 示例（移动端/嵌入式平台）
#include <arm_neon.h>

void apply_gain_neon(uint8_t* img, int size, float gain) {
    float32x4_t gain_v = vdupq_n_f32(gain);  // 4个通道同时处理
    
    int i = 0;
    for (; i <= size - 16; i += 16) {
        // 一次加载16个 uint8 值
        uint8x16_t pixels = vld1q_u8(img + i);
        
        // 分成4组，转换为 float 处理
        uint8x8_t low = vget_low_u8(pixels);
        uint16x8_t u16_low = vmovl_u8(low);
        uint32x4_t u32_0 = vmovl_u16(vget_low_u16(u16_low));
        float32x4_t f_0 = vcvtq_f32_u32(u32_0);
        f_0 = vmulq_f32(f_0, gain_v);  // 4像素同时乘以增益
        
        // 转回 uint8 并存储...
    }
}

// x86 SSE/AVX 示例
#include <immintrin.h>

void apply_gain_avx(float* img, int size, float gain) {
    __m256 gain_v = _mm256_set1_ps(gain);  // 8个 float 同时处理
    
    for (int i = 0; i <= size - 8; i += 8) {
        __m256 pixels = _mm256_loadu_ps(img + i);   // 加载8个float
        pixels = _mm256_mul_ps(pixels, gain_v);      // 8个同时乘
        _mm256_storeu_ps(img + i, pixels);            // 存储
    }
}
```

---

### 3.4 C++ ISP 类设计

```cpp
// CMakeLists.txt
// cmake_minimum_required(VERSION 3.15)
// project(CppISP)
// find_package(OpenCV REQUIRED)
// target_link_libraries(cpp_isp PRIVATE ${OpenCV_LIBS} OpenMP::OpenMP_CXX)

#include <opencv2/opencv.hpp>
#include <omp.h>

class ISPModule {
public:
    virtual cv::Mat process(const cv::Mat& input) = 0;
    virtual std::string name() const = 0;
    virtual ~ISPModule() = default;
};

class BlackLevelCorrection : public ISPModule {
    float black_level_, white_level_;
public:
    BlackLevelCorrection(float black = 64.0f, float white = 4095.0f)
        : black_level_(black), white_level_(white) {}
    
    cv::Mat process(const cv::Mat& raw) override {
        cv::Mat result;
        raw.convertTo(result, CV_32F);
        result = (result - black_level_) / (white_level_ - black_level_);
        cv::threshold(result, result, 0, 0, cv::THRESH_TOZERO);
        cv::threshold(result, result, 1, 1, cv::THRESH_TRUNC);
        return result;
    }
    
    std::string name() const override { return "BLC"; }
};

class ISPPipeline {
    std::vector<std::unique_ptr<ISPModule>> modules_;
public:
    void add_module(std::unique_ptr<ISPModule> mod) {
        modules_.push_back(std::move(mod));
    }
    
    cv::Mat run(const cv::Mat& raw) {
        cv::Mat current = raw.clone();
        for (auto& mod : modules_) {
            auto t1 = std::chrono::high_resolution_clock::now();
            current = mod->process(current);
            auto t2 = std::chrono::high_resolution_clock::now();
            auto ms = std::chrono::duration_cast<std::chrono::microseconds>(t2-t1).count();
            printf("[%s] %.2f ms\n", mod->name().c_str(), ms/1000.0);
        }
        return current;
    }
};
```

---

### 3.5 阶段三：里程碑项目

> **项目名称**：C++ 高性能 ISP 库（开源到 GitHub）

**验收标准**：
- 单张 1080P 图像端到端处理时间 < 50ms（单线程），< 15ms（8线程）
- 代码通过 Valgrind / AddressSanitizer 零错误
- GitHub README 包含：架构设计 + 性能测试报告（各模块耗时）+ 效果对比图

---

## 阶段四：部署闭环 — CUDA 加速与端侧 AI 推理（4-6 周）

> **目标**：完成从 PyTorch 训练到 C++ 端侧实时推理的完整工程链路

---

### 4.1 CUDA 并行计算基础

```cuda
// Hello World 级别：向量加法
__global__ void vector_add(float* A, float* B, float* C, int N) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < N) {
        C[idx] = A[idx] + B[idx];
    }
}

// 图像亮度调整 Kernel
__global__ void brightness_adjust(float* img, float gain, int H, int W) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;  // 列
    int y = blockIdx.y * blockDim.y + threadIdx.y;  // 行
    
    if (x < W && y < H) {
        int idx = y * W + x;
        img[idx] = fminf(img[idx] * gain, 1.0f);
    }
}

// 调用方式
void launch_brightness(float* d_img, float gain, int H, int W) {
    dim3 block(32, 32);  // 每个 Block 1024 个线程（32×32）
    dim3 grid((W + 31) / 32, (H + 31) / 32);  // Grid 大小根据图像尺寸计算
    brightness_adjust<<<grid, block>>>(d_img, gain, H, W);
    cudaDeviceSynchronize();
}
```

#### Shared Memory 优化图像滤波

```cuda
#define BLOCK_SIZE 32
#define RADIUS 1

// 3×3 均值滤波，使用 Shared Memory 优化
__global__ void mean_filter_shared(float* input, float* output, int H, int W) {
    // Shared Memory 大小 = (BLOCK_SIZE + 2*RADIUS) × (BLOCK_SIZE + 2*RADIUS)
    __shared__ float smem[BLOCK_SIZE + 2*RADIUS][BLOCK_SIZE + 2*RADIUS];
    
    int tx = threadIdx.x, ty = threadIdx.y;
    int x = blockIdx.x * BLOCK_SIZE + tx;
    int y = blockIdx.y * BLOCK_SIZE + ty;
    
    // 协作加载数据到 Shared Memory（包括边界 halo）
    int smem_x = tx + RADIUS;
    int smem_y = ty + RADIUS;
    
    if (x < W && y < H)
        smem[smem_y][smem_x] = input[y * W + x];
    
    // 加载边界（每个线程负责加载自己对应的 halo 部分）
    // ...（省略边界处理代码）
    
    __syncthreads();  // 等待所有线程加载完毕
    
    // 从 Shared Memory 计算均值（速度是 Global Memory 的 10-100 倍）
    if (x < W && y < H && x > 0 && y > 0 && x < W-1 && y < H-1) {
        float sum = 0;
        for (int dy = -RADIUS; dy <= RADIUS; dy++)
            for (int dx = -RADIUS; dx <= RADIUS; dx++)
                sum += smem[smem_y + dy][smem_x + dx];
        output[y * W + x] = sum / ((2*RADIUS+1) * (2*RADIUS+1));
    }
}
```

---

### 4.2 TensorRT 模型部署

#### 完整部署流程

```python
# Step 1: PyTorch 模型导出 ONNX
import torch
import torch.onnx

model = NAFNet(...)  # 加载训练好的模型
model.eval()

dummy_input = torch.randn(1, 4, 256, 256)  # Batch=1, Channel=4(RAW), H, W
torch.onnx.export(
    model,
    dummy_input,
    "nafnet.onnx",
    input_names=["raw_input"],
    output_names=["rgb_output"],
    dynamic_axes={"raw_input": {0: "batch", 2: "height", 3: "width"}},
    opset_version=17
)

# Step 2: 验证 ONNX 模型
import onnx
model_onnx = onnx.load("nafnet.onnx")
onnx.checker.check_model(model_onnx)
```

```cpp
// Step 3: C++ TensorRT 推理
#include <NvInfer.h>
#include <cuda_runtime_api.h>

class TRTInference {
    nvinfer1::IRuntime* runtime_;
    nvinfer1::ICudaEngine* engine_;
    nvinfer1::IExecutionContext* context_;
    
    void* d_input_;   // GPU 输入显存
    void* d_output_;  // GPU 输出显存
    
public:
    TRTInference(const std::string& engine_path) {
        // 从文件加载序列化的 TRT 引擎
        std::ifstream file(engine_path, std::ios::binary);
        std::vector<char> engine_data(
            (std::istreambuf_iterator<char>(file)),
            std::istreambuf_iterator<char>()
        );
        
        runtime_ = nvinfer1::createInferRuntime(gLogger);
        engine_ = runtime_->deserializeCudaEngine(engine_data.data(), engine_data.size());
        context_ = engine_->createExecutionContext();
        
        // 分配 GPU 显存
        cudaMalloc(&d_input_,  1 * 4 * 256 * 256 * sizeof(float));
        cudaMalloc(&d_output_, 1 * 3 * 512 * 512 * sizeof(float));
    }
    
    void infer(const float* h_input, float* h_output,
               int batch, int C_in, int H, int W) {
        // CPU → GPU 数据传输
        cudaMemcpy(d_input_, h_input,
                   batch * C_in * H * W * sizeof(float),
                   cudaMemcpyHostToDevice);
        
        // 执行推理
        void* bindings[] = {d_input_, d_output_};
        context_->executeV2(bindings);
        
        // GPU → CPU 数据传输
        int out_H = H * 2, out_W = W * 2;  // 如果模型有上采样
        cudaMemcpy(h_output, d_output_,
                   batch * 3 * out_H * out_W * sizeof(float),
                   cudaMemcpyDeviceToHost);
    }
};
```

---

### 4.3 移动端 NCNN 部署

```bash
# 模型转换流程
pip install onnx onnxsim

# 1. 简化 ONNX 模型（移除冗余节点）
python -m onnxsim nafnet.onnx nafnet_simplified.onnx

# 2. 转换为 NCNN 格式
./onnx2ncnn nafnet_simplified.onnx nafnet.param nafnet.bin

# 3. 量化（INT8）
./ncnnoptimize nafnet.param nafnet.bin nafnet_int8.param nafnet_int8.bin 65536
```

```cpp
// NCNN C++ 推理
#include "net.h"

ncnn::Net net;
net.opt.use_vulkan_compute = true;  // 使用 GPU 加速（如果支持）
net.load_param("nafnet.param");
net.load_model("nafnet.bin");

ncnn::Mat input = ncnn::Mat(W, H, 4);  // 4通道RAW输入
// 填充输入数据...

ncnn::Extractor ex = net.create_extractor();
ex.input("raw_input", input);

ncnn::Mat output;
ex.extract("rgb_output", output);
```

---

### 4.4 阶段四：终极里程碑项目

> **项目名称**：端到端 AI-ISP 推理系统

**完整架构**：
```
RAW 图像输入
    │
    ▼
C++ 传统 ISP 前端（BLC + DPC + LSC）      ← 阶段三成果
    │
    ▼
AI 推理模块（TensorRT / NCNN）             ← 阶段二+四成果
  - Demosaic + Denoising (联合)
  - Low-light Enhancement
    │
    ▼
C++ 传统 ISP 后端（色调映射 + Gamma）      ← 阶段三成果
    │
    ▼
RGB 图像输出（JPEG/PNG）
```

**GitHub README 必须包含**：
- 系统架构图
- 性能测试表（延迟 / PSNR / 内存占用）
- 效果对比图（暗光场景 Before / After）
- 构建和运行说明

---

## 五、10 个月执行路线

> **执行原则**：每个月只围绕一个主目标推进，所有学习都必须落到代码、图表、报告或可复述的面试材料上。你已有 ISP 工程经验，所以不要把时间花在泛泛看课上，而要把过去做过的“功能对齐、定点化、四通道改造、Pipeline 适配”升级成“算法解释、画质评价、调参决策、工程落地”能力。
>
> **每周固定节奏**：每周 5 天学习/编码，每天 2 小时理论 + 2～3 小时实践；第 6 天整理实验记录和 README；第 7 天复盘本周掌握情况。每个月至少沉淀 1 篇技术笔记、1 个可运行 Demo、1 组 Before/After 图和 1 张指标表。

### Month 1：RAW / Sensor / ISP 数据流补基础

**目标**：补齐你过去“会对齐数值但不完全知道数值物理含义”的短板，建立 RAW 域直觉。

**学习内容**：
- Sensor 基础：光电转换、满阱容量、量子效率、黑电平、白电平、ADC、bit depth、ISO/gain。
- Bayer / Quad Bayer / RCCB 等 CFA 基本概念，理解为什么 RAW 不是普通灰度图。
- 噪声来源：shot noise、read noise、dark current、fixed pattern noise。
- RAW 数据统计：四通道均值、方差、直方图、饱和比例、黑电平附近像素比例。

**具体动作**：
1. 找 5～10 张真实 RAW / DNG / ARW 样张，优先选择不同 ISO、不同亮度、不同色温场景。
2. 用 Python + rawpy 读取 RAW，输出 R/Gr/Gb/B 四通道统计。
3. 画出每个通道的 histogram、mean-variance、饱和像素 mask。
4. 写一篇笔记：《一张 RAW 图里的数值到底代表什么》。

**掌握标准**：
- 能解释 RAW 域、线性光、sRGB、Gamma 编码的区别。
- 能说明 black level / white level / gain / bit depth 对后续 ISP 的影响。
- 面试时能用自己的话讲清：为什么 AI-ISP 不能只把 sRGB 图像当普通 RGB 图训练。
- 能独立写脚本分析一张 RAW 的四通道统计，并根据统计判断是否过曝、偏暗、黑电平异常。

### Month 2：传统 ISP 主链路实现与模块解释

**目标**：从“维护 Pipeline”升级到“能解释 Pipeline 每个模块为什么存在”。

**学习内容**：
- BLC、DPC、LSC、Demosaic、AWB、CCM、Gamma / Tone Mapping 的输入输出与顺序关系。
- Demosaic 从 bilinear 到 AHD 的思想，不要求一开始实现复杂算法，但要能解释边缘伪彩来源。
- AWB 的灰度世界、白点假设、色温估计基本思路。
- CCM 与色卡标定，理解线性 RGB、XYZ、Lab、DeltaE。

**具体动作**：
1. 实现 Python Soft-ISP：BLC → DPC → LSC → Demosaic → AWB → CCM → Gamma。
2. 每个模块保存中间图、统计信息、直方图。
3. 对比 rawpy / LibRaw / Lightroom 输出，记录差异。
4. 为每个模块写 README：算法目的、公式、参数、失败场景、调参影响。

**掌握标准**：
- 能画出完整 ISP Pipeline 数据流，并说明每一步处理的数据域。
- 能解释某个模块放错顺序会造成什么问题，例如先 Gamma 再 CCM、先 Demosaic 再 BLC 的风险。
- 能把一张 RAW 输出成基本正常的 RGB 图，不追求商业画质，但不能明显偏色、全黑、全白或通道错乱。
- 能回答国内 ISP 岗常见问题：BLC 值从哪里来、LSC 如何标定、AWB 何时失效、Demosaic 为什么会有伪彩。

### Month 3：图像质量评价与调参方法

**目标**：补齐算法岗最重要的“画质语言”。你过去主要做输出一致性，现在要学会判断输出好不好、为什么不好。

**学习内容**：
- 客观指标：PSNR、SSIM、MS-SSIM、LPIPS、DeltaE、SNR、MTF。
- 主观问题：噪声、过锐、过平滑、伪彩、偏色、halo、banding、暗部脏、肤色异常。
- ROI 评价：暗部、边缘、高光、肤色、纯色块、纹理区域分别看什么。
- A/B 测试规范：同输入、同曝光、同 ROI、同显示条件、同统计口径。

**具体动作**：
1. 建一个 IQA notebook，支持 PSNR / SSIM / LPIPS / DeltaE 计算。
2. 从 Month 2 的 Soft-ISP 输出中选 20 个 ROI，建立问题标签。
3. 对 AWB、CCM、Gamma、锐化/降噪参数做小范围 sweep，观察指标与主观画质的冲突。
4. 写一篇笔记：《为什么 PSNR 高不代表图像好看》。

**掌握标准**：
- 能根据图像现象判断可能是哪个模块导致的问题。
- 能解释 PSNR、SSIM、LPIPS、DeltaE 各自适合评价什么、不适合评价什么。
- 能做一份包含图像、ROI、指标、结论的画质对比报告。
- 面试时能讲清“画质调参不是只看一致性，也不是只看单一指标”。

### Month 4：3A 与 HDR / WDR

**目标**：补国内 ISP 岗高频要求。结合你做过交替行、交替帧、混合模式 Pipeline 的经验，把框架适配升级成算法理解。

**学习内容**：
- AE：亮度统计、metering、曝光目标、曝光收敛、防震荡、曝光补偿。
- AWB 深入：色温、光源估计、肤色保护、混合光、异常区域剔除。
- AF 了解：contrast AF、phase AF 基本概念，不需要深入到马达控制。
- HDR / WDR：多曝光融合、交替行、交替帧、motion artifact、ghost、tone mapping。

**具体动作**：
1. 写一个简化 AE 控制模拟器：输入当前亮度统计，输出曝光调整量。
2. 写一个 AWB 区域筛选实验：比较全图统计、灰度世界、白点法、剔除饱和/暗区后的结果。
3. 针对交替行 / 交替帧 HDR，画出数据路由图，标注每一路曝光、缓存、同步、融合位置。
4. 整理你过去做过的 Pipeline 多模式适配经验，重写成“算法数据流 + 工程风险 + 验证方法”。

**掌握标准**：
- 能解释 AE/AWB/AF 各自解决什么问题，以及 3A 为什么是控制闭环而不是单帧函数。
- 能说明 HDR 交替行和交替帧在数据解析、运动伪影、缓存、时序上的差异。
- 能把你过去的 HDR / 混合模式 Pipeline 工作讲成算法相关项目，而不是单纯“改代码适配”。
- 能回答“低光、逆光、混合光、运动场景下 ISP 哪些模块最容易出问题”。

### Month 5：传统降噪、锐化与图像增强

**目标**：进入国内 ISP 算法岗的核心模块：降噪、锐化、HDR 后处理、细节增强。

**学习内容**：
- RAW 域噪声模型：Poisson-Gaussian，ISO/gain 与噪声强度关系。
- 传统降噪：mean、median、bilateral、guided filter、NLM 思想。
- 锐化：unsharp mask、边缘增强、halo 控制、噪声放大问题。
- 低光增强：亮度提升、对比度增强、暗部噪声、色彩漂移。
- 降噪与锐化的 tradeoff：保纹理、去噪点、防伪影。

**具体动作**：
1. 实现传统 denoise + sharpen demo，支持参数 sweep。
2. 在不同 ISO 或合成噪声强度下，观察降噪参数对细节和噪声的影响。
3. 做一组“降噪强度 vs 锐化强度”的二维实验表。
4. 写一篇笔记：《降噪、锐化、纹理保留之间为什么互相冲突》。

**掌握标准**：
- 能解释为什么低光图像不能简单提亮，为什么锐化会放大噪声。
- 能看图判断是“噪声残留”“过平滑”“过锐”“halo”“假纹理”中的哪类问题。
- 能写出传统降噪/锐化的可运行代码，并能用指标和 ROI 图说明参数影响。
- 能把传统模块和后续 AI 降噪联系起来：AI 模型到底在替代或增强哪一部分。

### Month 6：PyTorch 图像恢复基础

**目标**：建立 AI-ISP 的训练能力，但先做稳定 baseline，不追求大而新的模型。

**学习内容**：
- PyTorch Dataset、Dataloader、训练循环、checkpoint、TensorBoard。
- UNet、DnCNN、NAFNet 的基本结构。
- Loss：L1、L2、SSIM、Perceptual loss。
- 数据集：SIDD、SID、LOL、LSRW，理解各自输入输出域。
- RAW pack：RGGB → 4 channel，理解为什么很多 RAW 网络这样输入。

**具体动作**：
1. 先用 RGB 降噪数据训练一个 DnCNN / UNet baseline。
2. 再做 RAW pack 输入实验，至少能跑通一个小规模 RAW 增强或降噪训练。
3. 每次训练记录配置、数据、loss 曲线、指标和可视化结果。
4. 整理训练失败案例：过拟合、输出偏色、过平滑、棋盘格、边缘伪影。

**掌握标准**：
- 能从零写出一个可训练、可验证、可保存模型的 PyTorch 工程。
- 能解释 UNet 跳连、残差学习、NAFNet SimpleGate 的基本作用。
- 能说明 RAW 域训练和 sRGB 域训练的差异。
- 能用 PSNR / SSIM / LPIPS 和可视化结果评价模型，不只看 loss 是否下降。

### Month 7：AI-ISP 数据建模与论文复现

**目标**：从“会训练模型”升级到“知道数据怎么来、退化怎么建模、结果怎么解释”。

**学习内容**：
- SID：低光 RAW → RGB 的端到端思路。
- NAFNet：图像恢复强 baseline，重点理解简化设计和消融。
- CycleISP：RAW/sRGB 双向退化建模，理解真实噪声合成。
- 合成噪声 vs 真实噪声，配对数据 vs 非配对数据。
- 训练域、输出域、评价域要一致。

**具体动作**：
1. 精读 SID、NAFNet、CycleISP，每篇写一页“问题、方法、数据、Loss、指标、局限”。
2. 复现一个轻量版 SID 或 NAFNet，不要求追到论文 SOTA，但要跑通完整流程。
3. 做一次小消融：L1 vs L1+SSIM、真实噪声 vs 合成噪声、RAW 输入 vs RGB 输入。
4. 可视化 PSNR 最低的 10 张图，逐张分析失败原因。

**掌握标准**：
- 能讲清一篇 AI-ISP / 图像恢复论文，不只背网络结构。
- 能解释数据退化建模为什么比盲目换网络更重要。
- 能做至少一个消融实验，并从实验中得出明确结论。
- 面试时能回答“你这个 AI 模型解决了传统 ISP 的什么痛点，代价是什么”。

### Month 8：C++ 算法工程化、定点化与四通道强化

**目标**：把你的已有优势打磨成可展示的“工程深度”。这是你区别于纯算法同学的重要竞争力。

**学习内容**：
- 定点化：scale、rounding、saturation、overflow、bit width、误差传播。
- Python / C++ bit-exact 对齐方法。
- 四通道数据布局：planar、interleaved、packed RGGB、cache locality。
- 4K 大图处理：tile、line buffer、padding、边界同步。
- OpenMP、SIMD、cache profiling。

**具体动作**：
1. 从 Soft-ISP 里选 1～2 个模块迁移到 C++，优先选 BLC、LSC、Gamma、简单滤波。
2. 做 float → fixed 的定点化实验，记录每一步误差来源。
3. 对比单通道与四通道实现，写清内存布局、边界处理、状态隔离。
4. 做性能测试：1080P / 4K，单线程 / 多线程，优化前 / 优化后。

**掌握标准**：
- 能解释定点化中 scale、rounding、saturation 的选择依据。
- 能定位 Python/C++ 输出不一致的常见原因：数据类型、舍入、边界、padding、溢出、遍历顺序。
- 能拿出一份性能报告，而不是只说“做过优化”。
- 能把你过去的四通道重构经历讲成：数据流改造、状态隔离、边界一致性、跨版本验证。

### Month 9：模型部署与端侧推理闭环

**目标**：补国内 AI-ISP 岗常见的落地要求。重点不是写很复杂的 CUDA，而是完成可解释的部署链路。

**学习内容**：
- PyTorch → ONNX 导出。
- ONNX Runtime / TensorRT / NCNN / MNN 选择 1～2 个重点实践。
- FP32、FP16、INT8，理解 calibration 数据选择。
- 模型压缩：剪枝、轻量化结构、输入分辨率权衡。
- 部署评价：延迟、显存、吞吐、画质损失、平台限制。

**具体动作**：
1. 将 Month 6/7 的轻量模型导出 ONNX。
2. 用 ONNX Runtime 或 TensorRT 跑通 C++ 推理；如果目标移动端，补 NCNN / MNN。
3. 做 FP32 / FP16 / INT8 对比，记录 PSNR / SSIM / latency / memory。
4. 写一份部署报告：《量化后画质损失来自哪里，是否可接受》。

**掌握标准**：
- 能完整讲出 PyTorch 模型到 C++ 推理的链路。
- 能解释 calibration 数据为什么必须覆盖真实场景。
- 能说明部署时如何在画质、速度、内存、功耗之间取舍。
- 能回答“为什么训练指标好，部署后效果变差”。

### Month 10：作品集、简历与面试表达

**目标**：把前 9 个月的学习成果包装成国内 ISP / AI-ISP 算法岗能看懂的项目。

**最终作品集结构**：
1. **Soft-ISP Pipeline**：RAW 读取、BLC、DPC、LSC、Demosaic、AWB、CCM、Gamma、IQA。
2. **AI RAW/RGB 降噪或暗光增强**：数据集、网络、Loss、训练曲线、指标、失败案例、消融。
3. **C++ / 定点化 / 部署闭环**：Python-C++ 对齐、四通道/4K 数据流、性能报告、ONNX/TensorRT/NCNN/ONNX Runtime 推理。

**面试表达模板**：
- 背景：我不是纯零基础转行，我做过 ISP Pipeline 工程维护、Python/C++ 对齐、定点化、四通道重构、多模式 Pipeline 和测试验证。
- 短板补齐：过去偏工程迁移，后来系统补了 RAW 物理、传统 ISP、IQ 评价、3A/HDR、降噪锐化和 AI-ISP 数据建模。
- 项目价值：我能从输入数据、算法原理、画质指标、工程实现和部署性能五个层面解释一个模块。
- 差异化：我既能读论文和训练模型，也能处理定点化、四通道数据流、C++ 对齐和端侧部署问题。

**掌握标准**：
- 简历上至少有 2 个能展开 20 分钟讲的项目。
- 每个项目都能讲清：问题、数据、方法、指标、失败案例、改进方向。
- 能手写或伪代码说明 3～5 个核心模块：BLC、AWB、Demosaic、CCM、降噪、定点化、ONNX 推理任选。
- 能对自己的真实工作经历做算法化表达，不再只说“我做了功能模块改造”。

### 每月复盘检查表

- 这个月是否有可运行代码，而不是只看课程？
- 是否有图像 Before/After 和指标表？
- 是否写清楚了失败案例，而不是只展示好图？
- 是否能把本月内容用 5 分钟讲给面试官？
- 是否把新学内容和已有工作经历连接起来？
- 是否明确下个月要补的最大短板？

---

## 六、必读论文精选列表

### 🔴 必须精读复现（P0 级）

| 论文名 | 会议/年份 | 核心贡献 | 阅读重点 | 代码地址 |
|---|---|---|---|---|
| **Learning to See in the Dark (SID)** | CVPR 2018 | 端到端暗光 RAW→RGB，4通道打包技巧 | RAW 数据打包方式，端到端思路 | [github.com/cchen156/SID](https://github.com/cchen156/SID) |
| **NAFNet: Simple Baselines for Image Restoration** | ECCV 2022 | 极简设计、SOTA 降噪超分，SimpleGate | 网络简化哲学，各组件消融分析 | [github.com/megvii-research/NAFNet](https://github.com/megvii-research/NAFNet) |
| **Restormer: Efficient Transformer for High-Res Image Restoration** | CVPR 2022 | Transformer 在高分辨率图像恢复，MDTA | Transposed Attention 设计原理 | [github.com/swz30/Restormer](https://github.com/swz30/Restormer) |
| **CycleISP: Real Image Restoration via Improved Data Synthesis** | CVPR 2020 | 真实噪声合成，RAW↔sRGB 循环转换 | 如何合成更真实的 Sensor 噪声 | [github.com/swz30/CycleISP](https://github.com/swz30/CycleISP) |

### 🟡 重要阅读（P1 级）

| 论文名 | 会议/年份 | 核心贡献 |
|---|---|---|
| **PMRID: Pyramid Multi-scale Residual Image Denoiser** | 2020 | 专为移动端设计的轻量级降噪 |
| **CBDNet: Toward Convolutional Blind Denoising** | CVPR 2019 | 非盲降噪，噪声估计子网络 |
| **DnCNN: Beyond Gaussian Denoiser** | TIP 2017 | 深度残差降噪的奠基性论文 |
| **DBSN: Noise2Void** | CVPR 2019 | 无需配对数据的自监督降噪 |
| **Real-ESRGAN: Training Real-World Blind Super-Resolution** | ICCV 2021 | 真实场景超分，复杂退化建模 |
| **Uformer: A General U-Shaped Transformer** | CVPR 2022 | UNet 与 Transformer 的结合 |
| **AWNet: Attentive Wavelet Network for Image ISP** | ECCV 2020 | 端到端 ISP，小波域处理 |
| **PyNet: Processing RAW Images with Portable Networks** | CVPR 2020 | 手机端轻量 ISP 网络 |
| **MPRNet: Multi-Stage Progressive Image Restoration** | CVPR 2021 | 多阶段渐进恢复，高质量输出 |

### 🟢 了解即可（背景知识）

| 论文名 | 会议/年份 | 核心贡献 |
|---|---|---|
| A Practical Model for the Sensitivity of a Camera | Hasinoff 2014 | Sensor 噪声物理模型 |
| Noise Flow: Noise Modeling with Conditional Normalizing Flows | ICCV 2019 | 高级噪声建模 |
| Practical ISP: A Camera Pipeline | Karaimer & Brown, CVPR 2016 | 标准 ISP Pipeline 综述 |
| Handheld Multi-frame Super-resolution (Google) | SIGGRAPH 2019 | 多帧超分原理，Google HDR+ |

---

## 七、必看开源项目清单

### ISP Pipeline 类

| 项目名 | 地址 | 语言 | 用途 |
|---|---|---|---|
| **OpenISP** | github.com/cruxopen/openISP | Python/C++ | 模块化传统 ISP，最佳学习教材 |
| **LibRaw** | libraw.org | C++ | 工业级 RAW 解码库，rawpy 的底层 |
| **rawpy** | github.com/letmaik/rawpy | Python | Python RAW 图像读取工具 |
| **libcamera** | libcamera.org | C++ | Linux 摄像头标准库，3A 算法参考 |
| **ISP-toolbox** | github.com/Qiububu/ISP-toolbox | Python | 常用 ISP 模块 Python 实现合集 |
| **IMAX-ISP** | github.com/JasonCai0529/IMAX-ISP | C++ | C++ 实时 ISP 框架 |

### AI-ISP 训练框架

| 项目名 | 地址 | 语言 | 用途 |
|---|---|---|---|
| **BasicSR** | github.com/XPixelGroup/BasicSR | Python | 最广泛使用的图像恢复训练框架 |
| **MMEditing** | github.com/open-mmlab/mmediting | Python | OpenMMLab 的图像编辑套件 |
| **IQA-PyTorch** | github.com/chaofengc/IQA-PyTorch | Python | 图像质量评价指标库（PSNR/SSIM/LPIPS等） |
| **pytorch-msssim** | github.com/VainF/pytorch-msssim | Python | SSIM/MS-SSIM Loss 实现 |

### 推理部署框架

| 项目名 | 地址 | 语言 | 用途 |
|---|---|---|---|
| **NCNN** | github.com/Tencent/ncnn | C++ | 移动端轻量推理，最佳移动端选择 |
| **MNN** | github.com/alibaba/MNN | C++ | 阿里移动端推理，支持多硬件后端 |
| **TensorRT** | developer.nvidia.com/tensorrt | C++ | Nvidia GPU 高性能推理 |
| **ONNX Runtime** | github.com/microsoft/onnxruntime | C++ | 跨平台推理框架 |
| **OpenVINO** | github.com/openvinotoolkit/openvino | C++ | Intel 硬件优化推理 |

### 数据集

| 数据集名 | 地址 | 用途 |
|---|---|---|
| **SIDD** | sidd-benchmark.s3.amazonaws.com | 真实 Sensor 噪声降噪基准（标准） |
| **DND** | noise.visinf.tu-darmstadt.de | 无参考降噪评测 |
| **SID** | cchen156.github.io/SID.html | 暗光 RAW→RGB 端到端 |
| **MIT-Adobe FiveK** | data.csail.mit.edu/graphics/fivek | 5 位专家修图 RAW 数据集 |
| **LOL Dataset** | daooshee.github.io/BMVC2018website | 低光照增强 |
| **LSRW** | github.com/JianghaiSCU/LSRW | 真实暗光配对数据集 |

---

## 八、公开课推荐

### 图像处理基础

| 课程名 | 机构 | 平台 | 语言 | 重点 |
|---|---|---|---|---|
| **Computational Photography** | Georgia Tech | Udacity | 英语 | RAW 处理、HDR、图像形成 |
| **CS194-26 Computational Photography** | UC Berkeley | 官网 | 英语 | 作业质量极高，含 RAW 处理 |
| **EE367: Computational Imaging** | Stanford | 官网 | 英语 | 感知成像系统深度课程 |
| **Image Signal Processing Tutorial** | - | YouTube | 英语 | 大量 ISP 实战讲解 |
| **大话成像** | 已购 | - | 中文 | 最适合入门的中文 ISP 课程 |

### 深度学习基础

| 课程名 | 机构 | 平台 | 语言 | 重点 |
|---|---|---|---|---|
| **CS231n: CNN for Visual Recognition** | Stanford | 官网/YouTube | 英语 | 计算机视觉深度学习圣经 |
| **动手学深度学习（D2L）** | 李沐 | d2l.ai | 中文/英语 | 最好的中文 DL 课程，有代码 |
| **PyTorch 官方 Tutorial** | Meta | pytorch.org | 英语 | 官方文档，边学边查 |
| **Fast.ai Practical Deep Learning** | fast.ai | fast.ai | 英语 | 自顶向下，快速上手 |

### 高性能计算

| 课程名 | 机构 | 平台 | 语言 | 重点 |
|---|---|---|---|---|
| **CUDA Programming Course** | Nvidia | developer.nvidia.com | 英语 | 官方 CUDA 入门课程 |
| **CS149: Parallel Computing** | Stanford | 官网 | 英语 | 并行计算系统性课程 |
| **15-418 Parallel Computer Architecture** | CMU | 官网 | 英语 | Cache/SIMD/GPU 深度理解 |
| **GAMES103 基于物理的计算机动画** | - | B站 | 中文 | 部分内容涉及 GPU 计算 |

---

## 九、面试高频考点与答题框架

> **社招 AI-ISP 算法工程师面试通常分三轮：技术一（ISP理论）→ 技术二（AI算法+项目）→ 系统设计**

---

### 9.1 ISP 理论考点

#### Q1：请解释 Demosaicing 的原理，以及为什么需要这个步骤？

**答题框架**：

1. **物理背景**：相机 Sensor 上的 Bayer 阵列，每个像素只采样 R/G/B 中的一种颜色，原始 RAW 图像实际上是单色图（每个位置只有一个颜色值）
2. **问题定义**：要恢复完整的 RGB 图像，需要从每个像素的邻域插值出缺失的两个颜色分量
3. **算法分级**：
   - 双线性插值：取同色邻域均值，简单但有边缘伪彩（Zipper 效应）
   - AHD（Adaptive Homogeneity-Directed）：在水平/垂直两个方向分别插值，用同质度指标选最优方向
   - LMMSE：利用图像统计先验的最小均方误差估计
   - AI-based：用 CNN 直接从 RAW 学习插值策略，可联合去噪
4. **工程取舍**：双线性用于低算力设备，AHD 是传统 ISP 主流，AI 方案用于追求极限画质的旗舰机

---

#### Q2：Sensor 噪声是怎么产生的？训练数据中如何模拟真实噪声？

**答题框架**：

1. **噪声来源**：
   - 散粒噪声（Shot Noise）：光子到达的量子随机性，服从泊松分布，与信号成正比
   - 读出噪声（Read Noise）：ADC 和放大器引入，服从高斯分布，与信号无关
   - 暗电流（Dark Current）：半导体漏电，随温度和时间变化
2. **数学模型**：Poisson-Gaussian 混合：`y ≈ x + N(0, k·x + σ²_read)`
3. **噪声标定**：拍摄不同曝光的平场帧，统计 mean-variance 线性关系，斜率=k，截距=σ²_read
4. **合成代码**：先用 Poisson 模拟散粒噪声，再叠加高斯模拟读出噪声
5. **进阶**：真实 ISP 处理（BLC/LSC/CCM）会改变噪声分布，需要在 ISP 前的 RAW 域合成噪声

---

#### Q3：AWB 算法的原理和局限性？

**答题框架**：

| 方法 | 原理 | 优点 | 局限 |
|---|---|---|---|
| 灰度世界 | 场景平均色为灰色 | 简单，稳定 | 饱和色场景失效 |
| 白斑点 | 最亮区域为白色 | 能处理高光 | 高光噪声/镜面反射干扰 |
| Gamut Map | 统计学方法，色温估计 | 准确，工程实用 | 需要标定 |
| 深度学习 | CNN 直接预测 gain | 泛化能力强 | 需要大量标注数据 |

---

#### Q4：LSC（镜头暗角校正）是如何标定的？

**答题框架**：

1. **暗角来源**：镜头边缘透光率遵循 cos⁴θ 定律，中心亮边缘暗，且存在颜色偏移
2. **标定方法**：
   - 积分球（Integrating Sphere）：提供完美均匀的各向同性光源
   - 均匀白板：在严格受控照明环境下拍摄均匀平场
3. **数据处理**：计算从图像中心到边缘的亮度衰减曲线，对 R/Gr/Gb/B 四通道分别计算
4. **应用方式**：生成网格增益图（Mesh LUT），在 ISP 中对每个像素乘以对应增益
5. **工程细节**：不同焦距/光圈组合需要不同的 LSC 表，通常存储在 OTP 或配置文件中

---

### 9.2 AI 算法考点

#### Q5：UNet 的跳跃连接为什么在图像恢复中比 ResNet 的残差连接更有效？

**答题框架**：

1. **ResNet 残差连接**：`Add`（相加），两路特征维度相同才能相加
2. **UNet 跳跃连接**：`Concat`（拼接），保留两路特征的独立性
3. **关键优势**：
   - UNet 编码器下采样过程中逐渐丢失空间细节（高频纹理）
   - 解码器单靠瓶颈层的全局语义特征无法恢复精确纹理
   - 跳跃连接把编码器每层的高分辨率特征"直接搬运"给解码器
4. **物理直觉**：对于降噪任务，网络需要区分"真实高频纹理"和"噪声"。跳跃连接保留了空间高频信息，让解码器做"选择"而不是"重建"

---

#### Q6：NAFNet 为什么能达到 SOTA 性能，却比之前的方法更简单？

**答题框架**：

1. **消融分析**：作者系统地移除了 CBAM、GELU 等组件，发现每个单独模块的贡献有限
2. **SimpleGate 的洞见**：GELU 的门控效果可以用 Channel Split + Multiply 完全复现，且计算量更小
3. **LayerNorm vs BatchNorm**：BN 在小 batch 训练图像时统计不稳定，LN 更适合图像恢复
4. **设计哲学**：追求"够用的非线性"而非"最强的非线性"，关键是特征的选择性抑制

---

#### Q7：如何评估一个降噪算法的好坏？如果 PSNR 高但主观效果差怎么办？

**答题框架**：

**客观指标**：
- PSNR：像素级精度，对人眼过平滑不敏感
- SSIM：结构相似性，与感知更相关
- LPIPS：感知损失，用 VGG 特征空间的距离衡量，最接近人眼判断

**主观评测**：
- A/B 盲测（ABX 测试）
- 专业摄影师主观打分（ITU-R BT.500 方法）

**任务导向评估**：
- 如果 ISP 服务于目标检测：看 mAP 是否提升
- 如果 ISP 服务于 OCR：看文字识别准确率

**处理矛盾的方法**：
1. 引入感知 Loss（Perceptual Loss / GAN Loss）替代纯 L2
2. 对比 LPIPS 指标，它比 PSNR 更能反映人眼感知
3. 做目标应用场景的任务评估，用实际业务指标决策

---

### 9.3 C++/性能考点

#### Q8：为什么 Cache 对图像处理性能影响这么大？如何写 Cache 友好的代码？

**答题框架**：

1. **数据量级分析**：
   - 4K RAW 图 = 约 3000×4000×2 bytes = 24MB
   - L1 Cache = 32KB，一次只能放 16K 像素
   - 如果遍历顺序不对，每次读取都是 Cache Miss，延迟上百倍

2. **行优先遍历**：图像按行存储，内层循环走列（X）方向，每步 +3 bytes，Cache 利用率接近 100%

3. **分块（Tile-based）处理**：把图像切成 64×64 的 Tile，每个 Tile 的数据能装入 L2 Cache

4. **验证方法**：用 `perf stat -e cache-misses,cache-references ./your_program` 统计 Cache Miss 率

---

#### Q9：CUDA Kernel 的 Shared Memory 和 Global Memory 如何合理使用？

**答题框架**：

1. **Global Memory**：所有 Thread 访问，延迟 400-800 cycles，带宽受限
2. **Shared Memory**：Block 内共享，延迟 ~5 cycles，容量 48KB/Block

3. **图像滤波使用 Shared Memory 的策略**：
   - 每个 Block 负责一个 Tile（如 32×32）的输出
   - 先协作把 Tile 及其边界（halo）从 Global Memory 搬到 Shared Memory
   - 所有计算从 Shared Memory 读取，节省大量 Global Memory 访问

4. **访问合并（Memory Coalescing）**：同一 Warp（32 个 Thread）的 Global Memory 访问，地址相邻则合并为一次大事务，非相邻则退化为多次小事务（严重影响性能）

---

#### Q10：INT8 量化的原理？为什么需要 Calibration 数据集？

**答题框架**：

1. **量化目标**：用 INT8 替代 FP32，速度提升 2-4×，内存减少 4×

2. **核心问题**：如何确定从 FP32 到 INT8 的 scale 因子？
   - 权重：固定的，可以直接统计最大值确定 scale
   - 激活值：依赖于输入数据，必须用真实数据统计

3. **Calibration 流程**：
   - 用 500-2000 张代表性输入跑 FP32 推理
   - 统计每层激活值的分布（直方图）
   - 用 KL 散度最小化找最优 scale，平衡量化误差和范围覆盖

4. **注意事项**：
   - Calibration 数据必须覆盖真实应用场景，否则某些极端值会被截断
   - 量化后必须在真实评测数据上验证 PSNR 损失（通常<0.5dB 可接受）

---

### 9.4 系统设计题

#### Q11：设计一个能在手机端实时运行的低光照 RAW 增强系统，要求帧率 > 30fps，功耗尽量低

**答题设计思路**：

```
1. 算法选择：
   - 不用大模型（NAFNet 太重），选轻量化变体（MobileISP / TinyISP 量级）
   - 考虑 Sub-pixel Convolution 替代 Deconv（更节省内存）
   
2. 数据流设计：
   RAW(RGGB) → 4ch Pack → 下采样到 1/2 分辨率 → 网络推理 → 上采样 → 后处理
   
3. 硬件部署：
   - 推理在 NPU/DSP 上（高通 SNPE / 海思 HIAI）
   - 传统 ISP 在 ISP 硬件上（BLC/LSC/DPC）
   
4. 延迟优化：
   - 流水线化：当第 N 帧在 NPU 推理时，第 N+1 帧的预处理在 CPU 跑
   - 分辨率权衡：从原始 RAW 下采样，输出再双线性上采样
   
5. 功耗控制：
   - 只在低光场景（AE 统计）激活 AI 增强模块
   - 正常光照走传统 ISP 快速通道
   
6. 评估指标：
   - 在目标手机上用 Profiling 工具（Android GPU Inspector）测实际延迟
   - 用电量统计工具测每帧功耗
```

---

## 十、GitHub 作品集搭建指南

> **社招面试最有力的敲门砖**：一个有内容、有数据、有思路的 GitHub 仓库

### 推荐仓库结构

```
ai-isp-portfolio/
├── README.md                    ← 必须包含效果图 + 性能表格
│
├── 01_soft_isp/                 ← 阶段一：Python ISP
│   ├── pipeline.py              # 完整 Pipeline
│   ├── modules/                 # 各模块实现
│   │   ├── blc.py
│   │   ├── awb.py
│   │   ├── demosaic.py
│   │   ├── ccm.py
│   │   └── gamma.py
│   ├── evaluate.py              # PSNR/SSIM 评估
│   └── notebooks/               # Jupyter 展示效果
│
├── 02_cpp_isp/                  ← 阶段三：C++ 高性能库
│   ├── CMakeLists.txt
│   ├── include/
│   ├── src/
│   ├── benchmark/               # 性能测试代码
│   └── README.md                # 性能测试报告
│
├── 03_ai_denoising/             ← 阶段二：AI 降噪模型
│   ├── models/
│   │   ├── unet.py
│   │   └── nafnet.py
│   ├── train.py
│   ├── evaluate.py
│   ├── noise_synthesis.py       # 噪声合成工具
│   ├── results/                 # 效果图 + 指标
│   └── README.md
│
├── 04_trt_deployment/           ← 阶段四：TensorRT 部署
│   ├── export_onnx.py
│   ├── build_engine.cpp
│   ├── inference.cpp
│   └── benchmark.md             # 延迟对比表
│
└── docs/
    ├── architecture.png         # 系统架构图
    └── comparison/              # Before/After 效果对比图
```

### README 必须包含的内容

```markdown
## Performance

| Method | PSNR (dB) | SSIM | Inference Time (ms) | Platform |
|--------|-----------|------|---------------------|----------|
| C++ ISP (baseline) | 28.5 | 0.82 | 12 ms | i7-12700 |
| AI-ISP (NAFNet FP32) | 32.1 | 0.91 | 45 ms | RTX 3060 |
| AI-ISP (TRT INT8) | 31.8 | 0.90 | 8 ms | RTX 3060 |

## Visual Results

[Before (Noisy)] → [After (Enhanced)]
```

---

## 十一、技术栈全景图

### 核心技术栈（社招必备）

```
┌─────────────────────────────────────────────────────────┐
│                    应用场景理解层                         │
│  ISP Pipeline 全流程 | 3A 算法 | 图像质量评价（IQ）       │
├─────────────────────────────────────────────────────────┤
│                    AI 算法层                              │
│  PyTorch | UNet/NAFNet/Restormer | 论文复现               │
│  Loss 设计：L1 + SSIM + Perceptual                        │
│  数据增强：噪声合成（Poisson-Gaussian）                   │
├─────────────────────────────────────────────────────────┤
│                    工程实现层                              │
│  C++17/20 | OpenCV | 内存管理（侯捷）                     │
│  多线程（OpenMP/std::thread）| SIMD（NEON/SSE）           │
│  CMake | Git | Linux 命令行                               │
├─────────────────────────────────────────────────────────┤
│                    性能优化层                              │
│  CUDA Kernel | Shared Memory | Stream 流水线              │
│  TensorRT（GPU 部署）| NCNN/MNN（移动端部署）              │
│  INT8 量化 | 模型剪枝                                     │
├─────────────────────────────────────────────────────────┤
│                    工具链层                                │
│  Python（NumPy/rawpy/matplotlib）| GCC | Valgrind         │
│  TensorBoard | Nsight Systems | perf                      │
└─────────────────────────────────────────────────────────┘
```

### 技能掌握里程碑

| 里程碑 | 标志性能力 | 对应面试水平 |
|---|---|---|
| **入门** | 能读取 RAW，Python 跑通基础 ISP Pipeline | ISP 调试助理工程师 |
| **初级** | 能复现 AI-ISP 论文，PSNR 接近论文 | AI 图像算法工程师（1-3年） |
| **中级** | C++ ISP + TensorRT 部署完整链路 | 高级图像算法工程师（3-5年） |
| **高级** | 设计端侧实时 AI-ISP 系统，平衡性能/功耗/画质 | 资深/专家级（5年+） |

---

## 附录：每日学习检查清单

### 理论学习维度

- [ ] 今天的概念能用大白话解释清楚吗？
- [ ] 这个模块的数学原理（公式）会推导吗？
- [ ] 能说出这个设计决策的物理直觉？

### 代码实践维度

- [ ] 今天写了多少行代码？（目标：至少 50 行有效代码）
- [ ] 代码有单元测试吗？
- [ ] 性能是否测量了？（耗时/内存占用）

### 项目推进维度

- [ ] 今天的输出（代码/图表/报告）是否推送到 GitHub？
- [ ] 本周里程碑目标完成了多少？

---

> **写在最后**：AI-ISP 是一个"物理直觉 + 数学基础 + 工程能力 + 算法创新"四维度高度融合的领域。你的软件工程背景是核心优势——很多光学背景的工程师卡在代码效率上，而你的 C++ 底层能力和工程系统性思维，结合扎实的 ISP 物理理解和 AI 算法能力，是 2026 年社招市场最稀缺的复合型人才。
>
> **最重要的一条原则**：每周输出大于输入。少看视频，多写代码，多提交 commit。
```
