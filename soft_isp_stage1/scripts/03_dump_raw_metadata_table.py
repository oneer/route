"""RAW 元数据表生成器 —— 扫描 DNG 文件并生成 Markdown 格式的概览表格。

用法:
    python 03_dump_raw_metadata_table.py

功能:
    读取 data/raw/ 目录下所有 `S*.dng` 文件（即 FiveK Starter 样张），提取每幅图像的关键元数据：
        - 文件名、分辨率形状、数据类型
        - 黑电平、白电平、色彩描述字符串
        - raw 像素的最小值、最大值、均值

    将所有记录汇总为一张 Markdown 表格，写入 materials/datasets/starter_sample_metadata.md，
    方便在项目文档中直接嵌入查看，便于快速了解数据集的数值范围与传感器特性。

    注意：Bayer 排列（RGGB/BGGR 等）需要结合 raw_pattern 和 color_desc 才能最终确定，
    本表仅做启动阶段的快速索引，不包含完整的 Bayer 推断结果。
"""

from __future__ import annotations  # PEP 604: 允许在类型注解中使用管道语法

from pathlib import Path  # 面向对象的文件路径处理

import rawpy  # libraw 的 Python 绑定，用于读取 RAW/DNG 文件


def main() -> None:
    """遍历 FiveK Starter 样张，生成 Markdown 格式的元数据概览表。"""

    # 输入目录：存放 FiveK Starter 样张 DNG 文件
    raw_dir = Path("data/raw")

    # 输出路径：生成的 Markdown 表格文件
    out_path = Path("materials/datasets/starter_sample_metadata.md")

    # 收集每个文件的元数据行
    rows = []

    # 遍历所有以 "S" 开头的 DNG 文件（FiveK Starter 样张命名格式）
    # sorted() 确保输出顺序稳定可复现
    for raw_path in sorted(raw_dir.glob("S*.dng")):
        with rawpy.imread(str(raw_path)) as raw:
            # raw_image_visible 是去除光学黑边后的有效像素，类型为 uint16
            visible = raw.raw_image_visible

            # 组装一行元数据记录
            rows.append(
                {
                    "file": raw_path.name,
                    # shape 格式为 "宽x高"（注意 numpy shape 是 (高, 宽)，需要交换）
                    "shape": f"{visible.shape[1]}x{visible.shape[0]}",
                    # dtype 显示像素的数据类型（通常是 uint16）
                    "dtype": str(visible.dtype),
                    # 各通道黑电平，用 "/" 分隔，例如 "512/512/512/512"
                    "black": "/".join(str(v) for v in raw.black_level_per_channel),
                    # 全局白电平（饱和阈值）
                    "white": str(raw.white_level),
                    # 色彩描述字符串，如 "RGBG"；errors="replace" 防止非 UTF-8 字节导致崩溃
                    "color_desc": raw.color_desc.decode(errors="replace"),
                    # raw 像素最小值，反映暗部黑电平偏移
                    "raw_min": str(int(visible.min())),
                    # raw 像素最大值，反映是否有像素接近饱和
                    "raw_max": str(int(visible.max())),
                    # raw 像素均值，粗略反映场景的平均亮度
                    "raw_mean": f"{float(visible.mean()):.2f}",
                }
            )

    # ---- 构建 Markdown 表格 ----
    lines = [
        "# FiveK Starter 样张 Metadata",
        "",
        # 表头：第二行的冒号控制该列的对齐方式
        # :--- = 左对齐，---: = 右对齐，---= 默认
        "| 文件 | shape | dtype | black level | white level | color desc | raw min | raw max | raw mean |",
        "|---|---:|---|---|---:|---|---:|---:|---:|",
    ]

    # 逐行填入数据
    for row in rows:
        lines.append(
            "| {file} | {shape} | {dtype} | {black} | {white} | {color_desc} | {raw_min} | {raw_max} | {raw_mean} |".format(
                **row
            )
        )

    # 追加说明信息
    lines.extend(
        [
            "",
            "说明：Bayer 排列需要结合 `raw_pattern` 和 `color_desc` 判断。当前表只做启动阶段的快速索引。",
        ]
    )

    # 写入文件（UTF-8 编码，末尾加换行符）
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_path)  # 输出路径到 stdout


if __name__ == "__main__":
    main()

