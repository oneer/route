"""配置驱动的最小 Soft-ISP Pipeline。

这个模块只负责组合 ``soft_isp`` 中已有的学习版算法，不隐藏各模块细节。
返回值同时包含最终预览和中间结果，便于测试、调试和参数消融。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rawpy
import yaml

from soft_isp.awb import apply_awb, gray_world_gains
from soft_isp.blc import apply_blc
from soft_isp.ccm import apply_ccm, ccm_from_rawpy_color_matrix
from soft_isp.demosaic import bilinear_demosaic
from soft_isp.dpc import detect_defects, repair_defects
from soft_isp.lsc import apply_lsc
from soft_isp.orientation import apply_rawpy_orientation
from soft_isp.stats import bayer_pattern_from_rawpy
from soft_isp.tone import apply_gamma, normalize_by_percentile, reinhard_tone_map, to_uint8


@dataclass(frozen=True)
class RawContext:
    raw_visible: np.ndarray
    raw_pattern: np.ndarray
    bayer_pattern: str
    black_levels: list[int]
    white_level: int
    display_flip: int
    ccm: np.ndarray


def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Pipeline config must contain a YAML mapping.")
    return config


def read_raw_context(raw_path: str | Path, config: dict[str, Any]) -> RawContext:
    raw_config = config.get("raw", {})
    with rawpy.imread(str(raw_path)) as raw:
        color_desc = raw.color_desc.decode(errors="replace")
        metadata_pattern = bayer_pattern_from_rawpy(raw.raw_pattern, color_desc)
        bayer_pattern = raw_config.get("bayer_pattern") or metadata_pattern

        metadata_black = [int(value) for value in raw.black_level_per_channel]
        black_override = raw_config.get("black_level")
        if black_override is None:
            black_levels = metadata_black
        elif isinstance(black_override, list):
            black_levels = [int(value) for value in black_override]
        else:
            black_levels = [int(black_override)] * len(metadata_black)

        white_level = int(raw_config.get("white_level") or raw.white_level)
        return RawContext(
            raw_visible=raw.raw_image_visible.copy(),
            raw_pattern=raw.raw_pattern.copy(),
            bayer_pattern=str(bayer_pattern).upper(),
            black_levels=black_levels,
            white_level=white_level,
            display_flip=int(raw.sizes.flip),
            ccm=ccm_from_rawpy_color_matrix(raw.color_matrix),
        )


def run_pipeline(raw_path: str | Path, config: dict[str, Any]) -> dict[str, Any]:
    """运行学习版 Pipeline，并返回最终预览、metadata 和所有已启用中间结果。"""
    ctx = read_raw_context(raw_path, config)
    switches = config.get("pipeline", {})
    parameters = config.get("parameters", {})
    stages: dict[str, np.ndarray] = {"raw": ctx.raw_visible}

    raw_stage = ctx.raw_visible
    if switches.get("enable_blc", True):
        raw_stage = apply_blc(raw_stage, ctx.raw_pattern, ctx.black_levels, ctx.white_level)
        stages["blc"] = raw_stage

    if switches.get("enable_dpc", True):
        dpc = parameters.get("dpc", {})
        detection = detect_defects(
            raw_stage,
            ctx.bayer_pattern,
            min_delta=int(dpc.get("min_delta", 1024)),
            mad_k=float(dpc.get("mad_k", 12.0)),
        )
        raw_stage = repair_defects(raw_stage, ctx.bayer_pattern, detection)
        stages["dpc"] = raw_stage

    if switches.get("enable_lsc", True):
        lsc = parameters.get("lsc", {})
        raw_stage, gain_map = apply_lsc(
            raw_stage,
            ctx.bayer_pattern,
            edge_gains=lsc.get("edge_gains"),
            white_level=ctx.white_level,
            power=float(lsc.get("power", 2.0)),
        )
        stages["lsc"] = raw_stage
        stages["lsc_gain"] = gain_map

    if not switches.get("enable_demosaic", True):
        raise ValueError("The learning pipeline needs demosaic enabled to create an RGB output.")
    rgb_stage = bilinear_demosaic(raw_stage, ctx.bayer_pattern)
    stages["demosaic"] = rgb_stage

    if switches.get("enable_awb", True):
        awb = parameters.get("awb", {})
        gains = gray_world_gains(
            rgb_stage,
            low_percentile=float(awb.get("low_percentile", 5.0)),
            high_percentile=float(awb.get("high_percentile", 95.0)),
            max_gain=float(awb.get("max_gain", 8.0)),
        )
        rgb_stage = apply_awb(rgb_stage, gains, white_level=ctx.white_level)
        stages["awb"] = rgb_stage
    else:
        gains = np.ones(3, dtype=np.float32)

    if switches.get("enable_ccm", True):
        rgb_stage = apply_ccm(rgb_stage, ctx.ccm, white_level=ctx.white_level)
        stages["ccm"] = rgb_stage

    tone = parameters.get("tone", {})
    percentile = float(tone.get("percentile", 99.5))
    if switches.get("enable_tone", True):
        method = str(tone.get("method", "percentile")).lower()
        if method == "reinhard":
            rgb_01 = reinhard_tone_map(rgb_stage, percentile=percentile)
        elif method == "percentile":
            rgb_01 = normalize_by_percentile(rgb_stage, percentile=percentile)
        else:
            raise ValueError(f"Unsupported tone method: {method}")
    else:
        rgb_01 = normalize_by_percentile(rgb_stage, percentile=percentile)

    preview = to_uint8(apply_gamma(rgb_01, gamma=float(tone.get("gamma", 2.2))))
    preview = apply_rawpy_orientation(preview, ctx.display_flip)
    stages["preview"] = preview

    return {
        "preview": preview,
        "stages": stages,
        "metadata": {
            "raw_path": str(raw_path),
            "bayer_pattern": ctx.bayer_pattern,
            "black_levels": ctx.black_levels,
            "white_level": ctx.white_level,
            "display_flip": ctx.display_flip,
            "awb_gains": [float(value) for value in gains],
            "ccm": ctx.ccm.tolist(),
        },
    }
