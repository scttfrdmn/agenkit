# Agenkit C++ API Reference

Complete API documentation for Agenkit-C++ v0.75.0.

## Table of Contents

- [Namespaces](#namespaces)
- [Core Types](#core-types)
  - [Message](#message)
  - [MessageContent](#messagecontent)
  - [Agent](#agent)
  - [AgentError](#agenterror)
  - [Result](#result)
  - [Tool](#tool)
  - [ToolResult](#toolresult)
- [Built-in Agents](#built-in-agents)
  - [EchoAgent](#echoagent)
  - [MockAgent](#mockagent)
- [LLM Adapters](#llm-adapters)
  - [ClaudeAgent](#claudeagent)
  - [OpenAIAgent](#openalagent)
  - [OllamaAgent](#ollamaagent)
  - [OpenAICompatibleAgent](#openaicompatibleagent)
- [Middleware](#middleware)
  - [RetryDecorator](#retrydecorator)
  - [CircuitBreakerDecorator](#circuitbreakerdecorator)
  - [TimeoutDecorator](#timeoutdecorator)
  - [RateLimiterDecorator](#ratelimiterdecorator)
  - [LoggingDecorator](#loggingdecorator)
  - [CachingDecorator](#cachingdecorator)
  - [ValidationDecorator](#validationdecorator)
  - [BudgetDecorator](#budgetdecorator)
- [Patterns](#patterns)
  - [SequentialAgent](#sequentialagent)
  - [ParallelAgent](#parallelagent)
  - [ReflectionAgent](#reflectionagent)
  - [ReActAgent](#reactagent)
  - [PlanningAgent](#planningagent)
  - [TaskAgent](#taskagent)
  - [ConversationalAgent](#conversationalagent)
  - [AgentsAsToolsAgent](#agentsastoolsagent)
  - [AutonomousAgent](#autonomousagent)
  - [MultiagentOrchestrator](#multiagentorchestrator)
  - [MemoryHierarchyAgent](#memoryhierarchyagent)
- [Observability](#observability)
  - [TracingMiddleware](#tracingmiddleware)
  - [MetricsMiddleware](#metricsmiddleware)
- [Transport](#transport)
  - [HttpServer](#httpserver)
  - [HttpAgent](#httpagent)
- [Utility Functions](#utility-functions)

---

## Namespaces

```cpp
agenkit::core        // Message, Agent, AgentError, Result
agenkit::adapters    // LLM adapters (Claude, OpenAI, Ollama, ...)
agenkit::middleware  // RetryDecorator, TimeoutDecorator, ...
agenkit::patterns    // SequentialAgent, ReflectionAgent, ...
agenkit::transports  // HttpServer, HttpAgent
agenkit::observability // TracingMiddleware, MetricsMiddleware, ...
```

All core types are also available under `using namespace agenkit::core;`.

---

## Core Types

### Message

The fundamental unit of communication between agents.

**Header**: `#include <agenkit/core/message.hpp>`

```cpp
namespace agenkit::core {

class Message {
public:
    // --- Constructors ---

    // Construct a text message
    static Message with_text(const std::string& role,
                              const std::string& text);

    // Construct a JSON message
    static Message with_json(const std::string& role,
                              const nlohmann::json& data);

    // Default constructor (empty content)
    Message();

    // Copy and move constructors (value semantics)
    Message(const Message&);
    Message(Message&&) noexcept;
    Message& operator=(const Message&);
    Message& operator=(Message&&) noexcept;

    // --- Accessors ---

    // The role of this message ("user", "assistant", "system", "tool")
    const std::string& role() const;

    // The message content
    const MessageContent& content() const;
    MessageContent& content();

    // --- Metadata ---

    // Set a metadata key-value pair
    void set_metadata(const std::string& key, const std::string& value);

    // Get metadata value (returns empty optional if key absent)
    std::optional<std::string> get_metadata(const std::string& key) const;

    // Check if metadata key exists
    bool has_metadata(const std::string& key) const;

    // Get all metadata as a map
    const std::map<std::string, std::string>& metadata() const;

    // Remove a metadata key
    void remove_metadata(const std::string& key);

    // --- Serialization ---

    // Convert to JSON
    nlohmann::json to_json() const;

    // Construct from JSON
    static Message from_json(const nlohmann::json& j);

    // --- Comparison ---
    bool operator==(const Message& other) const;
    bool operator!=(const Message& other) const;
};

} // namespace agenkit::core
```

**Example:**
```cpp
auto msg = Message::with_text("user", "What is RAII?");
msg.set_metadata("session_id", "sess-42");
msg.set_metadata("user_id", "u-17");

auto session = msg.get_metadata("session_id");  // std::optional<std::string>
assert(session.has_value());
assert(session.value() == "sess-42");

auto json = msg.to_json();
auto restored = Message::from_json(json);
assert(msg == restored);
```

---

### MessageContent

Holds either text or structured JSON content.

**Header**: `#include <agenkit/core/message.hpp>`

```cpp
namespace agenkit::core {

class MessageContent {
public:
    // --- Constructors ---
    static MessageContent from_text(const std::string& text);
    static MessageContent from_json(const nlohmann::json& data);

    // --- Type queries ---
    bool is_text() const;
    bool is_json() const;

    // --- Accessors (throw if wrong type) ---
    const std::string& as_text() const;
    const nlohmann::json& as_json() const;

    // --- Safe access ---
    std::optional<std::string>      text_opt() const;
    std::optional<nlohmann::json>   json_opt() const;

    // --- Conversion ---
    // Always returns a string representation
    std::string to_string() const;

    // Convert to JSON (wraps text in {"text": "..."} if needed)
    nlohmann::json to_json() const;
};

} // namespace agenkit::core
```

---

### Agent

Abstract base class for all agents.

**Header**: `#include <agenkit/core/agent.hpp>`

```cpp
namespace agenkit::core {

class Agent {
public:
    virtual ~Agent() = default;

    // --- Required interface ---

    // Stable, human-readable name for this agent (used in logs/traces)
    virtual std::string name() const = 0;

    // Process a message asynchronously
    // Returns a future that resolves to ok(Message) or err(AgentError)
    virtual std::future<Result<Message, AgentError>>
    process(Message message) = 0;

    // --- Optional interface ---

    // Return a list of capability tags (e.g., {"search", "math"})
    virtual std::vector<std::string> capabilities() const;

    // Return introspection data (patterns, config, stats)
    virtual nlohmann::json introspect() const;

    // Process a message and stream the response chunk by chunk
    virtual void process_stream(
        Message message,
        std::function<void(Message)>     on_chunk,
        std::function<void(AgentError)>  on_error,
        std::function<void()>            on_complete
    );
};

// Convenience function: create a resolved future
template<typename T>
std::future<T> make_ready_future(T value);

} // namespace agenkit::core
```

**Implementing a Custom Agent:**
```cpp
class TranslatorAgent : public agenkit::core::Agent {
public:
    explicit TranslatorAgent(const std::string& target_lang)
        : target_lang_(target_lang) {}

    std::string name() const override {
        return "translator-" + target_lang_;
    }

    std::future<agenkit::core::Result<agenkit::core::Message,
                                       agenkit::core::AgentError>>
    process(agenkit::core::Message message) override {
        return std::async(std::launch::async,
            [this, msg = std::move(message)]() {
                auto text = msg.content().as_text();
                auto translated = translate(text, target_lang_);
                auto response = agenkit::core::Message::with_text(
                    "assistant", translated
                );
                return agenkit::core::Result<
                    agenkit::core::Message,
                    agenkit::core::AgentError>::ok(std::move(response));
            });
    }

    std::vector<std::string> capabilities() const override {
        return {"translation", "language-" + target_lang_};
    }

private:
    std::string target_lang_;
    std::string translate(const std::string& text,
                           const std::string& lang);
};
```

---

### AgentError

Represents an error from agent processing.

**Header**: `#include <agenkit/core/agent_error.hpp>`

```cpp
namespace agenkit::core {

enum class AgentErrorCode {
    Unknown,
    ProcessingFailed,
    Timeout,
    RateLimited,
    InvalidInput,
    NetworkError,
    AuthFailed,
    CircuitOpen,
    BudgetExceeded,
    ValidationFailed,
    MaxIterationsReached,
};

class AgentError {
public:
    // Constructors
    AgentError(AgentErrorCode code, const std::string& message);
    explicit AgentError(const std::string& message);  // code = Unknown

    // Accessors
    AgentErrorCode code() const;
    const std::string& message() const;

    // Optional structured details
    const nlohmann::json& details() const;
    AgentError& with_details(const nlohmann::json& details);

    // Serialization
    nlohmann::json to_json() const;
    static AgentError from_json(const nlohmann::json& j);

    // Comparison
    bool operator==(const AgentError& other) const;
    bool operator!=(const AgentError& other) const;
};

} // namespace agenkit::core
```

**Example:**
```cpp
if (result.is_err()) {
    auto err = result.error();
    switch (err.code()) {
        case AgentErrorCode::Timeout:
            std::cerr << "Request timed out\n";
            break;
        case AgentErrorCode::RateLimited:
            std::cerr << "Rate limited — wait and retry\n";
            break;
        case AgentErrorCode::CircuitOpen:
            std::cerr << "Circuit breaker open — service unavailable\n";
            break;
        default:
            std::cerr << "Error: " << err.message() << "\n";
    }
}
```

---

### Result

A discriminated union of success and failure. Analogous to Rust's `Result<T, E>`.

**Header**: `#include <agenkit/core/result.hpp>`

```cpp
namespace agenkit::core {

template<typename T, typename E>
class Result {
public:
    // --- Constructors ---
    static Result ok(T value);
    static Result err(E error);

    // --- State queries ---
    bool is_ok()  const noexcept;
    bool is_err() const noexcept;

    // --- Value access (throws if wrong state) ---
    T&       value();
    const T& value() const;
    E&       error();
    const E& error() const;

    // --- Safe access ---
    std::optional<T> value_opt() const;
    std::optional<E> error_opt() const;

    // --- Transformations ---

    // Apply f to value if ok, else propagate error
    template<typename F>
    auto map(F&& f) -> Result<decltype(f(std::declval<T>())), E>;

    // Apply f to error if err, else propagate value
    template<typename F>
    auto map_err(F&& f) -> Result<T, decltype(f(std::declval<E>()))>;

    // Apply f to value if ok, f must return Result<U, E>
    template<typename F>
    auto and_then(F&& f) -> decltype(f(std::declval<T>()));

    // Return default value if err
    T value_or(T default_value) const;
};

} // namespace agenkit::core
```

**Chaining Results:**
```cpp
auto result = agent->process(message).get()
    .map([](Message msg) {
        return msg.content().as_text();
    })
    .map([](std::string text) {
        return "Processed: " + text;
    });

if (result.is_ok()) {
    std::cout << result.value() << "\n";
}
```

---

### Tool

Interface for tools that agents can invoke.

**Header**: `#include <agenkit/core/tool.hpp>`

```cpp
namespace agenkit::core {

struct ToolResult {
    bool        success;
    std::string output;
    std::string error_message;  // non-empty if !success
};

class Tool {
public:
    virtual ~Tool() = default;

    // Unique name used to select this tool
    virtual std::string name() const = 0;

    // Human-readable description for the LLM
    virtual std::string description() const = 0;

    // JSON Schema for the parameters object
    virtual nlohmann::json parameters_schema() const = 0;

    // Execute the tool with the given parameters
    virtual ToolResult execute(
        const std::map<std::string, nlohmann::json>& params
    ) const = 0;

    // Whether this tool is safe to call without user confirmation
    virtual bool is_safe() const { return true; }
};

} // namespace agenkit::core
```

**Implementing a Tool:**
```cpp
class CalculatorTool : public agenkit::core::Tool {
public:
    std::string name() const override { return "calculator"; }

    std::string description() const override {
        return "Evaluate a mathematical expression";
    }

    nlohmann::json parameters_schema() const override {
        return {
            {"type", "object"},
            {"properties", {
                {"expression", {
                    {"type", "string"},
                    {"description", "Math expression to evaluate, e.g. '2 + 2'"}
                }}
            }},
            {"required", {"expression"}}
        };
    }

    agenkit::core::ToolResult execute(
        const std::map<std::string, nlohmann::json>& params
    ) const override {
        auto expr = params.at("expression").get<std::string>();
        double result = evaluate_expression(expr);
        return {true, std::to_string(result), ""};
    }

private:
    double evaluate_expression(const std::string& expr) const;
};
```

---

## Built-in Agents

### EchoAgent

Returns the input message unchanged. Useful for testing pipelines.

**Header**: `#include <agenkit/adapters/echo_agent.hpp>`

```cpp
namespace agenkit::adapters {

class EchoAgent : public core::Agent {
public:
    EchoAgent();
    explicit EchoAgent(const std::string& prefix);  // Prepends prefix to response

    std::string name() const override;
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::adapters
```

### MockAgent

Cycles through predefined responses. Used in tests and examples.

**Header**: `#include <agenkit/test_utils/mock_agent.hpp>`

```cpp
namespace agenkit::test_utils {

class MockAgent : public core::Agent {
public:
    // Construct with fixed responses (cycles through them)
    explicit MockAgent(std::vector<std::string> responses);

    // Construct with a single response
    explicit MockAgent(const std::string& response);

    std::string name() const override;
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // --- Test helpers ---
    size_t call_count() const;
    void   reset_call_count();

    // Returns all messages received (copies)
    std::vector<core::Message> received_messages() const;
};

class FailingMockAgent : public core::Agent {
public:
    explicit FailingMockAgent(core::AgentErrorCode code,
                               const std::string& message = "mock error");

    std::string name() const override;
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::test_utils
```

---

## LLM Adapters

### ClaudeAgent

Connects to Anthropic's Claude models.

**Header**: `#include <agenkit/adapters/claude_agent.hpp>`

```cpp
namespace agenkit::adapters {

struct ClaudeModels {
    static constexpr const char* SONNET_4    = "claude-sonnet-4-5";
    static constexpr const char* OPUS_4      = "claude-opus-4-5";
    static constexpr const char* HAIKU_3     = "claude-3-haiku-20240307";
    static constexpr const char* SONNET_3_5  = "claude-3-5-sonnet-20241022";
};

struct ClaudeConfig {
    std::string api_key;
    std::string model       = ClaudeModels::SONNET_4;
    double      temperature = 1.0;   // 0.0 – 1.0, validated
    int         max_tokens  = 4096;  // > 0, validated
    double      top_p       = 1.0;   // 0.0 – 1.0, validated
    std::string base_url    = "https://api.anthropic.com";
    int         timeout_ms  = 30000;
};

class ClaudeAgent : public core::Agent {
public:
    explicit ClaudeAgent(const ClaudeConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    void process_stream(
        core::Message message,
        std::function<void(core::Message)>     on_chunk,
        std::function<void(core::AgentError)>  on_error,
        std::function<void()>                  on_complete
    ) override;

    // Access token usage from last response
    struct TokenUsage {
        int input_tokens;
        int output_tokens;
    };
    std::optional<TokenUsage> last_token_usage() const;
};

} // namespace agenkit::adapters
```

### OpenAIAgent

Connects to OpenAI's GPT models.

**Header**: `#include <agenkit/adapters/openai_agent.hpp>`

```cpp
namespace agenkit::adapters {

struct OpenAIConfig {
    std::string api_key;
    std::string model       = "gpt-4-turbo";
    double      temperature = 1.0;   // 0.0 – 2.0, validated
    int         max_tokens  = 4096;  // > 0, validated
    double      top_p       = 1.0;
    std::string base_url    = "https://api.openai.com/v1";
    int         timeout_ms  = 30000;
};

class OpenAIAgent : public core::Agent {
public:
    explicit OpenAIAgent(const OpenAIConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    void process_stream(
        core::Message message,
        std::function<void(core::Message)>     on_chunk,
        std::function<void(core::AgentError)>  on_error,
        std::function<void()>                  on_complete
    ) override;
};

} // namespace agenkit::adapters
```

### OllamaAgent

Connects to a locally-running Ollama instance (free, private).

**Header**: `#include <agenkit/adapters/ollama_agent.hpp>`

```cpp
namespace agenkit::adapters {

struct OllamaConfig {
    std::string host       = "http://localhost:11434";
    std::string model      = "llama3.3";
    double      temperature = 0.8;
    int         max_tokens  = 2048;
    int         timeout_ms  = 60000;  // local models may be slow
};

class OllamaAgent : public core::Agent {
public:
    explicit OllamaAgent(const OllamaConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // Check if Ollama server is reachable
    bool is_available() const;
};

} // namespace agenkit::adapters
```

### OpenAICompatibleAgent

Connects to any OpenAI-compatible API (vLLM, llama.cpp, SGLang, TGI, etc.).

**Header**: `#include <agenkit/adapters/openai_compatible_agent.hpp>`

```cpp
namespace agenkit::adapters {

struct OpenAICompatibleConfig {
    std::string base_url;
    std::string model;
    std::string api_key    = "";    // Optional for local deployments
    double      temperature = 0.8;
    int         max_tokens  = 2048;
    int         timeout_ms  = 60000;
};

// Pre-built configs for common local deployments
struct OpenAICompatibleProviders {
    static OpenAICompatibleConfig vllm(const std::string& model,
                                        const std::string& host = "http://localhost:8000");
    static OpenAICompatibleConfig llamacpp(const std::string& model,
                                            const std::string& host = "http://localhost:8080");
    static OpenAICompatibleConfig sglang(const std::string& model,
                                          const std::string& host = "http://localhost:30000");
    static OpenAICompatibleConfig tgi(const std::string& model,
                                       const std::string& host = "http://localhost:8080");
    static OpenAICompatibleConfig lmstudio(const std::string& model,
                                            const std::string& host = "http://localhost:1234");
};

class OpenAICompatibleAgent : public core::Agent {
public:
    explicit OpenAICompatibleAgent(const OpenAICompatibleConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::adapters
```

---

## Middleware

All middleware wraps an existing `Agent` (the decorator pattern). Each decorator is itself an `Agent`, so they compose freely.

### RetryDecorator

Retries failed operations with exponential backoff.

**Header**: `#include <agenkit/middleware/retry_decorator.hpp>`

```cpp
namespace agenkit::middleware {

struct RetryConfig {
    int    max_attempts     = 3;
    int    initial_delay_ms = 100;
    int    max_delay_ms     = 10000;
    double backoff_multiplier = 2.0;
    // Retry only on these error codes (empty = retry all)
    std::set<core::AgentErrorCode> retryable_codes = {
        core::AgentErrorCode::NetworkError,
        core::AgentErrorCode::RateLimited,
        core::AgentErrorCode::Timeout,
    };
};

class RetryDecorator : public core::Agent {
public:
    RetryDecorator(std::shared_ptr<core::Agent> inner, int max_attempts,
                    int initial_delay_ms = 100);

    explicit RetryDecorator(std::shared_ptr<core::Agent> inner,
                             const RetryConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // Metrics
    struct Stats {
        size_t total_calls;
        size_t total_retries;
        size_t successful_first_attempt;
    };
    Stats stats() const;
    void  reset_stats();
};

} // namespace agenkit::middleware
```

### CircuitBreakerDecorator

Prevents cascading failures by opening the circuit when failure rate is too high.

**Header**: `#include <agenkit/middleware/circuit_breaker_decorator.hpp>`

```cpp
namespace agenkit::middleware {

enum class CircuitState { Closed, Open, HalfOpen };

struct CircuitBreakerConfig {
    int    failure_threshold   = 5;      // Consecutive failures to open
    int    recovery_timeout_ms = 30000;  // Time before trying again
    int    half_open_max       = 3;      // Requests to allow in HalfOpen state
    double success_rate_threshold = 0.5; // Required in HalfOpen to close
};

class CircuitBreakerDecorator : public core::Agent {
public:
    CircuitBreakerDecorator(std::shared_ptr<core::Agent> inner,
                             int failure_threshold,
                             int recovery_timeout_ms = 30000);

    explicit CircuitBreakerDecorator(std::shared_ptr<core::Agent> inner,
                                      const CircuitBreakerConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    CircuitState state() const;
    void         force_open();
    void         force_close();
    void         reset();
};

} // namespace agenkit::middleware
```

### TimeoutDecorator

Cancels requests that exceed a time budget.

**Header**: `#include <agenkit/middleware/timeout_decorator.hpp>`

```cpp
namespace agenkit::middleware {

class TimeoutDecorator : public core::Agent {
public:
    TimeoutDecorator(std::shared_ptr<core::Agent> inner, int timeout_ms);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    void set_timeout_ms(int timeout_ms);
    int  timeout_ms() const;
};

} // namespace agenkit::middleware
```

### RateLimiterDecorator

Enforces a maximum request rate using a sliding window.

**Header**: `#include <agenkit/middleware/rate_limiter_decorator.hpp>`

```cpp
namespace agenkit::middleware {

class RateLimiterDecorator : public core::Agent {
public:
    // Allow at most max_requests within window_ms
    RateLimiterDecorator(std::shared_ptr<core::Agent> inner,
                          int max_requests,
                          int window_ms = 1000);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // Current utilization (0.0 – 1.0)
    double utilization() const;
};

} // namespace agenkit::middleware
```

### LoggingDecorator

Logs all requests and responses using the agenkit logging system.

**Header**: `#include <agenkit/middleware/logging_decorator.hpp>`

```cpp
namespace agenkit::middleware {

enum class LogLevel { Trace, Debug, Info, Warn, Error };

class LoggingDecorator : public core::Agent {
public:
    LoggingDecorator(std::shared_ptr<core::Agent> inner,
                      LogLevel level = LogLevel::Info);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::middleware
```

### CachingDecorator

Caches responses to avoid repeated identical requests.

**Header**: `#include <agenkit/middleware/caching_decorator.hpp>`

```cpp
namespace agenkit::middleware {

struct CacheConfig {
    size_t max_entries  = 1000;
    int    ttl_ms       = 300000;  // 5 minutes
    bool   case_insensitive = false;
};

class CachingDecorator : public core::Agent {
public:
    CachingDecorator(std::shared_ptr<core::Agent> inner, const CacheConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    size_t hit_count()  const;
    size_t miss_count() const;
    double hit_rate()   const;
    void   clear_cache();
};

} // namespace agenkit::middleware
```

### ValidationDecorator

Validates input messages before forwarding to the inner agent.

**Header**: `#include <agenkit/middleware/validation_decorator.hpp>`

```cpp
namespace agenkit::middleware {

using Validator = std::function<std::optional<std::string>(const core::Message&)>;
// Return empty optional if valid, or an error string if invalid

class ValidationDecorator : public core::Agent {
public:
    ValidationDecorator(std::shared_ptr<core::Agent> inner,
                         Validator validator);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::middleware
```

**Example:**
```cpp
auto validator = [](const core::Message& msg) -> std::optional<std::string> {
    auto text = msg.content().as_text();
    if (text.empty()) {
        return "Message content must not be empty";
    }
    if (text.length() > 10000) {
        return "Message content exceeds 10000 characters";
    }
    return std::nullopt;  // valid
};

auto validated = std::make_shared<ValidationDecorator>(base_agent, validator);
```

### BudgetDecorator

Tracks token/cost usage and rejects requests when budget is exhausted.

**Header**: `#include <agenkit/middleware/budget_decorator.hpp>`

```cpp
namespace agenkit::middleware {

struct BudgetConfig {
    double max_tokens = 1'000'000.0;
    double max_cost   = 10.0;         // In USD
    double cost_per_input_token  = 0.000003;
    double cost_per_output_token = 0.000015;
};

class BudgetDecorator : public core::Agent {
public:
    BudgetDecorator(std::shared_ptr<core::Agent> inner,
                     const BudgetConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    double tokens_used()    const;
    double cost_used()      const;
    double tokens_remaining() const;
    double cost_remaining()   const;
    void   reset_budget();
};

} // namespace agenkit::middleware
```

---

## Patterns

### SequentialAgent

Processes a message through a chain of agents, passing each output as the next input.

**Header**: `#include <agenkit/patterns/sequential_agent.hpp>`

```cpp
namespace agenkit::patterns {

class SequentialAgent : public core::Agent {
public:
    explicit SequentialAgent(std::vector<std::shared_ptr<core::Agent>> agents);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // Add an agent to the end of the chain
    void add_agent(std::shared_ptr<core::Agent> agent);

    size_t agent_count() const;
};

} // namespace agenkit::patterns
```

### ParallelAgent

Dispatches a message to multiple agents concurrently and aggregates results.

**Header**: `#include <agenkit/patterns/parallel_agent.hpp>`

```cpp
namespace agenkit::patterns {

enum class AggregationStrategy {
    Concatenate,    // Join all responses
    FirstSuccess,   // Return the first ok result
    Majority,       // Return the majority response (requires parsing)
    Custom,         // Use a user-provided aggregator
};

using Aggregator = std::function<
    core::Result<core::Message, core::AgentError>(
        std::vector<core::Result<core::Message, core::AgentError>>
    )>;

class ParallelAgent : public core::Agent {
public:
    ParallelAgent(std::vector<std::shared_ptr<core::Agent>> agents,
                   AggregationStrategy strategy = AggregationStrategy::Concatenate);

    ParallelAgent(std::vector<std::shared_ptr<core::Agent>> agents,
                   Aggregator custom_aggregator);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::patterns
```

### ReflectionAgent

Implements iterative self-improvement: draft, critique, refine.

**Header**: `#include <agenkit/patterns/reflection_agent.hpp>`

```cpp
namespace agenkit::patterns {

class ReflectionAgent : public core::Agent {
public:
    ReflectionAgent(std::shared_ptr<core::Agent> generator,
                     std::shared_ptr<core::Agent> critic,
                     int max_iterations = 3,
                     const std::string& critique_prompt = "Review and improve:");

    // When generator == critic (same model)
    ReflectionAgent(std::shared_ptr<core::Agent> agent,
                     int max_iterations = 3);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    int   max_iterations() const;
    void  set_max_iterations(int n);
};

} // namespace agenkit::patterns
```

### ReActAgent

Reason + Act: interleaves thinking steps with tool invocations.

**Header**: `#include <agenkit/patterns/react_agent.hpp>`

```cpp
namespace agenkit::patterns {

class ReActAgent : public core::Agent {
public:
    ReActAgent(std::shared_ptr<core::Agent> llm,
                std::vector<std::shared_ptr<core::Tool>> tools,
                int max_iterations = 10);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    void add_tool(std::shared_ptr<core::Tool> tool);
    void remove_tool(const std::string& tool_name);

    // Access the trace of thoughts and actions
    struct Step {
        std::string thought;
        std::string action;
        std::string observation;
    };
    std::vector<Step> last_trace() const;
};

} // namespace agenkit::patterns
```

### PlanningAgent

Decomposes a complex task into a plan, then executes each step.

**Header**: `#include <agenkit/patterns/planning_agent.hpp>`

```cpp
namespace agenkit::patterns {

class PlanningAgent : public core::Agent {
public:
    PlanningAgent(std::shared_ptr<core::Agent> planner,
                   std::shared_ptr<core::Agent> executor,
                   int max_steps = 10);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // The plan generated for the last request
    std::vector<std::string> last_plan() const;
};

} // namespace agenkit::patterns
```

### TaskAgent

Single-purpose agent optimized for a specific task category.

**Header**: `#include <agenkit/patterns/task_agent.hpp>`

```cpp
namespace agenkit::patterns {

class TaskAgent : public core::Agent {
public:
    TaskAgent(std::shared_ptr<core::Agent> inner,
               const std::string& task_description,
               const std::string& system_prompt = "");

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::patterns
```

### ConversationalAgent

Maintains conversation history across multiple turns.

**Header**: `#include <agenkit/patterns/conversational_agent.hpp>`

```cpp
namespace agenkit::patterns {

struct ConversationalConfig {
    std::string system_prompt = "";
    size_t      max_history   = 50;    // Messages to retain
    bool        include_system = true;
};

class ConversationalAgent : public core::Agent {
public:
    ConversationalAgent(std::shared_ptr<core::Agent> inner,
                         const ConversationalConfig& config = {});

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // Conversation management
    const std::vector<core::Message>& history() const;
    void clear_history();
    void set_system_prompt(const std::string& prompt);

    // Session-aware processing
    std::future<core::Result<core::Message, core::AgentError>>
    process_in_session(core::Message message, const std::string& session_id);
};

} // namespace agenkit::patterns
```

### AgentsAsToolsAgent

Orchestrates sub-agents by treating each as a callable tool.

**Header**: `#include <agenkit/patterns/agents_as_tools_agent.hpp>`

```cpp
namespace agenkit::patterns {

class AgentsAsToolsAgent : public core::Agent {
public:
    AgentsAsToolsAgent(std::shared_ptr<core::Agent> orchestrator,
                        std::vector<std::shared_ptr<core::Agent>> sub_agents,
                        int max_iterations = 10);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    void add_sub_agent(std::shared_ptr<core::Agent> agent);
};

} // namespace agenkit::patterns
```

### AutonomousAgent

Pursues a high-level goal autonomously over multiple iterations.

**Header**: `#include <agenkit/patterns/autonomous_agent.hpp>`

```cpp
namespace agenkit::patterns {

struct AutonomousConfig {
    int         max_iterations  = 20;
    std::string termination_signal = "TASK_COMPLETE";
    bool        allow_self_modification = false;
};

class AutonomousAgent : public core::Agent {
public:
    AutonomousAgent(std::shared_ptr<core::Agent> inner,
                     std::vector<std::shared_ptr<core::Tool>> tools,
                     const AutonomousConfig& config = {});

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    int iterations_used() const;
};

} // namespace agenkit::patterns
```

### MultiagentOrchestrator

Coordinates multiple specialized agents in a collaborative workflow.

**Header**: `#include <agenkit/patterns/multiagent_orchestrator.hpp>`

```cpp
namespace agenkit::patterns {

class MultiagentOrchestrator : public core::Agent {
public:
    MultiagentOrchestrator(
        std::shared_ptr<core::Agent> orchestrator,
        std::map<std::string, std::shared_ptr<core::Agent>> specialists
    );

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    void register_specialist(const std::string& role,
                               std::shared_ptr<core::Agent> agent);
};

} // namespace agenkit::patterns
```

### MemoryHierarchyAgent

Uses tiered memory (working → episodic → semantic) for long-running sessions.

**Header**: `#include <agenkit/patterns/memory_hierarchy_agent.hpp>`

```cpp
namespace agenkit::patterns {

struct MemoryHierarchyConfig {
    size_t working_memory_size  = 10;    // Recent messages
    size_t episodic_memory_size = 100;   // Episode summaries
    size_t semantic_memory_size = 1000;  // Long-term facts
    int    consolidation_interval = 10;  // Consolidate every N turns
};

class MemoryHierarchyAgent : public core::Agent {
public:
    MemoryHierarchyAgent(std::shared_ptr<core::Agent> inner,
                          const MemoryHierarchyConfig& config = {});

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    // Memory inspection
    std::vector<core::Message>    working_memory()  const;
    std::vector<std::string>      episodic_memory() const;
    std::map<std::string, std::string> semantic_memory() const;

    void clear_all_memory();
    void consolidate_now();
};

} // namespace agenkit::patterns
```

---

## Observability

See [OBSERVABILITY.md](OBSERVABILITY.md) for the complete observability guide.

### TracingMiddleware

Wraps an agent to emit OpenTelemetry spans for each request.

**Header**: `#include <agenkit/observability/tracing.hpp>`

```cpp
namespace agenkit::observability {

class TracingMiddleware : public core::Agent {
public:
    TracingMiddleware(std::shared_ptr<core::Agent> inner,
                       const std::string& span_name = "agent.process");

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::observability
```

### MetricsMiddleware

Records `agent_requests_total` (counter) and `agent_request_duration_seconds` (histogram).

**Header**: `#include <agenkit/observability/metrics.hpp>`

```cpp
namespace agenkit::observability {

class MetricsMiddleware : public core::Agent {
public:
    explicit MetricsMiddleware(std::shared_ptr<core::Agent> inner);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;
};

} // namespace agenkit::observability
```

---

## Transport

### HttpServer

Exposes an agent over HTTP so other services can call it.

**Header**: `#include <agenkit/transports/http_server.hpp>`

```cpp
namespace agenkit::transports {

struct HttpServerConfig {
    std::string host    = "127.0.0.1";
    int         port    = 8080;
    int         threads = 4;
    std::optional<std::string> api_key;  // If set, require X-API-Key header
};

class HttpServer {
public:
    HttpServer(std::shared_ptr<core::Agent> agent, const HttpServerConfig& config);

    // Simple constructor: "host:port"
    HttpServer(std::shared_ptr<core::Agent> agent, const std::string& address);

    // Start serving (blocks until stop() is called)
    void serve();

    // Start in background thread
    void serve_async();

    // Stop the server
    void stop();

    bool is_running() const;
};

} // namespace agenkit::transports
```

### HttpAgent

Connects to a remote agent exposed via HttpServer.

**Header**: `#include <agenkit/transports/http_agent.hpp>`

```cpp
namespace agenkit::transports {

struct HttpTransportConfig {
    std::string base_url;
    int         timeout_secs = 30;
    std::optional<std::string> api_key;
    int         max_retries  = 0;
};

class HttpAgent : public core::Agent {
public:
    HttpAgent(const std::string& name, const HttpTransportConfig& config);

    std::string name() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    bool is_healthy() const;  // GET /health
};

} // namespace agenkit::transports
```

---

## Utility Functions

```cpp
namespace agenkit::core {

// Create a std::future that is already resolved with value
template<typename T>
std::future<T> make_ready_future(T value);

// Create a std::future that is already resolved with an error
template<typename T, typename E>
std::future<Result<T, E>> make_error_future(E error);

} // namespace agenkit::core
```

---

**Version**: v0.75.0
**Last Updated**: March 2026
