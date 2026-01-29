# Getting Started with Agenkit (C++)

**Target audience**: C++ developers new to Agenkit
**Time to first agent**: 20-40 minutes
**Prerequisites**: C++17+, CMake 3.20+

---

## Installation

### Using CMake FetchContent

Add to your `CMakeLists.txt`:

```cmake
include(FetchContent)

FetchContent_Declare(
    agenkit
    GIT_REPOSITORY https://github.com/yourusername/agenkit-cpp.git
    GIT_TAG v0.50.0
)

FetchContent_MakeAvailable(agenkit)

target_link_libraries(your_target PRIVATE agenkit::agenkit)
```

### Or Install Locally

```bash
git clone https://github.com/yourusername/agenkit-cpp.git
cd agenkit-cpp
mkdir build && cd build
cmake ..
make
sudo make install
```

---

## Your First Agent

Let's create a simple greeting agent:

```cpp
#include <agenkit/agent.hpp>
#include <agenkit/message.hpp>
#include <iostream>
#include <memory>

class GreetingAgent : public agenkit::Agent {
public:
    std::string name() const override {
        return "greeting-agent";
    }

    std::future<agenkit::Result<agenkit::Message, agenkit::AgentError>>
    process(agenkit::Message message) override {
        auto user_content = message.content();
        auto greeting = "Hello! You said: " + user_content;

        agenkit::Message response("assistant", greeting);
        response.set_metadata("processed_by", name());

        return std::async(std::launch::deferred, [response]() {
            return agenkit::Result<agenkit::Message, agenkit::AgentError>::ok(response);
        });
    }
};

int main() {
    auto agent = std::make_unique<GreetingAgent>();

    agenkit::Message message("user", "Hi there!");

    auto future = agent->process(message);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << "Agent: " << result.value().content() << std::endl;
        // Output: Agent: Hello! You said: Hi there!
    } else {
        std::cerr << "Error: " << result.error().message() << std::endl;
    }

    return 0;
}
```

Compile and run:
```bash
g++ -std=c++17 main.cpp -lagenkit -o greeting
./greeting
```

---

## Production-Ready Agent with Middleware

Add resilience with retry, circuit breaker, and timeout middleware:

```cpp
#include <agenkit/agent.hpp>
#include <agenkit/middleware/retry_decorator.hpp>
#include <agenkit/middleware/circuit_breaker_decorator.hpp>
#include <agenkit/middleware/timeout_decorator.hpp>
#include <chrono>
#include <thread>

class ProductionAgent : public agenkit::Agent {
public:
    std::string name() const override {
        return "production-agent";
    }

    std::future<agenkit::Result<agenkit::Message, agenkit::AgentError>>
    process(agenkit::Message message) override {
        return std::async(std::launch::async, [this, message]() {
            // Simulate some processing
            std::this_thread::sleep_for(std::chrono::milliseconds(100));

            agenkit::Message response(
                "assistant",
                "Processed: " + message.content()
            );
            response.set_metadata("agent", name());

            return agenkit::Result<agenkit::Message, agenkit::AgentError>::ok(response);
        });
    }
};

int main() {
    auto base_agent = std::make_shared<ProductionAgent>();

    // Wrap with middleware (v0.50.0 uses milliseconds for clarity)
    auto agent = std::make_shared<agenkit::RetryDecorator>(
        base_agent,
        3,    // max_attempts
        100   // initial_delay_ms
    );

    agent = std::make_shared<agenkit::CircuitBreakerDecorator>(
        agent,
        5,      // failure_threshold
        30000   // recovery_timeout_ms
    );

    agent = std::make_shared<agenkit::TimeoutDecorator>(
        agent,
        5000    // timeout_ms
    );

    agenkit::Message message("user", "Hello production!");
    auto future = agent->process(message);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << result.value().content() << std::endl;
    }

    return 0;
}
```

**Note**: C++ uses milliseconds for timeout parameters (v0.50.0 naming clarity).

---

## Using LLM Adapters

