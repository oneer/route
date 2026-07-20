# 第16章：3A算法与ISP协同


> 课程阶段：硬件架构、HDR、计算摄影与 3A　|　难度：入门 → 中级　|　优先级：核心
>
> 建议用时：3–4 小时阅读 + 2–4 小时实验　|　内容整理：2026-07-19

> **学习提醒**：先确认数据域、位深、输入输出和模块假设，再讨论算法效果。

本章学习结果：**把 AE、AF、AWB 看作带延迟和稳定性约束的闭环控制系统。**

## 1. 本章先解决什么问题

3A 是相机系统里最典型的闭环控制问题。它不是普通后处理滤镜，而是根据当前帧或前几帧的统计结果，反过来控制传感器、镜头和 ISP 参数。

3A 分别是：

```text
AE / AEC / AGC：Auto Exposure / Auto Exposure Control / Auto Gain Control，控制亮度。
AF：Auto Focus，控制焦点和清晰度。
AWB：Auto White Balance，控制白平衡和光源色偏。
```

本章最小链路是：

```text
输入：当前帧图像统计、直方图、分区亮度、RGB 统计、对焦评价值、场景/人脸/ROI 信息
处理：测光、光源估计、对焦搜索、控制器平滑、异常区域排除、场景切换判断
输出：曝光时间、模拟增益、数字增益、光圈/ND、镜头位置、WB gains、3A metadata
```

读完本章，至少要能回答：

- AE、AF、AWB 各自控制什么硬件或 ISP 参数。
- 为什么 3A 是跨帧闭环，而不是单帧滤波。
- 为什么 AE 不能只看平均亮度。
- 为什么 AWB 很容易被大色块和混合光源欺骗。
- 为什么 AF 需要清晰度评价函数和搜索策略。
- 为什么 3A 需要 hysteresis、平滑和场景切换逻辑。

## 2. 3A 的核心直觉：统计到控制的闭环

3A 的工作方式可以理解为：

```text
第 N 帧：ISP 统计亮度、颜色、清晰度
第 N 帧结束：3A 算法计算新参数
第 N+1 或 N+2 帧：新曝光、增益、白平衡、镜头位置生效
```

这带来两个重要特点：

- 3A 有延迟：当前看到的问题，通常只能在下一帧或后几帧修正。
- 3A 要稳定：如果每帧都猛烈调整，视频会亮度闪烁、颜色跳变、焦点来回拉。

因此 3A 不只是“算一个正确值”，而是要在这些目标之间折中：

```text
快：场景变化时尽快收敛。
稳：静态场景不要来回抖动。
准：目标亮度、白点、焦点要合理。
鲁棒：面对高光、暗区、大色块、运动、闪烁、混合光也不崩。
```

## 3. 3A 统计模块到底给什么

ISP 硬件通常会在像素流经过时同步产生统计数据，而不是把整帧交给 CPU 慢慢扫。常见统计包括：

| 统计类型 | 给谁用 | 内容 | 用途 |
|---|---|---|---|
| 亮度直方图 | AE | Y 或 luma 分布 | 判断过曝、欠曝、整体亮度 |
| 分区亮度均值 | AE | 网格区域平均亮度 | 中央重点、ROI、背光检测 |
| RGB 分区统计 | AWB | R/G/B 均值、计数 | 灰点检测、色温估计 |
| 饱和/裁剪统计 | AE/AWB | 过亮像素比例 | 排除不可信区域 |
| 高频/梯度能量 | AF | Sobel/Laplacian/contrast | 判断当前焦点是否清晰 |
| 人脸/ROI 信息 | AE/AWB/AF | 位置和权重 | 人脸优先曝光、肤色保护、对焦 |
| flicker 统计 | AE | 亮度随时间/行变化 | 防 50/60Hz 光源频闪 |

libcamera 的 IPA 架构和 Raspberry Pi Camera Algorithm and Tuning Guide 都把 3A 算法作为相机控制器的一部分：算法从 ISP 统计和 metadata 中读信息，再输出控制值。这说明 3A 是“算法 + 硬件统计 + 传感器/镜头控制”的协同系统。

## 4. AE：自动曝光不是简单调平均亮度

AE 的目标是让画面达到合适亮度，同时避免重要区域欠曝或过曝。它能控制的参数通常包括：

