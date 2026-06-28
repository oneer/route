from __future__ import annotations

import numpy as np

from soft_isp.awb_advanced import compare_awb_methods, shades_of_gray_gains, white_patch_gains
from soft_isp.iq_metrics import approximate_dynamic_range_db, clipping_fractions, edge_mtf50_proxy, roi_snr_db


def test_iq_metrics_return_finite_values() -> None:
    raw = np.tile(np.linspace(64, 1023, 64, dtype=np.float32), (64, 1))
    clip = clipping_fractions(raw, black_level=64, white_level=1023, margin=1)
    snr = roi_snr_db(raw[:, 8:24], black_level=64)
    dr = approximate_dynamic_range_db(1023, 64, snr["noise_std"])
    mtf = edge_mtf50_proxy(raw, (8, 8, 32, 32))

    assert 0.0 <= clip["near_black_fraction"] <= 1.0
    assert 0.0 <= clip["near_white_fraction"] <= 1.0
    assert np.isfinite(snr["snr_db"])
    assert dr > 0.0
    assert mtf["mtf50_proxy_cyc_per_px"] >= 0.0


def test_awb_methods_keep_green_gain_as_anchor() -> None:
    rgb = np.ones((16, 16, 3), dtype=np.float32)
    rgb[..., 0] *= 0.5
    rgb[..., 1] *= 1.0
    rgb[..., 2] *= 2.0

    wp = white_patch_gains(rgb)
    sog = shades_of_gray_gains(rgb)
    compared = compare_awb_methods(rgb, white_level=4.0)

    assert np.isclose(wp[1], 1.0)
    assert np.isclose(sog[1], 1.0)
    assert set(compared) == {"none", "gray_world", "white_patch", "shades_of_gray"}
