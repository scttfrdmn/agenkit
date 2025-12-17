/**
 * @file benchmarks_example.cpp
 * @brief Example demonstrating the benchmark framework for agent evaluation
 *
 * This example shows how to use the benchmark framework to evaluate agents
 * across different scales and complexity levels. It demonstrates:
 * - Using pre-built benchmark suites (quick, standard, extreme_scale)
 * - Creating custom benchmarks
 * - Filtering test cases by tags
 * - Analyzing benchmark results
 * - Best practices for agent evaluation
 */

#include "agenkit/evaluation/benchmarks.hpp"
#include <iostream>
#include <iomanip>

using namespace agenkit::evaluation;

/**
 * Print test case details
 */
void print_test_case(const TestCase& tc, size_t index) {
    std::cout << "   Test " << (index + 1) << ":" << std::endl;
    std::cout << "     Input: " << tc.input.substr(0, 60);
    if (tc.input.length() > 60) {
        std::cout << "...";
    }
    std::cout << std::endl;

    std::cout << "     Tags: ";
    for (size_t i = 0; i < tc.tags.size(); ++i) {
        if (i > 0) {
            std::cout << ", ";
        }
        std::cout << tc.tags[i];
    }
    std::cout << std::endl;

    // Print metadata
    if (!tc.metadata.empty()) {
        std::cout << "     Metadata: ";
        bool first = true;
        for (const auto& [key, value] : tc.metadata) {
            if (!first) {
                std::cout << ", ";
            }
            first = false;
            std::cout << key << "=";
            if (value.type() == typeid(std::string)) {
                std::cout << std::any_cast<std::string>(value);
            } else if (value.type() == typeid(int)) {
                std::cout << std::any_cast<int>(value);
            } else if (value.type() == typeid(double)) {
                std::cout << std::any_cast<double>(value);
            }
        }
        std::cout << std::endl;
    }
}

/**
 * Demonstrate individual benchmarks
 */
void demonstrate_individual_benchmarks() {
    std::cout << "=== Individual Benchmarks ===" << std::endl;
    std::cout << std::endl;

    // 1. SimpleQABenchmark
    std::cout << "1. SimpleQABenchmark:" << std::endl;
    SimpleQABenchmark simple_qa;
    std::cout << "   Description: " << simple_qa.description() << std::endl;

    auto simple_cases = simple_qa.generate_test_cases().get();
    std::cout << "   Test cases: " << simple_cases.size() << std::endl;
    std::cout << std::endl;

    // Show first test case
    if (!simple_cases.empty()) {
        print_test_case(simple_cases[0], 0);
    }
    std::cout << std::endl;

    // 2. NeedleInHaystackBenchmark
    std::cout << "2. NeedleInHaystackBenchmark:" << std::endl;
    NeedleInHaystackBenchmark needle_benchmark(5000, 3);  // 5K tokens, 3 needles
    std::cout << "   Description: " << needle_benchmark.description() << std::endl;

    auto needle_cases = needle_benchmark.generate_test_cases().get();
    std::cout << "   Test cases: " << needle_cases.size() << std::endl;

    if (!needle_cases.empty()) {
        std::cout << "   First test case context length: "
                  << std::any_cast<int>(needle_cases[0].metadata.at("context_length"))
                  << " tokens" << std::endl;
    }
    std::cout << std::endl;

    // 3. InformationRetentionBenchmark
    std::cout << "3. InformationRetentionBenchmark:" << std::endl;
    InformationRetentionBenchmark retention_benchmark(
        30,  // 30 turns
        std::vector<size_t>{10, 20, 30}  // Recall at these points
    );
    std::cout << "   Description: " << retention_benchmark.description() << std::endl;

    auto retention_cases = retention_benchmark.generate_test_cases().get();
    std::cout << "   Test cases: " << retention_cases.size() << std::endl;
    std::cout << std::endl;

    // 4. ExtremeScaleBenchmark (small for demo)
    std::cout << "4. ExtremeScaleBenchmark (scaled down for demo):" << std::endl;
    ExtremeScaleBenchmark extreme_benchmark(
        std::vector<size_t>{10000, 50000},  // Much smaller than production
        2  // 2 needles per length
    );
    std::cout << "   Description: " << extreme_benchmark.description() << std::endl;

    auto extreme_cases = extreme_benchmark.generate_test_cases().get();
    std::cout << "   Test cases: " << extreme_cases.size() << std::endl;
    std::cout << std::endl;
}

/**
 * Demonstrate benchmark suites
 */