### OpenAI Example

```cpp
#include <agenkit/adapters/openai_llm.hpp>
#include <agenkit/message.hpp>
#include <cstdlib>
#include <iostream>
#include <vector>

int main() {
    // Initialize LLM (validates parameters at construction)
    auto llm = agenkit::OpenAILLM(
        std::getenv("OPENAI_API_KEY"),
        "gpt-4-turbo"
    );

    // Set options (validated)
    llm.set_temperature(0.7);   // Validated: 0-2
    llm.set_max_tokens(1024);   // Validated: >0

    // Create conversation
    std::vector<agenkit::Message> messages = {
        agenkit::Message("system", "You are a helpful assistant."),
        agenkit::Message("user", "What is Agenkit?")
    };

    // Get completion
    auto future = llm.complete(messages);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << result.value().content() << std::endl;
    }

    // Stream response
    llm.process_stream(
        messages.back(),
        // on_message
        [](agenkit::Message chunk) {
            std::cout << chunk.content() << std::flush;
        },
        // on_error
        [](agenkit::AgentError error) {
            std::cerr << error.message() << std::endl;
        },
        // on_complete
        []() {
            std::cout << "\nComplete\n";
        }
    );

    return 0;
}
```

### Anthropic Example

```cpp
#include <agenkit/adapters/anthropic_llm.hpp>

auto llm = agenkit::AnthropicLLM(
    std::getenv("ANTHROPIC_API_KEY"),
    "claude-3-5-sonnet-20241022"
);
llm.set_temperature(1.0);
llm.set_max_tokens(4096);
```

**Parameter Validation** (v0.50.0):
- `temperature`: 0.0 - 2.0 (validated at construction/setter)
- `max_tokens`: > 0 (validated at construction/setter)
- `top_p`: 0.0 - 1.0 (validated at construction/setter)

Invalid values throw `std::invalid_argument` immediately.

---

## Common Patterns

Agenkit provides **18 core patterns** for building AI agents (see the [Agent Patterns Book](../../agent-patterns-book) for comprehensive details). Here are three essential patterns to get started:

### 1. Reflection Pattern

**One-line**: Iterative self-improvement through draft-critique-refine loop

```cpp
#include <agenkit/patterns/reflection_agent.hpp>
#include <agenkit/adapters/openai_llm.hpp>

int main() {
    auto llm = std::make_shared<agenkit::OpenAILLM>(
        std::getenv("OPENAI_API_KEY"),
        "gpt-4-turbo"
    );

    auto agent = agenkit::ReflectionAgent(
        llm,
        3,  // max_iterations
        "Review and improve this response:"
    );

    agenkit::Message message("user", "Explain RAII in C++");
    auto future = agent.process(message);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << result.value().content() << std::endl;
    }

    return 0;
}
```

### 2. ReAct Pattern

**One-line**: Reasoning + Acting with explicit thought-action-observation loop

```cpp
#include <agenkit/patterns/react_agent.hpp>
#include <agenkit/tool.hpp>
#include <agenkit/adapters/openai_llm.hpp>

class SearchTool : public agenkit::Tool {
public:
    std::string name() const override {
        return "search";
    }

    std::string description() const override {
        return "Search for information";
    }

    std::map<std::string, nlohmann::json> parameters() const override {
        return {
            {"query", {
                {"type", "string"},
                {"description", "Search query"}
            }}
        };
    }

    agenkit::ToolResult execute(
        const std::map<std::string, nlohmann::json>& params
    ) const override {
        auto query = params.at("query").get<std::string>();
        // Simulate search
        return agenkit::ToolResult{
            true,  // success
            "Search results for: " + query
        };
    }
};

int main() {
    auto llm = std::make_shared<agenkit::OpenAILLM>(
        std::getenv("OPENAI_API_KEY"),
        "gpt-4-turbo"
    );

    std::vector<std::shared_ptr<agenkit::Tool>> tools = {
        std::make_shared<SearchTool>()
    };

    auto agent = agenkit::ReActAgent(llm, tools, 5);  // max_iterations

    agenkit::Message message("user", "What's the weather in Paris?");
    auto future = agent.process(message);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << result.value().content() << std::endl;
    }

    return 0;
}
```

