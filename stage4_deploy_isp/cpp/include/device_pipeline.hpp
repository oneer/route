#pragma once

#include <cstddef>
#include <string>
#include <vector>

namespace stage4 {

enum class MemoryLocation {
    host_pageable,
    host_pinned,
    cuda_device,
};

struct TensorContract {
    std::vector<std::size_t> shape;
    std::string dtype;
    MemoryLocation location = MemoryLocation::host_pageable;
    bool contiguous = true;
};

struct DevicePipelineContract {
    TensorContract preprocess_output;
    TensorContract inference_input;
    TensorContract inference_output;
    int h2d_count = 0;
    int intermediate_d2h_count = 0;
    int final_d2h_count = 0;
    bool shares_preprocess_inference_buffer = false;
    bool uses_same_cuda_stream = false;
};

// Validate the target direct-device contract. Runtime evidence is recorded
// separately; passing this check alone is not a measurement claim.
void validate_device_pipeline_contract(const DevicePipelineContract& contract);

}  // namespace stage4
