# Route 统一 Benchmark Protocol

## 1. 适用范围

本协议适用于 Stage 2 训练/评估、Stage 3 C++ 算法性能和 Stage 4 ONNX Runtime/CUDA/TensorRT 部署。历史 CSV 可保留原格式，但新增汇总必须映射到统一字段。

## 2. 强制上下文

每次 benchmark 必须记录：代码版本、配置、模型/engine hash、输入 manifest、样本数、shape、dtype、layout、设备、CPU/GPU 型号、线程数、编译器、优化级别、Python/ORT/CUDA/TensorRT 版本、warmup 和 timed runs。

## 3. 时间边界

1. `pre_ms`：解码后的输入到模型 tensor；是否含 resize/normalize/layout conversion 必须说明。
2. `h2d_ms`：host 到 device；注明 pageable 或 pinned memory。
3. `infer_ms`：仅后端调用。异步 GPU 必须在计时边界同步。
4. `d2h_ms`：device 到 host。
5. `post_ms`：tensor 到可交付 RGB，不含文件保存时必须明确。
6. `compute_e2e_ms`：pre + transfer + infer + post。
7. `io_ms`：读取和保存单独列出。
8. `wall_e2e_ms`：用户可感知总耗时，必须说明是否含 session/engine 创建。

不同边界的数据不得放在同一列直接排名。`trtexec compute`、ORT `session.run` 和带保存的 pipeline latency 是三个不同口径。

## 4. 统计纪律

1. warmup 不少于 3 次，GPU 首次 kernel/engine 初始化不得混入 steady-state。
2. 报告样本数、运行次数、mean、p50、p90；长尾敏感场景增加 p95/p99。
3. GPU 使用显式同步或后端事件计时，记录同步位置。
4. CPU 固定线程数和电源模式；GPU 记录温度/频率策略及是否发生降频。
5. 性能优化必须同时执行 correctness/quality 阈值，不能只报告加速比。

## 5. 统一汇总字段

`stage4_deploy_isp/outputs/audit/latency_matrix.csv` 是当前机器可读汇总基线，至少包含：

```text
backend,device,shape,precision,warmup_runs,timed_runs,
pre_ms,h2d_ms,infer_mean_ms,infer_p50_ms,infer_p90_ms,
d2h_ms,post_ms,e2e_ms,includes_io
```

空字段表示该环节没有独立测量，不表示耗时为 0。`includes_io` 必须是可读说明，不能留空。

## 6. 可比较性判定

只有输入 manifest、shape、precision、质量阈值和时间边界一致时，结果才能直接比较。否则报告应使用“独立观测”而不是“更快/更慢”的结论。
