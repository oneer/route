# ISP 课程实验总览

所有命令默认从仓库根目录 `D:\document\route` 或实验中明确指定的目录运行。不要覆盖既有结果；如需修改输出路径，先复制配置并记录新路径。

Python 实验入口已通过 `--help` 检查。Lab 04、06、07、11、12 的 C++ 部分要求 `cmake`、`ctest` 和项目配置的编译器可用；先运行 `cmake --version`。如果命令不在 PATH，按 [`stage3_cpp_isp/README.md`](../../stage3_cpp_isp/README.md) 配置工具链后再继续，不要把“未安装工具”记录成算法失败。

| 实验 | 对应章节 | 核心产物 |
|---|---|---|
| [Lab 01](lab01-raw与传感器身份契约.md) | 1–3 | RAW 身份卡、metadata、输入契约 |
| [Lab 02](lab02-raw前端校正.md) | 4–6 | BLC/LSC/DPC 图、统计和失败说明 |
| [Lab 03](lab03-去马赛克与伪影.md) | 7 | demosaic 对比与伪影 crop |
| [Lab 04](lab04-降噪与NLM.md) | 8–9 | 参数扫描、质量/耗时/纹理取舍 |
| [Lab 05](lab05-色彩与3A.md) | 10、16 | AWB/CCM、Delta E、稳定性分析 |
| [Lab 06](lab06-硬件数据流与定点.md) | 11–13、33 | 像素率、带宽、定点误差、benchmark |
| [Lab 07](lab07-HDR计算摄影与3A稳定性.md) | 14–16 | HDR/tone、配准、3A 收敛检查 |
| [Lab 08](lab08-产业资料证据审计.md) | 17–24 | 公开事实/推断/未知三栏证据卡 |
| [Lab 09](lab09-视频场景与系统指标.md) | 20–27 | 场景矩阵、时域质量、系统指标 |
| [Lab 10](lab10-AI-ISP训练与失败案例.md) | 28–29 | 训练、测试、error map、failure gallery |
| [Lab 11](lab11-异构性能与编码协同.md) | 30–31 | 质量/延迟/内存/码率矩阵 |
| [Lab 12](lab12-验证部署与系统集成.md) | 32–34 | tests、部署对齐、系统 profile |
| [Lab 13](lab13-技术趋势证据卡.md) | 35 | 技术成熟度和个人方向判断 |

统一验收见 [自测与实验评分标准](../SELF_TEST_RUBRIC.md)。
