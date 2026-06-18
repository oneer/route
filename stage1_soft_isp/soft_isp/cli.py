"""命令行脚本共用的小工具。"""

from __future__ import annotations

import glob
from pathlib import Path


def expand_paths(paths: list[Path]) -> list[Path]:
    """在 Windows PowerShell 和 POSIX shell 下统一展开通配符路径。"""
    expanded: list[Path] = []
    for path in paths:
        text = str(path)
        if any(char in text for char in "*?[]"):
            expanded.extend(Path(match) for match in glob.glob(text))
        else:
            expanded.append(path)
    return sorted(dict.fromkeys(expanded))
