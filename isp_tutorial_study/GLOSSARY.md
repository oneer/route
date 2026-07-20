# ISP 核心术语表

| 术语 | 简明定义 | 常见误区 |
|---|---|---|
| RAW | 传感器数字测量及其 metadata，不是可直接显示照片 | “RAW 就是未压缩 RGB” |
| CFA/Bayer | 让不同像素采样不同光谱通道的滤色阵列 | 把 Bayer 单平面当灰度图或完整 RGB |
| Black level | 无有效光信号时的数字基线 | 把 BLC 当亮度调节 |
| White level | RAW 有效饱和上限 | 直接假设等于 `2^bit_depth-1` |
| BLC | 扣除黑电平并处理裁剪/位深 | 在 gain 之后再减同一个 black level |
| FPN | 随像素、行或列固定的空间噪声 | 和每帧随机噪声混为一谈 |
| PRNU | 像素光响应非均匀性 | 和镜头 shading 完全等同 |
| LSC | 用位置/通道相关 gain 修正镜头阴影和色偏 | 忽略四角噪声也会被放大 |
| DPC/BPC | 检测并修复缺陷像素 | 不看 CFA 相位就平均邻居 |
| Demosaic | 从 CFA 采样估计每像素 RGB | 认为只是普通放大插值 |
| Camera RGB | 相机传感器相关的 RGB 响应 | 直接当 sRGB 显示 |
| Linear RGB | 与光强近似线性关系的 RGB | 在 gamma 域做应在线性域完成的计算 |
| AWB | 估计光源并使中性物体回到中性 | 用 AWB 修复所有颜色误差 |
| CCM | 把 camera RGB 映射到目标颜色表示的矩阵 | 用通道增益代替混色矩阵 |
| OETF/Gamma | 面向编码/显示的非线性传输 | 简单理解为“调亮” |
| YCbCr | 数字视频常用亮度/色度编码 | 不区分标准矩阵和 full/limited range |
| HDR | 覆盖更大场景亮度范围的采集、融合和表示体系 | 和 tone mapping 混为一谈 |
| Tone mapping | 把高动态范围映射到目标显示/编码范围 | 只拉曲线而忽略局部 halo 和颜色 |
| 3A | AE、AF、AWB 的统计—控制闭环 | 把 3A 当单帧滤镜 |
| Line buffer | 为流式邻域计算缓存若干行 | 和整帧缓存混为一谈 |
| Tile | 将大图分块处理 | 忽略 overlap 和边界一致性 |
| Fixed-point | 用有限位宽近似实数计算 | 只看位数，不分析范围、舍入和饱和 |
| Golden reference | 用于对齐实现的参考模型/输出 | 假设 golden 永远正确 |
| Failure gallery | 按失败类型组织的局部视觉证据 | 只保留最好看的成功样例 |

