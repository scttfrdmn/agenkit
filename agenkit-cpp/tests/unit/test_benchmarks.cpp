/**
 * @file test_benchmarks.cpp
 * @brief Unit tests for benchmark framework
 */

#include <gtest/gtest.h>
#include "agenkit/evaluation/benchmarks.hpp"

using namespace agenkit::evaluation;

// ============================================================================
// TestCase Tests
// ============================================================================

TEST(TestCaseTest, ValidateSubstringMatch) {
    TestCase tc("input", "expected");
    EXPECT_TRUE(tc.validate("expected"));
    EXPECT_FALSE(tc.validate("wrong"));
}

TEST(TestCaseTest, ValidateMatchesFragmentInProse) {
    // A string `expected` is the fragment to find in the output, not the whole output.
    // This used to be `==`, which disagreed with this core's own AccuracyMetric and
    // scored every realistic agent reply zero (#820).
    TestCase tc("What is 15 + 27?", "42");

    EXPECT_TRUE(tc.validate("42"));
    EXPECT_TRUE(tc.validate("The answer is 42."));
    EXPECT_TRUE(tc.validate("15 + 27 = 42, so the total is 42 items."));
    EXPECT_FALSE(tc.validate("The answer is 41."));

    // The fragment must appear whole — a prefix of it is not a match.
    TestCase paris("Capital of France?", "Paris");
    EXPECT_FALSE(paris.validate("Par"));
    EXPECT_TRUE(paris.validate("It is Paris, in northern France."));
}

TEST(TestCaseTest, ValidateIgnoresCase) {
    // Case-insensitive by default, matching Python, Go, TypeScript, Rust and Zig, and
    // the case_sensitive = false default of every core's AccuracyMetric. Callers
    // needing case sensitivity use the std::function variant.
    TestCase tc("Capital of France?", "Paris");

    EXPECT_TRUE(tc.validate("paris"));
    EXPECT_TRUE(tc.validate("PARIS"));
    EXPECT_TRUE(tc.validate("The capital is PaRiS."));
    EXPECT_FALSE(tc.validate("Lyon"));
}

TEST(TestCaseTest, ValidateSubstringEdgeCases) {
    // An empty expected value matches anything: nothing was asked for.
    TestCase empty("input", "");
    EXPECT_TRUE(empty.validate(""));
    EXPECT_TRUE(empty.validate("anything at all"));

    // An expected value longer than the output cannot match.
    TestCase long_expected("input", "a very long expected value");
    EXPECT_FALSE(long_expected.validate("short"));
    EXPECT_FALSE(long_expected.validate(""));

    // A match at the very end of the output still counts.
    TestCase tail("input", "end");
    EXPECT_TRUE(tail.validate("this is the end"));
}

TEST(TestCaseTest, ValidateWithFunction) {
    auto validator = [](const std::string& output) {
        return output.find("42") != std::string::npos;
    };
    TestCase tc("What is the answer?", validator);

    EXPECT_TRUE(tc.validate("The answer is 42"));
    EXPECT_TRUE(tc.validate("42 is correct"));
    EXPECT_FALSE(tc.validate("The answer is 43"));
    EXPECT_FALSE(tc.validate("I don't know"));
}

TEST(TestCaseTest, HasTag) {
    TestCase tc("input", "output");
    tc.tags = {"math", "easy", "arithmetic"};

    EXPECT_TRUE(tc.has_tag("math"));
    EXPECT_TRUE(tc.has_tag("easy"));
    EXPECT_TRUE(tc.has_tag("arithmetic"));
    EXPECT_FALSE(tc.has_tag("hard"));
    EXPECT_FALSE(tc.has_tag("geography"));
}

TEST(TestCaseTest, Metadata) {
    TestCase tc("input", "output");
    tc.metadata["difficulty"] = std::string("medium");
    tc.metadata["score"] = 85;
    tc.metadata["timeout"] = 30.0;

    EXPECT_EQ(tc.metadata.size(), 3);
    EXPECT_EQ(std::any_cast<std::string>(tc.metadata["difficulty"]), "medium");
    EXPECT_EQ(std::any_cast<int>(tc.metadata["score"]), 85);
    EXPECT_DOUBLE_EQ(std::any_cast<double>(tc.metadata["timeout"]), 30.0);
}

