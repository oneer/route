from __future__ import annotations

from pathlib import Path

import rawpy


def main() -> None:
    raw_dir = Path("data/raw")
    out_path = Path("materials/datasets/starter_sample_metadata.md")
    rows = []

    for raw_path in sorted(raw_dir.glob("S*.dng")):
        with rawpy.imread(str(raw_path)) as raw:
            visible = raw.raw_image_visible
            rows.append(
                {
                    "file": raw_path.name,
                    "shape": f"{visible.shape[1]}x{visible.shape[0]}",
                    "dtype": str(visible.dtype),
                    "black": "/".join(str(v) for v in raw.black_level_per_channel),
                    "white": str(raw.white_level),
                    "color_desc": raw.color_desc.decode(errors="replace"),
                    "raw_min": str(int(visible.min())),
                    "raw_max": str(int(visible.max())),
                    "raw_mean": f"{float(visible.mean()):.2f}",
                }
            )

    lines = [
        "# FiveK Starter 样张 Metadata",
        "",
        "| 文件 | shape | dtype | black level | white level | color desc | raw min | raw max | raw mean |",
        "|---|---:|---|---|---:|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {file} | {shape} | {dtype} | {black} | {white} | {color_desc} | {raw_min} | {raw_max} | {raw_mean} |".format(
                **row
            )
        )

    lines.extend(
        [
            "",
            "说明：Bayer 排列需要结合 `raw_pattern` 和 `color_desc` 判断。当前表只做启动阶段的快速索引。",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()

