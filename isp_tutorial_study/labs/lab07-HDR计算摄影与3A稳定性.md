# Lab 07：HDR、计算摄影与 3A 稳定性

对应章节：14–16。

## 目标

区分 HDR 采集、对齐、融合、tone mapping 和显示；验证多帧方法对运动、延迟和控制稳定性的敏感性。

## Tone/Gamma 基线

```powershell
Set-Location D:\document\route\stage1_soft_isp
$raw = 'data/raw/T01_a0006-IMG_2787.dng'
$out = '..\isp_tutorial_study\lab_outputs\lab07'
New-Item -ItemType Directory -Force $out | Out-Null
python scripts/11_apply_gamma.py $raw --out-dir "$out\gamma" --report-path "$out\gamma_report.md"
python scripts/12_apply_tone_mapping.py $raw --out-dir "$out\tone" --report-path "$out\tone_report.md"
```

## C++ HDR/LTM 对齐与性能

前置检查：`cmake --version`。没有可用工具链时只完成纸面预算，并明确标记“C++ 未实机验证”。

```powershell
Set-Location D:\document\route\stage3_cpp_isp
cmake --preset verify
cmake --build --preset verify
ctest --preset verify
.\build\bench_local_tone_mapping.exe
.\build\bench_image_fusion.exe
```

## 必做对照

1. 全局 tone 与局部 tone：固定输入，观察暗部、高光、halo 和颜色。
2. 对齐正确与故意偏移 1–3 像素：观察 HDR 鬼影和细节双边。
3. 短曝光/长曝光权重扫描：记录高光保留、暗部噪声和运动区域。
4. AE 阶跃：给目标亮度一个阶跃，记录收敛时间、过冲和稳态抖动。

## 输出

- 输入曝光和融合权重表。
- 对齐误差与输出误差/鬼影 crop。
- tone 曲线和统一显示条件下的对比图。
- 质量、延迟和内存估算。
- 3A 收敛曲线。

## 验收

- 不能把 HDR merge、tone mapping 和 HDR display 混为一层。
- 运动场景必须单独评价，不能只在静态图上验收。
- 局部 tone 评价包含 halo 和时域稳定性。
- 能说明多帧质量收益如何换来缓存、延迟、功耗和失败风险。
