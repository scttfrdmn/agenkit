# Framework Compatibility Tests

Validates that MiniChain and MiniCrew API compatibility with LangChain/CrewAI patterns (Issue #478).

## Test Coverage

### MiniChain (`test_minichain_compatibility.py`) — 24 tests

| Group | Tests | What's Validated |
|-------|-------|-----------------|
| `LLMChain` | 6 | Instantiation, template substitution, call count, multi-var templates, return type, response passthrough |
| `ConversationChain` | 6 | Instantiation, return type, history growth, clear, system prompt, max_history cap |
| `SequentialChain` | 4 | Instantiation, chaining, single agent, output passthrough |
| `RouterChain` | 4 | Instantiation, correct routing, default route, dynamic routing |
| `SimpleMemory` | 4 | Add/get messages, max enforcement, clear, `__len__` |

### MiniCrew (`test_minicrew_compatibility.py`) — 16 tests

| Group | Tests | What's Validated |
|-------|-------|-----------------|
| `CrewTask` | 3 | Creation, default `expected_output`, context list |
| `CrewAgent` | 4 | Instantiation, `name` property, `capabilities` derivation, system prompt construction |
| `Crew.sequential` | 4 | Basic kickoff, `tasks_completed` count, results structure, context passing |
| `Crew.parallel` + errors | 5 | Parallel results, combined output, `ValueError` on invalid process, empty tasks (both modes) |

## Running

```bash
# Compatibility tests only
uv run pytest tests/frameworks/ -v

# With test marker
uv run pytest -m frameworks -v

# Full suite (included automatically)
make test
```

## Compatibility Matrix

| LangChain API | MiniChain Equivalent | Agenkit Primitive |
|---------------|---------------------|------------------|
| `LLMChain` | `LLMChain` | `LLM.complete()` + prompt template |
| `ConversationChain` | `ConversationChain` | `ConversationalAgent` |
| `SequentialChain` | `SequentialChain` | `SequentialAgent` |
| `MultiPromptChain` | `RouterChain` | `RouterAgent` |
| `ChatMessageHistory` | `SimpleMemory` | `ConversationalAgent.history` |

| CrewAI API | MiniCrew Equivalent | Agenkit Primitive |
|------------|--------------------|--------------------|
| `Agent` | `CrewAgent` | `Agent` with role metadata |
| `Task` | `CrewTask` | Task dataclass with agent assignment |
| `Crew(sequential)` | `Crew(process="sequential")` | `SequentialAgent` pattern |
| `Crew(parallel)` | `Crew(process="parallel")` | `asyncio.gather()` |
