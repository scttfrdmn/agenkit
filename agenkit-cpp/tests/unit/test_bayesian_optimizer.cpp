/**
 * @file test_bayesian_optimizer.cpp
 * @brief Unit tests for Bayesian optimization
 */

#include <gtest/gtest.h>
#include "agenkit/evaluation/bayesian_optimizer.hpp"
#include <cmath>

using namespace agenkit::evaluation;

// ============================================================================
// Test Objectives
// ============================================================================

/**
 * @brief Simple quadratic objective with known optimum
 *
 * f(x) = -(x - 0.7)² with optimum at x=0.7
 */
double quadratic_objective(const std::map<std::string, std::any>& config) {
    double x = std::any_cast<double>(config.at("x"));
    double optimal = 0.7;
    return -(x - optimal) * (x - optimal);  // Maximum at x=0.7
}

/**
 * @brief Multi-parameter objective
 *
 * f(x, y) = -(x - 0.6)² - (y - 0.4)² with optimum at (0.6, 0.4)
 */
double multivariate_objective(const std::map<std::string, std::any>& config) {
    double x = std::any_cast<double>(config.at("x"));
    double y = std::any_cast<double>(config.at("y"));
    return -(x - 0.6) * (x - 0.6) - (y - 0.4) * (y - 0.4);
}

/**
 * @brief Rosenbrock function (classic optimization benchmark)
 *
 * f(x, y) = (1-x)² + 100(y-x²)² with global minimum at (1, 1)
 * We negate it for maximization
 */
double rosenbrock_objective(const std::map<std::string, std::any>& config) {
    double x = std::any_cast<double>(config.at("x"));
    double y = std::any_cast<double>(config.at("y"));
    double a = 1.0 - x;
    double b = y - x * x;
    return -(a * a + 100.0 * b * b);  // Negate for maximization
}

// ============================================================================
// Constructor Tests
// ============================================================================

TEST(BayesianOptimizerTest, ConstructorDefaults) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(quadratic_objective, space, true);

    // Initial best_score should be -inf for maximization
    EXPECT_EQ(optimizer.get_best_score(), -std::numeric_limits<double>::infinity());
}

TEST(BayesianOptimizerTest, ConstructorWithParameters) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,                      // maximize
        AcquisitionFunction::EI,   // acquisition
        10,                        // n_initial
        0.05,                      // xi
        3.0                        // kappa
    );

    // Just verify construction doesn't crash
    EXPECT_EQ(optimizer.get_history().size(), 0);
}

// ============================================================================
// Single Variable Optimization Tests
// ============================================================================

TEST(BayesianOptimizerTest, OptimizeSingleVariable) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,  // maximize
        AcquisitionFunction::EI,
        5,     // n_initial
        0.01,
        2.576
    );

    auto result = optimizer.optimize(30).get();

    // Check that optimization ran
    EXPECT_EQ(result.n_iterations, 30);
    EXPECT_EQ(result.history.size(), 30);

    // Check that best config is close to optimum (0.7)
    double best_x = std::any_cast<double>(result.best_config.at("x"));
    EXPECT_GT(best_x, 0.5);  // Should be in right ballpark
    EXPECT_LT(best_x, 0.9);

    // Check that best score is reasonably good (close to 0, the maximum)
    EXPECT_GT(result.best_score, -0.1);  // Within 0.1 of maximum
}

TEST(BayesianOptimizerTest, MinimizeVsMaximize) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    // Maximize
    BayesianOptimizer max_optimizer(quadratic_objective, space, true);
    auto max_result = max_optimizer.optimize(20).get();

    // Minimize (with negated objective)
    auto minimize_obj = [](const std::map<std::string, std::any>& config) {
        return -quadratic_objective(config);  // Negate to minimize
    };
    BayesianOptimizer min_optimizer(minimize_obj, space, false);
    auto min_result = min_optimizer.optimize(20).get();

    // Maximizing quadratic should give near-zero score
    EXPECT_GT(max_result.best_score, -0.2);

    // Minimizing negated quadratic should give negative score
    EXPECT_LT(min_result.best_score, 0.2);
}