TEST(TestCaseTest, ToJsonFromJson) {
    TestCase tc("What is 2+2?", "4");
    tc.tags = {"math", "easy"};
    tc.metadata["difficulty"] = std::string("easy");
    tc.metadata["score"] = 100;

    // Serialize
    auto json = tc.to_json();

    // Deserialize
    auto tc2 = TestCase::from_json(json);

    EXPECT_EQ(tc2.input, "What is 2+2?");
    EXPECT_EQ(std::get<std::string>(tc2.expected), "4");
    EXPECT_EQ(tc2.tags.size(), 2);
    EXPECT_TRUE(tc2.has_tag("math"));
    EXPECT_TRUE(tc2.has_tag("easy"));
    EXPECT_EQ(std::any_cast<std::string>(tc2.metadata["difficulty"]), "easy");
    EXPECT_EQ(std::any_cast<int>(tc2.metadata["score"]), 100);
}

TEST(TestCaseTest, FromJsonFunctionalCaseDoesNotBecomeAlwaysPass) {
    // A std::function expected value can't be serialized. from_json used to leave the
    // empty string, which failed everything under the old exact comparison — wrong, but
    // safely so. An empty string is now a substring check that matches *everything*, so
    // without care every round-tripped functional case would pass unconditionally (#820).
    TestCase tc("What is the answer?", [](const std::string& output) {
        return output.find("42") != std::string::npos;
    });

    auto json = tc.to_json();
    EXPECT_EQ(json["expected_type"], "function");

    auto restored = TestCase::from_json(json);
    EXPECT_FALSE(restored.validate("42"));
    EXPECT_FALSE(restored.validate("anything at all"));
    EXPECT_FALSE(restored.validate(""));
}

// ============================================================================
// SimpleQABenchmark Tests
// ============================================================================

TEST(SimpleQABenchmarkTest, NameAndDescription) {
    SimpleQABenchmark benchmark;

    EXPECT_EQ(benchmark.name(), "simple_qa");
    EXPECT_FALSE(benchmark.description().empty());
}

TEST(SimpleQABenchmarkTest, GenerateTestCases) {
    SimpleQABenchmark benchmark;
    auto future = benchmark.generate_test_cases();
    auto cases = future.get();

    EXPECT_EQ(cases.size(), 5);

    // Verify all cases have tags
    for (const auto& tc : cases) {
        EXPECT_FALSE(tc.tags.empty());
        EXPECT_FALSE(tc.input.empty());
    }
}

TEST(SimpleQABenchmarkTest, TestCaseValidation) {
    SimpleQABenchmark benchmark;
    auto cases = benchmark.generate_test_cases().get();

    // Test arithmetic case (should accept "4" or "four")
    bool found_arithmetic = false;
    for (const auto& tc : cases) {
        if (tc.has_tag("arithmetic")) {
            found_arithmetic = true;
            EXPECT_TRUE(tc.validate("The answer is 4"));
            EXPECT_TRUE(tc.validate("four"));
            EXPECT_FALSE(tc.validate("5"));
            break;
        }
    }
    EXPECT_TRUE(found_arithmetic);
}

// ============================================================================
// NeedleInHaystackBenchmark Tests
// ============================================================================

TEST(NeedleInHaystackBenchmarkTest, NameAndDescription) {
    NeedleInHaystackBenchmark benchmark(10000, 5);

    EXPECT_EQ(benchmark.name(), "needle_in_haystack_10000");
    EXPECT_FALSE(benchmark.description().empty());
    EXPECT_NE(benchmark.description().find("10000"), std::string::npos);
}

TEST(NeedleInHaystackBenchmarkTest, GenerateTestCases) {
    NeedleInHaystackBenchmark benchmark(1000, 3);  // Small for testing
    auto future = benchmark.generate_test_cases();
    auto cases = future.get();

    EXPECT_EQ(cases.size(), 3);  // One test case per needle

    // Verify all cases have retrieval tag
    for (const auto& tc : cases) {
        EXPECT_TRUE(tc.has_tag("retrieval"));
        EXPECT_TRUE(tc.has_tag("needle_in_haystack"));
        EXPECT_FALSE(tc.input.empty());
    }
}

