from __future__ import annotations

import csv
import sys
import time
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
import torch
import yaml
from PIL import Image


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return project_root().parent


def resolve_path(path: str | Path, base: Path | None = None) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (base or project_root()).joinpath(path).resolve()


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_stage2_import(stage2_root: str | Path) -> Path:
    stage2_path = resolve_path(stage2_root)
    if str(stage2_path) not in sys.path:
        sys.path.insert(0, str(stage2_path))
    return stage2_path


def build_stage2_model(stage2_root: str | Path, source_config: str | Path, checkpoint: str | Path) -> torch.nn.Module:
    ensure_stage2_import(stage2_root)
    from ai_isp.models import build_model

    source_cfg = load_yaml(resolve_path(source_config))
    model = build_model(source_cfg["model"])
    ckpt = torch.load(resolve_path(checkpoint), map_location="cpu")
    state = ckpt["model"] if isinstance(ckpt, dict) and "model" in ckpt else ckpt
    model.load_state_dict(state)
    model.eval()
    return model


def list_paired_images(noisy_dir: str | Path, clean_dir: str | Path, max_images: int | None = None) -> list[dict[str, str]]:
    noisy_root = resolve_path(noisy_dir)
    clean_root = resolve_path(clean_dir)
    noisy = {p.name: p for p in sorted(noisy_root.iterdir()) if p.suffix.lower() in IMAGE_EXTS}
    clean = {p.name: p for p in sorted(clean_root.iterdir()) if p.suffix.lower() in IMAGE_EXTS}
    names = sorted(set(noisy) & set(clean))
    if max_images is not None:
        names = names[: int(max_images)]
    return [
        {"id": Path(name).stem, "name": name, "noisy_path": str(noisy[name]), "clean_path": str(clean[name])}
        for name in names
    ]


def write_manifest(rows: list[dict[str, str]], path: str | Path) -> None:
    out = resolve_path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "name", "noisy_path", "clean_path"])
        writer.writeheader()
        writer.writerows(rows)


def load_rgb_tensor(path: str | Path, device: torch.device | str = "cpu") -> torch.Tensor:
    image = Image.open(path).convert("RGB")
    array = np.asarray(image, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
    return tensor.to(device)


def tensor_to_uint8(tensor: torch.Tensor) -> np.ndarray:
    image = tensor.detach().cpu().clamp(0.0, 1.0)
    if image.ndim == 4:
        image = image[0]
    array = image.permute(1, 2, 0).numpy()
    return (array * 255.0 + 0.5).astype(np.uint8)


def save_rgb(tensor: torch.Tensor, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(tensor_to_uint8(tensor)).save(out)


def save_triplet(noisy: torch.Tensor, output: torch.Tensor, clean: torch.Tensor, path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    grid = np.concatenate([tensor_to_uint8(noisy), tensor_to_uint8(output), tensor_to_uint8(clean)], axis=1)
    Image.fromarray(grid).save(out)


def save_error_map(pred: torch.Tensor, target: torch.Tensor, path: str | Path, scale: float = 8.0) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    err = torch.mean(torch.abs(pred.detach().cpu() - target.detach().cpu()), dim=1, keepdim=True)
    err = torch.clamp(err * scale, 0.0, 1.0).repeat(1, 3, 1, 1)
    Image.fromarray(tensor_to_uint8(err)).save(out)


def psnr(pred: torch.Tensor, target: torch.Tensor, eps: float = 1e-8) -> float:
    mse = torch.mean((pred - target) ** 2).item()
    return float(10.0 * np.log10(1.0 / max(mse, eps)))


def simple_ssim(pred: torch.Tensor, target: torch.Tensor) -> float:
    # Lightweight global SSIM. Week 1+ keeps this fixed for backend comparisons.
    x = pred.detach().cpu().numpy().astype(np.float64)
    y = target.detach().cpu().numpy().astype(np.float64)
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2
    mux = x.mean()
    muy = y.mean()
    vx = x.var()
    vy = y.var()
    cov = ((x - mux) * (y - muy)).mean()
    return float(((2 * mux * muy + c1) * (2 * cov + c2)) / ((mux * mux + muy * muy + c1) * (vx + vy + c2)))


def abs_error_stats(pred: torch.Tensor, target: torch.Tensor) -> dict[str, float]:
    err = torch.abs(pred - target)
    return {
        "max_abs_error": float(err.max().item()),
        "mean_abs_error": float(err.mean().item()),
    }


def select_device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(value)


def synchronize_if_needed(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize()


def time_model(model: torch.nn.Module, inp: torch.Tensor, warmup_runs: int, timed_runs: int) -> list[float]:
    with torch.no_grad():
        for _ in range(warmup_runs):
            _ = model(inp)
        synchronize_if_needed(inp.device)
        timings = []
        for _ in range(timed_runs):
            start = time.perf_counter()
            _ = model(inp)
            synchronize_if_needed(inp.device)
            timings.append((time.perf_counter() - start) * 1000.0)
    return timings


def summarize_timings(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=np.float64)
    return {
        "latency_mean_ms": float(mean(values)),
        "latency_std_ms": float(pstdev(values) if len(values) > 1 else 0.0),
        "latency_p50_ms": float(np.percentile(arr, 50)),
        "latency_p90_ms": float(np.percentile(arr, 90)),
    }

