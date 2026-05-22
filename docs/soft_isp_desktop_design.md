# C++ 桌面端 Soft ISP Pipeline 工作台开发设计文档

## 1. 文档目标

本文档用于指导一个基于 C++ 的桌面端 Soft ISP Pipeline 工作台开发。软件目标不是替代 Lightroom、darktable 或 RawTherapee 这类摄影后期软件，而是实现一个面向学习、研究、算法验证和调试的 ISP 可视化平台。

核心能力是：

```text
RAW/DNG 图像输入
→ 按阶段执行 ISP pipeline
→ 查看每个阶段的中间结果
→ 修改关键阶段参数
→ 替换或扩展部分算法模块
→ 导出最终 sRGB 图像或任意中间结果
```

这个软件的设计参考 Karaimer 和 Brown 在 ECCV 2016 的相机成像管线平台思想：把原本相机内部不可见的 ISP 黑盒拆成可观察、可操作、可实验的阶段。

## 2. 设计假设与边界

### 2.1 基本假设

1. 第一版优先支持单帧 RAW/DNG，不做多帧 HDR、夜景融合、语义增强等现代手机计算摄影能力。
2. 第一版优先支持 Bayer RAW，不优先支持 X-Trans、Foveon 或厂商高度私有格式。
3. 第一版重点验证 pipeline 架构、图像语义、参数调节和中间结果展示，不追求与 Adobe Camera Raw 或相机直出 JPEG 完全一致。
4. RAW 解码和 metadata 提取使用成熟库，ISP 关键流程由项目自己实现，避免把第三方库的黑盒渲染流程直接当作核心 pipeline。
5. 第一版使用 CPU 浮点 pipeline，预览分辨率和全分辨率导出分离。GPU、SIMD、tile-based processing 放到后续阶段。
6. 第一版仍以传统单帧 scene-referred ISP 为主，但架构必须预留 modern ISP 扩展点，包括 computational RAW、HDR gain map、AI/learned ISP、GPU 后端和任务驱动评估。
7. DNG 不再默认等同于纯传感器 Bayer RAW。现代手机的 ProRAW、computational RAW 或线性 DNG 可能已经包含部分计算摄影处理，因此 RAW loader 必须标记输入来源和处理状态。

### 2.2 不在第一版范围内的内容

第一版不做：

```text
完整图库管理
商业级修图工作流
批量后期预设市场
AI ISP
多帧融合
GPU 实时处理
动态插件系统
所有 RAW 格式完美支持
与 Adobe/相机厂商色彩完全一致
完整 ProRAW/Ultra HDR 还原
HDR gain map 写出
ONNX/AI 模型推理
任务驱动自动调参
```

这些功能并非不重要，而是会显著放大项目复杂度。第一版的成功标准应该是闭环清晰，而不是功能堆满。

### 2.3 面向当前 ISP 发展的架构要求

虽然第一版不实现现代计算摄影的全部能力，但设计上不能把系统锁死在 2016 年式的单帧传统 ISP 中。当前 ISP 发展至少带来以下变化：

1. **RAW 类型更复杂**：DNG 可能是纯 Bayer RAW，也可能是 linear DNG、demosaiced DNG、ProRAW 或其他 computational RAW。
2. **输出不再只有 SDR sRGB**：现代图像系统开始支持 HDR photo、gain map、Display P3、PQ/HLG 等显示和编码形式。
3. **ISP 不一定是固定手写算法**：denoise、demosaic、tone mapping、RAW-to-RGB 都可能由神经网络或混合模型完成。
4. **处理后端多样化**：CPU 标量实现只是基线，后续可能需要 SIMD、OpenCL、Vulkan、CUDA、DirectML 或 ONNX Runtime。
5. **评估目标更丰富**：除了视觉质量，还可能关注色差、动态范围、运行时间、功耗、模型大小，以及检测/分割等下游任务效果。

因此第一版虽然只实现传统 CPU pipeline，也要在数据结构、stage 接口、导出格式和测试体系里预留这些维度。

## 3. 产品定位

### 3.1 目标用户

主要用户包括：

1. 学习 ISP、RAW 处理和计算摄影的学生或工程师。
2. 调试 demosaic、denoise、white balance、tone mapping 等算法的研究者。
3. 希望观察 RAW 到 sRGB 每一步变化的图像处理开发者。
4. 需要导出中间结果做实验或论文对比的人。

### 3.2 核心使用场景

典型使用流程：

```text
1. 用户打开一张 DNG/RAW。
2. 软件读取 RAW 数据和 metadata。
3. 软件生成默认 ISP pipeline。
4. 用户在左侧 stage 列表中点击任意阶段。
5. 中间预览区显示该阶段输出。
6. 用户在右侧参数面板调整曝光、白平衡、tone curve 等参数。
7. 软件只重算受影响的后续阶段。
8. 用户对比 before/after 或导出当前阶段图像。
9. 用户导出最终 sRGB PNG/TIFF。
```

## 4. 技术选型

### 4.1 编程语言

推荐：

```text
C++20 或 C++23
```

原因：

1. ISP pipeline 涉及大量像素级计算，C++ 在性能和内存控制上更合适。
2. LibRaw、LittleCMS、OpenCV、OpenImageIO、Qt 等关键库都有成熟 C/C++ 接口。
3. 后续接 SIMD、OpenCL、CUDA、Vulkan、Metal 或 WebGPU 都更自然。
4. C++ 更适合长期维护 native 桌面软件。

不推荐纯 C 作为主语言。C 适合写底层像素 kernel，但完整软件还需要 GUI、缓存、插件、配置、项目文件、多线程和资源管理，用 C 会增加工程负担。

### 4.2 GUI 框架

推荐第一版使用：

```text
Qt 6 + Qt Widgets
```

原因：

1. Qt Widgets 对传统桌面工具类应用很成熟。
2. Dock、菜单栏、工具栏、列表、参数面板、图像视图都容易实现。
3. C++ 与 UI 的交互直接，不需要引入 Electron/Web 前端栈。
4. 第一版重点是工程闭环，不需要复杂动画和强视觉表现。

