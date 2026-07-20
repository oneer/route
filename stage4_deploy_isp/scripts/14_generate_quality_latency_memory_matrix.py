#!/usr/bin/env python3
"""Generate the Stage 4 quality/latency/memory/copy-count evidence matrix."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FIELDS = [
    "backend", "device", "precision", "quality_psnr", "quality_drop_db",
    "infer_p50_ms", "infer_p90_ms", "e2e_p50_ms", "e2e_p90_ms",
    "peak_ram_mib", "peak_vram_mib", "h2d_count", "d2h_count",
    "device_tensor_bound", "device_preprocess_bound", "status", "boundary",
]


def _read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    correctness = _read(ROOT / "outputs" / "audit" / "correctness_matrix.csv")
    latency = _read(ROOT / "outputs" / "audit" / "latency_matrix.csv")
    device_rows = _read(ROOT / "outputs" / "device_pipeline" / "device_pipeline_profile.csv")
    quality = {(row["backend"], row["precision"]): row for row in correctness}
    timing = {(row["backend"], row["precision"]): row for row in latency}
    baseline = next(float(row["quality_psnr"]) for row in correctness if row["backend"] == "ONNX Runtime Python CPU")
    rows: list[dict[str, object]] = []

    def add_historical(backend: str, timing_backend: str, precision: str, device: str, boundary: str) -> None:
        quality_row = quality.get((backend, precision), {})
        timing_row = timing.get((timing_backend, precision), {})
        psnr = quality_row.get("quality_psnr", "")
        rows.append({
            "backend": backend, "device": device, "precision": precision,
            "quality_psnr": psnr, "quality_drop_db": "" if psnr == "" else baseline - float(psnr),
            "infer_p50_ms": timing_row.get("infer_p50_ms", ""),
            "infer_p90_ms": timing_row.get("infer_p90_ms", ""),
            "e2e_p50_ms": "", "e2e_p90_ms": "", "peak_ram_mib": "", "peak_vram_mib": "",
            "h2d_count": 0 if device == "CPU" else "", "d2h_count": 0 if device == "CPU" else "",
            "device_tensor_bound": "false", "device_preprocess_bound": "false",
            "status": "verified_partial" if psnr != "" and timing_row else "not_run",
            "boundary": boundary,
        })

    add_historical("ONNX Runtime Python CPU", "ORT cpu", "FP32", "CPU", "Quality and inference latency verified; RAM peak not measured.")
    add_historical("trt_fp32", "ORT trt_fp32", "FP32", "RTX 4060 Ti", "Historical quality and ORT session latency verified; memory/copy count unmeasured.")
    add_historical("trt_fp16", "ORT trt_fp16", "FP16", "RTX 4060 Ti", "Historical quality and ORT session latency verified; memory/copy count unmeasured.")

    for item in device_rows:
        psnr = float(item["mean_quality_psnr"])
        rows.append({
            "backend": item["backend"], "device": item["device"], "precision": item["precision"],
            "quality_psnr": psnr, "quality_drop_db": float(item["mean_cpu_quality_psnr"]) - psnr,
            "infer_p50_ms": item["inference_p50_ms"], "infer_p90_ms": item["inference_p90_ms"],
            "e2e_p50_ms": item["e2e_p50_ms"], "e2e_p90_ms": item["e2e_p90_ms"],
            "peak_ram_mib": item["peak_ram_mib_sampled"], "peak_vram_mib": item["peak_vram_mib_sampled"],
            "h2d_count": item["h2d_count"],
            "d2h_count": int(item["intermediate_d2h_count"]) + int(item["final_d2h_count"]),
            "device_tensor_bound": item["device_tensor_bound"],
            "device_preprocess_bound": item["device_preprocess_bound"],
            "status": item["status"], "boundary": item["boundary"],
        })
    rows.append({
        "backend": "GPU direct custom preprocess", "device": "RTX 4060 Ti", "precision": "FP16",
        "status": "not_run", "device_tensor_bound": "false", "device_preprocess_bound": "false",
        "boundary": "CUDA 12.6 cannot compile the custom kernel with installed VS 2026; no direct preprocess pointer, Nsight timeline, or measured row.",
    })

    output = ROOT / "outputs" / "device_pipeline" / "quality_latency_memory_matrix.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    verified = [row for row in rows if row.get("status") != "not_run"]
    report = [
        "# GPU device pipeline", "",
        "The newly measured ORT CUDA I/O Binding row binds input and output as CUDA OrtValues and performs only the final host copy. The input is still prepared by NumPy on CPU and copied once to the device; the custom CUDA normalize output is not directly bound.", "",
        "## Verified contract", "",
        "- one H2D for the normalized input;",
        "- zero intermediate D2H;",
        "- device-bound ORT input and output;",
        "- one final D2H for quality/output consumption.", "",
    ]
    if device_rows:
        item = device_rows[0]
        report.extend([
            "## Measured result", "",
            f"- Correctness vs ORT CPU: max/mean absolute error `{float(item['max_abs_error_vs_ort_cpu']):.3e}` / `{float(item['mean_abs_error_vs_ort_cpu']):.3e}`.",
            f"- Inference p50/p90: `{float(item['inference_p50_ms']):.3f}` / `{float(item['inference_p90_ms']):.3f} ms`.",
            f"- Host-to-final-host e2e p50/p90 (file I/O excluded): `{float(item['e2e_p50_ms']):.3f}` / `{float(item['e2e_p90_ms']):.3f} ms`.",
            f"- Sampled process peak RAM: `{float(item['peak_ram_mib_sampled']):.2f} MiB`; per-process VRAM is blank because WDDM/nvidia-smi did not expose it.", "",
        ])
    report.extend([
        "## Unfinished direct path", "",
        "The installed CUDA 12.6 toolchain rejects VS 2026, and this environment has no GPU array library that can expose the existing preprocess device pointer to Python ORT. CUDA preprocess -> inference shared buffer/stream and Nsight agreement remain `not_run`.", "",
    ])
    (ROOT / "reports" / "gpu_direct_pipeline.md").write_text("\n".join(report), encoding="utf-8")
    tradeoff = [
        "# Quality, latency, and memory trade-off", "",
        f"Generated `{output.relative_to(ROOT).as_posix()}` with {len(rows)} rows ({len(verified)} measured/partial, {len(rows) - len(verified)} not run).", "",
        "Blank cells are deliberately unmeasured. Sampled RAM/VRAM values are process snapshots, not continuous profiler peaks. Historical TensorRT quality and latency retain their original runner boundaries and are not mixed into a false end-to-end number.", "",
        "No Snapdragon, mobile power, NPU, or production realtime claim is made.", "",
    ]
    (ROOT / "reports" / "quality_latency_memory_tradeoff.md").write_text("\n".join(tradeoff), encoding="utf-8")
    print(f"quality_latency_memory_matrix={output} rows={len(rows)}")


if __name__ == "__main__":
    main()
