# Soft-ISP 调试手册

## 固定排查顺序

每个模块先打印或断点检查：

```text
shape -> dtype -> min/max -> 是否有限值 -> 数据域 -> Bayer/RGB 顺序
```

不要先凭最终图片猜参数。

## 现象与优先检查项

| 现象 | 优先检查 |
|---|---|
| 大片纯黑/纯白 | black/white level、clip、归一化分母 |
| 明显紫绿错色 | Bayer pattern、RGB/BGR、CCM 方向 |
| 图像旋转或镜像 | `raw.sizes.flip`、reference 是否同方向 |
| 暗部出现巨大数值 | `uint16` 减法下溢 |
| 边缘彩边 | Bayer pattern、demosaic、padding、AAF/FCS 缺失 |
| AWB gain 极端 | 饱和/纯色区域是否进入统计、输入是否在线性域 |
| PSNR 很低但结构正常 | tone/gamma/orientation/颜色空间不一致 |
| DPC 检测大量像素 | 阈值过低、强纹理误检、同色邻域错误 |

## 最小化复现

1. 把真实大图问题缩成 4×4、8×8 或 16×16 合成数组。
2. 只运行一个模块。
3. 为预期结果写断言。
4. 修复后再回到真实 RAW。

## 建议断点

- BLC：减法前、clip 前；
- DPC：`residual`、`threshold`、`mask`；
- Demosaic：R/G/B mask、`weight_sum`；
- AWB：筛选 mask、三个均值和 gain；
- CCM：单个像素乘矩阵前后；
- Tone：percentile white、归一化和 Gamma 前后。

## Bug 记录模板

```text
现象：
最小输入：
预期：
实际：
排除过的原因：
根因：
修复：
回归测试：
```