后续可以局部引入 Qt Quick/QML：

```text
节点图编辑器
更现代的时间线/参数动画
高交互图像查看器
```

### 4.3 RAW 解码

推荐：

```text
LibRaw
```

使用方式：

1. 用 LibRaw 读取 RAW 像素数据。
2. 用 LibRaw 提取 CFA/Bayer pattern、黑电平、白电平、白平衡、相机型号、EXIF 等 metadata。
3. 不依赖 LibRaw 的完整 postprocess 输出作为项目核心结果。

原因：

LibRaw 的价值在于屏蔽大量相机 RAW 格式差异，让项目能专注于 ISP 处理本身。但项目目标是可视化和拆解 ISP pipeline，因此关键 stage 应由项目自己控制。

### 4.4 色彩管理

第一版推荐：

```text
LittleCMS
```

用途：

1. ICC profile 转换。
2. 输出 sRGB、Display P3 或其他显示/文件 profile。
3. 后续支持软打样或自定义 profile。

后续可选：

```text
OpenColorIO
```

OpenColorIO 更适合影视、ACES、复杂 LUT 和 view transform 工作流。第一版不建议直接引入，除非产品明确面向电影色彩管理或 LUT pipeline。

现代 ISP 需要额外区分：

```text
scene-referred linear data
display-referred SDR data
display-referred HDR data
wide-gamut working space
output transfer function
```

第一版可以使用 Linear sRGB 简化工作空间，但接口上不要把 `DisplayRgb`、`sRGB` 和 `final image` 混为一谈。后续应支持 Display P3、Rec.2020、PQ、HLG、OpenEXR 线性 HDR 和 gain map 输出。

### 4.5 图像处理辅助库

推荐：

```text
OpenCV
```

用途：

1. resize。
2. filter。
3. histogram。
4. 简单 denoise。
5. debug 输出。
6. 图像格式转换辅助。

注意：

核心图像数据结构不应完全依赖 `cv::Mat`。建议自己定义 `ImageBuffer`，OpenCV 作为辅助工具使用。这样可以更清楚表达 RAW mosaic、linear RGB、working RGB、display RGB 等不同语义。

### 4.6 图像读写

MVP 可先使用：

```text
Qt ImageWriter
```

用于输出 PNG/JPEG。

后续建议加入：

```text
OpenImageIO
```

用于更完整地支持 TIFF、OpenEXR、16-bit/32-bit 浮点图像、多通道图像和专业图像 I/O。

对于现代 HDR 工作流，建议把 OpenEXR 从“很后期”提前到第二阶段考虑。OpenEXR 适合保存 scene-linear 中间结果和 HDR 浮点结果，比 8-bit PNG 更适合作为算法调试输出。

HDR photo 输出可以分阶段支持：

```text
第一阶段：导出 SDR PNG/TIFF
第二阶段：导出 OpenEXR 线性 HDR
第三阶段：生成 SDR base + HDR gain map
第四阶段：写出 Ultra HDR / ISO 21496-1 兼容文件
```

### 4.7 构建与依赖管理

推荐：

```text
CMake + vcpkg
```

原因：

1. CMake 是 C++ 跨平台项目事实标准。
2. vcpkg 对 Windows 环境比较友好。
3. LibRaw、OpenCV、LittleCMS、OpenImageIO 等库可通过包管理集成。

建议支持平台：

```text
Windows 优先
macOS/Linux 后续
```

当前用户环境在 Windows，第一版先把 Windows 闭环跑通更现实。

### 4.8 AI/模型推理预留

第一版不实现 AI ISP，但建议预留模型推理后端。

后续推荐：

```text
ONNX Runtime C++ API
```

用途：

1. AI denoise。
2. learned demosaic。
3. learned tone mapping。
4. RAW-to-sRGB learned ISP。
5. 任务驱动 ISP 模型评估。

AI stage 不应直接绑定某个深度学习框架。建议抽象为：

```text
ModelRuntime
TensorAdapter
NeuralStage
```

这样后续可以接 ONNX Runtime、DirectML、CUDA、TensorRT 或 CPU fallback。

### 4.9 处理后端预留

第一版只实现 CPU，但 `ProcessContext` 应该从一开始包含处理后端信息。

```cpp
enum class ProcessingBackend {
    CpuScalar,
    CpuSimd,
    OpenCL,
    Vulkan,
    Cuda,
    DirectML,
    OnnxRuntime
};
```

设计原则：

1. CPU 标量实现是正确性基线。
2. SIMD/GPU/AI 后端是性能或算法增强，不应改变 stage 的图像语义。
3. 同一 stage 可以有多个 backend implementation，但参数 schema 和输入输出类型应保持一致。

## 5. 总体架构

软件分为五层：

```text
┌────────────────────────────────────┐
│ UI 层                               │
│ 主窗口、图像预览、参数面板、日志       │
├────────────────────────────────────┤
│ 应用服务层                          │
│ 项目管理、命令、任务调度、状态同步      │
├────────────────────────────────────┤
│ Pipeline 层                         │
│ stage 顺序、缓存、依赖、重算策略       │
├────────────────────────────────────┤
│ ISP Core 层                         │
│ RAW 处理、demosaic、色彩、tone 等      │
├────────────────────────────────────┤
│ 基础设施层                          │
│ 文件 I/O、线程池、日志、配置、第三方库   │
└────────────────────────────────────┘
```

### 5.1 UI 层

职责：

1. 展示文件、pipeline、参数、图像和 metadata。
2. 接收用户操作。
3. 发出参数变更或导出命令。
4. 不直接执行耗时图像处理。

UI 层必须避免：

```text
在 UI 线程跑完整 pipeline
直接持有大量全分辨率中间图
把算法逻辑写进 widget 代码
```

### 5.2 应用服务层

职责：

