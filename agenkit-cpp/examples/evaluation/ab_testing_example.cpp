/**
 * @file ab_testing_example.cpp
 * @brief Example demonstrating statistical A/B testing for agent comparison
 *
 * This example shows how to use the A/B testing framework to rigorously compare
 * two agent versions. It demonstrates:
 * - Creating test cases
 * - Setting up control and treatment agents
 * - Running statistical tests (t-test, Mann-Whitney, bootstrap)
 * - Interpreting results with p-values and effect sizes
 * - Calculating required sample sizes
 */

#include "agenkit/evaluation/ab_testing.hpp"
#include "agenkit/adapters/echo_agent.hpp"
#include <iostream>
#include <iomanip>
#include <random>

using namespace agenkit::evaluation;
using namespace agenkit::core;
using namespace agenkit::adapters;

/**
 * Mock agent for demonstration - simulates an agent with specific performance
 */
class SimulatedAgent : public Agent {
public:
    SimulatedAgent(const std::string& agent_name, double base_accuracy, double variance = 0.05)
        : name_(agent_name), base_accuracy_(base_accuracy), variance_(variance) {}

    std::string name() const override {
        return name_;
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() -> Result<Message, AgentError> {
            // Simulate agent processing with random variance
            std::random_device rd;
            std::mt19937 gen(rd());
            std::normal_distribution<> dist(base_accuracy_, variance_);
            double accuracy = std::max(0.0, std::min(1.0, dist(gen)));

            // Return message with accuracy in metadata
            Message response("assistant", "Simulated response to: " + msg.content_as_str());
            response.with_metadata("accuracy", accuracy);

            return Result<Message, AgentError>::ok(response);
        });
    }

private:
    std::string name_;
    double base_accuracy_;
    double variance_;
};

/**
 * Create test cases for evaluation
 */
std::vector<TestCase> create_test_cases(size_t count) {
    std::vector<TestCase> test_cases;
    test_cases.reserve(count);

    std::vector<std::string> inputs = {
        "What is 2+2?",
        "What is the capital of France?",
        "What color is the sky?",
        "How many days in a week?",
        "What is water made of?",
        "Who wrote Romeo and Juliet?",
        "What is the speed of light?",
        "How many planets in our solar system?",
        "What is the largest ocean?",
        "Who painted the Mona Lisa?"
    };

    for (size_t i = 0; i < count; ++i) {
        const std::string& input = inputs[i % inputs.size()];
        test_cases.push_back(TestCase(input, "expected_output"));
    }

    return test_cases;
}

