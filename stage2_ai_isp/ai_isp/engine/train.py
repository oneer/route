"""
训练引擎 —— 配置驱动的训练主循环。

本模块是 Stage 2 训练流程的核心入口。train_from_config(config) 接收一个
完整的配置字典，执行完整的训练循环，包括：

    1. 种子设置与设备选择（GPU/CPU 自动检测）
    2. 数据集构建（ToyRGBDenoiseDataset，训练/验证拆分）
    3. 模型构建（通过 build_model 工厂）
    4. 优化器与损失函数设置（AdamW + L1/MSE/Charbonnier）
    5. 训练循环：
        - 前向传播 + 反向传播 + 参数更新
        - 定期日志输出（每 log_every 步）
        - 定期验证 + CSV 记录 + TensorBoard（每 val_every 步）
        - Checkpoint 保存（last.pth + best_psnr.pth）
        - 可视化三联图保存
    6. 基于总步数（而非 epoch 数）的停止条件

配置字典结构（YAML 解析后传入）：
    experiment:
        seed: 42                # 随机种子
        output_dir: "output/"   # 输出目录
    data:
        train_size: 1000        # 训练样本数
        val_size: 100           # 验证样本数
        patch_size: 64          # patch 尺寸
        noise:
            sigma_min: 0.0      # 噪声 sigma 下限
            sigma_max: 0.2      # 噪声 sigma 上限
    model:
        name: "tiny_cnn"        # 模型名称
        ...                     # 模型特定参数
    train:
        steps: 1000             # 总训练步数
        batch_size: 8           # batch size
        learning_rate: 1e-3     # 学习率
        weight_decay: 0.0       # 权重衰减
        loss: "l1"              # "l1"、"mse"/"l2" 或 "charbonnier"
        resume: null            # 可选 checkpoint 路径
        device: "auto"          # 计算设备
        num_workers: 0          # DataLoader 工作进程数
        log_every: 25           # 日志输出间隔（步）
        val_every: 50           # 验证间隔（步）
"""
# 中文说明：从 YAML 配置构建完整训练流程，包括数据、模型、优化器、验证和可视化。

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from ai_isp.data.paired_image_dataset import PairedImageDenoiseDataset
from ai_isp.data.paired_pseudo_raw_dataset import PairedPseudoRawDataset
from ai_isp.data.toy_rgb_dataset import ToyRGBDenoiseDataset
from ai_isp.engine.checkpoint import load_checkpoint, save_checkpoint
from ai_isp.engine.logger import CSVLogger, SummaryWriterOrNoop
from ai_isp.engine.validate import validate
from ai_isp.models import build_model
from ai_isp.utils.seed import seed_everything
from ai_isp.utils.visualization import save_triplet


