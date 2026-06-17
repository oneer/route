# deploy_isp_stage4

Stage 4 deployment project for the AI-ISP / ISP algorithm engineer roadmap.

This project starts from the Stage 2 paired RGB restoration model and builds a
reproducible deployment chain:

1. PyTorch fixed baseline.
2. ONNX export and output alignment.
3. ONNX Runtime Python / C++ inference.
4. High-performance backend experiments.
5. Quantization and image-quality loss analysis.
6. Lightweight ISP preprocess / postprocess integration.

The current priority is AI-ISP / ISP algorithm work: correctness, image quality,
failure cases, and ISP pipeline positioning matter more than raw inference speed.

