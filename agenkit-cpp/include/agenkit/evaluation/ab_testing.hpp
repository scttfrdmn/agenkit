/**
 * @file ab_testing.hpp
 * @brief Statistical A/B testing framework for agent comparison
 *
 * This module provides rigorous statistical testing for comparing agent versions,
 * including:
 * - Parametric tests (t-test) for normal distributions
 * - Non-parametric tests (Mann-Whitney) for skewed distributions
 * - Bootstrap confidence intervals for robust estimation
 * - Effect size calculation (Cohen's d) for practical significance
 * - Sample size calculation for test planning
 *
 * Key use cases:
 * - Compare baseline vs improved agent versions
 * - Validate performance improvements with statistical confidence
 * - Detect regressions before deployment
 * - Plan experiments with appropriate sample sizes
 *
 * @example
 * @code
 * // Create A/B test with t-test and 95% confidence
 * auto ab_test = ABTest(StatisticalTestType::T_TEST, SignificanceLevel::P_0_05);
 *
 * // Run test on two agent variants
 * auto result = ab_test.run(control_agent, treatment_agent, test_cases, "accuracy").get();
 *
 * if (result.is_significant) {
 *     std::cout << "Winner: " << result.winner << std::endl;
 *     std::cout << "Effect size: " << result.effect_size << " (Cohen's d)" << std::endl;
 *     std::cout << "P-value: " << result.p_value << std::endl;
 * } else {
 *     std::cout << "No significant difference detected" << std::endl;
 * }
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_AB_TESTING_HPP
#define AGENKIT_EVALUATION_AB_TESTING_HPP

#include "agenkit/core/agent.hpp"
#include "benchmarks.hpp"
#include "quality_metrics.hpp"
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <future>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Statistical test types for A/B testing
 *
 * Different tests make different assumptions about the data:
 * - T_TEST: Assumes normal distribution, most powerful when assumption holds
 * - MANN_WHITNEY: Non-parametric, robust to outliers and skewed distributions
 * - CHI_SQUARE: For categorical outcomes (success/failure rates)
 * - BOOTSTRAP: Resampling-based, makes minimal assumptions
 */
enum class StatisticalTestType {
    T_TEST,         ///< Student's t-test (parametric)
    MANN_WHITNEY,   ///< Mann-Whitney U test (non-parametric)
    CHI_SQUARE,     ///< Chi-square test (categorical)
    BOOTSTRAP       ///< Bootstrap resampling
};

/**
 * @brief Significance levels (alpha) for hypothesis testing
 *
 * Common significance levels with their confidence levels:
 * - P_0_001 = 99.9% confidence (very strict)
 * - P_0_01 = 99% confidence (strict)
 * - P_0_05 = 95% confidence (standard)
 * - P_0_10 = 90% confidence (exploratory)
 */
enum class SignificanceLevel {
    P_0_001 = 1,   ///< 99.9% confidence
    P_0_01 = 2,    ///< 99% confidence
    P_0_05 = 5,    ///< 95% confidence (most common)
    P_0_10 = 10    ///< 90% confidence
};

// TestCase for A/B testing comes from benchmarks.hpp — there is exactly one
// agenkit::evaluation::TestCase.
//
// This header used to define a second struct of the same name in the same namespace:
// 72 bytes with a plain std::string `expected`, against benchmarks.hpp's 112 bytes with
// a std::variant. Both had an inline two-string constructor, so both emitted the same
// mangled symbol for the implicit copy constructor
// (_ZN7agenkit10evaluation8TestCaseC2ERKS1_), both weak, both in the same library
// target. The linker coalesced them without a diagnostic, so any program including both
// headers ran one type's copy constructor over the other type's storage and corrupted
// the heap. No translation unit in this repo included both, which is why the suite
// stayed green and the bug only fired in user code (#831).

/**
 * @brief Statistics for a single A/B test variant
 *
 * Tracks all measurements and computed statistics for one variant
 * (control or treatment).
 */
struct ABVariant {
    std::string name;                ///< Variant name ("control" or "treatment")
    std::vector<double> samples;     ///< All measurements
    double mean;                     ///< Sample mean
    double std_dev;                  ///< Sample standard deviation
    size_t sample_size;              ///< Number of samples

    /**
     * @brief Create a variant
     * @param variant_name Name of this variant
     */
    explicit ABVariant(const std::string& variant_name = "")
        : name(variant_name)
        , mean(0.0)
        , std_dev(0.0)
        , sample_size(0)
    {}

    /**
     * @brief Add a measurement to this variant
     * @param value Measurement value
     */
    void add_sample(double value);

