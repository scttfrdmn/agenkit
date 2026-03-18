# Building Production AI Agents in C++

A practical guide to building high-performance AI agents with agenkit-cpp. Each tutorial
is self-contained and buildable with CMake.

---

## Introduction: C++ Performance Advantages for AI Agents

C++ gives you maximum control over how your agent code runs:

- **Zero-overhead abstractions** — templates and `constexpr` compile away; you pay nothing
  at runtime for the abstractions you do not use.
- **Memory layout control** — place agents in contiguous arrays (struct-of-arrays) to
  maximise cache efficiency when processing many messages.
- **SIMD and hardware intrinsics** — directly use AVX-512 for batch embedding operations.
- **No GC pauses** — deterministic latency with RAII resource management and custom
  allocators.
- **25x faster than Python** in agenkit benchmarks for CPU-bound orchestration.

The trade-offs:
- Manual memory management risk (mitigated by RAII and smart pointers).
- Longer build cycles and more complex toolchain setup.
- Undefined behaviour for type punning, out-of-bounds access, etc.

For latency-critical inference servers, edge deployment, and embedded agent systems,
C++ is the highest-performance option.

### Prerequisites

```cmake
# CMakeLists.txt
find_package(agenkit REQUIRED)
find_package(GTest REQUIRED)

target_link_libraries(my_agent
    agenkit::agenkit
    GTest::GTest
    GTest::Main
)
```

C++20 is required. All examples build with:
```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build
```

---

## Tutorial 1: RAII Agent Resource Management

### Goal

Use `unique_ptr`, `shared_ptr`, and custom deleters to ensure agent resources are freed
deterministically — no leaks, no double-frees.

### unique_ptr for Exclusive Ownership

```cpp
#include <agenkit/agent.hpp>
#include <memory>
#include <iostream>

// RAII wrapper: connection is closed when the agent is destroyed.
class LLMAgent final : public agenkit::Agent {
public:
    explicit LLMAgent(std::string name, std::string endpoint)
        : name_(std::move(name))
        , conn_(connect(endpoint))  // RAII: establishes connection
    {}

    // No custom destructor needed — unique_ptr closes the connection.
    ~LLMAgent() override = default;

    // Non-copyable (unique_ptr is move-only).
    LLMAgent(const LLMAgent&) = delete;
    LLMAgent& operator=(const LLMAgent&) = delete;

    // Movable.
    LLMAgent(LLMAgent&&) noexcept = default;
    LLMAgent& operator=(LLMAgent&&) noexcept = default;

    [[nodiscard]] std::string_view name() const override { return name_; }
    [[nodiscard]] std::vector<std::string> capabilities() const override { return {"text"}; }

    [[nodiscard]] agenkit::Message process(const agenkit::Message& msg) const override;

private:
    std::string name_;
    std::unique_ptr<Connection> conn_;  // Freed when LLMAgent is destroyed.
};

// Factory function: caller gets exclusive ownership.
std::unique_ptr<LLMAgent> make_llm_agent(std::string name, std::string endpoint) {
    return std::make_unique<LLMAgent>(std::move(name), std::move(endpoint));
}

int main() {
    // Agent is destroyed (and connection closed) at end of scope.
    auto agent = make_llm_agent("gpt4o", "https://api.openai.com/v1");

    auto result = agent->process({.role = agenkit::Role::User, .content = "Hello"});
    std::cout << result.content << '\n';
}   // agent destroyed here — connection closed, memory freed.
```

### shared_ptr for Shared Ownership

```cpp
#include <memory>

// Multiple objects share a single LLM connection pool.
class ConnectionPool {
public:
    explicit ConnectionPool(int size) : size_(size) {}
    ~ConnectionPool() { /* closes all connections */ }

    [[nodiscard]] Connection* acquire();
    void release(Connection* c);

private:
    int size_;
    // implementation details
};

class PooledAgent : public agenkit::Agent {
public:
    // Many agents share the same pool.
    explicit PooledAgent(std::string name, std::shared_ptr<ConnectionPool> pool)
        : name_(std::move(name)), pool_(std::move(pool)) {}

    [[nodiscard]] agenkit::Message process(const agenkit::Message& msg) const override {
        auto* conn = pool_->acquire();
        // ... use conn ...
        pool_->release(conn);
        return {.role = agenkit::Role::Assistant, .content = "response"};
    }

    [[nodiscard]] std::string_view name() const override { return name_; }
    [[nodiscard]] std::vector<std::string> capabilities() const override { return {"text"}; }

private:
    std::string name_;
    std::shared_ptr<ConnectionPool> pool_;  // Pool lives as long as any agent does.
};

// Pool is destroyed only when the last agent is destroyed.
auto pool = std::make_shared<ConnectionPool>(10);
auto agent1 = std::make_unique<PooledAgent>("agent-1", pool);
auto agent2 = std::make_unique<PooledAgent>("agent-2", pool);
// pool use_count() == 3 (pool itself + agent1 + agent2).
```

