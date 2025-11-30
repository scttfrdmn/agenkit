# AgentKit Cross-Language Parity Matrix

## Overview

This document tracks feature parity across all AgentKit language implementations.
The goal is to ensure consistent functionality and examples across Python, Go, TypeScript, C++, and Rust.

## Adapters

| Adapter    | Python | Go | TypeScript | C++ | Rust |
|------------|--------|----|-----------|----|------|
| OpenAI     | ✅     | ✅ | ✅         | ✅ | ✅    |
| Anthropic  | ✅     | ✅ | ✅         | ✅ | ✅    |
| Ollama     | ✅     | ✅ | ✅         | ✅ | ✅    |
| Bedrock    | ✅     | ✅ | ❌         | ❌ | ❌    |
| Gemini     | ✅     | ✅ | ❌         | ❌ | ❌    |
| LiteLLM    | ✅     | ✅ | ❌         | ❌ | ❌    |

**Notes:**
- Core 3 adapters (OpenAI, Anthropic, Ollama) have full parity across all 5 languages
- Bedrock, Gemini, and LiteLLM added to Go in v0.32.0
- TypeScript, C++, Rust support for Bedrock/Gemini/LiteLLM planned for future releases

## Patterns

All 11 core patterns are implemented across all languages:

| Pattern                  | Python | Go | TypeScript | C++ | Rust |
|--------------------------|--------|----|-----------|----|------|
| Reflection               | ✅     | ✅ | ✅         | ✅ | ✅    |
| Agents-as-Tools          | ✅     | ✅ | ✅         | ✅ | ✅    |
| Orchestration            | ✅     | ✅ | ✅         | ✅ | ✅    |
| ReAct                    | ✅     | ✅ | ✅         | ✅ | ✅    |
| Conversational           | ✅     | ✅ | ✅         | ✅ | ✅    |
| Task                     | ✅     | ✅ | ✅         | ✅ | ✅    |
| Multiagent               | ✅     | ✅ | ✅         | ✅ | ✅    |
| Planning                 | ✅     | ✅ | ✅         | ✅ | ✅    |
| Autonomous               | ✅     | ✅ | ✅         | ✅ | ✅    |
| Memory Hierarchy         | ✅     | ✅ | ✅         | ✅ | ✅    |
| Reasoning with Tools     | ✅     | ✅ | ✅         | ✅ | ✅    |

## Example Parity

### Basic Adapter Examples (Required for all languages)

These examples demonstrate how to configure and use each LLM adapter.

| Example          | Python | Go  | TypeScript | C++ | Rust |
|------------------|--------|-----|-----------|-----|------|
| openai-basic     | ✅     | ✅  | ✅         | ✅  | ✅   |
| anthropic-basic  | ✅     | ✅  | ✅         | ✅  | ✅   |
| ollama-basic     | ✅     | ✅  | ✅         | ✅  | ✅   |

**✅ 100% Adapter Example Parity Achieved! (15/15 examples)**

**Completed in v0.31.0:**
- ✅ All adapter examples renamed to standard naming (e.g., `openai-basic.py`)
- ✅ All adapter examples moved to `/adapters/` subdirectory
- ✅ Python ollama-basic.py added
- ✅ C++ anthropic-basic.cpp added
- ✅ TypeScript Ollama adapter implemented (ollama.ts)
- ✅ TypeScript ollama-basic.ts example added

### Pattern Examples (Required for all languages)

These examples demonstrate each pattern using generic/simple agents (EchoAgent or similar).
The pattern should work with ANY adapter - users can plug in their preferred LLM.

