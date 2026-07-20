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

### 2.1 用一个小例子手算地址

假设图像参数如下：

```text
width = 3
height = 2
channels = 2
row_stride = 5
channel_stride = 10
```

内部 planar 地址公式为：

```text
offset(y, x, c) = c * channel_stride + y * row_stride + x
```

因此：

```text
offset(0, 0, 0) = 0
offset(1, 2, 0) = 0 + 1*5 + 2 = 7
offset(0, 0, 1) = 1*10 + 0 + 0 = 10
offset(1, 2, 1) = 10 + 5 + 2 = 17
```

每行只有前 3 个位置是有效像素，后 2 个是 padding。若错误地使用
`y * width + x`，第二行会从 offset 3 开始，读取到 padding；这种 bug 在
`row_stride == width` 的测试里完全不会暴露。

### 2.2 CPF32 与内部布局的转换

CPF32 payload 是连续 interleaved HWC：

```text
[R00, G00, R01, G01, R02, G02, R10, G10, ...]
```

而上面的 `ImageBuffer` 是 planar：

```text
channel 0: [R00, R01, R02, pad, pad, R10, ...]
channel 1: [G00, G01, G02, pad, pad, G10, ...]
```

所以文件读写层必须做 HWC ↔ planar 转换。CPF32 不携带 stride，不能把文件
payload 直接解释成带 padding 的内部 buffer。

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

## 4. 边界策略（Border Policy）

邻域算子必须定义越界访问方式。Week1 实现了：

| policy | 含义 | 常见影响 |
|---|---|---|
| constant | 越界返回固定值 | 边缘可能变暗或产生人工边界 |
| replicate | 使用最近边界像素 | 常用于滤波 baseline，稳定但可能拉平边缘 |
| reflect | 镜像反射 | 边缘更连续，但 Python/C++ 必须完全同定义 |

![Border policy](figures/week1/border_policy.png)

同一个 3x3 filter，如果 Python reference 用 reflect，而 C++ 用 replicate，主体区域可能一致，但边缘一圈会全部对不齐。这类问题肉眼不一定明显，却会导致 golden test 失败。

### 4.1 手算 reflect-101

本项目的 `reflect` 不重复端点，也就是常说的 reflect-101。对长度为 4 的一维
序列：

```text
index:     0  1  2  3
value:     A  B  C  D
extended:  C  B | A  B  C  D | C  B
index:    -2 -1 | 0  1  2  3 | 4  5
```

因此：

```text
reflect(-1) = 1
reflect(-2) = 2
reflect(4)  = 2
reflect(5)  = 1
```

它不同于重复端点的 symmetric 形式。特别地，`1x1` 图像的任意 reflect 访问都
必须落回唯一像素，否则容易出现死循环或负索引。

### 4.2 3×3 左上角采样比较

对左上角像素 `(0,0)` 使用半径 1：

| 访问位置 | replicate 映射 | reflect-101 映射 |
|---|---|---|
| `(-1,-1)` | `(0,0)` | `(1,1)` |
| `(-1,0)` | `(0,0)` | `(1,0)` |
| `(0,-1)` | `(0,0)` | `(0,1)` |

这解释了为什么 border 不一致时，误差通常先集中在图像边缘，而内部区域仍可能
完全一致。

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
- 带边界检查的访问；
- constant / replicate / reflect 映射；
- 边界采样。

### 5.1 公式到代码的对应关系

| 概念 | C++ 位置 | 阅读时检查什么 |
|---|---|---|
| owning storage | `include/cpp_isp/image.hpp` 的 `ImageBuffer` | 分配大小是否包含 stride/channel stride |
| non-owning access | `ImageView::operator()` / `at()` | 地址公式是否使用两个 stride |
| shape validation | `src/image.cpp` | width/height/channel 和 buffer 大小如何约束 |
| border index | `src/border.cpp` | constant、replicate、reflect 的分支和 1×1 情况 |
| layout visualization | `python_ref/visualize_week1_layout.py` | Python 示例是否与 C++ 地址公式一致 |

阅读代码时不要从类定义第一行顺读到底。先带着一个具体访问
`(y=1,x=2,c=1)`，追踪它最终访问哪个 offset。

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

## 9. 故障注入练习

### 练习 A：制造 stride bug

1. 在一个局部实验分支中，把地址计算临时改成 `y * width + x`。
2. 先运行连续图像测试，观察它为什么可能通过。
3. 再运行 `row_stride > width` 测试，记录第一个错误坐标。
4. 恢复代码，并解释为什么这个 bug 可能表现为斜纹、错行或通道污染。

### 练习 B：制造 border mismatch

1. 保持 Python reference 使用 reflect-101。
2. 临时让 C++ 邻域滤波使用 replicate。
3. 生成 error map，确认误差是否首先出现在边缘环带。
4. 比较 `1x1`、`3x3` 和 `17x19` 输入，解释哪一种最容易定位定义差异。

这些练习的目的不是“把测试弄红”，而是学习从误差空间分布反推 bug 类型。

## 10. 章末自测

1. `width=7, row_stride=12, channel_stride=60` 时，`(y=3,x=5,c=2)` 的 offset
   是多少？
2. 为什么 CPF32 文件不能保存 ROI view 的原始 stride？
3. `reflect(-1)` 与 `replicate(-1)` 分别映射到哪里？
4. 为什么一个只测试 `128x128` 连续图像的算法仍可能在相机 buffer 上崩溃？
5. planar4 的四个 plane 为什么不能简单解释成 RGBA？

答案检查：