### Custom Deleters for External Resources

```cpp
#include <memory>
#include <cstdlib>

// Custom deleter for a C-style GPU tensor buffer.
struct GpuBufferDeleter {
    void operator()(float* ptr) const noexcept {
        gpu_free(ptr);  // Platform-specific GPU free.
    }
};

using GpuBuffer = std::unique_ptr<float[], GpuBufferDeleter>;

class EmbeddingAgent : public agenkit::Agent {
public:
    explicit EmbeddingAgent(int embedding_dim)
        : dim_(embedding_dim)
        , buffer_(static_cast<float*>(gpu_alloc(embedding_dim * sizeof(float))))
    {}

    [[nodiscard]] agenkit::Message process(const agenkit::Message& msg) const override {
        // buffer_ is automatically freed when EmbeddingAgent is destroyed.
        compute_embedding(msg.content, buffer_.get(), dim_);
        return {.role = agenkit::Role::Assistant, .content = "embedding computed"};
    }

    [[nodiscard]] std::string_view name() const override { return "embedding"; }
    [[nodiscard]] std::vector<std::string> capabilities() const override { return {"embedding"}; }

private:
    int dim_;
    GpuBuffer buffer_;
};
```

### Scope Guard for Non-RAII Resources

```cpp
#include <functional>

// RAII scope guard for resources without smart pointer support.
class ScopeGuard {
public:
    explicit ScopeGuard(std::function<void()> fn) : fn_(std::move(fn)) {}
    ~ScopeGuard() noexcept { fn_(); }

    ScopeGuard(const ScopeGuard&) = delete;
    ScopeGuard& operator=(const ScopeGuard&) = delete;

private:
    std::function<void()> fn_;
};

agenkit::Message LLMAgent::process(const agenkit::Message& msg) const {
    conn_->begin_request();
    ScopeGuard guard([this] { conn_->end_request(); });  // Always called on return.

    // If an exception is thrown here, guard still calls end_request().
    auto response = conn_->send(msg.content);
    return {.role = agenkit::Role::Assistant, .content = std::move(response)};
}
```

### Key Takeaways

- Prefer `unique_ptr` for exclusive ownership; `shared_ptr` only when shared ownership
  is genuinely required (it has atomic reference counting overhead).
- Custom deleters let `unique_ptr`/`shared_ptr` manage any resource, not just heap memory.
- `ScopeGuard` (or `std::experimental::scope_exit`) handles cleanup for APIs that do
  not have RAII wrappers.
- Declare constructors `explicit` to prevent accidental implicit conversions.

---

## Tutorial 2: Template-Based Agent Composition

### Goal

Use variadic templates and CRTP (Curiously Recurring Template Pattern) to compose agents
and middleware at compile time with zero virtual dispatch overhead.

### Static Composition with Variadic Templates

```cpp
#include <tuple>
#include <utility>

// Compile-time sequential pipeline.
template <typename... Agents>
class StaticPipeline {
public:
    explicit StaticPipeline(Agents&&... agents)
        : agents_(std::forward<Agents>(agents)...) {}

    [[nodiscard]] agenkit::Message process(const agenkit::Message& msg) const {
        return process_impl(msg, std::index_sequence_for<Agents...>{});
    }

private:
    template <std::size_t... Is>
    [[nodiscard]] agenkit::Message process_impl(
        const agenkit::Message& msg,
        std::index_sequence<Is...>) const
    {
        agenkit::Message current = msg;
        // Fold expression: apply each agent in order.
        ((current = std::get<Is>(agents_).process(current)), ...);
        return current;
    }

    std::tuple<Agents...> agents_;
};

// Deduction guide so template arguments are inferred.
template <typename... Agents>
StaticPipeline(Agents&&...) -> StaticPipeline<std::decay_t<Agents>...>;

// Usage — no virtual dispatch, fully inlined:
StaticPipeline pipeline(EchoAgent{}, UpperAgent{}, CriticAgent{});
auto result = pipeline.process({.role = agenkit::Role::User, .content = "test"});
```

