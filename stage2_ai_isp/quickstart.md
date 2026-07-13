# 阶段二 Quickstart

这份 Quickstart 只解决一个问题：在全新环境中先得到一个可验证的成功结果，再进入
Week 0-12 正式路线。所有命令都从仓库根目录运行。

## 1. 选择路径

| 路径 | 是否需要外部数据 | 目的 | 完成标志 |
|---|---|---|---|
| A：最小 smoke | 否 | 验证 Python、Dataset、训练、验证和 checkpoint | 16 个测试通过，smoke run 生成指标和模型 |
| B：SIDD tiny | 是 | 进入真实 paired sRGB 去噪主线 | split audit 通过，train/val/test 均有 manifest 记录 |

第一次学习先完成 A。A 失败时不要下载数据、换模型或启动长训练。

## 2. 创建环境并安装

先记录解释器，避免以后无法说明实验环境：

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r stage2_ai_isp/requirements.txt
```

Linux/macOS 只需把激活命令换成：

```bash
source .venv/bin/activate
```

当前仓库已验证环境为 Windows x64、Python 3.14.4、PyTorch 2.12.0+cpu。
这只是已验证组合，不是唯一支持组合。安装其他 PyTorch/CUDA 组合时，应记录 Python、
PyTorch、CUDA、设备和安装来源；不要只写“用了 GPU”。

如果 Windows 终端中的中文测试说明乱码，先执行：

```powershell
chcp 65001
$env:PYTHONUTF8="1"
```

乱码只影响终端显示时，不等于数值测试失败；仍要以测试退出码和 `OK` 为准。

## 3. 路径 A：最小 smoke

### 3.1 跑回归测试

```powershell
$env:PYTHONPATH="stage2_ai_isp"
python -m unittest discover -s stage2_ai_isp/tests -v
```

当前基线预期为 16 个测试通过。测试数以后可能增加，因此最终判据是进程退出码为 0，
而不是永远等于 16。

### 3.2 生成无需下载的数据

```powershell
python stage2_ai_isp/scripts/03_prepare_paired_rgb_smoke.py --count 12 --size 256 --sigma 0.08
```

检查以下目录同时存在 noisy/clean 图片：

```text
stage2_ai_isp/runs/paired_rgb_smoke/noisy/
stage2_ai_isp/runs/paired_rgb_smoke/clean/
```

### 3.3 训练最小模型

```powershell
python stage2_ai_isp/scripts/01_train_toy_rgb.py --config stage2_ai_isp/configs/paired_rgb_smoke_dncnn_l2.yaml
```

至少检查四类输出：

```text
stage2_ai_isp/runs/paired_rgb_smoke_dncnn_l2/config.yaml
stage2_ai_isp/runs/paired_rgb_smoke_dncnn_l2/metrics.csv
stage2_ai_isp/runs/paired_rgb_smoke_dncnn_l2/checkpoints/
stage2_ai_isp/runs/paired_rgb_smoke_dncnn_l2/vis/
```

通过标准：能说明输入、GT、output、loss 和 validation 的关系，并能从 `metrics.csv`
和三联图判断训练链路是否正常。只看到命令退出码为 0，不算完成。

## 4. 路径 B：SIDD tiny

从 [SIDD 官方页面](https://abdokamel.github.io/sidd/)获取
`SIDD_Small_sRGB_Only.zip`。遵守数据集页面的许可和使用条件；仓库不重新分发原始数据。

解压后确认存在以下层级，再运行准备脚本：

```text
SIDD_Small_sRGB_Only/Data/<scene>/
```

```powershell
python stage2_ai_isp/scripts/07_prepare_sidd_small_subset.py `
  --source-root path/to/SIDD_Small_sRGB_Only/Data `
  --output-dir stage2_ai_isp/datasets/sidd_tiny `
  --train-count 80 --val-count 20 --test-count 20 --crop-size 512
python stage2_ai_isp/scripts/23_audit_dataset_splits.py
```

通过标准：审计退出码为 0，且 `manifest.csv` 中 train/val/test 的 source scene 不交叉。
这里处理的是 ISP 后 paired sRGB，不是 sensor RAW，也不是 SIDD 官方 benchmark 提交协议。

## 5. 运行成本和停止条件

- 回归测试和 smoke 用于分钟级链路检查，优先在 CPU 上运行。
- 300/1000/2000-step 的真实数据实验成本依设备而变；第一次运行先记录 20～50 step
  的 wall time，再估算总时长，不在文档中承诺固定分钟数。
- 磁盘至少要容纳原始压缩包、解压数据、tiny 子集、run、checkpoint 和可视化；下载前
  先检查本机剩余空间。
- 出现 shape、颜色顺序、值域、paired 对齐或 split 审计失败时立即停止训练，先修数据链路。

完成 Quickstart 后回到 [`stage2_start_here.md`](stage2_start_here.md)，从 Week 0 正式学习。