    /**
     * @brief Calculate statistics from samples
     *
     * Computes mean, standard deviation, and sample size.
     * Must be called after all samples are added.
     */
    void calculate_statistics();

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return ABVariant instance
     */
    static ABVariant from_json(const nlohmann::json& j);
};

/**
 * @brief Results from A/B test
 *
 * Contains complete results including statistics, p-value, effect size,
 * confidence intervals, and interpretation.
 *
 * @example
 * @code
 * auto result = ab_test.run(control, treatment, test_cases, "accuracy").get();
 *
 * std::cout << "Control mean: " << result.control.mean << std::endl;
 * std::cout << "Treatment mean: " << result.treatment.mean << std::endl;
 * std::cout << "P-value: " << result.p_value << std::endl;
 * std::cout << "Effect size: " << result.effect_size << std::endl;
 * std::cout << "95% CI: [" << result.confidence_interval.first
 *           << ", " << result.confidence_interval.second << "]" << std::endl;
 *
 * if (result.is_significant) {
 *     std::cout << "Winner: " << result.winner << std::endl;
 * }
 * @endcode
 */
struct ABResult {
    ABVariant control;                              ///< Control variant statistics
    ABVariant treatment;                            ///< Treatment variant statistics
    double p_value;                                 ///< P-value from statistical test
    double effect_size;                             ///< Cohen's d effect size
    std::pair<double, double> confidence_interval;  ///< 95% confidence interval for difference
    bool is_significant;                            ///< Whether difference is statistically significant
    std::string winner;                             ///< "control", "treatment", or "inconclusive"
    StatisticalTestType test_type;                  ///< Test used
    SignificanceLevel alpha;                        ///< Significance level used

    /**
     * @brief Create an AB result
     */
    ABResult()
        : p_value(1.0)
        , effect_size(0.0)
        , confidence_interval(0.0, 0.0)
        , is_significant(false)
        , winner("inconclusive")
        , test_type(StatisticalTestType::T_TEST)
        , alpha(SignificanceLevel::P_0_05)
    {}

    /**
     * @brief Serialize to JSON
     * @return JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Deserialize from JSON
     * @param j JSON object
     * @return ABResult instance
     */
    static ABResult from_json(const nlohmann::json& j);
};

/**
 * @brief A/B testing framework for comparing agents
 *
 * Provides statistical hypothesis testing to determine if differences between
 * agent versions are significant or due to chance. Supports multiple test types
 * and handles both parametric and non-parametric scenarios.
 *
 * @details
 * The ABTest class automates the entire A/B testing workflow:
 * 1. Evaluate both agents on test cases
 * 2. Collect measurements for specified metric
 * 3. Run appropriate statistical test
 * 4. Calculate effect size and confidence intervals
 * 5. Determine winner and statistical significance
 *
 * Use get_summary() to get a human-readable interpretation of results.
 *
 * @example
 * @code
 * // Create test with Mann-Whitney (non-parametric) at 95% confidence
 * auto ab_test = ABTest(StatisticalTestType::MANN_WHITNEY, SignificanceLevel::P_0_05);
 *
 * // Define test cases
 * std::vector<TestCase> test_cases = {
 *     {"What is 2+2?", "4"},
 *     {"What is the capital of France?", "Paris"},
 *     // ... more test cases
 * };
 *
 * // Run test comparing control vs treatment agents
 * auto result = ab_test.run(control_agent, treatment_agent, test_cases, "accuracy").get();
 *
 * // Print summary
 * std::cout << ab_test.get_summary(result) << std::endl;
 *
 * // Example output:
 * // A/B Test Results (Mann-Whitney U test, α=0.05)
 * // ==============================================
 * // Control:   mean=0.75, std=0.12, n=100
 * // Treatment: mean=0.82, std=0.10, n=100
 * // P-value:   0.003
 * // Effect size: 0.65 (medium effect)
 * // Conclusion: Treatment significantly outperforms control (p=0.003 < 0.05)
 * // Winner: treatment
 * @endcode
 */
class ABTest {
public:
    /**
     * @brief Create an A/B test
     * @param test_type Statistical test to use
     * @param alpha Significance level (default: 0.05 = 95% confidence)
     */
    explicit ABTest(
        StatisticalTestType test_type = StatisticalTestType::T_TEST,
        SignificanceLevel alpha = SignificanceLevel::P_0_05
    );

