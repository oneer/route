# RAW 样张登记表

阶段 1 至少准备 5 张 RAW / DNG。当前已经下载 5 张 MIT-Adobe FiveK DNG 到 `data/raw/`。这些 DNG 不提交到 Git，由 `.gitignore` 排除。

## 已准备样张

| 编号 | 建议用途 | 本地文件 | 来源链接 | 参考输出 | Bayer | black level | white level | 状态 |
|---|---|---|---|---|---|---:|---:|---|
| S01 | 起步样张：先跑通 metadata 和四通道统计 | `data/raw/S01_a0001-jmac_DSC1459.dng` | https://data.csail.mit.edu/graphics/fivek/img/dng/a0001-jmac_DSC1459.dng | 用 rawpy 生成到 `data/references/S01_rawpy_srgb.png` | 待脚本读取 | 待脚本读取 | 待脚本读取 | 已下载 |
| S02 | 对照样张：观察曝光和通道分布差异 | `data/raw/S02_a0002-dgw_005.dng` | https://data.csail.mit.edu/graphics/fivek/img/dng/a0002-dgw_005.dng | 用 rawpy 生成到 `data/references/S02_rawpy_srgb.png` | 待脚本读取 | 待脚本读取 | 待脚本读取 | 已下载 |
| S03 | 对照样张：观察不同相机/场景 metadata | `data/raw/S03_a0003-NKIM_MG_8178.dng` | https://data.csail.mit.edu/graphics/fivek/img/dng/a0003-NKIM_MG_8178.dng | 用 rawpy 生成到 `data/references/S03_rawpy_srgb.png` | 待脚本读取 | 待脚本读取 | 待脚本读取 | 已下载 |
| S04 | 对照样张：用于 histogram 和 clipping 检查 | `data/raw/S04_a0004-jmac_MG_1384.dng` | https://data.csail.mit.edu/graphics/fivek/img/dng/a0004-jmac_MG_1384.dng | 用 rawpy 生成到 `data/references/S04_rawpy_srgb.png` | 待脚本读取 | 待脚本读取 | 待脚本读取 | 已下载 |
| S05 | 对照样张：用于 demosaic / AWB 初步实验 | `data/raw/S05_a0005-jn_2007_05_10__564.dng` | https://data.csail.mit.edu/graphics/fivek/img/dng/a0005-jn_2007_05_10__564.dng | 用 rawpy 生成到 `data/references/S05_rawpy_srgb.png` | 待脚本读取 | 待脚本读取 | 待脚本读取 | 已下载 |

## 后续精挑目标

当前 5 张是启动包，优点是马上能跑代码。等 Week 1 metadata 和 thumbnail 都看完后，再按下面目标替换或补充样张：

| 目标编号 | 场景 | 选择原因 | 状态 |
|---|---|---|---|
| T01 | 日光室外正常曝光 | 建立正常 RAW histogram 和四通道均值直觉 | 待从 FiveK 缩略图精挑 |
| T02 | 室内暖光 | 观察 AWB 偏色、混合光和 R/B gain | 待从 FiveK 缩略图精挑 |
| T03 | 低光高 ISO | 观察暗部噪声、read noise、chroma noise | 可从 SID 或 FiveK 补 |
| T04 | 高动态范围 | 观察高光 clipping 和暗部细节 | 可从 HDR+ 或 FiveK 补 |
| T05 | 高频纹理/纯色 | 观察 demosaic artifact、false color、zipper | 待从 FiveK 缩略图精挑 |

## 本周要填的字段

运行：

```bash
python scripts/01_inspect_raw.py data/raw/S01_a0001-jmac_DSC1459.dng
```

把输出中的 `raw_pattern`、`black_level_per_channel`、`white_level`、四通道统计写回本表和 `reports/week1_raw_statistics.md`。

