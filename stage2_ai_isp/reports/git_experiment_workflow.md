# Git 与实验工程规范

每个实验遵循：

```text
一个问题 -> 一份 config -> 一个 run -> 一段结论 -> 一个 commit
```

提交前检查：

1. 不提交原始数据、checkpoint、TensorBoard event 和构建目录。
2. 提交 config、代码、汇总 CSV 和必要的小尺寸图。
3. commit message 写清变量，例如：
   `stage2: compare charbonnier against mse on fixed dncnn baseline`
4. 报告记录 commit SHA、seed、依赖版本和机器信息。
5. 不在同一实验中同时修改数据、loss、模型和训练预算。

推荐分支：

```text
stage2/exercise-dataset
stage2/ablation-charbonnier
stage2/onnx-alignment
```

模型或指标代码修改后，先运行：

```powershell
$env:PYTHONPATH="stage2_ai_isp"
python -m unittest discover -s stage2_ai_isp/tests -v
```

