# Getting Started with Agenkit-C++

A beginner-friendly guide to building AI agents with C++17.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Your First Agent](#your-first-agent)
- [Understanding Messages](#understanding-messages)
- [Modern C++17 Patterns](#modern-c17-patterns)
- [Error Handling](#error-handling)
- [LLM Adapters](#llm-adapters)
- [Adding Middleware](#adding-middleware)
- [Testing Your Agent](#testing-your-agent)
- [Next Steps](#next-steps)

---

## Prerequisites

You need:
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.16+
- Optional: vcpkg for dependency management

Check your compiler version:
```bash
g++ --version
# Should output GCC 7 or higher

clang++ --version
# Should output Clang 5 or higher
```

Check CMake:
```bash
cmake --version
# Should output cmake version 3.16 or higher
```

---

## Installation

### Option 1: vcpkg (Recommended)

vcpkg is the recommended way to manage C++ dependencies.

**Install vcpkg:**
```bash
git clone https://github.com/Microsoft/vcpkg.git ~/vcpkg
cd ~/vcpkg
./bootstrap-vcpkg.sh   # Linux/macOS
# or
.\bootstrap-vcpkg.bat  # Windows
```

**Install Agenkit dependencies:**
```bash
~/vcpkg/vcpkg install nlohmann-json cpp-httplib gtest
```

**Create your project's `CMakeLists.txt`:**
```cmake
cmake_minimum_required(VERSION 3.16)
project(my_agent_project CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# vcpkg integration
find_package(nlohmann_json REQUIRED)
find_package(httplib REQUIRED)

# FetchContent for agenkit
include(FetchContent)
FetchContent_Declare(
    agenkit
    GIT_REPOSITORY https://github.com/scttfrdmn/agenkit.git
    SOURCE_SUBDIR  agenkit-cpp
    GIT_TAG        v0.75.0
)
FetchContent_MakeAvailable(agenkit)

add_executable(my_agent src/main.cpp)
target_link_libraries(my_agent
    PRIVATE
    agenkit::agenkit
    nlohmann_json::nlohmann_json
)
```

**Build:**
```bash
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/scripts/buildsystems/vcpkg.cmake ..
cmake --build .
```

### Option 2: Building from Source

Clone the repository and build directly:

```bash
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-cpp

# Install dependencies
vcpkg install nlohmann-json cpp-httplib gtest

# Build
mkdir build && cd build
cmake -DCMAKE_TOOLCHAIN_FILE=~/vcpkg/scripts/buildsystems/vcpkg.cmake ..
cmake --build .

# Run tests to verify
ctest --output-on-failure
```

Expected output:
```
Test project .../agenkit-cpp/build
      Start  1: test_message
 1/17 Test  #1: test_message ..................... Passed    0.01 sec
      Start  2: test_agent
 2/17 Test  #2: test_agent ...................... Passed    0.02 sec
...
100% tests passed, 0 tests failed out of 17
```

### Option 3: System Package Manager

If your distribution provides the required libraries:

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential cmake nlohmann-json3-dev libgtest-dev
```

**macOS (Homebrew):**
```bash
brew install cmake nlohmann-json googletest
```

Then build without vcpkg:
```bash
mkdir build && cd build
cmake ..
cmake --build .
```

---

## Your First Agent

Let's build a simple echo agent step by step.

### Step 1: Create the Project

```bash
mkdir my-first-agent
cd my-first-agent
mkdir src build
```

### Step 2: Write the CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.16)
project(my_first_agent CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
FetchContent_Declare(
    agenkit
    GIT_REPOSITORY https://github.com/scttfrdmn/agenkit.git
    SOURCE_SUBDIR  agenkit-cpp
    GIT_TAG        v0.75.0
)
FetchContent_MakeAvailable(agenkit)

add_executable(my_first_agent src/main.cpp)
target_link_libraries(my_first_agent PRIVATE agenkit::agenkit)
```

### Step 3: Write the Agent Code

Create `src/main.cpp`:

```cpp
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>
#include <memory>
#include <string>

using namespace agenkit::core;

// Define a custom agent by inheriting from Agent
class EchoAgent : public Agent {
public:
    // Required: return a stable name for this agent
    std::string name() const override {
        return "echo-agent";
    }

    // Required: process a message and return a future result
    std::future<Result<Message, AgentError>>
    process(Message message) override {
        // Extract the text content from the input message
        auto input_text = message.content().as_text();

        // Create a response message
        auto response = Message::with_text("assistant", "Echo: " + input_text);

        // Return as a ready future (synchronous processing)
        return make_ready_future(
            Result<Message, AgentError>::ok(std::move(response))
        );
    }
};

int main() {
    std::cout << "=== My First Agent ===\n\n";

    // Create the agent (RAII: automatically cleaned up)
    auto agent = std::make_unique<EchoAgent>();

    // Create a user message
    auto message = Message::with_text("user", "Hello, agent!");

    std::cout << "User: " << message.content().as_text() << "\n";

    // Process the message (returns std::future)
    auto future = agent->process(std::move(message));

    // Wait for the result
    auto result = future.get();

    // Always check if the result succeeded
    if (result.is_ok()) {
        std::cout << "Agent: " << result.value().content().as_text() << "\n";
    } else {
        std::cerr << "Error: " << result.error().message() << "\n";
        return 1;
    }

    return 0;
}
```

### Step 4: Build and Run

```bash
cd build
cmake ..
cmake --build .
./my_first_agent
```

Expected output:
```
=== My First Agent ===

User: Hello, agent!
Agent: Echo: Hello, agent!
```

---

## Understanding Messages

`Message` is the fundamental unit of communication between agents. Every interaction passes through the Message type.

### Message Roles

Messages have four roles:

```cpp
// User input
auto user_msg = Message::with_text("user", "What is RAII?");

// Agent/model response
auto assistant_msg = Message::with_text("assistant", "RAII stands for...");

// System instructions (processed before user input)
auto system_msg = Message::with_text("system", "You are a helpful C++ expert.");

// Tool result
auto tool_msg = Message::with_text("tool", R"({"result": 42})");
```

### Message Content

Messages carry either text or structured JSON:

```cpp
// Text content
auto text_msg = Message::with_text("user", "Hello!");
std::string text = text_msg.content().as_text();

// Structured content (JSON)
nlohmann::json data = {{"query", "search term"}, {"max_results", 10}};
auto json_msg = Message::with_json("user", data);
nlohmann::json content = json_msg.content().as_json();

// Check content type
if (msg.content().is_text()) {
    // Handle text
} else if (msg.content().is_json()) {
    // Handle structured data
}
```

### Message Metadata

Metadata carries cross-cutting concerns like session IDs, trace context, and custom fields:

```cpp
auto msg = Message::with_text("user", "Hello!");

// Set metadata
msg.set_metadata("session_id", "abc-123");
msg.set_metadata("user_id", "user-42");
msg.set_metadata("request_id", "req-789");

// Get metadata
auto session = msg.get_metadata("session_id"); // returns std::optional<std::string>
if (session.has_value()) {
    std::cout << "Session: " << session.value() << "\n";
}

// Check metadata exists
if (msg.has_metadata("trace_id")) {
    // Trace context was propagated from upstream
}
```

### Copying vs Moving Messages

Messages follow C++ value semantics. Use `std::move` when the message is no longer needed:

```cpp
// Copy: preserves the original (more expensive)
auto copy = message;
agent1->process(copy);  // original still valid

// Move: transfers ownership (cheaper)
agent2->process(std::move(message));  // message is now in moved-from state
// Don't use message after this point
```

---

## Modern C++17 Patterns

Agenkit is designed around idiomatic C++17. Understanding these patterns helps you write correct agent code.

### RAII (Resource Acquisition Is Initialization)

All Agenkit resources follow RAII: construction acquires resources, destruction releases them.

```cpp
// RAII via unique_ptr: agent destroyed when scope exits
{
    auto agent = std::make_unique<EchoAgent>();
    auto result = agent->process(message).get();
    // agent destroyed here, all resources freed
}

// RAII via shared_ptr: agent destroyed when last reference drops
auto shared_agent = std::make_shared<EchoAgent>();
{
    auto also_owns = shared_agent;  // ref count: 2
}  // ref count: 1 -- agent still alive
// agent destroyed when shared_agent goes out of scope
```

### Smart Pointers

Choose the right ownership model:

```cpp
// unique_ptr: exclusive ownership (prefer this)
auto agent = std::make_unique<MyAgent>();
// Can't copy, only move
auto moved = std::move(agent);

// shared_ptr: shared ownership (use when needed)
auto llm = std::make_shared<ClaudeAgent>(config);
// Multiple agents can share the same LLM instance
auto agent_a = std::make_shared<ReflectionAgent>(llm, 3);
auto agent_b = std::make_shared<ReActAgent>(llm, tools, 5);
// llm reference count is 3 (llm + agent_a + agent_b)

// weak_ptr: non-owning reference (for caches, observers)
std::weak_ptr<Agent> weak_ref = shared_agent;
if (auto agent = weak_ref.lock()) {
    // agent is alive, use it
}
```

### std::optional for Nullable Values

Use `std::optional` instead of raw pointers or sentinel values:

```cpp
// Returning an optional result
std::optional<std::string> find_metadata(const Message& msg,
                                          const std::string& key) {
    return msg.get_metadata(key);  // already returns optional
}

// Using optional safely
auto session_id = find_metadata(msg, "session_id");
if (session_id.has_value()) {
    process_with_session(session_id.value());
}

// Or with value_or for defaults
auto model = find_metadata(msg, "model").value_or("gpt-4-turbo");
```

### std::variant for Type-Safe Unions

Message content uses `std::variant` internally for type safety:

```cpp
// Define a result that is either a string or an error
using ProcessResult = std::variant<std::string, AgentError>;

ProcessResult safe_process(const Message& msg) {
    if (msg.content().is_text()) {
        return msg.content().as_text();
    }
    return AgentError{"expected text content"};
}

// Use std::visit to handle all cases
auto result = safe_process(msg);
std::visit([](auto&& arg) {
    using T = std::decay_t<decltype(arg)>;
    if constexpr (std::is_same_v<T, std::string>) {
        std::cout << "Success: " << arg << "\n";
    } else if constexpr (std::is_same_v<T, AgentError>) {
        std::cerr << "Error: " << arg.message() << "\n";
    }
}, result);
```

### Structured Bindings

Use structured bindings for cleaner code:

```cpp
// Destructure pairs
auto [key, value] = std::make_pair("session_id", "abc-123");

// Destructure in range-based for loops
std::map<std::string, std::string> metadata = msg.metadata();
for (const auto& [key, value] : metadata) {
    std::cout << key << " = " << value << "\n";
}
```

### Lambdas with Captures

Lambdas are used extensively in async operations:

```cpp
// Capture by value (safe for async)
auto agent_name = std::string{"my-agent"};
auto future = std::async(std::launch::async, [agent_name, message]() {
    // agent_name is captured by value — safe in async context
    return process_message(agent_name, message);
});

// Capture shared_ptr for async lifetime management
auto shared_agent = std::make_shared<EchoAgent>();
auto future = std::async(std::launch::async, [shared_agent, message]() {
    // shared_agent keeps the agent alive until the lambda completes
    return shared_agent->process(message).get();
});
```

---

## Error Handling

Agenkit uses `Result<T, E>` for explicit error handling — no hidden exceptions from normal processing paths.

### The Result Type

```cpp
// Result<T, E> has two states: ok (success) or err (failure)
Result<Message, AgentError> result = agent->process(message).get();

// Always check before accessing value
if (result.is_ok()) {
    Message response = result.value();
    std::cout << response.content().as_text() << "\n";
} else {
    AgentError error = result.error();
    std::cerr << "Error: " << error.message() << "\n";
    std::cerr << "Code:  " << static_cast<int>(error.code()) << "\n";
}
```

### AgentError Codes

```cpp
enum class AgentErrorCode {
    Unknown,           // Unclassified error
    ProcessingFailed,  // General processing failure
    Timeout,           // Operation timed out
    RateLimited,       // API rate limit hit
    InvalidInput,      // Malformed input message
    NetworkError,      // HTTP/transport failure
    AuthFailed,        // Authentication error
    CircuitOpen,       // Circuit breaker is open
};
```

### Propagating Errors

Chain results without nested if-statements using early returns:

```cpp
Result<Message, AgentError> process_pipeline(Message input) {
    // Stage 1
    auto r1 = validator_->process(input).get();
    if (!r1.is_ok()) {
        return r1;  // propagate error
    }

    // Stage 2
    auto r2 = processor_->process(r1.value()).get();
    if (!r2.is_ok()) {
        return r2;
    }

    // Stage 3
    return formatter_->process(r2.value()).get();
}
```

### Exception Handling

Exceptions from LLM adapters and transport layers are caught internally and converted to `AgentError`. For your own code:

```cpp
std::future<Result<Message, AgentError>>
process(Message message) override {
    return std::async(std::launch::async, [this, message = std::move(message)]() {
        try {
            auto response = do_work(message);
            return Result<Message, AgentError>::ok(std::move(response));
        } catch (const std::invalid_argument& e) {
            return Result<Message, AgentError>::err(
                AgentError{AgentErrorCode::InvalidInput, e.what()}
            );
        } catch (const std::exception& e) {
            return Result<Message, AgentError>::err(
                AgentError{AgentErrorCode::ProcessingFailed, e.what()}
            );
        }
    });
}
```

---

## LLM Adapters

Connect your agents to real language models.

### Claude (Anthropic)

```cpp
#include <agenkit/adapters/claude_agent.hpp>
#include <cstdlib>

// Configure
adapters::ClaudeConfig config;
config.api_key = std::getenv("ANTHROPIC_API_KEY");
config.model   = adapters::ClaudeModels::SONNET_4;  // claude-sonnet-4-5

// Create adapter
auto llm = std::make_shared<adapters::ClaudeAgent>(config);

// Process a message
auto msg = Message::with_text("user", "Explain RAII in C++.");
auto result = llm->process(std::move(msg)).get();

if (result.is_ok()) {
    std::cout << result.value().content().as_text() << "\n";
}
```

### OpenAI

```cpp
#include <agenkit/adapters/openai_agent.hpp>

adapters::OpenAIConfig config;
config.api_key = std::getenv("OPENAI_API_KEY");
config.model   = "gpt-4-turbo";

auto llm = std::make_shared<adapters::OpenAIAgent>(config);
```

### Ollama (Local, Free)

```cpp
#include <agenkit/adapters/ollama_agent.hpp>

// Ollama runs locally — no API key needed
adapters::OllamaConfig config;
config.host  = "http://localhost:11434";
config.model = "llama3.3";

auto llm = std::make_shared<adapters::OllamaAgent>(config);
```

Start Ollama before running:
```bash
ollama serve               # Start the server
ollama pull llama3.3       # Download the model (one-time)
./build/my_agent           # Run your agent
```

### Parameter Validation

LLM adapters validate parameters at construction time:

```cpp
adapters::ClaudeConfig config;
config.api_key    = std::getenv("ANTHROPIC_API_KEY");
config.model      = adapters::ClaudeModels::SONNET_4;
config.temperature = 0.7;   // Valid: 0.0–1.0
config.max_tokens  = 4096;  // Valid: > 0

// Invalid values throw std::invalid_argument immediately:
// config.temperature = 2.5;  // throws: must be 0.0-1.0
// config.max_tokens  = 0;    // throws: must be > 0
```

---

## Adding Middleware

Middleware wraps agents to add cross-cutting concerns without modifying the agent itself.

### Retry

```cpp
#include <agenkit/middleware/retry_decorator.hpp>

auto base_agent = std::make_shared<ClaudeAgent>(config);

// Retry up to 3 times with exponential backoff starting at 100ms
auto resilient = std::make_shared<RetryDecorator>(
    base_agent,
    3,    // max_attempts
    100   // initial_delay_ms
);

auto result = resilient->process(message).get();
```

### Circuit Breaker

```cpp
#include <agenkit/middleware/circuit_breaker_decorator.hpp>

// Open the circuit after 5 consecutive failures
// Try to recover after 30 seconds
auto protected_agent = std::make_shared<CircuitBreakerDecorator>(
    base_agent,
    5,      // failure_threshold
    30000   // recovery_timeout_ms
);
```

### Timeout

```cpp
#include <agenkit/middleware/timeout_decorator.hpp>

// Fail if the agent does not respond within 5 seconds
auto bounded_agent = std::make_shared<TimeoutDecorator>(
    base_agent,
    5000  // timeout_ms
);
```

### Composing Middleware

Wrap in layers — outermost middleware runs first:

```cpp
auto base    = std::make_shared<ClaudeAgent>(config);

// Layer 1: retry transient failures
auto retried = std::make_shared<RetryDecorator>(base, 3, 100);

// Layer 2: open circuit on sustained failures
auto guarded = std::make_shared<CircuitBreakerDecorator>(retried, 5, 30000);

// Layer 3: enforce a time budget
auto bounded = std::make_shared<TimeoutDecorator>(guarded, 10000);

// All middleware applied: timeout > circuit breaker > retry > base agent
auto result = bounded->process(message).get();
```

### Rate Limiter

```cpp
#include <agenkit/middleware/rate_limiter_decorator.hpp>

// Allow at most 10 requests per second
auto throttled = std::make_shared<RateLimiterDecorator>(
    base_agent,
    10,     // requests_per_window
    1000    // window_ms
);
```

### Logging Middleware

```cpp
#include <agenkit/middleware/logging_decorator.hpp>

auto logged = std::make_shared<LoggingDecorator>(
    base_agent,
    LogLevel::Info
);
```

---

## Testing Your Agent

### Setting Up GoogleTest

Add to your `CMakeLists.txt`:

```cmake
enable_testing()

find_package(GTest REQUIRED)

add_executable(test_my_agent tests/test_my_agent.cpp)
target_link_libraries(test_my_agent
    PRIVATE
    agenkit::agenkit
    GTest::GTest
    GTest::Main
)

include(GoogleTest)
gtest_discover_tests(test_my_agent)
```

### Writing Your First Test

```cpp
#include <gtest/gtest.h>
#include <agenkit/core/message.hpp>
#include "my_agent.hpp"

using namespace agenkit::core;

class EchoAgentTest : public ::testing::Test {
protected:
    void SetUp() override {
        agent_ = std::make_unique<EchoAgent>();
    }

    std::unique_ptr<EchoAgent> agent_;
};

TEST_F(EchoAgentTest, ReturnsEchoOfInput) {
    auto msg = Message::with_text("user", "hello");
    auto result = agent_->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.value().content().as_text(), "Echo: hello");
}

TEST_F(EchoAgentTest, HasCorrectName) {
    EXPECT_EQ(agent_->name(), "echo-agent");
}

TEST_F(EchoAgentTest, ResponseRoleIsAssistant) {
    auto msg = Message::with_text("user", "test");
    auto result = agent_->process(std::move(msg)).get();

    ASSERT_TRUE(result.is_ok());
    EXPECT_EQ(result.value().role(), "assistant");
}
```

### Running Tests

```bash
cd build
cmake --build .
ctest --output-on-failure

# Or run a specific test binary
./tests/test_my_agent
./tests/test_my_agent --gtest_filter="EchoAgentTest.*"
```

---

## Next Steps

1. **Explore Patterns**: See [PATTERNS.md](PATTERNS.md) for all 11 agent patterns with full examples
2. **Read the API Reference**: See [API.md](API.md) for complete class and function documentation
3. **Add Observability**: See [OBSERVABILITY.md](OBSERVABILITY.md) for distributed tracing and metrics
4. **Check Examples**: `agenkit-cpp/examples/` has production-quality examples
5. **Build Guide**: See [BUILD.md](BUILD.md) for advanced build options
6. **Benchmarks**: See [BENCHMARKS.md](BENCHMARKS.md) for performance characteristics
7. **Migration**: See [MIGRATION.md](MIGRATION.md) to migrate from another language

---

## Quick Reference

```cpp
// Core includes
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>

// LLM adapters
#include <agenkit/adapters/claude_agent.hpp>
#include <agenkit/adapters/openai_agent.hpp>
#include <agenkit/adapters/ollama_agent.hpp>

// Middleware
#include <agenkit/middleware/retry_decorator.hpp>
#include <agenkit/middleware/timeout_decorator.hpp>
#include <agenkit/middleware/circuit_breaker_decorator.hpp>
#include <agenkit/middleware/rate_limiter_decorator.hpp>
#include <agenkit/middleware/logging_decorator.hpp>

// Patterns
#include <agenkit/patterns/sequential_agent.hpp>
#include <agenkit/patterns/parallel_agent.hpp>
#include <agenkit/patterns/reflection_agent.hpp>
#include <agenkit/patterns/react_agent.hpp>
#include <agenkit/patterns/planning_agent.hpp>

// Key types
agenkit::core::Message       // Unit of communication
agenkit::core::Agent         // Abstract base class
agenkit::core::AgentError    // Error type
agenkit::core::Result<T, E>  // Success/failure wrapper

// Smart pointer idioms
auto agent  = std::make_unique<MyAgent>();      // exclusive ownership
auto shared = std::make_shared<MyAgent>();      // shared ownership
auto result = agent->process(msg).get();        // synchronous wait
auto future = agent->process(msg);              // async, wait later

// Result handling
if (result.is_ok())  { auto msg   = result.value(); }
if (result.is_err()) { auto error = result.error(); }
```

---

**Version**: v0.75.0
**Last Updated**: March 2026

For help: Open an issue at https://github.com/scttfrdmn/agenkit/issues
