# OpenISP 模块参考笔记

本笔记用于回答一个问题：当前 Week1-4 的学习版 ISP 算法比较简单，引入 OpenISP 模块后，哪些点值得吸收进报告和后续升级路线？

## 总体判断

OpenISP 的价值不在于直接替换当前 `soft_isp/` 里的学习版实现，而在于提供了更接近传统 ISP 模块表的参考：

```text
BLC -> AAF -> DPC -> BNF/CNF/NLM -> AWB Gain -> CFA(Malvar) -> CCM -> CSC -> Gamma/LUT -> EE/FCS/BCC/HSC
```

当前项目 Week1-4 主要覆盖了 RAW 读取、BLC、DPC、Demosaic、AWB、CCM、Tone/Gamma。OpenISP 额外提醒我们：传统 ISP 里还会有 RAW 域抗混叠、RAW/Chroma 降噪、假彩抑制、锐化、亮度/对比度/色相/饱和度控制，以及更工程化的 LUT/fixed-point 实现。

## Week1-4 如何结合 OpenISP 学

| 周次 | 当前项目角色 | OpenISP 参考角色 | 应补充的学习目标 |
|---|---|---|---|
| Week1 | 建立 RAW metadata、Bayer pattern、histogram、ROI 坐标系 | 为所有 OpenISP 模块提供参数解释基础 | 从“会读 RAW”升级为“知道每个模块为什么需要这些 metadata” |
| Week2 | BLC / DPC / LSC 前端校正 | `blc.py`、`dpc.py`、`aaf.py`、`bnf.py`、`cnf.py`、`nlm.py` | 认识前端不只有扣黑和坏点，还包括抗混叠与多类降噪 |
| Week3 | Bilinear Demosaic + Gray World AWB | `cfa.py` Malvar、`awb.py` RAW 域 WB gain | 把 Bilinear/AWB 当 baseline，再理解 Malvar 和 RAW 域 gain 控制 |
| Week4 | CCM / Tone / Gamma 显示输出 | `ccm.py`、`csc.py`、`gac.py`、`eeh.py`、`fcs.py`、`bcc.py`、`hsc.py` | 从“能显示”升级为“知道后端 IQ 风格、锐化和假彩控制” |

## 可参考模块

| OpenISP 模块 | 对应问题 | 对当前项目的启发 |
|---|---|---|
| `aaf.py` | RAW 域 anti-aliasing | Demosaic 前可以对同色 Bayer 采样做温和低通，降低后续假彩和拉链伪影 |
| `blc.py` | per-channel BLC + alpha/beta 串扰修正 | 当前 BLC 只扣 black level；报告应补充绿色通道串扰/OB 校正是更工程化方向 |
| `dpc.py` | 坏点检测 + 梯度方向修复 | 当前 DPC 用同色 median；OpenISP 展示了按最小梯度方向修复以保护边缘 |
| `bnf.py` | RAW 域 bilateral denoise | 降噪不只是 DPC，RAW 域还可按空间距离和像素差异加权，保护边缘 |
| `cnf.py` | Chroma noise filtering | 色噪可以单独检测/抑制，尤其和 AWB gain、暗部亮度相关 |
| `nlm.py` | Non-local means denoise | 可作为传统非局部降噪参考，但计算量很大，适合离线理解不适合直接纳入主脚本 |
| `awb.py` | Bayer RAW 域 WB gain control | AWB 可以在 demosaic 前做 per-Bayer-position gain，而当前项目是在 RGB 域估计 Gray World |
| `cfa.py` | Malvar demosaic | 当前 bilinear 是 baseline；Malvar 使用更大的校正核，能作为 Week3 的进阶 demosaic 对照 |
| `ccm.py` / `csc.py` | fixed-point 矩阵和颜色空间转换 | 产品 ISP 常用整数缩放和 offset，而不是只用浮点矩阵 |
| `gac.py` | Gamma LUT | 产品实现常用 LUT，而不是逐像素 `pow` |
| `eeh.py` | Edge enhancement | Demosaic 后通常还需要锐化，但要配合阈值和限幅避免 halo |
| `fcs.py` | False color suppression | 假彩抑制是 demosaic 后的重要补救模块，当前项目还没有覆盖 |
| `bcc.py` / `hsc.py` | 亮度/对比度/色相/饱和度控制 | 这些更偏显示风格和调参，不应混同于 RAW 域物理校正 |

## 需要写进报告的补充点

1. **当前 Week1-4 是骨架，不是完整传统 ISP。** 它覆盖主干数据域转换，但没有覆盖完整 IQ 调参链路。
2. **Demosaic 之前可以有更多 RAW 域模块。** AAF、BNF、CNF、NLM 都说明前端不仅是 BLC/DPC/LSC。
3. **DPC 可以按方向修复。** median 简单稳健，但强边缘处容易抹细节；梯度方向修复更像工程策略。
4. **Bilinear demosaic 应升级到 Malvar/AHD 类方法。** OpenISP 的 `cfa.py` 是一个很好的下一步参考。
5. **AWB 的位置可以不同。** 当前项目在 RGB 域做 Gray World；OpenISP 展示了 RAW/Bayer 域直接乘 R/Gr/Gb/B gain 的实现。
6. **产品实现会考虑 fixed-point 和 LUT。** CCM、CSC、Gamma 在 OpenISP 中都有整数缩放或 LUT 痕迹，这对 C++/端侧部署很重要。
7. **后处理也是 ISP 的一部分。** 锐化、假彩抑制、亮度/对比度/饱和度控制不是“美颜”，而是最终 IQ 风格和伪影控制的一部分。

## 不建议直接照搬的原因

OpenISP 里的很多模块是逐像素 Python 循环，适合读算法，不适合直接作为当前项目主 pipeline 的生产实现。部分模块还依赖固定参数、fixed-point 缩放和 8-bit 假设，和当前 `rawpy` DNG 输入、float32 中间结果并不完全一致。

因此更稳的做法是：

```text
先在报告中把 OpenISP 作为“进阶参考”
-> 再挑一个模块做独立实验
-> 最后再决定是否纳入主 pipeline
```

## 后续最值得做的三个小闭环

1. **Malvar demosaic 对比实验**
   - 输入：BLC/DPC/LSC 后 RAW
   - 对比：Bilinear vs Malvar vs rawpy reference
   - 指标：边缘 crop、假彩区域、PSNR/SSIM

2. **RAW 域 AAF / BNF 消融**
   - 输入：Demosaic 前 RAW
   - 观察：纹理区假彩是否降低，细节是否被抹
   - 风险：低通过强导致解析力下降

3. **假彩抑制和锐化后处理**
   - 输入：Demosaic + AWB + CCM 后 RGB/YUV
   - 观察：边缘彩边、halo、纹理锐度
   - 风险：指标提升不一定代表主观更好，需要 crop 和主观评价