### CRTP for Zero-Cost Middleware

```cpp
// Base middleware via CRTP — no virtual functions needed.
template <typename Derived>
class AgentBase {
public:
    [[nodiscard]] agenkit::Message process(const agenkit::Message& msg) const {
        return static_cast<const Derived*>(this)->do_process(msg);
    }
};

// Retry CRTP mixin.
template <typename Inner>
class WithRetry : public AgentBase<WithRetry<Inner>> {
public:
    explicit WithRetry(Inner inner, int max_retries)
        : inner_(std::move(inner)), max_retries_(max_retries) {}

    [[nodiscard]] agenkit::Message do_process(const agenkit::Message& msg) const {
        for (int i = 0; i <= max_retries_; ++i) {
            try {
                return inner_.process(msg);
            } catch (const agenkit::TransientError& e) {
                if (i == max_retries_) throw;
                std::this_thread::sleep_for(std::chrono::milliseconds(100 * (1 << i)));
            }
        }
        throw agenkit::AgentError("retry limit exceeded");
    }

    [[nodiscard]] std::string_view name() const { return inner_.name(); }
    [[nodiscard]] std::vector<std::string> capabilities() const { return inner_.capabilities(); }

private:
    Inner inner_;
    int max_retries_;
};

// Timeout CRTP mixin.
template <typename Inner>
class WithTimeout : public AgentBase<WithTimeout<Inner>> {
public:
    explicit WithTimeout(Inner inner, std::chrono::milliseconds timeout)
        : inner_(std::move(inner)), timeout_(timeout) {}

    [[nodiscard]] agenkit::Message do_process(const agenkit::Message& msg) const {
        // std::async + wait_for for timeout.
        auto future = std::async(std::launch::async,
            [this, &msg] { return inner_.process(msg); });

        if (future.wait_for(timeout_) == std::future_status::timeout) {
            throw agenkit::TimeoutError(timeout_.count());
        }
        return future.get();
    }

    [[nodiscard]] std::string_view name() const { return inner_.name(); }
    [[nodiscard]] std::vector<std::string> capabilities() const { return inner_.capabilities(); }

private:
    Inner inner_;
    std::chrono::milliseconds timeout_;
};

// Compose at compile time — entirely stack-allocated, zero virtual dispatch:
auto agent = WithRetry(WithTimeout(LLMAgent{"gpt4o"}, 10s), 3);
auto result = agent.process({.role = agenkit::Role::User, .content = "Hello"});
```

### Concepts for Better Error Messages (C++20)

```cpp
#include <concepts>

template <typename T>
concept AgentConcept = requires(const T& a, const agenkit::Message& m) {
    { a.name() } -> std::convertible_to<std::string_view>;
    { a.capabilities() } -> std::same_as<std::vector<std::string>>;
    { a.process(m) } -> std::same_as<agenkit::Message>;
};

// Now the compiler emits a clear error if T doesn't satisfy AgentConcept.
template <AgentConcept T>
agenkit::Message safe_process(const T& agent, const agenkit::Message& msg) {
    return agent.process(msg);
}
```

### Key Takeaways

- Variadic templates + fold expressions enable compile-time pipelines with zero virtual
  dispatch.
- CRTP achieves static polymorphism: middleware composes at compile time, no vtable.
- C++20 Concepts replace SFINAE for readable compile-time constraints.
- Prefer stack allocation for short-lived agents; heap only when lifetime crosses scopes.

---

## Tutorial 3: std::async and Parallel Agents

### Goal

Use `std::future`, `std::promise`, and `std::packaged_task` to run agents concurrently
and manage results.

### std::async for Simple Concurrency

```cpp
#include <future>
#include <vector>

// Fan-out: run multiple agents concurrently.
std::vector<agenkit::Message> fan_out(
    const std::vector<std::unique_ptr<agenkit::Agent>>& agents,
    const agenkit::Message& msg)
{
    // Launch all agents asynchronously.
    std::vector<std::future<agenkit::Message>> futures;
    futures.reserve(agents.size());

    for (const auto& agent : agents) {
        futures.push_back(std::async(std::launch::async,
            [&agent, &msg] { return agent->process(msg); }));
    }

    // Collect results.
    std::vector<agenkit::Message> results;
    results.reserve(futures.size());

    for (auto& f : futures) {
        try {
            results.push_back(f.get());  // Blocks until this future is ready.
        } catch (const agenkit::AgentError& e) {
            std::cerr << "agent error: " << e.what() << '\n';
        }
    }
    return results;
}
```

