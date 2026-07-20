"""Static contract checks for CUDA event timing and pinned-memory comparison."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DevicePipelineContractTests(unittest.TestCase):
    def test_timing_contract_exposes_copy_kernel_and_e2e_fields(self) -> None:
        header = (ROOT / "cpp/include/cuda_preprocess.hpp").read_text(encoding="utf-8")
        for field in ("h2d_mean_ms", "kernel_mean_ms", "d2h_mean_ms", "e2e_mean_ms"):
            self.assertIn(field, header)
        self.assertIn("h2d_count_per_run", header)
        self.assertIn("d2h_count_per_run", header)

    def test_cuda_implementation_uses_events_stream_and_pinned_memory(self) -> None:
        source = (ROOT / "cuda_kernels/normalize.cu").read_text(encoding="utf-8")
        self.assertIn("cudaEventElapsedTime", source)
        self.assertIn("cudaHostAlloc", source)
        self.assertIn("cudaMemcpyAsync", source)
        self.assertIn("cudaStreamCreate", source)

    def test_benchmark_publishes_pageable_and_pinned_rows(self) -> None:
        source = (ROOT / "cpp/src/cuda_preprocess_benchmark.cpp").read_text(encoding="utf-8")
        self.assertIn('write_row("pageable"', source)
        self.assertIn('write_row("pinned"', source)
        self.assertIn("host_staging_included", source)

    def test_io_binding_profile_keeps_intermediate_output_on_device(self) -> None:
        source = (ROOT / "scripts/13_profile_device_pipeline.py").read_text(encoding="utf-8")
        self.assertIn("bind_ortvalue_input", source)
        self.assertIn("bind_ortvalue_output", source)
        self.assertIn('"intermediate_d2h_count": 0', source)
        self.assertIn('"device_preprocess_bound": "false"', source)

    def test_cpp_contract_rejects_intermediate_d2h(self) -> None:
        source = (ROOT / "cpp/src/device_pipeline.cpp").read_text(encoding="utf-8")
        self.assertIn("intermediate_d2h_count != 0", source)
        self.assertIn("shares_preprocess_inference_buffer", source)


if __name__ == "__main__":
    unittest.main()
