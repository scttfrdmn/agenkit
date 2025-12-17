/**
 * @file test_optimizer.cpp
 * @brief Unit tests for optimizer framework
 */

#include <gtest/gtest.h>
#include "agenkit/evaluation/optimizer.hpp"
#include <thread>
#include <chrono>

using namespace agenkit::evaluation;

// SearchSpace Tests

TEST(SearchSpaceTest, AddContinuousParameter) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);

    const auto& params = space.parameters();
    ASSERT_EQ(params.size(), 1);
    ASSERT_EQ(params.count("temperature"), 1);
    EXPECT_EQ(params.at("temperature").type, ParameterType::Continuous);
    EXPECT_DOUBLE_EQ(params.at("temperature").low, 0.0);
    EXPECT_DOUBLE_EQ(params.at("temperature").high, 1.0);
}

TEST(SearchSpaceTest, AddDiscreteParameter) {
    SearchSpace space;
    space.add_discrete("max_tokens", {128.0, 256.0, 512.0});

    const auto& params = space.parameters();
    ASSERT_EQ(params.size(), 1);
    ASSERT_EQ(params.count("max_tokens"), 1);
    EXPECT_EQ(params.at("max_tokens").type, ParameterType::Discrete);
    EXPECT_EQ(params.at("max_tokens").values.size(), 3);
}

TEST(SearchSpaceTest, AddIntegerParameter) {
    SearchSpace space;
    space.add_integer("top_k", 1, 100);

    const auto& params = space.parameters();
    ASSERT_EQ(params.size(), 1);
    ASSERT_EQ(params.count("top_k"), 1);
    EXPECT_EQ(params.at("top_k").type, ParameterType::Integer);
    EXPECT_DOUBLE_EQ(params.at("top_k").low, 1.0);
    EXPECT_DOUBLE_EQ(params.at("top_k").high, 100.0);
}

TEST(SearchSpaceTest, AddCategoricalParameter) {
    SearchSpace space;
    space.add_categorical("model", {"gpt-4", "claude-3", "gemini"});

    const auto& params = space.parameters();
    ASSERT_EQ(params.size(), 1);
    ASSERT_EQ(params.count("model"), 1);
    EXPECT_EQ(params.at("model").type, ParameterType::Categorical);
    EXPECT_EQ(params.at("model").values.size(), 3);
}

TEST(SearchSpaceTest, SampleContinuous) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);

    // Sample multiple times to test distribution
    for (int i = 0; i < 10; ++i) {
        auto config = space.sample();
        ASSERT_EQ(config.size(), 1);
        ASSERT_EQ(config.count("temperature"), 1);

        double value = std::any_cast<double>(config.at("temperature"));
        EXPECT_GE(value, 0.0);
        EXPECT_LE(value, 1.0);
    }
}

TEST(SearchSpaceTest, SampleInteger) {
    SearchSpace space;
    space.add_integer("top_k", 1, 10);

    // Sample multiple times
    for (int i = 0; i < 10; ++i) {
        auto config = space.sample();
        ASSERT_EQ(config.size(), 1);
        ASSERT_EQ(config.count("top_k"), 1);

        int value = std::any_cast<int>(config.at("top_k"));
        EXPECT_GE(value, 1);
        EXPECT_LE(value, 10);
    }
}

TEST(SearchSpaceTest, SampleDiscrete) {
    SearchSpace space;
    space.add_discrete("max_tokens", {128.0, 256.0, 512.0});

    std::set<double> seen_values;
    for (int i = 0; i < 20; ++i) {
        auto config = space.sample();
        double value = std::any_cast<double>(config.at("max_tokens"));
        seen_values.insert(value);

        EXPECT_TRUE(value == 128.0 || value == 256.0 || value == 512.0);
    }

    // Should see at least 2 different values in 20 samples (probabilistically)
    EXPECT_GE(seen_values.size(), 2);
}

TEST(SearchSpaceTest, SampleCategorical) {
    SearchSpace space;
    space.add_categorical("model", {"gpt-4", "claude-3"});

    std::set<std::string> seen_values;
    for (int i = 0; i < 20; ++i) {
        auto config = space.sample();
        std::string value = std::any_cast<std::string>(config.at("model"));
        seen_values.insert(value);

        EXPECT_TRUE(value == "gpt-4" || value == "claude-3");
    }

    // Should see both values in 20 samples (probabilistically)
    EXPECT_EQ(seen_values.size(), 2);
}

