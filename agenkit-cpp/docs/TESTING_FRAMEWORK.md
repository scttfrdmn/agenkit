# C++ Testing Framework

## Current State

The C++ implementation has **150+ tests across 22 test suites** with solid coverage of core functionality. Basic mock agents (`MockAgent` and `FailingMockAgent`) are available in `tests/test_utils/mock_agent.hpp`.

> **Note:** Issue #545 tracks adding comprehensive test coverage (property-based tests, benchmark regression tests, and additional pattern tests). The framework described here reflects both current state and the planned direction.

**Test Coverage:**
- Core agent interface: 20+ tests
- Message handling: 25+ tests
- Patterns (Sequential, Parallel, Reflection, ReAct, etc.): 60+ tests
- Middleware (Retry, Circuit Breaker, Timeout, etc.): 30+ tests
- Observability (Tracing, Metrics, Logging, Audit): 63 tests
- HTTP transport: 15+ tests

---

## Test Setup

### CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.16)
project(my_agent_tests CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable testing
enable_testing()

# Find GoogleTest
find_package(GTest REQUIRED)

# Include agenkit
include(FetchContent)
FetchContent_Declare(
    agenkit
    GIT_REPOSITORY https://github.com/scttfrdmn/agenkit.git
    SOURCE_SUBDIR  agenkit-cpp
    GIT_TAG        v0.75.0
)
FetchContent_MakeAvailable(agenkit)

# Test executable
add_executable(test_my_agent
    tests/test_my_agent.cpp
    tests/test_patterns.cpp
)
target_link_libraries(test_my_agent
    PRIVATE
    agenkit::agenkit
    GTest::GTest
    GTest::Main
)

include(GoogleTest)
gtest_discover_tests(test_my_agent)
```

### Running Tests

```bash
cd build
cmake --build .
ctest --output-on-failure       # Run all tests
ctest -R "pattern"              # Run tests matching "pattern"
ctest -V                        # Verbose output
./tests/test_my_agent --gtest_filter="AgentTest.*"  # Filter directly
```

---

## Available Test Utilities

### MockAgent (`tests/test_utils/mock_agent.hpp`)

**MockAgent** — cycles through predefined responses:

```cpp
#include <agenkit/test_utils/mock_agent.hpp>
#include <gtest/gtest.h>

using namespace agenkit::core;
using namespace agenkit::test_utils;

TEST(MockAgentTest, CyclesThroughResponses) {
    MockAgent mock({"Response A", "Response B"});

    auto msg = Message::with_text("user", "Hello");

    // First call
    auto r1 = mock.process(msg).get();
    ASSERT_TRUE(r1.is_ok());
    EXPECT_EQ(r1.value().content().as_text(), "Response A");

    // Second call
    auto r2 = mock.process(msg).get();
    ASSERT_TRUE(r2.is_ok());
    EXPECT_EQ(r2.value().content().as_text(), "Response B");

    // Third call — cycles back
    auto r3 = mock.process(msg).get();
    ASSERT_TRUE(r3.is_ok());
    EXPECT_EQ(r3.value().content().as_text(), "Response A");

    // Inspect call count
    EXPECT_EQ(mock.call_count(), 3u);

    // Inspect received messages
    ASSERT_EQ(mock.received_messages().size(), 3u);
    EXPECT_EQ(mock.received_messages()[0].content().as_text(), "Hello");

    mock.reset_call_count();
    EXPECT_EQ(mock.call_count(), 0u);
}
```

**FailingMockAgent** — always returns a specified error:

```cpp
TEST(FailingMockAgentTest, AlwaysFails) {
    FailingMockAgent failing(AgentErrorCode::Timeout, "simulated timeout");

    auto msg = Message::with_text("user", "Hello");
    auto result = failing.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_err());
    EXPECT_EQ(result.error().code(), AgentErrorCode::Timeout);
    EXPECT_EQ(result.error().message(), "simulated timeout");
}
```

---

## Test Fixtures

Use `::testing::Test` subclasses to share setup across tests:

```cpp
class AgentPipelineTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create shared agents
        mock_llm_ = std::make_shared<MockAgent>(std::vector<std::string>{
            "First response",
            "Second response",
            "Third response",
        });

        failing_llm_ = std::make_shared<FailingMockAgent>(
            AgentErrorCode::NetworkError
        );
    }

    void TearDown() override {
        // Cleanup (RAII handles most — but you can reset state here)
        mock_llm_->reset_call_count();
    }

    std::shared_ptr<MockAgent>        mock_llm_;
    std::shared_ptr<FailingMockAgent> failing_llm_;
};

