# Bug 排查练习

为每个问题写：症状、定位步骤、根因、修复、预防测试。

1. 把 clean 文件夹换成另一批图片，但保持文件名一致。
2. 在 C++ 推理中忘记 BGR→RGB。
3. validation 中忘记 `model.eval()`。
4. 将 YAML loss 写成 `charbonier`。
5. train 和 validation 指向同一个目录。
6. paired crop 对 noisy 和 clean 分别生成随机坐标。
7. 导出 ONNX 时模型没有 `.eval()`。
8. 只计时一次 C++ `forward()`，没有 warm-up。

提示：不要先换模型。先验证数据、shape、值域、颜色顺序、模式和指标协议。

