"""
models 子包 — 神经网络模型定义与构建工厂。

包含三种 CNN backbone：
    - TinyCNN:  最简 baseline（3 层卷积），用于快速验证训练管线
    - DnCNN:    小型 DnCNN 风格去噪器，支持残差学习（预测噪声而非干净图）
    - UNet:     紧凑型 UNet，Encoder-Decoder + Skip Connection，适合图像恢复任务

模型工厂 build_model(config) 根据配置字典的 "name" 字段自动选择并构建模型。
"""

from ai_isp.models.dncnn import DnCNN
from ai_isp.models.tiny_cnn import TinyCNN
from ai_isp.models.unet import UNet


def build_model(config: dict):
    """根据配置字典构建神经网络模型。

    支持的模型名称（config["name"]，不区分大小写）：
        - "tiny_cnn": 3 层纯卷积，参数最少，训练最快
        - "dncnn":    DnCNN 风格去噪器，支持残差学习
        - "unet":     Encoder-Decoder + Skip Connection 结构

    参数：
        config: 模型配置字典，必须包含 "name" 键。可选键因模型而异：
                - TinyCNN/DnCNN: in_channels, out_channels, features
                - DnCNN 额外:     depth, residual
                - UNet:           in_channels, out_channels, base_channels

    返回：
        构建好的 nn.Module 实例

    异常：
        ValueError: config["name"] 不是已知模型名
    """
    name = config["name"].lower()

    if name == "tiny_cnn":
        return TinyCNN(
            in_channels=config.get("in_channels", 3),     # 输入通道数，默认 3（RGB）
            out_channels=config.get("out_channels", 3),   # 输出通道数，默认 3（RGB）
            features=config.get("features", 32),          # 中间特征通道数
        )

    if name == "dncnn":
        return DnCNN(
            in_channels=config.get("in_channels", 3),
            out_channels=config.get("out_channels", 3),
            features=config.get("features", 32),          # 中间特征通道数
            depth=config.get("depth", 5),                  # 卷积层数（含首尾）
            residual=config.get("residual", True),         # 是否使用残差学习
        )

    if name == "unet":
        return UNet(
            in_channels=config.get("in_channels", 3),
            out_channels=config.get("out_channels", 3),
            base_channels=config.get("base_channels", 16),  # 基础通道数（每层翻倍）
        )

    raise ValueError(f"Unknown model: {config['name']}")