// ============================================================================
// Multi-Variable Optimization Tests
// ============================================================================

TEST(BayesianOptimizerTest, OptimizeMultipleVariables) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);
    space->add_continuous("y", 0.0, 1.0);

    BayesianOptimizer optimizer(
        multivariate_objective,
        space,
        true,
        AcquisitionFunction::EI,
        10
    );

    auto result = optimizer.optimize(50).get();

    // Check convergence
    double best_x = std::any_cast<double>(result.best_config.at("x"));
    double best_y = std::any_cast<double>(result.best_config.at("y"));

    // Should be close to optimum at (0.6, 0.4)
    EXPECT_GT(best_x, 0.3);
    EXPECT_LT(best_x, 0.9);
    EXPECT_GT(best_y, 0.1);
    EXPECT_LT(best_y, 0.7);

    // Best score should be close to 0 (maximum)
    EXPECT_GT(result.best_score, -0.15);
}

// ============================================================================
// Acquisition Function Tests
// ============================================================================

TEST(BayesianOptimizerTest, ExpectedImprovementAcquisition) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,
        AcquisitionFunction::EI
    );

    auto result = optimizer.optimize(25).get();

    EXPECT_EQ(result.metadata.at("acquisition"), std::string("expected_improvement"));
    EXPECT_GT(result.best_score, -0.2);
}

TEST(BayesianOptimizerTest, UpperConfidenceBoundAcquisition) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,
        AcquisitionFunction::UCB
    );

    auto result = optimizer.optimize(25).get();

    EXPECT_EQ(result.metadata.at("acquisition"), std::string("upper_confidence_bound"));
    EXPECT_GT(result.best_score, -0.2);
}

TEST(BayesianOptimizerTest, ProbabilityOfImprovementAcquisition) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,
        AcquisitionFunction::PI
    );

    auto result = optimizer.optimize(25).get();

    EXPECT_EQ(result.metadata.at("acquisition"), std::string("probability_of_improvement"));
    EXPECT_GT(result.best_score, -0.2);
}

// ============================================================================
// History and Metadata Tests
// ============================================================================

TEST(BayesianOptimizerTest, HistoryTracking) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(quadratic_objective, space, true);

    auto result = optimizer.optimize(20).get();

    EXPECT_EQ(result.history.size(), 20);

    // Verify each history step has config and score
    for (const auto& step : result.history) {
        EXPECT_FALSE(step.config.empty());
        EXPECT_TRUE(step.config.find("x") != step.config.end());
        EXPECT_TRUE(std::isfinite(step.score));
    }
}

TEST(BayesianOptimizerTest, MetadataPopulated) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,
        AcquisitionFunction::EI,
        7,    // n_initial
        0.02,  // xi
        3.0    // kappa
    );

    auto result = optimizer.optimize(15).get();

    EXPECT_TRUE(result.metadata.contains("algorithm"));
    EXPECT_EQ(result.metadata["algorithm"].get<std::string>(), "bayesian_optimization");
    EXPECT_EQ(result.metadata["acquisition"].get<std::string>(), "expected_improvement");
    EXPECT_EQ(result.metadata["n_initial"].get<int>(), 7);
    EXPECT_TRUE(result.metadata["maximize"].get<bool>());
    EXPECT_DOUBLE_EQ(result.metadata["xi"].get<double>(), 0.02);
    EXPECT_DOUBLE_EQ(result.metadata["kappa"].get<double>(), 3.0);
}

// ============================================================================
// Integer and Discrete Parameters Tests
// ============================================================================

TEST(BayesianOptimizerTest, IntegerParameters) {
    auto space = std::make_shared<SearchSpace>();
    space->add_integer("n", 1, 100);

    auto integer_objective = [](const std::map<std::string, std::any>& config) {
        int n = std::any_cast<int>(config.at("n"));
        // Optimal at n=50
        return -std::abs(n - 50.0);
    };

    BayesianOptimizer optimizer(integer_objective, space, true);

    auto result = optimizer.optimize(30).get();

    int best_n = std::any_cast<int>(result.best_config.at("n"));
    EXPECT_GT(best_n, 30);
    EXPECT_LT(best_n, 70);
}

