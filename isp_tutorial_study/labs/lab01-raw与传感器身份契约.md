# Lab 01：RAW 与传感器身份契约

对应章节：1–3。

## 目标

在处理像素前确认文件身份、CFA、black/white level、位深、曝光和输出尺寸，形成一张可复查的 RAW contract。

## 输入

仓库内置样例：`stage1_soft_isp/data/raw/T01_a0006-IMG_2787.dng`。

## 命令

```powershell
Set-Location D:\document\route\stage1_soft_isp
python -m pip install -r requirements.txt
$out = '..\isp_tutorial_study\lab_outputs\lab01'
New-Item -ItemType Directory -Force $out | Out-Null
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
python scripts/19_generate_raw_metadata_manifest.py --output "$out\raw_metadata_manifest.json"
python scripts/04_plot_raw_histogram.py "data/raw/T*.dng" --out-dir "$out\histograms"
```

## 必须记录

| 字段 | 记录值 | 为什么影响 ISP |
|---|---|---|
| width/height |  | 缓存、吞吐和 sensor mode |
| dtype/bit depth |  | 范围、位宽和量化 |
| CFA pattern |  | 同色邻域与 demosaic |
| black level |  | BLC 和暗部统计 |
| white level |  | 饱和、归一化和动态范围 |
| exposure/ISO |  | SNR、噪声和 3A |

## 对照实验

故意把 CFA pattern 写成另一个排列，或把 black/white level 用默认满量程代替 metadata。只做记录，不覆盖原配置。说明后续会出现什么错误，以及 AWB 为什么不能可靠修复错误 CFA。

## 输出

- RAW 身份卡一张。
- metadata manifest。
- 原始直方图和至少两个固定 crop 坐标。
- 一段“如果缺少 metadata，我会停止哪些处理”的说明。

## 验收

- 能解释 Bayer RAW 不是完整 RGB。
- 能指出 black/white level 不一定等于 0/满位宽。
- 能说明 sensor mode 改变为什么需要重新确认标定和坐标。
- 命令、输入文件和输出路径可由另一人复现。