def resolve_device(name: str) -> torch.device:
    """解析设备名称字符串为 torch.device 对象。

    参数：
        name: 设备名称，支持：
              - "auto": 自动选择（GPU 可用时用 cuda:0，否则用 cpu）
              - "cpu":  强制使用 CPU
              - "cuda": / "cuda:0" / "cuda:1" 等

    返回：
        torch.device 对象
    """
    # 中文说明：根据配置和本机 CUDA 可用性选择训练设备。
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def resolve_project_path(project_root: Path, path: str | Path) -> Path:
    """中文说明：把配置中的相对路径解析到项目根目录下，避免从不同工作目录运行时路径漂移。
    
    输入：project_root、path。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    resolved = Path(path)
    return resolved if resolved.is_absolute() else project_root / resolved


def build_criterion(name: str) -> nn.Module:
    """构建训练损失；未知名称必须报错，避免实验静默用错 loss。"""
    # 中文说明：根据配置名称创建训练损失函数。
    normalized = str(name).lower()
    if normalized == "l1":
        return nn.L1Loss()
    if normalized in {"l2", "mse"}:
        return nn.MSELoss()
    if normalized == "charbonnier":
        return CharbonnierLoss()
    raise ValueError(
        f"Unknown loss '{name}'. Expected one of: l1, l2, mse, charbonnier."
    )


class CharbonnierLoss(nn.Module):
    """平滑 L1：sqrt((prediction-target)^2 + eps^2)。"""
    # 中文说明：平滑版 L1 损失，对异常像素比 L2 更稳，也比普通 L1 更可导。

    def __init__(self, eps: float = 1e-3) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：eps。
        输出：构造函数不返回业务数据，只完成成员变量和子模块初始化。
        """
        super().__init__()
        self.eps = float(eps)

    def forward(self, prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """中文说明：定义前向传播：输入张量如何经过当前模块得到输出张量。
        
        输入：prediction、target。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        difference = prediction - target
        return torch.sqrt(difference * difference + self.eps * self.eps).mean()


def build_dataset(config: dict, project_root: Path, split: str):
    """中文说明：根据配置中的 dataset.type 构造训练集或验证集对象。
    
    输入：config、project_root、split。
    输出：返回值会被后续训练、评估、导出或测试流程继续使用。
    """
    data_cfg = config["data"]
    seed = config["experiment"].get("seed", 42)
    if split == "val":
        seed += 10000

    dataset_name = data_cfg.get("dataset", "toy_rgb")
    if dataset_name in {"paired_image", "paired_pseudo_raw"}:
        split_cfg = data_cfg[split]
        dataset_cls = (
            PairedPseudoRawDataset
            if dataset_name == "paired_pseudo_raw"
            else PairedImageDenoiseDataset
        )
        return dataset_cls(
            noisy_dir=resolve_project_path(project_root, split_cfg["noisy_dir"]),
            clean_dir=resolve_project_path(project_root, split_cfg["clean_dir"]),
            patch_size=data_cfg["patch_size"],
            size=data_cfg[f"{split}_size"],
            seed=seed,
            augment=split == "train" and data_cfg.get("augment", False),
        )

    noise_cfg = data_cfg["noise"]
    return ToyRGBDenoiseDataset(
        size=data_cfg[f"{split}_size"],
        patch_size=data_cfg["patch_size"],
        sigma_min=noise_cfg.get("sigma_min", 0.0),
        sigma_max=noise_cfg.get("sigma_max", 0.0),
        seed=seed,
        noise_type=noise_cfg.get("type", "gaussian"),
        shot_min=noise_cfg.get("shot_min", 0.0),
        shot_max=noise_cfg.get("shot_max", 0.0),
        read_min=noise_cfg.get("read_min", 0.0),
        read_max=noise_cfg.get("read_max", 0.0),
    )


def train_from_config(config: dict) -> None:
    """根据配置字典执行完整的训练流程。

    这是 Stage 2 的唯一训练入口，所有超参数通过 config 字典控制。
    训练完成后不返回任何值，但会在 output_dir 下生成：
        - checkpoints/last.pth         最新模型权重
        - checkpoints/best_psnr.pth    PSNR 最优模型权重
        - metrics.csv                  每步验证指标日志
        - vis/step_XXXX.png            可视化三联图
        - tb/                          TensorBoard 日志（可选）

    参数：
        config: 完整的配置字典（通常从 YAML 文件解析而来）
    """
    # 中文说明：读取配置并执行完整训练循环，同时处理日志、验证、可视化和 checkpoint。
    # ============================================================
    # 0. 基础设置：种子、设备、输出目录
    # ============================================================
    seed_everything(config["experiment"].get("seed", 42))
    device = resolve_device(config["train"].get("device", "auto"))

    # 解析输出目录（相对路径 → 绝对路径）
    project_root = Path(__file__).resolve().parents[2]  # stage2_ai_isp/
    out_dir = Path(config["experiment"]["output_dir"])
    if not out_dir.is_absolute():
        out_dir = project_root / out_dir

    ckpt_dir = out_dir / "checkpoints"   # 模型权重保存目录
    vis_dir = out_dir / "vis"            # 可视化输出目录
    out_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 1. 数据集构建
    # ============================================================
    train_set = build_dataset(config, project_root, "train")
    val_set = build_dataset(config, project_root, "val")

    # DataLoader：训练集 shuffle + drop_last，验证集顺序加载
    train_loader = DataLoader(
        train_set,
        batch_size=config["train"]["batch_size"],
        shuffle=True,
        num_workers=config["train"].get("num_workers", 0),
        drop_last=True,  # 丢弃最后不完整 batch，避免 BN 出错
    )
    val_loader = DataLoader(
        val_set,
        batch_size=config["train"]["batch_size"],
        shuffle=False,  # 验证集无需 shuffle
    )

    # ============================================================
    # 2. 模型、优化器、损失函数
    # ============================================================
    model = build_model(config["model"]).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config["train"]["learning_rate"],
        weight_decay=config["train"].get("weight_decay", 0.0),
    )

    # 损失函数：L1（MAE）或 MSE
    criterion = build_criterion(config["train"].get("loss", "l1"))

    resume_path = config["train"].get("resume")

    # 日志：CSV（始终启用）+ TensorBoard（可选）
    # 断点续训时保留已有 CSV；全新实验则重建表头。
    csv_logger = CSVLogger(out_dir / "metrics.csv", reset=not bool(resume_path))
    tb_logger = SummaryWriterOrNoop(out_dir / "tb")

    # ============================================================
    # 3. 训练循环（基于步数，而非 epoch）
    # ============================================================
    best_psnr = float("-inf")  # 历史最佳 PSNR（用于 checkpoint 选择）
    step = 0                    # 全局步数计数器
    epoch = 0                   # epoch 计数器（仅用于日志显示）
    running_loss = 0.0          # 累积损失（用于 log_every 间隔平均）

    if resume_path:
        checkpoint = load_checkpoint(
            resolve_project_path(project_root, resume_path),
            model,
            optimizer,
            map_location=device,
        )
        step = int(checkpoint.get("step", 0))
        best_psnr = float(checkpoint.get("best_psnr", float("-inf")))
        print(f"resumed checkpoint={resume_path} step={step} best_psnr={best_psnr:.4f}")

    model.train()

    while step < config["train"]["steps"]:
        epoch += 1
        for batch in train_loader:
            step += 1

            # --- 数据移入设备 ---
            noisy = batch["noisy"].to(device)
            clean = batch["clean"].to(device)

            # --- 前向传播 ---
            optimizer.zero_grad(set_to_none=True)  # set_to_none=True 更高效（释放梯度内存）
            output = model(noisy)
            loss = criterion(output, clean)

            # --- 反向传播与参数更新 ---
            loss.backward()
            optimizer.step()

            # --- 累积训练损失 ---
            running_loss += float(loss.item())
            tb_logger.add_scalar("train/loss", float(loss.item()), step)

            # --- 定期日志输出 ---
            if step % config["train"].get("log_every", 25) == 0:
                avg_loss = running_loss / config["train"].get("log_every", 25)
                print(f"step={step:04d} epoch={epoch} loss={avg_loss:.6f}")
                running_loss = 0.0

            # --- 定期验证 + CSV 记录 + Checkpoint + 可视化 ---
            if step % config["train"].get("val_every", 50) == 0 or step == config["train"]["steps"]:
                metrics = validate(model, val_loader, device)
                val_psnr = float(metrics["psnr"])
                val_ssim = float(metrics["ssim"])

                print(f"val step={step:04d} psnr={val_psnr:.2f} ssim={val_ssim:.4f}")

                # CSV 日志记录
                csv_logger.append(step, float(loss.item()), val_psnr, val_ssim)

                # TensorBoard 记录
                tb_logger.add_scalar("val/psnr", val_psnr, step)
                tb_logger.add_scalar("val/ssim", val_ssim, step)

                # 可视化三联图保存（noisy / output / clean）
                first = metrics["first_batch"]
                if isinstance(first, dict):
                    save_triplet(
                        first["noisy"], first["output"], first["clean"],
                        vis_dir / f"step_{step:04d}.png",
                    )

                # 如果当前 PSNR 超过历史最佳，保存最佳 checkpoint
                if val_psnr > best_psnr:
                    best_psnr = val_psnr
                    save_checkpoint(
                        ckpt_dir / "best_psnr.pth", model, optimizer, step, best_psnr, config
                    )

                # last.pth 始终记录更新后的 best_psnr。
                save_checkpoint(
                    ckpt_dir / "last.pth", model, optimizer, step, best_psnr, config
                )

            # 达到总步数后跳出
            if step >= config["train"]["steps"]:
                break

    # 关闭 TensorBoard writer
    tb_logger.close()
