"""生成 pipeline golden 数据：C++ golden test 会逐阶段读取这些 CPF32 文件做回归检查。"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from make_test_vectors import write_cpf32
from noise_model_ref import gaussian_kernel_1d
from tone_mapping_ref import apply_gamma, tone_map_luminance


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "pipeline_golden"


def make_input(width: int = 9, height: int = 7) -> np.ndarray:
    y, x = np.indices((height, width), dtype=np.float32)
    gx = x / np.float32(width - 1)
    gy = y / np.float32(height - 1)
    texture = ((x * 7.0 + y * 11.0) % 13.0) / 130.0
    base = 0.04 + 0.72 * gx + 0.31 * gy + texture
    rgb = np.stack(
        [
            base,
            base * 0.91 + 0.035,
            base * 0.79 + 0.075,
        ],
        axis=-1,
    )
    return rgb.astype(np.float32)


def gaussian_reflect101(image: np.ndarray, radius: int = 1, sigma: float = 1.0) -> np.ndarray:
    kernel = gaussian_kernel_1d(radius, sigma)
    padded_x = np.pad(image, ((0, 0), (radius, radius), (0, 0)), mode="reflect")
    temp = np.zeros_like(image, dtype=np.float32)
    for i, weight in enumerate(kernel):
        temp += np.float32(weight) * padded_x[:, i : i + image.shape[1], :]

    padded_y = np.pad(temp, ((radius, radius), (0, 0), (0, 0)), mode="reflect")
    output = np.zeros_like(image, dtype=np.float32)
    for i, weight in enumerate(kernel):
        output += np.float32(weight) * padded_y[i : i + image.shape[0], :, :]
    return output.astype(np.float32)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source = make_input()
    denoised = gaussian_reflect101(source)
    tone_mapped = tone_map_luminance(denoised, "reinhard", exposure=0.42)
    output = apply_gamma(tone_mapped, gamma=2.2)

    write_cpf32(OUTPUT_DIR / "pipeline_source.cpf32", source)
    write_cpf32(OUTPUT_DIR / "pipeline_denoised.cpf32", denoised)
    write_cpf32(OUTPUT_DIR / "pipeline_tone_mapped.cpf32", tone_mapped)
    write_cpf32(OUTPUT_DIR / "pipeline_output.cpf32", output)


if __name__ == "__main__":
    main()
