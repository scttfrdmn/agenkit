# Agenkit Agent Patterns Guide

A comprehensive guide to the 11 agent patterns in Agenkit-Zig.

## Table of Contents

- [Overview](#overview)
- [Pattern Comparison](#pattern-comparison)
- [Composition Patterns](#composition-patterns)
  - [Sequential](#sequential)
  - [Parallel](#parallel)
- [Enhancement Patterns](#enhancement-patterns)
  - [Reflection](#reflection)
  - [React](#react)
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

Agent patterns are reusable architectural templates that solve common problems in AI agent design. Agenkit provides 11 production-ready patterns that you can use immediately or combine for complex workflows.

### Why Patterns Matter

1. **Proven Solutions** - Patterns encode best practices from production systems
2. **Composability** - Patterns work together seamlessly
3. **Performance** - Optimized implementations with proper resource management
4. **Maintainability** - Clear separation of concerns

### Pattern Categories

- **Composition** (Sequential, Parallel) - Combine multiple agents
- **Enhancement** (Reflection, React, Planning) - Improve agent quality
- **Specialized** (Task, Conversational, Agents as Tools) - Domain-specific patterns
- **Advanced** (Autonomous, Multiagent, Memory Hierarchy) - Complex behaviors

---

## Pattern Comparison

| Pattern | Complexity | Use Case | Performance | Best For |
|---------|-----------|----------|-------------|----------|
| Sequential | Low | Data pipelines | Fast | Multi-stage processing |
| Parallel | Medium | Independent tasks | Very Fast | Concurrent operations |
| Reflection | Medium | Quality improvement | Slow (iterative) | Self-correction |
| React | Medium | Reasoning | Medium | Decision-making |
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

**Purpose:** Process messages through multiple agents in order.

**When to Use:**
- Data transformation pipelines
- Multi-stage validation
- Step-by-step processing
- When output of agent N feeds into agent N+1

**Pattern:**
```
Input → Agent1 → Agent2 → Agent3 → Output
```

**Implementation:**

```zig
const sequential = @import("agenkit").patterns.sequential;

// Create sequential agent
var seq = try sequential.SequentialAgent.init(allocator);
defer seq.agent().deinit();

// Add agents in order
try seq.addAgent(validator.agent());   // Step 1: Validate
try seq.addAgent(processor.agent());   // Step 2: Process
try seq.addAgent(formatter.agent());   // Step 3: Format

// Process message through pipeline
const result = try seq.agent().process(input_message);
var output = try result.unwrap();
defer output.deinit();
```

**Complete Example:**

```zig
const std = @import("std");
const agenkit = @import("agenkit");

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create agents
    var uppercase = try UppercaseAgent.init(allocator);
    defer uppercase.agent().deinit();

    var exclaim = try ExclaimAgent.init(allocator);
    defer exclaim.agent().deinit();

    // Build pipeline
    var seq = try agenkit.patterns.sequential.SequentialAgent.init(allocator);
    defer seq.agent().deinit();

    try seq.addAgent(uppercase.agent());
    try seq.addAgent(exclaim.agent());

    // Process
    var msg = try agenkit.Message.withText(allocator, .user, "hello world");
    defer msg.deinit();

    const result = try seq.agent().process(msg);
    var response = try result.unwrap();
    defer response.deinit();

    const text = try response.contentAsText();
    // Output: "HELLO WORLD!"
}
```

**Pros:**
- ✅ Simple to understand
- ✅ Predictable execution order
- ✅ Easy to debug
- ✅ Low overhead

**Cons:**
- ❌ No parallelism
- ❌ Slow if many stages
- ❌ One failure stops entire pipeline

**Trade-offs:**
- Use when order matters
- Avoid if stages are independent (use Parallel instead)
- Good for < 5 stages
- For > 10 stages, consider breaking into sub-pipelines

---

### Parallel

**Purpose:** Process messages through multiple agents concurrently.

**When to Use:**
- Independent operations
- Data gathering from multiple sources
- Concurrent analysis
- Fan-out operations

**Pattern:**
```
        ┌─→ Agent1 ─┐
Input ──┼─→ Agent2 ─┼→ Results[]
        └─→ Agent3 ─┘
```

**Implementation:**

```zig
const parallel = @import("agenkit").patterns.parallel;

// Create parallel agent
var par = try parallel.ParallelAgent.init(allocator);
defer par.agent().deinit();

// Add agents to run concurrently
try par.addAgent(search_papers.agent());
try par.addAgent(search_datasets.agent());
try par.addAgent(search_code.agent());

// Process - all agents run concurrently
const results = try par.processAll(query_message);
defer {
    for (results) |*result| {
        if (result.isOk()) {
            var msg = try result.unwrap();
            msg.deinit();
        }
    }
    allocator.free(results);
}

// All results available
for (results) |result| {
    if (result.isOk()) {
        var msg = try result.unwrap();
        defer msg.deinit();
        // Process result...
    }
}
```

**Complete Example:**

```zig
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Create multiple data source agents
    var agent1 = try DataSourceAgent.init(allocator, "Source1");
    defer agent1.agent().deinit();

    var agent2 = try DataSourceAgent.init(allocator, "Source2");
    defer agent2.agent().deinit();

    var agent3 = try DataSourceAgent.init(allocator, "Source3");
    defer agent3.agent().deinit();

    // Create parallel agent
    var par = try agenkit.patterns.parallel.ParallelAgent.init(allocator);
    defer par.agent().deinit();

    try par.addAgent(agent1.agent());
    try par.addAgent(agent2.agent());
    try par.addAgent(agent3.agent());

    // Query all sources concurrently
    var query = try agenkit.Message.withText(allocator, .user, "search query");
    defer query.deinit();

    const results = try par.processAll(query);
    defer {
        for (results) |*result| {
            if (result.isOk()) {
                var msg = try result.unwrap();
                msg.deinit();
            }
        }
        allocator.free(results);
    }

    // Aggregate results
    std.debug.print("Received {d} results\n", .{results.len});
    for (results, 0..) |result, i| {
        if (result.isOk()) {
            var msg = try result.unwrap();
            defer msg.deinit();
            std.debug.print("Result {d}: {s}\n", .{ i + 1, try msg.contentAsText() });
        }
    }
}
```

**Pros:**
- ✅ Fast - operations run concurrently
- ✅ Efficient resource usage
- ✅ Scales well
- ✅ Failures isolated

**Cons:**
- ❌ Results unordered
- ❌ More complex error handling
- ❌ Resource contention possible

**Trade-offs:**
- Use when operations are independent
- Results may arrive in any order
- Good for 2-10 concurrent agents
- Beyond 10, consider batching or rate limiting

---

## Enhancement Patterns

### Reflection

**Purpose:** Agent evaluates and improves its own output.

**When to Use:**
- Quality improvement needed
- Self-correction desired
- Iterative refinement beneficial
- Output needs validation

**Pattern:**
```
Input → Agent → Output → Reflect → Improved Output
         ↑_______________|
```

**Implementation:**

```zig
const reflection = @import("agenkit").patterns.reflection;

// Create base agent
var writer = try WriterAgent.init(allocator);
defer writer.agent().deinit();

// Wrap with reflection
var reflective = try reflection.ReflectionAgent.init(
    allocator,
    writer.agent(),
    3,  // max iterations
);
defer reflective.agent().deinit();

// Process with reflection
const result = try reflective.agent().process(msg);
var improved = try result.unwrap();
defer improved.deinit();
```

**Complete Example:**

```zig
pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    // Base agent that writes text
    var writer = try TextWriterAgent.init(allocator);
    defer writer.agent().deinit();

    // Wrap with reflection for quality improvement
    var reflective = try agenkit.patterns.reflection.ReflectionAgent.init(
        allocator,
        writer.agent(),
        3,  // Try up to 3 iterations
    );
    defer reflective.agent().deinit();

    var msg = try agenkit.Message.withText(allocator, .user, "Write about AI");
    defer msg.deinit();

    std.debug.print("Processing with reflection...\n", .{});
    const result = try reflective.agent().process(msg);
    var improved = try result.unwrap();
    defer improved.deinit();

    std.debug.print("Final (improved) output:\n{s}\n", .{try improved.contentAsText()});
}
```

**How It Works:**

1. Base agent produces initial output
2. Reflection evaluates quality
3. If quality insufficient, feedback given to base agent
4. Base agent produces improved output
5. Repeat up to max iterations

**Pros:**
- ✅ Improves output quality
- ✅ Self-correcting
- ✅ No external training needed
- ✅ Transparent process

**Cons:**
- ❌ Slower (multiple iterations)
- ❌ May not always improve
- ❌ Requires good evaluation criteria

**Trade-offs:**
- Set max iterations to prevent infinite loops
- Define clear quality criteria
- Balance quality vs. speed
- Good for 2-5 iterations typically

---

### React

**Purpose:** Agent reasons before acting.

**When to Use:**
- Decision-making required
- Actions have consequences
- Reasoning should be explicit
- Explanations needed

**Pattern:**
```
Input → Reason → Decision → Act → Output
```

**Implementation:**

```zig
const react = @import("agenkit").patterns.react;

// Create reasoning and acting agents
var reasoner = try ReasoningAgent.init(allocator);
defer reasoner.agent().deinit();

var actor = try ActionAgent.init(allocator);
defer actor.agent().deinit();

// Combine into React pattern
var react_agent = try react.ReactAgent.init(
    allocator,
    reasoner.agent(),
    actor.agent(),
);
defer react_agent.agent().deinit();

// Process with reasoning
const result = try react_agent.agent().process(msg);
```

**Pros:**
- ✅ Explicit reasoning
- ✅ Better decisions
- ✅ Explainable
- ✅ Safer (think before acting)

**Cons:**
- ❌ Slower (two-stage)
- ❌ Requires good reasoner
- ❌ May over-think simple tasks

**Trade-offs:**
- Use when safety matters
- Skip for simple, fast operations
- Consider caching reasoning

---

### Planning

**Purpose:** Break complex tasks into executable steps.

**When to Use:**
- Complex multi-step tasks
- Goal decomposition needed
- Coordination required
- Long-term planning beneficial

**Pattern:**
```
Goal → Plan Steps → Execute Step 1 → ... → Execute Step N → Complete
```

**Implementation:**

```zig
const planning = @import("agenkit").patterns.planning;

// Create executor agent
var executor = try ExecutorAgent.init(allocator);
defer executor.agent().deinit();

// Wrap with planning
var planner = try planning.PlanningAgent.init(
    allocator,
    executor.agent(),
);
defer planner.agent().deinit();

// Process - agent will create and execute plan
const result = try planner.agent().process(goal_message);
```

**Pros:**
- ✅ Handles complex tasks
- ✅ Structured approach
- ✅ Easy to debug
- ✅ Resumable

**Cons:**
- ❌ Slower (planning overhead)
- ❌ May over-plan
- ❌ Requires good planner

**Trade-offs:**
- Use for tasks with > 3 steps
- Consider caching plans
- Balance planning vs. execution time

---

## Specialized Patterns

### Task

**Purpose:** Execute specific, well-defined tasks.

**When to Use:**
- Single-purpose operations
- Job execution
- Focused functionality
- Simple, stateless processing

**Implementation:**

```zig
const task = @import("agenkit").patterns.task;

var task_agent = try task.TaskAgent.init(allocator, "email-sender");
defer task_agent.agent().deinit();

// Task agent handles specific job
const result = try task_agent.agent().process(email_message);
```

**Pros:**
- ✅ Simple and focused
- ✅ Easy to test
- ✅ Clear responsibility
- ✅ Fast

**Cons:**
- ❌ Limited to single task
- ❌ Not composable alone
- ❌ May need orchestration

**Trade-offs:**
- Best for < 100 lines of logic
- Combine multiple task agents for workflows
- Keep state minimal

---

### Conversational

**Purpose:** Maintain dialogue context across turns.

**When to Use:**
- Chatbots
- Interactive systems
- Multi-turn conversations
- Context-dependent responses

**Implementation:**

```zig
const conversational = @import("agenkit").patterns.conversational;

var conv = try conversational.ConversationalAgent.init(allocator);
defer conv.agent().deinit();

// Turn 1
var msg1 = try agenkit.Message.withText(allocator, .user, "My name is Alice");
defer msg1.deinit();
const result1 = try conv.agent().process(msg1);
var response1 = try result1.unwrap();
defer response1.deinit();

// Turn 2 - agent remembers context
var msg2 = try agenkit.Message.withText(allocator, .user, "What's my name?");
defer msg2.deinit();
const result2 = try conv.agent().process(msg2);
var response2 = try result2.unwrap();
defer response2.deinit();
// Response: "Your name is Alice"
```

**Pros:**
- ✅ Context-aware
- ✅ Natural dialogue
- ✅ Remembers history
- ✅ Good UX

**Cons:**
- ❌ Context grows unbounded
- ❌ Memory usage increases
- ❌ Old context may be stale

**Trade-offs:**
- Implement context window limits
- Use Memory Hierarchy for longer conversations
- Consider forgetting old context

---

### Agents as Tools

**Purpose:** Agents use other agents as tools.

**When to Use:**
- Tool orchestration
- Agent delegation
- Capability composition
- Dynamic tool selection

**Pattern:**
```
Main Agent → Select Tool → Tool Agent → Result → Main Agent
```

**Implementation:**

```zig
const tools = @import("agenkit").patterns.agents_as_tools;

// Create main orchestrator
var main = try tools.ToolUsingAgent.init(allocator);
defer main.agent().deinit();

// Register tool agents
try main.registerTool("calculator", calculator_agent.agent());
try main.registerTool("search", search_agent.agent());
try main.registerTool("weather", weather_agent.agent());

// Main agent will select and use appropriate tools
var msg = try agenkit.Message.withText(allocator, .user, "What's 5 + 3?");
defer msg.deinit();

const result = try main.agent().process(msg);
// Main agent uses calculator tool
```

**Pros:**
- ✅ Flexible tool usage
- ✅ Extensible
- ✅ Reusable tools
- ✅ Clear separation

**Cons:**
- ❌ Complex orchestration
- ❌ Tool selection overhead
- ❌ Error propagation tricky

**Trade-offs:**
- Good for 3-10 tools
- Consider tool categories for > 10
- Cache tool capabilities

---

## Advanced Patterns

### Autonomous

**Purpose:** Self-directed goal pursuit.

**When to Use:**
- Goal-driven systems
- Long-running operations
- Self-directed behavior
- Minimal human intervention needed

**Pattern:**
```
Goal → Plan → Execute → Evaluate → Adjust Plan → ...
```

**Implementation:**

```zig
const autonomous = @import("agenkit").patterns.autonomous;

var auto = try autonomous.AutonomousAgent.init(
    allocator,
    "Build a web scraper",
    100,  // max steps
);
defer auto.deinit();

// Agent will autonomously work toward goal
const result = try auto.run();
defer result.deinit();

std.debug.print("Goal completion: {d}%\n", .{result.progress});
```

**Pros:**
- ✅ Self-directed
- ✅ Handles complexity
- ✅ Adapts to feedback
- ✅ Minimal supervision

**Cons:**
- ❌ Unpredictable
- ❌ May diverge from goal
- ❌ Hard to debug
- ❌ Resource intensive

**Trade-offs:**
- Set step limits to prevent runaway
- Monitor progress regularly
- Provide clear goals
- Use for high-level objectives only

---

### Multiagent

**Purpose:** Coordinate multiple agents working together.

**When to Use:**
- Multiple agent collaboration
- Distributed processing
- Specialized agent teams
- Complex system coordination

**Pattern:**
```
Task → Coordinator → Assign to Agents → Aggregate Results
```

**Implementation:**

```zig
const multiagent = @import("agenkit").patterns.multiagent;

// Create multi-agent system
var multi = try multiagent.MultiagentSystem.init(allocator);
defer multi.agent().deinit();

// Add specialist agents
try multi.addAgent("researcher", researcher.agent());
try multi.addAgent("analyzer", analyzer.agent());
try multi.addAgent("writer", writer.agent());

// Coordinate agents to complete task
var task = try agenkit.Message.withText(allocator, .user, "Research AI agents");
defer task.deinit();

const result = try multi.coordinate(task);
var report = try result.unwrap();
defer report.deinit();
```

**Pros:**
- ✅ Specialized agents
- ✅ Parallel execution
- ✅ Scalable
- ✅ Fault tolerant

**Cons:**
- ❌ Coordination overhead
- ❌ Complex communication
- ❌ Deadlock risk
- ❌ Hard to debug

**Trade-offs:**
- Good for 2-5 agents
- Use message passing for communication
- Implement timeouts
- Consider hierarchical coordination

---

### Memory Hierarchy

**Purpose:** Efficient memory management for long-running agents.

**When to Use:**
- Long conversations
- Context window management
- Efficient memory usage
- Working/short/long-term memory needed

**Pattern:**
```
Working Memory (recent) ← Short-term Memory ← Long-term Memory (archive)
```

**Implementation:**

```zig
const memory = @import("agenkit").patterns.memory_hierarchy;

// Create base agent
var base = try ConversationalAgent.init(allocator);
defer base.agent().deinit();

// Add memory hierarchy
var mem = try memory.MemoryHierarchyAgent.init(
    allocator,
    base.agent(),
);
defer mem.agent().deinit();

// Memory automatically manages context
for (many_messages) |msg| {
    const result = try mem.agent().process(msg);
    // Old context moved to long-term storage
}
```

**How Memory Tiers Work:**

1. **Working Memory** - Recent 3-5 messages, always in context
2. **Short-term Memory** - Last 10-20 messages, loaded on demand
3. **Long-term Memory** - All messages, summarized or archived

**Pros:**
- ✅ Efficient context usage
- ✅ Handles long conversations
- ✅ Automatic management
- ✅ Faster processing

**Cons:**
- ❌ May lose details
- ❌ Retrieval overhead
- ❌ Complex implementation

**Trade-offs:**
- Tune window sizes for your use case
- Balance memory vs. context quality
- Consider semantic retrieval for long-term

---

## Pattern Selection Guide

### By Use Case

| Use Case | Recommended Pattern | Alternative |
|----------|-------------------|-------------|
| Data pipeline | Sequential | Parallel (if independent) |
| Web scraping | Parallel | Sequential (if order matters) |
| Quality improvement | Reflection | React + Planning |
| Chatbot | Conversational | Conversational + Memory |
| Tool orchestration | Agents as Tools | Multiagent |
| Complex goals | Autonomous | Planning |
| Long conversations | Memory Hierarchy | Conversational |
| Decision-making | React | Planning |
| Team coordination | Multiagent | Sequential |
| Job execution | Task | Sequential |

### By Complexity

**Simple (1-2 weeks to learn)**
- Sequential
- Parallel
- Task

**Medium (2-4 weeks to learn)**
- Conversational
- Reflection
- React

**Advanced (1-2 months to master)**
- Planning
- Agents as Tools
- Memory Hierarchy

**Expert (2-3 months to master)**
- Autonomous
- Multiagent

### By Performance

**Fast (< 100ms per message)**
- Task
- Sequential (few stages)
- Parallel

**Medium (100ms - 1s)**
- Conversational
- React
- Agents as Tools

**Slow (> 1s)**
- Reflection (iterations)
- Planning (planning overhead)
- Autonomous (complex reasoning)

---

## Composing Patterns

Patterns can be combined for powerful workflows.

### Example 1: Parallel + Sequential

Gather data in parallel, then process sequentially:

```zig
// Stage 1: Parallel data gathering
var gather = try ParallelAgent.init(allocator);
try gather.addAgent(source1.agent());
try gather.addAgent(source2.agent());
try gather.addAgent(source3.agent());

// Stage 2: Sequential processing
var process = try SequentialAgent.init(allocator);
try process.addAgent(gather.agent());  // ← Parallel agent as first stage
try process.addAgent(merge.agent());
try process.addAgent(analyze.agent());

const result = try process.agent().process(query);
```

### Example 2: Conversational + Memory Hierarchy

Long-running chatbot with efficient memory:

```zig
var chat = try ConversationalAgent.init(allocator);
var mem = try MemoryHierarchyAgent.init(allocator, chat.agent());

// Can handle thousands of messages efficiently
```

### Example 3: Reflection + Agents as Tools

Quality-checked tool orchestration:

```zig
var tools = try ToolUsingAgent.init(allocator);
try tools.registerTool("search", search.agent());
try tools.registerTool("calc", calc.agent());

var reflect = try ReflectionAgent.init(allocator, tools.agent(), 3);

// Tools are used, then results are quality-checked
```

### Example 4: React + Planning + Autonomous

Self-directed agent with reasoning and planning:

```zig
var planner = try PlanningAgent.init(allocator, executor.agent());
var reasoner = try ReactAgent.init(allocator, reasoner.agent(), planner.agent());
var auto = try AutonomousAgent.init(allocator, "goal", 100);
// Configure auto to use reasoner...

// Autonomous agent that reasons before planning before executing
```

### Composition Guidelines

1. **Keep it simple** - Max 2-3 pattern layers
2. **Test incrementally** - Add patterns one at a time
3. **Monitor performance** - Each layer adds overhead
4. **Document clearly** - Complex compositions need good docs
5. **Profile** - Measure actual performance impact

---

## Best Practices

### Pattern Selection

1. **Start simple** - Use simplest pattern that works
2. **Measure first** - Profile before optimizing
3. **Consider maintenance** - Complex patterns = harder debugging
4. **Think composability** - Will you combine patterns later?

### Performance

1. **Set timeouts** - Prevent hanging
2. **Limit iterations** - Prevent infinite loops
3. **Monitor resources** - Watch memory/CPU
4. **Batch when possible** - Process multiple messages together

### Error Handling

1. **Handle all errors** - Every pattern can fail
2. **Provide fallbacks** - What if a pattern fails?
3. **Log failures** - Debug with good logging
4. **Test error paths** - Not just happy paths

### Testing

1. **Unit test patterns** - Test each pattern individually
2. **Integration test compositions** - Test pattern combinations
3. **Load test** - Test under realistic load
4. **Test failure modes** - What happens when agents fail?

---

## Examples

See the `examples/` directory for working examples:

```bash
# Pattern examples
zig build run-sequential
zig build run-parallel
zig build run-reflection

# Integration examples
zig build run-multi-pattern      # Combines multiple patterns
zig build run-long-running        # Memory Hierarchy
zig build run-evaluation          # Performance testing
```

---

## Further Reading

- [API Reference](API.md) - Complete API documentation
- [Getting Started](GETTING_STARTED.md) - Basic usage
- [Migration Guide](MIGRATION.md) - Porting from other languages

---

## Summary

- **11 patterns** covering common agent architectures
- **Composable** - combine patterns for complex workflows
- **Production-ready** - optimized implementations
- **Well-tested** - comprehensive test suites
- **Documented** - clear usage and trade-offs

Choose the right pattern for your use case, start simple, and compose as needed.

**Happy agent building! 🚀**
