#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace stage4 {

struct ImageTensor {
    int width = 0;
    int height = 0;
    int channels = 3;
    std::vector<float> nchw;
};

ImageTensor load_ppm_rgb_as_nchw(const std::string& path);
void save_ppm_rgb_from_nchw(const std::string& path, const float* data, int width, int height, int channels);

}  // namespace stage4