### std::promise for Producer-Consumer

```cpp
#include <future>
#include <thread>

// Producer sets the promise; consumer awaits the future.
void producer_consumer_example() {
    std::promise<agenkit::Message> promise;
    std::future<agenkit::Message> future = promise.get_future();

    // Producer thread.
    std::thread producer([p = std::move(promise)]() mutable {
        try {
            auto agent = make_llm_agent("producer", "https://...");
            auto result = agent->process({
                .role = agenkit::Role::User,
                .content = "Generate a report"
            });
            p.set_value(std::move(result));
        } catch (...) {
            p.set_exception(std::current_exception());
        }
    });

    // Consumer: do other work while waiting.
    do_other_work();

    // Block until producer finishes.
    try {
        auto result = future.get();
        std::cout << result.content << '\n';
    } catch (const std::exception& e) {
        std::cerr << "producer failed: " << e.what() << '\n';
    }

    producer.join();
}
```

### std::packaged_task for Reusable Work Items

```cpp
#include <future>
#include <queue>
#include <mutex>
#include <condition_variable>

// Thread pool using packaged_task.
class AgentThreadPool {
public:
    explicit AgentThreadPool(int num_threads) {
        for (int i = 0; i < num_threads; ++i) {
            workers_.emplace_back([this] { worker_loop(); });
        }
    }

    ~AgentThreadPool() {
        {
            std::lock_guard lock(mutex_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& w : workers_) w.join();
    }

    // Submit a task; returns a future for the result.
    [[nodiscard]] std::future<agenkit::Message> submit(
        std::packaged_task<agenkit::Message()> task)
    {
        auto future = task.get_future();
        {
            std::lock_guard lock(mutex_);
            queue_.push(std::move(task));
        }
        cv_.notify_one();
        return future;
    }

private:
    void worker_loop() {
        while (true) {
            std::packaged_task<agenkit::Message()> task;
            {
                std::unique_lock lock(mutex_);
                cv_.wait(lock, [this] { return stop_ || !queue_.empty(); });
                if (stop_ && queue_.empty()) return;
                task = std::move(queue_.front());
                queue_.pop();
            }
            task();
        }
    }

    std::vector<std::thread> workers_;
    std::queue<std::packaged_task<agenkit::Message()>> queue_;
    std::mutex mutex_;
    std::condition_variable cv_;
    bool stop_{false};
};

// Usage:
AgentThreadPool pool(4);

auto future1 = pool.submit(std::packaged_task<agenkit::Message()>(
    [&] { return agent1.process(msg); }));

auto future2 = pool.submit(std::packaged_task<agenkit::Message()>(
    [&] { return agent2.process(msg); }));

auto r1 = future1.get();
auto r2 = future2.get();
```

### Key Takeaways

- `std::async(std::launch::async, ...)` guarantees a new thread; omitting `async` may
  defer execution (lazy evaluation).
- Never call `get()` on a future from the same thread that might produce it — deadlock.
- `std::packaged_task` wraps a callable so its result is accessible via `std::future`;
  useful for thread pools.
- `std::promise` is for one-shot producer-consumer; prefer `std::async` for simpler cases.

---

## Tutorial 4: GoogleTest Integration

### Goal

Write production-quality agent tests using GoogleTest fixtures, parameterized tests,
and death tests.

### Test Fixture

```cpp
#include <gtest/gtest.h>
#include <agenkit/agent.hpp>
#include <memory>

// Fixture: set up resources shared across all tests in the class.
class AgentTest : public ::testing::Test {
protected:
    void SetUp() override {
        agent_ = std::make_unique<EchoAgent>();
        user_msg_ = agenkit::Message{
            .role = agenkit::Role::User,
            .content = "Hello, world!",
        };
    }

    void TearDown() override {
        agent_.reset();
    }

    // Helper: assert that a Message is a valid assistant response.
    void AssertValidResponse(const agenkit::Message& msg) const {
        ASSERT_EQ(msg.role, agenkit::Role::Assistant);
        ASSERT_FALSE(msg.content.empty());
    }

    std::unique_ptr<EchoAgent> agent_;
    agenkit::Message user_msg_;
};

TEST_F(AgentTest, ProcessReturnsAssistantRole) {
    auto result = agent_->process(user_msg_);
    EXPECT_EQ(result.role, agenkit::Role::Assistant);
}

TEST_F(AgentTest, ProcessNonEmptyContent) {
    auto result = agent_->process(user_msg_);
    EXPECT_FALSE(result.content.empty());
}

TEST_F(AgentTest, NameMatchesExpected) {
    EXPECT_EQ(agent_->name(), "echo");
}

TEST_F(AgentTest, CapabilitiesIncludeText) {
    auto caps = agent_->capabilities();
    EXPECT_NE(std::find(caps.begin(), caps.end(), "text"), caps.end());
}
```

