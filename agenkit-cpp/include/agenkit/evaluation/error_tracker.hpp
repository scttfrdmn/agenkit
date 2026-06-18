/**
 * @file error_tracker.hpp
 * @brief Error tracking — per-step error rate and failure compounding.
 *
 * Long-running agents execute many steps; even a small per-step error rate
 * compounds into a high probability of at least one failure over a long run.
 * ErrorTracker records the outcome of each step and exposes the two core
 * quantities from the agent-failure-rate analysis:
 *
 * - p_a (per_step_error_rate) — the per-step error rate,
 *   failed_steps / total_steps.
 * - P_error (cumulative_failure_probability) — the probability of at least one
 *   failure across n independent steps, 1 - (1 - p_a)^n. With no argument, n is
 *   the number of recorded steps (observed cumulative failure probability);
 *   pass steps=N to project the compounding over a planned run of N steps.
 *
 * Tracking is opt-in: construct an ErrorTracker(true) and call record_step as
 * steps complete. When disabled (the default), record_step is a no-op and the
 * metrics report zero, so the tracker is cheap to leave wired in.
 *
 * Mirrors the Python reference implementation (agenkit/evaluation/error_tracker.py).
 */

#ifndef AGENKIT_EVALUATION_ERROR_TRACKER_HPP
#define AGENKIT_EVALUATION_ERROR_TRACKER_HPP

#include <optional>
#include <string>
#include <vector>

namespace agenkit {
namespace evaluation {

/**
 * @brief Outcome of a single agent step.
 */
struct StepResult {
    /** Whether the step completed without error. */
    bool success;

    /** Optional step label (useful for per-step breakdowns later). */
    std::optional<std::string> name;

    /** Optional error description when success is false. */
    std::optional<std::string> error;
};

/**
 * @brief Records step outcomes and computes error-rate / compounding metrics.
 *
 * @details
 * When disabled (the default), record_step is a no-op and all metrics report
 * 0.0 / 0 — tracking is strictly opt-in.
 *
 * @example
 * @code
 * ErrorTracker tracker(true);
 * tracker.record_step(true);
 * tracker.record_step(false, std::nullopt, "timeout");
 * tracker.per_step_error_rate();                       // 0.5
 * tracker.cumulative_failure_probability(10);          // ~0.999
 * @endcode
 */
class ErrorTracker {
public:
    /**
     * @brief Construct an error tracker.
     * @param enabled When false (the default), record_step is a no-op and all
     *        metrics report 0.0 / 0.
     */
    explicit ErrorTracker(bool enabled = false) : enabled_(enabled) {}

    /** @brief Whether tracking is enabled. */
    bool enabled() const { return enabled_; }

    /**
     * @brief Record the outcome of one step (no-op when disabled).
     * @param success Whether the step succeeded.
     * @param name Optional step label.
     * @param error Optional error description for a failed step.
     */
    void record_step(bool success,
                     std::optional<std::string> name = std::nullopt,
                     std::optional<std::string> error = std::nullopt);

    /** @brief Number of recorded steps. */
    std::size_t total_steps() const { return step_results_.size(); }

    /** @brief Number of recorded steps that failed. */
    std::size_t failed_steps() const;

    /**
     * @brief Per-step error rate p_a = failed_steps / total_steps.
     * @return 0.0 when no steps have been recorded.
     */
    double per_step_error_rate() const;

    /**
     * @brief Probability of at least one failure over n steps.
     *
     * P_error = 1 - (1 - p_a)^n where n is steps if given, otherwise the number
     * of recorded steps. Models error compounding: independent steps each
     * succeed with probability 1 - p_a, so the run succeeds only if all n
     * succeed.
     *
     * @param steps Project the compounding over this many steps. Defaults to the
     *        number of recorded steps (observed cumulative probability).
     * @return A probability in [0.0, 1.0]. Returns 0.0 if p_a is 0 or n <= 0.
     */
    double cumulative_failure_probability(
        std::optional<int> steps = std::nullopt) const;

    /** @brief Clear all recorded step results. */
    void reset();

    /** @brief Read-only access to the recorded step results. */
    const std::vector<StepResult>& step_results() const { return step_results_; }

private:
    bool enabled_;
    std::vector<StepResult> step_results_;
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_ERROR_TRACKER_HPP
