/**
 * @file benchmarks.hpp
 * @brief Standardized benchmark framework for agent evaluation
 *
 * This module provides a comprehensive benchmark framework for evaluating agents
 * across different scales and complexity levels. It includes:
 * - TestCase abstraction for input/output validation
 * - Benchmark base class for creating custom benchmarks
 * - Pre-built benchmarks (Q&A, needle-in-haystack, extreme scale, retention)
 * - BenchmarkSuite for organizing and running multiple benchmarks
 *
 * @example
 * ```cpp
 * // Use standard benchmark suite
 * auto suite = BenchmarkSuite::standard();
 * auto test_cases = suite.generate_all_test_cases().get();
 *
 * // Create custom benchmark
 * class CustomBenchmark : public Benchmark {
 *     std::string name() const override { return "custom"; }
 *     std::string description() const override { return "Custom test"; }
 *     std::future<std::vector<TestCase>> generate_test_cases() override {
 *         return std::async(std::launch::async, []() {
 *             return std::vector<TestCase>{TestCase("input", "output")};
 *         });
 *     }
 * };
 * ```
 */

#pragma once

#include <string>
#include <vector>
#include <map>
#include <any>
#include <functional>
#include <memory>
#include <future>
#include <variant>
#include <optional>
#include "nlohmann/json.hpp"

namespace agenkit {
namespace evaluation {

/**
 * @brief Test case for agent evaluation
 *
 * Represents a single test case with input, expected output, and metadata.
 * The expected output can be:
 * - A string for exact matching
 * - A validation function for custom validation logic
 *
 * @example
 * ```cpp
 * // Exact match
 * TestCase case1("What is 2+2?", "4");
 *
 * // Custom validation
 * TestCase case2("Explain quantum computing",
 *                [](const std::string& output) {
 *                    return output.length() > 100 &&
 *                           output.find("quantum") != std::string::npos;
 *                });
 *
 * // With metadata and tags
 * TestCase case3("Complex question", "answer");
 * case3.metadata["difficulty"] = "hard";
 * case3.tags = {"math", "reasoning"};
 * ```
 */
struct TestCase {
    /**
     * @brief Input prompt or question for the agent
     */
    std::string input;

    /**
     * @brief Expected output (string for exact match, or validation function)
     *
     * If this is a string, validation is done via exact match (case-sensitive).
     * If this is a function, it receives the agent's output and returns true if valid.
     */
    std::variant<std::string, std::function<bool(const std::string&)>> expected;

    /**
     * @brief Additional metadata for the test case
     *
     * Can store any test-specific information like difficulty, category, etc.
     */
    std::map<std::string, std::any> metadata;

    /**
     * @brief Tags for categorizing and filtering test cases
     *
     * Examples: "math", "reasoning", "retrieval", "long-context"
     */
    std::vector<std::string> tags;

    /**
     * @brief Construct test case with exact string match
     */
    TestCase(const std::string& input_str, const std::string& expected_str)
        : input(input_str), expected(expected_str) {}

    /**
     * @brief Construct test case with validation function
     */
    TestCase(const std::string& input_str,
             std::function<bool(const std::string&)> validator)
        : input(input_str), expected(validator) {}

    /**
     * @brief Validate agent output against expected result
     *
     * @param actual The agent's actual output
     * @return true if output is valid, false otherwise
     */
    bool validate(const std::string& actual) const;

    /**
     * @brief Check if test case has a specific tag
     */
    bool has_tag(const std::string& tag) const;

    /**
     * @brief Convert to JSON representation
     */
    nlohmann::json to_json() const;

    /**
     * @brief Create from JSON representation
     */
    static TestCase from_json(const nlohmann::json& j);
};

/**
 * @brief Abstract base class for benchmarks
 *
 * A benchmark is a collection of test cases that evaluate specific agent capabilities.
 * Subclasses must implement name(), description(), and generate_test_cases().
 *
 * @example
 * ```cpp
 * class MyBenchmark : public Benchmark {
 * public:
 *     std::string name() const override {
 *         return "my_benchmark";
 *     }
 *
 *     std::string description() const override {
 *         return "Tests my specific capability";
 *     }
 *
 *     std::future<std::vector<TestCase>> generate_test_cases() override {
 *         return std::async(std::launch::async, []() {
 *             std::vector<TestCase> cases;
 *             cases.push_back(TestCase("input1", "output1"));
 *             cases.push_back(TestCase("input2", "output2"));
 *             return cases;
 *         });
 *     }
 * };
 * ```
 */
class Benchmark {
public:
    virtual ~Benchmark() = default;

    /**
     * @brief Get the unique name of this benchmark
     *
     * @return Benchmark identifier (lowercase, underscore-separated)
     */
    virtual std::string name() const = 0;

    /**
     * @brief Get human-readable description of what this benchmark tests
     *
     * @return Description of benchmark purpose and scope
     */
    virtual std::string description() const = 0;

