/**
 * @file prompt_optimizer_example.cpp
 * @brief Example demonstrating automated prompt optimization
 *
 * This example shows how to use prompt optimization to automatically
 * find better prompts through systematic variation. It demonstrates:
 * - Defining templates with variable placeholders
 * - Grid search for exhaustive exploration
 * - Random search for efficient sampling
 * - Genetic algorithms for large search spaces
 * - Comparing optimization strategies
 */

#include "agenkit/evaluation/prompt_optimizer.hpp"
#include <iostream>
#include <iomanip>
#include <cmath>

using namespace agenkit::evaluation;

/**
 * Simulated agent evaluation objective
 *
 * In reality, this would:
 * 1. Create an agent with the given prompt
 * 2. Run it on test cases
 * 3. Return accuracy, quality, or other metric
 *
 * For this example, we use a scoring function with known optimal prompt:
 * - Role: "expert advisor" (best)
 * - Tone: "professional" (best)
 * - Instructions: "Be concise and accurate." (best)
 */
double evaluate_prompt_quality(const std::string& prompt) {
    double score = 0.0;

    // Role scoring (40% weight)
    if (prompt.find("expert advisor") != std::string::npos) {
        score += 0.40;
    } else if (prompt.find("advisor") != std::string::npos) {
        score += 0.30;
    } else if (prompt.find("assistant") != std::string::npos) {
        score += 0.20;
    }

    // Tone scoring (30% weight)
    if (prompt.find("professional") != std::string::npos) {
        score += 0.30;
    } else if (prompt.find("friendly") != std::string::npos) {
        score += 0.20;
    } else if (prompt.find("casual") != std::string::npos) {
        score += 0.10;
    }

    // Instructions scoring (30% weight)
    if (prompt.find("concise and accurate") != std::string::npos) {
        score += 0.30;
    } else if (prompt.find("detailed and thorough") != std::string::npos) {
        score += 0.20;
    } else if (prompt.find("brief and clear") != std::string::npos) {
        score += 0.15;
    }

    return score;
}

/**
 * Print prompt configuration and score
 */
void print_result(const std::string& label, const PromptOptimizationResult& result) {
    std::cout << label << ":" << std::endl;
    std::cout << "  Best Score: " << std::fixed << std::setprecision(3)
              << result.best_scores.at("objective") << std::endl;
    std::cout << "  Evaluations: " << result.n_evaluated << std::endl;
    std::cout << "  Duration: " << std::setprecision(2)
              << result.duration_seconds() << "s" << std::endl;
    std::cout << "  Best Config:" << std::endl;
    for (const auto& [key, value] : result.best_config) {
        std::cout << "    " << key << ": " << value << std::endl;
    }
    std::cout << "  Best Prompt: \"" << result.best_prompt << "\"" << std::endl;
    std::cout << std::endl;
}

/**
 * Demonstrate grid search optimization
 */
void demonstrate_grid_search() {
    std::cout << "=== Grid Search: Exhaustive Exploration ===" << std::endl;
    std::cout << std::endl;

    // Step 1: Define template
    std::cout << "1. Defining prompt template:" << std::endl;
    std::string template_str = R"(You are a {role}. Use a {tone} tone. {instructions})";
    std::cout << "   Template: \"" << template_str << "\"" << std::endl;
    std::cout << std::endl;

    // Step 2: Define variations
    std::cout << "2. Defining variable variations:" << std::endl;
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor"}},
        {"tone", {"friendly", "professional"}},
        {"instructions", {"Be brief and clear.", "Be concise and accurate."}}
    };

    for (const auto& [key, values] : variations) {
        std::cout << "   " << key << ": ";
        for (size_t i = 0; i < values.size(); ++i) {
            if (i > 0) std::cout << ", ";
            std::cout << "\"" << values[i] << "\"";
        }
        std::cout << std::endl;
    }
    std::cout << std::endl;

    // Step 3: Create optimizer
    std::cout << "3. Creating optimizer:" << std::endl;
    PromptOptimizer optimizer(template_str, variations, evaluate_prompt_quality);
    size_t search_space_size = optimizer.get_search_space_size();
    std::cout << "   Search space size: " << search_space_size << " configurations" << std::endl;
    std::cout << std::endl;

    // Step 4: Run grid search
    std::cout << "4. Running grid search..." << std::endl;
    auto result = optimizer.optimize_grid().get();
    std::cout << std::endl;

    // Step 5: Show results
    std::cout << "5. Grid Search Results:" << std::endl;
    print_result("   ", result);

    std::cout << "   Interpretation:" << std::endl;
    std::cout << "   • Grid search evaluated ALL " << search_space_size << " combinations" << std::endl;
    std::cout << "   • Guarantees finding the global optimum" << std::endl;
    std::cout << "   • Best for small search spaces (< 100 configs)" << std::endl;
    std::cout << std::endl;
}

