# 数据集包

## 已保存

| 文件 | 说明 |
|---|---|
| `fivek_index.html` | MIT-Adobe FiveK 官方索引页，本地可搜索 DNG/TIFF 链接。 |

## 已下载 RAW

当前主样张集为 14 张 DNG，已放在 `data/raw/`：

```text
T01_a0006-IMG_2787.dng
T02_a0008-WP_CRW_3959.dng
T03_a0010-jmac_MG_4807.dng
T04_a0012-kme_143.dng
T05_a0014-WP_CRW_6320.dng
T06_a0018-kme_234.dng
T07_a0020-jmac_MG_6225.dng
T08_a0022-IMG_2380.dng
T09_a0023-07-06-02-at-15h06m48-s_MG_1489.dng
T10_a0026-kme_391.dng
T11_a0033-KE_-2590.dng
T12_a0034-LSYD4O2202.dng
T13_a0035-dgw_048.dng
T14_a0040-_DSC5693.dng
```

这些样张来自 MIT-Adobe FiveK：

https://data.csail.mit.edu/graphics/fivek/

## 为什么不下载全量

FiveK 全量包约 50GB。阶段 1 的目标是理解 RAW 数据流和 ISP 模块，不需要一开始下载全量。当前 14 张 DNG 已覆盖人像、暗部、高动态范围、细纹理、大面积绿色/蓝色、建筑边缘等典型 ISP 测试场景：

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
