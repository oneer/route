# Week 1：RAW 输入合同

选择一张此前没分析过的 DNG，独立回答：

1. `raw_image_visible` 的 shape、dtype、min/max 是什么？
2. black level 和 white level 各代表什么？
3. Bayer pattern 如何由 `raw_pattern` 和 `color_desc` 得到？
4. R/Gr/Gb/B 的均值为什么不同？
5. 哪些像素接近黑位，哪些接近饱和？
6. 选一个暗部和一个高光 ROI，说明风险。

验收：

- 输出一份 JSON 和不超过两页的 Markdown；
- 至少有一个结论来自 ROI，而不是全图均值；
- 明确写一条“不确定、需要额外数据才能确认”的判断。
