# Getting Started with Agenkit - C++

**Complete guide to building high-performance AI agents with Agenkit in Modern C++**

## Table of Contents

1. [Installation](#installation)
2. [Your First Agent](#your-first-agent)
3. [Core Concepts](#core-concepts)
4. [Using Patterns](#using-patterns)
5. [Adding Middleware](#adding-middleware)
6. [Working with LLMs](#working-with-llms)
7. [Testing Your Agents](#testing-your-agents)
8. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- C++17 or higher compiler (GCC 9+, Clang 10+, MSVC 2019+)
- CMake 3.15 or higher
- vcpkg or conan for package management (recommended)

### Install with vcpkg

```bash
# Install vcpkg if you haven't
git clone https://github.com/Microsoft/vcpkg.git
cd vcpkg
./bootstrap-vcpkg.sh  # or bootstrap-vcpkg.bat on Windows

# Install agenkit
./vcpkg install agenkit
```

### Create New Project

```bash
mkdir my-agent
cd my-agent
```

Create `CMakeLists.txt`:

```cmake
cmake_minimum_required(VERSION 3.15)
project(my_agent VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(agenkit REQUIRED)
find_package(nlohmann_json REQUIRED)

add_executable(my_agent src/main.cpp)
target_link_libraries(my_agent
    PRIVATE
    agenkit::agenkit
    nlohmann_json::nlohmann_json
)
```

### Verify Installation

```bash
cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE=[vcpkg root]/scripts/buildsystems/vcpkg.cmake
cmake --build build
```

---

## Your First Agent

Let's create a simple agent that processes messages:

### Step 1: Create Your Agent

Create `src/agent.hpp`:

```cpp
#pragma once

#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <memory>
#include <string>

namespace my_agent {

/**
 * A simple agent that greets users
 */
class GreetingAgent : public agenkit::Agent {
public:
    GreetingAgent() = default;
    ~GreetingAgent() override = default;

    // Agent interface
    std::string name() const override {
        return "greeting-agent";
    }

    std::future<agenkit::Message> process(agenkit::Message message) override {
        auto user_message = std::get<std::string>(message.content);

        agenkit::Message response;
        response.role = "assistant";
        response.content = "Hello! You said: '" + user_message +
                          "'. How can I help you today?";

        // Return completed future
        std::promise<agenkit::Message> promise;
        promise.set_value(std::move(response));
        return promise.get_future();
    }
};

}  // namespace my_agent
```

### Step 2: Use Your Agent

Create `src/main.cpp`:

```cpp
#include "agent.hpp"
#include <iostream>

int main() {
    try {
        // Create agent instance
        auto agent = std::make_unique<my_agent::GreetingAgent>();

        // Create a user message
        agenkit::Message user_msg;
        user_msg.role = "user";
        user_msg.content = "Hi there!";

        // Process the message
        auto future = agent->process(std::move(user_msg));
        auto response = future.get();

        // Print the response
        std::cout << agent->name() << ": "
                  << std::get<std::string>(response.content) << std::endl;

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
```

### Step 3: Build and Run

```bash
cmake --build build
./build/my_agent
# Output: greeting-agent: Hello! You said: 'Hi there!'. How can I help you today?
```

**🎉 Congratulations!** You've created your first Agenkit agent in C++.

---

## Core Concepts

### The Agent Interface

Every agent in Agenkit inherits from the `Agent` base class:

```cpp
class Agent {
public:
    virtual ~Agent() = default;

    virtual std::string name() const = 0;
    virtual std::future<Message> process(Message message) = 0;
};
```

**Key points**:
- Pure virtual interface for polymorphism
- Uses `std::future` for async operations
- Virtual destructor for proper cleanup

### Messages

Messages are the unit of communication:

```cpp
#include <agenkit/core/message.hpp>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// Create a message
agenkit::Message msg;
msg.role = "user";
msg.content = "Hello!";  // Can be string or json
msg.metadata = json{
    {"source", "web"}
};

// Access message properties
std::cout << "Role: " << msg.role << std::endl;
std::cout << "Content: " << std::get<std::string>(msg.content) << std::endl;
std::cout << "Metadata: " << msg.metadata.dump() << std::endl;
```

### Smart Pointers and RAII

Modern C++ uses smart pointers for automatic memory management:

```cpp
#include <memory>

class MyAgent : public agenkit::Agent {
private:
    // Use unique_ptr for exclusive ownership
    std::unique_ptr<DependencyA> dependency_a_;

    // Use shared_ptr for shared ownership
    std::shared_ptr<DependencyB> dependency_b_;

public:
    MyAgent(std::unique_ptr<DependencyA> dep_a,
            std::shared_ptr<DependencyB> dep_b)
        : dependency_a_(std::move(dep_a))
        , dependency_b_(std::move(dep_b)) {
    }

    // No need for explicit destructor - RAII handles cleanup
    ~MyAgent() override = default;

    std::string name() const override {
        return "my-agent";
    }

    std::future<agenkit::Message> process(agenkit::Message message) override {
        // Use dependencies safely
        auto result = dependency_a_->process(message);

        std::promise<agenkit::Message> promise;
        promise.set_value(std::move(result));
        return promise.get_future();
    }
};
```

### Error Handling with Exceptions

C++ uses exceptions for error handling:

```cpp
#include <stdexcept>

class ProcessingError : public std::runtime_error {
public:
    explicit ProcessingError(const std::string& msg)
        : std::runtime_error("Processing error: " + msg) {
    }
};

class MyAgent : public agenkit::Agent {
public:
    std::future<agenkit::Message> process(agenkit::Message message) override {
        std::promise<agenkit::Message> promise;

        try {
            // Validate input
            auto content = std::get<std::string>(message.content);
            if (content.empty()) {
                throw ProcessingError("Empty message content");
            }

            // Process message
            auto result = process_internal(content);
            promise.set_value(std::move(result));

        } catch (...) {
            // Propagate exception through promise
            promise.set_exception(std::current_exception());
        }

        return promise.get_future();
    }
};
```

### Tools

Tools let agents take actions:

```cpp
#include <agenkit/core/tool.hpp>
#include <nlohmann/json.hpp>

class CalculatorTool : public agenkit::Tool {
public:
    std::string name() const override {
        return "calculator";
    }

    std::string description() const override {
        return "Performs basic arithmetic operations";
    }

    std::future<agenkit::ToolResult> execute(const nlohmann::json& params) override {
        std::promise<agenkit::ToolResult> promise;

        try {
            auto operation = params["operation"].get<std::string>();
            auto a = params["a"].get<double>();
            auto b = params["b"].get<double>();

            double result;
            if (operation == "add") {
                result = a + b;
            } else if (operation == "multiply") {
                result = a * b;
            } else {
                throw std::invalid_argument("Unknown operation: " + operation);
            }

            agenkit::ToolResult tool_result;
            tool_result.output = result;
            promise.set_value(std::move(tool_result));

        } catch (...) {
            promise.set_exception(std::current_exception());
        }

        return promise.get_future();
    }
};
```

---

## Using Patterns

Agenkit includes 18 pre-built patterns for common agent architectures.

### Reflection Pattern

Iteratively improve outputs through self-critique:

```cpp
#include <agenkit/patterns/reflection.hpp>

// Configure reflection
agenkit::ReflectionConfig config;
config.max_iterations = 3;
config.quality_threshold = 0.8;
config.stop_on_repeat = true;

// Create reflection agent
auto generator = std::make_shared<GeneratorAgent>();
auto critic = std::make_shared<CriticAgent>();

auto agent = std::make_unique<agenkit::ReflectionAgent>(
    generator,
    critic,
    config
);

// Use it
agenkit::Message msg;
msg.role = "user";
msg.content = "Write a haiku about coding";

auto future = agent->process(std::move(msg));
auto response = future.get();

// Response includes iteration metadata
std::cout << "Iterations: " << response.metadata["iterations"] << std::endl;
std::cout << "Quality: " << response.metadata["final_quality_score"] << std::endl;
```

### Sequential Pattern

Chain multiple agents in sequence:

```cpp
#include <agenkit/patterns/sequential.hpp>

// Create a pipeline: research → summarize → format
std::vector<std::shared_ptr<agenkit::Agent>> agents = {
    std::make_shared<ResearchAgent>(),
    std::make_shared<SummaryAgent>(),
    std::make_shared<FormatterAgent>()
};

auto pipeline = std::make_unique<agenkit::SequentialPattern>(agents);

// Input flows through each agent in order
agenkit::Message msg;
msg.role = "user";
msg.content = "Research quantum computing";

auto response = pipeline->process(std::move(msg)).get();
```

### Parallel Pattern

Run multiple agents concurrently and aggregate results:

```cpp
#include <agenkit/patterns/parallel.hpp>

// Configure parallel execution
agenkit::ParallelConfig config;
config.agents = {
    std::make_shared<TechnicalAgent>(),
    std::make_shared<BusinessAgent>(),
    std::make_shared<UserAgent>()
};
config.aggregation = agenkit::AggregationStrategy::Merge;

// Create parallel pattern
auto parallel = std::make_unique<agenkit::ParallelPattern>(config);

// All agents process simultaneously
agenkit::Message msg;
msg.role = "user";
msg.content = "Analyze this product idea";

auto response = parallel->process(std::move(msg)).get();
```

### ReAct Pattern

Reasoning + Acting with tool use:

```cpp
#include <agenkit/patterns/react.hpp>

// Configure ReAct
agenkit::ReActConfig config;
config.max_steps = 5;
config.tools = {
    std::make_shared<SearchTool>(),
    std::make_shared<CalculatorTool>()
};

// Create ReAct agent
auto agent = std::make_unique<agenkit::ReActAgent>(
    std::make_shared<ReasoningAgent>(),
    config
);

// Agent will alternate between thinking and acting
agenkit::Message msg;
msg.role = "user";
msg.content = "What's the population of Tokyo divided by the population of NYC?";

auto response = agent->process(std::move(msg)).get();

// Response includes reasoning trace
std::cout << "Steps: " << response.metadata["steps"] << std::endl;
std::cout << "Tool calls: " << response.metadata["tool_calls"] << std::endl;
```

---

## Adding Middleware

Middleware adds production features without changing your agent code.

### Retry Logic

Automatically retry failed operations:

```cpp
#include <agenkit/middleware/retry.hpp>
#include <chrono>

using namespace std::chrono_literals;

// Configure retries
agenkit::RetryConfig config;
config.max_attempts = 3;
config.backoff_factor = 2.0;
config.initial_delay = 1s;
config.max_delay = 30s;

// Wrap your agent
auto resilient_agent = std::make_unique<agenkit::RetryMiddleware>(
    std::move(my_agent),
    config
);

// Now handles transient failures automatically
auto response = resilient_agent->process(std::move(message)).get();
```

### Circuit Breaker

Prevent cascading failures:

```cpp
#include <agenkit/middleware/circuit_breaker.hpp>

// Configure circuit breaker
agenkit::CircuitBreakerConfig config;
config.failure_threshold = 5;
config.timeout = 60s;
config.success_threshold = 2;

// Wrap your agent
auto protected_agent = std::make_unique<agenkit::CircuitBreakerMiddleware>(
    std::move(my_agent),
    config
);

// Fails fast when circuit is open
try {
    auto response = protected_agent->process(std::move(message)).get();
    std::cout << "Success: " << std::get<std::string>(response.content) << std::endl;
} catch (const agenkit::CircuitBreakerError& e) {
    std::cerr << "Circuit is open - service unavailable" << std::endl;
}
```

### Timeout

Set maximum execution time:

```cpp
#include <agenkit/middleware/timeout.hpp>

// Configure timeout
agenkit::TimeoutConfig config;
config.timeout = 30s;
config.grace_period = 5s;

// Wrap your agent
auto timed_agent = std::make_unique<agenkit::TimeoutMiddleware>(
    std::move(my_agent),
    config
);

// Will cancel after 30 seconds
try {
    auto response = timed_agent->process(std::move(message)).get();
} catch (const agenkit::TimeoutError& e) {
    std::cerr << "Agent took too long to respond" << std::endl;
}
```

### Stacking Middleware

Combine multiple middleware layers:

```cpp
#include <agenkit/middleware/all.hpp>

// Stack middleware (innermost to outermost)
std::unique_ptr<agenkit::Agent> agent = std::move(my_agent);

agent = std::make_unique<agenkit::TimeoutMiddleware>(
    std::move(agent),
    timeout_config
);

agent = std::make_unique<agenkit::CircuitBreakerMiddleware>(
    std::move(agent),
    circuit_config
);

agent = std::make_unique<agenkit::RetryMiddleware>(
    std::move(agent),
    retry_config
);

// Now has full production resilience
auto response = agent->process(std::move(message)).get();
```

---

## Working with LLMs

### OpenAI Integration

```cpp
#include <agenkit/adapters/openai.hpp>
#include <cstdlib>

// Create OpenAI agent
agenkit::OpenAIConfig config;
config.model = "gpt-4";
config.api_key = std::getenv("OPENAI_API_KEY");

auto agent = std::make_unique<agenkit::OpenAIAdapter>(config);

// Use it like any agent
agenkit::Message msg;
msg.role = "user";
msg.content = "Explain quantum computing";

auto response = agent->process(std::move(msg)).get();
std::cout << std::get<std::string>(response.content) << std::endl;
```

### Anthropic (Claude) Integration

```cpp
#include <agenkit/adapters/anthropic.hpp>

// Create Claude agent
agenkit::AnthropicConfig config;
config.model = "claude-3-opus-20240229";
config.api_key = std::getenv("ANTHROPIC_API_KEY");

auto agent = std::make_unique<agenkit::AnthropicAdapter>(config);

agenkit::Message msg;
msg.role = "user";
msg.content = "Write a function to calculate Fibonacci numbers";

auto response = agent->process(std::move(msg)).get();
```

### Custom LLM Integration

```cpp
#include <agenkit/core/agent.hpp>
#include <curl/curl.h>
#include <nlohmann/json.hpp>

class CustomLLMAgent : public agenkit::Agent {
private:
    std::string api_url_;
    std::string api_key_;

public:
    CustomLLMAgent(std::string api_url, std::string api_key)
        : api_url_(std::move(api_url))
        , api_key_(std::move(api_key)) {
    }

    std::string name() const override {
        return "custom-llm";
    }

    std::future<agenkit::Message> process(agenkit::Message message) override {
        std::promise<agenkit::Message> promise;

        try {
            // Build request
            nlohmann::json request_body = {
                {"prompt", std::get<std::string>(message.content)}
            };

            // Call API (using libcurl)
            auto response_json = call_api(request_body);

            // Parse response
            agenkit::Message response;
            response.role = "assistant";
            response.content = response_json["completion"].get<std::string>();

            promise.set_value(std::move(response));

        } catch (...) {
            promise.set_exception(std::current_exception());
        }

        return promise.get_future();
    }

private:
    nlohmann::json call_api(const nlohmann::json& request) {
        // Implement your API call logic here
        // This is a simplified example
        throw std::runtime_error("Implement API call");
    }
};
```

---

## Testing Your Agents

### Unit Testing with Google Test

Add to `CMakeLists.txt`:

```cmake
enable_testing()
find_package(GTest REQUIRED)

add_executable(agent_test tests/agent_test.cpp)
target_link_libraries(agent_test
    PRIVATE
    agenkit::agenkit
    GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(agent_test)
```

Create `tests/agent_test.cpp`:

```cpp
#include <gtest/gtest.h>
#include "../src/agent.hpp"

TEST(GreetingAgentTest, RespondsWithGreeting) {
    auto agent = std::make_unique<my_agent::GreetingAgent>();

    agenkit::Message msg;
    msg.role = "user";
    msg.content = "Hello";

    auto response = agent->process(std::move(msg)).get();

    EXPECT_EQ(response.role, "assistant");
    EXPECT_TRUE(std::get<std::string>(response.content).find("Hello") != std::string::npos);
}

TEST(GreetingAgentTest, HasCorrectName) {
    auto agent = std::make_unique<my_agent::GreetingAgent>();
    EXPECT_EQ(agent->name(), "greeting-agent");
}
```

### Integration Testing with Mocks

```cpp
class MockAgent : public agenkit::Agent {
private:
    std::string response_;

public:
    explicit MockAgent(std::string response)
        : response_(std::move(response)) {
    }

    std::string name() const override {
        return "mock-agent";
    }

    std::future<agenkit::Message> process(agenkit::Message message) override {
        std::promise<agenkit::Message> promise;

        agenkit::Message response;
        response.role = "assistant";
        response.content = response_;

        promise.set_value(std::move(response));
        return promise.get_future();
    }
};

TEST(SequentialPatternTest, ProcessesThroughAllAgents) {
    std::vector<std::shared_ptr<agenkit::Agent>> agents = {
        std::make_shared<MockAgent>("Step 1 complete"),
        std::make_shared<MockAgent>("Step 2 complete"),
        std::make_shared<MockAgent>("Step 3 complete")
    };

    auto pipeline = std::make_unique<agenkit::SequentialPattern>(agents);

    agenkit::Message msg;
    msg.role = "user";
    msg.content = "Start pipeline";

    auto response = pipeline->process(std::move(msg)).get();
    EXPECT_TRUE(std::get<std::string>(response.content).find("Step 3 complete") != std::string::npos);
}
```

### Benchmarking with Google Benchmark

Add to `CMakeLists.txt`:

```cmake
find_package(benchmark REQUIRED)

add_executable(agent_benchmark benchmarks/agent_benchmark.cpp)
target_link_libraries(agent_benchmark
    PRIVATE
    agenkit::agenkit
    benchmark::benchmark
)
```

Create `benchmarks/agent_benchmark.cpp`:

```cpp
#include <benchmark/benchmark.h>
#include "../src/agent.hpp"

static void BM_GreetingAgent(benchmark::State& state) {
    auto agent = std::make_unique<my_agent::GreetingAgent>();

    agenkit::Message msg;
    msg.role = "user";
    msg.content = "Hello";

    for (auto _ : state) {
        auto response = agent->process(msg).get();
        benchmark::DoNotOptimize(response);
    }
}

BENCHMARK(BM_GreetingAgent);
BENCHMARK_MAIN();
```

Run benchmarks:
```bash
cmake --build build --target agent_benchmark
./build/agent_benchmark
```

---

## Next Steps

### Learn More

- **[Pattern Guide](../patterns/README.md)** - Detailed guide to all 18 patterns
- **[API Reference](../api/cpp/README.md)** - Complete API documentation
- **[Best Practices](../best-practices/CPP.md)** - Production deployment tips
- **[Examples](../../agenkit-cpp/examples/)** - Working examples

### Performance Optimization

- **[Zero-Copy Patterns](../performance/CPP_ZERO_COPY.md)** - Minimize allocations
- **[Move Semantics](../performance/CPP_MOVE.md)** - Efficient object transfer
- **[Memory Management](../performance/CPP_MEMORY.md)** - Smart pointers and RAII
- **[Profiling Guide](../performance/CPP_PROFILING.md)** - Profile your agents

### Deploy to Production

- **[Docker Deployment](../deployment/DOCKER.md)** - Containerize your agents
- **[Kubernetes Guide](../deployment/KUBERNETES.md)** - Scale with K8s
- **[Monitoring & Observability](../observability/README.md)** - Track agent performance

### Migrate from Other Languages

Coming from Python or another language?

- **[Python → C++ Migration](../migration/PYTHON_TO_CPP.md)** - Migrate from Python
- **[Go → C++ Migration](../migration/GO_TO_CPP.md)** - Migrate from Go

---

## Quick Reference

### Installation
```bash
./vcpkg install agenkit
```

### Minimal Agent
```cpp
#include <agenkit/core/agent.hpp>

class MyAgent : public agenkit::Agent {
public:
    std::string name() const override {
        return "my-agent";
    }

    std::future<agenkit::Message> process(agenkit::Message message) override {
        std::promise<agenkit::Message> promise;

        agenkit::Message response;
        response.role = "assistant";
        response.content = "Response";

        promise.set_value(std::move(response));
        return promise.get_future();
    }
};
```

### Common Includes
```cpp
// Core
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <agenkit/core/tool.hpp>

// Patterns
#include <agenkit/patterns/reflection.hpp>
#include <agenkit/patterns/react.hpp>
#include <agenkit/patterns/sequential.hpp>
#include <agenkit/patterns/parallel.hpp>

// Middleware
#include <agenkit/middleware/retry.hpp>
#include <agenkit/middleware/circuit_breaker.hpp>
#include <agenkit/middleware/timeout.hpp>

// Adapters
#include <agenkit/adapters/openai.hpp>
#include <agenkit/adapters/anthropic.hpp>
```

---

**Ready to build?** Check out the [examples](../../agenkit-cpp/examples/) for working code you can run right now.

**Performance tip:** C++'s control over memory and zero-cost abstractions provide maximum performance - perfect for high-throughput production AI agents!