    /**
     * @brief Generate all test cases for this benchmark
     *
     * This method may be computationally expensive (generating large contexts),
     * so it returns a future to allow async execution.
     *
     * @return Future containing vector of test cases
     */
    virtual std::future<std::vector<TestCase>> generate_test_cases() = 0;
};

/**
 * @brief Simple Q&A benchmark with basic questions
 *
 * Tests basic factual knowledge, arithmetic, and common sense reasoning.
 * Includes 5 test cases covering:
 * - Arithmetic (2+2)
 * - Geography (capital of France)
 * - Observation (color of sky)
 * - Counting (days in week)
 * - Chemistry (composition of water)
 *
 * @example
 * ```cpp
 * auto benchmark = std::make_shared<SimpleQABenchmark>();
 * auto test_cases = benchmark->generate_test_cases().get();
 * // test_cases.size() == 5
 * ```
 */
class SimpleQABenchmark : public Benchmark {
public:
    SimpleQABenchmark() = default;

    std::string name() const override;
    std::string description() const override;
    std::future<std::vector<TestCase>> generate_test_cases() override;
};

/**
 * @brief Needle-in-haystack retrieval benchmark
 *
 * Tests an agent's ability to retrieve specific information ("needles")
 * embedded within large amounts of distractor text ("haystack").
 *
 * This benchmark generates synthetic context with embedded facts at regular
 * intervals, then asks questions that require retrieving those facts.
 *
 * @example
 * ```cpp
 * // Test retrieval from 10K token context with 5 needles
 * auto benchmark = std::make_shared<NeedleInHaystackBenchmark>(10000, 5);
 * auto test_cases = benchmark->generate_test_cases().get();
 *
 * // Test retrieval from 1M token context (extreme scale)
 * auto extreme = std::make_shared<NeedleInHaystackBenchmark>(1000000, 10);
 * ```
 */
class NeedleInHaystackBenchmark : public Benchmark {
public:
    /**
     * @brief Construct needle-in-haystack benchmark
     *
     * @param context_length Target context length in tokens (approximate)
     * @param needle_count Number of needles to embed in haystack
     */
    explicit NeedleInHaystackBenchmark(
        size_t context_length = 10000,
        size_t needle_count = 5
    );

    std::string name() const override;
    std::string description() const override;
    std::future<std::vector<TestCase>> generate_test_cases() override;

private:
    size_t context_length_;
    size_t needle_count_;

    /**
     * @brief Generate haystack text of approximately target_tokens length
     */
    std::string generate_haystack(size_t target_tokens) const;

    /**
     * @brief Generate a needle (fact to be retrieved)
     */
    std::string generate_needle(size_t index) const;

    /**
     * @brief Estimate token count (rough approximation: 4 chars ≈ 1 token)
     */
    size_t estimate_tokens(const std::string& text) const;
};

/**
 * @brief Extreme-scale benchmark for testing at 1M-25M token contexts
 *
 * Tests agent performance at extreme context lengths suitable for systems
 * like "Endless" that handle millions of tokens. This benchmark is critical
 * for validating compression, retrieval, and memory management at scale.
 *
 * For each test length, embeds multiple needles and generates retrieval
 * questions to test if the agent can still access information correctly.
 *
 * @warning This benchmark generates very large contexts (up to 25M tokens)
 *          and may consume significant memory and time.
 *
 * @example
 * ```cpp
 * // Test at default lengths: 1M, 10M, 25M tokens
 * auto benchmark = std::make_shared<ExtremeScaleBenchmark>();
 * auto test_cases = benchmark->generate_test_cases().get();
 *
 * // Custom lengths: 500K, 2M, 5M tokens
 * auto custom = std::make_shared<ExtremeScaleBenchmark>(
 *     std::vector<size_t>{500000, 2000000, 5000000},
 *     5  // 5 needles per length
 * );
 * ```
 */
class ExtremeScaleBenchmark : public Benchmark {
public:
    /**
     * @brief Construct extreme-scale benchmark
     *
     * @param test_lengths Context lengths to test (in tokens)
     * @param needles_per_length Number of needles to embed at each length
     */
    explicit ExtremeScaleBenchmark(
        const std::vector<size_t>& test_lengths = {1000000, 10000000, 25000000},
        size_t needles_per_length = 10
    );

    std::string name() const override;
    std::string description() const override;
    std::future<std::vector<TestCase>> generate_test_cases() override;

private:
    std::vector<size_t> test_lengths_;
    size_t needles_per_length_;

    /**
     * @brief Generate test cases for a specific context length
     */
    std::vector<TestCase> generate_for_length(size_t length);
};

/**
 * @brief Information retention benchmark for multi-turn conversations
 *
 * Tests an agent's ability to retain and recall information across many
 * conversation turns. Simulates a long conversation with embedded facts,
 * then asks recall questions at various points.
 *
 * This is critical for conversational agents that need to remember context
 * from earlier in a session (e.g., user preferences, previous answers).
 *
 * @example
 * ```cpp
 * // 100-turn conversation with recall at turns 10, 25, 50, 75, 100
 * auto benchmark = std::make_shared<InformationRetentionBenchmark>(
 *     100,
 *     std::vector<size_t>{10, 25, 50, 75, 100}
 * );
 *
 * // 1000-turn conversation (extreme retention test)
 * auto extreme = std::make_shared<InformationRetentionBenchmark>(
 *     1000,
 *     std::vector<size_t>{100, 250, 500, 750, 1000}
 * );
 * ```
 */
class InformationRetentionBenchmark : public Benchmark {
public:
    /**
     * @brief Construct information retention benchmark
     *
     * @param conversation_length Total number of conversation turns
     * @param recall_points Turn numbers at which to test recall
     */
    explicit InformationRetentionBenchmark(
        size_t conversation_length = 100,
        const std::vector<size_t>& recall_points = {10, 25, 50, 75, 100}
    );

