from __future__ import annotations

import argparse
import csv
import ctypes
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image

KERNEL_SOURCE = r"""
extern "C" __global__ void normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    float scale) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = width * height * channels;
    if (idx >= total) {
        return;
    }
    const int c = idx % channels;
    const int pixel = idx / channels;
    const int nchw_index = c * width * height + pixel;
    output_nchw[nchw_index] = (float)input_hwc[idx] * scale;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 6 CPU vs NVRTC CUDA preprocess benchmark.")
    parser.add_argument("--input", default="outputs/week2_cpp_io/ppm_inputs/pair_00001.ppm")
    parser.add_argument("--output", default="outputs/week6_pipeline/week6_cuda_preprocess_summary.csv")
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--arch", default="compute_89")
    return parser.parse_args()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def check_nvrtc(status: int, message: str) -> None:
    if status != 0:
        raise RuntimeError(f"{message}: nvrtc status {status}")


def check_cuda(status: int, message: str) -> None:
    if status != 0:
        raise RuntimeError(f"{message}: CUDA driver status {status}")


def load_image_hwc(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def cpu_preprocess(hwc: np.ndarray, runs: int) -> tuple[np.ndarray, float]:
    output = np.empty((3, hwc.shape[0], hwc.shape[1]), dtype=np.float32)
    start = time.perf_counter()
    for _ in range(runs):
        output = np.transpose(hwc.astype(np.float32) / 255.0, (2, 0, 1)).copy()
    elapsed_ms = (time.perf_counter() - start) * 1000.0 / runs
    return output, elapsed_ms


def compile_ptx(nvrtc: ctypes.CDLL, arch: str) -> bytes:
    program = ctypes.c_void_p()
    source = KERNEL_SOURCE.encode("utf-8")
    check_nvrtc(
        nvrtc.nvrtcCreateProgram(
            ctypes.byref(program),
            source,
            b"normalize.cu",
            0,
            None,
            None,
        ),
        "nvrtcCreateProgram failed",
    )
    options = (ctypes.c_char_p * 2)(f"--gpu-architecture={arch}".encode("ascii"), b"--std=c++17")
    status = nvrtc.nvrtcCompileProgram(program, 2, options)
    log_size = ctypes.c_size_t()
    nvrtc.nvrtcGetProgramLogSize(program, ctypes.byref(log_size))
    if log_size.value > 1:
        log = ctypes.create_string_buffer(log_size.value)
        nvrtc.nvrtcGetProgramLog(program, log)
        print(log.value.decode("utf-8", errors="replace"))
    check_nvrtc(status, "nvrtcCompileProgram failed")
    ptx_size = ctypes.c_size_t()
    check_nvrtc(nvrtc.nvrtcGetPTXSize(program, ctypes.byref(ptx_size)), "nvrtcGetPTXSize failed")
    ptx = ctypes.create_string_buffer(ptx_size.value)
    check_nvrtc(nvrtc.nvrtcGetPTX(program, ptx), "nvrtcGetPTX failed")
    nvrtc.nvrtcDestroyProgram(ctypes.byref(program))
    return ptx.raw


def cuda_preprocess(hwc: np.ndarray, runs: int, arch: str) -> tuple[np.ndarray, float]:
    cuda_bin = r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin"
    if os.path.isdir(cuda_bin):
        os.add_dll_directory(cuda_bin)
        os.environ["PATH"] = cuda_bin + ";" + os.environ.get("PATH", "")
    nvrtc = ctypes.WinDLL("nvrtc64_120_0.dll")
    cuda = ctypes.WinDLL("nvcuda.dll")
    ptx = compile_ptx(nvrtc, arch)

    check_cuda(cuda.cuInit(0), "cuInit failed")
    device = ctypes.c_int()
    check_cuda(cuda.cuDeviceGet(ctypes.byref(device), 0), "cuDeviceGet failed")
    context = ctypes.c_void_p()
    check_cuda(cuda.cuCtxCreate_v2(ctypes.byref(context), 0, device), "cuCtxCreate failed")

    module = ctypes.c_void_p()
    check_cuda(cuda.cuModuleLoadData(ctypes.byref(module), ptx), "cuModuleLoadData failed")
    function = ctypes.c_void_p()
    check_cuda(
        cuda.cuModuleGetFunction(ctypes.byref(function), module, b"normalize_u8_to_float_nchw"),
        "cuModuleGetFunction failed",
    )

    input_bytes = hwc.nbytes
    output = np.empty((3, hwc.shape[0], hwc.shape[1]), dtype=np.float32)
    output_bytes = output.nbytes
    device_input = ctypes.c_void_p()
    device_output = ctypes.c_void_p()
    check_cuda(cuda.cuMemAlloc_v2(ctypes.byref(device_input), input_bytes), "cuMemAlloc input failed")
    check_cuda(cuda.cuMemAlloc_v2(ctypes.byref(device_output), output_bytes), "cuMemAlloc output failed")
    check_cuda(
        cuda.cuMemcpyHtoD_v2(device_input, hwc.ctypes.data_as(ctypes.c_void_p), input_bytes),
        "cuMemcpyHtoD failed",
    )

    height, width, channels = hwc.shape
    total = width * height * channels
    threads = 256
    blocks = (total + threads - 1) // threads
    width_arg = ctypes.c_int(width)
    height_arg = ctypes.c_int(height)
    channels_arg = ctypes.c_int(channels)
    scale_arg = ctypes.c_float(1.0 / 255.0)
    kernel_params = (ctypes.c_void_p * 6)(
        ctypes.cast(ctypes.byref(device_input), ctypes.c_void_p),
        ctypes.cast(ctypes.byref(device_output), ctypes.c_void_p),
        ctypes.cast(ctypes.byref(width_arg), ctypes.c_void_p),
        ctypes.cast(ctypes.byref(height_arg), ctypes.c_void_p),
        ctypes.cast(ctypes.byref(channels_arg), ctypes.c_void_p),
        ctypes.cast(ctypes.byref(scale_arg), ctypes.c_void_p),
    )

    check_cuda(
        cuda.cuLaunchKernel(function, blocks, 1, 1, threads, 1, 1, 0, None, kernel_params, None),
        "warmup cuLaunchKernel failed",
    )
    check_cuda(cuda.cuCtxSynchronize(), "warmup cuCtxSynchronize failed")
    start = time.perf_counter()
    for _ in range(runs):
        check_cuda(
            cuda.cuLaunchKernel(function, blocks, 1, 1, threads, 1, 1, 0, None, kernel_params, None),
            "timed cuLaunchKernel failed",
        )
    check_cuda(cuda.cuCtxSynchronize(), "timed cuCtxSynchronize failed")
    kernel_ms = (time.perf_counter() - start) * 1000.0 / runs
    check_cuda(
        cuda.cuMemcpyDtoH_v2(output.ctypes.data_as(ctypes.c_void_p), device_output, output_bytes),
        "cuMemcpyDtoH failed",
    )
    cuda.cuMemFree_v2(device_input)
    cuda.cuMemFree_v2(device_output)
    cuda.cuModuleUnload(module)
    cuda.cuCtxDestroy_v2(context)
    return output, kernel_ms


def main() -> None:
    args = parse_args()
    root = project_root()
    input_path = root / args.input
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    hwc = load_image_hwc(input_path)
    cpu_output, cpu_ms = cpu_preprocess(hwc, args.runs)
    cuda_output, cuda_ms = cuda_preprocess(hwc, args.runs, args.arch)
    abs_err = np.abs(cpu_output - cuda_output)
    row = {
        "input": str(input_path),
        "width": hwc.shape[1],
        "height": hwc.shape[0],
        "channels": hwc.shape[2],
        "runs": args.runs,
        "cuda_compile": "NVRTC",
        "cuda_arch": args.arch,
        "cpu_preprocess_mean_ms": float(cpu_ms),
        "cuda_kernel_mean_ms": float(cuda_ms),
        "max_abs_error": float(abs_err.max()),
        "mean_abs_error": float(abs_err.mean()),
    }
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    print(row)


if __name__ == "__main__":
    main()
