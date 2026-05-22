"""软 ISP 统计工具函数集合。

本模块提供三个核心辅助函数，是整个 Stage 1 脚本的共用基础设施：
    - bayer_pattern_from_rawpy:  从 rawpy 元数据推断标准 Bayer 排列字符串
    - describe_array:            计算 numpy 数组的统计描述
    - split_bayer:              将 Bayer 马赛克图像按通道拆分为 R/Gr/Gb/B

所有函数均为纯函数（无副作用，输入不变），适合在数据处理流水线中链式调用。
"""

from __future__ import annotations  # PEP 604: 允许在类型注解中使用管道语法

import numpy as np  # 数值计算库，操作 RAW 数据的核心依赖


def bayer_pattern_from_rawpy(raw_pattern: np.ndarray, color_desc: str) -> str:
    """根据 rawpy 的 raw_pattern 和 color_desc 推断标准 Bayer 排列字符串。

    Bayer 传感器上的每个像素只记录一种颜色，按 2x2 循环排列。常见的四种排列方式为
    RGGB、BGGR、GRBG、GBRG。rawpy 用两套元数据描述这个排列：

        - raw_pattern:  一个 2x2 的整数矩阵，每个元素是 color_desc 中的索引
                        例如 [[0, 1], [1, 2]] 表示第一行是 color_desc[0], color_desc[1]
                        第二行是 color_desc[1], color_desc[2]
        - color_desc:   字符串（如 "RGBG"），表示 raw_pattern 中数字对应的颜色字母

    由于两个绿色通道（Gr 和 Gb）在 Bayer 阵列中物理位置不同，本函数会区分它们：
        第一个遇到的 G 记为 "Gr"（Green on Red row），第二个记为 "Gb"（Green on Blue row）。

    参数:
        raw_pattern: rawpy 返回的 raw_pattern 属性，shape 应为 (2, 2)
        color_desc:  rawpy 返回的 color_desc 属性解码后的字符串，如 "RGBG"

    返回:
        标准 Bayer 字符串："RGGB" / "BGGR" / "GRBG" / "GBRG" 之一
        其中 G 在归一化时已合并（去掉了 r/b 后缀），因为后续 split_bayer 等函数
        只关心宏观的 Bayer 模式，不关心具体哪个 Green 在哪行

    异常:
        ValueError: raw_pattern shape 不是 (2, 2) 或无法识别为四种标准模式之一
    """
    pattern = np.asarray(raw_pattern)

    # 只支持 2x2 的 Bayer 模式（绝大多数相机传感器采用此模式）
    if pattern.shape != (2, 2):
        raise ValueError(f"Unsupported raw_pattern shape: {pattern.shape}")

    # 遍历 2x2 矩阵中的 4 个像素位置，将数字索引映射为颜色字母
    colors = []
    green_count = 0  # 用于区分第一个 G（Gr）和第二个 G（Gb）
    for color_index in pattern.ravel():  # ravel 按行展开为 [top-left, top-right, bottom-left, bottom-right]
        # 将数字索引转换为 color_desc 中的颜色字符
        color = color_desc[int(color_index)]
        if color == "G":
            # 区分两个绿色通道：先遇到的为 Gr（在 R 行），后遇到的为 Gb（在 B 行）
            color = "Gr" if green_count == 0 else "Gb"
            green_count += 1
        colors.append(color)

    # 将带后缀的 G 合并回普通 G，用于与标准模式做比较
    # 例如 ["R", "Gr", "Gb", "B"] → "RGGB"
    normalized = "".join("G" if color.startswith("G") else color for color in colors)
    if normalized not in {"RGGB", "BGGR", "GRBG", "GBRG"}:
        raise ValueError(f"Unsupported Bayer pattern from metadata: {normalized}")
    return normalized