### Parameterized Tests

```cpp
struct AgentTestCase {
    std::string input;
    std::string expected_contains;
    bool should_fail;
};

class AgentParamTest : public ::testing::TestWithParam<AgentTestCase> {
protected:
    EchoAgent agent_;
};

TEST_P(AgentParamTest, HandlesInput) {
    const auto& tc = GetParam();
    agenkit::Message msg{.role = agenkit::Role::User, .content = tc.input};

    if (tc.should_fail) {
        EXPECT_THROW(agent_.process(msg), agenkit::InvalidMessageError);
    } else {
        auto result = agent_.process(msg);
        EXPECT_EQ(result.role, agenkit::Role::Assistant);
        if (!tc.expected_contains.empty()) {
            EXPECT_NE(result.content.find(tc.expected_contains), std::string::npos);
        }
    }
}

INSTANTIATE_TEST_SUITE_P(
    AgentInputs,
    AgentParamTest,
    ::testing::Values(
        AgentTestCase{"Hello", "", false},
        AgentTestCase{"A very long input: " + std::string(5000, 'x'), "", false},
        AgentTestCase{"", "", true},          // empty input should fail
        AgentTestCase{"héllo 🌍", "", false},  // unicode
        AgentTestCase{"Line1\nLine2", "", false}
    )
);
```

### Death Tests

```cpp
// Death tests verify that code terminates or throws as expected.
TEST_F(AgentTest, ProcessNullptrAgentDeathTest) {
    agenkit::Agent* null_agent = nullptr;
    EXPECT_DEATH(
        null_agent->process(user_msg_),
        ".*"  // regex matching any output
    );
}

// Test that assertions fire in debug builds.
TEST(AgentAssertTest, NegativeRetryCountAssertion) {
    EXPECT_DEBUG_DEATH(
        { RetryAgent agent(std::make_unique<EchoAgent>(), -1, 100ms); },
        "max_retries >= 0"
    );
}
```

### Mock Agents with gmock

```cpp
#include <gmock/gmock.h>

class MockAgent : public agenkit::Agent {
public:
    MOCK_METHOD(std::string_view, name, (), (const, override));
    MOCK_METHOD(std::vector<std::string>, capabilities, (), (const, override));
    MOCK_METHOD(agenkit::Message, process, (const agenkit::Message&), (const, override));
};

TEST(RetryAgentTest, RetriesOnTransientError) {
    auto mock = std::make_unique<MockAgent>();

    agenkit::Message success_msg{.role = agenkit::Role::Assistant, .content = "ok"};

    // Fail twice, then succeed.
    EXPECT_CALL(*mock, process(::testing::_))
        .WillOnce(::testing::Throw(agenkit::TransientError("temporary")))
        .WillOnce(::testing::Throw(agenkit::TransientError("temporary")))
        .WillOnce(::testing::Return(success_msg));

    EXPECT_CALL(*mock, name()).WillRepeatedly(::testing::Return("mock"));
    EXPECT_CALL(*mock, capabilities()).WillRepeatedly(::testing::Return(
        std::vector<std::string>{"text"}));

    RetryAgent retry(std::move(mock), 3, 0ms);
    auto result = retry.process({.role = agenkit::Role::User, .content = "test"});

    EXPECT_EQ(result.content, "ok");
}
```

### Key Takeaways

- `TEST_F` fixtures share setup/teardown across related tests — prefer over global state.
- `INSTANTIATE_TEST_SUITE_P` feeds data-driven cases without copy-pasting test bodies.
- Death tests (`EXPECT_DEATH`, `EXPECT_DEBUG_DEATH`) verify fatal error paths.
- gmock's `EXPECT_CALL` is more expressive than hand-rolled mock agents.

---

## Tutorial 5: RapidCheck Property Tests

### Goal

Use RapidCheck to find edge cases in agent logic through automated random input generation
and minimal counterexample shrinking.

### Setup

```cmake
find_package(RapidCheck REQUIRED)
target_link_libraries(my_tests rapidcheck GTest::GTest)
```

### Basic Property Tests