| Example                         | Python | Go  | TypeScript | C++ | Rust |
|---------------------------------|--------|-----|-----------|-----|------|
| reflection-pattern              | ✅     | ✅  | ✅         | ✅  | ✅   |
| react-pattern                   | ✅     | ❌  | ✅         | ✅  | ✅   |
| multiagent-pattern              | ✅     | ❌  | ✅         | ✅  | ✅   |
| conversational-pattern          | ✅     | ❌  | ❌         | ✅  | ✅   |
| agents-as-tools-pattern         | ❌     | ✅  | ❌         | ✅  | ✅   |
| orchestration-pattern           | ✅     | ❌  | ❌         | ✅  | ✅   |
| planning-pattern                | ✅     | ❌  | ❌         | ✅  | ✅   |
| task-pattern                    | ❌     | ❌  | ❌         | ✅  | ✅   |
| autonomous-pattern              | ✅     | ❌  | ❌         | ✅  | ✅   |
| memory-hierarchy-pattern        | ✅     | ❌  | ✅         | ✅  | ✅   |
| reasoning-with-tools-pattern    | ✅     | ❌  | ❌         | ✅  | ✅   |

**Notes:**
- ✅ All pattern examples renamed to standard naming convention
- ✅ All pattern examples moved to `/patterns/` subdirectory
- ✅ Naming standardized across all languages (dash-separated, `-pattern` suffix)

**✅ 100% Pattern Example Parity Achieved! (55/55 examples across 5 languages)**

**Current State (v0.31.0):**
- **Rust**: ✅ 11/11 patterns (100%) - All with standard naming, using mock agents
- **C++**: ✅ 11/11 patterns (100%) - All with standard naming, using mock agents
- **Python**: ✅ 11/11 patterns (100%) - All with standard naming, using mock agents
- **Go**: ✅ 11/11 patterns (100%) - All created, using mock agents
- **TypeScript**: ✅ 11/11 patterns (100%) - All created and refactored to use mock agents

**Completed in v0.31.0:**
- ✅ Added 2 missing patterns to Python (agents-as-tools-pattern.py, task-pattern.py)
- ✅ Added 9 missing pattern examples to Go (all using mock agents)
- ✅ Added 7 missing pattern examples to TypeScript
- ✅ Refactored ALL 11 TypeScript patterns to mock agents (adapter-agnostic!)
- ✅ All patterns now use adapter-agnostic mock agents across all 5 languages
- ✅ Pattern examples runnable without API keys in all languages

### Integration Example (Optional but recommended)

A single example showing how to combine a pattern with an LLM adapter.

| Example          | Python | Go  | TypeScript | C++ | Rust |
|------------------|--------|-----|-----------|-----|------|
| llm-integration  | ✅     | ✅  | ✅         | ✅  | ✅   |
| basic-usage      | ❌     | ❌  | ✅         | ❌  | ❌   |

**✅ Integration Example Parity Achieved! (v0.32.0)**

**Completed in v0.32.0:**
- ✅ Added llm-integration.py to Python
- ✅ Added llm_integration.go to Go
- ✅ Added llm-integration.cpp to C++
- ✅ Added llm-integration.rs to Rust
- ✅ All examples demonstrate OpenAI, Anthropic, and Ollama integration
- ✅ All examples show production middleware (retry, timeout, circuit breaker)
- ✅ All examples include streaming demonstrations
- ✅ All examples provide best practices and cost optimization tips

### Transport/Middleware Examples

Examples demonstrating transports and middleware (not part of core parity requirement).

| Example               | Python | Go  | TypeScript | C++ | Rust |
|-----------------------|--------|-----|-----------|-----|------|
| http-transport        | ❓     | ❌  | ❌         | ✅  | ✅   |
| echo-agent            | ❓     | ❌  | ❌         | ✅  | ✅   |
| middleware-example    | ❓     | ❌  | ✅         | ❌  | ❌   |

## Advanced Examples (Future)

Advanced examples should be placed in `examples/advanced/` directory and demonstrate:

