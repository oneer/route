# Git 学习证据规范

阶段一的 Git 历史应证明“如何学会”，而不只是保存最终答案。

## 推荐提交粒度

```text
feat(stage1): implement Bayer channel split
test(stage1): add synthetic BLC cases
experiment(stage1): scan DPC threshold on injected defects
fix(stage1): avoid uint16 underflow in BLC
docs(stage1): explain Gray World failure on green scene
```

每个模块至少留下：

1. 首个可运行实现；
2. 合成测试；
3. 一次参数或失败案例实验；
4. 根据证据做的修正；
5. 自己的结论。

不要为了制造历史拆分无意义提交，也不要把全部阶段一次性提交。
