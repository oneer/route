"""练习：给合成 Bayer RAW 注入坏点并评价 DPC。

不要导入 ``soft_isp.dpc.detect_defects`` 作为你的检测实现。可以在完成后用它作对照。
"""

from __future__ import annotations

import numpy as np


def inject_defects(raw: np.ndarray, coordinates: list[tuple[int, int]], value: int) -> np.ndarray:
    result = raw.copy()
    for y, x in coordinates:
        result[y, x] = value
    return result


def detect_defects_exercise(raw: np.ndarray, threshold: int) -> np.ndarray:
    """返回全分辨率布尔 mask。要求只比较同色 Bayer 邻域。"""
    raise NotImplementedError("实现同色邻域坏点检测")


def precision_recall(mask: np.ndarray, truth: set[tuple[int, int]]) -> tuple[float, float]:
    """计算 precision 和 recall。"""
    raise NotImplementedError("根据检测 mask 和注入坐标计算 precision/recall")


if __name__ == "__main__":
    base = np.full((32, 32), 1000, dtype=np.uint16)
    truth = {(8, 8), (12, 20), (22, 6), (24, 24)}
    damaged = inject_defects(base, sorted(truth), 6000)
    detected = detect_defects_exercise(damaged, threshold=500)
    precision, recall = precision_recall(detected, truth)
    print({"precision": precision, "recall": recall, "detected": int(detected.sum())})
    assert recall >= 0.75
