from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def project_root() -> Path:
    return SCRIPT_ROOT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 3 TensorRT/CUDA benchmark and output alignment.")
    parser.add_argument("--manifest", default="data/test_inputs/week0_fixed_manifest.csv")
    parser.add_argument("--onnx", default="models/onnx/dncnn_sidd_tiny_fp32.onnx")
    parser.add_argument("--output-dir", default="outputs/week3_backend")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--trtexec", default=r"D:\Env\TensorRT\TensorRT-10.8.0.43\bin\trtexec.exe")
    parser.add_argument("--cuda-bin", default=r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin")
    parser.add_argument("--tensorrt-bin", default=r"D:\Env\TensorRT\TensorRT-10.8.0.43\bin")
    parser.add_argument("--tensorrt-lib", default=r"D:\Env\TensorRT\TensorRT-10.8.0.43\lib")
    parser.add_argument("--cudnn-bin", default=r"C:\Program Files\NVIDIA\CUDNN\v9.23\bin\12.9\x64")
    return parser.parse_args()


def preload_gpu_dlls(extra_dirs: list[str]) -> None:
    site_packages = Path(sys.executable).resolve().parents[1] / "Lib" / "site-packages"
    bin_dirs = [str(path) for path in glob.glob(str(site_packages / "nvidia" / "*" / "bin"))]
    bin_dirs.append(str(site_packages / "onnxruntime" / "capi"))
    bin_dirs.extend(extra_dirs)
    existing = os.environ.get("PATH", "")
    os.environ["PATH"] = ";".join(bin_dirs) + ";" + existing
    for bin_dir in bin_dirs:
        if os.path.isdir(bin_dir):
            os.add_dll_directory(bin_dir)


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_input(path: str) -> np.ndarray:
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32) / 255.0
    return np.transpose(arr, (2, 0, 1))[None, ...].astype(np.float32)


def abs_error(pred: np.ndarray, target: np.ndarray) -> tuple[float, float, float]:
    err = np.abs(pred - target)
    mse = float(np.mean((pred - target) ** 2))
    psnr = float(10.0 * np.log10(1.0 / max(mse, 1e-8)))
    return float(err.max()), float(err.mean()), psnr


