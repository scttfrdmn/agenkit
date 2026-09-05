# Feature Parity Matrix

**Generated**: 2026-09-05 01:13:43 UTC

This matrix shows feature implementation status across all 9 Agenkit language implementations.

**Legend**:
- ✅ **Implemented** - Feature present in language
- ❌ **Missing** - Feature not yet implemented

---

## Summary Statistics

| Language | Total Features | Parity % | Test Coverage |
|----------|----------------|----------|---------------|
| python     | 58 | 100.0% | 2229 tests |
| go         | 54 | 93.1% | 1341 tests |
| cpp        | 49 | 84.5% | 1133 tests |
| rust       | 49 | 84.5% | 1352 tests |
| typescript | 47 | 81.0% | 976 tests |
| zig        | 45 | 77.6% | 671 tests |
| csharp     | 33 | 56.9% | 272 tests |
| java       | 33 | 56.9% | 358 tests |
| scala      | 33 | 56.9% | 363 tests |

---

## Feature Matrix by Category


### Patterns



| Feature | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|---------|------|------|------|------|------|------|------|------|------|
| AgentTask | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| AgentTool | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| AutonomousAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| ClassifierAgent | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| CollaborativeAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| ConditionalAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 
| ConsensusAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| ConversationalAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| ConversationalAgentConfig | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| FallbackAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| HumanInLoopAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| MemoryAugmentedAgent | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| MultiAgentConfig | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| MultiAgentOrchestrator | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| OrchestrationAgent | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| ParallelAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| PlannerAgent | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| PlanningAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| ReActAgent | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| ReactAgent | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| ReasoningAgent | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| ReasoningWithToolsAgent | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| RecoveryAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| ReflectionAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| RouterAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| SequentialAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| StreamingConversationalAgent | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| SupervisorAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 
| TaskAgent | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 


**Totals**:
Python: 25, Go: 18, Cpp: 19, Rust: 16, Typescript: 18, Zig: 13, Csharp: 18, Java: 18, Scala: 18


---


### Middleware



| Feature | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|---------|------|------|------|------|------|------|------|------|------|
| BatchingConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| BatchingDecorator | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| BatchingMiddleware | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| CachingConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| CachingDecorator | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| CachingMiddleware | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| CircuitBreakerConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| CircuitBreakerDecorator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| CircuitBreakerMiddleware | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 
| MetricsDecorator | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| MetricsMiddleware | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| PerUserRateLimiterConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| PerUserRateLimiterDecorator | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| PerUserRateLimiterMiddleware | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| RateLimiterConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| RateLimiterDecorator | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| RateLimiterMiddleware | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| RetryConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| RetryDecorator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| RetryMiddleware | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 
| TimeoutConfig | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| TimeoutDecorator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| TimeoutMiddleware | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 


**Totals**:
Python: 8, Go: 14, Cpp: 14, Rust: 14, Typescript: 7, Zig: 14, Csharp: 8, Java: 8, Scala: 8


---


### Llm Adapters



| Feature | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|---------|------|------|------|------|------|------|------|------|------|
| AnthropicAdapter | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 
| AnthropicLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| BedrockAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| BedrockLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| GeminiAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| GeminiLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| LiteLLMAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| LiteLLMLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| LocalAgent | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| MockAdapter | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| OllamaAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| OllamaLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| OpenAIAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| OpenAICompatibleLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| OpenAILLM | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| OpenAiAdapter | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 


**Totals**:
Python: 7, Go: 7, Cpp: 5, Rust: 6, Typescript: 7, Zig: 6, Csharp: 3, Java: 3, Scala: 3


---


### Memory



| Feature | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|---------|------|------|------|------|------|------|------|------|------|
| EndlessMemory | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| EphemeralMemory | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| HierarchyMemory | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| InMemoryMemory | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| MemoryHierarchy | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | 
| RedisMemory | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| VectorMemory | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 


**Totals**:
Python: 5, Go: 5, Cpp: 2, Rust: 3, Typescript: 5, Zig: 3, Csharp: 3, Java: 3, Scala: 3


---


### Techniques



| Feature | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|---------|------|------|------|------|------|------|------|------|------|
| ActorCriticVariation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| ChainOfThought | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| ChainOfThoughtAgent | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| ExplorationStrategy | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| GraphOfThought | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| GraphOfThoughtAgent | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| LeastToMost | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| LeastToMostAgent | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| PlanAndSolve | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| PlanAndSolveAgent | ❌ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 
| ReasoningGraph | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| ReasoningTree | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| SelfConsistency | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| SelfConsistencyAgent | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | 
| TreeOfThought | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| TreeOfThoughtAgent | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | 


**Totals**:
Python: 10, Go: 8, Cpp: 8, Rust: 8, Typescript: 8, Zig: 8, Csharp: 0, Java: 0, Scala: 0


---


### Protocols



| Feature | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|---------|------|------|------|------|------|------|------|------|------|
| a2a | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 
| agui | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 
| mcp | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 


**Totals**:
Python: 3, Go: 2, Cpp: 1, Rust: 2, Typescript: 2, Zig: 1, Csharp: 1, Java: 1, Scala: 1


---



## Category Breakdown

| Category | Python | Go | Cpp | Rust | Typescript | Zig | Csharp | Java | Scala | 
|----------|------|------|------|------|------|------|------|------|------|
| Patterns | 25 | 18 | 19 | 16 | 18 | 13 | 18 | 18 | 18 | 
| Middleware | 8 | 14 | 14 | 14 | 7 | 14 | 8 | 8 | 8 | 
| Llm Adapters | 7 | 7 | 5 | 6 | 7 | 6 | 3 | 3 | 3 | 
| Memory | 5 | 5 | 2 | 3 | 5 | 3 | 3 | 3 | 3 | 
| Techniques | 10 | 8 | 8 | 8 | 8 | 8 | 0 | 0 | 0 | 
| Protocols | 3 | 2 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 


---

## Gap Analysis

See `GAPS_ANALYSIS.md` for features present in the reference implementation
(Python) but missing in other languages.


## Test Coverage Highlights
- **Python**: 2229 tests
- **Go**: 1341 tests
- **Cpp**: 1133 tests
- **Rust**: 1352 tests
- **Typescript**: 976 tests
- **Zig**: 671 tests
- **Csharp**: 272 tests
- **Java**: 358 tests
- **Scala**: 363 tests


---

*Generated by: `scripts/parity/matrix_generator.py`*
*Feature data from: `feature-manifest.json`*
*Test data from: `test-parity-report.json`*