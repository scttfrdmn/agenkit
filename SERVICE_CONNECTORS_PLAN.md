# Service Connectors & Framework Examples - Implementation Plan

**Created**: January 15, 2026
**Target Release**: v0.50.0 or later
**Priority**: 🟡 Medium (Expansion, not blocking v1.0)
**Estimated Effort**: 18-24 days total (12-16 days connectors, 6-8 days framework examples)

---

## Executive Summary

This plan addresses two expansion areas for Agenkit:

1. **Service Connectors**: Adapters for 12+ LLM inference services (vLLM, SGLang, TensorRT-LLM, etc.)
2. **Framework Examples**: Reference implementations showing how to build framework-equivalent agents using Agenkit

**Key Insight**: 9 out of 12 requested services offer OpenAI-compatible APIs, suggesting a single well-designed adapter with provider-specific configurations can cover most use cases.

---

## Part 1: Service Connectors

### Current State

**Existing Adapters** (6 total across all languages):
- ✅ Anthropic (Claude)
- ✅ OpenAI (GPT-4, GPT-3.5)
- ✅ Ollama (local models)
- ✅ LiteLLM (100+ providers via proxy)
- ✅ Gemini (Google)
- ✅ Bedrock (AWS)

**Directory Structure**:
- **Python**: `agenkit/adapters/llm/` (7 files)
- **Go**: `agenkit-go/adapter/llm/`
- **TypeScript**: `agenkit-ts/src/adapters/` (no llm subdirectory)
- **Rust**: `agenkit-rust/src/adapters/` (no llm subdirectory)
- **C++**: `agenkit-cpp/src/adapters/` (using `*_agent.cpp` naming)
- **Zig**: `agenkit-zig/src/adapters/` (examples only)

---

### Requested Services - Research Summary

Based on comprehensive research (January 2026), here are the 12 requested inference services:

#### Category 1: Production OpenAI-Compatible Servers (HIGH PRIORITY)

**1. vLLM**
- **API**: HTTP REST (OpenAI-compatible)
- **Adoption**: ⭐⭐⭐⭐⭐ Industry Standard - "The safest bet"
- **Use Case**: High-throughput production serving
- **Key Feature**: PagedAttention, 24x higher throughput than TGI
- **Priority**: **HIGHEST** - Most widely adopted

**2. SGLang**
- **API**: HTTP REST (OpenAI-compatible)
- **Adoption**: ⭐⭐⭐⭐ Rising Star
- **Use Case**: Multi-turn conversations with repeated prefixes
- **Key Feature**: RadixAttention for KV cache reuse, 29-64% faster than vLLM
- **Priority**: **HIGH** - Performance leader for specific workloads

**3. llama.cpp**
- **API**: HTTP REST (OpenAI-compatible via llama-server)
- **Adoption**: ⭐⭐⭐⭐⭐ Universal Workhorse
- **Use Case**: Local/edge deployment, CPU inference, Apple Silicon
- **Key Feature**: Cross-platform, 10x developer growth in AI PC trend
- **Priority**: **HIGHEST** - Already mentioned in docs as "similar to Ollama"

**4. TensorRT-LLM**
- **API**: HTTP REST (OpenAI-compatible), Python, C++
- **Adoption**: ⭐⭐⭐⭐ Enterprise Standard
- **Use Case**: NVIDIA enterprise GPUs, automotive/robotics edge
- **Key Feature**: Optimized for A100/H100, used by Microsoft Bing
- **Priority**: **HIGH** - Enterprise production standard

#### Category 2: Platform Orchestration (MEDIUM PRIORITY)

**5. OpenLLM**
- **API**: HTTP REST (OpenAI-compatible)
- **Adoption**: ⭐⭐⭐ Production Ready
- **Use Case**: Full-featured deployment with BentoML orchestration
- **Key Feature**: Uses vLLM engine + orchestration, 4-5x faster than Ollama
- **Priority**: **MEDIUM** - Wraps vLLM, adds deployment features
- **Note**: Supporting vLLM covers most use cases

**6. MLC LLM**
- **API**: HTTP REST (OpenAI-compatible), Python, JS, iOS, Android
- **Adoption**: ⭐⭐⭐ Cross-Platform Specialist
- **Use Case**: Universal deployment including browser (WebLLM), mobile
- **Key Feature**: Apache TVM compiler, WebGPU for in-browser inference
- **Priority**: **MEDIUM** - Unique for non-standard targets

