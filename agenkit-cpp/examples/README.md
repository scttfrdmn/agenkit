# Agenkit C++ Examples

Comprehensive examples demonstrating all Agenkit patterns and features in modern C++17/20.

## Directory Structure

```
examples/
├── patterns/          # 11 core agentic patterns
├── adapters/          # LLM provider integrations (OpenAI, Anthropic, Ollama)
├── other/            # Basic usage, tools, transport, memory
├── tools/            # Reusable tool definitions
└── README.md         # This file
```

## Pattern Examples

All pattern examples use **mock agents** (no API keys required) to demonstrate the pattern mechanics in isolation. This makes them:
- ✅ Runnable without any external dependencies
- ✅ Fast and deterministic for learning
- ✅ Adapter-agnostic (work with any LLM provider)
- ✅ Perfect for understanding pattern behavior

| Pattern | File | Description |
|---------|------|-------------|
| **Reflection** | [patterns/reflection-pattern.cpp](patterns/reflection-pattern.cpp) | Iterative self-critique and refinement for quality improvement |
| **ReAct** | [patterns/react-pattern.cpp](patterns/react-pattern.cpp) | Reasoning and Acting - thought/action/observation cycles |
| **Planning** | [patterns/planning-pattern.cpp](patterns/planning-pattern.cpp) | Multi-step task decomposition and execution |
| **Task** | [patterns/task-pattern.cpp](patterns/task-pattern.cpp) | Structured task management with state tracking |
| **Multiagent** | [patterns/multiagent-pattern.cpp](patterns/multiagent-pattern.cpp) | Coordination between multiple specialized agents |
| **Orchestration** | [patterns/orchestration-pattern.cpp](patterns/orchestration-pattern.cpp) | Complex workflow management with dynamic routing |
| **Conversational** | [patterns/conversational-pattern.cpp](patterns/conversational-pattern.cpp) | Multi-turn conversations with context management |
| **Memory Hierarchy** | [patterns/memory-hierarchy-pattern.cpp](patterns/memory-hierarchy-pattern.cpp) | Working memory + long-term semantic storage |
| **Agents as Tools** | [patterns/agents-as-tools-pattern.cpp](patterns/agents-as-tools-pattern.cpp) | Expose agents as callable tools for composition |
| **Reasoning with Tools** | [patterns/reasoning-with-tools-pattern.cpp](patterns/reasoning-with-tools-pattern.cpp) | Advanced tool use with multi-step reasoning |
| **Autonomous** | [patterns/autonomous-pattern.cpp](patterns/autonomous-pattern.cpp) | Self-directed agents with goal-seeking behavior |

## Adapter Examples

Real LLM provider integrations for production use:

| Adapter | File | Use Case |
|---------|------|----------|
| **OpenAI** | [adapters/openai-basic.cpp](adapters/openai-basic.cpp) | GPT-4, GPT-3.5-turbo integration |
| **Anthropic** | [adapters/anthropic-basic.cpp](adapters/anthropic-basic.cpp) | Claude integration (Claude 3.5 Sonnet, Opus, Haiku) |
| **Ollama** | [adapters/ollama-basic.cpp](adapters/ollama-basic.cpp) | Local LLM inference (Llama 2, Mistral, etc.) |

## Other Examples

| Category | File | Description |
|----------|------|-------------|
| **Echo Agent** | [other/echo_agent.cpp](other/echo_agent.cpp) | Simple agent creation and message processing |
| **Agent Chain** | [other/agent_chain.cpp](other/agent_chain.cpp) | Sequential agent composition |
| **HTTP Transport** | [other/http_transport.cpp](other/http_transport.cpp) | HTTP-based agent communication |
| **Conversation Memory** | [other/conversation_memory.cpp](other/conversation_memory.cpp) | Multi-turn conversation state management |
| **ReAct Tools** | [other/react_tools_example.cpp](other/react_tools_example.cpp) | Tool integration with ReAct pattern |

## Reusable Tools

| Tool | File | Description |
|------|------|-------------|
| **Calculator** | [tools/calculator_tool.hpp](tools/calculator_tool.hpp) | Mathematical operations |
| **Search** | [tools/search_tool.hpp](tools/search_tool.hpp) | Mock search functionality |
| **Weather** | [tools/weather_tool.hpp](tools/weather_tool.hpp) | Weather data retrieval |

## Getting Started

### Prerequisites

- C++17 or later compiler (GCC 9+, Clang 10+, MSVC 2019+)
- CMake 3.15 or later
- vcpkg or system package manager for dependencies
- For adapter examples: API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY) or Ollama installation
- For pattern examples: **No API keys required!** Uses mock agents

### Dependencies

