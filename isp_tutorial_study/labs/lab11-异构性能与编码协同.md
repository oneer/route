# Lab 11：ISP、GPU/NPU 与 Codec 协同

对应章节：30–31。

## 目标

用端到端数据搬运、延迟、内存和码率，而不是峰值算力判断任务应该放在 ISP、CPU/GPU、NPU 还是 Codec 前处理。

## 性能基线

前置检查：`cmake --version`。Stage 4 GPU 行只有在模型、ORT/CUDA 和设备可用时才能复测；空值和 `not_run` 不应被改写成结果。

```powershell
Set-Location D:\document\route\stage3_cpp_isp
cmake --preset verify
cmake --build --preset verify
.\build\bench_pipeline.exe
Set-Location D:\document\route
python stage4_deploy_isp/scripts/13_profile_device_pipeline.py
python stage4_deploy_isp/scripts/14_generate_quality_latency_memory_matrix.py
```

## 任务卡

对 denoise、demosaic、tone、AI denoise、resize 和视频前处理分别填写：

| 任务 | 数据域/格式 | 算力 | 读写字节 | 启动/同步 | 延迟 | 内存 | 适合后端 |
|---|---|---:|---:|---:|---:|---:|---|
|  |  |  |  |  |  |  |  |

## 可选 Codec 实验

如果本机有 FFmpeg，先记录版本：

```powershell
ffmpeg -version
```

对同一短视频生成弱降噪、强降噪、过锐化三种前处理结果，以相同编码器、分辨率、帧率、preset 和目标质量/码率编码，比较文件大小、VMAF/SSIM（如可用）和运动纹理 crop。没有 FFmpeg 时，完成纸面实验并明确标记“未实机验证”。

## 验收

- 计算包含 host/device 或模块间数据搬运，而不只算 kernel 时间。
- 报告持续性能和 p90/p99，不用一次峰值。
- 能解释噪声和过锐化为什么增加编码残差/码率。
- 资源复用结论区分“共享算子”和“共享完整硬件模块”。
