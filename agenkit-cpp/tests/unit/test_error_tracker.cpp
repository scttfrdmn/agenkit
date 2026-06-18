/**
 * @file test_error_tracker.cpp
 * @brief Tests for ErrorTracker — per-step error rate (p_a) and compounding
 *        (P_error). Ported from tests/evaluation/test_error_tracker.py.
 */

#include "agenkit/evaluation/error_tracker.hpp"

#include <gtest/gtest.h>

#include <cmath>

using agenkit::evaluation::ErrorTracker;
using agenkit::evaluation::StepResult;

namespace {

constexpr double kEps = 1e-9;

} // namespace

// ============================================================================
// StepResult
// ============================================================================

TEST(StepResultTest, Defaults) {
    StepResult r{true, std::nullopt, std::nullopt};
    EXPECT_TRUE(r.success);
    EXPECT_FALSE(r.name.has_value());
    EXPECT_FALSE(r.error.has_value());
}

TEST(StepResultTest, FailureFields) {
    StepResult r{false, std::string("fetch"), std::string("timeout")};
    EXPECT_FALSE(r.success);
    ASSERT_TRUE(r.name.has_value());
    EXPECT_EQ(*r.name, "fetch");
    ASSERT_TRUE(r.error.has_value());
    EXPECT_EQ(*r.error, "timeout");
}

// ============================================================================
// Opt-in / disabled behavior
// ============================================================================

TEST(ErrorTrackerTest, DisabledByDefaultRecordsNothing) {
    ErrorTracker tracker;
    EXPECT_FALSE(tracker.enabled());
    tracker.record_step(false, std::nullopt, std::string("boom"));
    EXPECT_EQ(tracker.total_steps(), 0u);
    EXPECT_EQ(tracker.failed_steps(), 0u);
    EXPECT_NEAR(tracker.per_step_error_rate(), 0.0, kEps);
    EXPECT_NEAR(tracker.cumulative_failure_probability(), 0.0, kEps);
}

TEST(ErrorTrackerTest, EnabledRecordsSteps) {
    ErrorTracker tracker(true);
    tracker.record_step(true);
    tracker.record_step(false, std::nullopt, std::string("x"));
    EXPECT_EQ(tracker.total_steps(), 2u);
    EXPECT_EQ(tracker.failed_steps(), 1u);
}

// ============================================================================
// per_step_error_rate (p_a)
// ============================================================================

TEST(ErrorTrackerTest, PerStepErrorRateEmptyIsZero) {
    EXPECT_NEAR(ErrorTracker(true).per_step_error_rate(), 0.0, kEps);
}

TEST(ErrorTrackerTest, PerStepErrorRateAllSuccess) {
    ErrorTracker t(true);
    for (int i = 0; i < 5; ++i) {
        t.record_step(true);
    }
    EXPECT_NEAR(t.per_step_error_rate(), 0.0, kEps);
}

TEST(ErrorTrackerTest, PerStepErrorRateAllFail) {
    ErrorTracker t(true);
    for (int i = 0; i < 4; ++i) {
        t.record_step(false);
    }
    EXPECT_NEAR(t.per_step_error_rate(), 1.0, kEps);
}

TEST(ErrorTrackerTest, PerStepErrorRateMixed) {
    ErrorTracker t(true);
    // 2 failures out of 8 -> 0.25
    const bool outcomes[] = {true, false, true, true, false, true, true, true};
    for (bool ok : outcomes) {
        t.record_step(ok);
    }
    EXPECT_NEAR(t.per_step_error_rate(), 0.25, kEps);
}

// ============================================================================
// cumulative_failure_probability (P_error = 1 - (1 - p_a)^n)
// ============================================================================

TEST(ErrorTrackerTest, CumulativeEmptyIsZero) {
    EXPECT_NEAR(ErrorTracker(true).cumulative_failure_probability(), 0.0, kEps);
}

TEST(ErrorTrackerTest, CumulativeObservedUsesRecordedStepCount) {
    ErrorTracker t(true);
    t.record_step(true);
    t.record_step(false);
    // p_a = 0.5, n = 2 -> 1 - 0.5^2 = 0.75
    EXPECT_NEAR(t.cumulative_failure_probability(), 0.75, kEps);
}

TEST(ErrorTrackerTest, CumulativeProjectedSteps) {
    ErrorTracker t(true);
    t.record_step(true);
    t.record_step(false); // p_a = 0.5
    // project over 10 steps: 1 - 0.5^10
    EXPECT_NEAR(t.cumulative_failure_probability(10),
                1.0 - std::pow(0.5, 10), kEps);
}

TEST(ErrorTrackerTest, CumulativeCompoundingSmallRate) {
    // The motivating case: a small per-step rate compounds over a long run.
    ErrorTracker t(true);
    // p_a = 0.01 (1 failure in 100)
    t.record_step(false);
    for (int i = 0; i < 99; ++i) {
        t.record_step(true);
    }
    EXPECT_NEAR(t.per_step_error_rate(), 0.01, kEps);
    // Over 100 steps: 1 - 0.99^100 ~= 0.634
    const double p_error = t.cumulative_failure_probability(100);
    EXPECT_NEAR(p_error, 1.0 - std::pow(0.99, 100), kEps);
    EXPECT_GT(p_error, 0.63);
    EXPECT_LT(p_error, 0.64);
}

TEST(ErrorTrackerTest, CumulativeZeroRateIsZero) {
    ErrorTracker t(true);
    for (int i = 0; i < 10; ++i) {
        t.record_step(true);
    }
    EXPECT_NEAR(t.cumulative_failure_probability(1000), 0.0, kEps);
}

TEST(ErrorTrackerTest, CumulativeFullRateIsOne) {
    ErrorTracker t(true);
    t.record_step(false);
    EXPECT_NEAR(t.cumulative_failure_probability(5), 1.0, kEps);
}

TEST(ErrorTrackerTest, CumulativeNonPositiveStepsIsZero) {
    ErrorTracker t(true);
    t.record_step(false);
    EXPECT_NEAR(t.cumulative_failure_probability(0), 0.0, kEps);
    EXPECT_NEAR(t.cumulative_failure_probability(-3), 0.0, kEps);
}

TEST(ErrorTrackerTest, CumulativeInUnitInterval) {
    ErrorTracker t(true);
    const bool outcomes[] = {true, false, true, false, false};
    for (bool ok : outcomes) {
        t.record_step(ok);
    }
    for (int n = 1; n < 50; ++n) {
        const double p = t.cumulative_failure_probability(n);
        EXPECT_GE(p, 0.0);
        EXPECT_LE(p, 1.0);
        EXPECT_FALSE(std::isnan(p));
    }
}

// ============================================================================
// reset + docstring example
// ============================================================================

TEST(ErrorTrackerTest, ResetClearsSteps) {
    ErrorTracker t(true);
    t.record_step(true);
    t.record_step(false);
    t.reset();
    EXPECT_EQ(t.total_steps(), 0u);
    EXPECT_NEAR(t.per_step_error_rate(), 0.0, kEps);
}

TEST(ErrorTrackerTest, DocstringExampleValues) {
    ErrorTracker tracker(true);
    tracker.record_step(true);
    tracker.record_step(false, std::nullopt, std::string("timeout"));
    EXPECT_NEAR(tracker.per_step_error_rate(), 0.5, kEps);
    EXPECT_NEAR(tracker.cumulative_failure_probability(10), 0.999, 1e-4);
}
