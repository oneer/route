# 35 章自测专属关键点

各章单独页面提供统一 10 分 rubric；本页补充每章答案中必须覆盖的专属概念。开放题允许不同方案，但缺少这些核心关系通常说明尚未掌握。

| 章 | 答案必须覆盖的专属关键点 |
|---:|---|
| 1 | RAW 是测量而非照片；先校正测量基准再重建/表达；实时吞吐和前后依赖 |
| 2 | shot/read/dark/FPN 的区别；PTC/SNR；bit depth 不等于真实动态范围 |
| 3 | CFA、sensor mode、metadata、MIPI/时序；3A 和曝光延迟；多摄同步 |
| 4 | BLC/offset 在 gain 前；dark/bias/flat 区分；DSNU/PRNU/FPN 与温度/曝光 |
| 5 | shading/暗角/畸变/色差区分；gain map 标定；四角噪声放大 |
| 6 | 静态/动态坏点；同 CFA 相位邻域；误检/漏检与 cluster/row/column 边界 |
| 7 | CFA 正确性；沿边缘而非跨边缘插值；zipper/false color/moiré；前端噪声影响 |
| 8 | Poisson-Gaussian；RAW/RGB/YUV 与空域/时域；纹理损失、拖影和多指标 |
| 9 | patch/search/h；复杂度和访存；指数/LUT/定点/早停；RAW 同色约束 |
| 10 | camera/linear/display RGB；AWB 与 CCM 分工；XYZ/Lab/Delta E；标准和 range |
| 11 | 像素率、pixels/clock、line buffer、位宽、ready/valid、shadow register |
| 12 | line/window/tile/ping-pong；overlap；bank conflict；burst/stride/alignment |
| 13 | critical path、CDC/async FIFO；动态功耗公式；clock/power gating、DVFS、热 |
| 14 | capture/merge/tone/display 分层；权重和去鬼影；global/local、halo、PQ/HLG |
| 15 | 多帧信息增益；配准是核心风险；EIS crop；SR/夜景/散景的 hallucination 与代价 |
| 16 | statistics→controller→sensor→next frames；AE/AF/AWB 互扰；10ms/8.33ms；收敛与稳定 |
| 17 | 多摄/像素率/异构计算/ZSL/热；公开事实与 Qualcomm 宣传/推断分离 |
| 18 | Smart HDR、Deep Fusion、ProRAW 的功能边界；Apple 内部结构大多不可公开验证 |
| 19 | 用同一任务/日期/条件比较；高像素/TOPS 不等于画质；视频、生态和持续功耗 |
| 20 | ISO 26262、最坏延迟、timestamp、多摄/HDR/LFM、诊断和降级、人眼/CV 双目标 |
| 21 | 先定义任务和 sensor；接口/工具链/安全/生态；平台能力不等于 OEM 启用 |
| 22 | 雾雨雪/夜间/LED/隧道/运动的不同失效；检测与降级；场景覆盖和最坏情况 |
| 23 | RAW/JPEG 双路径；14/16-bit；色卡/风格；连拍缓存/写卡；Log/RAW 视频 |
| 24 | 100MP 数据量；tile overlap；预览/最终双 pipeline；热/暗电流；pixel shift 对齐 |
| 25 | 成本/功耗/延迟；预览/拍照/视频差异；肤色；多摄切换；调参和用户体验 |
| 26 | 长期可靠；低照 SNR；WDR/TNR 拖影；IR-cut/红外；隐私位置；编码码率 |
| 27 | 时域稳定；8K/高帧率带宽；TNR/EIS/RS；Log/HDR；4:2:x；编码前处理 |
| 28 | 替代/增强/预测；RAW/RGB/YUV 域；数据/损失；搬运；fallback、可信和时域 |
| 29 | 去噪/demosaic/SR/HDR/语义模块差异；真实数据；量化/tile；failure gallery |
| 30 | 固定流水线 vs SIMT；cache vs line buffer；峰值算力≠端到端；异构搬运和确定性 |
| 31 | ISP 增强 vs Codec 压缩；tile vs CTU；运动/变换/熵编码；噪声/锐化影响码率 |
| 32 | directed/random/golden/coverage/assertion；IQ+性能+场景；分层平台和回归版本 |
| 33 | floorplan/STA/IR/EM；SRAM/DFT/BIST；signoff/ECO；算法最终变成物理成本 |
| 34 | buffer ownership/lifetime；metadata 对齐；HAL/V4L2/DMA；QoS/功耗；异常恢复 |
| 35 | 技术成熟度而非热度；传感器/数据/硬件/生态/安全；明确日期、未知项和复查条件 |

[统一评分标准](../SELF_TEST_RUBRIC.md) · [课程索引](../full_content_index.md)

