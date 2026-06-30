"""Week 1：导出 ONNX 并验证 ONNX Runtime 与 PyTorch 对齐。

部署链路的第一步是把 PyTorch 模型冻结成 ONNX。脚本导出模型、运行 ONNX
checker、记录图结构摘要，并在固定输入集上比较 PyTorch 输出与 ORT 输出的
绝对误差和质量指标。
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from deploy.common import (
    abs_error_stats,
    build_stage2_model,
    load_rgb_tensor,
    load_yaml,
    project_root,
    psnr,
    save_error_map,
    save_rgb,
    simple_ssim,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 1 ONNX export and ORT alignment.")
    parser.add_argument("--config", default="configs/week1_onnx.yaml")
    return parser.parse_args()


def read_manifest(path: Path) -> list[dict[str, str]]:
    # 沿用 Week 0.5 固定 manifest，保证导出验证和 PyTorch 基线使用同一批图。
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def graph_summary(model: onnx.ModelProto) -> dict[str, object]:
    # 图摘要用于审计导出的模型结构，确认输入输出名、opset 和算子种类。
    graph = model.graph
    op_counts: dict[str, int] = {}
    for node in graph.node:
        op_counts[node.op_type] = op_counts.get(node.op_type, 0) + 1
    return {
        "ir_version": model.ir_version,
        "opset": ",".join(f"{imp.domain or 'ai.onnx'}:{imp.version}" for imp in model.opset_import),
        "num_nodes": len(graph.node),
        "inputs": [value.name for value in graph.input],
        "outputs": [value.name for value in graph.output],
        "op_counts": op_counts,
    }


def write_graph_summary(summary: dict[str, object], path: Path) -> None:
    # 写成 Markdown，便于直接贴进阶段报告或代码审查记录。
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write("# ONNX Graph Summary\n\n")
        f.write(f"- IR version: {summary['ir_version']}\n")
        f.write(f"- Opset: {summary['opset']}\n")
        f.write(f"- Nodes: {summary['num_nodes']}\n")
        f.write(f"- Inputs: {summary['inputs']}\n")
        f.write(f"- Outputs: {summary['outputs']}\n\n")
        f.write("## Operator Counts\n\n")
        for op, count in sorted(summary["op_counts"].items()):
            f.write(f"- `{op}`: {count}\n")


def export_onnx(cfg: dict, model: torch.nn.Module, onnx_path: Path) -> None:
    # dummy_shape 必须与部署合同一致；本阶段默认固定 1x3x512x512。
    model.eval()
    dummy = torch.randn(*cfg["model"]["dummy_shape"], dtype=torch.float32)
    dynamic_axes = None
    if cfg["model"].get("dynamic_axes", False):
        # 如果未来启用动态尺寸，这里会把 batch/height/width 标记为动态轴。
        dynamic_axes = {
            cfg["model"]["input_name"]: {0: "batch", 2: "height", 3: "width"},
            cfg["model"]["output_name"]: {0: "batch", 2: "height", 3: "width"},
        }
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        dummy,
        str(onnx_path),
        input_names=[cfg["model"]["input_name"]],
        output_names=[cfg["model"]["output_name"]],
        opset_version=int(cfg["model"]["opset"]),
        dynamic_axes=dynamic_axes,
        do_constant_folding=True,
    )


def main() -> None:
    args = parse_args()
    root = project_root()
    cfg = load_yaml(root / args.config)
    out_dir = root / cfg["project"]["output_dir"]
    ort_output_dir = out_dir / "ort_outputs"
    error_dir = out_dir / "pytorch_vs_ort_error_maps"
    metrics_path = out_dir / "week1_onnx_alignment.csv"
    summary_path = out_dir / "week1_onnx_alignment_summary.csv"
    graph_path = out_dir / "onnx_graph_summary.md"
    out_dir.mkdir(parents=True, exist_ok=True)

    model = build_stage2_model(
        cfg["project"]["stage2_root"],
        cfg["model"]["source_config"],
        cfg["model"]["checkpoint"],
    ).cpu()
    onnx_path = root / cfg["model"]["onnx_path"]
    # 先导出，再用 onnx.checker 做结构合法性检查，避免后续 ORT 报错难定位。
    export_onnx(cfg, model, onnx_path)

    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)
    write_graph_summary(graph_summary(onnx_model), graph_path)

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = cfg["model"]["input_name"]
    output_name = cfg["model"]["output_name"]
    clamp = bool(cfg["model"].get("clamp_output", True))
    rows = read_manifest(root / cfg["data"]["fixed_manifest"])

    metric_rows: list[dict[str, object]] = []
    with torch.no_grad():
        for row in rows:
            # 同一输入分别跑 PyTorch 和 ORT，误差直接反映导出链路是否保持数值一致。
            sample_id = row["id"]
            inp = load_rgb_tensor(row["noisy_path"], device="cpu")
            clean = load_rgb_tensor(row["clean_path"], device="cpu")
            pytorch_out = model(inp)
            if clamp:
                pytorch_out = pytorch_out.clamp(0.0, 1.0)

            ort_array = session.run([output_name], {input_name: inp.numpy().astype(np.float32)})[0]
            ort_out = torch.from_numpy(ort_array)
            if clamp:
                ort_out = ort_out.clamp(0.0, 1.0)

            align_errors = abs_error_stats(ort_out, pytorch_out)
            metric_rows.append(
                {
                    "id": sample_id,
                    "name": row["name"],
                    "ort_vs_pytorch_max_abs_error": align_errors["max_abs_error"],
                    "ort_vs_pytorch_mean_abs_error": align_errors["mean_abs_error"],
                    "ort_vs_pytorch_psnr": psnr(ort_out, pytorch_out),
                    "ort_quality_psnr": psnr(ort_out, clean),
                    "ort_quality_ssim": simple_ssim(ort_out, clean),
                    "pytorch_quality_psnr": psnr(pytorch_out, clean),
                    "pytorch_quality_ssim": simple_ssim(pytorch_out, clean),
                }
            )
            save_rgb(ort_out, ort_output_dir / f"{sample_id}_ort_output.png")
            save_error_map(ort_out, pytorch_out, error_dir / f"{sample_id}_ort_vs_pytorch_error_x1000.png", scale=1000.0)

    # alignment CSV 是后续审计矩阵中“PyTorch -> ONNX Runtime”的证据来源。
    fieldnames = list(metric_rows[0].keys())
    with metrics_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metric_rows)

    summary = {
        "num_images": len(metric_rows),
        "onnx_path": str(onnx_path),
        "max_abs_error": max(float(r["ort_vs_pytorch_max_abs_error"]) for r in metric_rows),
        "mean_abs_error": sum(float(r["ort_vs_pytorch_mean_abs_error"]) for r in metric_rows) / len(metric_rows),
        "mean_ort_vs_pytorch_psnr": sum(float(r["ort_vs_pytorch_psnr"]) for r in metric_rows) / len(metric_rows),
        "mean_ort_quality_psnr": sum(float(r["ort_quality_psnr"]) for r in metric_rows) / len(metric_rows),
        "mean_pytorch_quality_psnr": sum(float(r["pytorch_quality_psnr"]) for r in metric_rows) / len(metric_rows),
    }
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)

    print(f"Wrote ONNX: {onnx_path}")
    print(f"Wrote graph summary: {graph_path}")
    print(f"Wrote alignment: {metrics_path}")
    print(summary)


if __name__ == "__main__":
    main()