def describe_array(array: np.ndarray) -> dict[str, float | str | tuple[int, ...]]:
    """计算 numpy 数组的基本统计描述。

    返回一个字典，包含数组的形状、数据类型、以及像素值的分布信息。
    主要用于 RAW 图像的初步检查——快速了解像素的取值范围、集中趋势和离散程度。

    参数:
        array: 任意维度的 numpy 数组（通常是 uint16 的 raw 数据）

    返回:
        包含以下键的字典：
            - shape:   数组形状 (H, W)
            - dtype:   数据类型字符串，如 "uint16"
            - min:     像素最小值
            - max:     像素最大值
            - mean:    像素均值
            - std:     像素标准差（离散程度）
            - p01:     第 1 百分位数（暗部下界）
            - p50:     第 50 百分位数（中位数）
            - p99:     第 99 百分位数（亮部上界，用于检测过曝）

        所有数值型统计均转换为 Python float，便于 JSON 序列化输出。
    """
    data = np.asarray(array)  # 确保输入被转换为 numpy 数组
    return {
        "shape": data.shape,
        "dtype": str(data.dtype),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "std": float(np.std(data)),
        # 百分位数比 min/max 更稳健，不受少数极端值干扰
        "p01": float(np.percentile(data, 1)),
        "p50": float(np.percentile(data, 50)),
        "p99": float(np.percentile(data, 99)),
    }


def split_bayer(raw: np.ndarray, pattern: str = "RGGB") -> dict[str, np.ndarray]:
    """将 Bayer 马赛克图像按颜色通道拆分为四个独立的子数组。

    Bayer 传感器每个像素只记录一种颜色，排列方式为 2x2 重复模式：

        列 0  列 1  列 2  列 3  ...
        行 0: R   Gr    R    Gr    ...
        行 1: Gb  B     Gb   B     ...
        行 2: R   Gr    R    Gr    ...
        ...   (以 RGGB 模式为例)

    拆分后，每个通道的子数组大小为 (H/2, W/2)，即原图分辨率的一半。

    参数:
        raw:     二维 numpy 数组，完整的 Bayer raw 数据
        pattern: Bayer 排列模式，支持 "RGGB"/"BGGR"/"GRBG"/"GBRG"（不区分大小写）

    返回:
        字典，包含四个通道的子数组：
            {"R": ndarray, "Gr": ndarray, "Gb": ndarray, "B": ndarray}
        其中 Gr 是"与 R 同行的 Green"，Gb 是"与 B 同行的 Green"

    原理:
        利用 numpy 的步长切片 raw[y::2, x::2] 从 2x2 模式中提取特定位置的像素：
            - y=0, x=0: 偶数行、偶数列 → 左上角像素
            - y=0, x=1: 偶数行、奇数列 → 右上角像素
            - y=1, x=0: 奇数行、偶数列 → 左下角像素
            - y=1, x=1: 奇数行、奇数列 → 右下角像素
        不同的 Bayer 模式只是这四个位置对应的颜色不同。
    """
    pattern = pattern.upper()  # 统一转大写，兼容小写输入
    if pattern not in {"RGGB", "BGGR", "GRBG", "GBRG"}:
        raise ValueError(f"Unsupported Bayer pattern: {pattern}")

    # 四种标准 Bayer 模式中，每个通道在 2x2 块中的坐标 (行偏移, 列偏移)
    # 例如 RGGB 模式：(0,0)→R, (0,1)→Gr, (1,0)→Gb, (1,1)→B
    positions = {
        "RGGB": {"R": (0, 0), "Gr": (0, 1), "Gb": (1, 0), "B": (1, 1)},
        "BGGR": {"B": (0, 0), "Gb": (0, 1), "Gr": (1, 0), "R": (1, 1)},
        "GRBG": {"Gr": (0, 0), "R": (0, 1), "B": (1, 0), "Gb": (1, 1)},
        "GBRG": {"Gb": (0, 0), "B": (0, 1), "R": (1, 0), "Gr": (1, 1)},
    }[pattern]

    # raw[y::2, x::2] 从坐标 (y, x) 开始，每 2 步取一个像素
    # 这样就提取出了该通道在整个 Bayer 阵列中的所有像素
    return {name: raw[y::2, x::2] for name, (y, x) in positions.items()}
