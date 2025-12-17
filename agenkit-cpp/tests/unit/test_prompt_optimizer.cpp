/**
 * @file test_prompt_optimizer.cpp
 * @brief Tests for prompt optimization framework
 */

#include "agenkit/evaluation/prompt_optimizer.hpp"
#include <gtest/gtest.h>
#include <cmath>

using namespace agenkit::evaluation;

// ============================================================================
// Test Objectives
// ============================================================================

/**
 * Simple objective: Score based on role and style combination
 * "advisor" + "detailed" = optimal (score 1.0)
 */
double simple_objective(const std::string& prompt) {
    double score = 0.0;

    if (prompt.find("advisor") != std::string::npos) {
        score += 0.6;
    }
    if (prompt.find("detailed") != std::string::npos) {
        score += 0.4;
    }

    return score;
}

/**
 * Length-based objective: Prefer shorter prompts
 */
double length_objective(const std::string& prompt) {
    // Score inversely proportional to length
    return 1.0 / (1.0 + prompt.length() / 100.0);
}

/**
 * Multi-factor objective: Complex scoring
 */
double complex_objective(const std::string& prompt) {
    double score = 0.5;  // Base score

    // Prefer "expert"
    if (prompt.find("expert") != std::string::npos) {
        score += 0.3;
    }
    // Prefer "concise"
    if (prompt.find("concise") != std::string::npos) {
        score += 0.2;
    }
    // Penalize long prompts
    if (prompt.length() > 50) {
        score -= 0.1;
    }

    return score;
}

// ============================================================================
// Constructor Tests
// ============================================================================

TEST(PromptOptimizerTest, ConstructorValid) {
    std::string template_str = "You are a {role}.";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor"}}
    };

    EXPECT_NO_THROW({
        PromptOptimizer optimizer(template_str, variations, simple_objective);
    });
}

TEST(PromptOptimizerTest, ConstructorEmptyTemplate) {
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant"}}
    };

    EXPECT_THROW({
        PromptOptimizer optimizer("", variations, simple_objective);
    }, std::invalid_argument);
}

TEST(PromptOptimizerTest, ConstructorEmptyVariations) {
    std::string template_str = "You are a {role}.";
    std::map<std::string, std::vector<std::string>> variations;

    EXPECT_THROW({
        PromptOptimizer optimizer(template_str, variations, simple_objective);
    }, std::invalid_argument);
}

TEST(PromptOptimizerTest, ConstructorEmptyVariationValues) {
    std::string template_str = "You are a {role}.";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {}}  // Empty values
    };

    EXPECT_THROW({
        PromptOptimizer optimizer(template_str, variations, simple_objective);
    }, std::invalid_argument);
}

// ============================================================================
// Grid Search Tests
// ============================================================================

TEST(PromptOptimizerTest, GridSearchSmall) {
    std::string template_str = "You are a {role}. {style}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor"}},
        {"style", {"Be brief.", "Be detailed."}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    // Should evaluate all 2x2 = 4 combinations
    EXPECT_EQ(result.n_evaluated, 4);
    EXPECT_EQ(result.history.size(), 4);
    EXPECT_EQ(result.strategy, OptimizationStrategy::GRID);

    // Best should be "advisor" + "detailed"
    EXPECT_NE(result.best_prompt.find("advisor"), std::string::npos);
    EXPECT_NE(result.best_prompt.find("detailed"), std::string::npos);
    EXPECT_DOUBLE_EQ(result.best_scores.at("objective"), 1.0);
}

TEST(PromptOptimizerTest, GridSearchLarge) {
    std::string template_str = "{a}{b}{c}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"a", {"1", "2", "3"}},
        {"b", {"A", "B", "C"}},
        {"c", {"x", "y", "z"}}
    };

    auto objective = [](const std::string& prompt) {
        // Prefer "2Bx"
        return (prompt == "2Bx") ? 1.0 : 0.5;
    };

    PromptOptimizer optimizer(template_str, variations, objective);

    auto result = optimizer.optimize_grid().get();

    // Should evaluate all 3x3x3 = 27 combinations
    EXPECT_EQ(result.n_evaluated, 27);
    EXPECT_EQ(result.history.size(), 27);

    // Best should be "2Bx"
    EXPECT_EQ(result.best_prompt, "2Bx");
    EXPECT_DOUBLE_EQ(result.best_scores.at("objective"), 1.0);
}