    std::string name() const override;
    std::string description() const override;
    std::future<std::vector<TestCase>> generate_test_cases() override;

private:
    size_t conversation_length_;
    std::vector<size_t> recall_points_;

    /**
     * @brief Generate conversation history with embedded facts
     */
    std::string generate_conversation(size_t turns, std::vector<std::string>& facts);

    /**
     * @brief Generate a fact to be remembered
     */
    std::string generate_fact(size_t index) const;
};

/**
 * @brief Collection of benchmarks for comprehensive evaluation
 *
 * A BenchmarkSuite combines multiple benchmarks into a single test suite.
 * Provides factory methods for common configurations:
 * - standard(): Balanced suite for general evaluation
 * - extreme_scale(): Tests at 1M-25M tokens
 * - quick(): Fast subset for rapid iteration
 *
 * @example
 * ```cpp
 * // Use standard benchmark suite
 * auto suite = BenchmarkSuite::standard();
 * auto all_cases = suite.generate_all_test_cases().get();
 * std::cout << "Total test cases: " << all_cases.size() << std::endl;
 *
 * // Create custom suite
 * BenchmarkSuite custom;
 * custom.add_benchmark(std::make_shared<SimpleQABenchmark>());
 * custom.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(50000));
 *
 * // Get benchmarks by name
 * auto benchmarks = custom.get_benchmarks();
 * for (const auto& [name, benchmark] : benchmarks) {
 *     std::cout << name << ": " << benchmark->description() << std::endl;
 * }
 * ```
 */
class BenchmarkSuite {
public:
    BenchmarkSuite() = default;

    /**
     * @brief Add a benchmark to this suite
     *
     * @param benchmark Shared pointer to benchmark instance
     */
    void add_benchmark(std::shared_ptr<Benchmark> benchmark);

    /**
     * @brief Generate all test cases from all benchmarks
     *
     * Runs all benchmarks in parallel and combines results.
     *
     * @return Future containing all test cases from all benchmarks
     */
    std::future<std::vector<TestCase>> generate_all_test_cases();

    /**
     * @brief Get all benchmarks in this suite
     *
     * @return Map of benchmark name to benchmark instance
     */
    std::map<std::string, std::shared_ptr<Benchmark>> get_benchmarks() const;

    /**
     * @brief Get a specific benchmark by name
     *
     * @param name Benchmark name
     * @return Optional containing benchmark if found
     */
    std::optional<std::shared_ptr<Benchmark>> get_benchmark(const std::string& name) const;

    /**
     * @brief Get test cases filtered by tags
     *
     * @param tags Tags to filter by (test case must have ALL tags)
     * @return Future containing filtered test cases
     */
    std::future<std::vector<TestCase>> generate_test_cases_by_tags(
        const std::vector<std::string>& tags
    );

    /**
     * @brief Get summary statistics for this suite
     *
     * @return JSON object with test case counts per benchmark
     */
    std::future<nlohmann::json> get_summary();

    /**
     * @brief Create standard benchmark suite
     *
     * Includes:
     * - SimpleQABenchmark: 5 basic Q&A tests
     * - NeedleInHaystackBenchmark: 10K tokens, 5 needles
     * - InformationRetentionBenchmark: 50 turns, recall at 10/25/50
     *
     * Total: ~20-30 test cases
     * Good for: General agent evaluation
     *
     * @return Standard benchmark suite
     */
    static BenchmarkSuite standard();

    /**
     * @brief Create extreme-scale benchmark suite
     *
     * Includes:
     * - ExtremeScaleBenchmark: 1M, 10M, 25M tokens
     * - InformationRetentionBenchmark: 1000 turns
     * - NeedleInHaystackBenchmark: 1M tokens, 20 needles
     *
     * Total: ~50-100 test cases
     * Good for: Testing compression and extreme context handling
     *
     * @warning This suite is very resource-intensive
     *
     * @return Extreme-scale benchmark suite
     */
    static BenchmarkSuite extreme_scale();

    /**
     * @brief Create quick benchmark suite
     *
     * Includes:
     * - SimpleQABenchmark: 5 tests
     * - NeedleInHaystackBenchmark: 1K tokens, 3 needles
     *
     * Total: ~10 test cases
     * Good for: Rapid iteration during development
     *
     * @return Quick benchmark suite
     */
    static BenchmarkSuite quick();

private:
    std::map<std::string, std::shared_ptr<Benchmark>> benchmarks_;
};

}  // namespace evaluation
}  // namespace agenkit
