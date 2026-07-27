"""
metrics 子包 — 图像质量评估指标。

包含：
    - batch_psnr:  批量 PSNR（Peak Signal-to-Noise Ratio，峰值信噪比）
    - batch_ssim:  批量 SSIM（Structural Similarity Index Measure，结构相似度）

两者均在验证阶段使用，默认对 [0, 1] 范围的图像计算。
"""
# 中文说明：图像质量评估指标代码，主要用于批量计算 PSNR/SSIM。

from __future__ import annotations

from typing import TYPE_CHECKING, Any


__all__ = ["batch_psnr", "batch_ssim"]

if TYPE_CHECKING:
    from ai_isp.metrics.psnr_ssim import batch_psnr, batch_ssim


def __getattr__(name: str) -> Any:
    """Lazily import torch-backed metrics.

    Pure NumPy/skimage evaluators such as ``camera_scene`` should remain usable
    in lightweight analysis environments that do not load PyTorch.
    """
    if name in __all__:
        from ai_isp.metrics.psnr_ssim import batch_psnr, batch_ssim

        return {"batch_psnr": batch_psnr, "batch_ssim": batch_ssim}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
