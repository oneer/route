# 章节到项目的工程映射

| 章节 | 主要项目入口 | 建议产物 |
|---|---|---|
| 1–3 | [`stage1_soft_isp`](../stage1_soft_isp/materials/stage1_start_here.md) | RAW 身份卡、pipeline 图、metadata 表 |
| 4 | [`blc.py`](../stage1_soft_isp/soft_isp/blc.py) | BLC 前后直方图与暗部 crop |
| 5 | [`lsc.py`](../stage1_soft_isp/soft_isp/lsc.py) | gain map、四角噪声与平场报告 |
| 6 | [`dpc.py`](../stage1_soft_isp/soft_isp/dpc.py) | 坏点注入、mask、修复 crop |
| 7 | [`demosaic.py`](../stage1_soft_isp/soft_isp/demosaic.py) | 双线性/边缘感知/参考实现对比 |
| 8–9 | [`denoise.py`](../stage1_soft_isp/soft_isp/denoise.py)、[`bench_denoise.cpp`](../stage3_cpp_isp/benchmarks/bench_denoise.cpp) | 参数扫描、纹理 crop、耗时和指标 |
| 10 | [`awb.py`](../stage1_soft_isp/soft_isp/awb.py)、[`ccm.py`](../stage1_soft_isp/soft_isp/ccm.py) | 灰卡统计、ColorChecker、Delta E |
| 11–13 | [`stage3_cpp_isp`](../stage3_cpp_isp/README.md) | 像素率、带宽、定点对齐、benchmark |
| 14–16 | Tone/HDR/统计模块与综合项目 | tone 曲线、HDR failure case、3A 收敛图 |
| 17–27 | [`camera_system_capstone`](../camera_system_capstone/README.md) | 厂商证据卡、场景验证矩阵、系统选型说明 |
| 28–29 | [`stage2_ai_isp`](../stage2_ai_isp/stage2_start_here.md) | 训练配置、测试指标、error map、failure gallery |
| 30–31 | Stage 3/4 与 Codec 实验 | quality/latency/memory/bitrate 对比 |
| 32 | 各阶段 tests 与 metrics | regression 清单、覆盖矩阵、golden 版本 |
| 33–34 | Stage 3/4、综合项目 | CMake/部署 contract、系统 profile、恢复策略 |
| 35 | 全项目证据 | 技术成熟度卡和个人方向选择 |

详细命令见各章关联的 `labs/` 文档。

