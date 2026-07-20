#include "device_pipeline.hpp"

#include <stdexcept>

namespace stage4 {
namespace {

void validate_tensor(const TensorContract& tensor, const char* name) {
    if (tensor.shape.empty() || tensor.dtype.empty()) {
        throw std::invalid_argument(std::string(name) + " has no shape or dtype");
    }
    for (const std::size_t dimension : tensor.shape) {
        if (dimension == 0U) {
            throw std::invalid_argument(std::string(name) + " has a zero dimension");
        }
    }
    if (!tensor.contiguous) {
        throw std::invalid_argument(std::string(name) + " must be contiguous");
    }
}

}  // namespace

void validate_device_pipeline_contract(const DevicePipelineContract& contract) {
    validate_tensor(contract.preprocess_output, "preprocess_output");
    validate_tensor(contract.inference_input, "inference_input");
    validate_tensor(contract.inference_output, "inference_output");
    if (contract.preprocess_output.shape != contract.inference_input.shape ||
        contract.preprocess_output.dtype != contract.inference_input.dtype) {
        throw std::invalid_argument("preprocess output and inference input contract mismatch");
    }
    if (contract.preprocess_output.location != MemoryLocation::cuda_device ||
        contract.inference_input.location != MemoryLocation::cuda_device ||
        contract.inference_output.location != MemoryLocation::cuda_device) {
        throw std::invalid_argument("direct pipeline tensors must remain on the CUDA device");
    }
    if (contract.h2d_count != 1 || contract.intermediate_d2h_count != 0 ||
        contract.final_d2h_count > 1) {
        throw std::invalid_argument("direct pipeline copy count contract is not satisfied");
    }
    if (!contract.shares_preprocess_inference_buffer || !contract.uses_same_cuda_stream) {
        throw std::invalid_argument("direct pipeline requires shared device storage and stream ordering");
    }
}

}  // namespace stage4