1. 管理当前打开的项目。
2. 管理当前 RAW 文件和 pipeline 配置。
3. 协调 UI 与 pipeline。
4. 调度后台任务。
5. 管理 undo/redo，后续实现。

可定义：

```cpp
class ProjectController;
class PipelineController;
class PreviewController;
class ExportController;
```

### 5.3 Pipeline 层

职责：

1. 保存 stage 列表。
2. 维护 stage 参数。
3. 维护 stage 输出缓存。
4. 处理局部重算。
5. 检查输入输出类型是否匹配。

### 5.4 ISP Core 层

职责：

1. 实现具体 ISP 算法。
2. 保证图像数据语义正确。
3. 不依赖 UI。
4. 可以被命令行工具、测试和 GUI 共同调用。

### 5.5 基础设施层

职责：

1. 文件路径和资源管理。
2. 日志。
3. 线程池。
4. JSON 配置。
5. 第三方库封装。

## 6. 推荐目录结构

```text
soft-isp-workbench/
  CMakeLists.txt
  README.md
  docs/
    soft_isp_desktop_design.md
  src/
    app/
      main.cpp
      Application.cpp
      ProjectController.cpp
      PipelineController.cpp
    ui/
      MainWindow.cpp
      ImageViewport.cpp
      PipelinePanel.cpp
      StageParamPanel.cpp
      HistogramPanel.cpp
      MetadataPanel.cpp
      LogPanel.cpp
    io/
      RawLoader.cpp
      ImageExporter.cpp
      ProjectFile.cpp
    image/
      ImageBuffer.cpp
      ImageView.cpp
      ImageTypes.cpp
    pipeline/
      Pipeline.cpp
      PipelineStage.cpp
      StageRegistry.cpp
      PipelineCache.cpp
    isp/
      RawDecodeStage.cpp
      BlackLevelStage.cpp
      NormalizeStage.cpp
      DemosaicStage.cpp
      WhiteBalanceStage.cpp
      ColorMatrixStage.cpp
      ExposureStage.cpp
      ToneMappingStage.cpp
      GammaStage.cpp
    color/
      ColorSpace.cpp
      Matrix3x3.cpp
      IccTransform.cpp
    infra/
      Logger.cpp
      ThreadPool.cpp
      Json.cpp
  tests/
    test_black_level.cpp
    test_demosaic.cpp
    test_color_matrix.cpp
    test_pipeline_cache.cpp
  samples/
    README.md
```

## 7. 核心数据结构设计

### 7.1 图像类型

必须明确每个阶段的图像语义：

```cpp
enum class ImageKind {
    RawMosaic,
    LinearCameraRgb,
    LinearWorkingRgb,
    SceneLinearRgb,
    DisplayReferredSdrRgb,
    DisplayReferredHdrRgb,
    DisplayRgb
};
```

含义：

1. `RawMosaic`：单通道 Bayer/X-Trans 传感器数据，尚未 demosaic。
2. `LinearCameraRgb`：demosaic 后的相机 RGB，仍处于相机设备相关空间。
3. `LinearWorkingRgb`：转换到工作色彩空间后的线性 RGB。
4. `SceneLinearRgb`：场景线性 RGB，适合曝光、物理意义上的 HDR 和部分算法处理。
5. `DisplayReferredSdrRgb`：面向 SDR 显示或 SDR 文件输出的图像。
6. `DisplayReferredHdrRgb`：面向 HDR 显示或 HDR 文件输出的图像。
7. `DisplayRgb`：兼容旧接口的显示 RGB，后续应逐步替换为更明确的 SDR/HDR 类型。

新增 `SceneLinearRgb`、`DisplayReferredSdrRgb`、`DisplayReferredHdrRgb` 是为了避免把 scene-referred 数据、tone-mapped SDR 数据和 HDR 输出数据混在一起。传统 ISP 里这一区分不明显，但现代 HDR photo、gain map 和 AI ISP 都依赖清晰的数据语义。

### 7.1.1 RAW 来源类型

不能假设所有 DNG 都是纯 Bayer RAW。建议增加：

```cpp
enum class RawSourceKind {
    SensorMosaicRaw,
    LinearDng,
    DemosaicedDng,
    ComputationalRaw,
    Unknown
};
```

含义：

1. `SensorMosaicRaw`：接近传感器原始 CFA 数据，需要完整传统 ISP。
2. `LinearDng`：已经是线性图像，但可能仍需要色彩、tone 和输出处理。
3. `DemosaicedDng`：已经完成 demosaic，不应再进入 RawMosaic 专用 stage。
4. `ComputationalRaw`：例如手机 ProRAW 一类，可能已经包含多帧融合、降噪、局部 tone 或厂商处理痕迹。
5. `Unknown`：metadata 不足，UI 需要提示用户当前 pipeline 可能不可靠。

RAW loader 必须把该类型写入 metadata，pipeline 根据类型生成不同默认 stage。

### 7.1.2 CFA 描述器

不要只用简单的 `BayerPattern` enum 描述传感器排列。现代传感器可能是 Bayer、X-Trans、Quad Bayer、RYYB 或其他排列。建议使用描述器：

```cpp
enum class ColorFilter {
    R,
    G,
    B,
    C,
    M,
    Y,
    W,
    Unknown
};

enum class SensorArrangement {
    Bayer,
    XTrans,
    QuadBayer,
    Ryyb,
    Monochrome,
    Unknown
};

struct CfaDescriptor {
    int tileWidth = 2;
    int tileHeight = 2;
    std::vector<ColorFilter> pattern;
    SensorArrangement arrangement = SensorArrangement::Unknown;
};
```

MVP 只需要支持 2x2 Bayer，但用描述器可以避免后续支持 Quad Bayer 或特殊 CFA 时大改数据结构。

### 7.2 像素格式

```cpp
enum class PixelFormat {
    UInt16,
    Float16,
    Float32
};
```

MVP 内部推荐全部用 `Float32`。

原因：