TEST(BayesianOptimizerTest, DiscreteParameters) {
    auto space = std::make_shared<SearchSpace>();
    space->add_discrete("value", {0.1, 0.3, 0.5, 0.7, 0.9});

    auto discrete_objective = [](const std::map<std::string, std::any>& config) {
        double val = std::any_cast<double>(config.at("value"));
        // Optimal at 0.7
        return -std::abs(val - 0.7);
    };

    BayesianOptimizer optimizer(discrete_objective, space, true);

    auto result = optimizer.optimize(25).get();

    double best_val = std::any_cast<double>(result.best_config.at("value"));
    // Should pick one of the discrete values
    EXPECT_TRUE(best_val == 0.1 || best_val == 0.3 || best_val == 0.5 ||
                best_val == 0.7 || best_val == 0.9);
}

TEST(BayesianOptimizerTest, MixedParameterTypes) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);
    space->add_integer("n", 1, 10);
    space->add_discrete("scale", {1.0, 2.0, 3.0});

    auto mixed_objective = [](const std::map<std::string, std::any>& config) {
        double x = std::any_cast<double>(config.at("x"));
        int n = std::any_cast<int>(config.at("n"));
        double scale = std::any_cast<double>(config.at("scale"));

        // Optimal at x=0.5, n=5, scale=2.0
        return -(x - 0.5) * (x - 0.5) - (n - 5.0) * (n - 5.0) / 25.0 - (scale - 2.0) * (scale - 2.0);
    };

    BayesianOptimizer optimizer(mixed_objective, space, true);

    auto result = optimizer.optimize(50).get();

    // Just verify it runs without crashing and finds reasonable solution
    EXPECT_GT(result.best_score, -2.0);
}

// ============================================================================
// Performance and Convergence Tests
// ============================================================================

TEST(BayesianOptimizerTest, ConvergenceImprovement) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(quadratic_objective, space, true);

    auto result = optimizer.optimize(40).get();

    // Score should improve over iterations
    // Compare first 10 iterations to last 10 iterations
    double early_avg = 0.0;
    for (size_t i = 0; i < 10; ++i) {
        early_avg += result.history[i].score;
    }
    early_avg /= 10.0;

    double late_avg = 0.0;
    for (size_t i = 30; i < 40; ++i) {
        late_avg += result.history[i].score;
    }
    late_avg /= 10.0;

    // Later iterations should have better average score
    EXPECT_GT(late_avg, early_avg);
}

TEST(BayesianOptimizerTest, DurationTracking) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(quadratic_objective, space, true);

    auto result = optimizer.optimize(15).get();

    // Duration should be positive and reasonable
    EXPECT_GT(result.duration_seconds(), 0);
    EXPECT_LT(result.duration_seconds(), 10.0);  // Less than 10 seconds
}

// ============================================================================
// Edge Cases and Error Handling
// ============================================================================

TEST(BayesianOptimizerTest, SmallSearchSpace) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.5, 0.6);  // Very narrow range

    BayesianOptimizer optimizer(quadratic_objective, space, true);

    auto result = optimizer.optimize(10).get();

    // Should still work
    EXPECT_EQ(result.n_iterations, 10);
    double best_x = std::any_cast<double>(result.best_config.at("x"));
    EXPECT_GE(best_x, 0.5);
    EXPECT_LE(best_x, 0.6);
}

TEST(BayesianOptimizerTest, FewIterations) {
    auto space = std::make_shared<SearchSpace>();
    space->add_continuous("x", 0.0, 1.0);

    BayesianOptimizer optimizer(
        quadratic_objective,
        space,
        true,
        AcquisitionFunction::EI,
        3  // n_initial
    );

    // Run with only initial samples (no Bayesian phase)
    auto result = optimizer.optimize(3).get();

    EXPECT_EQ(result.n_iterations, 3);
    EXPECT_EQ(result.history.size(), 3);
}