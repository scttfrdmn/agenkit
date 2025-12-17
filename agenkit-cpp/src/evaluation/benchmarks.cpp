/**
 * @file benchmarks.cpp
 * @brief Implementation of benchmark framework
 */

#include "agenkit/evaluation/benchmarks.hpp"
#include <algorithm>
#include <sstream>
#include <random>
#include <cmath>

namespace agenkit {
namespace evaluation {

// ============================================================================
// TestCase Implementation
// ============================================================================

bool TestCase::validate(const std::string& actual) const {
    if (std::holds_alternative<std::string>(expected)) {
        // Exact string match
        return std::get<std::string>(expected) == actual;
    } else {
        // Custom validation function
        auto validator = std::get<std::function<bool(const std::string&)>>(expected);
        return validator(actual);
    }
}

bool TestCase::has_tag(const std::string& tag) const {
    return std::find(tags.begin(), tags.end(), tag) != tags.end();
}

nlohmann::json TestCase::to_json() const {
    nlohmann::json j;
    j["input"] = input;

    // Serialize expected (only string variant, functions can't be serialized)
    if (std::holds_alternative<std::string>(expected)) {
        j["expected"] = std::get<std::string>(expected);
        j["expected_type"] = "string";
    } else {
        j["expected_type"] = "function";
    }

    // Serialize metadata (simplified - only string values)
    nlohmann::json metadata_json = nlohmann::json::object();
    for (const auto& [key, value] : metadata) {
        if (value.type() == typeid(std::string)) {
            metadata_json[key] = std::any_cast<std::string>(value);
        } else if (value.type() == typeid(int)) {
            metadata_json[key] = std::any_cast<int>(value);
        } else if (value.type() == typeid(double)) {
            metadata_json[key] = std::any_cast<double>(value);
        } else if (value.type() == typeid(bool)) {
            metadata_json[key] = std::any_cast<bool>(value);
        }
    }
    j["metadata"] = metadata_json;
    j["tags"] = tags;

    return j;
}

TestCase TestCase::from_json(const nlohmann::json& j) {
    std::string input_str = j.at("input").get<std::string>();
    std::string expected_type = j.value("expected_type", "string");

    TestCase tc(input_str, "");  // Default construction

    if (expected_type == "string") {
        tc.expected = j.at("expected").get<std::string>();
    }
    // Note: functions can't be deserialized, will remain as empty string

    // Deserialize metadata
    if (j.contains("metadata")) {
        for (auto it = j["metadata"].begin(); it != j["metadata"].end(); ++it) {
            if (it.value().is_string()) {
                tc.metadata[it.key()] = it.value().get<std::string>();
            } else if (it.value().is_number_integer()) {
                tc.metadata[it.key()] = it.value().get<int>();
            } else if (it.value().is_number_float()) {
                tc.metadata[it.key()] = it.value().get<double>();
            } else if (it.value().is_boolean()) {
                tc.metadata[it.key()] = it.value().get<bool>();
            }
        }
    }

    if (j.contains("tags")) {
        tc.tags = j["tags"].get<std::vector<std::string>>();
    }

    return tc;
}

// ============================================================================
// SimpleQABenchmark Implementation
// ============================================================================

std::string SimpleQABenchmark::name() const {
    return "simple_qa";
}

std::string SimpleQABenchmark::description() const {
    return "Basic Q&A benchmark testing factual knowledge, arithmetic, and common sense";
}

std::future<std::vector<TestCase>> SimpleQABenchmark::generate_test_cases() {
    return std::async(std::launch::async, []() {
        std::vector<TestCase> cases;

        // Test 1: Arithmetic
        TestCase case1("What is 2+2?", [](const std::string& output) {
            // Accept "4", "four", or any output containing 4
            return output.find("4") != std::string::npos ||
                   output.find("four") != std::string::npos;
        });
        case1.tags = {"math", "arithmetic", "easy"};
        case1.metadata["difficulty"] = std::string("easy");
        case1.metadata["category"] = std::string("math");
        cases.push_back(case1);

        // Test 2: Geography
        TestCase case2("What is the capital of France?", [](const std::string& output) {
            std::string lower = output;
            std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
            return lower.find("paris") != std::string::npos;
        });
        case2.tags = {"knowledge", "geography", "easy"};
        case2.metadata["difficulty"] = std::string("easy");
        case2.metadata["category"] = std::string("geography");
        cases.push_back(case2);

        // Test 3: Observation
        TestCase case3("What color is the sky?", [](const std::string& output) {
            std::string lower = output;
            std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
            return lower.find("blue") != std::string::npos;
        });
        case3.tags = {"knowledge", "observation", "easy"};
        case3.metadata["difficulty"] = std::string("easy");
        case3.metadata["category"] = std::string("observation");
        cases.push_back(case3);

        // Test 4: Counting
        TestCase case4("How many days are in a week?", [](const std::string& output) {
            return output.find("7") != std::string::npos ||
                   output.find("seven") != std::string::npos;
        });
        case4.tags = {"knowledge", "counting", "easy"};
        case4.metadata["difficulty"] = std::string("easy");
        case4.metadata["category"] = std::string("counting");
        cases.push_back(case4);

        // Test 5: Chemistry
        TestCase case5("What is water made of?", [](const std::string& output) {
            std::string lower = output;
            std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
            return (lower.find("h2o") != std::string::npos ||
                    lower.find("hydrogen") != std::string::npos) &&
                   (lower.find("oxygen") != std::string::npos);
        });
        case5.tags = {"knowledge", "chemistry", "medium"};
        case5.metadata["difficulty"] = std::string("medium");
        case5.metadata["category"] = std::string("chemistry");
        cases.push_back(case5);

        return cases;
    });
}

// ============================================================================
// NeedleInHaystackBenchmark Implementation
// ============================================================================

NeedleInHaystackBenchmark::NeedleInHaystackBenchmark(
    size_t context_length,
    size_t needle_count,
    size_t haystack_multiplier
)
    : context_length_(context_length),
      needle_count_(needle_count),
      haystack_multiplier_(haystack_multiplier) {}

std::string NeedleInHaystackBenchmark::name() const {
    return "needle_in_haystack_" + std::to_string(context_length_ / 1000) + "k";
}

std::string NeedleInHaystackBenchmark::description() const {
    std::ostringstream oss;
    oss << "Retrieval benchmark with " << needle_count_ << " needles in "
        << context_length_ << " token context";
    return oss.str();
}

std::future<std::vector<TestCase>> NeedleInHaystackBenchmark::generate_test_cases() {
    return std::async(std::launch::async, [this]() {
        std::vector<TestCase> cases;
        std::vector<std::string> needles;

        // Generate needles
        for (size_t i = 0; i < needle_count_; ++i) {
            needles.push_back(generate_needle(i));
        }

        // Calculate tokens per section
        size_t total_needle_tokens = 0;
        for (const auto& needle : needles) {
            total_needle_tokens += estimate_tokens(needle);
        }
        size_t haystack_tokens = total_needle_tokens * haystack_multiplier_;
        size_t tokens_per_section = haystack_tokens / (needle_count_ + 1);

        // Build context by interleaving haystack and needles
        std::ostringstream context_builder;
        for (size_t i = 0; i < needle_count_; ++i) {
            context_builder << generate_haystack(tokens_per_section) << "\n\n";
            context_builder << needles[i] << "\n\n";
        }
        context_builder << generate_haystack(tokens_per_section);

        std::string context = context_builder.str();

        // Generate test cases for each needle
        for (size_t i = 0; i < needle_count_; ++i) {
            std::string question = "What is the secret code number " +
                                   std::to_string(i + 1) + "?";

            // Create validator that checks for the code in the output
            std::string expected_code = std::to_string((i + 1) * 1000 + 42);
            auto validator = [expected_code](const std::string& output) {
                return output.find(expected_code) != std::string::npos;
            };

            TestCase test_case(context + "\n\n" + question, validator);
            test_case.tags = {"retrieval", "needle_in_haystack"};
            test_case.metadata["context_length"] = static_cast<int>(estimate_tokens(context));
            test_case.metadata["needle_index"] = static_cast<int>(i);
            test_case.metadata["expected_code"] = expected_code;

            cases.push_back(test_case);
        }

        return cases;
    });
}

std::string NeedleInHaystackBenchmark::generate_haystack(size_t target_tokens) const {
    // Generate random filler text
    const std::vector<std::string> sentences = {
        "The quick brown fox jumps over the lazy dog.",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        "In a galaxy far far away, there lived a brave knight.",
        "The ancient forest whispered secrets of old.",
        "Technology advances at an unprecedented pace.",
        "Mountains rise majestically against the horizon.",
        "Rivers flow endlessly towards the sea.",
        "Cities pulse with energy and life.",
        "Stars twinkle in the night sky.",
        "Waves crash rhythmically on the shore."
    };

    std::ostringstream haystack;
    size_t current_tokens = 0;
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dist(0, sentences.size() - 1);

    while (current_tokens < target_tokens) {
        const std::string& sentence = sentences[dist(gen)];
        haystack << sentence << " ";
        current_tokens += estimate_tokens(sentence);
    }

    return haystack.str();
}

std::string NeedleInHaystackBenchmark::generate_needle(size_t index) const {
    std::ostringstream needle;
    needle << "IMPORTANT: The secret code number " << (index + 1)
           << " is " << ((index + 1) * 1000 + 42) << ". "
           << "Remember this code for later retrieval.";
    return needle.str();
}

size_t NeedleInHaystackBenchmark::estimate_tokens(const std::string& text) const {
    // Rough approximation: 4 characters ≈ 1 token
    return text.length() / 4;
}

// ============================================================================
// ExtremeScaleBenchmark Implementation
// ============================================================================

ExtremeScaleBenchmark::ExtremeScaleBenchmark(
    const std::vector<size_t>& test_lengths,
    size_t needles_per_length
)
    : test_lengths_(test_lengths),
      needles_per_length_(needles_per_length) {}

std::string ExtremeScaleBenchmark::name() const {
    return "extreme_scale";
}

std::string ExtremeScaleBenchmark::description() const {
    std::ostringstream oss;
    oss << "Extreme-scale benchmark testing at ";
    for (size_t i = 0; i < test_lengths_.size(); ++i) {
        if (i > 0) {
            oss << ", ";
        }
        oss << (test_lengths_[i] / 1000000) << "M";
    }
    oss << " tokens with " << needles_per_length_ << " needles each";
    return oss.str();
}

std::future<std::vector<TestCase>> ExtremeScaleBenchmark::generate_test_cases() {
    return std::async(std::launch::async, [this]() {
        std::vector<TestCase> all_cases;

        for (size_t length : test_lengths_) {
            auto cases = generate_for_length(length);
            all_cases.insert(all_cases.end(), cases.begin(), cases.end());
        }

        return all_cases;
    });
}

std::vector<TestCase> ExtremeScaleBenchmark::generate_for_length(size_t length) {
    // For extreme scale, we use NeedleInHaystack as a building block
    NeedleInHaystackBenchmark needle_benchmark(length, needles_per_length_, 10);
    auto future = needle_benchmark.generate_test_cases();
    auto cases = future.get();

    // Add extreme_scale tag and update metadata
    for (auto& test_case : cases) {
        test_case.tags.push_back("extreme_scale");
        test_case.metadata["test_length"] = static_cast<int>(length);
    }

    return cases;
}

// ============================================================================
// InformationRetentionBenchmark Implementation
// ============================================================================

InformationRetentionBenchmark::InformationRetentionBenchmark(
    size_t conversation_length,
    const std::vector<size_t>& recall_points
)
    : conversation_length_(conversation_length),
      recall_points_(recall_points) {}

std::string InformationRetentionBenchmark::name() const {
    return "information_retention_" + std::to_string(conversation_length_);
}

std::string InformationRetentionBenchmark::description() const {
    std::ostringstream oss;
    oss << "Multi-turn conversation with " << conversation_length_
        << " turns, testing recall at " << recall_points_.size() << " points";
    return oss.str();
}

std::future<std::vector<TestCase>> InformationRetentionBenchmark::generate_test_cases() {
    return std::async(std::launch::async, [this]() {
        std::vector<TestCase> cases;
        std::vector<std::string> facts;

        // Generate conversation with embedded facts
        std::string conversation = generate_conversation(conversation_length_, facts);

        // Generate test cases for each recall point
        for (size_t recall_point : recall_points_) {
            if (facts.empty() || recall_point > conversation_length_) {
                continue;  // Skip if no facts or recall point beyond conversation
            }

            // Pick a fact to recall from before this point
            size_t fact_index = (recall_point > 0) ? (recall_point - 1) % facts.size() : 0;
            const std::string& fact = facts[fact_index];

            std::string question = "What was mentioned earlier about topic " +
                                   std::to_string(fact_index + 1) + "?";

            // Create validator
            auto validator = [fact](const std::string& output) {
                // Check if output contains key terms from the fact
                std::string lower_output = output;
                std::string lower_fact = fact;
                std::transform(lower_output.begin(), lower_output.end(),
                              lower_output.begin(), ::tolower);
                std::transform(lower_fact.begin(), lower_fact.end(),
                              lower_fact.begin(), ::tolower);

                // Simple heuristic: check if at least 2 words from fact appear in output
                std::istringstream iss(lower_fact);
                std::vector<std::string> fact_words;
                std::string word;
                while (iss >> word) {
                    if (word.length() > 4) {  // Only significant words
                        fact_words.push_back(word);
                    }
                }

                int matches = 0;
                for (const auto& fw : fact_words) {
                    if (lower_output.find(fw) != std::string::npos) {
                        matches++;
                    }
                }

                return matches >= 2 || (fact_words.size() <= 2 && matches >= 1);
            };

            TestCase test_case(conversation + "\n\n" + question, validator);
            test_case.tags = {"retention", "multi_turn", "memory"};
            test_case.metadata["conversation_length"] = static_cast<int>(conversation_length_);
            test_case.metadata["recall_point"] = static_cast<int>(recall_point);
            test_case.metadata["fact_index"] = static_cast<int>(fact_index);

            cases.push_back(test_case);
        }

        return cases;
    });
}

std::string InformationRetentionBenchmark::generate_conversation(
    size_t turns,
    std::vector<std::string>& facts
) {
    std::ostringstream conversation;
    std::random_device rd;
    std::mt19937 gen(rd());

    const std::vector<std::string> filler_exchanges = {
        "User: How are you?\nAssistant: I'm doing well, thank you for asking!",
        "User: What's the weather like?\nAssistant: I don't have access to weather information.",
        "User: Tell me a joke.\nAssistant: Why did the programmer quit? They didn't get arrays!",
        "User: What time is it?\nAssistant: I don't have access to the current time.",
        "User: Can you help me?\nAssistant: Of course! I'm here to help."
    };

    // Insert facts at regular intervals
    size_t fact_interval = turns / 10;  // Approximately 10 facts
    if (fact_interval == 0) {
        fact_interval = 1;
    }

    for (size_t turn = 0; turn < turns; ++turn) {
        if (turn % fact_interval == 0 && facts.size() < 20) {
            // Insert a fact
            std::string fact = generate_fact(facts.size());
            facts.push_back(fact);
            conversation << "User: " << fact << "\n";
            conversation << "Assistant: I've noted that information about topic "
                        << (facts.size()) << ".\n\n";
        } else {
            // Insert filler
            std::uniform_int_distribution<> dist(0, filler_exchanges.size() - 1);
            conversation << filler_exchanges[dist(gen)] << "\n\n";
        }
    }

    return conversation.str();
}

std::string InformationRetentionBenchmark::generate_fact(size_t index) const {
    std::ostringstream fact;
    fact << "Remember that topic " << (index + 1) << " is about "
         << "specialized information regarding subject matter "
         << (index * 100 + 42) << " which involves detailed analysis "
         << "and comprehensive understanding.";
    return fact.str();
}

// ============================================================================
// BenchmarkSuite Implementation
// ============================================================================

void BenchmarkSuite::add_benchmark(std::shared_ptr<Benchmark> benchmark) {
    benchmarks_[benchmark->name()] = benchmark;
}

std::future<std::vector<TestCase>> BenchmarkSuite::generate_all_test_cases() {
    return std::async(std::launch::async, [this]() {
        std::vector<std::future<std::vector<TestCase>>> futures;

        // Launch all benchmarks in parallel
        for (auto& [name, benchmark] : benchmarks_) {
            futures.push_back(benchmark->generate_test_cases());
        }

        // Collect results
        std::vector<TestCase> all_cases;
        for (auto& future : futures) {
            auto cases = future.get();
            all_cases.insert(all_cases.end(), cases.begin(), cases.end());
        }

        return all_cases;
    });
}

std::map<std::string, std::shared_ptr<Benchmark>> BenchmarkSuite::get_benchmarks() const {
    return benchmarks_;
}

std::optional<std::shared_ptr<Benchmark>> BenchmarkSuite::get_benchmark(
    const std::string& name
) const {
    auto it = benchmarks_.find(name);
    if (it != benchmarks_.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::future<std::vector<TestCase>> BenchmarkSuite::generate_test_cases_by_tags(
    const std::vector<std::string>& tags
) {
    return std::async(std::launch::async, [this, tags]() {
        auto all_cases_future = generate_all_test_cases();
        auto all_cases = all_cases_future.get();

        std::vector<TestCase> filtered;
        for (const auto& test_case : all_cases) {
            bool has_all_tags = true;
            for (const auto& tag : tags) {
                if (!test_case.has_tag(tag)) {
                    has_all_tags = false;
                    break;
                }
            }
            if (has_all_tags) {
                filtered.push_back(test_case);
            }
        }

        return filtered;
    });
}

std::future<nlohmann::json> BenchmarkSuite::get_summary() {
    return std::async(std::launch::async, [this]() {
        nlohmann::json summary = nlohmann::json::object();
        std::vector<std::future<std::vector<TestCase>>> futures;
        std::vector<std::string> names;

        for (auto& [name, benchmark] : benchmarks_) {
            names.push_back(name);
            futures.push_back(benchmark->generate_test_cases());
        }

        size_t total_cases = 0;
        for (size_t i = 0; i < futures.size(); ++i) {
            auto cases = futures[i].get();
            summary[names[i]] = {
                {"test_case_count", cases.size()},
                {"description", benchmarks_[names[i]]->description()}
            };
            total_cases += cases.size();
        }

        summary["total_test_cases"] = total_cases;
        summary["benchmark_count"] = benchmarks_.size();

        return summary;
    });
}

BenchmarkSuite BenchmarkSuite::standard() {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(10000, 5));
    suite.add_benchmark(std::make_shared<InformationRetentionBenchmark>(
        50,
        std::vector<size_t>{10, 25, 50}
    ));
    return suite;
}

BenchmarkSuite BenchmarkSuite::extreme_scale() {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<ExtremeScaleBenchmark>(
        std::vector<size_t>{1000000, 10000000, 25000000},
        10
    ));
    suite.add_benchmark(std::make_shared<InformationRetentionBenchmark>(
        1000,
        std::vector<size_t>{100, 250, 500, 750, 1000}
    ));
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(1000000, 20));
    return suite;
}

BenchmarkSuite BenchmarkSuite::quick() {
    BenchmarkSuite suite;
    suite.add_benchmark(std::make_shared<SimpleQABenchmark>());
    suite.add_benchmark(std::make_shared<NeedleInHaystackBenchmark>(1000, 3));
    return suite;
}

}  // namespace evaluation
}  // namespace agenkit