// ============================================================================
// Random Search Tests
// ============================================================================

TEST(PromptOptimizerTest, RandomSearchSamples) {
    std::string template_str = "You are a {role}.";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor", "guide", "expert"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_random(10).get();

    // Should evaluate exactly 10 samples
    EXPECT_EQ(result.n_evaluated, 10);
    EXPECT_EQ(result.history.size(), 10);
    EXPECT_EQ(result.strategy, OptimizationStrategy::RANDOM);

    // Should have found something
    EXPECT_FALSE(result.best_prompt.empty());
    EXPECT_GT(result.best_scores.at("objective"), 0.0);
}

TEST(PromptOptimizerTest, RandomSearchFindsGood) {
    std::string template_str = "You are a {role}. {style}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor", "guide"}},
        {"style", {"Be brief.", "Be detailed.", "Be friendly."}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    // With 20 samples from 9 combinations, likely to find optimal
    auto result = optimizer.optimize_random(20).get();

    EXPECT_EQ(result.n_evaluated, 20);
    // Should find at least a good solution (>= 0.6)
    EXPECT_GE(result.best_scores.at("objective"), 0.6);
}

// ============================================================================
// Genetic Algorithm Tests
// ============================================================================

TEST(PromptOptimizerTest, GeneticAlgorithmBasic) {
    std::string template_str = "You are a {role}. {style}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor"}},
        {"style", {"Be brief.", "Be detailed."}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_genetic(
        4,    // population_size
        3,    // n_generations
        0.3   // mutation_rate
    ).get();

    // Should evaluate: initial_pop + (n_gen * pop_size) = 4 + (3 * 4) = 16
    EXPECT_EQ(result.n_evaluated, 16);
    EXPECT_EQ(result.history.size(), 16);
    EXPECT_EQ(result.strategy, OptimizationStrategy::GENETIC);

    // Should find a decent solution
    EXPECT_GT(result.best_scores.at("objective"), 0.5);
}

TEST(PromptOptimizerTest, GeneticAlgorithmConvergence) {
    std::string template_str = "{role} {style} {tone}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"advisor", "guide", "mentor"}},
        {"style", {"detailed", "thorough", "comprehensive"}},
        {"tone", {"professional", "friendly", "formal"}}
    };

    auto objective = [](const std::string& prompt) {
        double score = 0.0;
        if (prompt.find("advisor") != std::string::npos) score += 0.4;
        if (prompt.find("detailed") != std::string::npos) score += 0.4;
        if (prompt.find("professional") != std::string::npos) score += 0.2;
        return score;
    };

    PromptOptimizer optimizer(template_str, variations, objective);

    auto result = optimizer.optimize_genetic(
        10,   // population_size
        5,    // n_generations
        0.2   // mutation_rate
    ).get();

    // Should evaluate: 10 + (5 * 10) = 60
    EXPECT_EQ(result.n_evaluated, 60);

    // Should converge to near-optimal (>= 0.8 out of 1.0)
    EXPECT_GE(result.best_scores.at("objective"), 0.8);
}

// ============================================================================
// Maximize vs Minimize Tests
// ============================================================================

TEST(PromptOptimizerTest, MaximizeObjective) {
    std::string template_str = "Length: {size}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"size", {"short", "medium", "very long indeed"}}
    };

    auto objective = [](const std::string& prompt) {
        return static_cast<double>(prompt.length());
    };

    PromptOptimizer optimizer(template_str, variations, objective, true);  // maximize

    auto result = optimizer.optimize_grid().get();

    // Should prefer longest
    EXPECT_NE(result.best_prompt.find("very long indeed"), std::string::npos);
}

TEST(PromptOptimizerTest, MinimizeObjective) {
    std::string template_str = "Length: {size}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"size", {"short", "medium", "very long indeed"}}
    };

    auto objective = [](const std::string& prompt) {
        return static_cast<double>(prompt.length());
    };

    PromptOptimizer optimizer(template_str, variations, objective, false);  // minimize

    auto result = optimizer.optimize_grid().get();

    // Should prefer shortest
    EXPECT_NE(result.best_prompt.find("short"), std::string::npos);
}

// ============================================================================
// Search Space Tests
// ============================================================================

