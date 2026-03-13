# C++ API Reference

**Namespaces:** `agenkit::core`, `agenkit::adapters`, `agenkit::patterns`, `agenkit::techniques`
**Standard:** C++20
**Build system:** CMake 3.20+

---

## Build Integration

### CMake — installed package

```cmake
find_package(agenkit REQUIRED)
target_link_libraries(my_target agenkit::agenkit)
```

### CMake — FetchContent

```cmake
include(FetchContent)
FetchContent_Declare(agenkit
    GIT_REPOSITORY https://github.com/scttfrdmn/agenkit.git
    GIT_TAG        main
    SOURCE_SUBDIR  agenkit-cpp
)
FetchContent_MakeAvailable(agenkit)
target_link_libraries(my_target agenkit::agenkit)
```

### Headers

```cpp
#include <agenkit/core/message.hpp>
#include <agenkit/core/agent.hpp>
#include <agenkit/core/tool.hpp>
#include <agenkit/adapters/claude_agent.hpp>
#include <agenkit/adapters/openai_agent.hpp>
#include <agenkit/patterns/reflection.hpp>
// … etc.
```

---

## Core Types

**Namespace:** `agenkit::core`

### `Message`

```cpp
class Message {
public:
    std::string role;
    std::map<std::string, std::string> metadata;

    // Factory — preferred construction
    static Message with_text(std::string role, std::string content);

    // Content access
    std::string content_as_str() const;

    // Metadata helpers
    void set_metadata(std::string key, std::string value);
    std::optional<std::string> get_metadata(const std::string& key) const;
};
```

### `Agent` (virtual base)

```cpp
class Agent {
public:
    virtual ~Agent() = default;

    virtual std::future<Result<Message, AgentError>>
        process(Message message) = 0;

    virtual std::string name() const = 0;
    virtual std::vector<std::string> capabilities() const { return {}; }
};
```

### `Result<T, E>`

```cpp
template<typename T, typename E>
class Result {
public:
    static Result ok(T value);
    static Result err(E error);

    bool is_ok() const;
    bool is_err() const;
    T&       value();          // throws if err
    const T& value() const;
    E&       error();          // throws if ok
};
```

### `AgentError`

```cpp
enum class AgentErrorKind {
    Adapter,
    Timeout,
    CircuitOpen,
    BudgetExceeded,
    Checkpoint,
    Other,
};

class AgentError {
public:
    AgentErrorKind kind;
    std::string    message;
};
```

### `Tool`

```cpp
class Tool {
public:
    std::string name;
    std::string description;
    nlohmann::json parameters;   // JSON Schema

    virtual ~Tool() = default;
    virtual std::future<nlohmann::json>
        execute(nlohmann::json args) = 0;
};
```

---

## LLM Adapters

**Namespace:** `agenkit::adapters`

### `ClaudeAgent` (Anthropic)

```cpp
#include <agenkit/adapters/claude_agent.hpp>

struct ClaudeConfig {
    std::string model       = "claude-sonnet-4-6";
    std::string api_key;              // or ANTHROPIC_API_KEY env var
    int         max_tokens  = 4096;
    double      temperature = 1.0;
};

class ClaudeAgent : public core::Agent {
public:
    explicit ClaudeAgent(ClaudeConfig config);
    std::future<Result<core::Message, core::AgentError>>
        process(core::Message message) override;
    std::string name() const override;
};
```

### `OpenAIAgent`

```cpp
#include <agenkit/adapters/openai_agent.hpp>

struct OpenAIConfig {
    std::string model       = "gpt-4o";
    std::string api_key;              // or OPENAI_API_KEY env var
    int         max_tokens  = 4096;
    double      temperature = 0.7;
};

class OpenAIAgent : public core::Agent {
public:
    explicit OpenAIAgent(OpenAIConfig config);
    std::future<Result<core::Message, core::AgentError>>
        process(core::Message message) override;
    std::string name() const override;
};
```

### Additional Adapters

| Class | Header | Notes |
|-------|--------|-------|
| `BedrockAgent` | `adapters/bedrock_agent.hpp` | AWS Bedrock |
| `GeminiAgent` | `adapters/gemini_agent.hpp` | Google Gemini |
| `OllamaAgent` | `adapters/ollama_agent.hpp` | Local Ollama |
| `LiteLLMAgent` | `adapters/litellm_agent.hpp` | LiteLLM proxy |
| `EchoAgent` | `adapters/echo_agent.hpp` | Testing stub |

---

## Patterns

**Namespace:** `agenkit::patterns`

All pattern classes inherit from `core::Agent`.

