"""Cross-stage contracts and evidence aggregation for the Camera Systems capstone.

This module intentionally contains no ISP, ML, fusion, or deployment algorithm.
It validates portable manifests and normalizes evidence already produced by the
four stage projects.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path, PureWindowsPath
from statistics import mean
from typing import Iterable

import yaml


CAPSTONE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = CAPSTONE_ROOT.parent
MANIFEST_ROOT = CAPSTONE_ROOT / "data" / "manifests"

MANIFEST_SCHEMAS = {
    "capture_manifest.csv": {
        "id": "sample_id",
        "required": {
            "sample_id",
            "asset_path",
            "sha256",
            "source_kind",
            "device",
            "lens",
            "image_format",
            "data_space",
            "cfa_pattern",
            "width",
            "height",
            "iso",
            "exposure_time_s",
            "focal_length_mm",
            "capture_mode",
            "scene_tags",
            "lighting",
            "roi_set",
            "computation_status",
            "split",
            "status",
        },
        "paths": {"asset_path"},
    },
    "iq_eval_manifest.csv": {
        "id": "evaluation_id",
        "required": {
            "evaluation_id",
            "capture_id",
            "stage_output_path",
            "scene_group",
            "roi_set",
            "reference_kind",
            "split",
            "status",
        },
        "paths": {"stage_output_path"},
    },
    "multicamera_manifest.csv": {
        "id": "pair_id",
        "required": {
            "pair_id",
            "left_capture_id",
            "right_capture_id",
            "calibration_path",
            "scene_group",
            "split",
            "sync_kind",
            "status",
        },
        "paths": {"calibration_path"},
    },
}

IQ_OUTPUT_FIELDS = [
    "evaluation_id",
    "capture_id",
    "scene_group",
    "source_kind",
    "data_space",
    "near_black_fraction",
    "near_white_fraction",
    "mean_normalized",
    "p01_normalized",
    "p50_normalized",
    "p99_normalized",
    "flat_roi_snr_db_proxy",
    "approx_dynamic_range_db_proxy",
    "mtf50_proxy_cyc_per_px",
    "status",
    "boundary",
]

MULTICAMERA_OUTPUT_FIELDS = [
    "pair_id",
    "reprojection_error_px",
    "overlap_alignment_error_px",
    "overlap_color_delta",
    "seam_gradient_delta",
    "runtime_ms",
    "peak_memory_mib",
    "status",
    "boundary",
]

SYSTEM_OUTPUT_FIELDS = [
    "backend",
    "device",
    "shape",
    "precision",
    "p50_ms",
    "p90_ms",
    "e2e_ms",
    "e2e_p90_ms",
    "peak_ram_mib",
    "peak_vram_mib",
    "h2d_d2h_count",
    "status",
    "includes_io",
    "boundary",
]

EVIDENCE_FIELDS = [
    "jd_requirement",
    "evidence_file",
    "command",
    "environment",
    "result",
    "status",
    "boundary",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_config(name: str) -> dict:
    path = CAPSTONE_ROOT / "configs" / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _key_value_csv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return {row["key"]: row["value"] for row in read_csv(path)}


def _mean_for_method(rows: list[dict[str, str]], method: str, field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get("method") == method and row.get(field)]
    return mean(values) if values else None


def _portable_path_error(value: str) -> str | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute() or PureWindowsPath(value).is_absolute():
        return "must be repository-relative"
    if "\\" in value:
        return "must use forward slashes"
    if ".." in path.parts:
        return "must not escape the repository"
    return None


def _validate_manifest_shape(path: Path, schema: dict) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    if not path.exists():
        return [], [f"missing manifest: {path.relative_to(REPO_ROOT).as_posix()}"]
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        rows = list(reader)
    missing = schema["required"] - columns
    if missing:
        errors.append(f"{path.name}: missing columns {sorted(missing)}")
    return rows, errors


def validate_repository() -> tuple[list[str], list[str]]:
    """Validate schemas, portable paths, hashes, and cross-manifest references."""
    errors: list[str] = []
    warnings: list[str] = []
    manifests: dict[str, list[dict[str, str]]] = {}

    contract = load_config("data_contract.yaml")
    for section in ("image_spaces", "path_rules", "splits", "roi_contract", "status_values"):
        if section not in contract:
            errors.append(f"data_contract.yaml: missing {section}")

    for name, schema in MANIFEST_SCHEMAS.items():
        path = MANIFEST_ROOT / name
        rows, shape_errors = _validate_manifest_shape(path, schema)
        manifests[name] = rows
        errors.extend(shape_errors)
        identifiers: set[str] = set()
        for line_number, row in enumerate(rows, start=2):
            identifier = row.get(schema["id"], "").strip()
            if not identifier:
                errors.append(f"{name}:{line_number}: missing {schema['id']}")
            elif identifier in identifiers:
                errors.append(f"{name}:{line_number}: duplicate id {identifier}")
            identifiers.add(identifier)
            if row.get("status") not in {"available", "planned", "not_available"}:
                errors.append(f"{name}:{line_number}: invalid status {row.get('status')!r}")
            if row.get("split") not in {"calibration", "validation", "evaluation", "none"}:
                errors.append(f"{name}:{line_number}: invalid split {row.get('split')!r}")
            for field in schema["paths"]:
                value = row.get(field, "").strip()
                problem = _portable_path_error(value)
                if problem:
                    errors.append(f"{name}:{line_number}:{field} {problem}: {value}")

    captures = {row["sample_id"]: row for row in manifests["capture_manifest.csv"] if row.get("sample_id")}
    for row in manifests["capture_manifest.csv"]:
        if row.get("status") != "available":
            continue
        relative = row.get("asset_path", "")
        asset = REPO_ROOT / relative
        if not asset.is_file():
            errors.append(f"capture_manifest.csv: available asset missing: {relative}")
            continue
        expected = row.get("sha256", "").lower()
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            errors.append(f"capture_manifest.csv: invalid sha256 for {row['sample_id']}")
        else:
            actual = hashlib.sha256(asset.read_bytes()).hexdigest()
            if actual != expected:
                errors.append(f"capture_manifest.csv: hash mismatch for {row['sample_id']}")
        if row.get("source_kind") not in {"self_capture", "public_dataset", "synthetic"}:
            errors.append(f"capture_manifest.csv: invalid source_kind for {row['sample_id']}")

    for row in manifests["iq_eval_manifest.csv"]:
        capture_id = row.get("capture_id", "")
        if capture_id not in captures:
            errors.append(f"iq_eval_manifest.csv: unknown capture_id {capture_id}")
        if row.get("status") == "available":
            output = REPO_ROOT / row.get("stage_output_path", "")
            if not output.is_file():
                errors.append(f"iq_eval_manifest.csv: stage output missing: {row.get('stage_output_path')}")

    for row in manifests["multicamera_manifest.csv"]:
        for field in ("left_capture_id", "right_capture_id"):
            capture_id = row.get(field, "")
            if capture_id and capture_id not in captures:
                errors.append(f"multicamera_manifest.csv: unknown {field} {capture_id}")
        if row.get("status") != "available":
            warnings.append(f"multicamera pair {row.get('pair_id', '<none>')} is not available")

    if not manifests["multicamera_manifest.csv"]:
        warnings.append("multicamera_manifest.csv has no captured pair; evaluation remains not_run")
    return errors, warnings


def generate_iq_summary(output_path: Path) -> list[dict[str, str]]:
    """Normalize Stage 1 proxy results without reimplementing IQ algorithms."""
    captures = {row["sample_id"]: row for row in read_csv(MANIFEST_ROOT / "capture_manifest.csv")}
    evaluations = read_csv(MANIFEST_ROOT / "iq_eval_manifest.csv")
    rows: list[dict[str, str]] = []
    cache: dict[Path, dict[str, dict[str, str]]] = {}
    for evaluation in evaluations:
        if evaluation["status"] != "available":
            continue
        source_path = REPO_ROOT / evaluation["stage_output_path"]
        if source_path not in cache:
            cache[source_path] = {
                row.get("sample_id", row.get("sample", "")): row
                for row in read_csv(source_path)
            }
        capture = captures[evaluation["capture_id"]]
        source = cache[source_path].get(evaluation["capture_id"])
        if source is None:
            raise ValueError(f"Stage 1 summary has no sample {evaluation['capture_id']}")
        rows.append(
            {
                "evaluation_id": evaluation["evaluation_id"],
                "capture_id": evaluation["capture_id"],
                "scene_group": evaluation["scene_group"],
                "source_kind": capture["source_kind"],
                "data_space": capture["data_space"],
                "near_black_fraction": source["near_black_fraction"],
                "near_white_fraction": source["near_white_fraction"],
                "mean_normalized": source["mean_normalized"],
                "p01_normalized": source["p01_normalized"],
                "p50_normalized": source["p50_normalized"],
                "p99_normalized": source["p99_normalized"],
                "flat_roi_snr_db_proxy": source["flat_roi_snr_db_proxy"],
                "approx_dynamic_range_db_proxy": source["approx_dynamic_range_db_proxy"],
                "mtf50_proxy_cyc_per_px": source["mtf50_proxy_cyc_per_px"],
                "status": "verified_proxy",
                "boundary": "Public DNG natural-image ROI proxies; not self-captured lab IQ, ColorChecker, or slanted-edge MTF.",
            }
        )
    write_csv(output_path, IQ_OUTPUT_FIELDS, rows)
    return rows


def generate_multicamera_summary(output_path: Path) -> list[dict[str, str]]:
    pairs = read_csv(MANIFEST_ROOT / "multicamera_manifest.csv")
    rows: list[dict[str, str]] = []
    for pair in pairs:
        rows.append(
            {
                "pair_id": pair["pair_id"],
                "status": "not_run" if pair["status"] != "available" else "asset_ready",
                "boundary": "No calibration/fusion metric is published until an available static pair is evaluated; no hardware-sync claim.",
            }
        )
    if not rows:
        rows.append(
            {
                "pair_id": "no_available_pair",
                "status": "not_run",
                "boundary": "No multicamera captures exist yet; static calibration/fusion and hardware sync are not claimed.",
            }
        )
    write_csv(output_path, MULTICAMERA_OUTPUT_FIELDS, rows)
    return rows


def generate_system_profile_summary(output_path: Path) -> list[dict[str, str]]:
    config = load_config("system_profile.yaml")
    source_rows = read_csv(REPO_ROOT / config["source_latency_matrix"])
    allowed = set(config["include_backends"])
    rows: list[dict[str, str]] = []
    for source in source_rows:
        if source["backend"] not in allowed:
            continue
        rows.append(
            {
                "backend": source["backend"],
                "device": source["device"],
                "shape": source["shape"],
                "precision": source["precision"],
                "p50_ms": source["infer_p50_ms"],
                "p90_ms": source["infer_p90_ms"],
                "e2e_ms": source["e2e_ms"],
                "e2e_p90_ms": "",
                "peak_ram_mib": "",
                "peak_vram_mib": "",
                "h2d_d2h_count": "",
                "status": "verified_partial",
                "includes_io": source["includes_io"],
                "boundary": "Existing desktop measurement; RAM/VRAM and copy count are unmeasured, and this is not Snapdragon/mobile evidence.",
            }
        )

    device_profile = REPO_ROOT / config.get("device_pipeline_profile", "")
    if device_profile.is_file():
        for source in read_csv(device_profile):
            rows.append(
                {
                    "backend": source["backend"],
                    "device": source["device"],
                    "shape": source["shape"],
                    "precision": source["precision"],
                    "p50_ms": source["inference_p50_ms"],
                    "p90_ms": source["inference_p90_ms"],
                    "e2e_ms": source["e2e_p50_ms"],
                    "e2e_p90_ms": source["e2e_p90_ms"],
                    "peak_ram_mib": source["peak_ram_mib_sampled"],
                    "peak_vram_mib": source["peak_vram_mib_sampled"],
                    "h2d_d2h_count": (
                        f"{source['h2d_count']} H2D / {source['intermediate_d2h_count']} intermediate D2H / "
                        f"{source['final_d2h_count']} final D2H"
                    ),
                    "status": source["status"],
                    "includes_io": "no file I/O; CPU preprocess, H2D, inference, and final D2H included",
                    "boundary": source["boundary"],
                }
            )
    write_csv(output_path, SYSTEM_OUTPUT_FIELDS, rows)
    return rows


def build_evidence_rows(
    iq_rows: list[dict[str, str]],
    system_rows: list[dict[str, str]],
    multicamera_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    tuning_rows = read_csv(REPO_ROOT / "stage1_soft_isp" / "reports" / "figures" / "camera_iq" / "tuning_sweep.csv")
    selected_tuning = [row for row in tuning_rows if row.get("selected") == "true"]

    camera_scene_path = (
        REPO_ROOT / "stage2_ai_isp" / "reports" / "figures" / "camera_scene_evaluation" / "per_sample_metrics.csv"
    )
    camera_scene_rows = read_csv(camera_scene_path) if camera_scene_path.is_file() else []
    bilateral_psnr = _mean_for_method(camera_scene_rows, "stage1_bilateral", "output_psnr")
    ml_psnr = _mean_for_method(camera_scene_rows, "dncnn_ort_fp32", "output_psnr")
    scene_samples = len({row["sample_id"] for row in camera_scene_rows}) if camera_scene_rows else 0
    scene_gain = None if bilateral_psnr is None or ml_psnr is None else ml_psnr - bilateral_psnr

    geometry = _key_value_csv(REPO_ROOT / "stage3_cpp_isp" / "reports" / "multicamera_geometry_alignment.csv")
    fusion = _key_value_csv(REPO_ROOT / "stage3_cpp_isp" / "reports" / "multicamera_fusion_alignment.csv")
    synthetic_verified = geometry.get("passed") == "1.0" and fusion.get("passed") == "1.0"

    device_row = next((row for row in system_rows if row.get("backend") == "ORT CUDA IOBinding"), None)
    iq_result = (
        f"{len(iq_rows)} public DNG sample(s); {len(selected_tuning)} controlled tuning decisions; "
        "clipping, ROI SNR, DR and MTF proxies"
    )
    scene_result = (
        f"{scene_samples} frozen public SIDD sRGB sample(s), {len(camera_scene_rows)} method rows; "
        f"DnCNN - bilateral PSNR = {scene_gain:.3f} dB"
        if scene_gain is not None
        else "Camera-scene evaluator implemented; no complete frozen comparison rows"
    )
    multicamera_result = (
        "Synthetic C++/OpenCV homography max difference "
        f"{float(geometry['max_homography_abs_error']):.3e}; NumPy/C++ fusion max error "
        f"{float(fusion['max_cpp_python_abs_error']):.3e}"
        if synthetic_verified
        else "No complete synthetic calibration/fusion alignment result"
    )
    system_result = (
        f"ORT CUDA I/O Binding inference p50/p90={float(device_row['p50_ms']):.3f}/"
        f"{float(device_row['p90_ms']):.3f} ms; e2e p50/p90={float(device_row['e2e_ms']):.3f}/"
        f"{float(device_row['e2e_p90_ms']):.3f} ms; RAM={float(device_row['peak_ram_mib']):.2f} MiB; "
        f"copies={device_row['h2d_d2h_count']}"
        if device_row
        else f"{len(system_rows)} historical backend profile row(s); memory/copy fields unmeasured"
    )
    return [
        {
            "jd_requirement": "IQ evaluation",
            "evidence_file": "camera_system_capstone/outputs/iq_summary.csv",
            "command": "python camera_system_capstone/scripts/02_run_iq_evaluation.py",
            "environment": "CPU; existing Stage 1 public DNG audit",
            "result": iq_result,
            "status": "verified_proxy" if iq_rows else "not_run",
            "boundary": "Not self-captured lab IQ; no ColorChecker or standard slanted-edge chart.",
        },
        {
            "jd_requirement": "Traditional vs ML camera-scene tuning",
            "evidence_file": "stage2_ai_isp/reports/figures/camera_scene_evaluation/per_sample_metrics.csv",
            "command": "python stage2_ai_isp/scripts/24_evaluate_camera_scenes.py",
            "environment": "CPU evaluation; frozen public SIDD validation pairs 00011-00020",
            "result": scene_result,
            "status": "verified_public_rgb" if camera_scene_rows else "not_run",
            "boundary": "Paired public rendered sRGB restoration, not self-captured scenes or Sensor RAW AI-ISP.",
        },
        {
            "jd_requirement": "Multi-camera calibration and fusion",
            "evidence_file": "stage3_cpp_isp/reports/multicamera_geometry_alignment.csv",
            "command": "cmake --build <release-build>; ctest --test-dir <release-build> -C Release",
            "environment": "MSVC C++17 Release plus OpenCV/NumPy synthetic reference",
            "result": multicamera_result,
            "status": "verified_synthetic" if synthetic_verified else "not_run",
            "boundary": "Synthetic planar geometry/fusion only; captured camera pair remains not_run, with no hardware synchronization claim.",
        },
        {
            "jd_requirement": "System optimization",
            "evidence_file": "camera_system_capstone/outputs/system_profile_summary.csv",
            "command": "python camera_system_capstone/scripts/04_run_system_profile.py",
            "environment": "Desktop RTX 4060 Ti; ONNX Runtime CUDA I/O Binding; file I/O excluded",
            "result": system_result,
            "status": "verified_partial" if system_rows else "not_run",
            "boundary": "Input/output tensors are device-bound, but preprocess remains CPU NumPy plus one H2D; per-process VRAM and Nsight timeline are unavailable.",
        },
        {
            "jd_requirement": "C++ system software",
            "evidence_file": "stage3_cpp_isp/reports/multicamera_calibration_and_fusion.md",
            "command": "cmake --preset verify; cmake --build --preset verify; ctest --preset verify",
            "environment": "MSVC 19.51 C++17 Release; Intel i3-12100F; I/O excluded",
            "result": "14/14 CTest passed; synthetic calibration/fusion aligned; fusion p50/p90 = 17.558/18.795 ms at 1080P",
            "status": "verified_learning",
            "boundary": "Learning-oriented library, not a production realtime ISP.",
        },
    ]


def render_capstone_report(evidence_rows: list[dict[str, str]]) -> str:
    evidence = {row["jd_requirement"]: row for row in evidence_rows}
    table = [
        "| JD requirement | Status | Result | Boundary |",
        "|---|---|---|---|",
    ]
    for row in evidence_rows:
        table.append(
            f"| {row['jd_requirement']} | {row['status']} | {row['result']} | {row['boundary']} |"
        )
    return "\n".join(
        [
            "# Qualcomm 3083325 Camera Systems Capstone",
            "",
            "## 1. 问题与目标",
            "",
            "把四阶段学习产物整理为可重复验收的 Camera Systems 证据链；未实测项目保持 `not_run`。",
            "",
            "## 2. Camera 数据流和系统架构",
            "",
            "Capstone 只校验 manifest、消费各 Stage 输出并生成证据矩阵，不复制 ISP、ML、C++ 或 CUDA 算法。",
            "",
            "## 3. 数据与拍摄协议",
            "",
            f"当前登记并校验了 {evidence['IQ evaluation']['result']}。自采设备、镜头、曝光、场景、ROI 和计算摄影状态的协议见 `reports/capture_protocol.md`。",
            "",
            "## 4. IQ 评价系统",
            "",
            "Stage 1 的 manifest IQ 与受控调参 sweep 已接入。曝光统计、clipping、自然图 ROI SNR、动态范围和 MTF50 都是 proxy；完整数值和边界见 `reports/iq_system_report.md`。",
            "",
            "## 5. Traditional vs ML tuning",
            "",
            f"{evidence['Traditional vs ML camera-scene tuning']['result']}。这是真实公开配对 sRGB 的同输入比较，不等同于 Sensor RAW AI-ISP 或自采 Camera 调参。",
            "",
            "## 6. 多摄标定与融合",
            "",
            f"{evidence['Multi-camera calibration and fusion']['result']}。实拍双摄对仍为 `not_run`，不声称硬件同步。",
            "",
            "## 7. C++/GPU 系统优化",
            "",
            f"{evidence['C++ system software']['result']}。{evidence['System optimization']['result']}。",
            "",
            "## 8. 质量、延迟和内存权衡",
            "",
            "Stage 4 已汇总质量、延迟、RAM 与拷贝次数。WDDM 未暴露每进程 VRAM，因此该字段保持空值；历史 backend 中未测的内存/拷贝字段也不作推断。",
            "",
            "## 9. 失败案例",
            "",
            "受控 IQ sweep、Stage 2 artifact 分类和 Stage 3 几何/运动/低纹理诊断均已记录。剩余证据缺口是标准色卡/斜边、自采 Sensor RAW、实拍双摄和 GPU 自定义预处理直连时间线。",
            "",
            "## 10. 已知边界",
            "",
            "本项目不代表商业量产、高通内部平台、Snapdragon/NPU、移动端功耗或硬件同步经验。",
            "",
            "## 11. Job ID 3083325 能力证据表",
            "",
            *table,
            "",
            "## 12. 最小复现命令",
            "",
            "```powershell",
            "python camera_system_capstone/scripts/06_run_capstone.py --cpu-only",
            "python -m unittest discover -s camera_system_capstone/tests -v",
            "```",
            "",
        ]
    )


def render_supporting_reports(evidence_rows: list[dict[str, str]]) -> dict[str, str]:
    """Render the four interview-facing reports from tracked stage evidence."""
    evidence = {row["jd_requirement"]: row for row in evidence_rows}
    tuning_rows = read_csv(REPO_ROOT / "stage1_soft_isp" / "reports" / "figures" / "camera_iq" / "tuning_sweep.csv")
    selected = [row for row in tuning_rows if row.get("selected") == "true"]
    rejected = [row for row in tuning_rows if row.get("selected") != "true"]
    failure_matrix_path = (
        REPO_ROOT / "stage2_ai_isp" / "reports" / "figures" / "camera_scene_evaluation" / "failure_matrix.csv"
    )
    stage2_failures = read_csv(failure_matrix_path) if failure_matrix_path.is_file() else []
    stage3_failures_path = REPO_ROOT / "stage3_cpp_isp" / "reports" / "multicamera_failure_cases.csv"
    stage3_failures = read_csv(stage3_failures_path) if stage3_failures_path.is_file() else []
    system_output = CAPSTONE_ROOT / "outputs" / "system_profile_summary.csv"
    system_rows = read_csv(system_output) if system_output.is_file() else []
    device = next((row for row in system_rows if row["backend"] == "ORT CUDA IOBinding"), None)

    iq_lines = [
        "# IQ system report", "",
        "## Verified evidence", "",
        f"- {evidence['IQ evaluation']['result']}.",
        "- Manifest hashes and repository-relative paths are validated before aggregation.",
        "- Tuning decisions use a declared problem → hypothesis → parameter sweep → metric → rejection loop.",
        "", "| Case | Selected value | PSNR | SSIM | Delta E proxy |", "|---|---|---:|---:|---:|",
    ]
    for row in selected:
        iq_lines.append(
            f"| {row['case_id']} | {row['value']} | {float(row['psnr']):.3f} | "
            f"{float(row['ssim']):.4f} | {float(row['mean_delta_e_2000_proxy']):.3f} |"
        )
    iq_lines.extend([
        "", "## Boundary", "",
        "The 14 inputs are public DNGs. Natural-image ROI SNR/DR/MTF and full-image Delta E are proxies, not lab chart measurements. Self-captured ColorChecker, flat-field, slanted-edge, and Sensor RAW tuning remain `not_run`.", "",
    ])

    multicamera_lines = [
        "# Multicamera report", "", "## Verified synthetic alignment", "",
        f"- {evidence['Multi-camera calibration and fusion']['result']}.",
        "- C++ implements least-squares planar homography, reprojection metrics, caller-owned inverse-map bilinear warp, color matching, and feather fusion.",
        "- Degenerate collinear correspondences are rejected; parallax and moving-overlap diagnostics are recorded.",
        "", "## Boundary", "",
        "The correctness evidence is synthetic and validates implementation alignment only. A captured calibrated pair, depth-dependent scenes, exposure mismatch, rolling-shutter behavior, and hardware synchronization remain `not_run`.", "",
    ]

    system_lines = [
        "# System optimization report", "", "## Verified result", "",
        f"- {evidence['C++ system software']['result']}.",
        f"- {evidence['System optimization']['result']}.",
    ]
    if device:
        system_lines.extend([
            f"- Correctness is compared with ORT CPU in Stage 4; peak RAM is `{float(device['peak_ram_mib']):.2f} MiB`.",
            f"- Transfer contract: `{device['h2d_d2h_count']}`.",
        ])
    system_lines.extend([
        "", "## Boundary", "",
        "The desktop RTX 4060 Ti result excludes file I/O. Preprocess is still CPU NumPy followed by one H2D; custom CUDA preprocess pointer binding, Nsight validation, per-process VRAM, Snapdragon/NPU latency, and mobile power remain `not_run`.", "",
    ])

    failure_lines = [
        "# Failure case report", "", "## Recorded cases", "",
        f"- Stage 1: {len(rejected)} rejected controlled tuning settings with explicit failure reasons.",
        f"- Stage 2: {len(stage2_failures)} scene/method/failure aggregate rows; `excess_high_frequency` is a risk diagnostic, not automatic halo proof.",
        f"- Stage 3: {len(stage3_failures)} synthetic diagnostics covering parallax, motion overlap, and low-texture/degenerate geometry.",
        "- Stage 4: device I/O Binding is verified, while custom GPU preprocess direct binding remains `not_run`.",
        "", "## Interpretation rule", "",
        "A diagnostic flag identifies a review target; it does not by itself prove a product-visible defect. Public/synthetic failures are not presented as phone-camera production failures.", "",
        "## Boundary", "",
        "Self-captured product failure reproduction, hardware-synchronized multicamera artifacts, and mobile GPU timeline failures remain `not_run`.", "",
    ]
    return {
        "iq_system_report.md": "\n".join(iq_lines),
        "multicamera_report.md": "\n".join(multicamera_lines),
        "system_optimization_report.md": "\n".join(system_lines),
        "failure_case_report.md": "\n".join(failure_lines),
    }


def write_supporting_reports(report_root: Path, evidence_rows: list[dict[str, str]]) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    for name, content in render_supporting_reports(evidence_rows).items():
        (report_root / name).write_text(content, encoding="utf-8")