TEST_F(AgentPipelineTest, SequentialPassesOutputForward) {
    using namespace agenkit::patterns;

    std::vector<std::shared_ptr<Agent>> stages = {mock_llm_, mock_llm_};
    SequentialAgent pipeline(std::move(stages));

    auto msg    = Message::with_text("user", "Start");
    auto result = pipeline.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    // Second stage received the first stage's output
    EXPECT_EQ(mock_llm_->call_count(), 2u);
}

TEST_F(AgentPipelineTest, RetryRecoversFromTransientFailure) {
    using namespace agenkit::middleware;

    // After N failures, switch to success
    int call_num = 0;
    // Use a custom lambda agent for fine control
    auto flaky = std::make_shared<LambdaAgent>([&call_num](Message msg) {
        ++call_num;
        if (call_num < 3) {
            return Result<Message, AgentError>::err(
                AgentError{AgentErrorCode::NetworkError, "transient"}
            );
        }
        return Result<Message, AgentError>::ok(
            Message::with_text("assistant", "success")
        );
    });

    RetryDecorator retry(flaky, 3, 1);  // 1ms delay for fast tests

    auto msg    = Message::with_text("user", "test");
    auto result = retry.process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.value().content().as_text(), "success");
    EXPECT_EQ(call_num, 3);
}
```

---

## Mocking Agents with Google Mock (gmock)

For more expressive mocks using gmock:

```cpp
#include <gmock/gmock.h>
#include <agenkit/core/agent.hpp>

using namespace agenkit::core;
using ::testing::Return;
using ::testing::_;

class GmockAgent : public Agent {
public:
    MOCK_METHOD(std::string, name, (), (const, override));
    MOCK_METHOD(
        (std::future<Result<Message, AgentError>>),
        process,
        (Message message),
        (override)
    );
};

TEST(GmockTest, CallsProcessExactlyOnce) {
    auto mock = std::make_shared<GmockAgent>();

    auto expected_response = Message::with_text("assistant", "hello");

    EXPECT_CALL(*mock, name()).WillRepeatedly(Return("mock-agent"));
    EXPECT_CALL(*mock, process(_))
        .Times(1)
        .WillOnce([&expected_response](Message) {
            return make_ready_future(
                Result<Message, AgentError>::ok(expected_response)
            );
        });

    auto msg    = Message::with_text("user", "hi");
    auto result = mock->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.value().content().as_text(), "hello");
}
```

---

## Property-Based Tests with RapidCheck

Property-based testing generates random inputs to find edge cases.

> Issue #545 tracks implementing RapidCheck integration for agenkit-cpp.

### Setup

```cmake
include(FetchContent)
FetchContent_Declare(
    rapidcheck
    GIT_REPOSITORY https://github.com/emil-e/rapidcheck.git
    GIT_TAG        master
)
FetchContent_MakeAvailable(rapidcheck)

target_link_libraries(test_properties
    PRIVATE
    agenkit::agenkit
    rapidcheck
    rapidcheck_gtest
    GTest::GTest
)
```

### Example Property Tests

```cpp
#include <rapidcheck.h>
#include <rapidcheck/gtest.h>
#include <agenkit/core/message.hpp>
#include <agenkit/test_utils/mock_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::test_utils;