#### Category 3: Maintenance Mode or Limited Adoption (DEFER)

**7. TGI (Text Generation Inference)**
- **API**: HTTP REST (OpenAI-compatible)
- **Adoption**: ⭐⭐⭐ Legacy Production
- **Status**: ⚠️ **MAINTENANCE MODE** since Dec 11, 2025
- **Note**: HuggingFace recommends vLLM or SGLang for new deployments
- **Priority**: **DEFER** - Explicitly deprecated

**8. LMDeploy**
- **API**: HTTP REST, Python library
- **Adoption**: ⭐⭐⭐ Performance Enthusiast (Chinese AI community)
- **Use Case**: Extreme performance optimization (1.8x vs vLLM)
- **Priority**: **DEFER** - Limited adoption outside China

**9. Mistral.rs**
- **API**: HTTP REST (OpenAI-compatible), Rust library
- **Adoption**: ⭐⭐ Emerging
- **Use Case**: Rust ecosystem integration, multimodal
- **Priority**: **DEFER** - Early stage, limited adoption

**10. PowerInfer**
- **API**: HTTP REST (llama.cpp compatible)
- **Adoption**: ⭐⭐ Research Project
- **Use Case**: Consumer hardware, smartphones (sparse inference)
- **Priority**: **DEFER** - Research project, not production-ready

**11. Inferflow**
- **API**: HTTP REST (OpenAI-compatible)
- **Adoption**: ⭐⭐ Emerging
- **Use Case**: Multi-GPU distributed inference
- **Priority**: **DEFER** - Very new, unclear adoption

#### Category 4: Library-Only (LOW PRIORITY)

**12. DeepSpeed**
- **API**: Python library only (init_inference API)
- **Adoption**: ⭐⭐⭐⭐ Research & Custom Deployments
- **Note**: Not a standalone server - requires custom integration
- **Priority**: **LOW** - Library, not a service. Document integration pattern instead

---

### Proposed Implementation Strategy

#### Option A: Generic OpenAI-Compatible Adapter (RECOMMENDED)

**Rationale**: 9 out of 12 services offer OpenAI-compatible APIs. Single adapter with provider-specific configurations covers 80% of use cases.

**Implementation**:

```python
# agenkit/adapters/llm/openai_compatible.py

from typing import Any, Literal
from agenkit.adapters.llm.base import LLM
from agenkit.interfaces import Message

Provider = Literal[
    "vllm",
    "sglang",
    "llama_cpp",
    "tensorrt_llm",
    "openllm",
    "mlc_llm",
    "tgi",
    "inferflow"
]

class OpenAICompatibleLLM(LLM):
    """
    Generic adapter for OpenAI-compatible inference services.

    Supports:
    - vLLM (production high-throughput)
    - SGLang (multi-turn conversations)
    - llama.cpp (local/edge/CPU)
    - TensorRT-LLM (NVIDIA enterprise)
    - OpenLLM (BentoML orchestration)
    - MLC LLM (cross-platform/browser)
    - TGI (legacy HuggingFace)
    - Inferflow (distributed)

    Example:
        >>> # vLLM server
        >>> llm = OpenAICompatibleLLM(
        ...     provider="vllm",
        ...     base_url="http://localhost:8000/v1",
        ...     model="mistralai/Mistral-7B-v0.1"
        ... )

        >>> # llama.cpp server
        >>> llm = OpenAICompatibleLLM(
        ...     provider="llama_cpp",
        ...     base_url="http://localhost:8080/v1",
        ...     model="llama-2-7b-chat.Q4_K_M.gguf"
        ... )

        >>> # SGLang with RadixAttention
        >>> llm = OpenAICompatibleLLM(
        ...     provider="sglang",
        ...     base_url="http://localhost:30000/v1",
        ...     provider_config={"enable_radix_attention": True}
        ... )
    """

    def __init__(
        self,
        provider: Provider,
        base_url: str,
        model: str,
        api_key: str | None = None,
        provider_config: dict[str, Any] | None = None,
        **kwargs: Any
    ):
        self._provider = provider
        self._base_url = base_url
        self._model = model
        self._api_key = api_key
        self._provider_config = provider_config or {}

        # Use OpenAI client for HTTP communication
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key or "not-needed",
            **kwargs
        )

    async def complete(self, messages: list[Message], **kwargs: Any) -> Message:
        """Generate completion using OpenAI-compatible API."""
        # Convert Agenkit messages to OpenAI format
        openai_messages = self._convert_messages(messages)

        # Merge provider-specific config
        params = {**self._provider_config, **kwargs}

        # Call OpenAI-compatible endpoint
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            **params
        )

        # Convert response to Agenkit Message
        return self._convert_response(response)
```

