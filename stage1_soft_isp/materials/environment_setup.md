# 可复现环境搭建

## 已验证环境

- Python：3.14.4
- Windows PowerShell
- 依赖版本：见 `requirements.txt`

如果某个固定版本暂时不支持你的 Python，优先创建 Python 3.11 或 3.12 虚拟环境，不要随意混装多个解释器。

## 推荐步骤

```powershell
cd stage1_soft_isp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

只阅读 `openisp/` 中依赖 SciPy 的模块时，再安装：

```powershell
python -m pip install -r requirements-openisp.txt
```

## 安装验证

```powershell
python -c "import cv2, imageio, matplotlib, numpy, rawpy, skimage, yaml; print('dependencies ok')"
python -m unittest discover -s tests -v
python scripts/01_inspect_raw.py data/raw/T01_a0006-IMG_2787.dng
```

## 常见错误

- `ModuleNotFoundError`：确认 `python -m pip` 和运行脚本使用的是同一个 Python。
- PowerShell 禁止激活脚本：可在当前终端临时执行 `Set-ExecutionPolicy -Scope Process Bypass`。
- RAW 无法打开：先检查文件大小和 SHA256，不要直接怀疑算法。
- 大图运行慢：先使用一张样张或合成小数组验证，不要立即跑 14 张全量。
