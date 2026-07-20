# Lab 03：去马赛克与伪影

对应章节：7。

## 目标

比较双线性、边缘感知和参考实现，建立 false color、zipper、moiré 与输入错误的视觉对应关系。

## 命令

```powershell
Set-Location D:\document\route\stage1_soft_isp
$out = '..\isp_tutorial_study\lab_outputs\lab03'
New-Item -ItemType Directory -Force $out | Out-Null
python scripts/08_apply_demosaic.py data/raw/T01_a0006-IMG_2787.dng --out-dir "$out\figures" --report "$out\demosaic_report.md"
```

可选练习：完成 [`week3_demosaic_todo.py`](../../stage1_soft_isp/exercises/week3_demosaic_todo.py)，再运行相关测试。

## 固定观察区域

- 高反差斜边。
- 周期性细纹理或水面/羽毛。
- 高饱和颜色边界。
- 人工注入坏点附近。

## 对照

- 正确 CFA 与三个错误 CFA。
- 双线性与边缘感知。
- BPC 前后再 demosaic。
- 加噪前后，观察边缘方向判断是否变差。

## 输出与验收

- 四种方法/配置的同坐标 crop。
- 至少标注一处 zipper、一处 false color 或解释为什么样例未出现。
- 区分 demosaic 差异与 AWB/CCM 差异。
- 能说明为什么绿色通道常被优先重建，以及 CFA 错误为什么不能靠 AWB 稳定补救。
