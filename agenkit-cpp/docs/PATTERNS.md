# Agenkit C++ Agent Patterns Guide

A comprehensive guide to the 11 agent patterns in Agenkit-C++.

## Table of Contents

- [Overview](#overview)
- [Pattern Comparison](#pattern-comparison)
- [Composition Patterns](#composition-patterns)
  - [Sequential](#sequential)
  - [Parallel](#parallel)
- [Enhancement Patterns](#enhancement-patterns)
  - [Reflection](#reflection)
  - [ReAct](#react)
  - [Planning](#planning)
- [Specialized Patterns](#specialized-patterns)
  - [Task](#task)
  - [Conversational](#conversational)
  - [Agents as Tools](#agents-as-tools)
- [Advanced Patterns](#advanced-patterns)
  - [Autonomous](#autonomous)
  - [Multiagent](#multiagent)
  - [Memory Hierarchy](#memory-hierarchy)
- [Pattern Selection Guide](#pattern-selection-guide)
- [Composing Patterns](#composing-patterns)

---

## Overview

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit provides 11 production-ready patterns you can use immediately or combine for complex workflows.

### Why Patterns Matter

1. **Proven Solutions** — Patterns encode best practices from production systems
2. **Composability** — Patterns work together seamlessly; each pattern is itself an `Agent`
3. **Performance** — Optimized implementations using `std::async`, `std::future`, and RAII
4. **Maintainability** — Clear separation of concerns, easy to test in isolation

### Pattern Categories

- **Composition** (Sequential, Parallel) — Combine multiple agents
- **Enhancement** (Reflection, ReAct, Planning) — Improve agent quality
- **Specialized** (Task, Conversational, Agents as Tools) — Domain-specific patterns
- **Advanced** (Autonomous, Multiagent, Memory Hierarchy) — Complex behaviors

---

## Pattern Comparison

| Pattern | Complexity | Use Case | Performance | Best For |
|---------|-----------|----------|-------------|----------|
| Sequential | Low | Data pipelines | Fast | Multi-stage processing |
| Parallel | Medium | Independent tasks | Very Fast | Concurrent operations |
| Reflection | Medium | Quality improvement | Slow (iterative) | Self-correction |
| ReAct | Medium | Reasoning + tools | Medium | Decision-making |
| Planning | High | Complex tasks | Slow (planning) | Multi-step workflows |
| Task | Low | Job execution | Fast | Single-purpose agents |
| Conversational | Medium | Dialogue | Fast | Chatbots |
| Agents as Tools | High | Orchestration | Medium | Tool delegation |
| Autonomous | Very High | Goal pursuit | Slow (iterative) | Self-directed agents |
| Multiagent | Very High | Collaboration | Medium | Multi-agent systems |
| Memory Hierarchy | High | Context management | Medium | Long-running agents |

---

## Composition Patterns

### Sequential

**Purpose:** Process a message through multiple agents in order, feeding each agent's output as the next agent's input.

**When to Use:**
- Data transformation pipelines (validate → enrich → format)
- Multi-stage processing where order matters
- When each stage transforms or specializes the content

**ASCII Diagram:**
```
Input → Agent1 → Agent2 → Agent3 → Output
         (validate)  (enrich)  (format)
```

**Implementation:**

```cpp
#include <agenkit/patterns/sequential_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>
#include <iostream>
#include <memory>
#include <vector>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

// Stage 1: Validate and clean the input
class ValidatorAgent : public Agent {
public:
    std::string name() const override { return "validator"; }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto text = message.content().as_text();
        if (text.empty()) {
            return make_ready_future(
                Result<Message, AgentError>::err(
                    AgentError{AgentErrorCode::InvalidInput, "empty input"}
                )
            );
        }
        // Strip leading/trailing whitespace
        auto cleaned = trim(text);
        return make_ready_future(
            Result<Message, AgentError>::ok(
                Message::with_text("assistant", cleaned)
            )
        );
    }
private:
    std::string trim(const std::string& s);
};

// Stage 2: Summarize
class SummarizerAgent : public Agent {
public:
    explicit SummarizerAgent(std::shared_ptr<Agent> llm) : llm_(llm) {}

    std::string name() const override { return "summarizer"; }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto prompt = Message::with_text(
            "user",
            "Summarize in one sentence: " + message.content().as_text()
        );
        return llm_->process(std::move(prompt));
    }
private:
    std::shared_ptr<Agent> llm_;
};

// Stage 3: Format for output
class FormatterAgent : public Agent {
public:
    std::string name() const override { return "formatter"; }

    std::future<Result<Message, AgentError>>
    process(Message message) override {
        auto formatted = "Summary: " + message.content().as_text();
        return make_ready_future(
            Result<Message, AgentError>::ok(
                Message::with_text("assistant", formatted)
            )
        );
    }
};

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::SONNET_4;
    auto llm = std::make_shared<ClaudeAgent>(config);

    // Build the pipeline
    std::vector<std::shared_ptr<Agent>> stages = {
        std::make_shared<ValidatorAgent>(),
        std::make_shared<SummarizerAgent>(llm),
        std::make_shared<FormatterAgent>(),
    };

    auto pipeline = SequentialAgent(std::move(stages));

    auto msg = Message::with_text("user",
        "The quick brown fox jumps over the lazy dog. "
        "This sentence contains all letters of the alphabet.");

    auto result = pipeline.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";
        // Output: Summary: A classic pangram sentence using all alphabet letters.
    }
}
```

**Trade-offs:**
- Pro: Simple, predictable, easy to debug
- Pro: Each stage is independently testable
- Con: Sequential — each stage must complete before the next starts
- Con: Error in any stage aborts the pipeline

---

### Parallel

**Purpose:** Dispatch a message to multiple agents simultaneously and combine their results.

**When to Use:**
- Independent tasks that don't depend on each other
- Ensemble approaches (voting, averaging)
- Exploratory generation (generate multiple drafts, pick the best)
- Fan-out/fan-in patterns

**ASCII Diagram:**
```
              ┌─→ Agent1 ─→┐
Input ──────→ ├─→ Agent2 ─→┤ ──→ Aggregator ──→ Output
              └─→ Agent3 ─→┘
```

**Implementation:**

```cpp
#include <agenkit/patterns/parallel_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>
#include <future>
#include <vector>

using namespace agenkit::core;
using namespace agenkit::patterns;

// Three specialized sub-agents
class OptimistAgent : public Agent { /* ... */ };
class PessimistAgent : public Agent { /* ... */ };
class RealistAgent : public Agent { /* ... */ };

// Custom aggregator: combine three perspectives into one response
auto aggregator = [](std::vector<Result<Message, AgentError>> results)
    -> Result<Message, AgentError>
{
    std::string combined;
    for (auto& r : results) {
        if (r.is_ok()) {
            combined += r.value().content().as_text() + "\n\n";
        }
    }
    if (combined.empty()) {
        return Result<Message, AgentError>::err(
            AgentError{"all agents failed"}
        );
    }
    return Result<Message, AgentError>::ok(
        Message::with_text("assistant", combined)
    );
};

int main() {
    std::vector<std::shared_ptr<Agent>> agents = {
        std::make_shared<OptimistAgent>(),
        std::make_shared<PessimistAgent>(),
        std::make_shared<RealistAgent>(),
    };

    auto parallel = ParallelAgent(std::move(agents), aggregator);

    auto msg = Message::with_text("user", "Should we launch the product now?");
    auto result = parallel.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";
    }
}
```

**Parallel with std::async directly (advanced):**

```cpp
// Manual parallelism for full control
std::vector<std::future<Result<Message, AgentError>>> futures;

auto msg_copy1 = message;
auto msg_copy2 = message;
auto msg_copy3 = message;

// Launch all three simultaneously
futures.push_back(agent_a->process(std::move(msg_copy1)));
futures.push_back(agent_b->process(std::move(msg_copy2)));
futures.push_back(agent_c->process(std::move(msg_copy3)));

// Collect results
std::vector<Result<Message, AgentError>> results;
results.reserve(futures.size());
for (auto& f : futures) {
    results.push_back(f.get());
}
```

**Trade-offs:**
- Pro: Dramatically faster when tasks are independent
- Pro: Natural fault isolation (one failure doesn't block others)
- Con: Consumes more threads/resources
- Con: Aggregation logic can be complex
- Con: All branches consume API credits even if only one result is needed

---

## Enhancement Patterns

### Reflection

**Purpose:** Iteratively improve an output through a draft-critique-refine cycle.

**When to Use:**
- Code generation (write → review → fix)
- Essay/document writing (draft → critique → polish)
- Any task where first attempts are suboptimal
- Quality-sensitive outputs

**ASCII Diagram:**
```
Input → Generator → Draft
                       ↓
                    Critic → Feedback
                       ↓
                    Generator (with feedback) → Better Draft
                       ↓
                    [repeat until max_iterations or satisfied]
                       ↓
                    Final Output
```

**Implementation:**

```cpp
#include <agenkit/patterns/reflection_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::SONNET_4;

    // Both generator and critic use the same model
    auto agent    = std::make_shared<ClaudeAgent>(config);
    auto critic   = std::make_shared<ClaudeAgent>(config);

    // Reflect for up to 3 iterations
    ReflectionAgent reflection(
        agent,
        critic,
        3,                              // max_iterations
        "Review this C++ code for correctness, safety, and idioms. "
        "List specific issues and improvements:"
    );

    auto msg = Message::with_text("user",
        "Write a thread-safe singleton in C++17");

    auto result = reflection.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << "Final (after reflection):\n"
                  << result.value().content().as_text() << "\n";
    }
}
```

**Custom Critique Prompt:**

```cpp
// Domain-specific critique prompts
const std::string security_critique =
    "Review this code for security vulnerabilities including: "
    "SQL injection, buffer overflow, race conditions, improper input validation. "
    "Be specific about line numbers and fixes.";

ReflectionAgent secure_coder(agent, critic, 5, security_critique);
```

**Trade-offs:**
- Pro: Significantly improves output quality
- Pro: Self-contained — no external tools needed
- Con: Multiplies API calls by max_iterations
- Con: Diminishing returns after 3-4 iterations
- Con: Slow — sequential iteration

---

### ReAct

**Purpose:** Alternate between Reasoning (thought) and Acting (tool calls) to solve problems that require external information.

**When to Use:**
- Tasks requiring web search, database queries, or calculations
- Multi-step problem solving with information gathering
- When the agent needs to verify facts or perform real-world actions

**ASCII Diagram:**
```
Question
   ↓
Thought: "I need to look up X"
   ↓
Action: search("X")
   ↓
Observation: "Search result..."
   ↓
Thought: "Now I know X, I can compute Y"
   ↓
Action: calculator("Y = X * 2")
   ↓
Observation: "Y = 42"
   ↓
Thought: "I have all the information"
   ↓
Final Answer
```

**Implementation:**

```cpp
#include <agenkit/patterns/react_agent.hpp>
#include <agenkit/adapters/ollama_agent.hpp>
#include <agenkit/core/tool.hpp>
#include <cmath>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

class CalculatorTool : public Tool {
public:
    std::string name() const override { return "calculator"; }
    std::string description() const override {
        return "Evaluate a mathematical expression. Returns the numeric result.";
    }
    nlohmann::json parameters_schema() const override {
        return {
            {"type", "object"},
            {"properties", {
                {"expression", {{"type", "string"}, {"description", "Math expression"}}}
            }},
            {"required", {"expression"}}
        };
    }
    ToolResult execute(const std::map<std::string, nlohmann::json>& params) const override {
        auto expr = params.at("expression").get<std::string>();
        // Real implementation would evaluate the expression
        return {true, "Result: 47.50 * 0.15 = 7.125", ""};
    }
};

class WeatherTool : public Tool {
public:
    std::string name() const override { return "weather"; }
    std::string description() const override {
        return "Get current weather for a city.";
    }
    nlohmann::json parameters_schema() const override {
        return {
            {"type", "object"},
            {"properties", {
                {"city", {{"type", "string"}, {"description", "City name"}}}
            }},
            {"required", {"city"}}
        };
    }
    ToolResult execute(const std::map<std::string, nlohmann::json>& params) const override {
        auto city = params.at("city").get<std::string>();
        return {true, city + ": 18°C, partly cloudy", ""};
    }
};

int main() {
    // Use Ollama for free local inference
    OllamaConfig config;
    config.model = "llama3.3";
    auto llm = std::make_shared<OllamaAgent>(config);

    std::vector<std::shared_ptr<Tool>> tools = {
        std::make_shared<CalculatorTool>(),
        std::make_shared<WeatherTool>(),
    };

    ReActAgent react(llm, tools, 10);  // max 10 reasoning steps

    auto msg = Message::with_text("user",
        "What's a 15% tip on $47.50? Also, what's the weather in Paris?");

    auto result = react.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";

        // Inspect the reasoning trace
        for (const auto& step : react.last_trace()) {
            std::cout << "Thought: " << step.thought << "\n";
            std::cout << "Action:  " << step.action << "\n";
            std::cout << "Obs:     " << step.observation << "\n\n";
        }
    }
}
```

**Trade-offs:**
- Pro: Can solve problems requiring external information
- Pro: Traceable reasoning makes debugging straightforward
- Con: Slow — each tool call may require an LLM round-trip
- Con: LLM must support function/tool calling
- Con: Risk of infinite loops without max_iterations guard

---

### Planning

**Purpose:** Decompose a complex goal into a sequence of steps, then execute each step.

**When to Use:**
- Long-horizon tasks (write a research report, build a feature)
- Tasks with many interdependent sub-goals
- When you want explicit, inspectable plans

**ASCII Diagram:**
```
Goal
  ↓
Planner → Plan: [Step1, Step2, Step3, ...]
                    ↓
                 Executor(Step1) → Result1
                    ↓
                 Executor(Step2, context=Result1) → Result2
                    ↓
                 Executor(Step3, context=Result1+2) → Result3
                    ↓
                 Final Synthesis
```

**Implementation:**

```cpp
#include <agenkit/patterns/planning_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::OPUS_4;  // Use a powerful model for planning
    auto planner = std::make_shared<ClaudeAgent>(config);

    config.model = ClaudeModels::SONNET_4;  // Faster model for execution
    auto executor = std::make_shared<ClaudeAgent>(config);

    PlanningAgent planner_agent(planner, executor, 15);  // max 15 steps

    auto msg = Message::with_text("user",
        "Write a comprehensive blog post about RAII in modern C++");

    auto result = planner_agent.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";

        // Inspect what was planned
        for (size_t i = 0; i < planner_agent.last_plan().size(); ++i) {
            std::cout << i + 1 << ". " << planner_agent.last_plan()[i] << "\n";
        }
    }
}
```

**Trade-offs:**
- Pro: Handles very complex tasks systematically
- Pro: Plan is auditable before and after execution
- Con: Expensive — planning adds extra LLM calls
- Con: Plan quality depends heavily on the planner model
- Con: Plans can become stale if execution discovers new constraints

---

## Specialized Patterns

### Task

**Purpose:** A focused agent pre-configured for a specific category of tasks via a system prompt.

**When to Use:**
- Domain-specific processing (code review, sentiment analysis, translation)
- When you want a reusable, named capability
- As a building block in pipelines

**Implementation:**

```cpp
#include <agenkit/patterns/task_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::SONNET_4;
    auto llm = std::make_shared<ClaudeAgent>(config);

    // Create specialized task agents from the same LLM
    TaskAgent code_reviewer(
        llm,
        "code-reviewer",
        "You are an expert C++ code reviewer. Focus on: memory safety, "
        "thread safety, RAII compliance, and idiomatic C++17 usage. "
        "Be concise and actionable."
    );

    TaskAgent sentiment_analyzer(
        llm,
        "sentiment-analyzer",
        "Classify user feedback as: POSITIVE, NEGATIVE, or NEUTRAL. "
        "Return only the classification and a confidence score (0-1)."
    );

    // Use the code reviewer
    auto code = Message::with_text("user",
        "Review: int* ptr = new int(42); // used later\n"
        "delete ptr;");

    auto review_result = code_reviewer.process(std::move(code)).get();
    if (review_result.is_ok()) {
        std::cout << "Review: " << review_result.value().content().as_text() << "\n";
    }

    // Use the sentiment analyzer
    auto feedback = Message::with_text("user",
        "The product is great but the documentation could be better.");

    auto sentiment = sentiment_analyzer.process(std::move(feedback)).get();
    if (sentiment.is_ok()) {
        std::cout << "Sentiment: " << sentiment.value().content().as_text() << "\n";
    }
}
```

**Trade-offs:**
- Pro: Very simple — just a system prompt wrapper
- Pro: Easy to create many specialized agents from one LLM
- Con: No memory, no history — stateless by design
- Con: Quality depends entirely on the system prompt

---

### Conversational

**Purpose:** Maintain conversation history across multiple turns, enabling coherent multi-turn dialogue.

**When to Use:**
- Chatbots and virtual assistants
- Interactive tutoring systems
- Any multi-turn application where context matters

**ASCII Diagram:**
```
Turn 1: User → [System + User] → Agent → Response1
Turn 2: User → [System + User + Resp1 + User2] → Agent → Response2
Turn 3: User → [System + User + ... + User3] → Agent → Response3
```

**Implementation:**

```cpp
#include <agenkit/patterns/conversational_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>
#include <iostream>
#include <string>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::SONNET_4;
    auto llm = std::make_shared<ClaudeAgent>(config);

    ConversationalConfig conv_config;
    conv_config.system_prompt =
        "You are a helpful C++ programming tutor. Explain concepts "
        "clearly with examples. Remember what the student has asked before.";
    conv_config.max_history = 20;  // Keep last 20 messages

    ConversationalAgent assistant(llm, conv_config);

    // Simulate a multi-turn conversation
    std::vector<std::string> user_turns = {
        "What is RAII?",
        "Can you show me an example?",
        "How does it relate to what you just showed me with unique_ptr?",
    };

    for (const auto& turn : user_turns) {
        std::cout << "User: " << turn << "\n";

        auto msg = Message::with_text("user", turn);
        auto result = assistant.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << "Assistant: "
                      << result.value().content().as_text() << "\n\n";
        }
    }

    // History is retained automatically
    std::cout << "History length: " << assistant.history().size() << "\n";

    // Start fresh
    assistant.clear_history();
}
```

**Session Management:**

```cpp
// Use session IDs for multi-user applications
ConversationalAgent agent(llm, config);

// User A's conversation
agent.process_in_session(
    Message::with_text("user", "Hello!"), "session-user-a"
).get();

// User B's conversation (independent context)
agent.process_in_session(
    Message::with_text("user", "Hi there!"), "session-user-b"
).get();
```

**Trade-offs:**
- Pro: Natural multi-turn conversation support
- Pro: Context is managed automatically
- Con: Token usage grows with history length
- Con: Very long histories may exceed context window
- Con: History trimming can cause the agent to "forget" earlier turns

---

### Agents as Tools

**Purpose:** An orchestrator agent that can delegate work to specialized sub-agents by treating each as a callable tool.

**When to Use:**
- Dynamic task routing (let the LLM decide which specialist to call)
- Hierarchical agent systems
- When specialist selection logic is complex

**ASCII Diagram:**
```
User Request
     ↓
Orchestrator (decides which specialist to use)
     ↓
  [calls] SearchAgent or MathAgent or CodeAgent
     ↓
Specialist produces result
     ↓
Orchestrator synthesizes final answer
```

**Implementation:**

```cpp
#include <agenkit/patterns/agents_as_tools_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

// Specialized sub-agents
class SearchAgent : public Agent {
public:
    std::string name() const override { return "web_search"; }
    std::vector<std::string> capabilities() const override {
        return {"search", "lookup", "find information"};
    }
    std::future<Result<Message, AgentError>>
    process(Message message) override;  // Calls a search API
};

class MathAgent : public Agent {
public:
    std::string name() const override { return "math_solver"; }
    std::vector<std::string> capabilities() const override {
        return {"calculate", "math", "arithmetic", "algebra"};
    }
    std::future<Result<Message, AgentError>>
    process(Message message) override;  // Evaluates expressions
};

class CodeAgent : public Agent {
public:
    std::string name() const override { return "code_executor"; }
    std::vector<std::string> capabilities() const override {
        return {"code", "execute", "run python", "programming"};
    }
    std::future<Result<Message, AgentError>>
    process(Message message) override;  // Executes code safely
};

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::OPUS_4;
    auto orchestrator_llm = std::make_shared<ClaudeAgent>(config);

    std::vector<std::shared_ptr<Agent>> specialists = {
        std::make_shared<SearchAgent>(),
        std::make_shared<MathAgent>(),
        std::make_shared<CodeAgent>(),
    };

    AgentsAsToolsAgent orchestrator(orchestrator_llm, specialists, 10);

    auto msg = Message::with_text("user",
        "Search for the current price of gold, then calculate how much "
        "1 kilogram would cost.");

    auto result = orchestrator.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";
    }
}
```

**Trade-offs:**
- Pro: Flexible — orchestrator decides routing dynamically
- Pro: Easy to add new specialists without changing orchestrator logic
- Con: Complex — requires a capable orchestrator model
- Con: Multiple LLM calls for each delegation
- Con: Hard to predict which path will be taken

---

## Advanced Patterns

### Autonomous

**Purpose:** An agent that pursues a high-level goal over many iterations with minimal human intervention, stopping when the goal is achieved.

**When to Use:**
- Long-running background tasks (research, code generation, analysis)
- When you want the agent to self-direct toward a goal
- Automation pipelines that should run unattended

**ASCII Diagram:**
```
Goal
  ↓
[Iteration 1]: Think → Act → Observe → Goal achieved? No
  ↓
[Iteration 2]: Think (with history) → Act → Observe → Goal achieved? No
  ↓
...
[Iteration N]: Think → Act → Observe → "TASK_COMPLETE"
  ↓
Final Report
```

**Implementation:**

```cpp
#include <agenkit/patterns/autonomous_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>
#include <agenkit/core/tool.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

class FileWriteTool : public Tool {
public:
    std::string name() const override { return "write_file"; }
    std::string description() const override {
        return "Write content to a file. Use to save results.";
    }
    nlohmann::json parameters_schema() const override {
        return {
            {"type", "object"},
            {"properties", {
                {"path",    {{"type", "string"}}},
                {"content", {{"type", "string"}}}
            }},
            {"required", {"path", "content"}}
        };
    }
    ToolResult execute(const std::map<std::string, nlohmann::json>& params) const override {
        auto path    = params.at("path").get<std::string>();
        auto content = params.at("content").get<std::string>();
        // Write to file
        return {true, "Written to " + path, ""};
    }
};

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::OPUS_4;
    auto llm = std::make_shared<ClaudeAgent>(config);

    AutonomousConfig auto_config;
    auto_config.max_iterations       = 20;
    auto_config.termination_signal   = "TASK_COMPLETE";

    std::vector<std::shared_ptr<Tool>> tools = {
        std::make_shared<FileWriteTool>(),
        std::make_shared<CalculatorTool>(),
    };

    AutonomousAgent agent(llm, tools, auto_config);

    auto msg = Message::with_text("user",
        "Research the top 5 C++ build systems, compare them, "
        "and write a summary to 'build_systems.md'. "
        "When done, output TASK_COMPLETE.");

    auto result = agent.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << "Completed in " << agent.iterations_used()
                  << " iterations\n";
        std::cout << result.value().content().as_text() << "\n";
    }
}
```

**Trade-offs:**
- Pro: Handles complex long-horizon tasks autonomously
- Pro: Flexible — agent decides its own sub-strategy
- Con: Expensive — many iterations mean many LLM calls
- Con: Unpredictable behavior without good guardrails
- Con: Must set max_iterations to prevent infinite loops

---

### Multiagent

**Purpose:** Multiple specialized agents collaborate, each handling what it does best, coordinated by an orchestrator.

**When to Use:**
- Complex tasks requiring diverse expertise
- Peer review workflows (write → review → revise)
- Research tasks (gather → analyze → synthesize)

**ASCII Diagram:**
```
Task
  ↓
Orchestrator
  ↓        ↓       ↓
Research  Analysis  Writing
  Agent     Agent   Agent
  ↓        ↓       ↓
Orchestrator (synthesizes all results)
  ↓
Final Output
```

**Implementation:**

```cpp
#include <agenkit/patterns/multiagent_orchestrator.hpp>
#include <agenkit/adapters/claude_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

int main() {
    ClaudeConfig fast_config;
    fast_config.api_key = std::getenv("ANTHROPIC_API_KEY");
    fast_config.model   = ClaudeModels::SONNET_4;

    ClaudeConfig smart_config;
    smart_config.api_key = std::getenv("ANTHROPIC_API_KEY");
    smart_config.model   = ClaudeModels::OPUS_4;

    // Specialists
    auto researcher = std::make_shared<ClaudeAgent>(fast_config);
    auto analyst    = std::make_shared<ClaudeAgent>(fast_config);
    auto writer     = std::make_shared<ClaudeAgent>(fast_config);

    // Orchestrator (uses a more powerful model)
    auto orchestrator = std::make_shared<ClaudeAgent>(smart_config);

    MultiagentOrchestrator system(
        orchestrator,
        {
            {"researcher", researcher},
            {"analyst",    analyst},
            {"writer",     writer},
        }
    );

    auto msg = Message::with_text("user",
        "Create a technical report on memory safety in C++");

    auto result = system.process(std::move(msg)).get();

    if (result.is_ok()) {
        std::cout << result.value().content().as_text() << "\n";
    }

    // Add a new specialist dynamically
    auto proofreader = std::make_shared<ClaudeAgent>(fast_config);
    system.register_specialist("proofreader", proofreader);
}
```

**Trade-offs:**
- Pro: Best-in-class results from specialized agents
- Pro: Natural division of labor
- Con: Most expensive pattern in API calls
- Con: Coordination overhead
- Con: Debugging multi-agent interactions is complex

---

### Memory Hierarchy

**Purpose:** Manage context across long conversations using tiered storage: working memory (recent), episodic memory (summaries), and semantic memory (persistent facts).

**When to Use:**
- Long-running sessions that exceed context windows
- Agents that need to remember facts across restarts
- Applications where users expect the agent to recall previous interactions

**ASCII Diagram:**
```
Working Memory  (last 10 messages, always in context)
      ↓ consolidate every 10 turns
Episodic Memory (summaries of older conversations)
      ↓ extract important facts
Semantic Memory (long-term facts: "User prefers Python", "Company is ACME Corp")
```

**Implementation:**

```cpp
#include <agenkit/patterns/memory_hierarchy_agent.hpp>
#include <agenkit/adapters/claude_agent.hpp>

using namespace agenkit::core;
using namespace agenkit::patterns;
using namespace agenkit::adapters;

int main() {
    ClaudeConfig config;
    config.api_key = std::getenv("ANTHROPIC_API_KEY");
    config.model   = ClaudeModels::SONNET_4;
    auto llm = std::make_shared<ClaudeAgent>(config);

    MemoryHierarchyConfig mem_config;
    mem_config.working_memory_size    = 10;    // Last 10 messages
    mem_config.episodic_memory_size   = 50;    // Up to 50 episode summaries
    mem_config.semantic_memory_size   = 200;   // Up to 200 long-term facts
    mem_config.consolidation_interval = 10;    // Consolidate every 10 turns

    MemoryHierarchyAgent agent(llm, mem_config);

    // Simulate a long conversation
    std::vector<std::string> messages = {
        "My name is Alex and I'm working on a C++ networking library.",
        "I need help with async I/O using Boost.Asio.",
        "Let's focus on TCP connections first.",
        // ... many more turns
    };

    for (const auto& text : messages) {
        auto msg = Message::with_text("user", text);
        auto result = agent.process(std::move(msg)).get();

        if (result.is_ok()) {
            std::cout << result.value().content().as_text() << "\n\n";
        }
    }

    // Inspect memory state
    std::cout << "Working memory size: "
              << agent.working_memory().size() << " messages\n";

    std::cout << "Episodic memory size: "
              << agent.episodic_memory().size() << " episodes\n";

    for (const auto& [key, fact] : agent.semantic_memory()) {
        std::cout << "Fact: " << key << " = " << fact << "\n";
    }

    // Force consolidation
    agent.consolidate_now();
}
```

**Trade-offs:**
- Pro: Handles arbitrarily long conversations without losing important context
- Pro: Facts persist across sessions
- Con: Complex implementation — three distinct storage tiers
- Con: Consolidation quality depends on the LLM
- Con: Additional LLM calls for consolidation and summarization

---

## Pattern Selection Guide

Use this decision tree to choose the right pattern:

```
Is the task single-turn (one request, one response)?
  → YES: Is it a specialized domain?
      → YES: Task pattern
      → NO: Direct agent call (no pattern)
  → NO: Does it require conversation history?
      → YES: Conversational pattern
      → NO: Does it require external tools/data?
          → YES: Does it need planning?
              → YES: Planning pattern
              → NO: ReAct pattern
          → NO: Do you need multiple agents?
              → YES: Are they in sequence?
                  → YES: Sequential pattern
                  → NO: Are they peers or specialists?
                      → Parallel, Multiagent, or AgentsAsTools
              → NO: Do you need quality improvement?
                  → YES: Reflection pattern
                  → NO: Is it a long autonomous task?
                      → YES: Autonomous pattern
```

### Quick Reference

| Use Case | Recommended Pattern |
|----------|---------------------|
| Multi-stage pipeline | Sequential |
| Independent parallel tasks | Parallel |
| Quality-critical output | Reflection |
| Tool use / information gathering | ReAct |
| Complex multi-step planning | Planning |
| Domain-specific task | Task |
| Chatbot / assistant | Conversational |
| Dynamic specialist routing | Agents as Tools |
| Long autonomous task | Autonomous |
| Collaborative expertise | Multiagent |
| Long-running sessions | Memory Hierarchy |

---

## Composing Patterns

All patterns implement `Agent`, so they compose freely. Here are common combinations:

### Conversational + Memory Hierarchy

```cpp
// A chatbot that never forgets
MemoryHierarchyConfig mem_config;
mem_config.working_memory_size = 10;

auto memory_agent = std::make_shared<MemoryHierarchyAgent>(llm, mem_config);

ConversationalConfig conv_config;
conv_config.system_prompt = "You are a helpful assistant.";

ConversationalAgent chatbot(memory_agent, conv_config);
```

### ReAct + Middleware (Production Hardening)

```cpp
// Resilient ReAct agent with full middleware stack
auto base_llm = std::make_shared<ClaudeAgent>(claude_config);
auto react     = std::make_shared<ReActAgent>(base_llm, tools, 10);

// Add retry for transient failures
auto retried  = std::make_shared<RetryDecorator>(react, 3, 100);

// Add circuit breaker for sustained failures
auto guarded  = std::make_shared<CircuitBreakerDecorator>(retried, 5, 30000);

// Add observability
auto traced   = std::make_shared<TracingMiddleware>(guarded);
auto observed = std::make_shared<MetricsMiddleware>(traced);

// Result: fully production-hardened ReAct agent
auto result = observed->process(message).get();
```

### Sequential + Reflection

```cpp
// Pipeline with quality check on the final stage
auto raw_writer = std::make_shared<TaskAgent>(llm, "writer", writing_prompt);
auto reflector  = std::make_shared<ReflectionAgent>(raw_writer, 3);
auto formatter  = std::make_shared<TaskAgent>(llm, "formatter", format_prompt);

std::vector<std::shared_ptr<Agent>> stages = {raw_writer, reflector, formatter};
SequentialAgent pipeline(std::move(stages));
```

### Parallel + Reflection (Ensemble Reflection)

```cpp
// Generate multiple drafts in parallel, then pick the best
auto writer_a = std::make_shared<ClaudeAgent>(config_a);
auto writer_b = std::make_shared<ClaudeAgent>(config_b);
auto writer_c = std::make_shared<ClaudeAgent>(config_c);

// Pick the longest response as a proxy for depth
auto best_picker = [](std::vector<Result<Message, AgentError>> results)
    -> Result<Message, AgentError>
{
    std::optional<Message> best;
    for (auto& r : results) {
        if (r.is_ok()) {
            if (!best || r.value().content().as_text().length()
                         > best->content().as_text().length()) {
                best = r.value();
            }
        }
    }
    if (best) return Result<Message, AgentError>::ok(std::move(*best));
    return Result<Message, AgentError>::err(AgentError{"all failed"});
};

ParallelAgent ensemble({writer_a, writer_b, writer_c}, best_picker);

// Then refine the best draft
ReflectionAgent final_agent(
    std::make_shared<ParallelAgent>(std::move(ensemble)),
    critic,
    2
);
```

---

**Version**: v0.75.0
**Last Updated**: March 2026