TEST(NeedleInHaystackBenchmarkTest, ValidateRetrieval) {
    NeedleInHaystackBenchmark benchmark(500, 2);
    auto cases = benchmark.generate_test_cases().get();

    ASSERT_EQ(cases.size(), 2);

    // First needle should have code 1042
    EXPECT_TRUE(cases[0].validate("The code is 1042"));
    EXPECT_FALSE(cases[0].validate("The code is 2042"));

    // Second needle should have code 2042
    EXPECT_TRUE(cases[1].validate("The code is 2042"));
    EXPECT_FALSE(cases[1].validate("The code is 1042"));
}

TEST(NeedleInHaystackBenchmarkTest, ContextLength) {
    constexpr int kTarget = 5000;
    NeedleInHaystackBenchmark benchmark(kTarget, 3);
    auto cases = benchmark.generate_test_cases().get();

    // Check that context_length is in metadata, and that it actually approximates the
    // requested target.
    //
    // `EXPECT_GT(context_length, 0)` was all this asserted, which is why the benchmark
    // could advertise a 5000-token context and build ~1155 for years: the multiplier was
    // read *instead of* context_length, so the size didn't track the request at all (#796).
    // A ±20% band is generous enough for the 4-chars-per-token estimate and the
    // whole-sentence granularity of the filler, but tight enough to catch a wrong formula.
    for (const auto& tc : cases) {
        EXPECT_TRUE(tc.metadata.find("context_length") != tc.metadata.end());
        int context_length = std::any_cast<int>(tc.metadata.at("context_length"));
        EXPECT_GT(context_length, kTarget * 0.8)
            << "context far below the requested " << kTarget;
        EXPECT_LT(context_length, kTarget * 1.2)
            << "context far above the requested " << kTarget;
    }
}

TEST(NeedleInHaystackBenchmarkTest, ContextScalesWithRequestedLength) {
    // A tenfold larger request must produce a substantially larger context. Under the old
    // formula both sizes were derived from the needles alone, so this ratio was ~1.0
    // regardless of what the caller asked for (#796).
    auto small = NeedleInHaystackBenchmark(1000, 3).generate_test_cases().get();
    auto large = NeedleInHaystackBenchmark(10000, 3).generate_test_cases().get();

    ASSERT_FALSE(small.empty());
    ASSERT_FALSE(large.empty());

    auto tokens = [](const TestCase& tc) {
        return std::any_cast<int>(tc.metadata.at("context_length"));
    };
    EXPECT_GT(tokens(large[0]), tokens(small[0]) * 5)
        << "context size does not track the requested length";
}

TEST(NeedleInHaystackBenchmarkTest, NameEncodesFullContextLength) {
    // The name is a registry key (BenchmarkSuite::add_benchmark) and must match the form
    // Python, Go, Rust and TypeScript use. It previously abbreviated to "_10k" via integer
    // division, which both diverged from the other cores and collided: every context under
    // 1000 tokens became "needle_in_haystack_0k" (#790).
    EXPECT_EQ(NeedleInHaystackBenchmark(10000, 5).name(), "needle_in_haystack_10000");
    EXPECT_EQ(NeedleInHaystackBenchmark(500, 2).name(), "needle_in_haystack_500");
    EXPECT_NE(NeedleInHaystackBenchmark(500, 2).name(),
              NeedleInHaystackBenchmark(900, 2).name())
        << "sub-1000 contexts must not collide in the suite registry";
}

// ============================================================================
// ExtremeScaleBenchmark Tests
// ============================================================================

TEST(ExtremeScaleBenchmarkTest, NameAndDescription) {
    ExtremeScaleBenchmark benchmark(std::vector<size_t>{100000, 500000}, 3);

    EXPECT_EQ(benchmark.name(), "extreme_scale");
    EXPECT_FALSE(benchmark.description().empty());
}

TEST(ExtremeScaleBenchmarkTest, GenerateTestCases) {
    // Use smaller sizes for testing
    ExtremeScaleBenchmark benchmark(std::vector<size_t>{1000, 2000}, 2);
    auto future = benchmark.generate_test_cases();
    auto cases = future.get();

    // Should have 2 lengths * 2 needles = 4 test cases
    EXPECT_EQ(cases.size(), 4);

    // Verify all have extreme_scale tag
    for (const auto& tc : cases) {
        EXPECT_TRUE(tc.has_tag("extreme_scale"));
        EXPECT_TRUE(tc.has_tag("retrieval"));
    }
}

