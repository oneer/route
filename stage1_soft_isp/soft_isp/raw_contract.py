"""Machine-readable metadata contract for real sensor RAW inputs."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import numpy as np
import rawpy


CONTRACT_VERSION = "1.0"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_float(value: object) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def float_list(values: object) -> list[float | None] | None:
    if values is None:
        return None
    return [finite_float(value) for value in values]


def float_matrix(values: object) -> list[list[float | None]]:
    array = np.asarray(values)
    return [[finite_float(value) for value in row] for row in array]


def bayer_pattern(raw: rawpy.RawPy) -> str | None:
    if raw.raw_pattern is None:
        return None
    color_desc = raw.color_desc.decode("ascii", errors="replace")
    return "".join(color_desc[int(index)] for index in np.asarray(raw.raw_pattern).reshape(-1))


def inspect_raw(path: Path, base: Path) -> dict[str, Any]:
    path = path.resolve()
    base = base.resolve()
    with rawpy.imread(str(path)) as raw:
        sizes = raw.sizes
        white_level = int(raw.white_level)
        entry: dict[str, Any] = {
            "source_file": path.relative_to(base).as_posix(),
            "sha256": sha256(path),
            "file_size_bytes": path.stat().st_size,
            "raw_type": raw.raw_type.name,
            "storage_dtype": str(raw.raw_image_visible.dtype),
            "raw_width": int(sizes.raw_width),
            "raw_height": int(sizes.raw_height),
            "visible_width": int(sizes.width),
            "visible_height": int(sizes.height),
            "top_margin": int(sizes.top_margin),
            "left_margin": int(sizes.left_margin),
            "crop_left_margin": int(sizes.crop_left_margin),
            "crop_top_margin": int(sizes.crop_top_margin),
            "crop_width": int(sizes.crop_width),
            "crop_height": int(sizes.crop_height),
            "pixel_aspect": float(sizes.pixel_aspect),
            "libraw_flip": int(sizes.flip),
            "num_colors": int(raw.num_colors),
            "color_desc": raw.color_desc.decode("ascii", errors="replace"),
            "raw_pattern_indices": (
                np.asarray(raw.raw_pattern, dtype=int).tolist() if raw.raw_pattern is not None else None
            ),
            "bayer_pattern": bayer_pattern(raw),
            "black_level_per_channel": [int(value) for value in raw.black_level_per_channel],
            "white_level": white_level,
            "camera_white_level_per_channel": (
                [int(value) for value in raw.camera_white_level_per_channel]
                if raw.camera_white_level_per_channel is not None
                else None
            ),
            "inferred_signal_bits": white_level.bit_length(),
            "camera_whitebalance": float_list(raw.camera_whitebalance),
            "daylight_whitebalance": float_list(raw.daylight_whitebalance),
            "color_matrix": float_matrix(raw.color_matrix),
            "rgb_xyz_matrix": float_matrix(raw.rgb_xyz_matrix),
            "iso": None,
            "exposure_time_s": None,
            "metadata_gaps": [
                "ISO and exposure time are not exposed by rawpy; preserve as unknown until an EXIF audit is added."
            ],
        }
    return entry


def build_manifest(paths: list[Path], base: Path) -> dict[str, Any]:
    samples = [inspect_raw(path, base) for path in sorted(paths)]
    return {
        "contract_version": CONTRACT_VERSION,
        "source_count": len(samples),
        "field_notes": {
            "inferred_signal_bits": "bit_length(white_level); not a container bit-depth claim",
            "libraw_flip": "rawpy/LibRaw orientation code",
            "null_metadata": "unknown is explicit; values are never silently guessed",
        },
        "samples": samples,
    }


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported contract_version")
    samples = manifest.get("samples")
    if not isinstance(samples, list) or not samples:
        return errors + ["samples must be a non-empty list"]
    if manifest.get("source_count") != len(samples):
        errors.append("source_count does not match samples")

    required = {
        "source_file",
        "sha256",
        "file_size_bytes",
        "raw_type",
        "storage_dtype",
        "raw_width",
        "raw_height",
        "visible_width",
        "visible_height",
        "libraw_flip",
        "raw_pattern_indices",
        "bayer_pattern",
        "black_level_per_channel",
        "white_level",
        "inferred_signal_bits",
        "camera_whitebalance",
        "color_matrix",
        "iso",
        "exposure_time_s",
        "metadata_gaps",
    }
    seen: set[str] = set()
    for index, sample in enumerate(samples):
        label = sample.get("source_file", f"sample[{index}]") if isinstance(sample, dict) else f"sample[{index}]"
        if not isinstance(sample, dict):
            errors.append(f"{label}: sample must be an object")
            continue
        missing = sorted(required - set(sample))
        if missing:
            errors.append(f"{label}: missing fields {', '.join(missing)}")
            continue
        if label in seen:
            errors.append(f"{label}: duplicate source_file")
        seen.add(label)
        if len(sample["sha256"]) != 64:
            errors.append(f"{label}: invalid sha256")
        if sample["file_size_bytes"] <= 0:
            errors.append(f"{label}: invalid file size")
        if min(sample["raw_width"], sample["raw_height"], sample["visible_width"], sample["visible_height"]) <= 0:
            errors.append(f"{label}: invalid dimensions")
        if sample["bayer_pattern"] is not None and len(sample["bayer_pattern"]) != 4:
            errors.append(f"{label}: Bayer pattern must contain four positions")
        black = sample["black_level_per_channel"]
        if not isinstance(black, list) or len(black) != 4:
            errors.append(f"{label}: black_level_per_channel must have four values")
        elif sample["white_level"] <= max(black):
            errors.append(f"{label}: white level must exceed black levels")
        if sample["inferred_signal_bits"] != int(sample["white_level"]).bit_length():
            errors.append(f"{label}: inferred_signal_bits mismatch")
        if not isinstance(sample["metadata_gaps"], list):
            errors.append(f"{label}: metadata_gaps must be a list")
    return errors