1. RAW 处理经常需要保留 0 以下或 1 以上的值。
2. 白平衡、矩阵变换、曝光和 tone mapping 都会产生浮点结果。
3. 浮点能减少多次处理造成的量化误差。

### 7.3 ImageBuffer

```cpp
struct ImageBuffer {
    int width = 0;
    int height = 0;
    int channels = 0;
    ImageKind kind = ImageKind::RawMosaic;
    PixelFormat format = PixelFormat::Float32;
    ColorSpace colorSpace;
    std::vector<float> data;

    float* row(int y);
    const float* row(int y) const;
};
```

设计原则：

1. `ImageBuffer` 只描述像素数据和基本语义。
2. metadata 不塞进 `ImageBuffer`。
3. 不在 `ImageBuffer` 内部直接依赖 Qt 或 OpenCV。
4. 后期如果需要 tile-based processing，可以扩展出 `ImageTile` 或 `ImagePlane`。

### 7.4 RAW Metadata

```cpp
struct RawMetadata {
    std::string cameraMake;
    std::string cameraModel;
    int rawWidth = 0;
    int rawHeight = 0;

    RawSourceKind rawSourceKind = RawSourceKind::Unknown;
    CfaDescriptor cfa;

    std::array<float, 4> blackLevel = {0, 0, 0, 0};
    float whiteLevel = 1.0f;

    std::array<float, 4> whiteBalance = {1, 1, 1, 1};

    Matrix3x3 colorMatrix1;
    Matrix3x3 colorMatrix2;
    std::optional<Matrix3x3> forwardMatrix1;
    std::optional<Matrix3x3> forwardMatrix2;

    double exposureTime = 0.0;
    double iso = 0.0;
    double aperture = 0.0;
    double focalLength = 0.0;

    bool hasHdrGainMap = false;
    bool hasEmbeddedPreview = false;
    bool mayContainComputationalProcessing = false;
};
```

注意：

不同 RAW 文件 metadata 可能缺失。缺失时应该在 UI 中清楚显示，而不是静默假装存在。

如果 `rawSourceKind != SensorMosaicRaw`，UI 应提示用户：当前文件可能不适合完整传统 Bayer pipeline，部分 stage 会被跳过或替换。

## 8. Pipeline Stage 设计

### 8.1 Stage 接口

```cpp
class PipelineStage {
public:
    virtual ~PipelineStage() = default;

    virtual std::string id() const = 0;
    virtual std::string displayName() const = 0;

    virtual ImageKind inputKind() const = 0;
    virtual ImageKind outputKind() const = 0;

    virtual StageParamSchema paramSchema() const = 0;

    virtual ImageBuffer process(
        const ImageBuffer& input,
        const RawMetadata& metadata,
        const StageParams& params,
        const ProcessContext& context
    ) const = 0;
};
```

`ProcessContext` 至少应包含：

```cpp
struct ProcessContext {
    ProcessingBackend backend = ProcessingBackend::CpuScalar;
    bool previewMode = true;
    int maxPreviewSize = 1600;
    bool allowApproximation = true;
    bool allowGpu = false;
    bool allowNeuralRuntime = false;
};
```

这样第一版可以只使用 `CpuScalar`，后续加入 SIMD、GPU 或 ONNX Runtime 时不需要改动所有 stage 的函数签名。

### 8.2 Stage 参数

参数需要支持 UI 自动生成控件，因此不能只用零散变量。

```cpp
enum class ParamType {
    Bool,
    Int,
    Float,
    Enum,
    Curve,
    Matrix3x3,
    FilePath
};
```

每个参数包含：

```text
id
显示名
类型
默认值
最小值/最大值
步进
是否实时预览
```

示例：

```json
{
  "id": "exposure_ev",
  "name": "曝光补偿",
  "type": "float",
  "default": 0.0,
  "min": -5.0,
  "max": 5.0,
  "step": 0.05
}
```

### 8.3 MVP Stage 列表

第一版建议实现如下阶段：

```text
1. Raw Decode
2. Black Level Correction
3. White Level Normalize
4. Demosaic
5. White Balance
6. Camera RGB To XYZ
7. XYZ To Working RGB
8. Exposure Compensation
9. Tone Mapping
10. Display Transform
11. Gamma Encode
12. Output
```

其中真正需要用户调参的阶段先控制在少数：

```text
White Balance
Exposure Compensation
Tone Mapping
Gamma Encode
```

这样能让第一版功能可控。

### 8.4 现代扩展 Stage 类型

第一版不实现，但接口应预留以下 stage 类型：

```text
RawSourceDetectStage
HdrGainMapDecodeStage
HdrGainMapEncodeStage
NeuralDenoiseStage
NeuralDemosaicStage
NeuralIspStage
LocalToneMappingStage
TaskMetricStage
PipelineOptimizerStage
```

这些 stage 不进入 MVP 默认 pipeline，但需要在 stage registry 和项目文件 schema 中允许出现。这样后续不会因为文件格式和 stage 类型写死而返工。

### 8.5 根据 RAW 类型生成默认 Pipeline

不同 RAW 来源应生成不同默认 pipeline：

```text
SensorMosaicRaw:
  Raw Decode
  Black Level Correction
  White Level Normalize
  Demosaic
  White Balance
  Camera RGB To XYZ
  XYZ To Working RGB
  Exposure
  Tone Mapping
  Display Transform
  Gamma

LinearDng:
  Raw Decode
  White Balance，可选
  Color Transform
  Exposure
  Tone Mapping
  Display Transform
  Gamma

DemosaicedDng:
  Raw Decode
  Color Transform
  Exposure
  Tone Mapping
  Display Transform
  Gamma

ComputationalRaw:
  Raw Decode
  Computational Metadata Inspect
  Color Transform
  Exposure
  Tone Mapping / Gain Map Preview
  Display Transform
```

如果类型未知，软件应允许用户手动选择 pipeline 模板，并在 UI 中显示风险提示。