TEST(ExtremeScaleBenchmarkTest, MultipleTestLengths) {
    ExtremeScaleBenchmark benchmark(std::vector<size_t>{500, 1000, 1500}, 1);
    auto cases = benchmark.generate_test_cases().get();

    EXPECT_EQ(cases.size(), 3);  // 3 lengths * 1 needle each

    // Check that each has different test_length in metadata
    std::set<int> lengths;
    for (const auto& tc : cases) {
        int length = std::any_cast<int>(tc.metadata.at("test_length"));
        lengths.insert(length);
    }
    EXPECT_EQ(lengths.size(), 3);
}

// ============================================================================
// InformationRetentionBenchmark Tests
// ============================================================================

TEST(InformationRetentionBenchmarkTest, NameAndDescription) {
    InformationRetentionBenchmark benchmark(100, std::vector<size_t>{10, 50, 100});

    EXPECT_EQ(benchmark.name(), "information_retention_100");
    EXPECT_FALSE(benchmark.description().empty());
    EXPECT_NE(benchmark.description().find("100"), std::string::npos);
}

TEST(InformationRetentionBenchmarkTest, GenerateTestCases) {
    InformationRetentionBenchmark benchmark(20, std::vector<size_t>{5, 10, 20});
    auto future = benchmark.generate_test_cases();
    auto cases = future.get();

    EXPECT_EQ(cases.size(), 3);  // One per recall point

    // Verify all have retention tags
    for (const auto& tc : cases) {
        EXPECT_TRUE(tc.has_tag("retention"));
        EXPECT_TRUE(tc.has_tag("multi_turn"));
        EXPECT_TRUE(tc.has_tag("memory"));
        EXPECT_FALSE(tc.input.empty());
    }
}

TEST(InformationRetentionBenchmarkTest, RecallPoints) {
    InformationRetentionBenchmark benchmark(50, std::vector<size_t>{10, 25, 50});
    auto cases = benchmark.generate_test_cases().get();

    EXPECT_EQ(cases.size(), 3);

    // Check recall points in metadata
    std::set<int> recall_points;
    for (const auto& tc : cases) {
        int recall_point = std::any_cast<int>(tc.metadata.at("recall_point"));
        recall_points.insert(recall_point);
    }

    EXPECT_TRUE(recall_points.find(10) != recall_points.end());
    EXPECT_TRUE(recall_points.find(25) != recall_points.end());
    EXPECT_TRUE(recall_points.find(50) != recall_points.end());
}

// ============================================================================
// BenchmarkSuite Tests
// ============================================================================

TEST(BenchmarkSuiteTest, AddBenchmark) {
    BenchmarkSuite suite;
    auto benchmark = std::make_shared<SimpleQABenchmark>();

    suite.add_benchmark(benchmark);

    auto benchmarks = suite.get_benchmarks();
    EXPECT_EQ(benchmarks.size(), 1);
    EXPECT_TRUE(benchmarks.find("simple_qa") != benchmarks.end());
}

TEST(BenchmarkSuiteTest, GetBenchmark) {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(1000, 3));

    auto simple_qa = suite.get_benchmark("simple_qa");
    ASSERT_TRUE(simple_qa.has_value());
    EXPECT_EQ(simple_qa.value()->name(), "simple_qa");

    auto not_found = suite.get_benchmark("nonexistent");
    EXPECT_FALSE(not_found.has_value());
}

TEST(BenchmarkSuiteTest, GenerateAllTestCases) {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(500, 2));

    auto future = suite.generate_all_test_cases();
    auto all_cases = future.get();

    // SimpleQA has 5 cases, NeedleInHaystack has 2
    EXPECT_EQ(all_cases.size(), 7);
}

TEST(BenchmarkSuiteTest, GenerateTestCasesByTags) {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());

    auto future = suite.generate_test_cases_by_tags(std::vector<std::string>{"math"});
    auto filtered = future.get();

    // Should only get math-tagged cases
    EXPECT_GE(filtered.size(), 1);
    for (const auto& tc : filtered) {
        EXPECT_TRUE(tc.has_tag("math"));
    }
}

