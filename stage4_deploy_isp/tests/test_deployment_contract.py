"""部署契约、模型资产、数据划分和审计表的回归测试。"""

from __future__ import annotations

import csv
import hashlib
import json
import unittest
from pathlib import Path, PureWindowsPath

import yaml


ROOT = Path(__file__).resolve().parents[1]


def read_manifest(relative_path: str) -> list[dict[str, str]]:
    """从 Stage 4 根目录读取一个 CSV 数据清单。"""
    with (ROOT / relative_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class DeploymentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # 所有测试共享同一份部署契约，避免各测试重复解析 YAML。
        cls.contract = yaml.safe_load((ROOT / "configs/deployment_contract.yaml").read_text(encoding="utf-8"))

    def test_tensor_contract_is_explicit_and_consistent(self) -> None:
        """输入输出必须明确规定形状、布局、颜色、类型和值域。"""
        for section in ("model", "input", "output", "data", "thresholds"):
            self.assertIn(section, self.contract)

        input_contract = self.contract["input"]
        output_contract = self.contract["output"]
        self.assertEqual(input_contract["shape"], [1, 3, 512, 512])
        self.assertEqual(output_contract["shape"], input_contract["shape"])
        self.assertEqual(input_contract["layout"], "NCHW")
        self.assertEqual(input_contract["color"], "RGB")
        self.assertEqual(input_contract["dtype"], "float32")
        self.assertEqual(input_contract["range"], [0.0, 1.0])

    def test_model_card_matches_contract_and_tracked_model_hashes(self) -> None:
        """模型卡中的契约副本和 SHA-256 必须与当前资产一致。"""
        card = json.loads((ROOT / "outputs/audit/model_card.json").read_text(encoding="utf-8"))
        self.assertEqual(card["contract"], self.contract)

        assets = {
            "onnx_sha256": ROOT / "models/onnx/dncnn_sidd_tiny_fp32.onnx",
            "onnx_external_data_sha256": ROOT / "models/onnx/dncnn_sidd_tiny_fp32.onnx.data",
            "int8_qdq_sha256": ROOT / "models/onnx/dncnn_sidd_tiny_int8_qdq.onnx",
        }
        for hash_name, path in assets.items():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, card["hashes"][hash_name], path.name)

    def test_manifests_are_portable_and_splits_are_isolated(self) -> None:
        """数据清单应可跨平台使用，且量化校准集与评估集不能泄漏。"""
        data = self.contract["data"]
        fixed = read_manifest(data["fixed_manifest"])
        calibration = read_manifest(data["calibration_manifest"])
        evaluation = read_manifest(data["quantization_evaluation_manifest"])

        self.assertEqual(len(fixed), 20)
        self.assertEqual(len(calibration), 10)
        self.assertEqual(len(evaluation), 10)

        fixed_ids = [row["id"] for row in fixed]
        calibration_ids = [row["id"] for row in calibration]
        evaluation_ids = [row["id"] for row in evaluation]
        self.assertEqual(len(fixed_ids), len(set(fixed_ids)))
        self.assertEqual(len(calibration_ids), len(set(calibration_ids)))
        self.assertEqual(len(evaluation_ids), len(set(evaluation_ids)))
        self.assertTrue(set(calibration_ids).isdisjoint(evaluation_ids))
        self.assertEqual(set(calibration_ids) | set(evaluation_ids), set(fixed_ids))

        # 禁止绝对路径和 Windows 反斜杠，确保仓库移动后清单仍然有效。
        for row in fixed + calibration + evaluation:
            self.assertEqual(set(row), {"id", "name", "noisy_path", "clean_path"})
            for key in ("noisy_path", "clean_path"):
                value = row[key]
                self.assertFalse(Path(value).is_absolute(), value)
                self.assertFalse(PureWindowsPath(value).is_absolute(), value)
                self.assertNotIn("\\", value)

    def test_audit_matrix_contains_only_verified_backends(self) -> None:
        """正确性矩阵只能发布已经完成验证的后端。"""
        with (ROOT / "outputs/audit/correctness_matrix.csv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows), 6)
        self.assertTrue(all(row["status"].startswith("verified") for row in rows))

    def test_latency_matrix_declares_measurement_boundaries(self) -> None:
        """延迟矩阵必须说明测试条件，并至少填写一个实际测量阶段。"""
        with (ROOT / "outputs/audit/latency_matrix.csv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {
            "backend",
            "device",
            "shape",
            "precision",
            "warmup_runs",
            "timed_runs",
            "pre_ms",
            "h2d_ms",
            "infer_mean_ms",
            "infer_p50_ms",
            "infer_p90_ms",
            "d2h_ms",
            "post_ms",
            "e2e_ms",
            "includes_io",
        }
        self.assertGreaterEqual(len(rows), 10)
        self.assertEqual(set(rows[0]), required)
        for row in rows:
            for field in ("backend", "device", "shape", "precision", "warmup_runs", "timed_runs", "includes_io"):
                self.assertTrue(row[field].strip(), f"{row['backend']} missing {field}")
            measured = [row[field] for field in ("pre_ms", "h2d_ms", "infer_mean_ms", "d2h_ms", "post_ms", "e2e_ms")]
            self.assertTrue(any(value.strip() for value in measured), f"{row['backend']} has no measured latency")
            for value in measured:
                if value.strip():
                    self.assertGreaterEqual(float(value), 0.0)


if __name__ == "__main__":
    unittest.main()
