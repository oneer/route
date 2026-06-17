# Week 3.5: SIDD Tiny sRGB Real Data Bridge

## Goal

This bridge connects Stage 3 traditional ISP denoise experiments to the existing Stage 2 SIDD tiny paired dataset. The data is real phone sRGB noisy/GT pairs, so it is stronger than synthetic noise for visual sanity checks, while still not being RAW sensor-domain data.

## Dataset

- Pair count discovered: 100
- Stage3 manifest: `C:/Users/10439/Desktop/route/stage3_cpp_isp/data/real_cases/sidd_tiny/manifest.csv`
- Format: `train/val` paired `noisy` and `clean` PNG crops
- Current use: validate denoise behavior on real sRGB noise and texture
- Limitation: black level, CFA, gain map, and RAW noise calibration are not available in this sRGB subset

## Baseline

For a small validation subset, this report compares noisy input, Gaussian filtering, and bilateral filtering. The bilateral implementation is the same Python reference used in Week 3, applied per RGB channel on center crops to keep runtime reasonable.

- Mean noisy PSNR: 26.391 dB
- Mean Gaussian PSNR: 32.116 dB
- Mean bilateral PSNR: 29.650 dB
- Best bilateral sample: `pair_00002.png` at 40.767 dB

![SIDD real comparison](figures/week3_sidd_real/week3_sidd_real_comparison.png)

## Engineering Notes

- This is intentionally a bridge, not a dataset copy. The manifest points to the existing Stage 2 files.
- The same metric code now runs on synthetic vectors and real paired crops, which makes later C++ parity checks easier.
- For an ISP algorithm interview, describe this as a real-image validation set for denoise artifacts, not as RAW ISP evidence.

## Outputs

- Metrics CSV: `C:/Users/10439/Desktop/route/stage3_cpp_isp/reports/figures/week3_sidd_real/week3_sidd_real_metrics.csv`
- Figure: `C:/Users/10439/Desktop/route/stage3_cpp_isp/reports/figures/week3_sidd_real/week3_sidd_real_comparison.png`
- Data card: `C:/Users/10439/Desktop/route/stage3_cpp_isp/data/real_cases/sidd_tiny/README.md`
