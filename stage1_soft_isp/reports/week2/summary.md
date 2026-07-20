# Week 2 学习总结：BLC / DPC

## 本周学习闭环

| 项目 | 要求 |
|---|---|
| 目标 | 解释 BLC、DPC、学习版 LSC 的物理来源、处理顺序、参数方向和失败传播 |
| 前置 | 能从 Week 1 metadata 得到 Bayer pattern、逐通道 black level 和 white level |
| 运行前预测 | 预测 black level 过扣/欠扣、DPC 阈值变大、LSC edge gain 变大分别会发生什么 |
| 最小实验 | 对 T01 生成 BLC histogram 和 DPC mask/crop；再用合成坏点评价 recall/误检 |
| 验收 | BLC 不发生无符号下溢；注入坏点 recall 可计算；能指出强边缘误检风险 |

```powershell
python scripts/06_apply_blc.py data/raw/T01_a0006-IMG_2787.dng `
  --out-dir outputs/tutorial/week2/blc `
  --report outputs/tutorial/week2/blc_report.md
python scripts/07_apply_dpc.py data/raw/T01_a0006-IMG_2787.dng `
  --out-dir outputs/tutorial/week2/dpc `
  --report outputs/tutorial/week2/dpc_report.md
python exercises/week2_dpc_injection.py
```