| Class | Header | Key Constructor Parameters |
|-------|--------|---------------------------|
| `ReflectionAgent` | `patterns/reflection.hpp` | `agent`, `max_iterations = 3` |
| `ReactAgent` | `patterns/react.hpp` | `agent`, `tools: vector<shared_ptr<Tool>>` |
| `AgentsAsToolsAgent` | `patterns/agents_as_tools.hpp` | `agent`, `sub_agents` |
| `OrchestrationAgent` | `patterns/orchestration.hpp` | `orchestrator`, `workers` |
| `ReasoningWithToolsAgent` | `patterns/reasoning_with_tools.hpp` | `agent`, `tools`, `max_steps = 10` |
| `ConversationalAgent` | `patterns/conversational.hpp` | `agent`, optional `memory` |
| `TaskAgent` | `patterns/task.hpp` | `agent`, `task_description` |
| `MultiagentAgent` | `patterns/multiagent.hpp` | `agents: vector<shared_ptr<Agent>>` |
| `PlanningAgent` | `patterns/planning.hpp` | `planner`, `executor` |
| `AutonomousAgent` | `patterns/autonomous.hpp` | `agent`, `max_iterations = 10` |
| `SequentialAgent` | `patterns/sequential.hpp` | `agents: vector<shared_ptr<Agent>>` |
| `ParallelAgent` | `patterns/parallel.hpp` | `agents`, optional aggregator |
| `RouterAgent` | `patterns/router.hpp` | `router`, `routes: map<string, shared_ptr<Agent>>` |
| `FallbackAgent` | `patterns/fallback.hpp` | `primary`, `fallbacks` |
| `CollaborativeAgent` | `patterns/collaborative.hpp` | `agents`, `coordinator` |
| `HumanInLoopAgent` | `patterns/human_in_loop.hpp` | `agent`, approval callback |
| `SupervisorAgent` | `patterns/supervisor.hpp` | `supervisor`, `workers` |
| `WorkingMemoryAgent` | `patterns/memory.hpp` | `agent`, `memory` |

---

## Middleware

**Namespace:** `agenkit::middleware`
**Header:** `<agenkit/middleware/middleware.hpp>`

All middleware classes inherit from `core::Agent`.

| Class | Key Constructor Parameters |
|-------|---------------------------|
| `RetryMiddleware` | `agent`, `max_attempts = 3`, `backoff_base_ms = 1000` |
| `TimeoutMiddleware` | `agent`, `timeout_ms` |
| `RateLimiter` | `agent`, `requests_per_second`, `burst` |
| `CircuitBreaker` | `agent`, `failure_threshold = 5`, `recovery_timeout_ms = 60000` |
| `BatchingMiddleware` | `agent`, `max_batch_size = 10`, `max_wait_ms = 100` |
| `CachingMiddleware` | `agent`, `ttl_ms = 0` (0 = no expiry) |
| `PerUserRateLimiter` | `agent`, per-user `requests_per_second` |

---

## Reasoning Techniques

**Namespace:** `agenkit::techniques::reasoning`

| Class | Header | Key Parameters |
|-------|--------|---------------|
| `ChainOfThoughtAgent` | `techniques/reasoning/chain_of_thought.hpp` | `agent`, `steps = 3` |
| `TreeOfThoughtAgent` | `techniques/reasoning/tree_of_thought.hpp` | `agent`, `branches = 3`, `depth = 3` |
| `SelfConsistencyAgent` | `techniques/reasoning/self_consistency.hpp` | `agent`, `samples = 5` |
| `GraphOfThoughtAgent` | `techniques/reasoning/graph_of_thought.hpp` | `agent`, `max_nodes = 10` |
| `PlanAndSolveAgent` | `techniques/reasoning/plan_and_solve.hpp` | `planner`, `solver` |
| `LeastToMostAgent` | `techniques/reasoning/least_to_most.hpp` | `agent`, `max_subproblems = 5` |

---

## Memory

**Namespace:** `agenkit::memory`

```cpp
class Memory {
public:
    virtual ~Memory() = default;
    virtual void add(const core::Message& message) = 0;
    virtual std::vector<core::Message> history() const = 0;
    virtual void clear() = 0;
};
```

| Class | Notes |
|-------|-------|
| `InMemoryStore` | Ephemeral, bounded ring buffer |
| `HierarchicalMemory` | Short-term + long-term |
| `VectorMemory` | Embedding-based retrieval |

---

## Error Handling

Functions returning `std::future<Result<T, AgentError>>` never throw from the async chain. Synchronous constructors may throw `std::invalid_argument` for missing required fields (e.g., empty `api_key`).

Inspect `AgentError::kind` to distinguish error categories and `AgentError::message` for a human-readable description.
