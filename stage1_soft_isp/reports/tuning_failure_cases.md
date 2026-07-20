# Stage 1 tuning failure cases

| Case | Rejected setting | Failure classification | Evidence |
|---|---|---|---|
| awb_filter | 10/90 | lower_reference_similarity | SSIM=0.9858, texture=1.008, clip=0.1457 |
| bilateral_sigma | 0.020 | lower_reference_similarity | SSIM=0.6840, texture=2.484, clip=0.0201 |
| tone_highlight | reinhard/99 | over_smoothing | SSIM=0.9291, texture=0.701, clip=0.0000 |

These are controlled failures, not claims about an actual phone ISP.