void demonstrate_benchmark_suites() {
    std::cout << "=== Benchmark Suites ===" << std::endl;
    std::cout << std::endl;

    // 1. Quick suite (for rapid iteration)
    std::cout << "1. Quick Suite (for rapid iteration):" << std::endl;
    auto quick = BenchmarkSuite::quick();

    auto quick_benchmarks = quick.get_benchmarks();
    std::cout << "   Benchmarks: " << quick_benchmarks.size() << std::endl;
    for (const auto& [name, benchmark] : quick_benchmarks) {
        std::cout << "     - " << name << ": " << benchmark->description() << std::endl;
    }

    auto quick_cases = quick.generate_all_test_cases().get();
    std::cout << "   Total test cases: " << quick_cases.size() << std::endl;
    std::cout << "   Use case: Development and debugging" << std::endl;
    std::cout << std::endl;

    // 2. Standard suite (balanced evaluation)
    std::cout << "2. Standard Suite (balanced evaluation):" << std::endl;
    auto standard = BenchmarkSuite::standard();

    auto standard_benchmarks = standard.get_benchmarks();
    std::cout << "   Benchmarks: " << standard_benchmarks.size() << std::endl;
    for (const auto& [name, benchmark] : standard_benchmarks) {
        std::cout << "     - " << name << ": " << benchmark->description() << std::endl;
    }

    auto standard_cases = standard.generate_all_test_cases().get();
    std::cout << "   Total test cases: " << standard_cases.size() << std::endl;
    std::cout << "   Use case: Production agent evaluation" << std::endl;
    std::cout << std::endl;

    // 3. Extreme scale suite (resource intensive)
    std::cout << "3. Extreme Scale Suite (⚠️  very resource intensive):" << std::endl;
    auto extreme = BenchmarkSuite::extreme_scale();

    auto extreme_benchmarks = extreme.get_benchmarks();
    std::cout << "   Benchmarks: " << extreme_benchmarks.size() << std::endl;
    for (const auto& [name, benchmark] : extreme_benchmarks) {
        std::cout << "     - " << name << std::endl;
    }

    std::cout << "   Use case: Testing compression and extreme context handling" << std::endl;
    std::cout << "   Warning: May generate contexts up to 25M tokens" << std::endl;
    std::cout << std::endl;

    // NOTE: We don't generate extreme_cases here to avoid memory issues in example
}

/**
 * Demonstrate custom benchmark creation
 */
void demonstrate_custom_suite() {
    std::cout << "=== Custom Benchmark Suite ===" << std::endl;
    std::cout << std::endl;

    BenchmarkSuite custom;

    // Add specific benchmarks
    custom.add_benchmark(std::make_shared<SimpleQABenchmark>());
    custom.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(3000, 3));

    std::cout << "Custom suite with:" << std::endl;
    auto benchmarks = custom.get_benchmarks();
    for (const auto& [name, benchmark] : benchmarks) {
        std::cout << "  - " << name << std::endl;
    }
    std::cout << std::endl;

    // Get summary
    auto summary = custom.get_summary().get();
    std::cout << "Summary:" << std::endl;
    std::cout << "  Total benchmarks: " << summary["benchmark_count"] << std::endl;
    std::cout << "  Total test cases: " << summary["total_test_cases"] << std::endl;
    std::cout << std::endl;

    for (const auto& [name, benchmark] : benchmarks) {
        if (summary.contains(name)) {
            std::cout << "  " << name << ": "
                      << summary[name]["test_case_count"] << " cases" << std::endl;
        }
    }
    std::cout << std::endl;
}

/**
 * Demonstrate filtering test cases by tags
 */
void demonstrate_tag_filtering() {
    std::cout << "=== Tag-Based Filtering ===" << std::endl;
    std::cout << std::endl;

    auto suite = BenchmarkSuite::standard();

    // Filter for math tests
    std::cout << "1. Math tests only:" << std::endl;
    auto math_cases = suite.generate_test_cases_by_tags(
        std::vector<std::string>{"math"}
    ).get();
    std::cout << "   Found " << math_cases.size() << " math test cases" << std::endl;
    std::cout << std::endl;

    // Filter for easy tests
    std::cout << "2. Easy tests only:" << std::endl;
    auto easy_cases = suite.generate_test_cases_by_tags(
        std::vector<std::string>{"easy"}
    ).get();
    std::cout << "   Found " << easy_cases.size() << " easy test cases" << std::endl;
    std::cout << std::endl;

    // Filter for retrieval tests
    std::cout << "3. Retrieval tests only:" << std::endl;
    auto retrieval_cases = suite.generate_test_cases_by_tags(
        std::vector<std::string>{"retrieval"}
    ).get();
    std::cout << "   Found " << retrieval_cases.size() << " retrieval test cases" << std::endl;
    std::cout << std::endl;

    // Multiple tag filter (AND logic)
    std::cout << "4. Tests that are both 'math' AND 'easy':" << std::endl;
    auto math_easy_cases = suite.generate_test_cases_by_tags(
        std::vector<std::string>{"math", "easy"}
    ).get();
    std::cout << "   Found " << math_easy_cases.size() << " test cases" << std::endl;
    std::cout << std::endl;
}

/**
 * Demonstrate validation
 */