## 9. ISP 阶段详细设计

### 9.1 Raw Decode

输入：

```text
RAW/DNG 文件路径
```

输出：

```text
RawMosaic ImageBuffer
RawMetadata
```

实现：

1. 使用 LibRaw 打开文件。
2. 读取 RAW 像素。
3. 读取 CFA pattern。
4. 读取 black level、white level、white balance、color matrix 等 metadata。
5. 把 RAW 像素转为 float32，但不要做完整渲染。
6. 判断并记录 `RawSourceKind`，区分纯传感器 mosaic RAW、linear DNG、demosaiced DNG 和 computational RAW。
7. 如果发现 embedded preview、HDR metadata、gain map 或手机 computational RAW 特征，应写入 metadata 并在 UI 中展示。

Raw Decode 的输出不一定总是 `RawMosaic`。如果输入是 demosaiced DNG 或 linear DNG，输出类型应根据实际数据设为 `LinearCameraRgb`、`SceneLinearRgb` 或更合适的类型，而不是强制进入 demosaic stage。

### 9.2 Black Level Correction

输入：

```text
RawMosaic
```

公式：

```text
corrected = raw - black_level[channel]
```

注意：

1. Bayer 四个位置可能有不同黑电平。
2. 结果可暂时保留负值，用于 debug；显示时再 clamp。

### 9.3 White Level Normalize

公式：

```text
normalized = corrected / (white_level - black_level[channel])
```

输出范围理论上接近：

```text
0.0 ~ 1.0
```

但实际处理时不要过早 clamp，高光可能需要保留。

### 9.4 Bad Pixel Correction

MVP 可不做，或只做非常简单的坏点替换。

后续实现：

1. 利用 metadata 中的坏点表。
2. 或使用邻域中值检测异常点。

### 9.5 Denoise

MVP 可选。

第一版如果做，只建议简单算法：

```text
median filter
bilateral filter
```

不要一开始实现复杂 BM3D 或深度学习降噪。

### 9.6 Demosaic

MVP 实现：

```text
bilinear demosaic
```

原因：

1. 简单。
2. 容易验证。
3. 适合展示 pipeline 概念。

后续再加入：

```text
AHD
VNG
AMaZE
RCD
```

注意：

Demosaic 输入必须是 `RawMosaic`，输出是 `LinearCameraRgb`。

### 9.7 White Balance

输入：

```text
LinearCameraRgb
```

公式：

```text
R' = R * r_gain
G' = G * g_gain
B' = B * b_gain
```

参数来源：

1. RAW metadata 的 as-shot white balance。
2. 用户自定义色温/色调。
3. 灰点取样。

MVP 可以先做通道增益滑条。

### 9.8 Camera RGB To XYZ

输入：

```text
LinearCameraRgb
```

输出：

```text
Linear XYZ
```

使用 DNG/RAW metadata 中的 color matrix 或 forward matrix。

注意：

1. 不同光源可能对应不同矩阵。
2. DNG 中 ColorMatrix1/2 对应不同 calibration illuminant。
3. MVP 可以先选一个矩阵，后续再根据白平衡或光源插值。

### 9.9 XYZ To Working RGB

推荐第一版工作空间：

```text
Linear sRGB
```

原因：

1. 简单。
2. 显示转换直观。
3. 便于 debug。

后续可改成：

```text
Linear Rec.2020
ACEScg
ProPhoto RGB
```

如果目标包含现代 HDR 或大范围色彩实验，后续建议优先支持：

```text
Linear Rec.2020
ACEScg
Linear Display P3
```

`Linear sRGB` 适合 MVP，但色域较窄，不适合作为长期唯一工作空间。

### 9.10 Exposure Compensation

公式：

```text
out = in * pow(2.0, ev)
```

参数：

```text
EV: -5.0 ~ +5.0
```

注意：

曝光补偿应发生在线性空间。

### 9.11 Tone Mapping

MVP 提供三种模式：

```text
None
Reinhard
Simple Filmic
```

简单 Reinhard：

```text
out = x / (1 + x)
```

注意：

tone mapping 和 gamma 是两件事。tone mapping 处理动态范围，gamma 处理显示编码。

现代 HDR 工作流中，还需要区分：

```text
全局 tone mapping
局部 tone mapping
HDR → SDR rendition
HDR scene-linear → HDR display-referred
gain map generation
```

第一版只做 SDR tone mapping，但接口不要假设 tone mapping 的输出一定是 sRGB。后续同一个 scene-linear 输入可能同时生成 SDR base image 和 HDR gain map。

### 9.12 Display Transform

职责：

1. 从 working RGB 转到显示/输出 RGB。
2. 可以使用 LittleCMS 或固定矩阵。

MVP 如果 working RGB 就是 linear sRGB，则这一阶段可以很薄。

### 9.13 Gamma Encode

sRGB 编码：

```text
if x <= 0.0031308:
    y = 12.92 * x
else:
    y = 1.055 * pow(x, 1/2.4) - 0.055
```

输出：

```text
DisplayRgb
```

UI 显示前需要 clamp 到：

```text
0.0 ~ 1.0
```

### 9.14 HDR Gain Map，后续

HDR gain map 用于在一个 SDR base 图像上附加恢复 HDR 亮度和色彩的信息。现代移动端 HDR 照片工作流常见这种形式。

后续可设计为：

```text
SceneLinearRgb
→ HDR Render
→ SDR Render
→ GainMap = f(HDR Render, SDR Render)
→ SDR image + gain map + metadata
```

需要保存的 metadata 包括：

```text
min/max gain
gamma
offset
HDR headroom
SDR reference white
HDR reference white
color space
transfer function
```

MVP 不写 gain map，但应允许 pipeline 中存在 `HdrGainMapEncodeStage`，并允许项目文件保存相关参数。

### 9.15 Neural ISP，后续

AI/learned ISP stage 的输入输出可能不是普通 `ImageBuffer`，而是 tensor。建议使用 adapter，不要让核心 ImageBuffer 直接变成深度学习框架对象。

