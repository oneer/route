"""练习：不查看项目答案，补全最小 RGGB bilinear demosaic。"""

from __future__ import annotations

import numpy as np


def demosaic_rggb(raw: np.ndarray) -> np.ndarray:
    """输入 H×W Bayer，输出 H×W×3 float32 RGB。"""
    raise NotImplementedError("补全 mask、插值和真实采样值保留")


def self_check() -> None:
    constant = np.full((8, 8), 512, dtype=np.uint16)
    output = demosaic_rggb(constant)
    assert output.shape == (8, 8, 3)
    assert output.dtype == np.float32
    np.testing.assert_allclose(output, 512.0, atol=1e-5)


if __name__ == "__main__":
    self_check()
