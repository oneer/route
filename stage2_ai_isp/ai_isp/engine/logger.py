"""
训练日志模块 —— CSV 日志与可选的 TensorBoard 日志。

CSVLogger:
    将训练指标顺序追加到 CSV 文件中，格式为：
        step, train_loss, val_psnr, val_ssim
    文件头部自动写入列名行。

SummaryWriterOrNoop:
    包装 PyTorch 的 SummaryWriter（TensorBoard），如果 tensorboard 未安装
    则静默退化为空操作（no-op），不阻塞训练流程。
"""
# 中文说明：封装 CSV 和 TensorBoard 日志写入，保证训练过程可追踪。

from __future__ import annotations

from pathlib import Path
import warnings


class CSVLogger:
    """简单的 CSV 日志记录器，按行追加训练指标。

    用法：
        logger = CSVLogger("output/metrics.csv")
        logger.append(step=100, train_loss=0.05, val_psnr=30.1, val_ssim=0.92)

    参数：
        path: CSV 文件输出路径（自动创建父目录并写入表头）
    """
    # 中文说明：轻量 CSV 日志器：每次写入一行训练或验证指标。

    def __init__(self, path: str | Path, reset: bool = True) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：path、reset。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if reset or not self.path.exists():
            self.path.write_text(
                "step,train_loss,val_psnr,val_ssim\n", encoding="utf-8"
            )

    def append(self, step: int, train_loss: float, val_psnr: float, val_ssim: float) -> None:
        """追加一行训练指标记录。

        参数：
            step:       当前训练步数
            train_loss: 训练损失值
            val_psnr:   验证 PSNR（dB）
            val_ssim:   验证 SSIM
        """
        # 中文说明：补充说明：`append` 是当前模块流程中的一个复用步骤。
        with self.path.open("a", encoding="utf-8") as f:
            f.write(f"{step},{train_loss:.6f},{val_psnr:.4f},{val_ssim:.5f}\n")


class SummaryWriterOrNoop:
    """TensorBoard SummaryWriter 的可选包装器。

    当 tensorboard 包不可用时，自动退化为空操作（所有方法调用无效果）。
    这样训练脚本无需在使用和不使用 TensorBoard 之间分支判断。

    参数：
        log_dir: TensorBoard 日志目录
    """
    # 中文说明：TensorBoard 包装器：可用时写 TensorBoard，不可用时静默跳过。

    def __init__(self, log_dir: str | Path) -> None:
        """中文说明：初始化模块参数和子层；真正的数据流在 forward 中执行。
        
        输入：log_dir。
        输出：返回值会被后续训练、评估、导出或测试流程继续使用。
        """
        try:
            from torch.utils.tensorboard import SummaryWriter

            self.writer = SummaryWriter(str(log_dir))
        except Exception as error:
            warnings.warn(
                f"TensorBoard disabled because SummaryWriter could not start: {error}",
                RuntimeWarning,
                stacklevel=2,
            )
            self.writer = None

    def add_scalar(self, name: str, value: float, step: int) -> None:
        """记录标量指标到 TensorBoard（仅在 writer 可用时生效）。

        参数：
            name:  指标名称（如 "train/loss", "val/psnr"）
            value: 标量值
            step:  当前训练步数
        """
        # 中文说明：补充说明：`add_scalar` 是当前模块流程中的一个复用步骤。
        if self.writer is not None:
            self.writer.add_scalar(name, value, step)

    def close(self) -> None:
        """关闭 TensorBoard writer（仅在 writer 可用时生效）。"""
        # 中文说明：补充说明：`close` 是当前模块流程中的一个复用步骤。
        if self.writer is not None:
            self.writer.close()