    /**
     * @brief Run A/B test comparing two agents
     *
     * @param control_agent Baseline agent (control group)
     * @param treatment_agent Modified agent (treatment group)
     * @param test_cases Test cases to evaluate on
     * @param metric_name Metric to compare (must be available from agent evaluation)
     * @return Future with ABResult
     *
     * The test:
     * 1. Evaluates both agents on all test cases
     * 2. Collects metric measurements
     * 3. Runs statistical test
     * 4. Calculates effect size
     * 5. Determines winner
     *
     * @example
     * @code
     * auto result = ab_test.run(
     *     control_agent,
     *     treatment_agent,
     *     test_cases,
     *     "accuracy"
     * ).get();
     * @endcode
     */
    std::future<ABResult> run(
        std::shared_ptr<core::Agent> control_agent,
        std::shared_ptr<core::Agent> treatment_agent,
        const std::vector<TestCase>& test_cases,
        const std::string& metric_name
    );

    /**
     * @brief Get human-readable summary of A/B test results
     *
     * @param result Test results to summarize
     * @return Formatted summary string
     *
     * The summary includes:
     * - Test type and significance level
     * - Descriptive statistics for both variants
     * - P-value and interpretation
     * - Effect size with interpretation (small/medium/large)
     * - Confidence interval
     * - Winner determination
     */
    std::string get_summary(const ABResult& result) const;

    /**
     * @brief Calculate required sample size for test
     *
     * @param baseline_mean Expected baseline metric value
     * @param min_detectable_effect Minimum effect to detect (as proportion)
     * @param alpha Significance level (Type I error rate)
     * @param power Statistical power (1 - Type II error rate, typically 0.8)
     * @param std_dev Expected standard deviation
     * @return Required sample size per variant
     *
     * Use this to plan experiments before running them.
     *
     * @example
     * @code
     * // Want to detect 10% improvement with 95% confidence, 80% power
     * size_t n = ABTest::calculate_sample_size(
     *     0.75,   // baseline mean
     *     0.10,   // detect 10% improvement
     *     0.05,   // 95% confidence
     *     0.80,   // 80% power
     *     0.12    // expected std dev
     * );
     * std::cout << "Need " << n << " samples per variant" << std::endl;
     * @endcode
     */
    static size_t calculate_sample_size(
        double baseline_mean,
        double min_detectable_effect,
        double alpha,
        double power,
        double std_dev
    );

private:
    /**
     * @brief Perform Student's t-test
     * @param sample1 First sample
     * @param sample2 Second sample
     * @return P-value
     */
    double t_test(const std::vector<double>& sample1, const std::vector<double>& sample2);

    /**
     * @brief Perform Mann-Whitney U test
     * @param sample1 First sample
     * @param sample2 Second sample
     * @return P-value
     */
    double mann_whitney(const std::vector<double>& sample1, const std::vector<double>& sample2);

    /**
     * @brief Perform chi-square test
     * @param sample1 First sample
     * @param sample2 Second sample
     * @return P-value
     */
    double chi_square(const std::vector<double>& sample1, const std::vector<double>& sample2);

    /**
     * @brief Calculate Cohen's d effect size
     * @param control Control variant statistics
     * @param treatment Treatment variant statistics
     * @return Cohen's d (standardized mean difference)
     *
     * Interpretation:
     * - |d| < 0.2: negligible
     * - 0.2 ≤ |d| < 0.5: small
     * - 0.5 ≤ |d| < 0.8: medium
     * - |d| ≥ 0.8: large
     */
    double cohens_d(const ABVariant& control, const ABVariant& treatment);

    /**
     * @brief Calculate bootstrap confidence interval for difference
     * @param sample1 First sample
     * @param sample2 Second sample
     * @param confidence_level Confidence level (default: 0.95)
     * @param n_resamples Number of bootstrap resamples (default: 10000)
     * @return Pair (lower bound, upper bound)
     */
    std::pair<double, double> bootstrap_confidence_interval(
        const std::vector<double>& sample1,
        const std::vector<double>& sample2,
        double confidence_level = 0.95,
        size_t n_resamples = 10000
    );

    /**
     * @brief Collect metric measurements from agent evaluation
     * @param agent Agent to evaluate
     * @param test_cases Test cases
     * @param metric_name Metric to extract
     * @return Vector of measurements
     */
    std::vector<double> collect_measurements(
        std::shared_ptr<core::Agent> agent,
        const std::vector<TestCase>& test_cases,
        const std::string& metric_name
    );

    /**
     * @brief Get alpha value from SignificanceLevel enum
     * @return Alpha as double (0.001, 0.01, 0.05, or 0.10)
     */
    double get_alpha_value() const;

    /**
     * @brief Interpret effect size
     * @param d Cohen's d
     * @return Human-readable interpretation
     */
    std::string interpret_effect_size(double d) const;

    StatisticalTestType test_type_;
    SignificanceLevel alpha_;
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_AB_TESTING_HPP
