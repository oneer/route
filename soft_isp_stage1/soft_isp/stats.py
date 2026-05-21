from __future__ import annotations

import numpy as np


def describe_array(array: np.ndarray) -> dict[str, float | str | tuple[int, ...]]:
    """Return basic numeric statistics for a RAW or image array."""
    data = np.asarray(array)
    return {
        "shape": data.shape,
        "dtype": str(data.dtype),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        "p01": float(np.percentile(data, 1)),
        "p50": float(np.percentile(data, 50)),
        "p99": float(np.percentile(data, 99)),
    }


def split_bayer(raw: np.ndarray, pattern: str = "RGGB") -> dict[str, np.ndarray]:
    """Split a Bayer mosaic into R, Gr, Gb and B channels."""
    pattern = pattern.upper()
    if pattern not in {"RGGB", "BGGR", "GRBG", "GBRG"}:
        raise ValueError(f"Unsupported Bayer pattern: {pattern}")

    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }[pattern]

    return {name: raw[y::2, x::2] for name, (y, x) in positions.items()}