void demonstrate_validation() {
    std::cout << "=== Test Case Validation ===" << std::endl;
    std::cout << std::endl;

    SimpleQABenchmark benchmark;
    auto cases = benchmark.generate_test_cases().get();

    // Find arithmetic test
    for (const auto& tc : cases) {
        if (tc.has_tag("arithmetic")) {
            std::cout << "Testing arithmetic question: \"" << tc.input << "\"" << std::endl;
            std::cout << std::endl;

            // Test various responses
            std::vector<std::pair<std::string, bool>> test_responses = {
                {"The answer is 4", true},
                {"4", true},
                {"four", true},
                {"2+2=4", true},
                {"The answer is 5", false},
                {"I don't know", false}
            };

            for (const auto& [response, expected] : test_responses) {
                bool valid = tc.validate(response);
                std::cout << "   Response: \"" << response << "\" → "
                          << (valid ? "✓ VALID" : "✗ INVALID");
                if (valid != expected) {
                    std::cout << " (UNEXPECTED!)";
                }
                std::cout << std::endl;
            }

            break;
        }
    }
    std::cout << std::endl;
}

/**
 * Demonstrate JSON serialization
 */
void demonstrate_json_export() {
    std::cout << "=== JSON Export ===" << std::endl;
    std::cout << std::endl;

    SimpleQABenchmark benchmark;
    auto cases = benchmark.generate_test_cases().get();

    if (!cases.empty()) {
        auto json = cases[0].to_json();
        std::cout << "Example test case as JSON:" << std::endl;
        std::cout << json.dump(2) << std::endl;
        std::cout << std::endl;

        // Demonstrate roundtrip
        auto restored = TestCase::from_json(json);
        std::cout << "Restored from JSON:" << std::endl;
        std::cout << "  Input: " << restored.input << std::endl;
        std::cout << "  Tags: ";
        for (size_t i = 0; i < restored.tags.size(); ++i) {
            if (i > 0) {
                std::cout << ", ";
            }
            std::cout << restored.tags[i];
        }
        std::cout << std::endl;
    }
    std::cout << std::endl;
}

/**
 * Best practices and recommendations
 */
void print_best_practices() {
    std::cout << "=== Best Practices ===" << std::endl;
    std::cout << std::endl;

    std::cout << "1. Choosing a benchmark suite:" << std::endl;
    std::cout << "   • quick(): For rapid iteration during development" << std::endl;
    std::cout << "   • standard(): For comprehensive agent evaluation" << std::endl;
    std::cout << "   • extreme_scale(): For testing compression and extreme contexts" << std::endl;
    std::cout << std::endl;

    std::cout << "2. Creating custom benchmarks:" << std::endl;
    std::cout << "   • Inherit from Benchmark base class" << std::endl;
    std::cout << "   • Implement name(), description(), generate_test_cases()" << std::endl;
    std::cout << "   • Add appropriate tags for filtering" << std::endl;
    std::cout << "   • Include metadata for analysis" << std::endl;
    std::cout << std::endl;

    std::cout << "3. Validation strategies:" << std::endl;
    std::cout << "   • Exact match: Good for deterministic answers" << std::endl;
    std::cout << "   • Function validator: For flexible validation logic" << std::endl;
    std::cout << "   • Consider case-sensitivity and whitespace" << std::endl;
    std::cout << std::endl;

    std::cout << "4. Performance considerations:" << std::endl;
    std::cout << "   • Start with quick() suite for development" << std::endl;
    std::cout << "   • Use tag filtering to test specific capabilities" << std::endl;
    std::cout << "   • Extreme scale tests consume significant resources" << std::endl;
    std::cout << "   • Generate test cases in parallel when possible" << std::endl;
    std::cout << std::endl;

    std::cout << "5. Integration with evaluation pipeline:" << std::endl;
    std::cout << "   • Combine with MetricsCollector for automated evaluation" << std::endl;
    std::cout << "   • Use SessionRecorder to replay benchmark runs" << std::endl;
    std::cout << "   • Export results to JSON for analysis" << std::endl;
    std::cout << "   • Track regression with RegressionDetector" << std::endl;
    std::cout << std::endl;
}

int main() {
    std::cout << "=== Benchmark Framework Example ===" << std::endl;
    std::cout << std::endl;

    // Demonstrate individual benchmarks
    demonstrate_individual_benchmarks();

    // Demonstrate benchmark suites
    demonstrate_benchmark_suites();

    // Demonstrate custom suite creation
    demonstrate_custom_suite();

    // Demonstrate tag-based filtering
    demonstrate_tag_filtering();

    // Demonstrate validation
    demonstrate_validation();

    // Demonstrate JSON export
    demonstrate_json_export();

    // Print best practices
    print_best_practices();

    std::cout << "=== Example Complete ===" << std::endl;
    std::cout << std::endl;
    std::cout << "Next steps:" << std::endl;
    std::cout << "  1. Choose appropriate benchmark suite for your use case" << std::endl;
    std::cout << "  2. Integrate with your agent implementation" << std::endl;
    std::cout << "  3. Run benchmarks to establish baseline performance" << std::endl;
    std::cout << "  4. Use results to identify areas for improvement" << std::endl;
    std::cout << "  5. Track changes over time with RegressionDetector" << std::endl;

    return 0;
}
