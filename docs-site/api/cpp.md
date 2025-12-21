# C++ API Reference

Complete API documentation for Agenkit C++ implementation.

## Official Documentation

The C++ implementation uses Doxygen to generate comprehensive API documentation from inline comments. Documentation can be generated locally or viewed through your IDE's IntelliSense.

**Status**: Doxygen configuration complete - documentation generation available

---

## Quick Navigation

### Core Module

**`agenkit::core`** - Core types and interfaces

```cpp
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <agenkit/core/errors.hpp>
#include <agenkit/core/result.hpp>
```

Key types:
- `Agent` - Core agent interface
- `Message` - Universal message format
- `Result<T, E>` - Result type for error handling
- `AgentError` - Error type for agent operations

### Patterns

**`agenkit::patterns`** - Agent patterns

```cpp
#include <agenkit/patterns/reflection.hpp>
#include <agenkit/patterns/react.hpp>
#include <agenkit/patterns/agents_as_tools.hpp>
// ... and 15 more patterns
```

Available patterns:
- `ReflectionAgent` - Self-critique loop
- `ReActAgent` - Reasoning + Acting
- `AgentsAsToolsAgent` - Hierarchical delegation
- `OrchestrationAgent` - Complex workflows
- `ReasoningWithToolsAgent` - Advanced tool usage
- `ConversationalAgent` - Multi-turn conversations
- `TaskAgent` - Task decomposition
- `MultiagentAgent` - Multi-agent coordination
- `PlanningAgent` - Goal-driven planning
- `AutonomousAgent` - Self-directed behavior
- `MemoryHierarchyAgent` - Memory management
- `SequentialAgent` - Sequential pipeline
- `ParallelAgent` - Concurrent execution
- `SupervisorAgent` - Agent supervision
- `RouterAgent` - Dynamic routing
- `CollaborativeAgent` - Agent collaboration
- `HumanInLoopAgent` - Human oversight
- `FallbackAgent` - Graceful degradation

### Reasoning Techniques

**`agenkit::techniques::reasoning`** - Advanced reasoning

```cpp
#include <agenkit/techniques/reasoning/chain_of_thought.hpp>
#include <agenkit/techniques/reasoning/tree_of_thought.hpp>
#include <agenkit/techniques/reasoning/self_consistency.hpp>
```

Available techniques:
- `ChainOfThought` - Step-by-step reasoning
- `TreeOfThought` - Multi-path exploration
- `SelfConsistency` - Voting strategy
- `ReasoningTree` - Tree utilities

### LLM Adapters

**`agenkit::adapters`** - LLM provider adapters

```cpp
#include <agenkit/adapters/openai_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>
#include <agenkit/adapters/gemini_agent.hpp>
#include <agenkit/adapters/bedrock_agent.hpp>
#include <agenkit/adapters/ollama_agent.hpp>
```

Available adapters:
- `OpenAIAgent` - OpenAI API
- `ClaudeAgent` - Anthropic Claude API
- `GeminiAgent` - Google Gemini API
- `BedrockAgent` - AWS Bedrock
- `OllamaAgent` - Ollama (local models)
- `LiteLLMAgent` - LiteLLM proxy

### Transport

**`agenkit::transports`** - HTTP server/client

```cpp
#include <agenkit/transports/http_agent.hpp>
#include <agenkit/transports/http_server.hpp>
```

Features:
- `HttpAgent` - Connect to remote agents
- `HttpServer` - Serve agents over HTTP

### Evaluation

**`agenkit::evaluation`** - Testing and optimization

```cpp
#include <agenkit/evaluation/metrics.hpp>
#include <agenkit/evaluation/recorder.hpp>
#include <agenkit/evaluation/benchmarks.hpp>
```

Features:
- `Recorder` - Session recording
- `BenchmarkRunner` - Performance benchmarks
- `BayesianOptimizer` - Hyperparameter optimization
- `PromptOptimizer` - Prompt optimization
- `QualityMetrics` - Quality evaluation
- `ContextMetrics` - Context analysis
- `RegressionDetector` - Performance monitoring
- `ABTesting` - A/B testing framework

---

## Getting Started with C++

### Installation

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/agenkit-cpp

# Build with CMake
mkdir build && cd build
cmake ..
cmake --build .

