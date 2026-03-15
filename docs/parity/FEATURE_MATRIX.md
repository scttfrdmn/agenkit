# Feature Parity Matrix

**Generated**: 2026-03-15 02:59:57 UTC

This matrix shows feature implementation status across all 6 Agenkit language implementations.

**Legend**:
- ✅ **Implemented** - Feature present in language
- ❌ **Missing** - Feature not yet implemented
- 🔧 **Partial** - Implementation exists but incomplete (future)

---

## Summary Statistics

| Language | Total Features | Parity % | Test Coverage |
|----------|----------------|----------|---------------|
| python     | 43 | 100.0% | 1836 tests |
| go         | 43 | 100.0% | 950 tests |
| typescript | 36 | 83.7% | 863 tests |
| rust       | 38 | 88.4% | 681 tests |
| cpp        | 37 | 86.0% | 793 tests |
| zig        | 27 | 62.8% | 214 tests |

---

## Feature Matrix by Category


### Patterns



| Feature | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|----|-----------| -----|-----|-----|
| AgentTask | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AgentTool | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| AutonomousAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ClassifierAgent | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| CollaborativeAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ConsensusAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| ConversationalAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| FallbackAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| HumanInLoopAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| MultiAgentConfig | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| MultiAgentOrchestrator | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| OrchestrationAgent | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ |
| ParallelAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PlannerAgent | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| PlanningAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ReActAgent | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| ReactAgent | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| ReasoningAgent | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| ReasoningWithToolsAgent | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| RecoveryAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| ReflectionAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| RouterAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SequentialAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| StreamingConversationalAgent | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| SupervisorAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Totals**:
Python: 23, Go: 17, TypeScript: 17, Rust: 15, C++: 18, Zig: 13


---


### Middleware



| Feature | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|----|-----------| -----|-----|-----|
| BatchingConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| BatchingDecorator | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| BatchingMiddleware | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| CachingConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| CachingDecorator | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| CachingMiddleware | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| CircuitBreakerConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| CircuitBreakerDecorator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| CircuitBreakerMiddleware | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| MetricsDecorator | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| PerUserRateLimiterConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| PerUserRateLimiterDecorator | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| PerUserRateLimiterMiddleware | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| RateLimiterConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| RateLimiterDecorator | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| RateLimiterMiddleware | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| RetryConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| RetryDecorator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| RetryMiddleware | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| TimeoutConfig | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| TimeoutDecorator | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| TimeoutMiddleware | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |

**Totals**:
Python: 8, Go: 14, TypeScript: 7, Rust: 14, C++: 14, Zig: 14


---


### Llm Adapters



| Feature | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|----|-----------| -----|-----|-----|
| AnthropicAdapter | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| AnthropicLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| BedrockAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| BedrockLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| GeminiAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| GeminiLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| LiteLLMAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| LiteLLMLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| LocalAgent | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| OllamaAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| OllamaLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| OpenAIAdapter | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| OpenAICompatibleLLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| OpenAILLM | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

**Totals**:
Python: 7, Go: 7, TypeScript: 7, Rust: 6, C++: 5, Zig: 0


---


### Memory



| Feature | Python | Go | TypeScript | Rust | C++ | Zig |
|---------|--------|----|-----------| -----|-----|-----|
| EndlessMemory | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| HierarchyMemory | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| InMemoryMemory | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| RedisMemory | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| VectorMemory | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

**Totals**:
Python: 5, Go: 5, TypeScript: 5, Rust: 3, C++: 0, Zig: 0


---



## Category Breakdown

| Category | Python | Go | TypeScript | Rust | C++ | Zig |
|----------|--------|----|-----------| -----|-----|-----|
| Patterns | 23 | 17 | 17 | 15 | 18 | 13 |
| Middleware | 8 | 14 | 7 | 14 | 14 | 14 |
| Llm Adapters | 7 | 7 | 7 | 6 | 5 | 0 |
| Memory | 5 | 5 | 5 | 3 | 0 | 0 |

---

## Insights








### Top Performing Languages (by feature count)
1. **Go** - 43 features (100.0% parity) - Excellent coverage!
2. **TypeScript** - 36 features (83.7% parity) - Strong implementation
3. **Rust** - 38 features (88.4% parity) - Growing rapidly

### Areas for Improvement


### Test Coverage Highlights
- **Python**: 1836 tests
- **Go**: 950 tests
- **Typescript**: 863 tests
- **Rust**: 681 tests
- **Cpp**: 793 tests
- **Zig**: 214 tests


---

## Next Steps

1. **Phase 3**: Implement Rust, C++, and Zig scanners to complete parity tracking
2. **Gap Analysis**: Review `GAPS_ANALYSIS.md` for specific missing features
3. **CI Integration**: Add parity validation to prevent regressions

---

*Generated by: `scripts/parity/matrix_generator.py`*
*Feature data from: `feature-manifest.json`*
*Test data from: `test-parity-report.json`*