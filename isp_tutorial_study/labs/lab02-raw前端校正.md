# Lab 02：RAW 前端校正

对应章节：4–6。

## 目标

分别验证 BLC、LSC 和 DPC，观察前端错误如何在后续 demosaic/颜色处理后被放大。

## 输入与命令

```powershell
Set-Location D:\document\route\stage1_soft_isp
$raw = 'data/raw/T01_a0006-IMG_2787.dng'
$out = '..\isp_tutorial_study\lab_outputs\lab02'
New-Item -ItemType Directory -Force $out | Out-Null
python scripts/06_apply_blc.py $raw --out-dir "$out\blc" --report "$out\blc_report.md"
python scripts/14_apply_lsc.py $raw --out-dir "$out\lsc" --report "$out\lsc_report.md"
python scripts/07_apply_dpc.py $raw --out-dir "$out\dpc" --report "$out\dpc_report.md"
```

## 三组对照

1. **BLC**：正确 black level、偏低、偏高各一组；比较 RAW 直方图和暗部 crop。
2. **LSC**：关闭、合理、过强三组；比较中心/四角亮度和噪声。
3. **DPC**：对人工注入坏点比较关闭、静态表、动态检测；记录 TP/FP/FN。

坏点注入入口：[`week2_dpc_injection.py`](../../stage1_soft_isp/exercises/week2_dpc_injection.py)。

## 输出

- BLC 前后直方图和视觉对比。
- LSC gain map/mesh、四角 crop 和噪声统计。
- DPC mask、修复 crop、误检与漏检数量。
- 一张表说明每个模块的输入域、输出域、前置依赖和失败现象。

## 验收

- BLC 过校正能观察到暗部截断，欠校正能观察到抬黑或色偏风险。
- LSC 评价同时包含均匀性和四角噪声，而不只是“看起来更亮”。
- DPC 只使用合适的 CFA 同色邻域，且能解释纹理误检风险。
- 所有对照保持同一输入、crop、显示变换和后续 pipeline。