```cpp
#include <rapidcheck.h>
#include <rapidcheck/gtest.h>

// Property: EchoAgent always returns role=assistant.
RC_GTEST_PROP(EchoAgentProperties, AlwaysReturnsAssistantRole, ()) {
    EchoAgent agent;
    const auto content = *rc::gen::string<std::string>();
    RC_PRE(!content.empty());  // Precondition: non-empty input.

    agenkit::Message msg{.role = agenkit::Role::User, .content = content};
    auto result = agent.process(msg);

    RC_ASSERT(result.role == agenkit::Role::Assistant);
}

// Property: output content is non-empty for any non-empty input.
RC_GTEST_PROP(EchoAgentProperties, NonEmptyOutputForNonEmptyInput, ()) {
    EchoAgent agent;
    const auto content = *rc::gen::nonEmpty(rc::gen::string<std::string>());

    agenkit::Message msg{.role = agenkit::Role::User, .content = content};
    auto result = agent.process(msg);

    RC_ASSERT(!result.content.empty());
}

// Property: Sequential(echo, upper) output is uppercase.
RC_GTEST_PROP(SequentialProperties, UppercaseOutputIsUppercase, ()) {
    StaticPipeline<EchoAgent, UpperAgent> pipeline(EchoAgent{}, UpperAgent{});

    const auto content = *rc::gen::nonEmpty(rc::gen::string<char>());
    agenkit::Message msg{.role = agenkit::Role::User, .content = content};

    auto result = pipeline.process(msg);

    // Every alphabetic character in output must be uppercase.
    for (char c : result.content) {
        RC_ASSERT(!std::islower(c));
    }
}
```

### Custom Generators

```cpp
// Custom generator for agenkit::Message.
namespace rc {
    template <>
    struct Arbitrary<agenkit::Message> {
        static Gen<agenkit::Message> arbitrary() {
            return gen::build<agenkit::Message>(
                gen::set(&agenkit::Message::role,
                    gen::elementOf(std::vector<agenkit::Role>{
                        agenkit::Role::User,
                        agenkit::Role::Assistant,
                        agenkit::Role::System,
                    })),
                gen::set(&agenkit::Message::content,
                    gen::nonEmpty(gen::string<std::string>()))
            );
        }
    };
}

// Now rc::gen::arbitrary<agenkit::Message>() works.
RC_GTEST_PROP(CustomGenTest, MessageRoundTrip, ()) {
    const auto msg = *rc::gen::arbitrary<agenkit::Message>();
    EchoAgent agent;

    // Any valid message should produce a valid response.
    auto result = agent.process(msg);
    RC_ASSERT(result.role == agenkit::Role::Assistant);
    RC_ASSERT(!result.content.empty());
}
```

### Stateful Property Tests

```cpp
// Test that a stateful agent accumulates history correctly.
RC_GTEST_PROP(ConversationalAgentProperties, HistoryGrows, ()) {
    ConversationalAgent agent;

    const auto num_turns = *rc::gen::inRange(1, 10);
    const auto messages = *rc::gen::container<std::vector<std::string>>(
        num_turns, rc::gen::nonEmpty(rc::gen::string<std::string>())
    );

    for (const auto& content : messages) {
        agent.process({.role = agenkit::Role::User, .content = content});
    }

    RC_ASSERT(static_cast<int>(agent.history_size()) >= num_turns);
}
```

### Key Takeaways

- `RC_PRE(condition)` is like a `prop.Pre()` in other frameworks — skips the case if the
  precondition fails, rather than failing the test.
- `RC_ASSERT` integrates with RapidCheck's shrinking; counterexamples are minimised
  automatically.
- Specialise `rc::Arbitrary<T>` for your domain types to get clean test code.
- RapidCheck saves failed seeds in `.rcs-db/` for reproducible failures in CI.

---

## Next Steps

- **Reference**: `agenkit-cpp/docs/API.md` — Doxygen documentation
- **Examples**: `examples/cpp/` — 15+ runnable examples
- **Patterns**: `docs/PATTERNS.md` — canonical pattern catalogue (all languages)
- **Benchmarks**: `benchmarks/cpp/` — performance baselines

```bash
# Build and run all C++ tests
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
cd build && ctest --output-on-failure

# Run with AddressSanitizer for memory error detection
cmake -B build-asan -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined"
cmake --build build-asan
cd build-asan && ctest

# Run RapidCheck with more tests
RC_PARAMS="max_success=1000" ctest -R RapidCheck
```