### 3. Sequential Pattern

**One-line**: Execute agents in order, passing outputs between stages

```cpp
#include <agenkit/patterns/sequential_agent.hpp>

int main() {
    // Create agent pipeline
    std::vector<std::shared_ptr<agenkit::Agent>> agents = {
        std::make_shared<ResearchAgent>(),
        std::make_shared<SummarizerAgent>(),
        std::make_shared<EditorAgent>()
    };

    auto agent = agenkit::SequentialAgent(agents);

    agenkit::Message message("user", "Research AI safety");
    auto future = agent.process(message);
    auto result = future.get();

    if (result.is_ok()) {
        std::cout << result.value().content() << std::endl;
    }

    return 0;
}
```

**See all 18 patterns**: Refer to the [Agent Patterns Book](../../agent-patterns-book) for complete pattern descriptions, trade-offs, and when to use each pattern.

---

## Memory Management

### RAII Pattern

```cpp
// Agents follow RAII - resources cleaned up automatically
{
    auto agent = std::make_unique<MyAgent>();
    // Use agent...
} // Agent destroyed, resources released
```

### Smart Pointers

```cpp
// Use shared_ptr for shared ownership
auto llm = std::make_shared<OpenAILLM>(...);
auto agent1 = std::make_shared<Agent>(llm);
auto agent2 = std::make_shared<Agent>(llm);  // Shares LLM

// Use unique_ptr for exclusive ownership
auto agent = std::make_unique<MyAgent>();
```

---

## Common Pitfalls

### 1. Always Check Results

```cpp
// WRONG:
auto result = agent->process(message).get();
std::cout << result.value().content();  // Crashes if error!

// CORRECT:
auto result = agent->process(message).get();
if (result.is_ok()) {
    std::cout << result.value().content();
} else {
    std::cerr << "Error: " << result.error().message() << std::endl;
}
```

### 2. Move Semantics

```cpp
// Use std::move for expensive types
agenkit::Message message = createMessage();
auto result = agent->process(std::move(message));
```

### 3. Thread Safety

```cpp
// LLM adapters are thread-safe for reads
// For writes, synchronize access
std::mutex mutex;
{
    std::lock_guard<std::mutex> lock(mutex);
    llm.set_temperature(0.7);
}
```

---

## Next Steps

1. **Explore Patterns**: See the [Agent Patterns Book](../../agent-patterns-book) for all 18 patterns
2. **Read Architecture**: `ARCHITECTURE.md` explains design principles
3. **Check Examples**: `agenkit-cpp/examples/` has production examples
4. **API Reference**: Coming soon in `docs/api-reference/cpp/`
5. **Build Guide**: See `agenkit-cpp/docs/BUILD.md` for build instructions

---

## Quick Reference

```cpp
// Core includes
#include <agenkit/agent.hpp>
#include <agenkit/message.hpp>
#include <agenkit/tool.hpp>

// Middleware
#include <agenkit/middleware/retry_decorator.hpp>
#include <agenkit/middleware/timeout_decorator.hpp>
#include <agenkit/middleware/circuit_breaker_decorator.hpp>

// LLM adapters
#include <agenkit/adapters/openai_llm.hpp>
#include <agenkit/adapters/anthropic_llm.hpp>

// Patterns
#include <agenkit/patterns/reflection_agent.hpp>
#include <agenkit/patterns/react_agent.hpp>
#include <agenkit/patterns/sequential_agent.hpp>

// Result type
agenkit::Result<T, E>  // Like Rust's Result
if (result.is_ok()) { result.value(); }
if (result.is_err()) { result.error(); }
```

---

**Version**: v0.50.0
**Last Updated**: January 28, 2026

For help: Open an issue at https://github.com/yourusername/agenkit/issues
