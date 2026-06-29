# RAW 前端校正：BLC、DPC、LSC、噪声模型与隐式校正

## 模块定位

RAW 前端是 ISP 的地基，通常发生在 demosaic 之前：

```text
Sensor RAW
-> black level correction
-> bad/dead pixel correction
-> lens shading correction
-> noise model / gain handling
-> clean linear RAW for reconstruction
```

如果这一段做错，后面的 AWB、Demosaic、CCM、Denoise 都会被污染。AI-ISP 也一样，RAW 输入契约错了，模型再强也会学到错误分布。

## 传统做法

### Black Level Correction

传感器没有光照时仍然有偏置值。BLC 做的是：

```text
raw_corrected = max(raw - black_level, 0)
raw_norm = raw_corrected / (white_level - black_level)
```

不同相机、不同 ISO、不同通道可能有不同 black level。初学者最常犯的错误是把 RAW 当成天然 0 起点。

### Bad Pixel Correction

坏点可能是 hot pixel、dead pixel 或 stuck pixel。传统方法通常基于邻域检测：如果某个像素和同色邻域差异过大，就用邻域中值或方向插值替换。

### Lens Shading Correction

镜头和传感器会导致边缘亮度下降、颜色不均。LSC 通常用网格 gain map：

```text
corrected(x, y, c) = raw(x, y, c) * gain_map(x, y, c)
```

注意 LSC 会放大边缘噪声，因为暗角区域被乘了更大的 gain。

## 传统瓶颈

1. BLC 参数如果不准，暗部会有色偏或被截断。
2. DPC 如果过强，会把真实星点、纹理或高光误杀。
3. LSC 会放大噪声，尤其在低光边缘。
4. 噪声不是固定高斯，而是和信号、ISO、模拟/数字增益有关。

## 当前更先进的做法

### RAW-aware Neural ISP

近年的 Neural ISP 会把 black level、CFA pattern、曝光和局部亮度作为显式或隐式因素。例如 RMFA-Net 这类 RAW2RGB 方法强调 RAW 特性处理，包括 black level、CFA 和不均匀曝光。它的动机是：如果网络不知道 RAW 的物理结构，容易产生纹理和颜色问题。

### 隐式校正

有些 AI-ISP 不显式写 BLC/LSC，而是让网络从数据中学习校正。但工程上仍建议保留显式元数据和输入契约。隐式校正的风险是跨相机泛化差：训练相机的 black level 和测试相机不同，模型可能颜色漂移。

### 噪声模型驱动训练

先进 RAW 去噪通常不会只加固定 Gaussian noise，而会使用 shot noise + read noise：

```text
variance = a * signal + b
```

其中 `a` 与 photon shot noise 和 gain 有关，`b` 与 read noise 有关。这个模型比固定 sigma 更接近传感器。

## 工程注意点

- BLC 必须在归一化前做。
- LSC 后噪声分布改变，denoise 需要知道 gain map。
- 不同 CFA 的 pack 顺序必须固定并写入文档。
- 黑电平、白电平、ISO、曝光时间最好进入实验 manifest。
- AI 模型训练和部署必须使用同一套 RAW 前处理。

## 和本项目对应

- stage1：直接对应 BLC、DPC、LSC。
- stage2：对应 pseudo RAW、low-light、RAW-aware denoise。
- stage3：可把 BLC/LSC 写成 C++ 高性能模块。
- stage4：对应 CUDA `pack_raw`、normalize、输入 tensor 契约。

## 练习

1. 在 `stage1_soft_isp` 选择一张 RAW，分别输出未做 BLC、做 BLC、做 BLC+LSC 的暗部 crop 和直方图。
2. 在边缘区域观察 LSC 前后噪声是否被放大。
3. 写一个 YAML 输入契约：black_level、white_level、CFA、pack_order、normalize_range。
4. 在 stage2 模拟 shot/read noise，与固定 Gaussian noise 训练结果做对比。

## 你应该掌握

RAW 前端不是清理杂活，而是决定整条 ISP 是否物理可信的入口。先进 AI-ISP 也不能绕开 RAW 契约，只是把部分校正从显式规则变成可学习模块。