**Advantages**:
- ✅ Single implementation covers 9 services
- ✅ Minimal maintenance burden
- ✅ Users can easily switch providers
- ✅ Clear upgrade path as new services emerge

**Implementation Effort**:
- **Python**: 3-4 days (adapter + tests + examples for 4 priority services)
- **Go**: 2-3 days (port from Python)
- **TypeScript**: 2-3 days
- **Rust**: 2-3 days
- **C++**: 2-3 days
- **Zig**: 2-3 days
- **Total**: 13-19 days across all 6 languages

---

#### Option B: Individual Adapters (NOT RECOMMENDED)

**Implementation**: Separate adapter for each service (`VllmLLM`, `SGLangLLM`, `LlamaCppLLM`, etc.)

**Disadvantages**:
- ❌ 12x implementation effort (12 services × 6 languages = 72 adapters!)
- ❌ High maintenance burden
- ❌ Code duplication (all implement OpenAI protocol)
- ❌ Unclear benefit over generic adapter

**Verdict**: Not recommended given OpenAI API compatibility.

---

### Recommended Implementation Plan

#### Phase 1: High-Priority Services (v0.50.0)

**Scope**: 4 services covering 80% of production use cases

1. **vLLM** - Production high-throughput (Industry standard)
2. **llama.cpp** - Local/edge/CPU inference (10x growth trend)
3. **SGLang** - Multi-turn conversations (Performance leader)
4. **TensorRT-LLM** - NVIDIA enterprise (Enterprise standard)

**Implementation**:
- Create `OpenAICompatibleLLM` adapter in Python
- Add provider-specific configuration profiles
- Implement in all 6 languages
- Create 4 examples (one per service)
- Document setup and deployment

**Effort**: 13-16 days

**Files to Create**:
```
agenkit/adapters/llm/openai_compatible.py          (main adapter)
tests/adapters/llm/test_openai_compatible.py       (tests)
examples/adapters/vllm-basic.py                    (vLLM example)
examples/adapters/llamacpp-basic.py                (llama.cpp example)
examples/adapters/sglang-basic.py                  (SGLang example)
examples/adapters/tensorrt-basic.py                (TensorRT-LLM example)
docs/adapters/INFERENCE_SERVICES.md                (setup guide)

# Repeat for all 6 languages
agenkit-go/adapter/llm/openai_compatible.go
agenkit-ts/src/adapters/openai_compatible.ts
agenkit-rust/src/adapters/openai_compatible.rs
agenkit-cpp/src/adapters/openai_compatible_agent.cpp
agenkit-zig/src/adapters/openai_compatible.zig
```

---

#### Phase 2: Platform Orchestration (v0.51.0+)

**Scope**: 2 services with unique features

5. **OpenLLM** - BentoML orchestration (wraps vLLM)
6. **MLC LLM** - Browser/mobile deployment (unique target)

**Implementation**:
- Already covered by Phase 1 adapter (both are OpenAI-compatible)
- Add provider-specific examples
- Document BentoML deployment patterns
- Document WebLLM browser integration

**Effort**: 2-3 days (examples + documentation only)

---

#### Phase 3: Deferred/Monitor Adoption

**Defer indefinitely** (revisit if adoption grows):
- ❌ TGI (maintenance mode - deprecated)
- ❌ LMDeploy (limited adoption outside China)
- ❌ Mistral.rs (early stage)
- ❌ PowerInfer (research project)
- ❌ Inferflow (too new)

**DeepSpeed**: Create integration example showing how to use DeepSpeed library with custom serving layer (not an adapter).

---

### Directory Structure Proposal

