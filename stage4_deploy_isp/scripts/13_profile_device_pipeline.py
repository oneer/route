#!/usr/bin/env python3
"""Profile ORT CUDA I/O Binding with device input/output OrtValues.

This removes intermediate host output from inference, but preprocessing is
still CPU NumPy followed by one H2D. It does not claim that the custom CUDA
normalize kernel is directly bound to ORT.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _resolve_manifest_path(value: str) -> Path:
    return (ROOT / value).resolve()


def _load_hwc(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def _preprocess(hwc: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(np.transpose(hwc.astype(np.float32) / 255.0, (2, 0, 1))[None])


def _rss_mib() -> float | None:
    if os.name != "nt":
        return None

    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    ok = psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    return float(counters.PeakWorkingSetSize) / (1024.0 * 1024.0) if ok else None


def _process_vram_mib() -> float | None:
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-compute-apps=pid,used_gpu_memory", "--format=csv,noheader,nounits"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for line in output.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 2 and fields[0] == str(os.getpid()):
            try:
                return float(fields[1])
            except ValueError:
                return None
    return None


def _create_cuda_session(model: Path) -> ort.InferenceSession:
    available = ort.get_available_providers()
    if "CUDAExecutionProvider" not in available:
        raise RuntimeError(f"CUDAExecutionProvider unavailable: {available}")
    session = ort.InferenceSession(
        str(model),
        providers=[("CUDAExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"],
    )
    if session.get_providers()[0] != "CUDAExecutionProvider":
        raise RuntimeError(f"CUDA provider did not activate: {session.get_providers()}")
    return session


def _run_device(session: ort.InferenceSession, input_array: np.ndarray) -> np.ndarray:
    input_value = ort.OrtValue.ortvalue_from_numpy(input_array, "cuda", 0)
    output_value = ort.OrtValue.ortvalue_from_shape_and_type(input_array.shape, np.float32, "cuda", 0)
    binding = session.io_binding()
    binding.bind_ortvalue_input(session.get_inputs()[0].name, input_value)
    binding.bind_ortvalue_output(session.get_outputs()[0].name, output_value)
    session.run_with_iobinding(binding)
    return output_value.numpy()


def _percentile(values: list[float], quantile: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), quantile))


def _max_optional(first: float | None, second: float | None) -> float | None:
    values = [value for value in (first, second) if value is not None]
    return max(values) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "test_inputs" / "week4_evaluation_manifest.csv")
    parser.add_argument("--model", type=Path, default=ROOT / "models" / "onnx" / "dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "device_pipeline")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--runs", type=int, default=30)
    args = parser.parse_args()

    manifest = _read(args.manifest)
    if not manifest:
        raise RuntimeError("evaluation manifest is empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    session = _create_cuda_session(args.model)
    cpu_session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    host_hwc = _load_hwc(_resolve_manifest_path(manifest[0]["noisy_path"]))
    for _ in range(args.warmup):
        _run_device(session, _preprocess(host_hwc))

    pre_times: list[float] = []
    h2d_times: list[float] = []
    infer_times: list[float] = []
    d2h_times: list[float] = []
    e2e_times: list[float] = []
    peak_ram = _rss_mib()
    peak_vram = _process_vram_mib()
    for _ in range(args.runs):
        e2e_start = time.perf_counter()
        start = time.perf_counter()
        host_input = _preprocess(host_hwc)
        pre_times.append((time.perf_counter() - start) * 1000.0)

        start = time.perf_counter()
        input_value = ort.OrtValue.ortvalue_from_numpy(host_input, "cuda", 0)
        h2d_times.append((time.perf_counter() - start) * 1000.0)

        output_value = ort.OrtValue.ortvalue_from_shape_and_type(host_input.shape, np.float32, "cuda", 0)
        binding = session.io_binding()
        binding.bind_ortvalue_input(input_name, input_value)
        binding.bind_ortvalue_output(output_name, output_value)
        start = time.perf_counter()
        session.run_with_iobinding(binding)
        infer_times.append((time.perf_counter() - start) * 1000.0)

        start = time.perf_counter()
        _ = output_value.numpy()
        d2h_times.append((time.perf_counter() - start) * 1000.0)
        e2e_times.append((time.perf_counter() - e2e_start) * 1000.0)
        peak_ram = _max_optional(peak_ram, _rss_mib())
        peak_vram = _max_optional(peak_vram, _process_vram_mib())

    max_abs = 0.0
    abs_sum = 0.0
    value_count = 0
    quality_psnr: list[float] = []
    cpu_quality_psnr: list[float] = []
    for item in manifest:
        host_input = _preprocess(_load_hwc(_resolve_manifest_path(item["noisy_path"])))
        device_output = _run_device(session, host_input)
        cpu_output = cpu_session.run(None, {cpu_session.get_inputs()[0].name: host_input})[0]
        difference = np.abs(device_output.astype(np.float64) - cpu_output.astype(np.float64))
        max_abs = max(max_abs, float(np.max(difference)))
        abs_sum += float(np.sum(difference))
        value_count += difference.size
        clean = np.asarray(Image.open(_resolve_manifest_path(item["clean_path"])).convert("RGB"), dtype=np.float32) / 255.0
        restored = np.clip(device_output[0].transpose(1, 2, 0), 0.0, 1.0)
        mse = max(float(np.mean((restored - clean) ** 2)), 1.0e-12)
        quality_psnr.append(float(10.0 * np.log10(1.0 / mse)))
        cpu_restored = np.clip(cpu_output[0].transpose(1, 2, 0), 0.0, 1.0)
        cpu_mse = max(float(np.mean((cpu_restored - clean) ** 2)), 1.0e-12)
        cpu_quality_psnr.append(float(10.0 * np.log10(1.0 / cpu_mse)))

    row = {
        "backend": "ORT CUDA IOBinding", "device": "RTX 4060 Ti", "shape": "1x3x512x512",
        "precision": "FP32", "samples": len(manifest), "warmup_runs": args.warmup, "timed_runs": args.runs,
        "preprocess_mean_ms": float(np.mean(pre_times)), "h2d_mean_ms": float(np.mean(h2d_times)),
        "inference_mean_ms": float(np.mean(infer_times)), "inference_p50_ms": _percentile(infer_times, 50),
        "inference_p90_ms": _percentile(infer_times, 90), "final_d2h_mean_ms": float(np.mean(d2h_times)),
        "e2e_mean_ms": float(np.mean(e2e_times)), "e2e_p50_ms": _percentile(e2e_times, 50),
        "e2e_p90_ms": _percentile(e2e_times, 90),
        "peak_ram_mib_sampled": "" if peak_ram is None else peak_ram,
        "peak_vram_mib_sampled": "" if peak_vram is None else peak_vram,
        "h2d_count": 1, "intermediate_d2h_count": 0, "final_d2h_count": 1,
        "device_tensor_bound": "true", "device_preprocess_bound": "false", "host_memory_kind": "pageable_numpy",
        "max_abs_error_vs_ort_cpu": max_abs, "mean_abs_error_vs_ort_cpu": abs_sum / value_count,
        "mean_quality_psnr": float(np.mean(quality_psnr)),
        "mean_cpu_quality_psnr": float(np.mean(cpu_quality_psnr)), "status": "verified_partial",
        "boundary": "ORT input/output are device OrtValues; preprocess remains CPU NumPy + one H2D; no custom CUDA preprocess pointer binding or Nsight validation.",
    }
    with (args.output_dir / "device_pipeline_profile.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    environment = {
        "onnxruntime": ort.__version__, "available_providers": ort.get_available_providers(),
        "active_providers": session.get_providers(), "python": __import__("sys").version.split()[0],
        "pid": os.getpid(),
        "memory_sampling": "Windows PeakWorkingSet + nvidia-smi per-process samples; not continuous profiler peaks",
    }
    (args.output_dir / "device_pipeline_environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    print(row)


if __name__ == "__main__":
    main()