练习脚本故意保留 `NotImplementedError`，应先独立补全。仓库已有实测扫描见[RAW 质量审计的 DPC 参数扫描](../feasible_raw_quality_audit.md#dpc-参数扫描)，不要把下面的练习模板误认为实测结论。

Week2 的目标是做 RAW 前端校正。前端校正发生在 Demosaic 之前，仍然工作在单通道 Bayer RAW 上。本周已经完成 BLC、DPC 和一个学习用径向 LSC baseline。LSC 不是产品标定版，但已经把镜头阴影校正放回了正确的数据域和 pipeline 位置。

## 本周 Pipeline 位置

```text
RAW
  -> BLC：扣除传感器黑电平偏置
  -> DPC：检测并修复坏点候选
  -> LSC：补偿位置相关亮度/色偏
  -> 后续 AAF / BNF / CNF / Demosaic / AWB
```

## 已完成交付物

| 模块 | 代码 | 报告 | 输出 |
|---|---|---|---|
| BLC | `soft_isp/blc.py`、`scripts/06_apply_blc.py` | `reports/week2/blc_report.md` | `reports/figures/*_blc_*.png/json` |
| DPC | `soft_isp/dpc.py`、`scripts/07_apply_dpc.py` | `reports/week2/dpc_report.md` | `reports/figures/*_dpc_*.png/json` |
| LSC | `soft_isp/lsc.py`、`scripts/14_apply_lsc.py` | `reports/week2/lsc_report.md` | `reports/figures/*_lsc_*.png/json` |

## BLC 学到了什么

BLC 的全称是 Black Level Correction，黑电平校正。RAW 像素值里包含真实光信号，也包含传感器和读出电路的基线偏置。这个偏置就是 black level。

本周实现的核心公式是：

```text
corrected = raw - black_level
corrected = clip(corrected, 0, white_level - black_level)
```

如果 black level 为 0，BLC 前后应该基本不变；如果 black level 不为 0，暗部会整体向 0 移动。BLC 后有效白电平也要同步变成 `white_level - black_level`。

这里的“基本不变”只指减黑位部分是 identity；实现仍可能按 `white_level` 截断高于有效白电平的码值。因此验证 BLC 不能只比较 p50，还要分别检查低端归零比例、高端 clipping 比例和每个 Bayer 位置的变化。

## DPC 学到了什么

DPC 通常指 Defective Pixel Correction，坏点检测与修复；坏点既可能是 dead pixel，也可能是 hot、stuck 或响应异常像素。它的目标不是让图马上变好看，而是避免孤立异常点在后续 Demosaic 中扩散成彩色伪影。

Bayer RAW 中相邻像素不是同色，所以 DPC 不能直接拿上下左右像素比较。本周做法是：

```text
按 Bayer pattern 拆成 R / Gr / Gb / B 四个同色平面
  -> 每个同色平面做 3x3 median
  -> residual = abs(pixel - local_median)
  -> residual 超过阈值则标记为坏点候选
  -> 用 local_median 替换候选点
```

阈值由两部分共同决定：

```text
threshold = max(min_delta, median(residual) + mad_k * MAD(residual))
```

这样做可以同时保留一个固定最低门槛，并根据图像局部噪声水平自适应调整。

## 本周验证标准

1. BLC 后暗部基线应向 0 移动。
2. black level 为 0 的样张应基本不变，用来验证流程没有破坏数据。
3. DPC 候选点数量应很稀疏，不能大面积误检。
4. DPC mask 要叠到图上看，确认候选点是否集中在强边缘、高光或纹理区域。
5. DPC 修复 crop 要检查修复前后是否合理。

## LSC 学到了什么

LSC 的全称是 Lens Shading Correction，镜头阴影校正。它主要处理中心亮、边缘暗，以及不同 Bayer 通道位置相关响应不一致的问题。当前实现使用保守径向 gain map：

```text
gain(center) = 1
gain(edge)   = edge_gain
raw_lsc      = raw * gain_map
```

这能帮助理解 LSC 应放在 Demosaic 前，但它不能替代积分球或均匀白场标定。

三个模块可以用同一组问题检查：

| 模块 | 它修正的来源 | 为什么放在这里 | 参数或 metadata 错误时 | 最小验证 |
|---|---|---|---|---|
| BLC | 传感器、ADC 和读出链路的黑位偏置 | 先建立正确零点，避免污染 DPC、LSC 和 AWB | 欠扣使暗部发灰，过扣造成暗部 clip 和颜色偏移 | per-position 小数组测试；比较暗部 histogram 和 clipping |
| DPC | 稀疏 hot/dead pixel 或异常读出点 | 必须在 Demosaic 前处理，避免单点扩散到 RGB 邻域 | 阈值太低误伤纹理，太高漏掉坏点 | 注入已知坏点，计算 precision/recall，再检查强边缘 crop |
| LSC | 镜头和像素角度响应导致的中心—边缘亮度/颜色不均匀 | Bayer RAW 域仍能对四个位置独立补偿 | gain 太大放大边缘噪声，错误场景估计会把真实光照当暗角 | identity gain、合成 flat-field、四通道中心/边缘残差 |

这张表区分了“算法有没有运行”和“算法有没有修对问题”。最终图变亮或候选点变少都不是充分证据；验证必须针对模块原本要修正的物理来源。

## 本周局限

1. 当前 DPC 是学习用候选检测，不是工厂坏点表。
2. 强边缘、高光饱和、纹理区域可能被误检。
3. 当前 LSC 是学习用径向模型，不是标定 gain map；它可能把真实场景亮度变化误当成镜头暗角。
4. BLC/DPC 都在 Bayer RAW 上工作，不能用最终视觉效果单独评价。

## 深度补强：验证前端校正是否真的可靠

Week2 的 BLC/DPC/LSC 已经能跑通，但产品级前端校正更关心“阈值是否稳、误检是否少、标定是否真实”。

### 1. BLC 误差会向后传播

BLC 不是孤立模块。black level 扣多或扣少，会影响后面的 DPC、AWB、CCM 和暗部观感。

建议增加 BLC 误差传播实验：

| 实验 | 设置 | 观察 |
|---|---|---|
| 欠扣 | `black_level - 10` | 暗部是否发灰，AWB gain 是否变化 |
| 正常 | metadata black level | 作为基准 |
| 过扣 | `black_level + 10` | 暗部是否 clip，阴影细节是否丢失 |

重点不是这几个数字本身，而是理解：

```text
黑位错误会改变暗部噪声分布，DPC 的阈值和 AWB 的通道统计都会被污染。
```

### 2. DPC 需要参数敏感性和注入坏点验证

现有 DPC mask 和 repair crop 能说明算法在工作，但还不能说明 recall / false positive。

建议做一个最小可复现实验：

```text
选择若干非边缘像素
  -> 人工注入 hot pixel 或 dead pixel
  -> 跑 DPC
  -> 统计找回多少注入点，以及误检多少正常点
```

参数扫描练习模板（由学习者填写；当前仓库实测采用 `min_delta × mad_k` 更完整网格）：

| `mad_k` | 检测点数 | 注入点召回率 | 误检风险 | 结论 |
|---:|---:|---:|---|---|
| 1.0 | 待填写 | 待填写 | 高 | 可能过敏感 |
| 2.0 | 待填写 | 待填写 | 中 | 候选 |
| 3.0 | 待填写 | 待填写 | 低 | 可能漏检 |
| 4.0 | 待填写 | 待填写 | 很低 | 保守 |

这样 DPC 的验证就不只依赖全图指标，因为坏点通常很稀疏，全图 PSNR/SSIM 很难反映它的价值。

### 3. DPC 边界和强边缘要单独看

DPC 最容易误伤：

- 高对比边缘；
- 星点和灯光；
- 细密纹理；
- 饱和高光附近；
- 图像边界。

报告里应该固定放 100% crop，分别看：

```text
坏点区域 / 强边缘区域 / 高频纹理区域 / 高光区域
```

这样才能回答“它修的是坏点，还是把真实细节当坏点修掉了”。

### 4. LSC 必须区分学习模型和真实标定

当前径向 LSC 和 Week6 synthetic flat-field 适合学习概念，但不是产品标定。

真实 LSC 流程应写清楚：

1. 拍摄均匀白场或积分球；
2. 多帧平均降低随机噪声；
3. 按 R/Gr/Gb/B 四通道分别估计 shading；
4. 生成 mesh gain LUT；
5. 插值到全图；
6. 验证中心、边缘、四角残差。

建议产品级目标写成：

```text
flat-field 校正后，中心到边缘亮度残差尽量控制在 2%-5% 以内。
```

## 结合 OpenISP 后的补充理解

OpenISP 让 Week2 的前端校正视野更完整。我们当前实现的是“最小可解释前端”：BLC、DPC、LSC；OpenISP 里还出现了 RAW 域抗混叠和降噪模块，说明 Demosaic 前通常还有更多清理工作。

| 模块 | 我们当前实现 | OpenISP 参考 | 可以补进报告的点 |
|---|---|---|---|
| BLC | 按 metadata 扣 per-channel black level | `blc.py` 额外包含 `alpha/beta` 绿色通道串扰修正 | 工程 BLC 不一定只是减常数，还可能处理读出通道串扰或 OB 校正 |
| DPC | 同色平面 3x3 median + MAD 阈值 | `dpc.py` 用 5x5 同色邻域，并可按最小梯度方向修复 | 坏点修复要保护边缘，median 是 baseline，gradient repair 是进阶 |
| LSC | 学习用径向 gain map | OpenISP 当前没有完整 LSC 模块 | 这反而说明 LSC 通常依赖标定数据，不容易只靠一段通用代码解决 |
| AAF | 未实现 | `aaf.py` 在 RAW 域对同色采样做 5x5 温和低通 | Demosaic 前可先抑制高频混叠，代价是解析力下降 |
| BNF/CNF/NLM | 未实现 | `bnf.py`、`cnf.py`、`nlm.py` | 前端降噪可分亮度噪声、色噪和非局部相似块，不只是坏点修复 |

最值得后续补的小实验不是马上做复杂 NLM，而是先做两个轻量消融：

```text
BLC/DPC/LSC -> Bilinear
BLC/DPC/LSC -> AAF -> Bilinear
```

看纹理区假彩有没有减少、边缘是否变糊。这样能把 OpenISP 的 AAF 思想纳入当前验证闭环。

## 为什么 LSC 后续还要升级

LSC 是 Lens Shading Correction，镜头阴影校正。它主要解决画面边缘变暗、不同颜色通道边缘响应不一致的问题。如果不做 LSC，AWB 可能被边缘色偏影响，CCM 也可能在不同位置表现不一致。

但 LSC 通常需要 flat-field 标定图或可靠的估计策略。当前数据集没有专门的均匀白场标定图，所以本次只做“简化版径向 LSC”实验。后续如果要产品化，应使用均匀白场估计 R/Gr/Gb/B 四通道 gain map，并评估边缘噪声放大。

## 和 Week3 的关系

```text
BLC 不干净 -> Demosaic 会把黑位偏置插值到 RGB
DPC 不干净 -> Demosaic 会把坏点扩散成彩色伪影
LSC 不干净 -> AWB 会受到位置相关亮度/色偏影响
```

一句话总结：Week2 是在给 Demosaic 准备更干净的 RAW 输入。

## 关键词与参数验收表

| 关键词/参数 | 当前学习版含义 | 调节方向与风险 | 验证方式 |
|---|---|---|---|
| per-position BLC | 按 R/Gr/Gb/B 位置扣 metadata black level | 欠扣会发灰，过扣会让暗部大量归零 | 比较四平面 p01、0 附近比例和暗部 ROI |
| `min_delta=1024` | DPC 最低残差门限，单位是当前 RAW code value | 增大更保守但漏检；减小更敏感但误伤纹理 | 注入坏点后统计 precision/recall |
| `mad_k=12` | residual 的 robust 离散倍数 | 增大减少 false positive，也可能降低 recall | 与 `min_delta` 做二维 sweep，不能单独调 |
| local median | 同色 Bayer 邻域的局部稳健参考 | 邻域过大会跨结构，过小会受噪声影响 | 强边缘 crop 与平坦注入同时检查 |
| `edge_gains` | R/Gr/Gb/B 的学习版角落增益 | 太大使角落过亮并放大噪声，太小残留 shading | 看 gain map、中心/边缘均值和 clipping |
| `power=2.0` | 径向 profile 从中心到边缘的曲率 | 越大增益更集中在边缘；不是实机 mesh 标定 | synthetic flat-field 只验流程，不验产品效果 |

默认值服务于可复现实验，不是跨 Sensor 通用参数。尤其 `1024` 离开 black/white level 和有效位深就没有独立意义。

## 从输入到结论：可复现教程

### 数据契约与公式假设

| 模块 | 输入 | 输出 | 线性/范围约定 |
|---|---|---|---|
| BLC | `(H,W)` Bayer，通常 `uint16`，RAW code value | `(H,W)` Bayer，`uint16` | 线性；按 Bayer 位置扣黑并 clip 到有效白电平 |
| DPC | BLC 后 Bayer、pattern、有效白电平 | 修复后 Bayer + boolean mask | 线性；只替换候选点，不做显示归一化 |
| 学习版 LSC | DPC 后 Bayer + R/Gr/Gb/B gain 参数 | `(H,W)` `float32` Bayer | 线性；乘 gain 后可能超范围，必须记录 clipping |

对 Bayer 位置 `p`，BLC 可写为：

```text
y_p = clip(float(x_p) - b_c(p), 0, w - b_c(p))
```

`x_p/y_p` 是校正前后 RAW code value，`c(p)` 是位置所属的 R/Gr/Gb/B，`b_c` 是该位置黑电平，`w` 是 white level。先转浮点/有符号类型是为了避免 `uint16` 下溢绕回大正数。

DPC 对同色平面的残差为 `r_p=|y_p-median(N_p)|`，robust 阈值为：

```text
T = max(min_delta, median(r) + mad_k * median(|r - median(r)|))
```

`N_p` 是同 CFA 色的局部邻域；这个全局 robust threshold 是学习 baseline，不代表产品按亮度、ISO、温度分段的阈值。径向 LSC 可抽象为 `z_p=clip(y_p*g_c(r_p),0,w')`；这里的 `r_p` 指归一化半径，不要与 DPC residual 同名混用。

### 参数完整地图

| 参数 | 默认/单位 | 增大 | 减小 | 耦合与选择理由 | 失败现象 |
|---|---:|---|---|---|---|
| BLC `black_level` | metadata / RAW code | 暗部更黑、归零更多 | 暗部残留偏置 | 与 Bayer 位置、white level、温度/ISO 耦合 | 过扣死黑/色偏；欠扣发灰 |
| DPC `min_delta` | 1024 / RAW code | 更保守、漏检增加 | 更敏感、误检增加 | 必须按有效信号跨度归一理解，并与 `mad_k` 二维扫描 | 强边缘被修或热像素残留 |
| DPC `mad_k` | 12 / 无量纲 | 阈值随残差离散度提高 | 更易触发 | 噪声、纹理、ISO；不能脱离 `min_delta` 单调比较 | 大面积 mask 或 mask 为空 |
| `crop_size` | 100 / pixel | 上下文更多、局部点更小 | 更聚焦、缺少邻域语义 | 输出分辨率 | 修复点看不清或无法判断是否处于边缘 |
| LSC `edge_gains` | R1.18/Gr1.12/Gb1.12/B1.22 | 角落更亮且噪声/clip 增多 | shading 残留 | 与每通道 shading、AWB、white headroom 耦合 | 四角偏色、噪声增强 |
| LSC `power` | 2.0 / 无量纲 | 补偿更集中到边缘 | 增益更平缓铺开 | `edge_gains` 和半径定义 | 环状亮度过渡或中心被错误补偿 |

### 运行、产物和代码导航

```text
scripts/06_apply_blc.py -> soft_isp/blc.py -> *_blc.json / histogram / visual
scripts/07_apply_dpc.py -> soft_isp/dpc.py -> *_dpc.json / mask / crop
scripts/14_apply_lsc.py -> soft_isp/lsc.py -> *_lsc.json / gain map / compare
tests/test_stats_blc.py + test_dpc_demosaic.py + test_lsc_orientation.py
```

命令必须从 `stage1_soft_isp/` 执行。先运行 T01，再运行 `python exercises/week2_dpc_injection.py` 补全练习；最后运行 `python -m unittest discover -s tests -v`。正常证据至少包括模块 JSON、mask/gain map、固定 crop 和测试结果；只有最终 PNG 不算完成。

### Failure case、调试顺序与 trade-off

| 现象 | 第一发散点 | 验证实验 | 可能修复及代价 |
|---|---|---|---|
| 暗部出现大码值亮点 | BLC dtype | 用 `x<black` 小数组检查减法 | 转浮点/有符号；增加一次类型转换 |
| 强边缘被抹掉 | DPC mask | 同时看注入平坦区和真实强边缘 crop | 提高阈值会减少误检，但降低 recall |
| 坏点变成彩色十字 | DPC 是否在 Demosaic 前 | 对比 no-DPC 与 full 局部 crop | 更强检测会增加纹理损失风险 |
| 四角亮但噪声明显 | LSC gain map | 比较中心/角落 mean、std、clip | 限制 gain 保噪声，但残留 shading |
| Gr/Gb 角落差异异常 | pattern/每通道 gain | 画四平面中心—角落残差 | 修正 pattern/gain，不能用全局 AWB 掩盖 |

### 证据等级、跨周连接与学习验收

| 结论 | 证据等级 | 支持范围 | 边界 |
|---|---|---|---|
| BLC/DPC 对公开 DNG 的流程与图表 | `verified_public` | 代码可处理公开真实 RAW | 没有实机 factory calibration |
| 人工坏点注入与参数扫描 | `verified_synthetic` | recall/额外检测及参数方向 | 不能代表真实 hot/dead pixel 分布 |
| 径向 LSC、synthetic mesh | `verified_synthetic` | gain/mesh 流程和边界处理 | 不能证明真实镜头 shading 被校准 |
| 真实 flat-field/暗帧 | `not_run` | 无 | 需要新增标准采集 |

Week2 输出应仍是干净的线性 Bayer RAW，交给 Week3 Demosaic；若此处黑位、坏点或位置增益错误，插值会扩散错误，AWB 又会把它们当作场景颜色统计。

动手验收：

- [ ] 能手算一个 R/Gr/Gb/B 小数组的 BLC，并解释下溢风险
- [ ] 能固定输入，完成 `min_delta × mad_k` 二维扫描而非同时改多个模块
- [ ] 能在 mask 中区分注入坏点、额外检测和强边缘误检
- [ ] 能解释为何 LSC gain 同时放大信号与噪声
- [ ] 能把 synthetic、public 和 `not_run` 证据分别标注

## 本周面试闭环

完整参考答案见[Week 2：BLC/DPC/LSC 面试题](../interview/week2_frontend_correction_questions.md)。

1. **概念题：** BLC、DPC、LSC 各修正什么物理来源，为什么都在 Demosaic 前？
2. **原理题：** DPC 为什么比较同色 Bayer 邻域，而不是直接比较四邻域？
3. **参数题：** `min_delta` 与 `mad_k` 各解决什么问题，怎样设计公平参数扫描？
4. **调试题：** 为什么 DPC 同时需要 precision、recall 和强边缘视觉检查？
5. **系统题：** synthetic flat-field 验证了什么，怎样升级为真实 LSC 标定并控制角落噪声？