// Property: EchoAgent always returns the same text it received
RC_GTEST_PROP(EchoAgentProperties, ReturnsInputText, ()) {
    const auto text = *rc::gen::string<std::string>();
    RC_PRE(!text.empty());  // skip empty strings

    auto agent = EchoAgent{};
    auto msg   = Message::with_text("user", text);
    auto result = agent.process(std::move(msg)).get();

    RC_ASSERT(result.is_ok());
    RC_ASSERT(result.value().content().as_text() == text);
}

// Property: Message serializes and deserializes without loss
RC_GTEST_PROP(MessageProperties, JsonRoundTrip, ()) {
    const auto text    = *rc::gen::string<std::string>();
    const auto session = *rc::gen::string<std::string>();
    RC_PRE(!text.empty());

    auto msg = Message::with_text("user", text);
    msg.set_metadata("session_id", session);

    auto json     = msg.to_json();
    auto restored = Message::from_json(json);

    RC_ASSERT(restored.content().as_text() == text);
    RC_ASSERT(restored.get_metadata("session_id").value() == session);
    RC_ASSERT(msg == restored);
}

// Property: RetryDecorator never exceeds max_attempts
RC_GTEST_PROP(RetryProperties, NeverExceedsMaxAttempts, ()) {
    const int max_attempts = *rc::gen::inRange(1, 10);

    int call_count = 0;
    auto always_fail = std::make_shared<LambdaAgent>([&call_count](Message) {
        ++call_count;
        return Result<Message, AgentError>::err(
            AgentError{AgentErrorCode::NetworkError, "always fails"}
        );
    });

    RetryDecorator retry(always_fail, max_attempts, 0);  // 0ms delay
    auto msg    = Message::with_text("user", "test");
    auto result = retry.process(std::move(msg)).get();

    RC_ASSERT(result.is_err());
    RC_ASSERT(call_count <= max_attempts);
}

// Property: SequentialAgent always calls agents in order
RC_GTEST_PROP(SequentialProperties, CallsInOrder, ()) {
    const int n = *rc::gen::inRange(1, 6);

    std::vector<int> call_order;
    std::vector<std::shared_ptr<Agent>> agents;

    for (int i = 0; i < n; ++i) {
        agents.push_back(std::make_shared<LambdaAgent>(
            [i, &call_order](Message msg) {
                call_order.push_back(i);
                return Result<Message, AgentError>::ok(std::move(msg));
            }
        ));
    }

    SequentialAgent seq(std::move(agents));
    auto msg    = Message::with_text("user", "test");
    auto result = seq.process(std::move(msg)).get();

    RC_ASSERT(result.is_ok());
    RC_ASSERT(call_order.size() == static_cast<size_t>(n));
    for (int i = 0; i < n; ++i) {
        RC_ASSERT(call_order[i] == i);
    }
}
```

---

## Benchmark Tests with Google Benchmark

Track performance regressions and verify SLA targets.

### Setup

```cmake
include(FetchContent)
FetchContent_Declare(
    benchmark
    GIT_REPOSITORY https://github.com/google/benchmark.git
    GIT_TAG        v1.8.3
    CMAKE_ARGS     -DBENCHMARK_ENABLE_TESTING=OFF
)
FetchContent_MakeAvailable(benchmark)

add_executable(bench_agents benchmarks/bench_agents.cpp)
target_link_libraries(bench_agents
    PRIVATE
    agenkit::agenkit
    benchmark::benchmark
    benchmark::benchmark_main
)
```

### Example Benchmarks

```cpp
#include <benchmark/benchmark.h>
#include <agenkit/core/message.hpp>
#include <agenkit/test_utils/mock_agent.hpp>
#include <agenkit/patterns/sequential_agent.hpp>
#include <agenkit/patterns/parallel_agent.hpp>
#include <agenkit/middleware/retry_decorator.hpp>

using namespace agenkit::core;
using namespace agenkit::test_utils;
using namespace agenkit::patterns;

