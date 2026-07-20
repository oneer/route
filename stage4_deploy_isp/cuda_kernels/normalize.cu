#include "cuda_preprocess.hpp"

#include <cuda_runtime.h>

#include <algorithm>
#include <stdexcept>
#include <string>

// CUDA kernel：把解码后的 RGB uint8 HWC 图像转换为模型输入需要的 float32 NCHW。
// 每个线程处理一个 HWC 元素，并根据 channel 与 pixel 下标写到 NCHW 对应位置。
__global__ void normalize_u8_to_float_nchw_kernel(
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

namespace {

void check_cuda(cudaError_t status, const char* message) {
    // Runtime API 出错时带上 CUDA 的字符串说明，便于定位环境或 launch 问题。
    if (status != cudaSuccess) {
        throw std::runtime_error(std::string(message) + ": " + cudaGetErrorString(status));
    }
}

}  // namespace

namespace stage4 {

CudaPreprocessTimings profile_cuda_normalize_u8_to_float_nchw(
    const unsigned char* input_hwc,
    float* output_nchw,
    int width,
    int height,
    int channels,
    int runs,
    bool use_pinned_memory) {
    if (input_hwc == nullptr || output_nchw == nullptr || width <= 0 || height <= 0 ||
        channels <= 0 || runs <= 0) {
        throw std::invalid_argument("invalid CUDA preprocess input");
    }
    const int total = width * height * channels;
    // 输入是 uint8，输出是 float32；元素数相同，字节数不同。
    const size_t input_bytes = static_cast<size_t>(total) * sizeof(unsigned char);
    const size_t output_bytes = static_cast<size_t>(total) * sizeof(float);

    unsigned char* device_input = nullptr;
    float* device_output = nullptr;
    unsigned char* pinned_input = nullptr;
    float* pinned_output = nullptr;
    check_cuda(cudaMalloc(&device_input, input_bytes), "cudaMalloc input failed");
    check_cuda(cudaMalloc(&device_output, output_bytes), "cudaMalloc output failed");
    const unsigned char* host_input = input_hwc;
    float* host_output = output_nchw;
    if (use_pinned_memory) {
        check_cuda(cudaHostAlloc(&pinned_input, input_bytes, cudaHostAllocDefault), "cudaHostAlloc input failed");
        check_cuda(cudaHostAlloc(&pinned_output, output_bytes, cudaHostAllocDefault), "cudaHostAlloc output failed");
        std::copy(input_hwc, input_hwc + total, pinned_input);
        host_input = pinned_input;
        host_output = pinned_output;
    }

    const int threads = 256;
    // blocks 向上取整，保证 total 不是 256 的倍数时尾部元素也会被处理。
    const int blocks = (total + threads - 1) / threads;
    cudaEvent_t start = nullptr;
    cudaEvent_t stop = nullptr;
    cudaStream_t stream = nullptr;
    check_cuda(cudaStreamCreate(&stream), "cudaStreamCreate failed");
    check_cuda(cudaEventCreate(&start), "cudaEventCreate start failed");
    check_cuda(cudaEventCreate(&stop), "cudaEventCreate stop failed");

    check_cuda(cudaMemcpyAsync(device_input, host_input, input_bytes, cudaMemcpyHostToDevice, stream), "warmup H2D failed");
    normalize_u8_to_float_nchw_kernel<<<blocks, threads, 0, stream>>>(
        device_input, device_output, width, height, channels, 1.0f / 255.0f);
    check_cuda(cudaGetLastError(), "warmup kernel launch failed");
    check_cuda(cudaMemcpyAsync(host_output, device_output, output_bytes, cudaMemcpyDeviceToHost, stream), "warmup D2H failed");
    check_cuda(cudaStreamSynchronize(stream), "warmup synchronize failed");

    auto elapsed_for = [&](auto&& enqueue) {
        check_cuda(cudaEventRecord(start, stream), "cudaEventRecord start failed");
        for (int run = 0; run < runs; ++run) {
            enqueue();
        }
        check_cuda(cudaEventRecord(stop, stream), "cudaEventRecord stop failed");
        check_cuda(cudaEventSynchronize(stop), "cudaEventSynchronize stop failed");
        float elapsed_ms = 0.0F;
        check_cuda(cudaEventElapsedTime(&elapsed_ms, start, stop), "cudaEventElapsedTime failed");
        return elapsed_ms / static_cast<float>(runs);
    };

    CudaPreprocessTimings timings;
    timings.uses_pinned_memory = use_pinned_memory;
    timings.h2d_mean_ms = elapsed_for([&] {
        check_cuda(cudaMemcpyAsync(device_input, host_input, input_bytes, cudaMemcpyHostToDevice, stream), "H2D copy failed");
    });
    timings.kernel_mean_ms = elapsed_for([&] {
        normalize_u8_to_float_nchw_kernel<<<blocks, threads, 0, stream>>>(
            device_input, device_output, width, height, channels, 1.0f / 255.0f);
    });
    check_cuda(cudaGetLastError(), "timed kernel launch failed");
    timings.d2h_mean_ms = elapsed_for([&] {
        check_cuda(cudaMemcpyAsync(host_output, device_output, output_bytes, cudaMemcpyDeviceToHost, stream), "D2H copy failed");
    });
    timings.e2e_mean_ms = elapsed_for([&] {
        check_cuda(cudaMemcpyAsync(device_input, host_input, input_bytes, cudaMemcpyHostToDevice, stream), "E2E H2D failed");
        normalize_u8_to_float_nchw_kernel<<<blocks, threads, 0, stream>>>(
            device_input, device_output, width, height, channels, 1.0f / 255.0f);
        check_cuda(cudaMemcpyAsync(host_output, device_output, output_bytes, cudaMemcpyDeviceToHost, stream), "E2E D2H failed");
    });
    check_cuda(cudaGetLastError(), "E2E kernel launch failed");
    check_cuda(cudaStreamSynchronize(stream), "final synchronize failed");
    if (use_pinned_memory) {
        std::copy(pinned_output, pinned_output + total, output_nchw);
    }

    cudaEventDestroy(start);
    cudaEventDestroy(stop);
    cudaStreamDestroy(stream);
    cudaFree(device_input);
    cudaFree(device_output);
    if (pinned_input != nullptr) {
        cudaFreeHost(pinned_input);
    }
    if (pinned_output != nullptr) {
        cudaFreeHost(pinned_output);
    }
    return timings;
}

}  // namespace stage4