Core dependencies (automatically managed by CMake):
- nlohmann_json - JSON parsing
- cpr - HTTP client (for adapters)
- spdlog - Logging (optional)

### Building

```bash
# Create build directory
mkdir build && cd build

# Configure with CMake
cmake .. -DCMAKE_BUILD_TYPE=Release

# Build all examples
cmake --build .

# Or build specific example
cmake --build . --target reflection-pattern
```

### Running Examples

```bash
# Pattern examples (no API keys needed)
./build/examples/reflection-pattern
./build/examples/react-pattern
./build/examples/planning-pattern
./build/examples/multiagent-pattern

# Adapter examples (requires API keys or Ollama)
# OpenAI
export OPENAI_API_KEY="sk-..."
./build/examples/openai-basic

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
./build/examples/anthropic-basic

# Ollama (local, free)
# Install from https://ollama.ai then:
ollama pull llama2
./build/examples/ollama-basic

# Other examples
./build/examples/echo-agent
./build/examples/http-transport
./build/examples/conversation-memory
```

### CMake Integration

To use Agenkit in your project:

```cmake
find_package(agenkit REQUIRED)

add_executable(my_agent main.cpp)
target_link_libraries(my_agent PRIVATE agenkit::agenkit)
```

## Key Principles

### Pattern Examples Use Mock Agents

All pattern examples in `patterns/` use **mock agents** that simulate LLM behavior:

```cpp
/**
 * Mock agent - no API calls
 */
class WriterAgent : public core::Agent {
public:
    std::string name() const override {
        return "writer";
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        // Simulated behavior for demonstration
        std::string response = generateMockResponse(message);
        auto msg = core::Message::with_text("assistant", response);
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(msg)
        );
    }
};
```

**Why mock agents?**
- ✅ Learn pattern mechanics without API costs
- ✅ Fast, deterministic, reproducible
- ✅ No external dependencies or API keys
- ✅ Focus on pattern logic, not LLM responses

### Swapping Mock Agents for Real LLMs

Once you understand a pattern, swap the mock agent for a real LLM:

```cpp
// Development: Mock agent (from pattern example)
auto generator = std::make_shared<MockCodeGenerator>();

// Production: Real LLM (Ollama - free, local)
auto generator = std::make_shared<OllamaAgent>(OllamaConfig{
    .model = "llama2",
    .base_url = "http://localhost:11434"
});

// Production: Real LLM (OpenAI - paid, cloud)
auto generator = std::make_shared<OpenAIAgent>(OpenAIConfig{
    .model = "gpt-4",
    .api_key = std::getenv("OPENAI_API_KEY")
});

// Pattern works identically with all agents!
auto reflection = patterns::ReflectionAgent(generator, critic, config);
```

The pattern orchestration remains **identical** - only the agents change.

## Learning Path

We recommend following this progression:

### 1. Start with Patterns (Mock Agents)
Learn pattern mechanics without external dependencies:
```bash
./build/examples/reflection-pattern      # Iterative improvement
./build/examples/react-pattern           # Reasoning + Acting
./build/examples/planning-pattern        # Task decomposition
./build/examples/multiagent-pattern      # Agent coordination
```

### 2. Explore Adapters (Real LLMs)

#### Local Development (Free)
Start with Ollama for local, free LLM access:
```bash
# Install Ollama: https://ollama.ai
ollama pull llama2

# Run Ollama example
./build/examples/ollama-basic
```

**Ollama advantages:**
- ✅ Completely free
- ✅ Runs locally (no internet required)
- ✅ Fast for development
- ✅ Privacy-preserving
- ✅ Multiple models available (Llama 2, Mistral, CodeLlama, etc.)

#### Cloud Providers (Paid)
Move to cloud providers when ready:
```bash
# OpenAI (GPT-4)
export OPENAI_API_KEY="sk-..."
./build/examples/openai-basic

# Anthropic (Claude 3.5 Sonnet)
export ANTHROPIC_API_KEY="sk-ant-..."
./build/examples/anthropic-basic
```

### 3. Production Features
Add resilience and observability:
```bash
./build/examples/http-transport         # HTTP communication
./build/examples/conversation-memory    # State management
./build/examples/react-tools-example    # Tool integration
```

### 4. Advanced Patterns
Explore composition and specialized patterns:
```bash
./build/examples/autonomous-pattern
./build/examples/memory-hierarchy-pattern
./build/examples/orchestration-pattern
```

## Best Practices

### Modern C++ Features

Use modern C++17/20 features:
```cpp
// Smart pointers for memory management
auto agent = std::make_shared<MyAgent>();

// std::optional for nullable values
std::optional<std::string> result = tryExtract(message);
if (result) {
    std::cout << *result << std::endl;
}

// Structured bindings
auto [success, error] = result.into_parts();
```

