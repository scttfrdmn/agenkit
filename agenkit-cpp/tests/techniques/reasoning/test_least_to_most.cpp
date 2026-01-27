/**
 * @file test_least_to_most.cpp
 * @brief Tests for Least-to-Most reasoning technique
 */

#include <gtest/gtest.h>
#include "agenkit/techniques/reasoning/least_to_most.hpp"
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <memory>
#include <vector>
#include <string>

using namespace agenkit::techniques::reasoning;
using namespace agenkit::core;

/**
 * @brief Mock agent for testing
 */
class MockAgent : public Agent {
public:
    MockAgent(const std::vector<std::string>& responses)
        : responses_(responses), call_count_(0) {}

    std::string name() const override {
        return "mock_agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "testing"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        return std::async(std::launch::async, [this, msg = std::move(message)]() mutable {
            size_t idx = call_count_ % responses_.size();
            call_count_++;
            return Result<Message, AgentError>::ok(
                Message::with_text("assistant", responses_[idx])
            );
        });
    }

private:
    std::vector<std::string> responses_;
    size_t call_count_;
};

// Test basic Least-to-Most functionality
TEST(LeastToMostTest, BasicFunctionality) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results",
        "12",
        "10",
        "22"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Calculate 3*4 + 2*5");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "22");

    // Check metadata
    auto metadata = response.metadata();
    EXPECT_EQ(metadata["technique"].get<std::string>(), "least_to_most");
    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 3);

    // Check subproblems array
    EXPECT_TRUE(metadata.contains("subproblems"));
    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();
    EXPECT_EQ(subproblems.size(), 3);

    // Check solutions array
    EXPECT_TRUE(metadata.contains("subproblem_solutions"));
    auto solutions = metadata["subproblem_solutions"].get<std::vector<std::string>>();
    EXPECT_EQ(solutions.size(), 3);
}

// Test name and capabilities
TEST(LeastToMostTest, NameAndCapabilities) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{"response"});
    LeastToMostAgent ltm(mock);

    EXPECT_EQ(ltm.name(), "least_to_most");

    auto caps = ltm.capabilities();
    EXPECT_EQ(caps.size(), 5);
    EXPECT_NE(std::find(caps.begin(), caps.end(), "reasoning"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "decomposition"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "compositional_reasoning"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "least_to_most"), caps.end());
    EXPECT_NE(std::find(caps.begin(), caps.end(), "sequential_solving"), caps.end());
}

// Test decomposition with periods
TEST(LeastToMostTest, DecompositionWithPeriods) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First subproblem\n2. Second subproblem\n3. Third subproblem",
        "Solution 1",
        "Solution 2",
        "Solution 3"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Complex problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();

    EXPECT_EQ(subproblems[0], "First subproblem");
    EXPECT_EQ(subproblems[1], "Second subproblem");
    EXPECT_EQ(subproblems[2], "Third subproblem");
}

// Test decomposition with parentheses
TEST(LeastToMostTest, DecompositionWithParentheses) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1) First\n2) Second\n3) Third",
        "S1",
        "S2",
        "S3"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();

    EXPECT_EQ(subproblems[0], "First");
    EXPECT_EQ(subproblems[1], "Second");
    EXPECT_EQ(subproblems[2], "Third");
}

// Test sequential solving
TEST(LeastToMostTest, SequentialSolving) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Step A\n2. Step B",
        "Answer A",
        "Answer B"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto solutions = metadata["subproblem_solutions"].get<std::vector<std::string>>();

    EXPECT_EQ(solutions[0], "Answer A");
    EXPECT_EQ(solutions[1], "Answer B");
}

// Test final solution is last
TEST(LeastToMostTest, FinalSolutionIsLast) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Subproblem 1\n2. Subproblem 2",
        "Intermediate",
        "Final answer"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    EXPECT_EQ(response.content_as_str(), "Final answer");
    EXPECT_EQ(response.role(), "assistant");
}

// Test max_subproblems limit
TEST(LeastToMostTest, MaxSubproblemsLimit) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Sub 1\n2. Sub 2\n3. Sub 3\n4. Sub 4\n5. Sub 5\n6. Sub 6",
        "S1",
        "S2",
        "S3"
    });

    LeastToMostConfig config;
    config.max_subproblems = 3;
    LeastToMostAgent ltm(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 3);
    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();
    EXPECT_EQ(subproblems.size(), 3);
}

// Test custom decomposer
TEST(LeastToMostTest, CustomDecomposer) {
    auto custom_decomposer = [](const std::string& problem) -> std::vector<std::string> {
        return {
            "Custom step 1",
            "Custom step 2",
            "Custom step 3"
        };
    };

    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "Sol 1",
        "Sol 2",
        "Sol 3"
    });

    LeastToMostConfig config;
    config.decomposer = custom_decomposer;
    LeastToMostAgent ltm(mock, config);

    auto message = Message::with_text("user", "Any problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();

    EXPECT_EQ(subproblems[0], "Custom step 1");
    EXPECT_EQ(subproblems[1], "Custom step 2");
    EXPECT_EQ(subproblems[2], "Custom step 3");
}

