# Multicamera report

## Verified synthetic alignment

- Synthetic C++/OpenCV homography max difference 3.246e-07; NumPy/C++ fusion max error 2.384e-07.
- C++ implements least-squares planar homography, reprojection metrics, caller-owned inverse-map bilinear warp, color matching, and feather fusion.
- Degenerate collinear correspondences are rejected; parallax and moving-overlap diagnostics are recorded.

## Boundary

The correctness evidence is synthetic and validates implementation alignment only. A captured calibrated pair, depth-dependent scenes, exposure mismatch, rolling-shutter behavior, and hardware synchronization remain `not_run`.