int main() {
    std::cout << "=== A/B Testing Example ===" << std::endl;
    std::cout << std::endl;

    // Scenario: Comparing baseline agent vs improved agent
    std::cout << "Scenario: Testing new agent improvement" << std::endl;
    std::cout << "  Control (baseline):  75% accuracy" << std::endl;
    std::cout << "  Treatment (improved): 82% accuracy" << std::endl;
    std::cout << "  Question: Is the improvement statistically significant?" << std::endl;
    std::cout << std::endl;

    // Step 1: Calculate required sample size
    std::cout << "1. Planning: Calculate required sample size" << std::endl;
    std::cout << "   Parameters:" << std::endl;
    std::cout << "   - Baseline mean: 0.75" << std::endl;
    std::cout << "   - Minimum detectable effect: 5% (0.05)" << std::endl;
    std::cout << "   - Significance level (α): 0.05 (95% confidence)" << std::endl;
    std::cout << "   - Statistical power: 0.80 (80% chance to detect effect)" << std::endl;
    std::cout << "   - Expected std dev: 0.05" << std::endl;

    size_t required_n = ABTest::calculate_sample_size(
        0.75,   // baseline mean
        0.05,   // min detectable effect (5%)
        0.05,   // alpha
        0.80,   // power
        0.05    // std dev
    );

    std::cout << "   → Required sample size: " << required_n << " per variant" << std::endl;
    std::cout << std::endl;

    // Step 2: Create agents
    std::cout << "2. Creating agents..." << std::endl;
    std::shared_ptr<Agent> control_agent(new SimulatedAgent("control", 0.75, 0.05));
    std::shared_ptr<Agent> treatment_agent(new SimulatedAgent("treatment", 0.82, 0.05));
    std::cout << "   ✓ Control agent created (75% base accuracy)" << std::endl;
    std::cout << "   ✓ Treatment agent created (82% base accuracy)" << std::endl;
    std::cout << std::endl;

    // Step 3: Create test cases
    std::cout << "3. Preparing test cases..." << std::endl;
    size_t n_samples = 40;  // Using slightly more than minimum required
    auto test_cases = create_test_cases(n_samples);
    std::cout << "   ✓ Created " << test_cases.size() << " test cases" << std::endl;
    std::cout << std::endl;

    // Step 4: Run t-test
    std::cout << "4. Running Student's t-test..." << std::endl;
    ABTest t_test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);
    auto t_result = t_test.run(control_agent, treatment_agent, test_cases, "accuracy").get();

    std::cout << "   Results:" << std::endl;
    std::cout << "   Control mean:   " << std::fixed << std::setprecision(4)
              << t_result.control.mean << " (n=" << t_result.control.sample_size << ")" << std::endl;
    std::cout << "   Treatment mean: " << t_result.treatment.mean
              << " (n=" << t_result.treatment.sample_size << ")" << std::endl;
    std::cout << "   P-value:        " << std::setprecision(6) << t_result.p_value << std::endl;
    std::cout << "   Effect size:    " << std::setprecision(4) << t_result.effect_size
              << " (Cohen's d)" << std::endl;
    std::cout << "   95% CI:         [" << t_result.confidence_interval.first
              << ", " << t_result.confidence_interval.second << "]" << std::endl;
    std::cout << "   Significant:    " << (t_result.is_significant ? "YES" : "NO") << std::endl;
    std::cout << "   Winner:         " << t_result.winner << std::endl;
    std::cout << std::endl;

    // Step 5: Run Mann-Whitney test (non-parametric)
    std::cout << "5. Running Mann-Whitney U test (non-parametric)..." << std::endl;
    ABTest mw_test(StatisticalTestType::MANN_WHITNEY, SignificanceLevel::P_0_05);
    auto mw_result = mw_test.run(control_agent, treatment_agent, test_cases, "accuracy").get();

    std::cout << "   P-value:     " << std::setprecision(6) << mw_result.p_value << std::endl;
    std::cout << "   Significant: " << (mw_result.is_significant ? "YES" : "NO") << std::endl;
    std::cout << "   Winner:      " << mw_result.winner << std::endl;
    std::cout << std::endl;

    // Step 6: Run bootstrap test
    std::cout << "6. Running Bootstrap confidence interval..." << std::endl;
    ABTest bootstrap_test(StatisticalTestType::BOOTSTRAP, SignificanceLevel::P_0_05);
    auto bootstrap_result = bootstrap_test.run(control_agent, treatment_agent, test_cases, "accuracy").get();

    std::cout << "   95% CI:      [" << std::setprecision(4)
              << bootstrap_result.confidence_interval.first << ", "
              << bootstrap_result.confidence_interval.second << "]" << std::endl;
    std::cout << "   Significant: " << (bootstrap_result.is_significant ? "YES" : "NO") << std::endl;
    std::cout << "   Winner:      " << bootstrap_result.winner << std::endl;
    std::cout << std::endl;

    // Step 7: Print full summary
    std::cout << "7. Detailed Summary (t-test):" << std::endl;
    std::cout << "─────────────────────────────────────────────────" << std::endl;
    std::string summary = t_test.get_summary(t_result);
    std::cout << summary;
    std::cout << "─────────────────────────────────────────────────" << std::endl;
    std::cout << std::endl;

    // Step 8: Interpret effect size
    std::cout << "8. Effect Size Interpretation:" << std::endl;
    double abs_d = std::abs(t_result.effect_size);
    std::string interpretation;
    if (abs_d < 0.2) {
        interpretation = "negligible (< 0.2)";
    } else if (abs_d < 0.5) {
        interpretation = "small (0.2 - 0.5)";
    } else if (abs_d < 0.8) {
        interpretation = "medium (0.5 - 0.8)";
    } else {
        interpretation = "large (≥ 0.8)";
    }
    std::cout << "   Cohen's d = " << std::setprecision(4) << t_result.effect_size << std::endl;
    std::cout << "   Interpretation: " << interpretation << std::endl;
    std::cout << "   → This represents a " << (abs_d >= 0.5 ? "meaningful" : "modest")
              << " practical difference" << std::endl;
    std::cout << std::endl;

    // Step 9: Export results
    std::cout << "9. Exporting results..." << std::endl;
    auto json_result = t_result.to_json();
    std::cout << "   ✓ JSON serialization: " << json_result.dump().length() << " bytes" << std::endl;
    std::cout << "   ✓ Contains full variant statistics and test metadata" << std::endl;
    std::cout << std::endl;

    // Step 10: Recommendations
    std::cout << "10. Decision Guidance:" << std::endl;
    if (t_result.is_significant && t_result.winner == "treatment") {
        std::cout << "   ✓ RECOMMENDATION: Deploy treatment variant" << std::endl;
        std::cout << "   Rationale:" << std::endl;
        std::cout << "   - Statistically significant improvement (p=" << std::setprecision(6)
                  << t_result.p_value << " < 0.05)" << std::endl;
        std::cout << "   - " << std::setprecision(1)
                  << ((t_result.treatment.mean - t_result.control.mean) / t_result.control.mean * 100)
                  << "% relative improvement" << std::endl;
        std::cout << "   - Effect size indicates " << interpretation << " difference" << std::endl;
    } else if (!t_result.is_significant) {
        std::cout << "   ⚠ RECOMMENDATION: Keep control variant" << std::endl;
        std::cout << "   Rationale:" << std::endl;
        std::cout << "   - No statistically significant difference detected" << std::endl;
        std::cout << "   - Consider collecting more samples or larger improvements" << std::endl;
    } else {
        std::cout << "   ⚠ RECOMMENDATION: Treatment appears worse than control" << std::endl;
        std::cout << "   - Do not deploy treatment variant" << std::endl;
    }
    std::cout << std::endl;

    // Step 11: Best practices
    std::cout << "11. A/B Testing Best Practices:" << std::endl;
    std::cout << "   ✓ Calculate sample size before testing" << std::endl;
    std::cout << "   ✓ Use multiple statistical tests for robustness" << std::endl;
    std::cout << "   ✓ Check both statistical and practical significance" << std::endl;
    std::cout << "   ✓ Consider Mann-Whitney for non-normal distributions" << std::endl;
    std::cout << "   ✓ Bootstrap provides robust confidence intervals" << std::endl;
    std::cout << "   ✓ Document all test parameters and results" << std::endl;
    std::cout << std::endl;

    std::cout << "=== Example Complete ===" << std::endl;

    return 0;
}