# Or use provided script
./scripts/build.sh
```

### Basic Example

```cpp
#include <agenkit/core/agent.hpp>
#include <agenkit/core/message.hpp>
#include <iostream>

using namespace agenkit::core;

class EchoAgent : public Agent {
public:
    std::string name() const override {
        return "echo-agent";
    }

    std::vector<std::string> capabilities() const override {
        return {"echo", "simple"};
    }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto content = message.content_as_str();
        auto response = Message::with_text(
            "assistant",
            "Echo: " + content
        );
        return make_ready_future(
            Result<Message, AgentError>::ok(response)
        );
    }
};

int main() {
    auto agent = std::make_unique<EchoAgent>();

    auto message = Message::with_text("user", "Hello!");
    auto future = agent->process(message);
    auto result = future.get();

    if (result.is_ok()) {
        auto response = result.unwrap();
        std::cout << response.content_as_str() << std::endl;
        // Output: "Echo: Hello!"
    }

    return 0;
}
```

---

## C++-Specific Features

### Modern C++17

Agenkit C++ uses modern C++17 features:

```cpp
// Smart pointers for memory safety
auto agent = std::make_unique<MyAgent>();

// std::optional for optional values
std::optional<std::string> api_key = get_api_key();
if (api_key.has_value()) {
    // Use api_key.value()
}

// Structured bindings
auto [name, age] = get_user_info();

// String views for efficiency
std::string_view content = message.content_as_str();
```

### Result Type

C++ uses a `Result<T, E>` type for error handling:

```cpp
Result<Message, AgentError> result = agent->process(message).get();

if (result.is_ok()) {
    Message response = result.unwrap();
    // Success path
} else {
    AgentError error = result.unwrap_err();
    std::cerr << "Error: " << error.message() << std::endl;
}

// Or use match-like syntax
result.match(
    [](Message& msg) {
        // Success case
        std::cout << msg.content_as_str() << std::endl;
    },
    [](AgentError& err) {
        // Error case
        std::cerr << "Failed: " << err.message() << std::endl;
    }
);
```

### Async with std::future

Agents return `std::future` for async operations:

```cpp
// Start async operation
std::future<Result<Message, AgentError>> future =
    agent->process(message);

// Do other work...

// Wait for result
auto result = future.get();
```

### RAII and Zero-Copy

C++ uses RAII for automatic resource management and supports zero-copy operations:

```cpp
{
    // HttpServer automatically cleaned up at end of scope
    HttpServer server(std::move(agent), "localhost:8080");
    server.serve();
} // server destroyed here

// Move semantics for zero-copy
Message message = Message::with_text("user", "Hello");
auto response = agent->process(std::move(message)).get();
```

---

## Building Documentation Locally

Generate Doxygen documentation locally:

```bash
cd agenkit-cpp

# Install Doxygen (if not already installed)
# macOS: brew install doxygen
# Ubuntu: sudo apt-get install doxygen
# Windows: choco install doxygen

# Configure CMake
mkdir build && cd build
cmake ..

# Generate documentation
cmake --build . --target docs

# Documentation will be in build/docs/api/html/
# Open in browser:
# macOS: open docs/api/html/index.html
# Linux: xdg-open docs/api/html/index.html
# Windows: start docs/api/html/index.html
```

Or generate directly with Doxygen:

```bash
cd agenkit-cpp
doxygen Doxyfile

# Output will be in docs/api/html/
```

---

## IDE Integration

### Visual Studio

Full IntelliSense support with inline documentation:

1. Open project in Visual Studio
2. Hover over any type/function for documentation
3. Press `F1` for detailed help
4. Use `Ctrl+K, Ctrl+I` for quick info

### CLion / Visual Studio Code

IntelliSense/code completion with documentation:

1. **CLion**: Built-in support, hover for docs
2. **VS Code**: Install C/C++ extension
   ```bash
   code --install-extension ms-vscode.cpptools
   ```
3. Hover over types/functions for documentation
4. `Ctrl+Space` for autocomplete with docs

### vim/neovim

Use clangd LSP for inline documentation:

```vim
" For vim-lsp
Plug 'prabirshrestha/vim-lsp'