```cpp
class TensorAdapter {
public:
    virtual Tensor toTensor(const ImageBuffer& image, const TensorLayout& layout) = 0;
    virtual ImageBuffer toImage(const Tensor& tensor, const ImageDescriptor& desc) = 0;
};
```

Neural stage 需要声明：

```text
模型路径
输入图像类型
输出图像类型
tile size
overlap
归一化方式
色彩空间要求
是否支持 FP16/INT8
推荐 backend
```

第一版不实现，但 stage 接口和项目文件要允许这些参数存在。

## 10. Pipeline 缓存与重算

### 10.1 缓存目标

用户拖动参数时，不能每次从 RAW 全量重跑。应只重算受影响的后续阶段。

例如：

```text
Raw Decode
Black Level
Normalize
Demosaic
White Balance
Color Matrix
Exposure
Tone Mapping
Gamma
```

如果用户改 `Exposure`，只需要清除：

```text
Exposure
Tone Mapping
Gamma
```

之前的缓存保留。

### 10.2 缓存结构

```cpp
struct StageCacheEntry {
    std::string stageId;
    size_t paramHash;
    std::shared_ptr<ImageBuffer> output;
};
```

### 10.3 Preview 与 Full 分离

必须分两套 pipeline context：

```text
PreviewContext:
  maxSize = 1600
  fastMode = true

FullContext:
  maxSize = original
  fastMode = false
```

原因：

1. 预览需要响应快。
2. 导出需要质量高。
3. 用户拖滑条时不应触发全分辨率重算。

## 11. UI 详细设计

### 11.1 主窗口布局

推荐布局：

```text
┌────────────────────────────────────────────────────────────┐
│ 菜单栏 / 工具栏                                             │
├───────────────┬──────────────────────────────┬─────────────┤
│ 文件与阶段列表 │ 图像预览区                    │ 参数面板      │
│               │                              │             │
├───────────────┴──────────────────────────────┴─────────────┤
│ histogram / metadata / log / RGB 采样                        │
└────────────────────────────────────────────────────────────┘
```

### 11.2 左侧 Pipeline Panel

显示：

```text
stage 名称
启用/禁用状态
处理耗时
缓存状态
错误状态
```

交互：

1. 点击 stage：预览该 stage 输出。
2. 勾选启用：stage 生效。
3. 取消启用：跳过 stage，若输入输出类型允许。
4. 右键菜单：导出该 stage 输出、复制参数、重置参数。

### 11.3 中央图像预览区

功能：

```text
缩放
平移
适应窗口
100% 查看
before/after 对比
split view
鼠标像素取样
```

显示信息：

```text
坐标
RGB 值
线性值/显示值切换
当前 stage
缩放比例
```

### 11.4 参数面板

根据 stage 的 `StageParamSchema` 自动生成控件：

```text
Bool → checkbox
Float → slider + spinbox
Enum → combobox
Curve → curve editor，后期
Matrix3x3 → matrix editor，后期
FilePath → file picker
```

参数变更策略：

```text
滑动中：低分辨率预览
释放滑块：高质量预览
导出时：全分辨率处理
```

### 11.5 底部信息区

Tabs：

```text
Histogram
Metadata
Log
Performance
Pixel Inspector
```

MVP 优先：

```text
Histogram
Metadata
Log
```

## 12. 项目文件设计

项目文件使用 JSON。

示例：

```json
{
  "version": 1,
  "source": "C:/photos/sample.dng",
  "activeStage": "tone_mapping",
  "pipeline": [
    {
      "stage": "black_level",
      "enabled": true,
      "params": {}
    },
    {
      "stage": "white_balance",
      "enabled": true,
      "params": {
        "r_gain": 2.1,
        "g_gain": 1.0,
        "b_gain": 1.6
      }
    },
    {
      "stage": "exposure",
      "enabled": true,
      "params": {
        "ev": 0.5
      }
    }
  ]
}
```

设计原则：

1. 只保存参数和引用，不修改原始 RAW。
2. 相对路径优先，方便项目移动。
3. 加 `version`，为后续格式迁移留空间。

## 13. 导出设计

### 13.1 最终输出

MVP 支持：

```text
PNG 8-bit
TIFF 16-bit，后续
JPEG，后续
```

建议调整优先级：

```text
MVP：PNG 8-bit，用于快速可视化
第二阶段：TIFF 16-bit，用于较高质量 SDR 输出
第二阶段：OpenEXR float16/float32，用于 scene-linear/HDR 中间结果
第三阶段：JPEG/PNG + ICC profile
第四阶段：HDR gain map / Ultra HDR / ISO 21496-1 兼容输出
```

不要把 PNG 作为算法中间结果的唯一格式。PNG 适合看图，不适合保存 scene-linear、负值、高光超过 1.0 或宽动态范围数据。

### 13.2 中间结果输出

根据 stage 类型决定：

```text
RawMosaic → 16-bit TIFF 或 debug PNG
Linear RGB → 16-bit TIFF / OpenEXR
Display RGB → PNG / TIFF / JPEG
```

MVP 可以先全部导出可视化 PNG，但文档和 UI 要明确：PNG 是显示用，不等同于原始数值精度。

### 13.3 HDR 与 Gain Map 输出，后续

后续 HDR 输出应支持两类：

```text
OpenEXR：保存 scene-linear HDR 或 display-referred HDR 浮点图
Gain Map Image：保存 SDR base + HDR gain map + metadata
```

建议 UI 中把导出目标分成：

```text
显示分享：SDR PNG/JPEG
算法调试：TIFF/OpenEXR
HDR 照片：SDR base + gain map
```

这样用户不会误把 8-bit SDR 结果当成完整 HDR 数据。

## 14. 多线程设计

### 14.1 基本原则

1. UI 线程只负责交互和显示。
2. pipeline 计算在后台线程执行。
3. 任务可取消。
4. 新参数变更到来时，取消旧预览任务。