TEST(SearchSpaceTest, SampleMultipleParameters) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);
    space.add_integer("top_k", 1, 100);
    space.add_categorical("model", {"gpt-4", "claude-3"});

    auto config = space.sample();
    EXPECT_EQ(config.size(), 3);
    EXPECT_EQ(config.count("temperature"), 1);
    EXPECT_EQ(config.count("top_k"), 1);
    EXPECT_EQ(config.count("model"), 1);
}

TEST(SearchSpaceTest, ValidateCorrectConfig) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);
    space.add_integer("top_k", 1, 100);

    std::map<std::string, std::any> config;
    config["temperature"] = 0.7;
    config["top_k"] = 50;

    EXPECT_TRUE(space.validate(config));
}

TEST(SearchSpaceTest, ValidateOutOfRangeContinuous) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);

    std::map<std::string, std::any> config;
    config["temperature"] = 1.5;  // Out of range

    EXPECT_FALSE(space.validate(config));
}

TEST(SearchSpaceTest, ValidateOutOfRangeInteger) {
    SearchSpace space;
    space.add_integer("top_k", 1, 100);

    std::map<std::string, std::any> config;
    config["top_k"] = 150;  // Out of range

    EXPECT_FALSE(space.validate(config));
}

TEST(SearchSpaceTest, ValidateMissingParameter) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);
    space.add_integer("top_k", 1, 100);

    std::map<std::string, std::any> config;
    config["temperature"] = 0.7;  // Missing top_k

    EXPECT_FALSE(space.validate(config));
}

TEST(SearchSpaceTest, ValidateUnknownParameter) {
    SearchSpace space;
    space.add_continuous("temperature", 0.0, 1.0);

    std::map<std::string, std::any> config;
    config["temperature"] = 0.7;
    config["unknown_param"] = 42;  // Unknown parameter

    EXPECT_FALSE(space.validate(config));
}

TEST(SearchSpaceTest, ValidateInvalidDiscreteValue) {
    SearchSpace space;
    space.add_discrete("max_tokens", {128.0, 256.0, 512.0});

    std::map<std::string, std::any> config;
    config["max_tokens"] = 300.0;  // Not in list

    EXPECT_FALSE(space.validate(config));
}

TEST(SearchSpaceTest, ValidateInvalidCategoricalValue) {
    SearchSpace space;
    space.add_categorical("model", {"gpt-4", "claude-3"});

    std::map<std::string, std::any> config;
    config["model"] = std::string("unknown-model");  // Not in list

    EXPECT_FALSE(space.validate(config));
}

// OptimizationResult Tests

TEST(OptimizationResultTest, DurationSeconds) {
    OptimizationResult result;
    result.start_time = std::chrono::system_clock::now();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    result.end_time = std::chrono::system_clock::now();

    double duration = result.duration_seconds();
    EXPECT_GE(duration, 0.1);
    EXPECT_LT(duration, 0.2);  // Should be close to 0.1s
}

TEST(OptimizationResultTest, GetImprovement) {
    OptimizationResult result;

    OptimizationStep step1;
    step1.score = 0.5;
    result.history.push_back(step1);

    OptimizationStep step2;
    step2.score = 0.7;
    result.history.push_back(step2);

    result.best_score = 0.7;

    double improvement = result.get_improvement();
    EXPECT_DOUBLE_EQ(improvement, 40.0);  // (0.7 - 0.5) / 0.5 * 100 = 40%
}

TEST(OptimizationResultTest, GetImprovementEmptyHistory) {
    OptimizationResult result;
    double improvement = result.get_improvement();
    EXPECT_DOUBLE_EQ(improvement, 0.0);
}

