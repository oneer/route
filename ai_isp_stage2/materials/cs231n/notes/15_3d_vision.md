# Lecture 15：三维视觉

## 这讲在讲什么

这讲讨论 3D shape representations、shape reconstruction、neural implicit representations 等三维视觉内容。

## 核心概念

| 概念 | 解释 | 和 AI-ISP 的关系 |
|---|---|---|
| 3D representation | 点云、网格、体素、隐式场 | 非当前主线 |
| Reconstruction | 从图像恢复三维结构 | 相机几何相关 |
| Neural implicit | 用网络表示连续空间函数 | 现代 3D 表示 |
| Multi-view | 多视角几何 | 相机系统可能相关 |

## 为什么当前可以跳过

AI-ISP Stage 2 当前重点是：

```text
2D image restoration
```

3D 视觉关注：

```text
2D image(s) -> 3D structure
```

任务目标不同。

## 和相机工程的间接关系

3D 视觉依赖图像质量。ISP 影响：

- 特征点稳定性。
- 低光下结构恢复。
- 双目/多目匹配。
- 深度估计质量。

但这属于下游视觉，不是当前图像恢复主线。

## 最小带走

1. 3D 视觉是另一个方向。
2. 好的 ISP 能改善下游 3D 任务输入。
3. 当前不需要为学 AI-ISP 去深挖 3D。

