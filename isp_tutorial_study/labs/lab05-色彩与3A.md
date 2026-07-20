# Lab 05：色彩、AWB、CCM 与 3A

对应章节：10、16。

## 目标

区分中性校正、颜色映射、显示编码和 3A 时域稳定；建立灰卡、色卡、曲线和视频序列的评价方法。

## 命令

```powershell
Set-Location D:\document\route\stage1_soft_isp
$raw = 'data/raw/T01_a0006-IMG_2787.dng'
$out = '..\isp_tutorial_study\lab_outputs\lab05'
New-Item -ItemType Directory -Force $out | Out-Null
python scripts/09_apply_awb.py $raw --out-dir "$out\awb" --report "$out\awb_report.md"
python scripts/10_apply_ccm.py $raw --out-dir "$out\ccm" --report-path "$out\ccm_report.md"
python scripts/11_apply_gamma.py $raw --out-dir "$out\gamma" --report-path "$out\gamma_report.md"
Copy-Item data/colorchecker_patches_template.csv "$out\my_colorchecker_patches.csv"
```

`colorchecker_patches_template.csv` 只有表头。必须填入真实测量值和参考值后才能运行标定；空模板不会产生有效 CCM，也不得把模板结果描述为真实相机结论。

填入真实 measured/reference 线性 RGB 后再执行：

```powershell
python scripts/21_calibrate_colorchecker.py "$out\my_colorchecker_patches.csv" --output "$out\ccm_fit.json"
```

## 对照

- AWB：关闭、灰世界、手动中性点。
- CCM：单位矩阵、当前矩阵、R/B 交换错误矩阵。
- 处理域：线性域 CCM 后编码，与错误地在 sRGB 域使用同一矩阵。
- 3A：构造亮度或色温阶跃，画目标值、测量值和控制值随帧变化的曲线。

## Anti-flicker 检查

- 理想 50Hz 电源光强周期常见约 10ms。
- 理想 60Hz 电源光强周期常见约 8.33ms。
- LED/PWM 可能不遵守简单倍频模型，必须用行亮度或高速采样实测。

## 输出与验收

- 灰卡 R/G/B 比例和 AWB gains。
- ColorChecker 平均/最大 Delta E，单独报告灰阶和肤色。
- 正确/错误处理域的固定 crop。
- AE/AWB 阶跃响应：收敛帧数、过冲和稳态抖动。
- 能解释“白色正确但其他颜色错误”为什么应检查 CCM/光源/处理域，而不是继续调 AWB。
