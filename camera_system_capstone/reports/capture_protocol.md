# Camera 数据采集协议

## 目标

为 IQ、Traditional vs ML 和静态多摄评价建立可追溯输入。第一批公开 DNG 只验证流程；岗位证据需要后续自采数据替换或扩展。

## 每个样本必填

- SHA-256、来源类型、设备、镜头和格式；
- ISO、曝光时间、焦距和拍摄模式；无法读取时留空，不猜测；
- 场景、光照、固定 ROI、数据 split；
- `bayer_raw` / `linear_rgb` / `srgb` 的数据空间；
- 是否经过系统计算摄影处理，未知时写 `unknown`。

## DNG 入口检查

先检查 CFA、PhotometricInterpretation、black/white level、visible area 和维度，再确定是 Bayer RAW、线性 DNG 或经过融合的 ProRAW。不得仅凭 `.dng` 扩展名声明为未经处理的 Sensor RAW。

## 建议场景

室外日光、室内暖光、冷暖混合光、低照度、高动态逆光、细密纹理、肤色、高饱和颜色、运动物体，以及广角/超广角/长焦相同静态场景。每类目标至少 3 个有效样本。

## Split 与 ROI 冻结

Calibration、Validation、Evaluation 不得复用同一 capture ID。Evaluation ROI 必须在参数选择前冻结，坐标统一为左上角原点的 `x,y,w,h`。

## 多摄边界

手动多镜头静态拍摄只用于标定/拼接概念验证，记录 `sync_kind=manual_static`；没有同步双流时不得声称硬件级多摄同步。