TEST(OptimizationResultTest, ToJsonFromJson) {
    OptimizationResult result;
    result.best_config["temperature"] = 0.7;
    result.best_config["top_k"] = 50;
    result.best_score = 0.85;
    result.n_iterations = 10;
    result.metadata["algorithm"] = "random_search";

    OptimizationStep step;
    step.config["temperature"] = 0.5;
    step.score = 0.75;
    result.history.push_back(step);

    // Serialize
    auto json = result.to_json();

    // Deserialize
    auto result2 = OptimizationResult::from_json(json);

    EXPECT_DOUBLE_EQ(result2.best_score, 0.85);
    EXPECT_EQ(result2.n_iterations, 10);
    EXPECT_EQ(result2.history.size(), 1);
    EXPECT_DOUBLE_EQ(result2.history[0].score, 0.75);
}

// RandomSearchOptimizer Tests

TEST(RandomSearchOptimizerTest, OptimizeMaximize) {
    // Create search space
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", -10.0, 10.0);

    // Objective: maximize -(x-3)^2 (peak at x=3)
    auto objective = [](const std::map<std::string, std::any>& config) -> double {
        double x = std::any_cast<double>(config.at("x"));
        return -(x - 3.0) * (x - 3.0);
    };

    // Run optimization
    RandomSearchOptimizer optimizer(objective, space, true);
    auto result = optimizer.optimize(50).get();

    EXPECT_EQ(result.n_iterations, 50);
    EXPECT_EQ(result.history.size(), 50);

    // Best x should be close to 3
    double best_x = std::any_cast<double>(result.best_config.at("x"));
    EXPECT_GE(best_x, 1.0);
    EXPECT_LE(best_x, 5.0);

    // Best score should be close to 0 (the maximum)
    EXPECT_GE(result.best_score, -4.0);  // Within reasonable range
}

TEST(RandomSearchOptimizerTest, OptimizeMinimize) {
    // Create search space
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", -10.0, 10.0);

    // Objective: minimize (x-3)^2 (minimum at x=3)
    auto objective = [](const std::map<std::string, std::any>& config) -> double {
        double x = std::any_cast<double>(config.at("x"));
        return (x - 3.0) * (x - 3.0);
    };

    // Run optimization (minimize)
    RandomSearchOptimizer optimizer(objective, space, false);
    auto result = optimizer.optimize(50).get();

    EXPECT_EQ(result.n_iterations, 50);

    // Best x should be close to 3
    double best_x = std::any_cast<double>(result.best_config.at("x"));
    EXPECT_GE(best_x, 1.0);
    EXPECT_LE(best_x, 5.0);

    // Best score should be negative (since we negate for minimization)
    // and close to 0 (the minimum)
    EXPECT_LE(result.best_score, 0.0);
    EXPECT_GE(result.best_score, -4.0);
}

TEST(RandomSearchOptimizerTest, OptimizeMultipleParameters) {
    // Create search space
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", -5.0, 5.0);
    space->add_continuous("y", -5.0, 5.0);

    // Objective: maximize -(x^2 + y^2) (peak at (0,0))
    auto objective = [](const std::map<std::string, std::any>& config) -> double {
        double x = std::any_cast<double>(config.at("x"));
        double y = std::any_cast<double>(config.at("y"));
        return -(x*x + y*y);
    };

    // Run optimization
    RandomSearchOptimizer optimizer(objective, space, true);
    auto result = optimizer.optimize(100).get();

    EXPECT_EQ(result.n_iterations, 100);

    // Best should be close to (0, 0)
    double best_x = std::any_cast<double>(result.best_config.at("x"));
    double best_y = std::any_cast<double>(result.best_config.at("y"));

    // With 100 samples, should get reasonably close
    EXPECT_GE(best_x, -3.0);
    EXPECT_LE(best_x, 3.0);
    EXPECT_GE(best_y, -3.0);
    EXPECT_LE(best_y, 3.0);

    // Best score should be close to 0
    EXPECT_GE(result.best_score, -10.0);
}

TEST(RandomSearchOptimizerTest, ImprovementCalculation) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 10.0);

    // Objective that improves
    auto objective = [](const std::map<std::string, std::any>& config) -> double {
        double x = std::any_cast<double>(config.at("x"));
        return x;  // Higher is better
    };

    RandomSearchOptimizer optimizer(objective, space, true);
    auto result = optimizer.optimize(20).get();

    // Should see improvement
    double improvement = result.get_improvement();
    EXPECT_GT(improvement, 0.0);
}
