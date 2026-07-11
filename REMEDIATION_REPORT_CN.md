# Route 项目整改报告

更新时间：2026-07-10

## 1. 使用说明

1. `[x]` 表示代码、文档和验证均已完成。
2. `[ ]` 表示尚未达到验收条件，不以“已有设计文档”代替真实完成。
3. 本报告按 P0（阻断交付）、P1（重要工程化）、P2（能力扩展）排序。
4. 每个整改项都给出验收标准；只有验收命令通过后才能勾选。

## 2. P0：测试与持续验证

1. [x] 修复 Stage 1 测试静默漏跑。
   - 问题：`test_iq_awb.py` 使用 pytest 风格顶层函数，但项目入口是 `unittest discover`。
   - 验收：Stage 1 从 15 项提升到 17 项，全部通过。

2. [x] 为 Stage 4 增加部署合同回归测试。
   - 覆盖：输入输出 shape/layout/color/dtype/range、manifest 字段、模型卡与合同一致性。
   - 验收：`python -m unittest discover -s stage4_deploy_isp/tests -v` 通过。

3. [x] 为 Stage 4 增加数据切分回归测试。
   - 覆盖：固定集 20 张、校准集 10 张、INT8 评价集 10 张、校准与评价无交集。
   - 验收：测试自动拒绝重复 ID、绝对路径和 split overlap。

4. [x] 将 Stage 4 manifest 改为仓库相对路径。
   - 问题：当前 CSV 固化了个人 Windows 用户目录。
   - 验收：三个 manifest 不含盘符和用户名；原脚本仍能解析图像路径。

5. [x] 增加根级统一验证入口。
   - 验收：一个 PowerShell 命令可运行 Stage 1、Stage 2、Stage 4 Python 测试，并可选构建/运行 Stage 3 C++ 测试。

6. [ ] 启用 GitHub Actions CI 并获得 hosted 首跑通过。
   - 验收：CI 分别执行 Python 回归与 Stage 3 CMake/CTest；GPU/TensorRT 不伪装成普通 CI 已验证。
   - 当前：workflow、语法和等价本地命令已完成；等待提交到 GitHub 后首次 hosted run，暂不勾选。

## 3. P0：项目定位与交付边界

7. [x] 将“生产级 C++ ISP”调整为“学习型/验证型 C++ ISP”。
   - 验收：根 README 与 Stage 3 自身的非生产定位一致。

8. [x] 在根 README 增加真实状态摘要。
   - 验收：明确说明 Stage 2 是 RGB restoration/RAW-like bridge，Stage 3 尚未串入 Stage 4，CUDA 前处理尚未接入推理，ARM/Android 尚未完成。

9. [x] 在根 README 增加统一验证命令和整改报告入口。
   - 验收：新读者不进入周报即可找到验证入口、已知限制和整改状态。

10. [x] 定义唯一端到端 capstone 验收口径。
    - 输入：真实 sensor RAW 或公开 RAW paired 数据。
    - 链路：RAW contract → 传统/学习型前处理 → AI 模型 → C++/ONNX Runtime → RGB 输出。
    - 验收：单命令、固定 manifest、阶段输出、质量指标、性能指标和失败样本齐全。

## 4. P1：环境与构建复现

11. [x] 增加根级 `pyproject.toml` 和 Python 版本边界。
    - 验收：声明项目是 monorepo 元数据入口，不错误地把各阶段打包成一个 Python 包。

12. [x] 统一 Python 依赖策略。
    - 当前问题：Stage 1 精确锁定，Stage 2 仅下界，Stage 4 完全不锁版本。
    - 验收：形成 CPU 与 CUDA 两套可复现 lock/constraints，并记录生成命令。

13. [x] 为 Stage 3 增加 CMake Presets。
    - 验收：`cmake --preset verify`、`cmake --build --preset verify`、`ctest --preset verify` 可运行；MSVC 使用 `/utf-8`，避免中文注释在 ACP 936 下破坏 token 解析。

14. [x] 将个人机器路径与可复现环境说明分离。
    - 验收：`environment_paths.md` 明确标记为本机观测记录；公共入口使用环境变量、相对路径或 preset。

15. [x] 建立 CPU/CUDA/ORT/TensorRT 兼容矩阵。
    - 验收：记录 Python、PyTorch、ONNX、ORT、CUDA、cuDNN、TensorRT、编译器和 GPU 架构，并区分“要求”与“本次观测”。

## 5. P1：仓库资产治理

16. [x] 建立仓库资产策略。
    - 验收：定义源码、golden fixture、代表图、完整实验输出、数据集、模型、论文 PDF 分别应存放在哪里。

17. [x] 保留最小可验证 fixtures。
    - 验收：普通 CI 无需拉取完整 LFS 数据即可运行核心单测和合同测试。

18. [ ] 将大批量生成图和完整实验输出迁移到 Release/对象存储。
    - 验收：迁移清单、hash 和下载方式齐全；Git 历史清理需单独审批，不在本轮执行破坏性操作。

19. [x] 增加仓库体积审计。
    - 验收：自动报告跟踪文件数、LFS 文件数、大文件排行和超限资产。

## 6. P1：许可证与第三方内容

20. [x] 建立第三方内容清单。
    - 覆盖：OpenISP、ISP 教程改写、论文 PDF、数据集、PDF 导出正文与图片。
    - 验收：记录来源、用途、许可证状态和是否允许再分发。

