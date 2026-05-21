# 数据集包

## 已保存

| 文件 | 说明 |
|---|---|
| `fivek_index.html` | MIT-Adobe FiveK 官方索引页，本地可搜索 DNG/TIFF 链接。 |

## 已下载 RAW

5 张 DNG 已放在 `data/raw/`：

```text
S01_a0001-jmac_DSC1459.dng
S02_a0002-dgw_005.dng
S03_a0003-NKIM_MG_8178.dng
S04_a0004-jmac_MG_1384.dng
S05_a0005-jn_2007_05_10__564.dng
```

这些样张来自 MIT-Adobe FiveK：

https://data.csail.mit.edu/graphics/fivek/

## 为什么不下载全量

FiveK 全量包约 50GB。阶段 1 的目标是理解 RAW 数据流和 ISP 模块，不需要一开始下载全量。先用 5 张 DNG 跑通：

1. RAW metadata 检查
2. 四通道统计
3. histogram 和 ROI
4. rawpy 参考输出
5. 自己的 Soft-ISP 输出

## 后续怎么精挑样张

打开 `fivek_index.html`，搜索 `img/dng/` 或直接浏览缩略图。每选一张，记录：

- 场景类型
- DNG 文件名
- 是否有明显高光/暗部/纹理/混合光
- 是否适合当前模块实验

