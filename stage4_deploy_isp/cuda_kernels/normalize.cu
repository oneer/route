// CUDA kernel：把解码后的 RGB uint8 HWC 图像转换为模型输入需要的 float32 NCHW。
// 每个线程处理一个 HWC 元素，并根据 channel 与 pixel 下标写到 NCHW 对应位置。
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
    // NCHW 中同一通道的所有像素连续存放：channel_offset + spatial_index。
    const int nchw_index = c * width * height + pixel;
    output_nchw[nchw_index] = static_cast<float>(input_hwc[idx]) * scale;
}

#include "cuda_preprocess.hpp"

#include <cuda_runtime.h>

#include <stdexcept>
#include <string>

namespace {

void check_cuda(cudaError_t status, const char* message) {
    // Runtime API 出错时带上 CUDA 的字符串说明，便于定位环境或 launch 问题。
    if (status != cudaSuccess) {
        throw std::runtime_error(std::string(message) + ": " + cudaGetErrorString(status));
    }
}

}  // namespace

namespace stage4 {

float cuda_normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    int runs) {
    const int total = width * height * channels;
    // 输入是 uint8，输出是 float32；元素数相同，字节数不同。
    const size_t input_bytes = static_cast<size_t>(total) * sizeof(unsigned char);
    const size_t output_bytes = static_cast<size_t>(total) * sizeof(float);

    unsigned char* device_input = nullptr;
    float* device_output = nullptr;
    check_cuda(cudaMalloc(&device_input, input_bytes), "cudaMalloc input failed");
    check_cuda(cudaMalloc(&device_output, output_bytes), "cudaMalloc output failed");
    check_cuda(cudaMemcpy(device_input, input_hwc, input_bytes, cudaMemcpyHostToDevice), "H2D copy failed");

    const int threads = 256;
    // blocks 向上取整，保证 total 不是 256 的倍数时尾部元素也会被处理。
    const int blocks = (total + threads - 1) / threads;
    cudaEvent_t start = nullptr;
    cudaEvent_t stop = nullptr;
    check_cuda(cudaEventCreate(&start), "cudaEventCreate start failed");
    check_cuda(cudaEventCreate(&stop), "cudaEventCreate stop failed");

    normalize_u8_to_float_nchw<<<blocks, threads>>>(device_input, device_output, width, height, channels, 1.0f / 255.0f);
    check_cuda(cudaGetLastError(), "warmup kernel launch failed");
    // warmup 同步后再计时，避免首次 launch 开销混进平均 kernel 时间。
    check_cuda(cudaDeviceSynchronize(), "warmup synchronize failed");

    check_cuda(cudaEventRecord(start), "cudaEventRecord start failed");
    // CUDA event 只包住 kernel launch 循环，所以返回值不包含 H2D/D2H 拷贝。
    for (int run = 0; run < runs; ++run) {
        normalize_u8_to_float_nchw<<<blocks, threads>>>(
            device_input, device_output, width, height, channels, 1.0f / 255.0f);
    }
    check_cuda(cudaEventRecord(stop), "cudaEventRecord stop failed");
    check_cuda(cudaEventSynchronize(stop), "cudaEventSynchronize stop failed");
    check_cuda(cudaGetLastError(), "timed kernel launch failed");

    float elapsed_ms = 0.0f;
    check_cuda(cudaEventElapsedTime(&elapsed_ms, start, stop), "cudaEventElapsedTime failed");
    // 拷回 GPU 输出，调用方会和 CPU 参考逐元素比较。
    check_cuda(cudaMemcpy(output_nchw, device_output, output_bytes, cudaMemcpyDeviceToHost), "D2H copy failed");

    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    cudaFree(device_input);
    cudaFree(device_output);
    return elapsed_ms / static_cast<float>(runs);
}

}  // namespace stage4