**Python** (existing structure works well):
```
agenkit/adapters/llm/
├── __init__.py
├── base.py                    # LLM interface
├── anthropic.py               # Existing
├── openai.py                  # Existing
├── ollama.py                  # Existing (local models)
├── litellm.py                 # Existing (100+ providers)
├── gemini.py                  # Existing
├── bedrock.py                 # Existing
└── openai_compatible.py       # NEW - Generic adapter for inference services
```

**Go/TypeScript/Rust/C++/Zig**: Follow Python structure (some already flatten into `adapters/`)

**Rationale**: Keep flat structure, add single generic adapter.

---

### Testing Strategy

**Unit Tests**:
- Test provider configuration parsing
- Test OpenAI message conversion
- Mock HTTP responses

**Integration Tests** (require running services):
- vLLM: `docker run vllm/vllm-openai --model mistralai/Mistral-7B-v0.1`
- llama.cpp: `./llama-server -m model.gguf`
- SGLang: `docker run sglang/sglang-runtime --model-path meta-llama/Llama-2-7b-chat-hf`
- TensorRT-LLM: NVIDIA Docker runtime required

**Mark integration tests as skipped in CI** (like current Anthropic/OpenAI tests).

---

### Documentation Requirements

**1. Setup Guide**: `docs/adapters/INFERENCE_SERVICES.md`
```markdown
# LLM Inference Services with Agenkit

## Overview
Agenkit supports 9+ OpenAI-compatible inference services through a single unified adapter...

## Quick Start

### vLLM (Production High-Throughput)
```bash
# Install vLLM
pip install vllm

# Start server
vllm serve mistralai/Mistral-7B-v0.1

# Use with Agenkit
from agenkit.adapters.llm import OpenAICompatibleLLM
llm = OpenAICompatibleLLM(provider="vllm", base_url="http://localhost:8000/v1", model="mistralai/Mistral-7B-v0.1")
```

### llama.cpp (Local/Edge/CPU)
...

## Provider Comparison Table
| Provider | Best For | GPU Required | CPU Support | Memory | Setup |
|----------|----------|--------------|-------------|--------|-------|
| vLLM | Production serving | Yes (NVIDIA) | No | High | Easy |
| llama.cpp | Local/Edge | Optional | ✅ Yes | Low | Easy |
| SGLang | Multi-turn chat | Yes (NVIDIA) | No | High | Medium |
| TensorRT-LLM | Enterprise NVIDIA | Yes (A100/H100) | No | High | Hard |
```

**2. Migration Guide**: Add section to `docs/migrations/*-to-agenkit.md`

**3. API Reference**: Auto-generated from docstrings

---

### Success Criteria

**Phase 1 (v0.50.0)**:
- [ ] `OpenAICompatibleLLM` adapter implemented in all 6 languages
- [ ] Tests pass (50+ tests total across languages)
- [ ] 4 examples demonstrating each priority service
- [ ] Documentation complete with setup guide
- [ ] Integration tests for all 4 services (CI skip, manual verification)

**Phase 2 (v0.51.0+)**:
- [ ] OpenLLM and MLC LLM examples added
- [ ] BentoML deployment documented
- [ ] WebLLM browser integration documented

---

## Part 2: Framework Examples

### Overview

**Goal**: Create reference implementations showing how to build framework-equivalent agents using Agenkit as a foundational toolkit.

**Key Principle**: Agenkit is a **toolkit**, not a **framework**. These examples demonstrate how other frameworks can be built **ON TOP** of Agenkit.

---

### Existing Migration Guides

Agenkit already has migration guides for 6 frameworks:

1. **LangChain/LangGraph** → Agenkit (`docs/migrations/langchain-to-agenkit.md`)
2. **CrewAI** → Agenkit (`docs/migrations/crewai-to-agenkit.md`)
3. **AutoGen** → Agenkit (`docs/migrations/autogen-to-agenkit.md`)
4. **Haystack** → Agenkit (`docs/migrations/haystack-to-agenkit.md`)
5. **SmolAgents** → Agenkit (`docs/migrations/smolagents-to-agenkit.md`)
6. **Strands** → Agenkit (`docs/migrations/strands-to-agenkit.md`)

These guides show:
- Pattern mapping (LangChain Chain → Agenkit SequentialAgent)
- Side-by-side code examples
- Feature comparison tables
- Migration strategies

**What's Missing**: Working code examples that fully re-implement these frameworks.

---

### Proposed Framework Examples

#### Example 1: MiniChain - LangChain Equivalent