### 14.2 任务类型

```text
LoadRawTask
PreviewPipelineTask
FullExportTask
GenerateHistogramTask
ExportStageTask
```

### 14.3 状态同步

后台任务完成后，通过 Qt signal/slot 通知 UI：

```text
previewReady(stageId, image)
pipelineError(stageId, error)
taskProgress(percent)
taskFinished()
```

## 15. 插件系统规划

### 15.1 第一阶段：内置注册

先做内部 stage registry：

```cpp
class StageRegistry {
public:
    void registerStage(std::unique_ptr<PipelineStage> stage);
    const PipelineStage* find(std::string_view id) const;
    std::vector<const PipelineStage*> allStages() const;
};
```

优点：

1. 简单。
2. 易调试。
3. 不引入 ABI、动态库加载和版本兼容问题。

### 15.2 第二阶段：动态 C++ 插件

插件需要声明：

```text
插件名称
版本
支持的 stage 类型
输入图像类型
输出图像类型
参数 schema
是否线程安全
```

风险：

1. C++ ABI 不稳定。
2. 不同编译器/运行库可能不兼容。
3. 崩溃隔离困难。

### 15.3 第三阶段：脚本插件

可考虑：

```text
Python 插件
WASM 插件
```

Python 适合算法研究者，但会带来打包、环境和性能问题。WASM 沙箱更干净，但图像大 buffer 传输需要认真设计。

## 16. 测试策略

### 16.1 单元测试

测试对象：

```text
BlackLevelStage
NormalizeStage
DemosaicStage
WhiteBalanceStage
ColorMatrixStage
ExposureStage
GammaStage
PipelineCache
```

测试内容：

1. 输入输出尺寸正确。
2. 输入输出类型正确。
3. 没有 NaN/Inf。
4. 简单输入下结果符合预期。
5. 参数修改后 cache invalidation 正确。

### 16.2 集成测试

准备固定 DNG 样张，执行完整 pipeline：

```text
RAW → sRGB PNG
```

检查：

```text
输出文件存在
尺寸正确
通道正确
无全黑/全白
无 NaN/Inf
histogram 合理
```

### 16.3 视觉回归测试

保存参考输出，后续修改算法后比较：

```text
平均绝对误差
最大误差
PSNR
SSIM，后续
```

### 16.4 色彩测试

使用 ColorChecker DNG：

```text
读取色块区域
计算白平衡误差
计算 ΔE，后续
比较不同 color matrix 策略
```

### 16.5 HDR 与动态范围测试

后续加入 HDR/gain map 后，需要测试：

```text
scene-linear 中间结果是否保留高光
tone mapping 是否避免异常色偏
SDR rendition 是否可独立正常显示
HDR rendition 是否保留高光层次
gain map 是否能重建接近 HDR rendition 的结果
metadata 是否完整写出
```

指标：

```text
高光区域误差
重建 HDR 与原始 HDR 的误差
SDR/HDR 直方图分布
clipping 像素比例
```

### 16.6 AI/Neural Stage 测试

后续加入 learned ISP 或 ONNX stage 后，需要测试：

```text
模型输入输出尺寸
tensor layout
归一化和反归一化
tile overlap 拼接痕迹
CPU/GPU backend 输出一致性
FP32/FP16 差异
模型加载失败时的错误提示
```

指标：

```text
PSNR / SSIM
LPIPS，后续
推理耗时
峰值显存/内存
模型大小
```

### 16.7 任务驱动评估，后续

如果软件后续用于 task-driven ISP，可以加入：

```text
检测 mAP
分割 mIoU
OCR 准确率
人脸/车牌识别准确率
运行时间
能耗，移动端后续
```

这部分不是 MVP，但应在架构上允许 `MetricStage` 或 `EvaluationPlugin` 接入。

## 17. 开发流程

### 17.1 阶段一：命令行核心闭环

目标：

```text
不做 GUI，先跑通 RAW 到 sRGB。
```

任务：

1. 建立 CMake 项目。
2. 集成 LibRaw。
3. 定义 `ImageBuffer` 和 `RawMetadata`。
4. 实现 Raw Decode。
5. 实现基础 stage。
6. 命令行导出每一步结果。

验收标准：

```text
给定一张 DNG，可以输出：
01_raw_debug.png
02_black_level.png
03_normalized.png
04_demosaic.png
05_white_balance.png
...
final_srgb.png
```

### 17.2 阶段二：Qt GUI MVP

目标：

```text
能打开文件，能看 stage，能显示中间图。
```

任务：

1. 建立 Qt 主窗口。
2. 加文件打开。
3. 加 pipeline stage 列表。
4. 加图像预览控件。
5. 加 metadata 面板。
6. 后台执行 preview pipeline。

验收标准：

```text
用户打开 DNG 后，左侧出现 stage 列表。
点击任意 stage，中间显示该阶段结果。
UI 不因处理大图而卡死。
```

### 17.3 阶段三：参数调节

目标：

```text
可调关键参数并局部重算。
```

任务：

1. 设计 `StageParamSchema`。
2. 参数面板自动生成控件。
3. 实现白平衡调节。
4. 实现曝光 EV 调节。
5. 实现 tone mapping 调节。
6. 实现 cache invalidation。

验收标准：

```text
调节曝光只重算曝光之后的 stage。
拖动滑条有低分辨率预览反馈。
最终导出使用全分辨率处理。
```

### 17.4 阶段四：导出与项目文件

目标：

```text
可保存工程，可导出结果。
```

任务：

1. 实现项目 JSON 保存/加载。
2. 实现最终图导出。
3. 实现当前 stage 导出。
4. 实现最近文件。

验收标准：

```text
关闭软件后重新打开项目，参数和 active stage 可以恢复。
导出的 PNG 能被系统图片查看器正常打开。
```

### 17.5 阶段五：质量提升

目标：

```text
提升算法质量和可用性。
```

可做：

