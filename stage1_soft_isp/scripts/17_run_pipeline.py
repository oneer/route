"""从 YAML 配置运行统一 Soft-ISP Pipeline，并保存可检查的中间结果。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import imageio.v3 as iio
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from soft_isp.pipeline import load_config, run_pipeline


# 中文注释：save_outputs 将 pipeline 的最终预览、中间阶段和 metadata 分别保存，方便逐阶段排查。
def save_outputs(result: dict, output_dir: Path, save_intermediate: bool, save_numpy: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    iio.imwrite(output_dir / "preview.png", result["preview"])
    (output_dir / "metadata.json").write_text(
        json.dumps(result["metadata"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not save_intermediate:
        return
    for name, array in result["stages"].items():
        if save_numpy:
            np.save(output_dir / f"{name}.npy", array)
        if name == "preview":
            continue
        summary = {
            "shape": list(array.shape),
            "dtype": str(array.dtype),
            "min": float(np.min(array)),
            "max": float(np.max(array)),
            "mean": float(np.mean(array)),
        }
        (output_dir / f"{name}.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


# 中文注释：脚本入口：解析命令行参数，调用本文件的处理流程，并把结果写入输出目录。
def main() -> None:
    parser = argparse.ArgumentParser(description="Run the config-driven Stage 1 Soft-ISP pipeline.")
    parser.add_argument("raw_path", type=Path)
    parser.add_argument("--config", type=Path, default=Path("configs/default.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/pipeline"))
    args = parser.parse_args()

    config = load_config(args.config)
    result = run_pipeline(args.raw_path, config)
    output_config = config.get("output", {})
    sample_dir = args.output_dir / args.raw_path.stem
    save_outputs(
        result,
        sample_dir,
        save_intermediate=bool(output_config.get("save_intermediate", True)),
        save_numpy=bool(output_config.get("save_numpy", False)),
    )
    print(sample_dir)


if __name__ == "__main__":
    main()