**File**: `examples/frameworks/minichain.py`

**Goal**: Build a minimal LangChain-equivalent using Agenkit primitives.

**Components to Re-implement**:
1. **Chain Interface**: Sequential execution of agents
2. **LLMChain**: Agent + prompt template
3. **ConversationChain**: Conversational agent with memory
4. **RouterChain**: Router pattern for conditional routing
5. **SequentialChain**: Multi-step sequential agent
6. **SimpleMemory**: Basic conversation history
7. **LCEL-style composition**: Pythonic composition operators

**Code Structure**:
```python
# examples/frameworks/minichain.py

from agenkit import Agent, Message, SequentialAgent, RouterAgent, ConversationalAgent
from agenkit.adapters.llm import OpenAILLM
from typing import Protocol, Callable

class Chain(Protocol):
    """Base interface for chains (mirrors LangChain)."""
    def run(self, input: str) -> str: ...

class LLMChain:
    """Simple LLM chain with prompt template."""
    def __init__(self, llm: Agent, prompt: str):
        self.llm = llm
        self.prompt = prompt

    def run(self, **kwargs: Any) -> str:
        prompt_text = self.prompt.format(**kwargs)
        message = Message(role="user", content=prompt_text)
        response = await self.llm.process(message)
        return response.content

class ConversationChain:
    """Conversational chain with memory."""
    def __init__(self, llm: Agent):
        self.agent = ConversationalAgent(llm=llm)

    def run(self, input: str) -> str:
        return await self.agent.process(Message(role="user", content=input))

# Example usage showing LangChain-style API
llm = OpenAILLM(model="gpt-4")

# Simple chain
chain = LLMChain(llm=llm, prompt="Translate to French: {text}")
result = chain.run(text="Hello, world!")
print(result)  # "Bonjour, monde!"

# Conversational chain
conv_chain = ConversationChain(llm=llm)
conv_chain.run("Hi, I'm Alice")
conv_chain.run("What's my name?")  # Remembers: "Your name is Alice"

# Sequential chain (multi-step)
translate_chain = LLMChain(llm=llm, prompt="Translate to French: {text}")
summary_chain = LLMChain(llm=llm, prompt="Summarize in 5 words: {text}")
sequential = SequentialChain(chains=[translate_chain, summary_chain])
result = sequential.run(text="The quick brown fox jumps over the lazy dog")

# Router chain
router = RouterChain(
    routes={
        "math": math_chain,
        "creative": creative_chain,
        "code": code_chain
    },
    classifier=classify_intent
)
```

**Demonstrates**:
- How LangChain's abstractions map to Agenkit
- Pattern composition
- Memory management
- Routing logic

**Effort**: 2-3 days (implementation + examples + docs)

---

#### Example 2: MiniCrew - CrewAI Equivalent

**File**: `examples/frameworks/minicrew.py`

**Goal**: Build a minimal CrewAI-equivalent showing role-based multi-agent collaboration.

**Components to Re-implement**:
1. **Role/Agent**: Agent with role, goal, backstory
2. **Task**: Discrete unit of work with description and agent assignment
3. **Crew**: Collection of agents working together
4. **Process**: Sequential vs parallel task execution
5. **Memory**: Shared crew memory

**Code Structure**:
```python
# examples/frameworks/minicrew.py

from dataclasses import dataclass
from agenkit import Agent, Message, SequentialAgent, ParallelAgent

@dataclass
class Task:
    """A task to be performed by an agent."""
    description: str
    agent: Agent
    expected_output: str

class Crew:
    """A crew of agents working together."""
    def __init__(self, agents: list[Agent], tasks: list[Task], process: str = "sequential"):
        self.agents = agents
        self.tasks = tasks
        self.process = process

    async def kickoff(self) -> dict[str, Any]:
        """Execute all tasks according to process type."""
        if self.process == "sequential":
            return await self._run_sequential()
        elif self.process == "parallel":
            return await self._run_parallel()

    async def _run_sequential(self) -> dict[str, Any]:
        """Run tasks sequentially."""
        results = []
        for task in self.tasks:
            message = Message(role="user", content=task.description)
            result = await task.agent.process(message)
            results.append(result)
        return {"results": results}

# Example: Market research crew
researcher = Agent(
    role="Market Researcher",
    goal="Uncover cutting-edge developments in AI",
    backstory="You're a seasoned researcher with a knack for uncovering trends"
)

writer = Agent(
    role="Tech Content Writer",
    goal="Craft compelling content on tech advancements",
    backstory="You're a creative writer with a passion for tech"
)

research_task = Task(
    description="Research latest AI trends in 2026",
    agent=researcher,
    expected_output="Bullet-point report on AI trends"
)

writing_task = Task(
    description="Write a blog post based on research",
    agent=writer,
    expected_output="800-word blog post"
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process="sequential"
)

result = await crew.kickoff()
```