TEST(BenchmarkSuiteTest, GetSummary) {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(500, 2));

    auto future = suite.get_summary();
    auto summary = future.get();

    EXPECT_TRUE(summary.contains("simple_qa"));
    EXPECT_TRUE(summary.contains("needle_in_haystack_500"));
    EXPECT_TRUE(summary.contains("total_test_cases"));
    EXPECT_TRUE(summary.contains("benchmark_count"));

    EXPECT_EQ(summary["benchmark_count"].get<int>(), 2);
    EXPECT_EQ(summary["total_test_cases"].get<int>(), 7);
}

TEST(BenchmarkSuiteTest, StandardSuite) {
    auto suite = BenchmarkSuite::standard();

    auto benchmarks = suite.get_benchmarks();
    EXPECT_GE(benchmarks.size(), 3);

    // Should contain SimpleQA, NeedleInHaystack, and InformationRetention
    EXPECT_TRUE(benchmarks.find("simple_qa") != benchmarks.end());
}

TEST(BenchmarkSuiteTest, QuickSuite) {
    auto suite = BenchmarkSuite::quick();

    auto benchmarks = suite.get_benchmarks();
    EXPECT_EQ(benchmarks.size(), 2);

    // Should contain SimpleQA and small NeedleInHaystack
    EXPECT_TRUE(benchmarks.find("simple_qa") != benchmarks.end());

    // Quick suite should generate cases quickly
    auto future = suite.generate_all_test_cases();
    auto cases = future.get();
    EXPECT_GE(cases.size(), 5);  // At least SimpleQA's 5 cases
}

TEST(BenchmarkSuiteTest, ExtremeSuite) {
    auto suite = BenchmarkSuite::extreme_scale();

    auto benchmarks = suite.get_benchmarks();
    EXPECT_GE(benchmarks.size(), 3);

    // Should contain ExtremeScale, large InformationRetention, large NeedleInHaystack
    EXPECT_TRUE(benchmarks.find("extreme_scale") != benchmarks.end());
}

// ============================================================================
// Integration Tests
// ============================================================================

TEST(BenchmarkIntegrationTest, EndToEndStandardSuite) {
    auto suite = BenchmarkSuite::standard();

    // Generate all test cases
    auto cases = suite.generate_all_test_cases().get();
    EXPECT_GT(cases.size(), 10);

    // Verify all cases are valid
    for (const auto& tc : cases) {
        EXPECT_FALSE(tc.input.empty());
        EXPECT_FALSE(tc.tags.empty());
    }

    // Get summary
    auto summary = suite.get_summary().get();
    EXPECT_TRUE(summary.contains("total_test_cases"));
    EXPECT_EQ(summary["total_test_cases"].get<size_t>(), cases.size());
}

TEST(BenchmarkIntegrationTest, FilterByMultipleTags) {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());

    // Filter by tags that should match arithmetic case
    auto cases = suite.generate_test_cases_by_tags(
        std::vector<std::string>{"math", "easy"}
    ).get();

    // Should get at least the arithmetic case
    EXPECT_GE(cases.size(), 1);

    for (const auto& tc : cases) {
        EXPECT_TRUE(tc.has_tag("math"));
        EXPECT_TRUE(tc.has_tag("easy"));
    }
}

TEST(BenchmarkIntegrationTest, ParallelGeneration) {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(500, 2));
    suite.add_benchmark(std::make_shared<InformationRetentionBenchmark>(10, std::vector<size_t>{5, 10}));

    // Generate all in parallel
    auto future = suite.generate_all_test_cases();
    auto cases = future.get();

    // Should have cases from all benchmarks
    EXPECT_GT(cases.size(), 5);  // At minimum SimpleQA's 5 cases

    // Verify we have cases from different benchmarks
    bool has_qa = false;
    bool has_retrieval = false;
    bool has_retention = false;

    for (const auto& tc : cases) {
        if (tc.has_tag("arithmetic")) has_qa = true;
        if (tc.has_tag("needle_in_haystack")) has_retrieval = true;
        if (tc.has_tag("retention")) has_retention = true;
    }

    EXPECT_TRUE(has_qa);
    EXPECT_TRUE(has_retrieval);
    EXPECT_TRUE(has_retention);
}
