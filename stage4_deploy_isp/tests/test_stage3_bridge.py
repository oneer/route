"""Stage 3/Stage 4 桥接格式及张量工具的回归测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from stage4_deploy_isp.deploy.stage3_bridge import hwc_to_nchw, psnr, read_cpf32, write_cpf32


class Stage3BridgeTests(unittest.TestCase):
    def test_cpf32_round_trip(self) -> None:
        """验证 CPF32 写入后读取可逐元素无损还原。"""
        array = np.arange(4 * 5 * 3, dtype=np.float32).reshape(4, 5, 3) / 100.0
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "sample.cpf32"
            write_cpf32(path, array)
            restored = read_cpf32(path)
        np.testing.assert_array_equal(restored, array)

    def test_layout_and_psnr_helpers(self) -> None:
        """验证 HWC→NCHW 形状，以及完全相同时的 PSNR 上限。"""
        array = np.zeros((4, 5, 3), dtype=np.float32)
        self.assertEqual(hwc_to_nchw(array).shape, (1, 3, 4, 5))
        self.assertEqual(psnr(array, array), 80.0)
