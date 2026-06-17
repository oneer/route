extern "C" __global__ void pack_rggb_to_4ch(
    const float* raw,
    float* packed,
    int width,
    int height) {
    const int out_w = width / 2;
    const int out_h = height / 2;
    const int idx = blockIdx.x * blockDim.x + threadIdx.x;
    const int total = out_w * out_h;
    if (idx >= total) {
        return;
    }
    const int y = idx / out_w;
    const int x = idx % out_w;
    const int raw_y = y * 2;
    const int raw_x = x * 2;
    const int base = y * out_w + x;
    packed[0 * total + base] = raw[(raw_y + 0) * width + raw_x + 0];  // R
    packed[1 * total + base] = raw[(raw_y + 0) * width + raw_x + 1];  // G on R row
    packed[2 * total + base] = raw[(raw_y + 1) * width + raw_x + 0];  // G on B row
    packed[3 * total + base] = raw[(raw_y + 1) * width + raw_x + 1];  // B
}

