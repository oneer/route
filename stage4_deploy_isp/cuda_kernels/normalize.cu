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

#include "cuda_preprocess.hpp"

#include <cuda_runtime.h>

#include <stdexcept>
#include <string>

namespace {

void check_cuda(cudaError_t status, const char* message) {
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
    const size_t input_bytes = static_cast<size_t>(total) * sizeof(unsigned char);
    const size_t output_bytes = static_cast<size_t>(total) * sizeof(float);

    unsigned char* device_input = nullptr;
    float* device_output = nullptr;
    check_cuda(cudaMalloc(&device_input, input_bytes), "cudaMalloc input failed");
    check_cuda(cudaMalloc(&device_output, output_bytes), "cudaMalloc output failed");
    check_cuda(cudaMemcpy(device_input, input_hwc, input_bytes, cudaMemcpyHostToDevice), "H2D copy failed");

    const int threads = 256;
    const int blocks = (total + threads - 1) / threads;
    cudaEvent_t start = nullptr;
    cudaEvent_t stop = nullptr;
    check_cuda(cudaEventCreate(&start), "cudaEventCreate start failed");
    check_cuda(cudaEventCreate(&stop), "cudaEventCreate stop failed");

    normalize_u8_to_float_nchw<<<blocks, threads>>>(device_input, device_output, width, height, channels, 1.0f / 255.0f);
    check_cuda(cudaGetLastError(), "warmup kernel launch failed");
    check_cuda(cudaDeviceSynchronize(), "warmup synchronize failed");

    check_cuda(cudaEventRecord(start), "cudaEventRecord start failed");
    for (int run = 0; run < runs; ++run) {
        normalize_u8_to_float_nchw<<<blocks, threads>>>(
            device_input, device_output, width, height, channels, 1.0f / 255.0f);
    }
    check_cuda(cudaEventRecord(stop), "cudaEventRecord stop failed");
    check_cuda(cudaEventSynchronize(stop), "cudaEventSynchronize stop failed");
    check_cuda(cudaGetLastError(), "timed kernel launch failed");

    float elapsed_ms = 0.0f;
    check_cuda(cudaEventElapsedTime(&elapsed_ms, start, stop), "cudaEventElapsedTime failed");
    check_cuda(cudaMemcpy(output_nchw, device_output, output_bytes, cudaMemcpyDeviceToHost), "D2H copy failed");

    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    cudaFree(device_input);
    cudaFree(device_output);
    return elapsed_ms / static_cast<float>(runs);
}

}  // namespace stage4