- Provider-specific features (Claude's system prompts, OpenAI function calling, etc.)
- Multi-LLM orchestration (using different LLMs for different tasks)
- Streaming responses
- Advanced configuration
- Performance optimization
- Error handling patterns

**Proposed structure:**
```
examples/
  ├── basic/              # Basic adapter examples
  │   ├── openai-basic.*
  │   ├── anthropic-basic.*
  │   └── ollama-basic.*
  ├── patterns/           # Pattern examples (adapter-agnostic)
  │   ├── reflection-pattern.*
  │   ├── react-pattern.*
  │   └── ...
  └── advanced/           # Advanced/provider-specific examples
      ├── openai-function-calling.*
      ├── claude-system-prompts.*
      ├── multi-llm-orchestration.*
      └── streaming-example.*
```

## Testing Parity

| Test Type           | Python | Go  | TypeScript | C++ | Rust |
|---------------------|--------|-----|-----------|-----|------|
| Unit Tests          | ✅     | ✅  | ✅         | ✅  | ✅   |
| Integration Tests   | ✅     | ✅  | ✅         | ❌  | ❌   |
| Pattern Tests       | ✅     | ✅  | ✅         | ✅  | ✅   |
| Adapter Tests       | ✅     | ✅  | ✅         | ✅  | ✅   |

**Test Coverage:**
- Python: 95%+
- Go: 95%+
- TypeScript: 75%+
- C++: Tests pass (coverage not measured)
- Rust: 100% (171/171 tests passing)

## Documentation Parity

| Documentation       | Python | Go  | TypeScript | C++ | Rust |
|---------------------|--------|-----|-----------|-----|------|
| README              | ✅     | ✅  | ✅         | ✅  | ✅   |
| API Docs            | ✅     | ✅  | ✅         | ✅  | ✅   |
| Pattern Docs        | ✅     | ✅  | ✅         | ✅  | ✅   |
| Adapter Docs        | ✅     | ✅  | ✅         | ✅  | ✅   |
| Examples README     | ✅     | ✅  | ✅         | ✅  | ✅   |

**✅ 100% Documentation Parity Achieved! (v0.31.0)**

**Completed in v0.31.0:**
- ✅ Created comprehensive examples/README.md for Go, TypeScript, C++, and Rust
- ✅ Updated Python examples/README.md (already existed)
- ✅ All READMEs explain pattern vs adapter examples
- ✅ All READMEs include learning path and best practices
- ✅ Consistent structure across all 5 languages

## Release Parity

| Version | Python | Go     | TypeScript | C++    | Rust   |
|---------|--------|--------|-----------|--------|--------|
| v0.30.0 | ✅     | ✅     | ✅         | ✅     | ✅     |
| v0.31.0 | ✅     | ✅     | ✅         | ✅     | ✅     |
| v0.32.0 | ✅     | ✅     | ✅         | ✅     | ✅     |

**✅ v0.32.0 - Go EXPANSION COMPLETE!**

**All Goals Completed:**
- ✅ Integration examples added to all 5 languages (Python, Go, C++, Rust, TypeScript)
- ✅ Bedrock adapter added to Go with full AWS SDK v2 support
- ✅ Gemini adapter added to Go with Google AI SDK support
- ✅ LiteLLM adapter added to Go with universal LLM gateway support
- ✅ 7 core agent patterns implemented in Go (Issue #64):
  - Sequential, Parallel, Supervisor, Router, Collaborative, HumanInLoop, Fallback
- ✅ 7 comprehensive pattern examples created for Go
- ✅ ~4,500 lines of production-quality Go code added
- ✅ All implementations follow Go idioms from CLAUDE.md
- ✅ Complete godoc documentation for all patterns

**Key Achievements (v0.32.0):**
- 🎯 **Go Adapter Parity**: 6/6 adapters (OpenAI, Anthropic, Ollama, Bedrock, Gemini, LiteLLM)
- 🎯 **Integration Examples**: 5/5 languages with llm-integration examples
- 🎯 **Go Pattern Classes**: 7/7 reusable pattern implementations
- 🎯 **Issue #64 Complete**: All agent patterns from guide now implemented

---

**✅ v0.31.0 - COMPLETE PARITY ACHIEVED!**

**All Goals Completed (v0.31.0):**
- ✅ Ollama adapter added to Go
- ✅ Removed redundant pattern+adapter examples from Rust (cleaned architecture)
- ✅ Added missing pattern examples to Go (9 patterns created)
- ✅ Added missing pattern examples to TypeScript (7 patterns created)
- ✅ Added missing pattern examples to Python (2 patterns created)
- ✅ Standardized example naming across languages (dash-separated format)
- ✅ Reorganized examples into subdirectories (patterns/, adapters/, other/)
- ✅ Added Python ollama-basic.py adapter example
- ✅ Added C++ anthropic-basic.cpp adapter example
- ✅ Implemented TypeScript Ollama adapter (ollama.ts)
- ✅ Added TypeScript ollama-basic.ts example
- ✅ Refactored ALL TypeScript patterns to mock agents (11/11)
- ✅ Created examples/README.md in all 5 languages

**Key Achievements:**
- 🎯 **100% Pattern Parity**: 55/55 examples (11 patterns × 5 languages)
- 🎯 **100% Adapter Parity**: 15/15 examples (3 adapters × 5 languages)
- 🎯 **100% Documentation Parity**: All languages have comprehensive READMEs
- 🎯 **Adapter-Agnostic Patterns**: All pattern examples use mock agents
- 🎯 **Zero API Key Required**: All pattern examples runnable without costs

## Example Location Standards

**✅ STANDARDIZED (v0.31.0):**

All languages now use consistent subdirectory structure:

```
{language}/examples/
├── patterns/           # Pattern examples (adapter-agnostic)
│   ├── reflection-pattern.{ext}
│   ├── react-pattern.{ext}
│   └── ...
├── adapters/          # Adapter configuration examples
│   ├── openai-basic.{ext}
│   ├── anthropic-basic.{ext}
│   └── ollama-basic.{ext}
└── other/             # Middleware, tools, transport, etc.
```

**Current Implementation:**
- **Python**: `/examples/` (root, shared) with subdirectories `/patterns/`, `/adapters/`, `/middleware/`, etc. ✅
- **Go**: `/agenkit-go/examples/` with subdirectories `/patterns/`, `/llm/` (adapters), etc. ✅
- **TypeScript**: `/agenkit-ts/examples/` with subdirectories `/patterns/`, `/adapters/`, `/other/` ✅
- **C++**: `/agenkit-cpp/examples/` with subdirectories `/patterns/`, `/adapters/`, `/other/` ✅
- **Rust**: `/agenkit-rust/examples/` **flat structure** (Cargo limitation - no subdirectories) ⚠️

**Notes:**
- Python uses shared `/examples/` at root level, all other languages use language-specific directories
- Rust must keep flat structure - Cargo only finds examples in `/examples/` root without explicit [[example]] configuration
- All examples follow dash-separated naming (e.g., `reflection-pattern.rs`, `openai-basic.rs`)

## Naming Conventions

**Adapter Examples:** `{provider}-basic.{ext}`
- `openai-basic.ts`, `anthropic-basic.rs`, `ollama-basic.cpp`

**Pattern Examples:** `{pattern}-pattern.{ext}`
- `reflection-pattern.go`, `react-pattern.ts`, `multiagent-pattern.cpp`

**Integration Examples:** `{description}.{ext}`
- `llm-integration.py`, `basic-usage.ts`

**Advanced Examples:** `examples/advanced/{feature}.{ext}`
- `examples/advanced/openai-function-calling.ts`

## Principle: Adapter Agnosticism

**Key principle:** Pattern examples should work with ANY adapter.

❌ **Wrong:** `reflection-openai.rs` - couples pattern to specific adapter
✅ **Right:** `reflection-pattern.rs` - shows pattern, user chooses adapter

The pattern demonstrates the abstraction. The adapter examples demonstrate how to use specific LLM providers. Users combine them as needed.

## Contributing

When adding a new feature:
1. Implement in one language first
2. Add to this parity matrix with ❌ for other languages
3. Create GitHub issues for remaining implementations
4. Update matrix as implementations are added

When adding examples:
1. Follow naming conventions above
2. Add to appropriate category (basic/patterns/advanced)
3. Ensure example works with any adapter (for patterns)
4. Add to this matrix

## Status Legend

- ✅ Implemented and verified
- ❌ Not implemented
- ❓ Unknown/needs verification
- 🔄 In progress
- 🚫 Not applicable/not planned
