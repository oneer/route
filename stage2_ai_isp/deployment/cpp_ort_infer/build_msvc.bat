@echo off
setlocal

set "VS_ROOT=D:\application\Microsoft Visual Studio\18\BuildTools"
set "CMAKE_EXE=%VS_ROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set "NINJA_EXE=%VS_ROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe"
set "ORT_ROOT=D:\Env\onnxruntime\cpu\onnxruntime-win-x64-1.26.0"

if not exist "%VS_ROOT%\VC\Auxiliary\Build\vcvars64.bat" (
  echo Missing vcvars64.bat under %VS_ROOT%
  exit /b 1
)
if not exist "%ORT_ROOT%\include\onnxruntime_cxx_api.h" (
  echo Missing ONNX Runtime SDK under %ORT_ROOT%
  exit /b 1
)

call "%VS_ROOT%\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "PATH=%VS_ROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%"

"%CMAKE_EXE%" -S "%~dp0." -B "%~dp0build_ninja" -G Ninja "-DONNXRUNTIME_ROOT=%ORT_ROOT%" -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 exit /b 1

"%CMAKE_EXE%" --build "%~dp0build_ninja"
if errorlevel 1 exit /b 1

echo Built %~dp0build_ninja\stage2_ort_infer.exe
