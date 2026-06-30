"""Week 1 可视化脚本：画出 stride、planar 和 border policy 布局示意图。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "reports" / "figures" / "week1"


def draw_stride_layout() -> None:
    width, height, stride = 5, 4, 8
    grid = np.zeros((height, stride), dtype=np.float32)
    grid[:, :width] = 1.0

    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.imshow(grid, cmap="Greys", vmin=0, vmax=1)
    for y in range(height):
        for x in range(stride):
            label = "valid" if x < width else "pad"
            ax.text(x, y, label, ha="center", va="center", fontsize=8,
                    color="white" if x < width else "black")
    ax.set_title("row_stride can be larger than width")
    ax.set_xticks(range(stride))
    ax.set_yticks(range(height))
    ax.set_xlabel("x / storage column")
    ax.set_ylabel("y")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "stride_layout.png", dpi=160)
    plt.close(fig)


def draw_planar4_layout() -> None:
    width, height, channels = 4, 3, 4
    planes = []
    for c in range(channels):
        plane = np.full((height, width), c + 1, dtype=np.float32)
        planes.append(plane)

    fig, axes = plt.subplots(1, channels, figsize=(10, 2.8))
    titles = ["R", "Gr", "Gb", "B"]
    for ax, plane, title in zip(axes, planes, titles):
        ax.imshow(plane, cmap="viridis", vmin=1, vmax=4)
        ax.set_title(f"plane {title}")
        ax.set_xticks(range(width))
        ax.set_yticks(range(height))
    fig.suptitle("planar4 keeps each Bayer-like channel in an independent plane")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "planar4_layout.png", dpi=160)
    plt.close(fig)


def draw_border_mapping() -> None:
    src = np.array([[1, 2, 3, 4]], dtype=np.float32)
    constant = np.array([[0, 0, 1, 2, 3, 4, 0, 0]], dtype=np.float32)
    replicate = np.array([[1, 1, 1, 2, 3, 4, 4, 4]], dtype=np.float32)
    reflect = np.array([[3, 2, 1, 2, 3, 4, 3, 2]], dtype=np.float32)

    rows = [constant, replicate, reflect]
    names = ["constant zero", "replicate", "reflect"]
    fig, axes = plt.subplots(3, 1, figsize=(8, 3.4))
    for ax, row, name in zip(axes, rows, names):
        ax.imshow(row, cmap="magma", vmin=0, vmax=4)
        ax.set_title(name, loc="left", fontsize=9)
        ax.set_xticks(range(row.shape[1]))
        ax.set_yticks([])
        for x, value in enumerate(row.ravel()):
            ax.text(x, 0, str(int(value)), ha="center", va="center", color="white", fontsize=9)
    fig.suptitle("border policy changes the values seen by neighborhood operators")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "border_policy.png", dpi=160)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    draw_stride_layout()
    draw_planar4_layout()
    draw_border_mapping()
    print(f"wrote Week1 figures to {FIGURE_DIR}")


if __name__ == "__main__":
    main()