**Demonstrates**:
- Role-based agents
- Task decomposition
- Sequential/parallel execution
- Multi-agent collaboration

**Effort**: 1-2 days

---

#### Example 3: MiniGen - AutoGen Equivalent

**File**: `examples/frameworks/minigen.py`

**Goal**: Build a minimal AutoGen-equivalent showing conversational multi-agent systems.

**Components to Re-implement**:
1. **ConversableAgent**: Agent that can have conversations
2. **AssistantAgent**: Agent with LLM
3. **UserProxyAgent**: Human-in-the-loop agent
4. **GroupChat**: Multi-agent conversation
5. **GroupChatManager**: Manages speaker selection

**Code Structure**:
```python
# examples/frameworks/minigen.py

from agenkit import Agent, Message
from agenkit.patterns.multi_agent import GroupConversation

class ConversableAgent:
    """Agent that can participate in conversations."""
    def __init__(self, name: str, system_message: str):
        self.name = name
        self.system_message = system_message

    async def send(self, message: str, recipient: "ConversableAgent") -> str:
        """Send a message to another agent."""
        return await recipient.receive(message, self)

    async def receive(self, message: str, sender: "ConversableAgent") -> str:
        """Receive a message from another agent."""
        # Override in subclasses
        pass

class AssistantAgent(ConversableAgent):
    """Agent powered by LLM."""
    def __init__(self, name: str, llm: Agent):
        super().__init__(name, system_message="You are a helpful assistant")
        self.llm = llm

class GroupChat:
    """Multi-agent conversation."""
    def __init__(self, agents: list[ConversableAgent], max_rounds: int = 10):
        self.agents = agents
        self.max_rounds = max_rounds

# Example: Code review conversation
coder = AssistantAgent(name="Coder", llm=OpenAILLM())
reviewer = AssistantAgent(name="Reviewer", llm=OpenAILLM())
tester = AssistantAgent(name="Tester", llm=OpenAILLM())

group_chat = GroupChat(agents=[coder, reviewer, tester], max_rounds=10)
manager = GroupChatManager(group_chat)

await coder.send("Write a function to calculate Fibonacci", recipient=reviewer)
```

**Demonstrates**:
- Conversational agents
- Multi-agent dialogue
- Speaker selection
- Human-in-the-loop patterns

**Effort**: 1-2 days

---

### Proposed Directory Structure

```
examples/frameworks/
├── README.md                  # Overview of framework examples
├── minichain.py               # LangChain equivalent (350-400 LOC)
├── minicrew.py                # CrewAI equivalent (250-300 LOC)
├── minigen.py                 # AutoGen equivalent (300-350 LOC)
├── minihaystack.py            # Haystack equivalent (300-350 LOC)
└── __init__.py
```

**Total Estimated LOC**: 1,200-1,400 lines across 4 framework examples

---

### Implementation Priority

**Phase 1 (v0.50.0)**: High-value examples
1. **MiniChain** (LangChain) - Most popular framework
2. **MiniCrew** (CrewAI) - Popular for multi-agent

**Phase 2 (v0.51.0)**: Additional examples
3. **MiniGen** (AutoGen) - Popular for research
4. **MiniHaystack** (Haystack) - RAG focus

**Deferred**: SmolAgents, Strands (less popular)

---

### Testing Strategy

**Unit Tests**: Not required - these are examples, not production code

**Documentation**: Each example should have:
1. Header comment explaining framework mapping
2. Inline comments showing equivalent framework code
3. Usage examples at bottom
4. Link to full migration guide

---

### Documentation Requirements

