/**
 * @file ab_testing.cpp
 * @brief Implementation of statistical A/B testing framework
 */

#include "agenkit/evaluation/ab_testing.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <random>
#include <sstream>
#include <iomanip>

namespace agenkit {
namespace evaluation {

// Helper functions for statistical calculations

static double calculate_mean(const std::vector<double>& values) {
    if (values.empty()) {
        return 0.0;
    }
    double sum = std::accumulate(values.begin(), values.end(), 0.0);
    return sum / static_cast<double>(values.size());
}

static double calculate_variance(const std::vector<double>& values, double mean) {
    if (values.empty()) {
        return 0.0;
    }
    double variance = 0.0;
    for (double val : values) {
        double diff = val - mean;
        variance += diff * diff;
    }
    return variance / static_cast<double>(values.size());
}

static double calculate_std_dev(const std::vector<double>& values, double mean) {
    return std::sqrt(calculate_variance(values, mean));
}

// Normal distribution CDF approximation (for p-value calculation)
static double normal_cdf(double x) {
    // Approximation using error function
    return 0.5 * (1.0 + std::erf(x / std::sqrt(2.0)));
}

// Inverse normal CDF approximation (for z-scores)
static double inverse_normal_cdf(double p) {
    // Simplified approximation
    // For more accuracy, use a proper statistical library
    if (p <= 0.0) return -std::numeric_limits<double>::infinity();
    if (p >= 1.0) return std::numeric_limits<double>::infinity();
    if (p == 0.5) return 0.0;

    // Using rational approximation
    double t = std::sqrt(-2.0 * std::log(std::min(p, 1.0 - p)));
    double c0 = 2.515517, c1 = 0.802853, c2 = 0.010328;
    double d1 = 1.432788, d2 = 0.189269, d3 = 0.001308;

    double z = t - ((c0 + c1*t + c2*t*t) / (1.0 + d1*t + d2*t*t + d3*t*t*t));
    return (p < 0.5) ? -z : z;
}

// ABVariant implementation

void ABVariant::add_sample(double value) {
    samples.push_back(value);
}

void ABVariant::calculate_statistics() {
    sample_size = samples.size();
    if (sample_size == 0) {
        mean = 0.0;
        std_dev = 0.0;
        return;
    }

    mean = calculate_mean(samples);
    std_dev = calculate_std_dev(samples, mean);
}

nlohmann::json ABVariant::to_json() const {
    nlohmann::json j;
    j["name"] = name;
    j["samples"] = samples;
    j["mean"] = mean;
    j["std_dev"] = std_dev;
    j["sample_size"] = sample_size;
    return j;
}

ABVariant ABVariant::from_json(const nlohmann::json& j) {
    ABVariant variant(j.value("name", ""));
    if (j.contains("samples") && j["samples"].is_array()) {
        variant.samples = j["samples"].get<std::vector<double>>();
    }
    variant.mean = j.value("mean", 0.0);
    variant.std_dev = j.value("std_dev", 0.0);
    variant.sample_size = j.value("sample_size", 0);
    return variant;
}

// ABResult implementation

nlohmann::json ABResult::to_json() const {
    nlohmann::json j;
    j["control"] = control.to_json();
    j["treatment"] = treatment.to_json();
    j["p_value"] = p_value;
    j["effect_size"] = effect_size;
    j["confidence_interval"] = nlohmann::json::array({
        confidence_interval.first,
        confidence_interval.second
    });
    j["is_significant"] = is_significant;
    j["winner"] = winner;

    // Enum to string conversions
    switch (test_type) {
        case StatisticalTestType::T_TEST:
            j["test_type"] = "t_test";
            break;
        case StatisticalTestType::MANN_WHITNEY:
            j["test_type"] = "mann_whitney";
            break;
        case StatisticalTestType::CHI_SQUARE:
            j["test_type"] = "chi_square";
            break;
        case StatisticalTestType::BOOTSTRAP:
            j["test_type"] = "bootstrap";
            break;
    }

    j["alpha"] = static_cast<int>(alpha);

    return j;
}

ABResult ABResult::from_json(const nlohmann::json& j) {
    ABResult result;

    if (j.contains("control")) {
        result.control = ABVariant::from_json(j["control"]);
    }
    if (j.contains("treatment")) {
        result.treatment = ABVariant::from_json(j["treatment"]);
    }

    result.p_value = j.value("p_value", 1.0);
    result.effect_size = j.value("effect_size", 0.0);

    if (j.contains("confidence_interval") && j["confidence_interval"].is_array()) {
        auto ci = j["confidence_interval"];
        if (ci.size() >= 2) {
            result.confidence_interval.first = ci[0];
            result.confidence_interval.second = ci[1];
        }
    }

    result.is_significant = j.value("is_significant", false);
    result.winner = j.value("winner", "inconclusive");

    // String to enum conversion
    if (j.contains("test_type") && j["test_type"].is_string()) {
        std::string test_type_str = j["test_type"];
        if (test_type_str == "t_test") {
            result.test_type = StatisticalTestType::T_TEST;
        } else if (test_type_str == "mann_whitney") {
            result.test_type = StatisticalTestType::MANN_WHITNEY;
        } else if (test_type_str == "chi_square") {
            result.test_type = StatisticalTestType::CHI_SQUARE;
        } else if (test_type_str == "bootstrap") {
            result.test_type = StatisticalTestType::BOOTSTRAP;
        }
    }

    if (j.contains("alpha")) {
        result.alpha = static_cast<SignificanceLevel>(j["alpha"].get<int>());
    }

    return result;
}

// ABTest implementation

ABTest::ABTest(StatisticalTestType test_type, SignificanceLevel alpha)
    : test_type_(test_type)
    , alpha_(alpha)
{
}

std::future<ABResult> ABTest::run(
    std::shared_ptr<core::Agent> control_agent,
    std::shared_ptr<core::Agent> treatment_agent,
    const std::vector<TestCase>& test_cases,
    const std::string& metric_name
) {
    return std::async(std::launch::async, [this, control_agent, treatment_agent, test_cases, metric_name]() {
        ABResult result;

        // Collect measurements for both variants
        auto control_measurements = collect_measurements(control_agent, test_cases, metric_name);
        auto treatment_measurements = collect_measurements(treatment_agent, test_cases, metric_name);

        // Create variants
        result.control = ABVariant("control");
        for (double val : control_measurements) {
            result.control.add_sample(val);
        }
        result.control.calculate_statistics();

        result.treatment = ABVariant("treatment");
        for (double val : treatment_measurements) {
            result.treatment.add_sample(val);
        }
        result.treatment.calculate_statistics();

        // Run statistical test
        switch (test_type_) {
            case StatisticalTestType::T_TEST:
                result.p_value = t_test(control_measurements, treatment_measurements);
                break;
            case StatisticalTestType::MANN_WHITNEY:
                result.p_value = mann_whitney(control_measurements, treatment_measurements);
                break;
            case StatisticalTestType::CHI_SQUARE:
                result.p_value = chi_square(control_measurements, treatment_measurements);
                break;
            case StatisticalTestType::BOOTSTRAP:
                // Bootstrap returns confidence interval directly
                result.confidence_interval = bootstrap_confidence_interval(
                    control_measurements, treatment_measurements
                );
                // P-value approximation: if 0 is in CI, not significant
                result.p_value = (result.confidence_interval.first <= 0.0 &&
                                  result.confidence_interval.second >= 0.0) ? 0.5 : 0.01;
                break;
        }

        // Calculate effect size
        result.effect_size = cohens_d(result.control, result.treatment);

        // Calculate confidence interval if not bootstrap
        if (test_type_ != StatisticalTestType::BOOTSTRAP) {
            result.confidence_interval = bootstrap_confidence_interval(
                control_measurements, treatment_measurements
            );
        }

        // Determine significance and winner
        double alpha_value = get_alpha_value();
        result.is_significant = (result.p_value < alpha_value);
        result.test_type = test_type_;
        result.alpha = alpha_;

        if (result.is_significant) {
            result.winner = (result.treatment.mean > result.control.mean) ? "treatment" : "control";
        } else {
            result.winner = "inconclusive";
        }

        return result;
    });
}

std::string ABTest::get_summary(const ABResult& result) const {
    std::ostringstream ss;

    // Header
    ss << "A/B Test Results (";
    switch (result.test_type) {
        case StatisticalTestType::T_TEST:
            ss << "Student's t-test";
            break;
        case StatisticalTestType::MANN_WHITNEY:
            ss << "Mann-Whitney U test";
            break;
        case StatisticalTestType::CHI_SQUARE:
            ss << "Chi-square test";
            break;
        case StatisticalTestType::BOOTSTRAP:
            ss << "Bootstrap";
            break;
    }
    ss << ", α=" << get_alpha_value() << ")\n";
    ss << "==============================================\n";

    // Variant statistics
    ss << std::fixed << std::setprecision(4);
    ss << "Control:   mean=" << result.control.mean
       << ", std=" << result.control.std_dev
       << ", n=" << result.control.sample_size << "\n";
    ss << "Treatment: mean=" << result.treatment.mean
       << ", std=" << result.treatment.std_dev
       << ", n=" << result.treatment.sample_size << "\n";

    // Statistical results
    ss << "P-value:   " << std::setprecision(6) << result.p_value << "\n";
    ss << "Effect size: " << std::setprecision(4) << result.effect_size
       << " (" << interpret_effect_size(result.effect_size) << ")\n";
    ss << "95% CI: [" << result.confidence_interval.first
       << ", " << result.confidence_interval.second << "]\n";

    // Conclusion
    ss << "\nConclusion: ";
    if (result.is_significant) {
        if (result.winner == "treatment") {
            ss << "Treatment significantly outperforms control";
        } else {
            ss << "Control significantly outperforms treatment";
        }
        ss << " (p=" << std::setprecision(6) << result.p_value
           << " < " << get_alpha_value() << ")\n";
    } else {
        ss << "No significant difference detected (p=" << std::setprecision(6)
           << result.p_value << " >= " << get_alpha_value() << ")\n";
    }
    ss << "Winner: " << result.winner << "\n";

    return ss.str();
}

size_t ABTest::calculate_sample_size(
    double baseline_mean,
    double min_detectable_effect,
    double alpha,
    double power,
    double std_dev
) {
    // Using simplified formula for two-sample t-test
    // n = 2 * (z_alpha/2 + z_beta)^2 * (σ^2 / δ^2)
    // where δ = effect size in same units as measurement

    double z_alpha = inverse_normal_cdf(1.0 - alpha / 2.0);
    double z_beta = inverse_normal_cdf(power);

    double effect_absolute = baseline_mean * min_detectable_effect;
    double variance = std_dev * std_dev;

    double n = 2.0 * std::pow(z_alpha + z_beta, 2.0) * variance / std::pow(effect_absolute, 2.0);

    return static_cast<size_t>(std::ceil(n));
}

double ABTest::t_test(const std::vector<double>& sample1, const std::vector<double>& sample2) {
    if (sample1.empty() || sample2.empty()) {
        return 1.0;
    }

    // Welch's t-test (doesn't assume equal variances)
    double mean1 = calculate_mean(sample1);
    double mean2 = calculate_mean(sample2);
    double var1 = calculate_variance(sample1, mean1);
    double var2 = calculate_variance(sample2, mean2);

    size_t n1 = sample1.size();
    size_t n2 = sample2.size();

    // Calculate t-statistic
    double se = std::sqrt(var1 / n1 + var2 / n2);
    if (se < 1e-10) {
        return 1.0;  // No difference
    }

    double t = (mean1 - mean2) / se;

    // Degrees of freedom (Welch-Satterthwaite equation)
    // Note: Calculated but not used since we use normal approximation for large samples
    double df_numerator = std::pow(var1 / n1 + var2 / n2, 2.0);
    double df_denominator = std::pow(var1 / n1, 2.0) / (n1 - 1) +
                            std::pow(var2 / n2, 2.0) / (n2 - 1);
    double df = df_numerator / df_denominator;
    (void)df;  // Unused - for future t-distribution implementation

    // Approximate p-value using normal distribution
    // For large df, t-distribution ≈ normal distribution
    double p_value = 2.0 * (1.0 - normal_cdf(std::abs(t)));

    return p_value;
}

double ABTest::mann_whitney(const std::vector<double>& sample1, const std::vector<double>& sample2) {
    if (sample1.empty() || sample2.empty()) {
        return 1.0;
    }

    size_t n1 = sample1.size();
    size_t n2 = sample2.size();

    // Calculate U statistic
    double u1 = 0.0;
    for (double val1 : sample1) {
        for (double val2 : sample2) {
            if (val1 > val2) {
                u1 += 1.0;
            } else if (val1 == val2) {
                u1 += 0.5;
            }
        }
    }

    double u2 = static_cast<double>(n1 * n2) - u1;
    double u = std::min(u1, u2);

    // Normal approximation for large samples
    double mean_u = static_cast<double>(n1 * n2) / 2.0;
    double std_u = std::sqrt(static_cast<double>(n1 * n2 * (n1 + n2 + 1)) / 12.0);

    if (std_u < 1e-10) {
        return 1.0;
    }

    double z = (u - mean_u) / std_u;
    double p_value = 2.0 * (1.0 - normal_cdf(std::abs(z)));

    return p_value;
}

double ABTest::chi_square(const std::vector<double>& sample1, const std::vector<double>& sample2) {
    // Simplified chi-square test for binary outcomes
    // Assumes samples are 0/1 values (success/failure)

    if (sample1.empty() || sample2.empty()) {
        return 1.0;
    }

    // Count successes
    size_t success1 = 0, success2 = 0;
    for (double val : sample1) {
        if (val > 0.5) success1++;
    }
    for (double val : sample2) {
        if (val > 0.5) success2++;
    }

    size_t n1 = sample1.size();
    size_t n2 = sample2.size();
    size_t failure1 = n1 - success1;
    size_t failure2 = n2 - success2;

    // 2x2 contingency table chi-square test
    double total = static_cast<double>(n1 + n2);
    double expected11 = static_cast<double>((success1 + success2) * n1) / total;
    double expected12 = static_cast<double>((failure1 + failure2) * n1) / total;
    double expected21 = static_cast<double>((success1 + success2) * n2) / total;
    double expected22 = static_cast<double>((failure1 + failure2) * n2) / total;

    double chi2 = 0.0;
    if (expected11 > 0) chi2 += std::pow(success1 - expected11, 2.0) / expected11;
    if (expected12 > 0) chi2 += std::pow(failure1 - expected12, 2.0) / expected12;
    if (expected21 > 0) chi2 += std::pow(success2 - expected21, 2.0) / expected21;
    if (expected22 > 0) chi2 += std::pow(failure2 - expected22, 2.0) / expected22;

    // P-value approximation (df=1)
    // Using chi-square CDF approximation
    double p_value = 1.0 - normal_cdf(std::sqrt(chi2));

    return p_value;
}

double ABTest::cohens_d(const ABVariant& control, const ABVariant& treatment) {
    // Cohen's d = (mean1 - mean2) / pooled_std_dev
    double mean_diff = treatment.mean - control.mean;

    // Pooled standard deviation
    double n1 = static_cast<double>(control.sample_size);
    double n2 = static_cast<double>(treatment.sample_size);

    if (n1 + n2 <= 2) {
        return 0.0;
    }

    double pooled_var = ((n1 - 1) * control.std_dev * control.std_dev +
                         (n2 - 1) * treatment.std_dev * treatment.std_dev) /
                        (n1 + n2 - 2);
    double pooled_std = std::sqrt(pooled_var);

    if (pooled_std < 1e-10) {
        return 0.0;
    }

    return mean_diff / pooled_std;
}

std::pair<double, double> ABTest::bootstrap_confidence_interval(
    const std::vector<double>& sample1,
    const std::vector<double>& sample2,
    double confidence_level,
    size_t n_resamples
) {
    if (sample1.empty() || sample2.empty()) {
        return {0.0, 0.0};
    }

    std::random_device rd;
    std::mt19937 rng(rd());
    std::uniform_int_distribution<size_t> dist1(0, sample1.size() - 1);
    std::uniform_int_distribution<size_t> dist2(0, sample2.size() - 1);

    std::vector<double> differences;
    differences.reserve(n_resamples);

    // Bootstrap resampling
    for (size_t i = 0; i < n_resamples; ++i) {
        // Resample with replacement
        std::vector<double> resample1, resample2;
        resample1.reserve(sample1.size());
        resample2.reserve(sample2.size());

        for (size_t j = 0; j < sample1.size(); ++j) {
            resample1.push_back(sample1[dist1(rng)]);
        }
        for (size_t j = 0; j < sample2.size(); ++j) {
            resample2.push_back(sample2[dist2(rng)]);
        }

        // Calculate difference in means
        double mean1 = calculate_mean(resample1);
        double mean2 = calculate_mean(resample2);
        differences.push_back(mean2 - mean1);
    }

    // Sort differences
    std::sort(differences.begin(), differences.end());

    // Calculate percentiles
    double alpha = 1.0 - confidence_level;
    size_t lower_idx = static_cast<size_t>(alpha / 2.0 * n_resamples);
    size_t upper_idx = static_cast<size_t>((1.0 - alpha / 2.0) * n_resamples);

    lower_idx = std::min(lower_idx, differences.size() - 1);
    upper_idx = std::min(upper_idx, differences.size() - 1);

    return {differences[lower_idx], differences[upper_idx]};
}

std::vector<double> ABTest::collect_measurements(
    std::shared_ptr<core::Agent> agent,
    const std::vector<TestCase>& test_cases,
    const std::string& metric_name
) {
    std::vector<double> measurements;
    measurements.reserve(test_cases.size());

    for (const auto& test_case : test_cases) {
        // Create message
        core::Message input_msg("user", test_case.input);

        // Process through agent
        auto response_future = agent->process(input_msg);

        try {
            auto response_result = response_future.get();

            if (response_result.is_ok()) {
                auto response = response_result.unwrap();

                // Extract metric from response metadata
                const auto& metadata = response.metadata();
                if (metadata.contains(metric_name)) {
                    const auto& metric_value = metadata[metric_name];
                    if (metric_value.is_number()) {
                        measurements.push_back(metric_value.get<double>());
                    } else if (metric_value.is_string()) {
                        try {
                            measurements.push_back(std::stod(metric_value.get<std::string>()));
                        } catch (...) {
                            // Failed to parse - use 0.0
                            measurements.push_back(0.0);
                        }
                    } else if (metric_value.is_boolean()) {
                        measurements.push_back(metric_value.get<bool>() ? 1.0 : 0.0);
                    } else {
                        measurements.push_back(0.0);
                    }
                } else {
                    // Metric not found - use 0.0
                    measurements.push_back(0.0);
                }
            } else {
                // Error processing - use 0.0
                measurements.push_back(0.0);
            }
        } catch (...) {
            // Exception - use 0.0
            measurements.push_back(0.0);
        }
    }

    return measurements;
}

double ABTest::get_alpha_value() const {
    switch (alpha_) {
        case SignificanceLevel::P_0_001:
            return 0.001;
        case SignificanceLevel::P_0_01:
            return 0.01;
        case SignificanceLevel::P_0_05:
            return 0.05;
        case SignificanceLevel::P_0_10:
            return 0.10;
        default:
            return 0.05;
    }
}

std::string ABTest::interpret_effect_size(double d) const {
    double abs_d = std::abs(d);
    if (abs_d < 0.2) {
        return "negligible effect";
    } else if (abs_d < 0.5) {
        return "small effect";
    } else if (abs_d < 0.8) {
        return "medium effect";
    } else {
        return "large effect";
    }
}

} // namespace evaluation
} // namespace agenkit
