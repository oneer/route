[CmdletBinding()]
param(
    [switch]$SkipCpp,
    [string]$CMakeExe = "cmake",
    [string]$PythonExe = "python",
    [string]$CudaPython = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = "1"

function Assert-LastExitCode {
    param([string]$Step)
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

Push-Location (Join-Path $RepoRoot "stage1_soft_isp")
try {
    & $PythonExe -m unittest discover -s tests -v
    Assert-LastExitCode "Stage 1 tests"
}
finally {
    Pop-Location
}

Push-Location $RepoRoot
try {
    & $PythonExe tools/check_environment.py --constraints requirements/constraints-cpu.txt --smoke-import torch
    Assert-LastExitCode "CPU environment constraints"

    $env:PYTHONPATH = Join-Path $RepoRoot "stage2_ai_isp"
    & $PythonExe -m unittest discover -s stage2_ai_isp/tests -v
    Assert-LastExitCode "Stage 2 tests"

    & $PythonExe -m unittest discover -s stage4_deploy_isp/tests -v
    Assert-LastExitCode "Stage 4 contract tests"

    & $PythonExe -m unittest discover -s camera_system_capstone/tests -v
    Assert-LastExitCode "Camera Systems capstone tests"

    if ($CudaPython) {
        if (-not (Test-Path -LiteralPath $CudaPython)) {
            throw "CUDA Python executable does not exist: $CudaPython"
        }
        & $CudaPython tools/check_environment.py --constraints requirements/constraints-ort-gpu-win-py311.txt --smoke-import onnxruntime
        Assert-LastExitCode "ORT GPU environment constraints"
    }
}
finally {
    Pop-Location
}

if (-not $SkipCpp) {
    $CMakeCommand = Get-Command $CMakeExe -ErrorAction SilentlyContinue
    if (-not $CMakeCommand -and -not (Test-Path -LiteralPath $CMakeExe)) {
        throw "CMake was not found. Pass -CMakeExe <path> or use -SkipCpp for Python-only verification."
    }

    Push-Location (Join-Path $RepoRoot "stage3_cpp_isp")
    try {
        & $CMakeExe --preset verify
        Assert-LastExitCode "Stage 3 configure"
        & $CMakeExe --build --preset verify
        Assert-LastExitCode "Stage 3 build"

        $CMakeDirectory = Split-Path -Parent $CMakeExe
        $CTestExe = if ($CMakeDirectory) {
            Join-Path $CMakeDirectory "ctest.exe"
        }
        else {
            "ctest"
        }
        if (-not (Get-Command $CTestExe -ErrorAction SilentlyContinue) -and -not (Test-Path -LiteralPath $CTestExe)) {
            $CTestExe = "ctest"
        }
        & $CTestExe --preset verify
        Assert-LastExitCode "Stage 3 tests"
    }
    finally {
        Pop-Location
    }

    Push-Location (Join-Path $RepoRoot "stage4_deploy_isp")
    try {
        & $CMakeExe --preset contract-verify
        Assert-LastExitCode "Stage 4 contract configure"
        & $CMakeExe --build --preset contract-verify
        Assert-LastExitCode "Stage 4 contract build"
        & $CTestExe --preset contract-verify
        Assert-LastExitCode "Stage 4 contract tests"
    }
    finally {
        Pop-Location
    }
}

Write-Host "All selected Route verification checks passed."