**1. Framework Examples README**: `examples/frameworks/README.md`
```markdown
# Framework Examples - Building on Agenkit

## Overview
These examples demonstrate how popular agent frameworks can be built using Agenkit as a foundational toolkit. Each example re-implements core framework patterns to show Agenkit's flexibility and composability.

**Remember**: Agenkit is a toolkit, not a framework. These examples show how frameworks are built ON TOP of Agenkit's primitives.

## Available Examples
1. **MiniChain** - LangChain/LangGraph equivalent
2. **MiniCrew** - CrewAI equivalent
3. **MiniGen** - AutoGen equivalent
4. **MiniHaystack** - Haystack equivalent

## Why Build Your Own?
- Full control over abstractions
- No hidden magic or implicit state
- Customize to your exact needs
- Learn framework internals
- Production-grade primitives

## See Also
- Migration Guides: `docs/migrations/`
- Pattern Documentation: `docs/PATTERNS.md`
```

**2. Update Migration Guides**: Add section linking to framework examples
```markdown
## Working Framework Example

See `examples/frameworks/minichain.py` for a complete working implementation of LangChain patterns using Agenkit.
```

---

### Success Criteria

**Phase 1 (v0.50.0)**:
- [ ] MiniChain example complete (LangChain equivalent)
- [ ] MiniCrew example complete (CrewAI equivalent)
- [ ] README with overview and usage
- [ ] Examples demonstrate key patterns from migration guides
- [ ] Links added to migration guide docs

**Phase 2 (v0.51.0)**:
- [ ] MiniGen example complete (AutoGen equivalent)
- [ ] MiniHaystack example complete (Haystack equivalent)
- [ ] All 4 framework examples tested and verified

---

## Combined Implementation Timeline

### Month 1 (Weeks 1-3): Service Connectors

**Week 1**: Design + Python Implementation
- Design OpenAICompatibleLLM adapter API
- Implement Python adapter
- Write tests
- Create 4 examples (vLLM, llama.cpp, SGLang, TensorRT-LLM)

**Week 2**: Multi-Language Implementation (Part 1)
- Port to Go
- Port to TypeScript
- Port to Rust

**Week 3**: Multi-Language Implementation (Part 2)
- Port to C++
- Port to Zig
- Write documentation (INFERENCE_SERVICES.md)

### Month 2 (Week 4): Framework Examples

**Week 4**: Framework Examples
- Day 1-2: MiniChain (LangChain equivalent)
- Day 3-4: MiniCrew (CrewAI equivalent)
- Day 5: README and documentation
- Test all examples

**Total Timeline**: 4 weeks (18-24 days of focused work)

---

## Dependencies & Risks

### Dependencies
- OpenAI Python SDK (already used by OpenAILLM adapter)
- Docker for integration testing
- Access to test models for each service

### Risks

**Risk 1**: API Changes in Inference Services
- **Mitigation**: OpenAI-compatible API is stable standard
- **Fallback**: Version-pin examples, document compatibility

**Risk 2**: Integration Test Complexity
- **Mitigation**: Mark as CI skip, manual verification only
- **Fallback**: Mock tests for CI, real tests for manual QA

**Risk 3**: Framework Examples Outdated
- **Mitigation**: Link to migration guides (authoritative)
- **Fallback**: Examples show patterns, not exact API parity

---

## Success Metrics

### Service Connectors
- [ ] 1 generic adapter supports 9 services (DRY principle)
- [ ] Implemented across all 6 languages (feature parity)
- [ ] 4 priority examples demonstrate production use
- [ ] Documentation explains setup for each service
- [ ] Integration tests exist (CI skip, manual verification)

### Framework Examples
- [ ] 4 framework equivalents implemented
- [ ] Each example <400 LOC (concise, readable)
- [ ] Examples link to full migration guides
- [ ] README explains "toolkit not framework" philosophy
- [ ] Examples tested and verified working

---

## Post-Implementation (v0.51.0+)

**Monitor Adoption**:
- Track which inference services users request
- Add examples for OpenLLM, MLC LLM if demand exists
- Revisit deferred services (Mistral.rs, Inferflow) if adoption grows

**Framework Examples Expansion**:
- Add SmolAgents, Strands examples if requested
- Add language ports (Go, TypeScript) if useful
- Consider standalone framework packages built on Agenkit

---

**Last Updated**: January 15, 2026
**Next Action**: Review with maintainer, prioritize for v0.50.0 milestone
**Estimated Effort**: 18-24 days (3-4 weeks of focused engineering work)