### Error Handling

Use Result types for robust error handling:
```cpp
auto result = agent->process(message).get();
if (result.is_ok()) {
    auto response = result.unwrap();
    std::cout << "Success: " << response.content_as_str() << std::endl;
} else {
    auto error = result.unwrap_err();
    std::cerr << "Error: " << error.message << std::endl;
}
```

### Async Operations

All agent operations return `std::future`:
```cpp
// Get result synchronously
auto future = agent->process(message);
auto result = future.get();

// Async processing
auto future = agent->process(message);
// Do other work...
auto result = future.get();  // Wait for completion
```

### Resource Management

Use RAII for automatic cleanup:
```cpp
{
    auto agent = std::make_shared<MyAgent>();
    auto result = agent->process(message).get();
    // agent automatically cleaned up at scope exit
}
```

## Pattern Achievements (v0.31.0)

Agenkit C++ now has **full pattern parity** across all 4 languages (Python, Go, TypeScript, Rust):

✅ **11/11 patterns implemented**
- All patterns use consistent APIs
- Mock agents for demonstration
- Production-ready implementations
- Comprehensive documentation
- Zero-cost abstractions where possible

## Examples Statistics

- **Pattern Examples**: 11 (all use mock agents)
- **Adapter Examples**: 3 (OpenAI, Anthropic, Ollama)
- **Other Examples**: 5 (basic usage, transport, memory, tools)
- **Reusable Tools**: 3 (calculator, search, weather)
- **Total**: 19 comprehensive examples + 3 tool libraries

## Documentation Links

- **Main README**: [/README.md](../../README.md) - Project overview
- **API Documentation**: [/docs/API.md](../../docs/API.md) - Detailed API reference
- **Architecture**: [/ARCHITECTURE.md](../../ARCHITECTURE.md) - Design principles
- **Roadmap**: [/ROADMAP.md](../../ROADMAP.md) - Development status and plans
- **Python Examples**: [/examples/README.md](../../examples/README.md) - Python reference implementation

## Cross-Language Compatibility

All C++ examples are designed for cross-language interoperability:
- **HTTP Transport**: RESTful API for cross-language communication
- **gRPC Transport**: High-performance binary protocol (coming soon)
- **WebSocket Transport**: Real-time bidirectional messaging (coming soon)
- **Consistent APIs**: Same patterns work across all languages

Example: C++ agent ↔ Python agent via HTTP:
```bash
# Terminal 1: Start Python agent server
python examples/transport/http_example.py

# Terminal 2: Connect with C++ client
./build/examples/http-transport
```

## Why C++?

C++ brings several advantages to Agenkit:
- **Performance**: Native code execution, zero-overhead abstractions
- **Memory Control**: Fine-grained resource management
- **Portability**: Compile to any platform
- **Ecosystem**: Access to vast C/C++ library ecosystem
- **Embedded Systems**: Run agents on resource-constrained devices
- **Game Development**: Integrate AI agents into games
- **HPC**: High-performance computing and scientific applications

## Testing

Run the test suite:
```bash
cmake --build build --target test
```

All examples are production-ready and well-tested. See [tests/](../../tests/) for additional patterns.

## Compiler Compatibility

| Compiler | Minimum Version | Status |
|----------|----------------|---------|
| GCC | 9.0 | ✅ Fully supported |
| Clang | 10.0 | ✅ Fully supported |
| MSVC | 2019 (19.20) | ✅ Fully supported |
| AppleClang | 12.0 | ✅ Fully supported |

## Platform Support

| Platform | Architecture | Status |
|----------|-------------|---------|
| Linux | x86_64, ARM64 | ✅ Fully supported |
| macOS | x86_64, ARM64 (Apple Silicon) | ✅ Fully supported |
| Windows | x86_64 | ✅ Fully supported |
| WebAssembly | wasm32 | 🚧 Coming soon |

## Need Help?

- **Issues**: [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues)
- **Discussions**: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)
- **Documentation**: [/docs](../../docs/)
- **Tests**: [/tests](../../tests/) - 137+ test examples

## Next Steps

1. **Build the examples**: `cmake --build build`
2. **Run a pattern example**: Start with `reflection-pattern`
3. **Understand the pattern**: Read the code comments and output
4. **Try Ollama**: Free, local LLM for development (`ollama-basic`)
5. **Add a cloud provider**: OpenAI or Anthropic when ready
6. **Build something**: Combine patterns for your use case
7. **Optimize**: Profile and optimize with C++'s performance tools

Happy building! 🚀
