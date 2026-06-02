# AI-ISP Stage 2

阶段二聚焦 AI-ISP 和图像恢复。当前不急着上真实手机 RAW 数据或大模型，而是先用一个小型 RGB 去噪任务，把深度学习训练闭环跑稳，再逐步走向真实成对 RGB 数据。

## 学习报告

报告已经按周整理，不再使用 `week1a/week1b/week1c` 这种碎片编号。

| 顺序 | 报告 | 作用 |
|---:|---|---|
| 0 | `reports/stage2_learning_flow.md` | 阶段二总路线，先读这个 |
| 1 | `reports/week0_foundation.md` | 神经网络训练基础 |
| 2 | `reports/week1_toy_rgb_denoise.md` | Toy RGB 去噪完整闭环 |
| 3 | `reports/week2_real_paired_rgb.md` | 真实成对 RGB 数据入口 |

推荐阅读顺序：

```text
stage2_learning_flow.md
  -> week0_foundation.md
  -> week1_toy_rgb_denoise.md
  -> week2_real_paired_rgb.md
```

## 当前进度

已经完成：

- Week 0：训练闭环基础梳理；
- Week 1：toy RGB 去噪闭环；
- TinyCNN probe；
- DnCNN residual 去噪；
- direct clean 和 residual 对比；
- L1 和 L2/MSE loss 对比；
- patch size 64 和 128 对比；
- Gaussian noise 到 shot/read noise；
- noisy 输入 baseline 测量；
- 成对 RGB 图片文件夹数据适配；
- SIDD-style 小型子集准备脚本。

下一步是 Week 2：

```text
准备真实 noisy/clean RGB 小子集
  -> 测 noisy 输入 baseline
  -> 跑 500 step DnCNN residual
  -> 对比 output 和 noisy 输入是否真的改善
```

## 环境

```bash
pip install -r requirements.txt
```

## Week 1 常用命令

TinyCNN probe：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_10.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_50.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_tiny_100_probe.yaml
```

DnCNN residual：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn.yaml
```

L1 / L2 对比：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l1.yaml
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2.yaml
```

测 noisy 输入 baseline：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/toy_rgb_denoise_dncnn_l2_shot_read_calibrated.yaml
```

Paired RGB smoke test：

```bash
python ai_isp_stage2/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_smoke_dncnn_l2.yaml
```

## Week 2 常用命令

准备外部真实成对 RGB 小子集：

```bash
python ai_isp_stage2/scripts/04_prepare_paired_rgb_subset.py --source-noisy-dir path/to/noisy --source-clean-dir path/to/clean --output-dir ai_isp_stage2/datasets/sidd_tiny --train-count 80 --val-count 20 --size 512
```

测真实子集 noisy 输入 baseline：

```bash
python ai_isp_stage2/scripts/02_measure_noise_baseline.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

训练真实子集：

```bash
python ai_isp_stage2/scripts/01_train_toy_rgb.py --config ai_isp_stage2/configs/paired_rgb_sidd_tiny_dncnn_l2.yaml
```

## 项目结构

```text
ai_isp_stage2/
├── ai_isp/      # dataset、engine、metrics、models、utils
├── configs/     # 训练配置
├── materials/   # 前置学习材料
├── reports/     # 按周整理后的学习报告
├── runs/        # 训练输出，已 git ignore
└── scripts/     # 训练、测 baseline、准备数据脚本
```

## 学习检查点

进入 Week 2 前，最好能说清楚：

1. noisy、clean、output 分别是什么；
2. loss、backward、optimizer 各自负责什么；
3. 为什么 DnCNN residual 适合去噪；
4. L1 和 L2/MSE 的差异；
5. patch size 为什么影响速度和指标；
6. 为什么比较模型前要先测 noisy 输入 baseline；
7. paired RGB 数据为什么必须保证 noisy/clean 对齐。

如果这些还不清楚，先回到 `reports/week1_toy_rgb_denoise.md`。
