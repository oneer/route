# Week 1：ImageBuffer / Layout / Border

## 1. 本周目标

Week 1 的目标是建立 C++ 图像算法模块的基础数据结构。后续 denoise、Tone Mapping、Local TM 和 HDR merge 都会依赖这套约定：

```text
ImageBuffer owns memory
ImageView references memory
row_stride describes row step
channel_stride describes plane step
border policy defines out-of-range access
```

这一步看似基础，但它直接决定后续模块能否处理奇数尺寸、padding、tile halo、多通道 layout 和 4K 输入。

## 2. ImageView 与 ImageBuffer

`ImageBuffer<T>` 是 owning container，负责持有内存。`ImageView<T>` 是 non-owning view，只描述如何访问一块图像内存。

这种拆分有两个好处：

- 算法函数可以只接收 `ImageView`，不关心内存由谁分配。
- 后续可以把整图、ROI、tile、临时 buffer 都统一成 view。

当前 Week1 实现的是 planar layout：

```text
offset = c * channel_stride + y * row_stride + x
```

其中 `row_stride` 允许大于 `width`。这点非常重要，因为真实图像工程里一行像素常常有 padding 或 alignment。

![Stride layout](figures/week1/stride_layout.png)

## 3. Planar4 的意义

阶段三后续会处理 RAW-like 数据。对于 Bayer RAW，可以把同色像素抽成四个平面：

```text
R / Gr / Gb / B
```

这种 `planar4` 表示不等价于普通 RGB 四通道，它更接近 ISP 前端常见的 Bayer-like 处理方式。好处是：

- 每个通道可以独立统计噪声和 gain。
- RAW denoise 可以避免直接混合不同颜色采样点。
- 四通道改造时更容易隔离状态变量。

![Planar4 layout](figures/week1/planar4_layout.png)

## 4. Border Policy

邻域算子必须定义越界访问方式。Week1 实现了：

| policy | 含义 | 常见影响 |
|---|---|---|
| constant | 越界返回固定值 | 边缘可能变暗或产生人工边界 |
| replicate | 使用最近边界像素 | 常用于滤波 baseline，稳定但可能拉平边缘 |
| reflect | 镜像反射 | 边缘更连续，但 Python/C++ 必须完全同定义 |

![Border policy](figures/week1/border_policy.png)

同一个 3x3 filter，如果 Python reference 用 reflect，而 C++ 用 replicate，主体区域可能一致，但边缘一圈会全部对不齐。这类问题肉眼不一定明显，却会导致 golden test 失败。

## 5. 本周实现

新增文件：

- `include/cpp_isp/image.hpp`
- `include/cpp_isp/border.hpp`
- `src/image.cpp`
- `src/border.cpp`
- `tests/test_image.cpp`
- `tests/test_border.cpp`
- `python_ref/visualize_week1_layout.py`

测试覆盖：

- `row_stride > width`
- `channel_stride`
- `planar4 indexing`
- bounds-checked access
- constant / replicate / reflect border mapping
- border sampling

## 6. 为什么这符合三年社招要求

三年社招 ISP 算法岗不会只问“会不会写卷积”。更常见的追问是：

- stride 不是 width 时你的代码是否还对？
- tile 处理边缘怎么和整图处理一致？
- RAW 四通道改造时状态变量怎么隔离？
- Python 和 C++ 边界策略不同怎么定位？
- 4K 输入下访问模式会不会破坏 cache locality？

Week1 的目标就是为这些追问建立代码和语言基础。

## 7. 面试复述要点

可以这样讲：

> 我在 C++ 工程里把 owning buffer 和 non-owning view 分开，算法模块只依赖 ImageView。ImageView 显式保存 width、height、channels、row_stride 和 channel_stride，不假设 stride 等于 width。对于 RAW-like 数据，我支持 planar4 layout，把 R/Gr/Gb/B 四个 Bayer-like 通道放在独立平面里。邻域算子通过统一 border policy 做越界访问，避免 Python reference 和 C++ 实现因为边界定义不同而对不齐。

常见追问：

1. **为什么 stride 不能默认等于 width？**
   因为真实图像 buffer 常有 padding、alignment 或 ROI view。默认等于 width 会导致跨行访问错误。
2. **planar 和 interleaved 哪个更好？**
   没有绝对。访问单通道或 RAW-like 四通道时 planar 更友好；逐像素 RGB 联合处理时 interleaved 可能更直接。
3. **border policy 为什么重要？**
   去噪、卷积、LTM 这类邻域算子的边缘输出完全由 border policy 决定。边界策略不一致会导致 reference 对齐失败。

## 8. 当前限制

- 当前只实现 planar layout，后续如果需要普通 RGB interleaved，可再增加 layout enum。
- 当前没有 aligned allocator，后续做 SIMD 时再补。
- 当前 border reflect 使用不重复边界的反射定义，后续 Python reference 必须保持同一口径。