" For coc.nvim
Plug 'neoclide/coc.nvim', {'branch': 'release'}
" :CocInstall coc-clangd
```

---

## Documentation Standards

All C++ code follows Doxygen documentation conventions:

### File Documentation

Every header file has a file-level doc comment:

```cpp
/**
 * @file agent.hpp
 * @brief Core Agent interface and abstractions
 *
 * This module defines the core Agent interface that all agents must implement,
 * following the same design as Python, Go, TypeScript, and Rust implementations.
 */
```

### Class Documentation

Every class is documented with purpose and usage:

```cpp
/**
 * @brief Core Agent interface - minimal contract for agent communication
 *
 * Design decisions:
 * - Only 2 required methods (name, process)
 * - Async process using std::future for portability
 * - No state in interface (agents manage their own state)
 *
 * @example
 * @code
 * class SimpleAgent : public Agent {
 * public:
 *     std::string name() const override { return "simple"; }
 *
 *     std::future<Result<Message, AgentError>>
 *     process(Message message) override {
 *         // Implementation
 *     }
 * };
 * @endcode
 */
class Agent {
    // ...
};
```

### Method Documentation

Every public method is documented:

```cpp
/**
 * @brief Process a message and return a response
 *
 * This is the primary method for synchronous request-response interactions.
 * The method returns a future to support async operations.
 *
 * @param message Input message
 * @return Future containing Result<Message, AgentError>
 */
virtual std::future<Result<Message, AgentError>>
process(Message message) = 0;
```

---

## Examples

Comprehensive examples are available in the [C++ examples directory](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-cpp/examples):

### Basic Examples
- Echo agent
- HTTP transport
- Sequential pipeline
- Parallel execution

### Pattern Examples
- Reflection loop
- Agents-as-Tools
- Orchestration
- ReAct with tools
- All 18 agent patterns

### LLM Examples
- OpenAI integration
- Claude/Anthropic integration
- Google Gemini integration
- AWS Bedrock integration
- Ollama (local models)
- LiteLLM proxy

### Production Examples
- Error handling
- HTTP server/client
- Long-running operations
- Collaborative agents

---

## Testing

Run tests for the C++ implementation:

```bash
cd agenkit-cpp/build

# Run all tests
ctest

# Run specific test
ctest -R test_echo_agent

# Run with verbose output
ctest --verbose

# Run benchmarks
./benchmarks/bench_patterns
```

---

## Cross-Language Compatibility

C++ agents can communicate with Python, Go, TypeScript, and other language implementations via HTTP:

### Call Python Agent from C++

```cpp
#include <agenkit/transports/http_agent.hpp>

HttpAgent python_agent("python-agent", "http://localhost:8000");
auto future = python_agent.process(message);
auto result = future.get();
```

### Expose C++ Agent to Python

```cpp
#include <agenkit/transports/http_server.hpp>

auto agent = std::make_unique<MyAgent>();
HttpServer server(std::move(agent), "localhost:8080");
server.serve(); // Blocking

// Python can now call this agent:
// from agenkit.transports import HTTPClient
// cpp_agent = HTTPClient("http://localhost:8080")
// response = await cpp_agent.process(message)
```

---

## Performance

C++ provides exceptional performance:

- **Native performance** - Compiled to machine code
- **Zero-overhead abstractions** - Pay only for what you use
- **Stack allocation** - Minimal heap allocations
- **Move semantics** - Zero-copy operations
- **SIMD support** - Vectorized operations where applicable

Benchmarks show C++ performance similar to Rust (both 15-20x faster than Python).

---

## Contributing

Help improve C++ implementation:

1. **Report issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
2. **Improve docs**: Add Doxygen comments to code
3. **Add examples**: [Submit PR](https://github.com/scttfrdmn/agenkit/pulls)

---

## See Also

- **[Python API Reference](python.md)**: Python implementation
- **[Go API Reference](go.md)**: Go implementation
- **[Rust API Reference](rust.md)**: Rust implementation
- **[TypeScript API Reference](typescript.md)**: TypeScript implementation
- **[Cross-Language Guide](../guides/cross-language.md)**: Language interop
- **[C++ README](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-cpp/README.md)**: C++-specific features
- **[Build Guide](https://github.com/scttfrdmn/agenkit/blob/main/agenkit-cpp/docs/BUILD.md)**: Detailed build instructions

---

**Last Updated**: December 2025
**C++ Standard**: C++17
**CMake Version**: 3.16+
**Agenkit Version**: 0.29.2+
