# Capstone 数据说明

这里仅保存轻量 manifest，不复制四个 Stage 的图像或模型资产。

- 所有路径必须相对仓库根目录，并使用 `/`。
- `available` 资产必须存在且通过 SHA-256 校验；暂缺数据使用 `planned` 或空 manifest。
- 未知 ISO、曝光、焦距或计算摄影状态保留为空/`unknown`，不得根据文件名猜测。
- 当前样本来自公开 DNG，只用于验证跨阶段契约；它不是自采 Camera IQ 数据。
- 多摄 manifest 当前为空，因此多摄评价必须输出 `not_run`。

