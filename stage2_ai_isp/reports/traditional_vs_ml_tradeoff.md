# Traditional vs ML trade-off

The comparison uses identical inputs and references. Traditional latency is a warmed single-call measurement from the current run; ORT latency is the existing audited aggregate p50 and therefore is not a direct end-to-end timing race.

- DnCNN improves mean PSNR by 4.043 dB over the bilateral baseline.
- DnCNN changes mean texture retention by -0.899 relative to bilateral.
- Observed classified failures: bilateral=7, DnCNN=5.
- Deployment choice must still consider backend latency, memory, power, and content-specific artifacts; this table alone does not justify always-on ML.

## Suggested policy

Use the ML path when the frozen evaluation confirms meaningful restoration gain and no texture/color failure trigger. Fall back to the traditional path when the ML result crosses a declared artifact threshold or when the deployment budget cannot absorb the measured backend cost.

## Non-claims

No production tuning, Sensor RAW processing, Snapdragon latency, mobile power, or INT8/TensorRT quality result is claimed here.
