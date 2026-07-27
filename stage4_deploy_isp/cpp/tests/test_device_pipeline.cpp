#include "device_pipeline.hpp"

#include <iostream>
#include <stdexcept>

int main() {
    try {
        const stage4::TensorContract device_tensor{{1U, 3U, 512U, 512U}, "float32", stage4::MemoryLocation::cuda_device, true};
        const stage4::DevicePipelineContract valid{
            device_tensor, device_tensor, device_tensor, 1, 0, 1, true, true,
        };
        stage4::validate_device_pipeline_contract(valid);

        bool rejected = false;
        try {
            auto invalid = valid;
            invalid.intermediate_d2h_count = 1;
            stage4::validate_device_pipeline_contract(invalid);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        if (!rejected) {
            throw std::runtime_error("intermediate D2H must be rejected");
        }

        rejected = false;
        try {
            auto invalid = valid;
            invalid.final_d2h_count = -1;
            stage4::validate_device_pipeline_contract(invalid);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        if (!rejected) {
            throw std::runtime_error("negative copy counts must be rejected");
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
