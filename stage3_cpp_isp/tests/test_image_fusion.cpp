#include "cpp_isp/image_fusion.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>

namespace {

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

cpp_isp::ImageBuffer<float> make_constant(float r, float g, float b) {
    cpp_isp::ImageBuffer<float> image(8, 4, 3);
    for (std::uint32_t y = 0; y < image.height(); ++y) {
        for (std::uint32_t x = 0; x < image.width(); ++x) {
            image(y, x, 0) = r;
            image(y, x, 1) = g;
            image(y, x, 2) = b;
        }
    }
    return image;
}

}  // namespace

int main() {
    try {
        auto reference = make_constant(0.6F, 0.4F, 0.2F);
        auto candidate = make_constant(0.3F, 0.2F, 0.1F);
        cpp_isp::ImageBuffer<float> matched(8, 4, 3);
        const auto reference_view = static_cast<const cpp_isp::ImageBuffer<float>&>(reference).view();
        const auto candidate_view = static_cast<const cpp_isp::ImageBuffer<float>&>(candidate).view();
        const auto gains = cpp_isp::estimate_overlap_color_gains(reference_view, candidate_view, 2, 6);
        require(gains.size() == 3, "gain count mismatch");
        require(std::abs(gains[0] - 2.0F) < 1.0e-5F, "red gain mismatch");
        cpp_isp::apply_channel_gains(candidate_view, matched.view(), gains);
        const auto matched_view = static_cast<const cpp_isp::ImageBuffer<float>&>(matched).view();
        const auto before = cpp_isp::evaluate_aligned_overlap(reference_view, candidate_view, 2, 6);
        const auto after = cpp_isp::evaluate_aligned_overlap(reference_view, matched_view, 2, 6);
        require(after.mean_color_delta < before.mean_color_delta, "color matching did not improve overlap");
        require(after.mean_alignment_error < 1.0e-5, "matched image should align numerically");

        cpp_isp::ImageBuffer<float> blended(8, 4, 3);
        cpp_isp::feather_blend_aligned(reference_view, candidate_view, blended.view(), 2, 6);
        require(std::abs(blended(0, 1, 0) - reference(0, 1, 0)) < 1.0e-6F, "left region mismatch");
        require(std::abs(blended(0, 6, 0) - candidate(0, 6, 0)) < 1.0e-6F, "right region mismatch");
        require(blended(0, 3, 0) < reference(0, 3, 0), "overlap should blend both inputs");

        bool rejected = false;
        try {
            cpp_isp::feather_blend_aligned(reference_view, candidate_view, blended.view(), 6, 2);
        } catch (const std::invalid_argument&) {
            rejected = true;
        }
        require(rejected, "invalid overlap must be rejected");
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