- exposure time：曝光时间。
- analog gain：模拟增益。
- digital gain：数字增益。
- aperture：光圈，很多手机/嵌入式相机固定。
- ND filter：某些系统有中性密度滤镜。
- frame duration：曝光时间受帧率约束。

最简单的 AE 可以看平均亮度：

```text
error = target_luma - current_luma
如果 current_luma 太低，提高曝光或增益
如果 current_luma 太高，降低曝光或增益
```

但平均亮度很容易失败：

- 逆光人像：背景很亮，平均亮度不低，但人脸很黑。
- 夜景车灯：少量高光很亮，平均策略可能压暗整幅图。
- 雪地：画面整体很亮，相机会误以为过曝而压暗，雪变灰。
- 黑色舞台：画面整体很暗，相机会拉亮，黑色变灰且噪声上升。

所以 AE 常用直方图、分区测光、ROI、人脸权重、highlight protection、shadow protection，而不是只看平均数。

## 5. 曝光时间、增益和噪声的取舍

提高亮度有几种方式，但代价不同。

| 控制量 | 好处 | 代价 |
---|---|---|
| 增加曝光时间 | 收集更多光子，SNR 更好 | 运动模糊、帧率受限 |
| 增加模拟增益 | 提高信号进入 ADC 前幅度 | 噪声也会增加，动态范围可能受影响 |
| 增加数字增益 | 实现简单，后端可调 | 不增加真实光子，放大噪声 |
| 开大光圈 | 更多光，SNR 更好 | 景深变浅，硬件不一定支持 |

AE 策略通常会优先增加曝光时间直到运动/帧率限制，再增加模拟增益，最后才依赖数字增益。但不同场景会调整优先级：

- 运动视频：不能太长曝光，否则拖影。
- 夜景静态：可以更长曝光或多帧融合。
- 车载：要避免 LED/交通灯饱和，也要控制运动模糊。
- 人脸场景：人脸亮度可能比背景更重要。

## 6. AE 收敛：快和稳的矛盾

AE 控制器通常不是一次跳到目标值，而是逐帧收敛。

一个简单 IIR 平滑：

```text
new_EV = alpha * calculated_EV + (1 - alpha) * old_EV
```

其中：

- `alpha` 大：响应快，但容易跳变和闪烁。
- `alpha` 小：稳定，但场景变化时反应慢。

还常用 hysteresis：

```text
如果亮度误差小于小阈值：不调整
如果亮度误差大于大阈值：快速调整
中间区域：缓慢调整
```

这样可以避免静态场景中因为统计噪声造成曝光来回抖。

## 7. Anti-flicker：为什么曝光时间要避开某些值

人工光源可能以电源频率闪烁。50Hz 地区和 60Hz 地区的灯光会造成图像亮度周期变化。如果曝光时间和闪烁周期不匹配，视频会出现明暗条纹或帧间闪烁。

常见策略是把曝光时间锁到 flicker 周期相关的安全点。例如：

```text
50Hz 电源：光强可能 100Hz 变化，周期约 10ms
60Hz 电源：光强可能 120Hz 变化，周期约 8.33ms
```

AE 不能只根据亮度选择任意曝光时间，还要考虑 anti-flicker 约束。真实系统可能提供 50Hz、60Hz、auto flicker detection 等模式。

## 8. AF：自动对焦是在找清晰度峰值

AF 控制镜头位置，让目标区域最清晰。不同相机可能支持：

- CDAF：Contrast Detection Auto Focus，对比度检测。
- PDAF：Phase Detection Auto Focus，相位检测。
- ToF/深度辅助。
- 混合 AF。

CDAF 的核心是：图像越清晰，高频越强，局部对比越大。常见 focus measure：

```text
FV = sum(|Sobel_x| + |Sobel_y|)
或
FV = sum(abs(Laplacian))
```

镜头从近到远移动时，FV 会先升后降，峰值附近就是最佳焦点。问题是 CDAF 不知道应该往哪个方向移动，常需要爬山搜索：

```text
移动镜头 -> 计算 FV -> 如果 FV 变大继续 -> 如果 FV 变小回退/缩步长
```

失败场景：

- 低纹理白墙：没有高频，FV 不可靠。
- 低光高噪：噪声也会增加高频。
- 运动物体：对焦过程中目标变了。
- 多主体：前景和背景抢焦点。
- 玻璃/反光：焦到错误平面。

## 9. PDAF 和混合 AF

