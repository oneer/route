from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import torch

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deploy.common import (
    abs_error_stats,
    build_stage2_model,
    list_paired_images,
    load_rgb_tensor,
    load_yaml,
    project_root,
    psnr,
    save_error_map,
    save_rgb,
    save_triplet,
    select_device,
    simple_ssim,
    summarize_timings,
    time_model,
    write_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 0.5 PyTorch fixed baseline.")
    parser.add_argument("--config", default="configs/week0_baseline.yaml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = project_root()
    cfg = load_yaml(root / args.config)

    out_dir = root / cfg["project"]["output_dir"]
    output_dir = out_dir / "pytorch_outputs"
    triplet_dir = out_dir / "triplets"
    error_dir = out_dir / "error_maps"
    metrics_path = out_dir / "week0_metrics.csv"
    summary_path = out_dir / "week0_summary.csv"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = list_paired_images(
        cfg["data"]["noisy_dir"],
        cfg["data"]["clean_dir"],
        max_images=cfg["data"].get("max_images"),
    )
    write_manifest(rows, cfg["data"]["fixed_manifest"])

    device = select_device(cfg["evaluation"].get("device", "auto"))
    model = build_stage2_model(
        cfg["project"]["stage2_root"],
        cfg["model"]["source_config"],
        cfg["model"]["checkpoint"],
    ).to(device)

    metric_rows: list[dict[str, object]] = []
    all_timings: list[float] = []
    warmup = int(cfg["evaluation"].get("warmup_runs", 3))
    timed = int(cfg["evaluation"].get("timed_runs", 10))
    clamp = bool(cfg["model"].get("clamp_output", True))

    with torch.no_grad():
        for row in rows:
            sample_id = row["id"]
            noisy = load_rgb_tensor(row["noisy_path"], device=device)
            clean = load_rgb_tensor(row["clean_path"], device=device)
            pred = model(noisy)
            if clamp:
                pred = pred.clamp(0.0, 1.0)

            timings = time_model(model, noisy, warmup_runs=warmup, timed_runs=timed)
            all_timings.extend(timings)

            noisy_cpu = noisy.cpu()
            clean_cpu = clean.cpu()
            pred_cpu = pred.cpu()

            model_errors = abs_error_stats(pred_cpu, clean_cpu)
            noisy_errors = abs_error_stats(noisy_cpu, clean_cpu)
            metric_rows.append(
                {
                    "id": sample_id,
                    "name": row["name"],
                    "noisy_psnr": psnr(noisy_cpu, clean_cpu),
                    "noisy_ssim": simple_ssim(noisy_cpu, clean_cpu),
                    "model_psnr": psnr(pred_cpu, clean_cpu),
                    "model_ssim": simple_ssim(pred_cpu, clean_cpu),
                    "psnr_gain": psnr(pred_cpu, clean_cpu) - psnr(noisy_cpu, clean_cpu),
                    "ssim_gain": simple_ssim(pred_cpu, clean_cpu) - simple_ssim(noisy_cpu, clean_cpu),
                    "model_max_abs_error": model_errors["max_abs_error"],
                    "model_mean_abs_error": model_errors["mean_abs_error"],
                    "noisy_max_abs_error": noisy_errors["max_abs_error"],
                    "noisy_mean_abs_error": noisy_errors["mean_abs_error"],
                }
            )

            save_rgb(pred_cpu, output_dir / f"{sample_id}_pytorch_output.png")
            save_triplet(noisy_cpu, pred_cpu, clean_cpu, triplet_dir / f"{sample_id}_triplet.png")
            save_error_map(pred_cpu, clean_cpu, error_dir / f"{sample_id}_error_x8.png")

    fieldnames = list(metric_rows[0].keys())
    with metrics_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metric_rows)

    timing_summary = summarize_timings(all_timings)
    mean_row = {
        "num_images": len(metric_rows),
        "device": str(device),
        "checkpoint": cfg["model"]["checkpoint"],
        "mean_noisy_psnr": sum(float(r["noisy_psnr"]) for r in metric_rows) / len(metric_rows),
        "mean_noisy_ssim": sum(float(r["noisy_ssim"]) for r in metric_rows) / len(metric_rows),
        "mean_model_psnr": sum(float(r["model_psnr"]) for r in metric_rows) / len(metric_rows),
        "mean_model_ssim": sum(float(r["model_ssim"]) for r in metric_rows) / len(metric_rows),
        "mean_psnr_gain": sum(float(r["psnr_gain"]) for r in metric_rows) / len(metric_rows),
        "mean_ssim_gain": sum(float(r["ssim_gain"]) for r in metric_rows) / len(metric_rows),
        **timing_summary,
    }
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(mean_row.keys()))
        writer.writeheader()
        writer.writerow(mean_row)

    print(f"Wrote manifest: {root / cfg['data']['fixed_manifest']}")
    print(f"Wrote metrics: {metrics_path}")
    print(f"Wrote summary: {summary_path}")
    print(mean_row)


if __name__ == "__main__":
    main()
