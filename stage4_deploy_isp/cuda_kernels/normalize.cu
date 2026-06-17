extern "C" __global__ void normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    float scale) {
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = width * height * channels;
    if (idx >= total) {
        return;
    }
    const int c = idx % channels;
    const int pixel = idx / channels;
    const int nchw_index = c * width * height + pixel;
    output_nchw[nchw_index] = static_cast<float>(input_hwc[idx]) * scale;
}