/**
 * Demonstrate random search optimization
 */
void demonstrate_random_search() {
    std::cout << "=== Random Search: Efficient Sampling ===" << std::endl;
    std::cout << std::endl;

    // Larger search space
    std::string template_str = R"(You are a {role}. Use a {tone} tone. {instructions})";

    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor", "expert advisor", "guide"}},
        {"tone", {"casual", "friendly", "professional", "formal"}},
        {"instructions", {
            "Be brief and clear.",
            "Be concise and accurate.",
            "Be detailed and thorough.",
            "Be comprehensive."
        }}
    };

    PromptOptimizer optimizer(template_str, variations, evaluate_prompt_quality);
    size_t search_space_size = optimizer.get_search_space_size();

    std::cout << "Search space: " << search_space_size << " total configurations" << std::endl;
    std::cout << "Sampling only 20 random configurations..." << std::endl;
    std::cout << std::endl;

    auto result = optimizer.optimize_random(20).get();

    std::cout << "Random Search Results:" << std::endl;
    print_result("  ", result);

    std::cout << "  Efficiency: Evaluated only " << result.n_evaluated
              << "/" << search_space_size << " configurations ("
              << std::fixed << std::setprecision(1)
              << (100.0 * result.n_evaluated / search_space_size) << "%)" << std::endl;
    std::cout << std::endl;

    std::cout << "  When to use Random Search:" << std::endl;
    std::cout << "  ✓ Large search spaces (> 100 configurations)" << std::endl;
    std::cout << "  ✓ When you need fast results" << std::endl;
    std::cout << "  ✓ When near-optimal is good enough" << std::endl;
    std::cout << std::endl;
}

/**
 * Demonstrate genetic algorithm optimization
 */
void demonstrate_genetic_algorithm() {
    std::cout << "=== Genetic Algorithm: Evolutionary Optimization ===" << std::endl;
    std::cout << std::endl;

    std::string template_str = R"(You are a {role}. Use a {tone} tone. {instructions} {style})";

    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor", "expert advisor", "guide", "mentor"}},
        {"tone", {"casual", "friendly", "professional", "formal", "authoritative"}},
        {"instructions", {
            "Be brief and clear.",
            "Be concise and accurate.",
            "Be detailed and thorough.",
            "Be comprehensive.",
            "Focus on key points."
        }},
        {"style", {
            "Use simple language.",
            "Use technical terms when appropriate.",
            "Provide examples.",
            "Include reasoning."
        }}
    };

    PromptOptimizer optimizer(template_str, variations, evaluate_prompt_quality);
    size_t search_space_size = optimizer.get_search_space_size();

    std::cout << "Search space: " << search_space_size << " total configurations" << std::endl;
    std::cout << "Running genetic algorithm:" << std::endl;
    std::cout << "  - Population size: 10" << std::endl;
    std::cout << "  - Generations: 5" << std::endl;
    std::cout << "  - Mutation rate: 0.2" << std::endl;
    std::cout << "  - Total evaluations: 10 + (5 × 10) = 60" << std::endl;
    std::cout << std::endl;

    auto result = optimizer.optimize_genetic(
        10,   // population_size
        5,    // n_generations
        0.2   // mutation_rate
    ).get();

    std::cout << "Genetic Algorithm Results:" << std::endl;
    print_result("  ", result);

    std::cout << "  How it works:" << std::endl;
    std::cout << "  1. Initialize random population" << std::endl;
    std::cout << "  2. Evaluate fitness (objective score)" << std::endl;
    std::cout << "  3. Select fitter individuals (tournament)" << std::endl;
    std::cout << "  4. Mutate (randomly change variables)" << std::endl;
    std::cout << "  5. Repeat for multiple generations" << std::endl;
    std::cout << std::endl;

    std::cout << "  When to use Genetic Algorithm:" << std::endl;
    std::cout << "  ✓ Very large search spaces (> 1000 configurations)" << std::endl;
    std::cout << "  ✓ When you have budget for multiple generations" << std::endl;
    std::cout << "  ✓ Smooth fitness landscapes (similar prompts = similar scores)" << std::endl;
    std::cout << std::endl;
}

/**
 * Compare all three strategies
 */
