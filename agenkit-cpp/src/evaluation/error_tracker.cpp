/**
 * @file error_tracker.cpp
 * @brief Implementation of per-step error rate and failure compounding.
 */

#include "agenkit/evaluation/error_tracker.hpp"

#include <algorithm>
#include <cmath>

namespace agenkit {
namespace evaluation {

void ErrorTracker::record_step(bool success,
                               std::optional<std::string> name,
                               std::optional<std::string> error) {
    if (!enabled_) {
        return;
    }
    step_results_.push_back(
        StepResult{success, std::move(name), std::move(error)});
}

std::size_t ErrorTracker::failed_steps() const {
    return static_cast<std::size_t>(
        std::count_if(step_results_.begin(), step_results_.end(),
                      [](const StepResult& r) { return !r.success; }));
}

double ErrorTracker::per_step_error_rate() const {
    const std::size_t total = step_results_.size();
    if (total == 0) {
        return 0.0;
    }
    return static_cast<double>(failed_steps()) / static_cast<double>(total);
}

double ErrorTracker::cumulative_failure_probability(
    std::optional<int> steps) const {
    const int n =
        steps.has_value() ? *steps : static_cast<int>(step_results_.size());
    if (n <= 0) {
        return 0.0;
    }
    const double p_a = per_step_error_rate();
    return 1.0 - std::pow(1.0 - p_a, n);
}

void ErrorTracker::reset() {
    step_results_.clear();
}

} // namespace evaluation
} // namespace agenkit