21. [ ] 选择并添加根级代码许可证。
    - 验收：由仓库所有者明确选择许可证；不能由自动整改代替法律/授权决策。

22. [ ] 清理无再分发授权的第三方资产。
    - 验收：仅保留来源链接、下载脚本、hash 或合法的小型引用；清理动作需仓库所有者确认。

## 7. P1：评估可信度

23. [ ] 扩大独立测试集并按 source scene/device/ISO 隔离。
    - 验收：训练、验证、测试和 INT8 校准集均有机器可读 manifest，自动检测泄漏。
    - 当前：现有 SIDD tiny 80/20/20 已增加配对、manifest 覆盖、重复行、尺寸和 source-scene 泄漏回归；扩大数据规模及 device/ISO 分层尚未完成。

24. [ ] 增加多随机种子与统计区间。
    - 验收：核心模型至少 3 个种子，报告均值、标准差和失败样本稳定性。

25. [x] 建立可比较 benchmark protocol。
    - 验收：区分 host API、H2D、compute、D2H、端到端和文件 I/O，不混用 latency 口径。

26. [x] 增加跨硬件复验。
    - 验收：至少 CPU 与一类 NVIDIA GPU；移动端完成后再加入 ARM 数据，不使用设计值冒充实测值。

## 8. P2：真实 AI-ISP 与端侧闭环

27. [x] 接入真实 sensor RAW 数据和 metadata contract。
    - 验收：black/white level、Bayer pattern、bit depth、orientation、CCM/illuminant 信息可追踪。

28. [x] 将 Stage 3 C++ ISP 串入 Stage 4。
    - 验收：不是独立 benchmark，而是同一 manifest 下的真实前处理或后处理节点。
    - 当前：固定 20 张 RGB manifest 均实际经过 Stage 3 global Reinhard 节点和 Stage 4 C++ ORT；C++/Python ORT 最大误差均为 `0`。这证明两个 C++ 阶段已串联，但不等于真实 RAW capstone 已完成。

29. [ ] 将 CUDA normalize/pack RAW 接入真实推理链路。
    - 验收：GPU buffer 不做无意义的中间回传，输出与 CPU reference 在阈值内对齐。

30. [ ] 完成 ARM/Android 实机部署。
    - 验收：真实设备型号、工具链、线程数、功耗/温升、p50/p90 latency 和画质对齐齐全。

31. [ ] 增加真实 ISP 能力扩展。
    - 候选：3A 闭环、时域降噪、多帧 HDR、真实标定 LSC/CCM、sharpen/chroma denoise。
    - 验收：每项必须有数据、对照、失败样本和性能成本，不以模块数量作为完成标准。

## 9. 本轮验证记录

1. [x] 根级统一验证：`tools/verify_project.ps1` 完整运行成功。
2. [x] Stage 1：20/20 通过，原先静默漏跑的 IQ/AWB 两项及 RAW contract 三项已纳入。
3. [x] Stage 2：16/16 通过，新增 4 项 split 审计回归。
4. [x] Stage 3：MSVC 19.51 + CMake/Ninja 构建 67 个目标，CTest 12/12 通过，包含 pipeline golden test。
5. [x] Stage 4：8/8 合同回归通过，latency 数值列、计时边界和 Windows ORT DLL 随 runner 部署均已机器校验。
6. [x] 仓库审计：3085 个跟踪文件、2117 个 LFS 文件、当前跟踪工作树约 1563.97 MB、无单文件超过 50 MB。
7. [x] `pyproject.toml`、`CMakePresets.json`、GitHub Actions YAML 均已完成语法解析。
8. [x] 三个 Stage 4 manifest 不再包含个人绝对路径；本机相对路径加载 smoke test 得到 `[1,3,512,512]`。
9. [x] `git diff --check` 通过，Markdown 本地链接检查为 0 个断链。
10. [x] CPU 直接依赖约束和 Windows ORT-GPU runtime 约束均通过实际环境版本检查。
11. [x] SIDD tiny 真实数据审计：train/val/test 为 80/20/20，配对与 manifest 覆盖完整，source scene 无交叉。
12. [x] RTX 4060 Ti 临时复验：同一 20 张 manifest 上 CUDA、TensorRT FP32/FP16 provider 均实际启用；最大误差分别为 `3.58e-7`、`5.29e-4`、`1.61e-3`。
13. [x] 14 张真实 FiveK DNG 已生成 metadata contract，含 SHA-256、尺寸、Bayer、黑白电平、方向、白平衡和色彩矩阵；ISO/曝光保持显式 unknown。
14. [ ] GitHub hosted CI：workflow 已创建，但本轮未被授权提交/推送，因此没有远端运行结果。
15. [ ] 资产外迁、根许可证、扩大数据集、真实 RAW capstone、CUDA 真接入和 ARM 实机仍按未完成状态保留。
16. [x] Stage 4 `ort-verify` preset 已使用 MSVC 19.51 和 ONNX Runtime 1.26 CPU SDK 构建成功。
17. [x] Stage 3→Stage 4 bridge 已完成 1 张和固定 20 张 runtime 验证；Windows runner 随构建复制匹配的 ORT 1.26 DLL，避免 System32 旧版本抢先加载。