void compare_strategies() {
    std::cout << "=== Comparing Strategies ===" << std::endl;
    std::cout << std::endl;

    std::string template_str = "You are a {role}. {style}";
    std::map<std::string, std::vector<std::string>> variations = {
        {"role", {"assistant", "advisor", "expert advisor"}},
        {"style", {"Be brief.", "Be detailed.", "Be friendly.", "Be professional."}}
    };

    PromptOptimizer optimizer(template_str, variations, evaluate_prompt_quality);
    size_t search_space_size = optimizer.get_search_space_size();

    std::cout << "Search space: " << search_space_size << " configurations" << std::endl;
    std::cout << std::endl;

    // Run all strategies
    std::cout << "Running all three strategies..." << std::endl;
    std::cout << std::endl;

    auto grid_result = optimizer.optimize_grid().get();
    auto random_result = optimizer.optimize_random(8).get();
    auto genetic_result = optimizer.optimize_genetic(5, 3, 0.3).get();

    // Print comparison table
    std::cout << "Results Comparison:" << std::endl;
    std::cout << "────────────────────────────────────────────────────────────" << std::endl;
    std::cout << std::setw(20) << "Strategy"
              << std::setw(15) << "Best Score"
              << std::setw(15) << "Evaluations"
              << std::setw(12) << "Time (s)" << std::endl;
    std::cout << "────────────────────────────────────────────────────────────" << std::endl;

    std::cout << std::setw(20) << "Grid Search"
              << std::setw(15) << std::fixed << std::setprecision(3)
              << grid_result.best_scores.at("objective")
              << std::setw(15) << grid_result.n_evaluated
              << std::setw(12) << std::setprecision(2)
              << grid_result.duration_seconds() << std::endl;

    std::cout << std::setw(20) << "Random Search"
              << std::setw(15) << std::fixed << std::setprecision(3)
              << random_result.best_scores.at("objective")
              << std::setw(15) << random_result.n_evaluated
              << std::setw(12) << std::setprecision(2)
              << random_result.duration_seconds() << std::endl;

    std::cout << std::setw(20) << "Genetic Algorithm"
              << std::setw(15) << std::fixed << std::setprecision(3)
              << genetic_result.best_scores.at("objective")
              << std::setw(15) << genetic_result.n_evaluated
              << std::setw(12) << std::setprecision(2)
              << genetic_result.duration_seconds() << std::endl;

    std::cout << "────────────────────────────────────────────────────────────" << std::endl;
    std::cout << std::endl;
}

/**
 * Best practices guide
 */
void show_best_practices() {
    std::cout << "=== Best Practices ===" << std::endl;
    std::cout << std::endl;

    std::cout << "1. Choosing a Strategy:" << std::endl;
    std::cout << "   • Search space < 50: Use Grid Search" << std::endl;
    std::cout << "   • Search space 50-500: Use Random Search (20-50 samples)" << std::endl;
    std::cout << "   • Search space > 500: Use Genetic Algorithm" << std::endl;
    std::cout << std::endl;

    std::cout << "2. Defining Variations:" << std::endl;
    std::cout << "   • Start with 2-3 variables, each with 2-4 options" << std::endl;
    std::cout << "   • Keep variations distinct and meaningful" << std::endl;
    std::cout << "   • Test variations manually first to ensure diversity" << std::endl;
    std::cout << std::endl;

    std::cout << "3. Objective Functions:" << std::endl;
    std::cout << "   • Use real agent evaluation on test cases" << std::endl;
    std::cout << "   • Combine multiple metrics (accuracy, quality, latency)" << std::endl;
    std::cout << "   • Ensure objective is noisy but consistent" << std::endl;
    std::cout << std::endl;

    std::cout << "4. Hyperparameters:" << std::endl;
    std::cout << "   Random Search:" << std::endl;
    std::cout << "     • n_samples: 3-5x the number of variables" << std::endl;
    std::cout << "   Genetic Algorithm:" << std::endl;
    std::cout << "     • population_size: 10-20 for most problems" << std::endl;
    std::cout << "     • n_generations: 5-10 is usually sufficient" << std::endl;
    std::cout << "     • mutation_rate: 0.1-0.3 (higher for more exploration)" << std::endl;
    std::cout << std::endl;

    std::cout << "5. Evaluation Budget:" << std::endl;
    std::cout << "   • Each evaluation runs agent on test cases" << std::endl;
    std::cout << "   • Budget time accordingly:" << std::endl;
    std::cout << "     - 1s per eval × 50 evals = ~1 minute" << std::endl;
    std::cout << "     - 5s per eval × 100 evals = ~8 minutes" << std::endl;
    std::cout << std::endl;
}

int main() {
    std::cout << "=== Prompt Optimization Example ===" << std::endl;
    std::cout << std::endl;

    // Demonstrate each strategy
    demonstrate_grid_search();
    demonstrate_random_search();
    demonstrate_genetic_algorithm();

    // Compare strategies
    compare_strategies();

    // Best practices
    show_best_practices();

    std::cout << "=== Example Complete ===" << std::endl;

    return 0;
}
