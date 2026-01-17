# RLM Pattern Analysis

## Does This Expose Missing Agenkit Functionality?

After implementing the RLM experimental example, here's what I found:

### What RLM Needs That Agenkit Has

✅ **Code Execution** - `ReasoningWithToolsAgent` provides tool/code execution
✅ **Recursive Calls** - `AgentTool` provides hierarchical agent delegation
✅ **Iterative Loops** - `ReActAgent` provides observe→act→reason cycles
✅ **External State** - `MemoryHierarchy` manages context outside prompts

### What RLM Needs That Agenkit Might Be Missing

#### 1. 🟡 **Sandboxed Code Execution Environment**

**Current State**: RLM uses Python's `exec()` with namespace isolation:
```python
exec(code, {"__builtins__": __builtins__}, repl_namespace)
```

**Gap**: No first-class sandboxed execution infrastructure in Agenkit.

**Options**:
- **Low priority** - Python's `exec()` with namespace works fine for trusted contexts
- **If needed**: Could add `agenkit.sandbox` module with:
  - RestrictedPython for enhanced safety
  - Docker/container-based execution
  - Resource limits (CPU, memory, time)
  - Whitelist of allowed imports/operations

**Recommendation**: Not critical for v1. Document security considerations in experimental README. Add if production use cases emerge.

---

#### 2. 🟡 **Context-as-Environment Pattern**

**Current State**: Agenkit agents typically receive context in prompts.

**RLM Innovation**: Treats context as external variable, references it programmatically.

**Gap**: No explicit support for "context offloading" - where large context lives outside the prompt and is accessed programmatically.

**Potential Pattern**:
```python
class EnvironmentContextAgent:
    """
    Agent that processes context as environment variable,
    not as direct prompt input.

    Useful when:
    - Context exceeds model limits
    - Want programmatic filtering before LLM sees text
    - Need to process context in chunks iteratively
    """

    def __init__(self, agent: Agent, environment: dict[str, Any]):
        self.agent = agent
        self.environment = environment  # Context lives here, not in prompt

    async def process(self, message: Message) -> Message:
        # Agent references context via environment, not prompt
        pass
```

**Recommendation**: Watch for this pattern in other use cases. If it emerges beyond RLM (e.g., large codebase processing, database query results, file system navigation), consider elevating to `agenkit/patterns/environment_context.py`.

---

#### 3. 🟢 **Code-Generation Agent Specialization**

**Current State**: ReActAgent and ReasoningWithToolsAgent execute code but don't specialize in generating it.

**RLM Observation**: Success depends heavily on LLM's ability to generate good code (chunking strategies, filtering logic, aggregation).

**Gap**: No explicit "code generation agent" pattern.

**Potential Pattern**:
```python
class CodeGenerationAgent:
    """
    Agent specialized for generating code to solve problems.

    Different from ReasoningWithTools:
    - Optimized prompts for code generation
    - Language-specific best practices
    - Iterative refinement of code
    - Test generation and validation
    """

    def __init__(self, agent: Agent, language: str = "python"):
        self.agent = agent
        self.language = language

    async def generate_code(self, task: str, context: str) -> str:
        # Generate code with iterations and refinement
        pass
```

**Recommendation**: **This might be worth adding** as a reusable pattern. Many agent systems need code generation (not just execution). Could live in `agenkit/patterns/code_generation.py`.

---

#### 4. ✅ **Cost Tracking & Budget Management** (Already Exists!)

**Current State**: **Agenkit has comprehensive budget infrastructure** in `agenkit/budget/`:
- `CostTracker` - Track costs per session/agent/globally
- `BudgetLimiter` - Middleware enforcing cost limits
- `ModelOptimizer` - Intelligent model routing
- `ModelPricing` - Pricing for OpenAI, Anthropic, Google

**RLM Challenge**: High cost variance - some trajectories make 1000s of sub-calls.

**Solution**: Integrate RLM with existing budget infrastructure:
```python
from agenkit.budget import CostTracker, BudgetLimiter
from basic_rlm import RecursiveREPLAgent

# Track costs
tracker = CostTracker()

# Enforce budget for RLM (prevent runaway costs)
limiter = BudgetLimiter(tracker, session_budget=5.00, action="error")
wrapped_agent = limiter(base_agent)

# Use RLM with cost protection
rlm = RecursiveREPLAgent(agent=wrapped_agent, max_iterations=20)
```

**Recommendation**: Update `basic_rlm.py` to demonstrate budget integration in the example. This is essential given RLM's high cost variance (95th percentile 3-10x median).

---

### Summary: What Should Be Added to Agenkit Core?

| Feature | Status | Priority | Location | Justification |
|---------|--------|----------|----------|---------------|
| **Cost tracking & budgeting** | ✅ **EXISTS** | N/A | `agenkit/budget/` (55 tests, all languages) | Already production-ready across Python, Go, Rust, TS, C++, Zig |
| **Code generation pattern** | 🟢 MEDIUM | `agenkit/patterns/code_generation.py` | Reusable across many use cases beyond RLM |
| **Environment context pattern** | 🟡 LOW | `agenkit/patterns/environment_context.py` | Wait for more use cases before adding |
| **Enhanced sandboxing** | 🟡 LOW | `agenkit/sandbox/` | Only if production needs emerge |