1. 更好的 demosaic。
2. 简单降噪模块。
3. 3D LUT。
4. ICC profile。
5. ColorChecker 校准工具。
6. 性能统计。
7. 批量导出。

## 18. 关键风险与应对

### 18.1 色彩结果不准

风险：

RAW 到 sRGB 涉及白平衡、矩阵、白点、工作空间、tone、gamma。任何一步错了，图像都会偏色。

应对：

1. 每一步都显示中间结果。
2. metadata 面板明确显示使用了哪个矩阵。
3. 使用 ColorChecker 做测试。
4. 不承诺第一版与相机 JPEG 一致。

### 18.2 RAW 格式差异大

风险：

不同相机 RAW 格式、黑电平、压缩方式、CFA pattern、metadata 差异很大。

应对：

1. 第一版优先 DNG 和常见 Bayer RAW。
2. unsupported metadata 明确报错。
3. 保留 raw loading log。

### 18.3 性能不足

风险：

全分辨率 float32 pipeline 内存和计算量很大。

应对：

1. 预览和全分辨率分离。
2. 缓存中间结果。
3. 后台线程执行。
4. 后期加入 tile 和 SIMD/GPU。

### 18.4 架构过度设计

风险：

一开始就做动态插件、节点编辑器、GPU 和 AI，导致核心闭环迟迟跑不通。

应对：

1. 先命令行核心。
2. 再 GUI。
3. 再参数化。
4. 最后插件和优化。

### 18.5 UI 与算法耦合

风险：

如果算法逻辑写在 Qt widget 中，后续测试、命令行和插件都会困难。

应对：

1. ISP Core 不依赖 Qt。
2. Pipeline 不依赖 UI。
3. UI 只通过 controller 调用 pipeline。

## 19. MVP 验收清单

第一版完成时，应满足：

```text
[ ] 可以打开一张 DNG/RAW
[ ] 可以读取并展示基础 metadata
[ ] 可以执行基础 ISP pipeline
[ ] 可以显示每个 stage 的输出
[ ] 可以调整白平衡参数
[ ] 可以调整曝光 EV
[ ] 可以调整 tone mapping
[ ] 可以导出最终 sRGB PNG
[ ] 可以导出当前 stage 预览图
[ ] UI 处理时不卡死
[ ] 参数修改后只重算受影响阶段
[ ] 有至少 5 个核心 stage 的单元测试
```

## 20. 后续演进方向

### 20.1 算法方向

```text
更高质量 demosaic
RAW 域降噪
去模糊
局部 tone mapping
高光恢复
镜头 shading correction
畸变校正
ColorChecker 自动校准
HDR gain map generation
computational RAW inspection
scene-linear HDR rendering
```

### 20.2 工程方向

```text
tile-based pipeline
SIMD
GPU preview
OpenCL/Vulkan/Metal backend
DirectML backend
ONNX Runtime backend
动态插件
批处理
项目模板
性能 profiler
OpenEXR 中间结果导出
HDR/gain map metadata 写出
```

### 20.3 研究方向

```text
AI denoise stage
learned demosaic stage
learned ISP stage
RAW-to-sRGB 网络对比
Reverse ISP
pipeline stage sensitivity analysis
task-driven ISP optimization
multi-frame RAW burst pipeline
ProRAW / computational RAW analysis
```

### 20.4 现代 ISP 兼容路线

建议按以下顺序演进：

```text
第一阶段：传统单帧 Bayer RAW → SDR sRGB
第二阶段：OpenEXR scene-linear/HDR 中间结果
第三阶段：computational RAW / linear DNG 识别与 pipeline 模板
第四阶段：HDR gain map 预览与导出
第五阶段：ONNX Runtime neural stage
第六阶段：GPU/tile backend
第七阶段：多帧 RAW burst 与任务驱动 ISP
```

这个顺序的原则是：先保证传统 ISP 的可解释性，再扩展到现代计算摄影。不要一开始就用 AI 或多帧能力掩盖基础 pipeline 语义不清的问题。

## 21. 推荐最小实现顺序

最推荐的实际开发顺序如下：

```text
1. CMake 空项目
2. LibRaw 读取 DNG
3. ImageBuffer / RawMetadata
4. black level / normalize
5. bilinear demosaic
6. white balance
7. camera RGB → sRGB 简化矩阵
8. exposure
9. tone mapping
10. gamma
11. 命令行导出每一步
12. Qt 主窗口
13. pipeline 列表
14. 图像预览
15. 参数面板
16. 缓存与局部重算
17. 项目文件与导出
18. RawSourceKind 检测
19. SceneLinearRgb / SDR / HDR 类型拆分
20. OpenEXR 导出
21. ProcessingBackend 抽象接入
22. NeuralStage 空实现和项目文件兼容
```

这条路线最稳，因为每一步都有可验证输出。

其中 18 到 22 不要求马上实现完整功能，但建议在第一轮架构稳定后尽早补上。这样项目不会被传统 Bayer RAW 假设锁死。

## 22. 总结

这个项目的本质不是“写一个修图软件”，而是写一个可观察、可调试、可扩展的 ISP 实验台。

第一版应该围绕一个明确闭环：

```text
DNG/RAW 输入
→ 基础 ISP pipeline
→ 每一步可视化
→ 少数关键参数可调
→ 最终 sRGB 输出
```

同时，现代版本需要在架构上预留：

```text
computational RAW 识别
scene-linear / SDR / HDR 数据区分
HDR gain map 输出
ONNX/AI stage
GPU/多后端处理
任务驱动评估
```

技术上建议使用：

```text
C++20
Qt 6
CMake
vcpkg
LibRaw
LittleCMS
OpenCV
OpenImageIO，第二阶段
ONNX Runtime，后续
```

最重要的设计原则是：

1. 图像语义要清楚。
2. pipeline stage 要独立。
3. UI 和算法要解耦。
4. 预览和导出要分离。
5. 先跑通闭环，再追求高级算法和性能。