TEST(PromptOptimizerTest, SearchSpaceSize) {
    std::string template_str = "{a}{b}{c}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"a", {"1", "2"}},
        {"b", {"A", "B", "C"}},
        {"c", {"x", "y", "z", "w"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    // 2 * 3 * 4 = 24
    EXPECT_EQ(optimizer.get_search_space_size(), 24);
}

TEST(PromptOptimizerTest, SearchSpaceSingleVariable) {
    std::string template_str = "{role}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"a", "b", "c", "d", "e"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    EXPECT_EQ(optimizer.get_search_space_size(), 5);
}

// ============================================================================
// Duration Tracking Tests
// ============================================================================

TEST(PromptOptimizerTest, DurationTracking) {
    std::string template_str = "{x}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"x", {"1", "2", "3"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    // Duration should be non-negative and reasonable
    EXPECT_GE(result.duration_seconds(), 0.0);
    EXPECT_LT(result.duration_seconds(), 10.0);  // Should be fast

    // Timestamps should be set
    EXPECT_NE(result.start_time.time_since_epoch().count(), 0);
    EXPECT_NE(result.end_time.time_since_epoch().count(), 0);
    EXPECT_GE(result.end_time, result.start_time);
}

// ============================================================================
// Template Filling Tests
// ============================================================================

TEST(PromptOptimizerTest, TemplateFillingSingle) {
    std::string template_str = "You are a {role}.";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    EXPECT_EQ(result.best_prompt, "You are a assistant.");
}

TEST(PromptOptimizerTest, TemplateFillingMultiple) {
    std::string template_str = "{greeting} I am a {role}. {outro}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"greeting", {"Hello!"}},
        {"role", {"helper"}},
        {"outro", {"How can I assist?"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    EXPECT_EQ(result.best_prompt, "Hello! I am a helper. How can I assist?");
}

TEST(PromptOptimizerTest, TemplateFillingRepeated) {
    std::string template_str = "{x} and {x} again";
    std::map<std::string, std::vector<std::string>> variations = {
        {"x", {"test"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    EXPECT_EQ(result.best_prompt, "test and test again");
}

// ============================================================================
// History Tracking Tests
// ============================================================================

TEST(PromptOptimizerTest, HistoryTracking) {
    std::string template_str = "{x}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"x", {"a", "b", "c"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    // History should have all evaluations
    EXPECT_EQ(result.history.size(), 3);

    // Each history entry should have prompt, config, and scores
    for (const auto& [prompt, config, scores] : result.history) {
        EXPECT_FALSE(prompt.empty());
        EXPECT_FALSE(config.empty());
        EXPECT_TRUE(scores.find("objective") != scores.end());
    }
}

// ============================================================================
// Edge Cases
// ============================================================================

TEST(PromptOptimizerTest, SingleConfiguration) {
    std::string template_str = "{role}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant"}}  // Only one option
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    EXPECT_EQ(result.n_evaluated, 1);
    EXPECT_EQ(result.history.size(), 1);
    EXPECT_EQ(result.best_config.at("role"), "assistant");
}

TEST(PromptOptimizerTest, TemplateNoPlaceholders) {
    std::string template_str = "Static prompt with no variables.";
    std::map<std::string, std::vector<std::string>> variations = {
        {"unused", {"value"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    auto result = optimizer.optimize_grid().get();

    // Should still work, just returns static prompt
    EXPECT_EQ(result.best_prompt, "Static prompt with no variables.");
}

TEST(PromptOptimizerTest, GeneticWithZeroMutation) {
    std::string template_str = "{x}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"x", {"a", "b"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    // Zero mutation rate - population should still evolve through selection
    auto result = optimizer.optimize_genetic(5, 3, 0.0).get();

    EXPECT_EQ(result.n_evaluated, 20);  // 5 + (3 * 5)
    EXPECT_FALSE(result.best_prompt.empty());
}

TEST(PromptOptimizerTest, GeneticWithFullMutation) {
    std::string template_str = "{x}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"x", {"a", "b", "c"}}
    };

    PromptOptimizer optimizer(template_str, variations, simple_objective);

    // Full mutation rate - should explore widely
    auto result = optimizer.optimize_genetic(5, 3, 1.0).get();

    EXPECT_EQ(result.n_evaluated, 20);
    EXPECT_FALSE(result.best_prompt.empty());
}
