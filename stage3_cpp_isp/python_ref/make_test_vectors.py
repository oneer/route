"""生成 Stage 3 的基础 CPF32 测试向量、manifest 和预览图，供 C++ 测试/工具复用。"""

from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "input"
REFERENCE_DIR = ROOT / "data" / "reference"
FIGURE_DIR = ROOT / "reports" / "figures" / "week0"


def write_cpf32(path: Path, array: np.ndarray) -> None:
    array = np.asarray(array, dtype=np.float32)
    if array.ndim == 2:
        h, w = array.shape
        c = 1
        payload = array.reshape(h, w, 1)
    elif array.ndim == 3:
        h, w, c = array.shape
        payload = array
    else:
        raise ValueError(f"expected 2D or 3D array, got shape {array.shape}")

    with path.open("wb") as f:
        f.write(f"CPF32\n{w} {h} {c}\n".encode("ascii"))
        f.write(payload.astype("<f4", copy=False).tobytes(order="C"))


def make_pattern(name: str, width: int, height: int, channels: int, rng: np.random.Generator) -> np.ndarray:
    if name == "zeros":
        base = np.zeros((height, width), dtype=np.float32)
    elif name == "ones":
        base = np.ones((height, width), dtype=np.float32)
    elif name == "checkerboard":
        y, x = np.indices((height, width))
        base = ((x + y) % 2).astype(np.float32)
    elif name == "gradient_x":
        base = np.tile(np.linspace(0.0, 1.0, width, dtype=np.float32), (height, 1))
    elif name == "gradient_y":
        base = np.tile(np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None], (1, width))
    elif name == "random":
        base = rng.random((height, width), dtype=np.float32)
    elif name == "dark_patch":
        base = np.full((height, width), 0.08, dtype=np.float32)
        y0, y1 = height // 4, 3 * height // 4
        x0, x1 = width // 4, 3 * width // 4
        base[y0:y1, x0:x1] = 0.015
    elif name == "highlight_patch":
        base = np.full((height, width), 0.35, dtype=np.float32)
        y0, y1 = height // 4, 3 * height // 4
        x0, x1 = width // 4, 3 * width // 4
        base[y0:y1, x0:x1] = 1.0
    else:
        raise ValueError(f"unknown pattern: {name}")

    if channels == 1:
        return base

    stacked = np.repeat(base[:, :, None], channels, axis=2)
    if channels >= 3:
        stacked[:, :, 1] = np.clip(stacked[:, :, 1] * 0.92 + 0.04, 0.0, 1.0)
        stacked[:, :, 2] = np.clip(stacked[:, :, 2] * 0.84 + 0.08, 0.0, 1.0)
    if channels == 4:
        stacked[:, :, 3] = np.clip(stacked[:, :, 0] * 0.75 + 0.12, 0.0, 1.0)
    return stacked.astype(np.float32)


def save_preview(path: Path, array: np.ndarray) -> None:
    array = np.asarray(array)
    if array.ndim == 3:
        preview = array[:, :, :3] if array.shape[2] >= 3 else array[:, :, 0]
    else:
        preview = array

    preview = np.clip(preview, 0.0, 1.0)
    image = (preview * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(image).save(path)


def write_contact_sheet(previews: list[tuple[str, Path]], output_path: Path) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(12, 6))
    for ax, (title, path) in zip(axes.ravel(), previews):
        ax.imshow(Image.open(path), cmap="gray", vmin=0, vmax=255)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    for ax in axes.ravel()[len(previews):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260615)
    parser.add_argument("--include-large", action="store_true", help="also write 1080P and 4K vectors")
    args = parser.parse_args()

    for directory in [INPUT_DIR, REFERENCE_DIR, FIGURE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    cases: list[dict[str, object]] = []
    preview_paths: list[tuple[str, Path]] = []
    patterns = [
        "zeros",
        "ones",
        "checkerboard",
        "gradient_x",
        "gradient_y",
        "random",
        "dark_patch",
        "highlight_patch",
    ]
    shapes = [(8, 8, 1), (17, 19, 1), (128, 128, 1), (128, 128, 3), (128, 128, 4)]
    if args.include_large:
        shapes.extend([(1920, 1080, 1), (3840, 2160, 1)])

    for width, height, channels in shapes:
        for pattern in patterns:
            array = make_pattern(pattern, width, height, channels, rng)
            stem = f"{pattern}_{width}x{height}x{channels}"
            input_path = INPUT_DIR / f"{stem}.cpf32"
            reference_path = REFERENCE_DIR / f"{stem}_identity.cpf32"
            write_cpf32(input_path, array)
            write_cpf32(reference_path, array)

            stats = {
                "name": stem,
                "pattern": pattern,
                "width": width,
                "height": height,
                "channels": channels,
                "min": float(np.min(array)),
                "max": float(np.max(array)),
                "mean": float(np.mean(array)),
                "std": float(np.std(array)),
                "input": str(input_path.relative_to(ROOT)),
                "reference": str(reference_path.relative_to(ROOT)),
            }
            cases.append(stats)

            if width == 128 and height == 128 and channels == 1:
                preview_path = FIGURE_DIR / f"{stem}.png"
                save_preview(preview_path, array)
                preview_paths.append((pattern, preview_path))

    manifest_json = ROOT / "data" / "test_vectors_manifest.json"
    manifest_csv = ROOT / "data" / "test_vectors_manifest.csv"
    manifest_json.write_text(json.dumps(cases, indent=2), encoding="utf-8")
    with manifest_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(cases[0].keys()))
        writer.writeheader()
        writer.writerows(cases)

    write_contact_sheet(preview_paths, FIGURE_DIR / "week0_test_vectors_contact_sheet.png")
    print(f"wrote {len(cases)} test vectors")
    print(f"manifest: {manifest_json}")
    print(f"figures: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