1. `2*60 + 3*12 + 5 = 161`。
2. CPF32 只保存连续 HWC payload 和 shape；ROI/padding 是内部内存语义。
3. 对长度大于 1 的数组，本项目 reflect-101 映射到 1，replicate 映射到 0。
4. 真实 buffer 可能有 padding、ROI、奇数尺寸和不同 channel stride。
5. planar4 表达 Bayer-like `R/Gr/Gb/B` 采样面，不是带 alpha 的显示 RGB。

## 11. 关键词、参数与面试答案

| 关键词/参数 | 地址/语义 | 为什么存在 | 典型错误 |
|---|---|---|---|
| width/height/channels | 有效图像形状 | 决定合法坐标和处理量 | 混淆 width/height 导致转置或越界 |
| `row_stride` | 同通道相邻行起点的元素间隔 | 支持行 padding/对齐 | 错当 width 会读入 padding 或错行 |
| `channel_stride` | 相邻 planar 通道起点间隔 | 支持独立通道面与 padding | 错当 `width*height` 会跨通道错位 |
| interleaved/planar | HWC 像素交错 / CHW 通道连续 | 不同库和 kernel 偏好不同布局 | 只看 shape 不检查内存顺序 |
| reflect-101 | 边界外索引镜像且不重复端点 | 减少边缘突变 | 与 symmetric 混用导致整圈对齐误差 |
| ownership/view | Buffer 持有内存，View 只描述访问 | 避免复制并支持 caller-owned memory | view 生命周期超过 owner 产生悬空引用 |

面试追问“planar 是否一定更快”时，应回答：取决于算子访问模式、SIMD/cache、转换成本和后端；布局是合同，不是脱离 workload 的性能结论。

## 12. 数据流、结果与边界

```text
CPF32 contiguous HWC -> 显式转换 -> planar ImageBuffer/View
-> stride/border 访问 -> 算法 -> 显式转换回 CPF32
```

本周结果是地址手算、stride/padding、planar4 和 reflect-101 的测试通过。它证明内存访问合同，不证明 planar 在所有硬件上更快，也不包含 aligned allocator、SIMD 或零拷贝 ROI 的性能结论。

## 13. 从接口到实验的学习闭环

### 13.1 输入输出和 ownership 契约

| 对象 | layout / dtype | ownership | 生命周期与别名风险 |
|---|---|---|---|
| CPF32 payload | contiguous HWC / `float32` | `TensorF32` 持有读入数据 | 文件不保存 stride，读入后才可转换 |
| `ImageBuffer<float>` | planar，可带 row/channel stride | owning | buffer 销毁后，由它生成的 view 立即失效 |
| `ImageView<const float>` | 只读 planar view | non-owning | 调用者保证底层内存在整个算法调用期间有效 |
| `ImageView<float>` | 可写 planar view | non-owning | 输出必须容量足够；当前接口不承诺任意 in-place alias 安全 |

shape 只回答“有多少元素”，layout 和 stride 才回答“元素在哪里”。任何跨 Python/C++
问题都按 `shape -> dtype -> range -> layout -> stride -> border` 的顺序核对。

### 13.2 代码导航和复现

```text
python_ref/visualize_week1_layout.py
  -> 画出 stride/planar4/border 语义
include/cpp_isp/image.hpp
  -> ImageBuffer 分配与 ImageView 地址合同
src/border.cpp
  -> 越界索引映射
tests/test_image.cpp + tests/test_border.cpp
  -> odd shape、padding、1x1 与边界不变量
```

从仓库根目录运行：

```powershell
python .\stage3_cpp_isp\python_ref\visualize_week1_layout.py
ctest --test-dir .\stage3_cpp_isp\out\build\verify --output-on-failure
```

先查看三张示意图，再手算一个带 padding 的地址，最后让测试验证。Python 图只解释
语义，CTest 才验证 C++；两者不能互相替代。

### 13.3 正确性、性能/安全权衡和 Python-C++ 边界

- planar 对单通道扫描友好，但 RGB 逐像素处理可能增加多 plane 访问；没有 benchmark
  不能宣布它一定更快。
- view 避免复制，但把生命周期和 alias 责任交给调用者；安全性与性能存在取舍。
- padding/alignment 可能帮助后续 SIMD，也增加有效宽度与实际行跨度不一致的风险。
- Python reference 必须显式模拟 reflect-101；NumPy 的不同 pad mode 名称不能只凭字面
  判断等价。
- 本周没有 SIMD、aligned allocator、真实 Camera buffer 或吞吐结果，证据仅为
  `verified_synthetic` 的内存合同测试。

### 13.4 面试五问与学习验收

1. **概念：Buffer 和 View 的核心区别？** 前者拥有内存，后者只携带地址与访问合同。
2. **原理：为什么 offset 要包含两个 stride？** 行和通道起点都可能带 padding，
   `width*height` 只对紧密存储成立。
3. **参数：tile 宽高是否越大越好？** 不一定；要联合 halo 重复、cache、任务粒度和 tail
   测量，Week 4 才给出实测。
4. **调试：误差只在四边一圈意味着什么？** 优先检查 border 定义和半径；若呈错行，
   再查 row stride。
5. **系统：怎样把 caller-owned Camera buffer 接入？** 用只读/可写 view 描述地址、shape、
   stride 和 layout，并让 owner 覆盖调用生命周期；必要时显式转换，而不是强转指针。

- [ ] 能在纸上计算带 padding 的三通道 offset；
- [ ] 能解释 HWC 文件为何不能直接作为 planar view；
- [ ] 能画出 Buffer→View 的 ownership 关系；
- [ ] 能通过 error map 区分 border mismatch 与 stride bug；
- [ ] 能说明本周合同如何被 Week 2 的邻域滤波复用。
