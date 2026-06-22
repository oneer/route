# 第 4 周补充：工具链与性能基线

## 目标

本报告记录阶段 3 C++ 项目第一次在本机完整配置、编译和测试的过程，确保后续
tile、thread、cache 和参数实验建立在可重复的 Release baseline 上。

## 本机工具链

- CMake：`D:\Env\QT\Tools\CMake_64\bin\cmake.exe`
- Ninja：`D:\Env\QT\Tools\Ninja\ninja.exe`
- C++ compiler：`D:\Env\MinGW32\mingw\bin\g++.exe`
- Compiler version：MinGW.org GCC 9.2.0
- Build type：Release

该 compiler 可用于当前 C++17 和测试，但属于较旧的 32-bit MinGW 工具链。这里的
性能数字只能作为学习基线，不能代表现代 x64 desktop 或 mobile SoC。

## 构建命令

```powershell
$env:PATH="D:\Env\QT\Tools\CMake_64\bin;D:\Env\QT\Tools\Ninja;D:\Env\MinGW32\mingw\bin;$env:PATH"

cmake -S .\stage3_cpp_isp `
  -B .\stage3_cpp_isp\build `
  -G Ninja `
  -DCMAKE_CXX_COMPILER="D:/Env/MinGW32/mingw/bin/g++.exe" `
  -DCMAKE_BUILD_TYPE=Release

cmake --build .\stage3_cpp_isp\build
ctest --test-dir .\stage3_cpp_isp\build --output-on-failure
```

## 测试结果

首次 bring-up 时：

```text
100% tests passed
0 tests failed out of 5
```

后续阶段 3 已扩展到 11 个测试；总报告记录了 2026-06-22 的 clean Release
verification。

## 基线性能测试

首次 baseline 用于确认：

- Release binary 可以执行；
- benchmark 输出格式可被脚本读取；
- 256×256、1080P、4K case 能进入同一测量链路；
- correctness 与 performance 可以在同一 commit 下复查。

绝对数字后来被 Week 4 完整 CSV 取代。当前又已把 harness 更新为 warmup + median，
因此早期结果只保留为历史证据。

## Bring-up 中修复的问题

- CMake、Ninja、compiler 未在系统 PATH；
- MinGW toolchain 不支持预期的 `std::thread` 路径，改用 Windows
  `_beginthreadex` wrapper；
- benchmark 与 test target 的输出位置需要统一；
- 目录重命名后旧 CMake cache 仍指向原绝对路径，需要重新 configure。

## 学习结论

工具链验证不是“环境杂事”。如果 build type、compiler architecture、运行库或
benchmark binary 不明确，后面的性能结论就没有可复现基础。
