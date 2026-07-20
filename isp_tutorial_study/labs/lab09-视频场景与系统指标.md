# Lab 09：视频、行业场景与系统指标

对应章节：20–27。

## 目标

把单帧画质扩展到时域稳定、最坏延迟、多摄同步、编码压力、异常检测和长期运行。

## 运行综合项目

```powershell
Set-Location D:\document\route
python camera_system_capstone/scripts/06_run_capstone.py --cpu-only
python -m unittest discover -s camera_system_capstone/tests -v
```

## 场景矩阵

至少选择四类：低照运动、逆光/HDR、LED/PWM、雨雾/脏污、多摄切换、PTZ/长焦、视频编码前处理。

| 场景 | 人眼输出目标 | CV 输出目标 | 关键 ISP 参数 | 失败现象 | 指标 | 降级策略 |
|---|---|---|---|---|---|---|
| 低照运动 |  |  |  |  |  |  |
| LED |  |  |  |  |  |  |
| 多摄 |  |  |  |  |  |  |
| HDR |  |  |  |  |  |  |

## 时域检查

- 逐帧亮度、色温和噪声曲线。
- 相邻帧差异和固定 ROI 曲线。
- 运动区域拖影/鬼影 crop。
- p50/p90/p99 延迟和掉帧。
- 多摄 timestamp/metadata 对齐误差。

## 验收

- 不能只用单帧 PSNR/SSIM 评价视频。
- 给人看的流和给算法看的流分别定义目标。
- 最坏延迟、帧间抖动和恢复时间进入验收。
- 对遮挡、脏污、不可恢复输入优先检测与降级，不承诺“算法修复一切”。