PDAF 利用相位差估计 defocus 的方向和大小。直觉上，它不仅知道“当前清不清”，还可以知道“应该往近处还是远处调”。

优点：

- 速度快。
- 方向明确。
- 适合连续追焦。

缺点：

- 需要传感器支持 PDAF 像素。
- PDAF 像素需要校正和补偿。
- 低光、低纹理、强重复纹理仍可能失败。

混合 AF 通常用 PDAF 快速拉到附近，再用 CDAF 精细确认。这样兼顾速度和精度。

## 10. AWB：白平衡是欠定问题

AWB 的目标是估计光源颜色，让中性物体看起来中性。但 AWB 本质上很难，因为相机看到的颜色同时由光源、物体反射率、传感器响应决定。

同一个 RGB 观测可能来自：

```text
白色物体在暖光下
黄色物体在白光下
某种反射率物体在混合光下
```

所以 AWB 是欠定问题，没有单帧完全可靠解。常见方法靠假设和统计：

- Gray World：平均反射接近灰。
- White Patch/Max-RGB：最亮点接近白。
- Shades of Gray：灰世界和白点之间的泛化。
- Gray Edge：边缘/导数统计接近中性。
- Gray pixel/gray surface identification：寻找更可信灰点。
- 学习型 AWB：从数据学习光源估计和场景先验。

Xiong、Funt 等的灰表面识别资料强调了自动白平衡中寻找可信中性区域的重要性；libcamera 和 Raspberry Pi 调参资料也体现了 AWB 算法、模式和 tuning 文件在真实相机栈中的工程角色。

## 11. AWB 为什么容易被大色块欺骗

灰世界假设在很多自然场景里有用，但在大色块场景会失败：

- 草地占满画面：算法误以为光源偏绿，可能把图调成偏洋红。
- 蓝天占满画面：算法误以为光源偏蓝，可能加暖。
- 红墙或红衣服占大面积：算法误以为光源偏红。
- 舞台彩灯：光源本来就是彩色，不一定应该拉成白光。

所以 AWB 需要候选灰点过滤：

- 排除饱和像素。
- 排除过暗噪声区。
- 排除高饱和颜色。
- 使用 chromaticity 范围约束。
- 对人脸/肤色做保护。
- 对色温轨迹做限制。
- 用时域平滑防止颜色跳变。

## 12. 3A 之间会互相影响

3A 不是三个孤立模块。

AE 影响 AWB：

- 曝光不足时，暗部噪声大，RGB 统计不可靠。
- 高光饱和时，通道比例被截断，AWB 会误判。

AWB 影响 AE：

- WB gains 改变 RGB/Y 关系，可能影响亮度统计和高光保护。

AE 影响 AF：

- 曝光太短或增益太高，AF 的高频评价被噪声干扰。
- 曝光太长，运动模糊降低清晰度。

AF 影响 AE/AWB：

- 对焦区域通常也是测光和白平衡的重要 ROI。
- 人脸对焦后，AE 可能要人脸优先。

因此真实系统常有 3A manager 或 controller 统一协调：

```text
先保证 AE 进入合理范围 -> AWB 统计更可靠 -> AF 评价更稳定
场景切换时快速收敛 -> 稳定后慢速平滑
人脸/ROI 出现时重新分配权重
```

## 13. 3A 统计区域和权重

统计区域设计非常关键。一个常见方式是把画面分成网格：

```text
16x12 或 32x24 统计网格
每个 cell 统计亮度、RGB、饱和像素、focus measure
```

然后不同算法使用不同权重：

- AE：中心重点、人脸重点、避免高光主导。
- AWB：只选择灰点候选和可信区域。
- AF：选择中心 ROI、人脸眼睛、触摸对焦区域。

统计区域要考虑：

- 黑边/无效区域不要统计。
- 过曝区域通道比例不可信。
- 暗噪声区域不适合 AWB。
- 运动区域不适合 AF 或多帧稳定。
- 统计结果要和 crop、scaler、EIS 后坐标对齐。

## 14. 3A 的时域稳定

视频中的 3A 最怕闪烁和抽动：

- AE 每帧小幅变化 -> 亮度呼吸。
- AWB 每帧变化 -> 色温漂移。
- AF 来回搜索 -> 画面清晰度抽动。

稳定手段：

