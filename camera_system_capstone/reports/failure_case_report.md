# Failure case report

## Recorded cases

- Stage 1: 9 rejected controlled tuning settings with explicit failure reasons.
- Stage 2: 17 scene/method/failure aggregate rows; `excess_high_frequency` is a risk diagnostic, not automatic halo proof.
- Stage 3: 3 synthetic diagnostics covering parallax, motion overlap, and low-texture/degenerate geometry.
- Stage 4: device I/O Binding is verified, while custom GPU preprocess direct binding remains `not_run`.

## Interpretation rule

A diagnostic flag identifies a review target; it does not by itself prove a product-visible defect. Public/synthetic failures are not presented as phone-camera production failures.

## Boundary

Self-captured product failure reproduction, hardware-synchronized multicamera artifacts, and mobile GPU timeline failures remain `not_run`.