// Benchmark: EchoAgent throughput
static void BM_EchoAgent(benchmark::State& state) {
    EchoAgent agent;
    auto msg = Message::with_text("user", "Hello, benchmark!");

    for (auto _ : state) {
        auto result = agent.process(msg).get();
        benchmark::DoNotOptimize(result);
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_EchoAgent)->Iterations(10000);

// Benchmark: Sequential pipeline (N stages)
static void BM_SequentialAgent(benchmark::State& state) {
    int n = state.range(0);
    std::vector<std::shared_ptr<Agent>> agents;
    for (int i = 0; i < n; ++i) {
        agents.push_back(std::make_shared<MockAgent>("response"));
    }
    SequentialAgent seq(std::move(agents));

    auto msg = Message::with_text("user", "test");

    for (auto _ : state) {
        auto result = seq.process(msg).get();
        benchmark::DoNotOptimize(result);
    }

    state.SetLabel(std::to_string(n) + " stages");
}
BENCHMARK(BM_SequentialAgent)->Arg(1)->Arg(3)->Arg(5)->Arg(10);

// Benchmark: Parallel agent (N agents)
static void BM_ParallelAgent(benchmark::State& state) {
    int n = state.range(0);
    std::vector<std::shared_ptr<Agent>> agents;
    for (int i = 0; i < n; ++i) {
        agents.push_back(std::make_shared<MockAgent>("response"));
    }
    ParallelAgent par(std::move(agents));

    auto msg = Message::with_text("user", "test");

    for (auto _ : state) {
        auto result = par.process(msg).get();
        benchmark::DoNotOptimize(result);
    }

    state.SetLabel(std::to_string(n) + " agents");
}
BENCHMARK(BM_ParallelAgent)->Arg(2)->Arg(4)->Arg(8);

// Benchmark: Message JSON round-trip
static void BM_MessageJsonRoundTrip(benchmark::State& state) {
    auto msg = Message::with_text("user", "Hello!");
    msg.set_metadata("session_id", "abc-123");
    msg.set_metadata("user_id", "u-42");

    for (auto _ : state) {
        auto json     = msg.to_json();
        auto restored = Message::from_json(json);
        benchmark::DoNotOptimize(restored);
    }
}
BENCHMARK(BM_MessageJsonRoundTrip);
```

### Running Benchmarks

```bash
cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build .

# Run all benchmarks
./benchmarks/bench_agents

# Run with specific filter
./benchmarks/bench_agents --benchmark_filter="BM_Sequential.*"

# Output as JSON for CI tracking
./benchmarks/bench_agents --benchmark_format=json \
                           --benchmark_out=benchmark_results.json

# Compare against baseline
./benchmarks/bench_agents --benchmark_out=current.json
benchmark_tools compare baseline.json current.json
```

Expected output:
```
--------------------------------------------------------------
Benchmark                    Time             CPU   Iterations
--------------------------------------------------------------
BM_EchoAgent              1.23 us          1.21 us     578756
BM_SequentialAgent/1      1.45 us          1.43 us     489234
BM_SequentialAgent/3      3.21 us          3.18 us     220134
BM_SequentialAgent/5      5.12 us          5.08 us     137812
BM_ParallelAgent/2        0.98 us          0.95 us     736421
BM_ParallelAgent/4        1.21 us          1.18 us     593218
BM_MessageJsonRoundTrip   2.34 us          2.31 us     302415
```

---

## Related Issues

- #545 — Comprehensive C++ test coverage (property tests, benchmark regression tests)
- #436 — Mock LLMs for C++ (MockAgent completed)
- #438 — Cross-language API consistency tests

## Status

- MockAgent and FailingMockAgent implemented
- GoogleTest integration complete (22 suites, 150+ tests)
- Observability tests: 63 tests passing
- Property-based tests (RapidCheck): planned in #545
- Benchmark regression tracking: planned in #545