def make_session(onnx_path: Path, backend: str, cache_dir: Path) -> ort.InferenceSession:
    if backend == "cpu":
        providers: list[object] = ["CPUExecutionProvider"]
    elif backend == "cuda":
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    elif backend == "trt_fp32":
        providers = [
            (
                "TensorrtExecutionProvider",
                {
                    "trt_engine_cache_path": str(cache_dir / "ort_trt_fp32"),
                    "trt_engine_cache_enable": "True",
                    "trt_fp16_enable": "False",
                },
            ),
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
    elif backend == "trt_fp16":
        providers = [
            (
                "TensorrtExecutionProvider",
                {
                    "trt_engine_cache_enable": "True",
                    "trt_engine_cache_path": str(cache_dir / "ort_trt_fp16"),
                    "trt_fp16_enable": "True",
                },
            ),
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ]
    else:
        raise ValueError(f"Unknown backend: {backend}")
    return ort.InferenceSession(str(onnx_path), providers=providers)


def benchmark_session(session: ort.InferenceSession, inp: np.ndarray, runs: int) -> tuple[np.ndarray, list[float]]:
    for _ in range(5):
        output = session.run(["output"], {"input": inp})[0]
    timings = []
    for _ in range(runs):
        start = time.perf_counter()
        output = session.run(["output"], {"input": inp})[0]
        timings.append((time.perf_counter() - start) * 1000.0)
    return output, timings


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_trtexec(args: argparse.Namespace, root: Path, out_dir: Path, precision: str) -> dict[str, object]:
    trtexec = Path(args.trtexec)
    engine = out_dir / f"dncnn_sidd_tiny_{precision}_trt108.plan"
    log_path = out_dir / f"week3_trtexec_{precision}.log"
    times_path = out_dir / f"week3_trtexec_{precision}_times.json"
    if engine.exists():
        engine.unlink()
    cmd = [
        str(trtexec),
        f"--onnx={root / args.onnx}",
        f"--saveEngine={engine}",
        "--duration=3",
        "--warmUp=200",
        f"--exportTimes={times_path}",
    ]
    if precision == "fp16":
        cmd.append("--fp16")
    env = os.environ.copy()
    env["PATH"] = f"{args.tensorrt_lib};{args.tensorrt_bin};{args.cudnn_bin};{args.cuda_bin};{env.get('PATH', '')}"
    result = subprocess.run(cmd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log_path.write_text(result.stdout, encoding="utf-8")

    gpu_mean_ms = ""
    gpu_median_ms = ""
    match = re.search(r"GPU Compute Time:.*?mean\s*=\s*([0-9.]+)\s*ms.*?median\s*=\s*([0-9.]+)\s*ms", result.stdout, re.S)
    if match:
        gpu_mean_ms = match.group(1)
        gpu_median_ms = match.group(2)
    if times_path.exists():
        try:
            data = json.loads(times_path.read_text(encoding="utf-8"))
            values = [float(item["computeMs"]) for item in data if "computeMs" in item]
            if values:
                gpu_mean_ms = f"{float(np.mean(values)):.6f}"
                gpu_median_ms = f"{float(np.percentile(values, 50)):.6f}"
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    return {
        "precision": precision,
        "returncode": result.returncode,
        "engine_path": str(engine),
        "engine_exists": engine.exists(),
        "log_path": str(log_path),
        "times_path": str(times_path) if times_path.exists() else "",
        "gpu_compute_mean_ms": gpu_mean_ms,
        "gpu_compute_p50_ms": gpu_median_ms,
    }


def main() -> None:
    args = parse_args()
    preload_gpu_dlls([args.cuda_bin, args.cudnn_bin, args.tensorrt_bin, args.tensorrt_lib])
    root = project_root()
    out_dir = root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "ort_engine_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    rows = read_manifest(root / args.manifest)
    onnx_path = root / args.onnx
    tools = {
        "trtexec": str(Path(args.trtexec)) if Path(args.trtexec).exists() else (shutil.which("trtexec") or "missing"),
        "nvcc": shutil.which("nvcc") or "missing",
        "nvidia_smi": shutil.which("nvidia-smi") or "missing",
    }
    trtexec_rows = [
        run_trtexec(args, root, out_dir, "fp32"),
        run_trtexec(args, root, out_dir, "fp16"),
    ]
    write_csv(out_dir / "week3_trtexec_summary.csv", trtexec_rows)

    sessions = {
        "cpu": make_session(onnx_path, "cpu", cache_dir),
        "cuda": make_session(onnx_path, "cuda", cache_dir),
        "trt_fp32": make_session(onnx_path, "trt_fp32", cache_dir),
        "trt_fp16": make_session(onnx_path, "trt_fp16", cache_dir),
    }
    alignment_rows = []
    all_times: dict[str, list[float]] = {name: [] for name in sessions}
    for row in rows:
        inp = load_input(row["noisy_path"])
        cpu_out, cpu_times = benchmark_session(sessions["cpu"], inp, args.runs)
        all_times["cpu"].extend(cpu_times)
        for backend in ("cuda", "trt_fp32", "trt_fp16"):
            output, times = benchmark_session(sessions[backend], inp, args.runs)
            all_times[backend].extend(times)
            max_err, mean_err, align_psnr = abs_error(output, cpu_out)
            alignment_rows.append(
                {
                    "id": row["id"],
                    "backend": backend,
                    "active_providers": ";".join(sessions[backend].get_providers()),
                    "max_abs_error_vs_ort_cpu": max_err,
                    "mean_abs_error_vs_ort_cpu": mean_err,
                    "psnr_vs_ort_cpu": align_psnr,
                    "latency_mean_ms": float(np.mean(times)),
                    "latency_p50_ms": float(np.percentile(times, 50)),
                    "latency_p90_ms": float(np.percentile(times, 90)),
                }
            )

    write_csv(out_dir / "week3_gpu_alignment_latency.csv", alignment_rows)
    summary_rows = []
    for backend, values in all_times.items():
        summary_rows.append(
            {
                "backend": backend,
                "available_providers": ";".join(ort.get_available_providers()),
                "active_providers": ";".join(sessions[backend].get_providers()),
                "trtexec": tools["trtexec"],
                "nvcc": tools["nvcc"],
                "nvidia_smi": tools["nvidia_smi"],
                "latency_mean_ms": float(np.mean(values)),
                "latency_p50_ms": float(np.percentile(values, 50)),
                "latency_p90_ms": float(np.percentile(values, 90)),
            }
        )
    write_csv(out_dir / "week3_backend_summary.csv", summary_rows)
    print(f"Wrote {out_dir / 'week3_backend_summary.csv'}")
    print(f"Wrote {out_dir / 'week3_gpu_alignment_latency.csv'}")
    print(f"Wrote {out_dir / 'week3_trtexec_summary.csv'}")


if __name__ == "__main__":
    main()