- hysteresis：小误差不动。
- IIR/低通滤波：参数逐帧平滑。
- scene change detection：场景大变时允许快速收敛。
- lock：拍照或录制关键时刻锁定部分 3A。
- convergence state：区分 searching、converging、stable。
- confidence：统计不可信时不盲目更新。

这里的核心是：3A 算法要像控制系统，而不是每帧独立优化器。

## 15. 最小可验证实验

实验 1：AE 直方图与平均亮度。

1. 准备逆光人像、雪地、夜景车灯三类图。
2. 计算平均亮度和亮度直方图。
3. 比较“只看平均”和“看 ROI/高光比例”的曝光决策。
4. 记录哪个场景平均亮度会误导 AE。

实验 2：AWB 灰世界失败。

1. 准备草地、蓝天、普通室内图。
2. 用全图灰世界计算 WB gains。
3. 再排除高饱和像素和过暗/过亮区域后计算。
4. 对比输出颜色。

实验 3：AE 跨帧收敛。

1. 模拟一段亮度从暗到亮变化的序列。
2. 用不同 `alpha` 做曝光参数平滑。
3. 比较响应速度和闪烁程度。
4. 加 hysteresis 后观察小幅抖动是否减少。

实验 4：AF focus curve。

1. 准备一组不同模糊程度的图。
2. 计算 Sobel 或 Laplacian focus value。
3. 绘制 lens position vs focus value 曲线。
4. 观察峰值和噪声对曲线的影响。

实验 5：3A 联动。

1. 选择一张低光高噪图。
2. 改变曝光/增益后计算 AWB 统计和 AF focus value。
3. 观察 AE 变化如何影响 AWB/AF 可信度。

## 16. 错误现象排查表

| 现象 | 可能原因 | 排查方向 |
|---|---|---|
| 画面忽明忽暗 | AE 平滑不足、hysteresis 太小 | 看 EV 曲线和亮度误差 |
| 逆光人脸很黑 | AE 权重被亮背景主导 | 增加人脸/ROI 权重，高光保护 |
| 雪地变灰 | AE 把高亮场景误判为过曝 | 场景识别或曝光补偿 |
| 颜色来回跳 | AWB 统计不稳或时域滤波不足 | 看 WB gains 曲线和灰点数量 |
| 草地/蓝天偏色 | 灰世界被大色块欺骗 | 排除高饱和区域，限制色温轨迹 |
| AF 来回拉风箱 | CDAF 搜索策略不稳或低纹理 | 检查 FV 曲线、ROI 和搜索步长 |
| AF 错焦到背景 | ROI 或主体检测错误 | 检查对焦窗口和人脸/主体权重 |
| LED 灯下条纹闪烁 | anti-flicker 曝光时间不匹配 | 检查 50/60Hz 和曝光时间档位 |
| 拍照首帧颜色异常 | 3A 未收敛就 capture | 检查 convergence state 和 lock 逻辑 |

## 17. 常见误区

- 误区 1：AE 就是让平均亮度到 128。真实 AE 要考虑 ROI、直方图、动态范围、噪声和运动。
- 误区 2：AWB 可以让所有场景颜色正确。AWB 是欠定问题，必须依赖假设和场景策略。
- 误区 3：AF 只要找最大锐度。噪声、纹理、主体选择和搜索策略都会影响 AF。
- 误区 4：3A 每帧算最优就好。视频里稳定性和收敛轨迹同样重要。
- 误区 5：统计越多越好。统计区域、排除规则、精度和延迟更关键。
- 误区 6：AE/AWB/AF 可以独立调。它们会互相影响，需要联动策略。
- 误区 7：AI 3A 能自动解决所有场景。数据偏差、可解释性、时域稳定和失败兜底仍然必要。

## 18. 学习优先级

必须掌握：

- AE、AF、AWB 的输入统计和输出控制量。
- 3A 跨帧闭环和帧延迟。
- AE 的直方图、测光权重、曝光时间/增益取舍。
- AF 的 focus measure、CDAF/PDAF/混合 AF 直觉。
- AWB 的灰世界、白点、灰点候选和失败场景。
- hysteresis、IIR 平滑、scene change 的作用。

了解即可：

- PID、LUT、模型预测和学习型 AE。
- Gray Edge、Shades of Gray、灰表面识别和学习型 AWB。
- PDAF 像素校正、lens driver、VCM 控制。
- 3A 统计硬件、DMA、metadata 和 tuning 文件。

