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
#include <cmath>
#include <iostream>
#include <iomanip>
#include <mutex>
#include <random>
#include <string>
#include <utility>
#include <vector>

using namespace agenkit::evaluation;
using namespace agenkit::core;
using namespace agenkit::adapters;

/**
 * Mock agent for demonstration - answers correctly a set proportion of the time
 *
 * The agent returns a real answer and is scored against TestCase::expected by the
 * metric named in ABTest::run. It does *not* report its own score: this example used to
 * do `response.with_metadata("accuracy", accuracy)`, which was the only reason the old
 * ABTest produced non-zero numbers (it read the score out of response metadata and never
 * looked at `expected`). Teaching that pattern taught users to grade their own agents —
 * see #829.
 */
class SimulatedAgent : public Agent {
public:
    SimulatedAgent(const std::string& agent_name, double base_accuracy, unsigned seed)
        : name_(agent_name), base_accuracy_(base_accuracy), gen_(seed) {}

    std::string name() const override {
        return name_;
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        // Draw before going async - the generator is shared mutable state.
        bool correct;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            correct = dist_(gen_) < base_accuracy_;
        }

        return std::async(std::launch::async,
                          [correct, msg = std::move(message)]() -> Result<Message, AgentError> {
            const std::string& answer = correct ? correct_answer(msg.content_as_str())
                                               : "I am not sure.";
            return Result<Message, AgentError>::ok(
                Message("assistant", "Thinking about it... " + answer));
        });
    }

private:
    // Answers keyed by question, so a correct response really does contain the expected
    // fragment. `expected` is a fragment, not the whole output (docs/DEFAULTS.md), which
    // is why answering in prose still scores 1.0.
    static const std::string& correct_answer(const std::string& question);

    std::string name_;
    double base_accuracy_;
    std::mt19937 gen_;
    std::uniform_real_distribution<> dist_{0.0, 1.0};
    std::mutex mutex_;
};

namespace {

// Question -> expected fragment. Shared by the agent (to answer) and the test cases (to
// score), so there is one source of truth for what a correct answer contains.
const std::vector<std::pair<std::string, std::string>>& qa_pairs() {
    static const std::vector<std::pair<std::string, std::string>> pairs = {
        {"What is 2+2?", "4"},
        {"What is the capital of France?", "Paris"},
        {"What color is the sky?", "blue"},
        {"How many days in a week?", "7"},
        {"What is water made of?", "hydrogen and oxygen"},
        {"Who wrote Romeo and Juliet?", "Shakespeare"},
        {"What is the speed of light?", "299,792,458"},
        {"How many planets in our solar system?", "8"},
        {"What is the largest ocean?", "Pacific"},
        {"Who painted the Mona Lisa?", "da Vinci"}
    };
    return pairs;
}

}  // namespace

const std::string& SimulatedAgent::correct_answer(const std::string& question) {
    for (const auto& [q, a] : qa_pairs()) {
        if (q == question) {
            return a;
        }
    }
    static const std::string unknown = "no answer on file";
    return unknown;
}

/**
 * Create test cases for evaluation
 */
