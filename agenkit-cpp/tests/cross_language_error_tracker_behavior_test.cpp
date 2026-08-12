/**
 * @file cross_language_error_tracker_behavior_test.cpp
 * @brief Cross-language error tracker behavior tests for C++
 *
 * Validates that Agenkit's C++ ErrorTracker (p_a / P_error) behaves
 * consistently with the cross-language error tracker behavior specification
 * (#652, follow-up to #321).
 */

#include <gtest/gtest.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <filesystem>
#include <cmath>
#include <string>
#include <vector>
#include "agenkit/evaluation/error_tracker.hpp"

using json = nlohmann::json;
using agenkit::evaluation::ErrorTracker;

class ErrorTrackerBehaviorTest : public ::testing::Test {
protected:
    json fixtures;

    void SetUp() override {
        // Path from agenkit-cpp/tests to agenkit/tests/cross_language
        auto fixtures_path = std::filesystem::path(__FILE__).parent_path()
                           / ".." / ".." / "tests" / "cross_language"
                           / "fixtures" / "error_tracker_behavior.json";

        std::ifstream file(fixtures_path);
        ASSERT_TRUE(file.is_open()) << "Failed to open fixtures file: " << fixtures_path;
        fixtures = json::parse(file);
    }

    static std::vector<bool> buildSteps(const json& test_case) {
        if (test_case.contains("steps")) {
            return test_case["steps"].get<std::vector<bool>>();
        }
        const auto& spec = test_case["steps_spec"];
        std::vector<bool> steps;
        int fail = spec["fail"].get<int>();
        int success = spec["success"].get<int>();
        steps.insert(steps.end(), static_cast<size_t>(fail), false);
        steps.insert(steps.end(), static_cast<size_t>(success), true);
        return steps;
    }
};

TEST_F(ErrorTrackerBehaviorTest, MatchesFixtureForEveryTestCase) {
    ASSERT_TRUE(fixtures.contains("test_cases"));
    ASSERT_GT(fixtures["test_cases"].size(), 0u);

    for (const auto& test_case : fixtures["test_cases"]) {
        const std::string id = test_case["id"].get<std::string>();
        const auto& expected = test_case["expected"];
        double tolerance = expected.contains("tolerance")
            ? expected["tolerance"].get<double>()
            : 1e-6;

        ErrorTracker tracker(true);
        for (bool success : buildSteps(test_case)) {
            tracker.record_step(success);
        }

        EXPECT_EQ(tracker.total_steps(), expected["total_steps"].get<std::size_t>())
            << "[" << id << "] total_steps";
        EXPECT_EQ(tracker.failed_steps(), expected["failed_steps"].get<std::size_t>())
            << "[" << id << "] failed_steps";
        EXPECT_NEAR(tracker.per_step_error_rate(),
                    expected["per_step_error_rate"].get<double>(),
                    tolerance)
            << "[" << id << "] per_step_error_rate";

        if (expected.contains("cumulative_failure_probability_observed")) {
            EXPECT_NEAR(tracker.cumulative_failure_probability(),
                        expected["cumulative_failure_probability_observed"].get<double>(),
                        tolerance)
                << "[" << id << "] cumulative_failure_probability_observed";
        }

        for (const auto& [steps_str, expected_p] :
             expected["cumulative_failure_probability_steps"].items()) {
            int n = std::stoi(steps_str);
            EXPECT_NEAR(tracker.cumulative_failure_probability(n),
                        expected_p.get<double>(),
                        tolerance)
                << "[" << id << "] cumulative_failure_probability_steps[" << n << "]";
        }
    }
}