// Test compose_solutions enabled
TEST(LeastToMostTest, ComposeSolutionsEnabled) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Sub 1\n2. Sub 2",
        "Solution 1",
        "Solution 2"
    });

    LeastToMostConfig config;
    config.compose_solutions = true;
    LeastToMostAgent ltm(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["compose_solutions"].get<bool>(), true);
}

// Test compose_solutions disabled
TEST(LeastToMostTest, ComposeSolutionsDisabled) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Sub 1\n2. Sub 2",
        "Solution 1",
        "Solution 2"
    });

    LeastToMostConfig config;
    config.compose_solutions = false;
    LeastToMostAgent ltm(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["compose_solutions"].get<bool>(), false);
}

// Test skip empty lines
TEST(LeastToMostTest, SkipEmptyLines) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First\n\n2. Second\n\n\n3. Third",
        "S1",
        "S2",
        "S3"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 3);
}

// Test atomic problem fallback
TEST(LeastToMostTest, AtomicProblemFallback) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "No valid decomposition",
        "Single solution"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Simple problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 1);

    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();
    EXPECT_EQ(subproblems[0], "Simple problem");

    EXPECT_EQ(response.content_as_str(), "Single solution");
}

// Test whitespace handling
TEST(LeastToMostTest, WhitespaceHandling) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "  1.   Trimmed   \n  2.   Also trimmed   ",
        "S1",
        "S2"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();
    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();

    EXPECT_EQ(subproblems[0], "Trimmed");
    EXPECT_EQ(subproblems[1], "Also trimmed");
}

// Test metadata includes all fields
TEST(LeastToMostTest, MetadataIncludesAllFields) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Calculate x\n2. Calculate y\n3. Combine results",
        "X",
        "Y",
        "XY"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Check all required metadata fields
    EXPECT_TRUE(metadata.contains("technique"));
    EXPECT_TRUE(metadata.contains("num_subproblems"));
    EXPECT_TRUE(metadata.contains("subproblems"));
    EXPECT_TRUE(metadata.contains("subproblem_solutions"));
    EXPECT_TRUE(metadata.contains("compose_solutions"));

    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();
    EXPECT_EQ(subproblems[0], "Calculate x");
    EXPECT_EQ(subproblems[1], "Calculate y");
    EXPECT_EQ(subproblems[2], "Combine results");
}

// Test empty problem string
TEST(LeastToMostTest, EmptyProblemString) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Sub",
        "Sol"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["technique"].get<std::string>(), "least_to_most");
}

// Test max_subproblems of 1
TEST(LeastToMostTest, MaxSubproblemsOne) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. A\n2. B\n3. C",
        "Only one"
    });

    LeastToMostConfig config;
    config.max_subproblems = 1;
    LeastToMostAgent ltm(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 1);

    auto subproblems = metadata["subproblems"].get<std::vector<std::string>>();
    EXPECT_EQ(subproblems.size(), 1);
}

// Test solution whitespace trimming
TEST(LeastToMostTest, SolutionWhitespaceTrimming) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. Sub",
        "   Solution with whitespace   "
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();

    EXPECT_EQ(response.content_as_str(), "Solution with whitespace");

    auto metadata = response.metadata();
    auto solutions = metadata["subproblem_solutions"].get<std::vector<std::string>>();
    EXPECT_EQ(solutions[0], "Solution with whitespace");
}

// Test multiline content parsing
TEST(LeastToMostTest, MultilineContentParsing) {
    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "1. First part\n   continued\n2. Second",
        "S1",
        "S2"
    });

    LeastToMostAgent ltm(mock);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Should only parse lines starting with numbers
    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 2);
}

// Test custom decomposer with max limit
TEST(LeastToMostTest, CustomDecomposerWithMaxLimit) {
    auto custom_decomposer = [](const std::string& problem) -> std::vector<std::string> {
        return {
            "Step 1",
            "Step 2",
            "Step 3",
            "Step 4",
            "Step 5"
        };
    };

    auto mock = std::make_shared<MockAgent>(std::vector<std::string>{
        "S1",
        "S2",
        "S3"
    });

    LeastToMostConfig config;
    config.decomposer = custom_decomposer;
    config.max_subproblems = 3;
    LeastToMostAgent ltm(mock, config);

    auto message = Message::with_text("user", "Problem");
    auto future = ltm.process(std::move(message));
    auto result = future.get();

    ASSERT_TRUE(result.is_ok());

    auto response = result.unwrap();
    auto metadata = response.metadata();

    // Should be limited to 3 even though custom decomposer returned 5
    EXPECT_EQ(metadata["num_subproblems"].get<size_t>(), 3);
}