std::vector<TestCase> create_test_cases(size_t count) {
    std::vector<TestCase> test_cases;
    test_cases.reserve(count);

    for (size_t i = 0; i < count; ++i) {
        const auto& [question, expected] = qa_pairs()[i % qa_pairs().size()];
        test_cases.push_back(TestCase(question, expected));
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
    //
    // The std dev must be the std dev *of the metric being measured*. Accuracy scores each
    // case 0.0 or 1.0, so it is Bernoulli: at p≈0.78 its std dev is sqrt(p(1-p)) ≈ 0.42, not
    // the 0.05 this example used to pass. Understating it by 8x understated the required
    // sample size by 70x, and the example then declared 28 cases sufficient before running
    // 40 and reporting "inconclusive" — its own two steps contradicting each other.
    const double baseline_mean = 0.75;
    const double treatment_mean = 0.82;
    const double relative_effect = (treatment_mean - baseline_mean) / baseline_mean;
    const double accuracy_std_dev = std::sqrt(0.78 * (1.0 - 0.78));

    std::cout << "1. Planning: Calculate required sample size" << std::endl;
    std::cout << "   Parameters:" << std::endl;
    std::cout << "   - Baseline mean: " << std::fixed << std::setprecision(2)
              << baseline_mean << std::endl;
    std::cout << "   - Minimum detectable effect: " << std::setprecision(1)
              << (relative_effect * 100) << "% relative ("
              << std::setprecision(2) << (treatment_mean - baseline_mean)
              << " absolute)" << std::endl;
    std::cout << "   - Significance level (α): 0.05 (95% confidence)" << std::endl;
    std::cout << "   - Statistical power: 0.80 (80% chance to detect effect)" << std::endl;
    std::cout << "   - Expected std dev: " << std::setprecision(4) << accuracy_std_dev
              << " (Bernoulli, since accuracy scores 0 or 1)" << std::endl;

    size_t required_n = ABTest::calculate_sample_size(
        baseline_mean,
        relative_effect,
        0.05,   // alpha
        0.80,   // power
        accuracy_std_dev
    );

    std::cout << "   → Required sample size: " << required_n << " per variant" << std::endl;
    std::cout << std::endl;

    // Step 2: Create agents
    std::cout << "2. Creating agents..." << std::endl;
    // A fresh pair per test, from fixed seeds. Steps 4-6 are three tests of the *same*
    // hypothesis, so they must analyse the same samples — an agent carries an advancing
    // generator, so reusing one pair would hand each test different data and the tests
    // would appear to disagree with each other.
    auto control_agent = [baseline_mean] {
        return std::shared_ptr<Agent>(new SimulatedAgent("control", baseline_mean, 1));
    };
    auto treatment_agent = [treatment_mean] {
        return std::shared_ptr<Agent>(new SimulatedAgent("treatment", treatment_mean, 7920));
    };
    std::cout << "   ✓ Control agent created (75% base accuracy)" << std::endl;
    std::cout << "   ✓ Treatment agent created (82% base accuracy)" << std::endl;
    std::cout << std::endl;

    // Step 3: Create test cases
    std::cout << "3. Preparing test cases..." << std::endl;
    // Run exactly what step 1 said was needed. Running fewer is how an experiment reports
    // "no significant difference" for an effect that is really there.
    auto test_cases = create_test_cases(required_n);
    std::cout << "   ✓ Created " << test_cases.size() << " test cases" << std::endl;
    std::cout << std::endl;

    // Step 4: Run t-test
    std::cout << "4. Running Student's t-test..." << std::endl;
    ABTest t_test(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);
    auto t_result = t_test.run(control_agent(), treatment_agent(), test_cases, "accuracy").get();

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
    auto mw_result = mw_test.run(control_agent(), treatment_agent(), test_cases, "accuracy").get();

    std::cout << "   P-value:     " << std::setprecision(6) << mw_result.p_value << std::endl;
    std::cout << "   Significant: " << (mw_result.is_significant ? "YES" : "NO") << std::endl;
    std::cout << "   Winner:      " << mw_result.winner << std::endl;
    std::cout << "   Note: rank-based tests lose power on a metric with only two distinct" << std::endl;
    std::cout << "         values, so expect a larger p-value than the t-test here." << std::endl;
    std::cout << std::endl;

    // Step 6: Run bootstrap test
    std::cout << "6. Running Bootstrap confidence interval..." << std::endl;
    ABTest bootstrap_test(StatisticalTestType::BOOTSTRAP, SignificanceLevel::P_0_05);
    auto bootstrap_result = bootstrap_test.run(
        control_agent(), treatment_agent(), test_cases, "accuracy").get();

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
    std::cout << "   Statistical and practical significance are different questions: a small" << std::endl;
    std::cout << "   effect can be significant at a large enough n. Whether 7 points of" << std::endl;
    std::cout << "   accuracy is worth deploying is a product decision, not a p-value." << std::endl;
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