---

## Suggestions for Improving This Approach

### 1. **Async-First Implementation**

**Current Issue**: `llm_query()` uses sync wrapper around async function:
```python
def llm_query_sync(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(llm_query(prompt))
```

**Problem**: Blocks event loop, prevents concurrent sub-calls.

**Improvement**:
```python
# Allow async code in REPL using special syntax
# ```async-python
async def process_chunks():
    tasks = [llm_query(chunk) for chunk in chunks]
    return await asyncio.gather(*tasks)

results = await process_chunks()
# ```
```

**Benefit**: 10x speedup for parallel sub-queries (paper noted this as bottleneck).

---

### 2. **Integrate with Existing Agenkit Patterns**

**Current Issue**: RLM is standalone, doesn't compose with Memory/Reflection/etc.

**Improvement**:
```python
class RLMWithMemory:
    """RLM + MemoryHierarchy for context caching."""

    def __init__(self, agent: Agent, memory: MemoryHierarchy):
        self.agent = agent
        self.memory = memory  # Cache processed chunks

    async def process(self, message: Message) -> Message:
        # Check if chunks already processed in long-term memory
        # Only query LLM for new/changed chunks
        pass
```

**Benefit**: Reduces cost for repeated queries over similar contexts.

---

### 3. **Cost Budget Integration**

**Current Issue**: No way to limit runaway costs.

**Improvement**:
```python
from agenkit.infrastructure.budgeting import BudgetLimiter

rlm = RecursiveREPLAgent(
    agent=agent,
    max_iterations=20,
    budget_limiter=BudgetLimiter(max_cost=5.00)  # Stop at $5
)
```

**Benefit**: Production safety, aligns with paper's observation of high cost variance.

---

### 4. **Better Prompt Engineering Utilities**

**Current Issue**: System prompts are static text files.

**Improvement**:
```python
from agenkit.prompts import PromptTemplate

class RLMPromptBuilder:
    """Build model-specific RLM prompts."""

    @staticmethod
    def for_gpt5(context_size: int, task_type: str) -> str:
        # Optimized for GPT-5
        pass

    @staticmethod
    def for_qwen(context_size: int, task_type: str) -> str:
        # Add sub-call warnings for Qwen
        pass

    @staticmethod
    def for_claude(context_size: int, task_type: str) -> str:
        # Optimized for Claude thinking style
        pass
```

**Benefit**: Easier to maintain model-specific optimizations.

---

### 5. **Instrumentation and Observability**

**Current Issue**: Hard to debug why RLM made certain decisions.

**Improvement**:
```python
from agenkit.observability import TracingMiddleware

rlm = RecursiveREPLAgent(agent=agent)
traced_rlm = TracingMiddleware(rlm, span_name="rlm-iteration")

# Now each iteration is traced:
# - Code generated
# - Execution results
# - Sub-calls made
# - Cost per iteration
```

**Benefit**: Essential for understanding and optimizing RLM trajectories.

---

### 6. **Fallback Strategies**

**Current Issue**: If RLM fails (max iterations, budget exceeded), no graceful degradation.

**Improvement**:
```python
from agenkit.patterns import FallbackAgent

rlm_pipeline = FallbackAgent([
    RecursiveREPLAgent(agent=gpt5, budget=5.00),      # Try RLM first
    SummarizationAgent(agent=gpt5_mini, budget=0.50),  # Fall back to summarization
    RAGAgent(agent=gpt5_mini, retriever=bm25),         # Finally try RAG
])
```

**Benefit**: Robustness for production systems.

---

### 7. **Testing Framework**

**Current Issue**: Hard to test without real LLM calls.

**Improvement**:
```python
# agenkit/testing/rlm_fixtures.py
class RLMTestAgent:
    """Deterministic agent for testing RLM mechanics."""

    def __init__(self, script: list[str]):
        self.script = script  # Pre-defined responses

    async def process(self, message: Message) -> Message:
        # Return scripted responses, allows testing without API calls
        pass
```

**Benefit**: Fast, deterministic tests for RLM logic.

---

## Recommended Next Steps

### Immediate (for experimental/)
1. ✅ Add async support for parallel sub-calls
2. ✅ Add cost tracking utilities
3. ✅ Create integration examples with Memory/Reflection patterns
4. ✅ Document security considerations for code execution

### If Promoting to Core (after validation)
1. Extract `BudgetLimiter` to `agenkit/infrastructure/`
2. Add `CodeGenerationAgent` to `agenkit/patterns/`
3. Create `PromptTemplate` utilities for model-specific prompts
4. Integrate with existing observability (TracingMiddleware)

### Long-term Research
1. Train models specifically for RLM pattern (STaR-style bootstrapping)
2. Develop automatic cost-aware chunking strategies
3. Create RLM-specific evaluation benchmarks
4. Study composition with other patterns (RLM + Reflection, RLM + Planning)

---

**Bottom Line**: RLM validation confirms that **cost management is critical** for production agents. Fortunately, Agenkit already has comprehensive budget infrastructure (`agenkit/budget/` with 55 tests). The experimental RLM implementation should be updated to demonstrate integration with existing cost tracking for production safety.