后面再回看：

- 3A 与 HDR、夜景、多摄、计算摄影的联动。
- 车载/机器人中的任务驱动曝光和白平衡。
- libcamera/Raspberry Pi IPA 算法实现和调参体系。
- 学习型 3A 的数据闭环和在线稳定性。

## 19. 自测题

1. 为什么 3A 是闭环控制，而不是后处理滤镜？
2. AE 为什么不能只看平均亮度？
3. 曝光时间、模拟增益、数字增益分别有什么代价？
4. anti-flicker 为什么会限制曝光时间？
5. CDAF 的 focus value 为什么在最佳焦点附近有峰值？
6. PDAF 相比 CDAF 的优势是什么？
7. AWB 为什么是欠定问题？
8. 灰世界 AWB 在草地和蓝天场景为什么容易失败？
9. AE、AWB、AF 之间至少举出两个互相影响的例子。
10. 如何设计实验观察 AE 平滑参数过大或过小的后果？

## 20. 读完本章的验收标准

合格的学习结果应该是：

- 口头解释：能讲清 3A 如何从 ISP 统计到传感器/镜头/ISP 参数控制形成闭环。
- 输入输出：能写出 AE、AF、AWB 各自输入统计和输出控制量。
- 控制理解：能解释帧延迟、收敛速度、hysteresis、IIR 平滑和 scene change。
- 现象排查：能根据亮度闪烁、白平衡跳变、拉风箱、逆光欠曝提出原因。
- 工程判断：能说明统计窗口、ROI、饱和排除、灰点过滤和联动策略的重要性。
- 实验验证：能用直方图、灰世界、focus value 曲线和跨帧参数曲线验证 3A 行为。

## 21. 推荐资料与进一步阅读

- [Raspberry Pi Camera Algorithm and Tuning Guide](https://datasheets.raspberrypi.com/camera/raspberry-pi-camera-guide.pdf)：系统讲解 AGC/AEC、AWB、AF、ALSC 等相机算法和 tuning 方式。
- [libcamera IPA 文档](https://libcamera2.stefanklug.com/docs/guides/ipa.html)：理解开源相机栈中 Image Processing Algorithm 模块如何组织。
- [libcamera IPU3 AGC 文档](https://www.libcamera.org/api-html/classlibcamera_1_1ipa_1_1ipu3_1_1algorithms_1_1Agc.html)：可参考均值亮度式 AGC/AE 算法接口和统计处理方式。
- [Automatic White Balancing via Gray Surface Identification](https://www.cs.sfu.ca/~colour/publications/CIC-2007/index_CIC15_XIONG_PG143.html)：理解灰点/灰表面识别在 AWB 中的作用。
- [Grey-Edge and Shades of Gray Color Constancy 相关资料](https://www.researchgate.net/publication/272590702_Grey-wavelet_unifying_grey-world_and_grey-edge_colour_constancy_algorithms)：了解灰世界、灰边和颜色恒常性方法谱系。
- [Automatic exposure control for video cameras towards HDR techniques](https://research.tue.nl/en/publications/automatic-exposure-control-for-video-cameras-towards-hdr-techniqu)：自动曝光控制与 HDR 相关策略资料。
## 复习入口

- [ISP 核心术语表](../GLOSSARY.md)
- [章节到工程项目映射](../PROJECT_MAPPING.md)

## 本章学习闭环

- 配套实验：[lab07-HDR计算摄影与3A稳定性.md](../labs/lab07-HDR计算摄影与3A稳定性.md)
- 视觉案例：[ISP 视觉图谱](../VISUAL_ATLAS.md)
- 自测答案与评分：[本章答案要点](../answer_keys/chapter16-第16章：3A算法与ISP协同.md)
- 项目落点：
  - [统计模块](../../stage1_soft_isp/soft_isp/stats.py)
- [高级 AWB](../../stage1_soft_isp/soft_isp/awb_advanced.py)
- [相机系统采集协议](../../camera_system_capstone/reports/capture_protocol.md)
- 原始资料：[原教程正文归档](../source_archive/chapter16-第16章：3A算法与ISP协同.md)

导航：[上一章](./chapter15-第15章：计算摄影与高级ISP功能.md) · [下一章](./chapter17-第17章：高通SpectraISP架构深度剖析.md) · [完整课程索引](../full_content_index.md)
