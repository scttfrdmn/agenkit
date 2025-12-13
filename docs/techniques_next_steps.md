# Techniques Library - Next Steps and Implementation Recommendations

**Created**: 2025-12-09
**Updated**: 2025-12-09 (Added enhancements from Rothman/Albada books)
**Status**: Ready for Implementation
**Related Milestone**: #38 "Techniques Library"
**Related Issues**: #231-240

---

## 🎯 What We Just Created

### Milestone #38: Techniques Library
- **Due**: June 30, 2026
- **10 issues total**: 6 reasoning + 2 protocols + 1 compositions (updated) + 1 documentation
- **Estimated effort**: 20 weeks, ~4,800 LOC
- **Target versions**: v0.41.0 - v0.43.0

### Issues Breakdown

#### Phase 1: Reasoning Techniques (v0.41.0) - 8 weeks
- **#231**: Chain-of-Thought (CoT) - ~150 LOC, 1 week
- **#232**: Tree-of-Thought (ToT) - ~300 LOC, 2 weeks
- **#233**: Self-Consistency - ~200 LOC, 1 week
- **#234**: Graph-of-Thought (GoT) - ~350 LOC, 2 weeks
- **#235**: Least-to-Most Prompting - ~200 LOC, 1 week
- **#236**: Plan-and-Solve - ~200 LOC, 1 week

#### Phase 2: Protocol Implementations (v0.42.0) - 6 weeks
- **#237**: Model Context Protocol (MCP) - ~1,100 LOC, 3 weeks
- **#238**: Agent-to-Agent (A2A) Protocol - ~1,350 LOC, 3 weeks

#### Phase 3: Compositions (v0.43.0) - 4 weeks
- **#239**: Composition Techniques and Recipes - ~550 LOC, 4 weeks
  - **UPDATED**: Added 3 new compositions from Rothman/Albada books:
    - RAG with Citations (high-fidelity RAG)
    - Context Optimization (token reduction)
    - Actor-Critic Variation (shows relation to Reflection)

#### Phase 4: Documentation Enhancement - 2 weeks
- **#240**: Testing, Security, Deployment Guides - ~6,000 lines docs, 2 weeks
  - **NEW ISSUE**: Comprehensive infrastructure guides
  - Testing strategies (AI judges, shadow mode)
  - Security patterns (prompt injection defense, PII)
  - Deployment patterns (canary, self-healing)
  - Best practices guide

### Documentation Created
- `/docs/techniques_library_design.md` - Comprehensive 770-line design doc
- `/docs/techniques_library_summary.md` - Implementation tracking
- This file - Next steps and recommendations

---

## 📚 Book Analysis Complete

We've analyzed **4 major books** on agentic systems:

1. ✅ **Gulli (2025)**: "Agentic Design Patterns" - 21 chapters
2. ✅ **Alto (2025)**: "AI Agents in Practice" - Practical focus
3. ✅ **Rothman (2025)**: "Context Engineering for Multi-Agent Systems" - MCP, citations
4. ✅ **Albada (2025)**: "Building Applications with AI Agents" - Testing, deployment

**Result**: Agenkit's plan covers EVERYTHING valuable from all 4 books:
- ✅ All patterns covered (18+ existing patterns)
- ✅ Reasoning techniques planned (#231-236)
- ✅ Protocols planned (#237-238)
- ✅ Compositions enhanced (#239 - now 9 recipes instead of 6)
- ✅ Infrastructure docs planned (#240)

---

## 🆕 What's New (Dec 9 Update)

### Issue #239 Enhanced
Added **3 new composition recipes** from recent books:

1. **RAG with Citations** (~25 lines)
   - Source: Rothman Ch. 7
   - High-fidelity RAG with source attribution
   - Use case: Legal, medical, research applications

2. **Context Optimization** (~30 lines)
   - Source: Rothman Ch. 6
   - Token reduction through summarization
   - Use case: Cost optimization, API limits

3. **Actor-Critic Variation** (~40 lines)
   - Source: Albada
   - Shows how actor-critic relates to Reflection pattern
   - Educational: Demonstrates they're the same thing!

**Total compositions**: 9 (up from 6)
**Total LOC**: ~550 (up from ~360)

### Issue #240 Created
New **documentation enhancement** issue for infrastructure guides:

1. **Testing Strategies Guide** (~2,000 lines)
   - AI judges for evaluation
   - Shadow mode testing
   - Regression testing with traces

2. **Security Patterns Guide** (~1,500 lines)
   - Prompt injection defense
   - Data poisoning safeguards
   - PII handling

3. **Deployment Patterns Guide** (~1,500 lines)
   - Canary deployments
   - Self-healing agents
   - Cost optimization

4. **Best Practices Guide** (~1,000 lines)
   - When to use patterns vs compositions
   - Performance, security, deployment checklists

**Note**: These are NOT agent patterns - they're infrastructure docs showing production best practices.

---

## 🚀 Recommended Implementation Approach

### Option 1: Quick Win Strategy (RECOMMENDED)

**Week 1: Foundation + CoT**
```bash
# 1. Set up infrastructure
mkdir -p agenkit/techniques/{reasoning,protocols,compositions}
mkdir -p agenkit/techniques/protocols/{mcp,a2a}
mkdir -p tests/techniques/{reasoning,protocols,compositions}
mkdir -p examples/techniques/{reasoning,protocols,compositions}

# 2. Create base files
touch agenkit/techniques/__init__.py
touch agenkit/techniques/reasoning/__init__.py
touch agenkit/techniques/protocols/__init__.py
touch agenkit/techniques/compositions/__init__.py

# 3. Implement Chain-of-Thought (Issue #231)
# - Simplest technique
# - Highest immediate value
# - Foundation for others
```

**Why CoT First:**
- ✅ Can implement in 2-3 days
- ✅ Validates architecture decisions
- ✅ Immediate user value (o3, Opus 4 use extended reasoning)
- ✅ Foundation for Self-Consistency, Plan-and-Solve
- ✅ Easy to explain and market

**Outcome**: Working CoT technique users can try immediately

**Weeks 2-8: Complete Phase 1**
Implement remaining 5 reasoning techniques in order:
1. **Self-Consistency** (#233) - Builds on any agent, including CoT
2. **Plan-and-Solve** (#236) - Similar to existing Planning pattern
3. **Least-to-Most** (#235) - Problem decomposition
4. **Tree-of-Thought** (#232) - More complex tree search
5. **Graph-of-Thought** (#234) - Most complex graph reasoning

**Weeks 9-14: Phase 2 (Protocols)**
- MCP implementation
- A2A implementation

**Weeks 15-18: Phase 3 (Compositions)**
- Original 6 compositions
- NEW: 3 enhanced compositions (RAG with citations, context optimization, actor-critic)

**Weeks 19-20: Phase 4 (Documentation)**
- Testing, security, deployment guides
- Best practices

### Option 2: High-Impact Protocol First

**Alternative: Start with MCP (#237)**

**Why MCP First:**
- ✅ High visibility (Anthropic standard)
- ✅ Ecosystem play (Claude Desktop integration)
- ✅ Can attract early adopters/contributors
- ❌ More complex (3 weeks vs 1 week)
- ❌ Depends on external spec stability

**If you choose this**: Implement MCP server/client first, validate with Claude Desktop, then do reasoning techniques.

### Option 3: Easy Win with Compositions

**Alternative: Start with Compositions (#239)**

**Why Compositions First:**
- ✅ Easiest to implement (each is 10-50 lines)
- ✅ Educational value (pattern vs composition)
- ✅ Shows Agenkit's composability
- ✅ NEW: Demonstrates book coverage (4 books referenced)
- ❌ Lower user demand
- ❌ Less marketing value

---

## 📋 Detailed Week 1 Plan (CoT Implementation)

### Day 1-2: Infrastructure + Documentation

**Create directory structure:**
```bash
agenkit/techniques/
├── __init__.py
├── reasoning/
│   ├── __init__.py
│   ├── chain_of_thought.py  # NEW
│   └── README.md
├── protocols/
│   ├── __init__.py
│   ├── mcp/
│   └── a2a/
└── compositions/
    ├── __init__.py
    └── README.md
```

**Write foundational docs:**
- `docs/techniques/REASONING_TECHNIQUES.md` - Overview of all 6 techniques, comparison matrix
- `agenkit/techniques/reasoning/README.md` - Quick reference

### Day 3-4: Implement Chain-of-Thought

**File: `agenkit/techniques/reasoning/chain_of_thought.py`**

```python
"""
Chain-of-Thought (CoT) Reasoning Technique

Encourages step-by-step reasoning through structured prompting.

References:
- Paper: https://arxiv.org/abs/2201.11903
- "Let's think step by step" prompting
"""

from typing import List, Optional, Callable
from agenkit import Agent, Message

class ChainOfThought(Agent):
    """
    Chain-of-Thought reasoning technique.

    Applies structured prompting to encourage step-by-step reasoning,
    optionally parsing and tracking individual reasoning steps.

    Examples:
        Basic usage:
        >>> cot = ChainOfThought(llm=my_llm)
        >>> response = await cot.process(Message(content="What is 15 * 24?"))
        >>> print(response.metadata["reasoning_steps"])

        Custom prompt template:
        >>> cot = ChainOfThought(
        ...     llm=my_llm,
        ...     prompt_template="Solve step by step:\n{query}"
        ... )
    """

    def __init__(
        self,
        llm,  # LLMClient
        prompt_template: str = "Let's think step by step:\n{query}",
        parse_steps: bool = True,
        step_delimiter: str = "\n",
        max_steps: Optional[int] = None
    ):
        """
        Initialize Chain-of-Thought agent.

        Args:
            llm: LLM client for generating responses
            prompt_template: Template with {query} placeholder
            parse_steps: Whether to extract reasoning steps
            step_delimiter: Delimiter for splitting steps (default: newline)
            max_steps: Maximum number of steps to extract (None = unlimited)
        """
        self.name = "chain_of_thought"
        self.llm = llm
        self.prompt_template = prompt_template
        self.parse_steps = parse_steps
        self.step_delimiter = step_delimiter
        self.max_steps = max_steps

    async def process(self, message: Message) -> Message:
        """
        Process message with Chain-of-Thought reasoning.

        Args:
            message: Input message with query

        Returns:
            Message with response and optional reasoning_steps in metadata
        """
        # Apply CoT prompting
        cot_prompt = self.prompt_template.format(query=message.content)
        response = await self.llm.complete(cot_prompt)

        # Parse steps if requested
        if self.parse_steps:
            steps = self._parse_steps(response)
            return Message(
                content=response,
                metadata={
                    "reasoning_steps": steps,
                    "num_steps": len(steps),
                    "technique": "chain_of_thought"
                }
            )

        return Message(
            content=response,
            metadata={"technique": "chain_of_thought"}
        )

    def _parse_steps(self, text: str) -> List[str]:
        """
        Parse reasoning steps from response.

        Supports multiple formats:
        - Numbered steps (1. 2. 3.)
        - Bullet points (- *)
        - Newline-separated thoughts

        Args:
            text: Response text to parse

        Returns:
            List of reasoning steps
        """
        import re

        # Try numbered steps first (1. 2. 3.)
        numbered = re.findall(r'^\d+\.\s*(.+)$', text, re.MULTILINE)
        if numbered and len(numbered) >= 2:
            steps = numbered
        else:
            # Try bullet points (-, *, •)
            bullets = re.findall(r'^[•\-\*]\s*(.+)$', text, re.MULTILINE)
            if bullets and len(bullets) >= 2:
                steps = bullets
            else:
                # Fall back to delimiter-based splitting
                steps = [
                    s.strip()
                    for s in text.split(self.step_delimiter)
                    if s.strip()
                ]

        # Apply max_steps limit
        if self.max_steps:
            steps = steps[:self.max_steps]

        return steps
```

### Day 5: Tests

**File: `tests/techniques/reasoning/test_chain_of_thought.py`**

```python
"""Tests for Chain-of-Thought reasoning technique."""

import pytest
from agenkit import Message
from agenkit.techniques.reasoning import ChainOfThought

class MockLLM:
    """Mock LLM for testing."""
    async def complete(self, prompt: str) -> str:
        if "step by step" in prompt.lower():
            return """1. First, multiply 15 by 20 to get 300
2. Then, multiply 15 by 4 to get 60
3. Add 300 + 60 = 360
Therefore, 15 * 24 = 360"""
        return "Response"

@pytest.mark.asyncio
async def test_cot_basic():
    """Test basic CoT functionality."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm)

    response = await cot.process(Message(content="What is 15 * 24?"))

    assert "360" in response.content
    assert "reasoning_steps" in response.metadata
    assert len(response.metadata["reasoning_steps"]) >= 3

@pytest.mark.asyncio
async def test_cot_custom_template():
    """Test custom prompt template."""
    llm = MockLLM()
    cot = ChainOfThought(
        llm=llm,
        prompt_template="Solve:\n{query}"
    )

    response = await cot.process(Message(content="Question"))
    assert response is not None

@pytest.mark.asyncio
async def test_cot_no_parsing():
    """Test CoT without step parsing."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm, parse_steps=False)

    response = await cot.process(Message(content="Question"))

    assert "reasoning_steps" not in response.metadata
    assert response.metadata["technique"] == "chain_of_thought"

@pytest.mark.asyncio
async def test_cot_max_steps():
    """Test max_steps limiting."""
    llm = MockLLM()
    cot = ChainOfThought(llm=llm, max_steps=2)

    response = await cot.process(Message(content="What is 15 * 24?"))

    assert len(response.metadata["reasoning_steps"]) == 2

# More tests: bullet points, various formats, edge cases
```

### Day 6: Example + Documentation

**File: `examples/techniques/reasoning/cot_example.py`**

```python
"""
Chain-of-Thought Reasoning Example

Demonstrates using CoT for step-by-step reasoning on various tasks.
"""

import asyncio
from agenkit import Message
from agenkit.techniques.reasoning import ChainOfThought
# from your_llm_client import YourLLMClient

async def main():
    # Initialize with your LLM
    llm = YourLLMClient(model="gpt-4")

    cot = ChainOfThought(llm=llm)

    # Example 1: Math reasoning
    print("=== Math Reasoning ===")
    response = await cot.process(
        Message(content="What is 15 * 24?")
    )
    print(f"Answer: {response.content}")
    print(f"Steps: {response.metadata['reasoning_steps']}")

    # Example 2: Logical reasoning
    print("\n=== Logical Reasoning ===")
    response = await cot.process(
        Message(content="If all roses are flowers and some flowers fade quickly, can we conclude that some roses fade quickly?")
    )
    print(f"Answer: {response.content}")
    print(f"Reasoning steps: {len(response.metadata['reasoning_steps'])}")

    # Example 3: Custom prompt template
    print("\n=== Custom Template ===")
    cot_custom = ChainOfThought(
        llm=llm,
        prompt_template="Break this down step by step:\n{query}"
    )
    response = await cot_custom.process(
        Message(content="How do I make a cup of coffee?")
    )
    print(f"Steps: {response.metadata['reasoning_steps']}")

if __name__ == "__main__":
    asyncio.run(main())
```

**Update: `docs/techniques/REASONING_TECHNIQUES.md`**

Add comprehensive guide with:
- Overview of all 6 techniques
- When to use each
- Comparison matrix (CoT vs ToT vs Self-Consistency, etc.)
- Performance considerations
- Examples

---

## 🏗️ Architecture Decisions to Validate

### 1. Base Class vs Standalone

**Option A: Inherit from Agent** (Recommended for CoT)
```python
class ChainOfThought(Agent):
    async def process(self, message: Message) -> Message:
        ...
```
- ✅ Works with all existing patterns/middleware
- ✅ Can be composed (e.g., Sequential([CoT, Reflection]))
- ✅ Consistent with Agenkit philosophy

**Option B: Wrapper/Decorator**
```python
def with_chain_of_thought(agent: Agent, **kwargs) -> Agent:
    return ChainOfThoughtWrapper(agent, **kwargs)
```
- ✅ More flexible
- ❌ Less consistent with patterns

**Decision**: Start with Option A (Agent inheritance), can add Option B later if needed.

### 2. LLM Client Interface

CoT needs to call LLMs. Options:

**Option A: Pass LLM client to constructor**
```python
cot = ChainOfThought(llm=my_llm_client)
```
- ✅ Explicit, testable
- ✅ No global state
- ❌ User must provide LLM

**Option B: Use existing ConversationalAgent**
```python
cot = ChainOfThought(agent=my_conversational_agent)
```
- ✅ Reuses existing LLM integration
- ❌ More complex

**Decision**: Option A for techniques, Option B can be added as convenience.

### 3. Metadata Format

Store reasoning artifacts in message metadata:

```python
{
    "technique": "chain_of_thought",
    "reasoning_steps": ["step 1", "step 2", ...],
    "num_steps": 3,
    "model": "gpt-4",
    "prompt_template": "..."
}
```

Consistent format across all reasoning techniques for observability.

---

## 🧪 Testing Strategy

### Coverage Goals
- **Unit tests**: 90%+ coverage for each technique
- **Integration tests**: Techniques work with patterns
- **Example tests**: All examples run successfully

### Test Categories

1. **Functionality Tests**
   - Basic operation
   - Custom configurations
   - Edge cases (empty input, malformed output)

2. **Integration Tests**
   - Works with Sequential, Parallel, Router
   - Works with middleware (Retry, Circuit Breaker)
   - Metadata preserved through pipeline

3. **Performance Tests**
   - ToT with large branching factors
   - Self-Consistency with many samples
   - Memory usage for long reasoning chains

---

## 📚 Documentation Requirements

### Per-Technique Documentation

Each technique needs:
1. **Docstrings** - Comprehensive API documentation
2. **README** - Quick reference in technique directory
3. **Examples** - At least one working example
4. **Guide entry** - Section in `REASONING_TECHNIQUES.md`

### Overview Documentation

- **`REASONING_TECHNIQUES.md`** - Complete guide
  - What each technique does
  - When to use each
  - Comparison matrix
  - Performance characteristics
  - Best practices

### NEW: Infrastructure Documentation (Issue #240)

- **`TESTING_STRATEGIES.md`** - AI judges, shadow mode, evaluation
- **`SECURITY_PATTERNS.md`** - Prompt injection, PII, safeguards
- **`DEPLOYMENT_PATTERNS.md`** - Canary, self-healing, monitoring
- **`BEST_PRACTICES.md`** - Checklists, decision trees

### API Reference

Generate from docstrings, ensure all public APIs documented.

---

## 🌍 Cross-Language Considerations

Agenkit targets 5 languages at 100% parity. For reasoning techniques:

### Python First Approach (Recommended)
1. Implement in Python
2. Validate with users
3. Port to TypeScript, Go, Rust, C++

**Pros:**
- ✅ Faster iteration
- ✅ Validate design decisions
- ✅ Python has richest LLM ecosystem

**Cons:**
- ❌ Potential Python-specific decisions
- ❌ Delayed parity

### Design Considerations

Ensure techniques are portable:
- Avoid Python-specific libraries where possible
- Use standard async patterns
- Document algorithm clearly for porting

### Parity Timeline

Target 100% parity by:
- **Python**: Immediate (v0.41.0)
- **TypeScript**: +2 months (v0.42.0)
- **Go**: +4 months (v0.43.0)
- **Rust**: +6 months (v0.44.0)
- **C++**: +6 months (v0.44.0)

---

## 🎯 Success Metrics

### Phase 1 (Reasoning) Success
- [ ] 6 techniques implemented and tested
- [ ] 90%+ test coverage
- [ ] All examples work
- [ ] Documentation complete
- [ ] At least 3 user success stories
- [ ] Performance benchmarks published

### Phase 2 (Protocols) Success
- [ ] MCP server + client working
- [ ] Successfully connects to Claude Desktop
- [ ] A2A integrates with Vertex AI
- [ ] A2A integrates with Bedrock
- [ ] Documentation with platform examples

### Phase 3 (Compositions) Success - UPDATED
- [ ] 9 composition recipes implemented (up from 6)
- [ ] README clearly explains pattern vs composition
- [ ] Educational value validated with users
- [ ] Links to full patterns where applicable
- [ ] **NEW**: RAG with citations working
- [ ] **NEW**: Context optimization working
- [ ] **NEW**: Actor-critic shows relation to Reflection

### Phase 4 (Documentation) Success - NEW
- [ ] 4 infrastructure guides complete
- [ ] All code examples tested
- [ ] Clear distinction: infrastructure vs patterns
- [ ] References to 4 books (Gulli, Alto, Rothman, Albada)

---

## 🚧 Potential Blockers & Mitigations

| Blocker | Impact | Mitigation |
|---------|--------|------------|
| MCP spec changes | HIGH | Implement against stable spec v1.0, add version compat layer |
| A2A not widely adopted | MEDIUM | Focus on Vertex AI/Bedrock first, provide value even standalone |
| Reasoning techniques too slow | MEDIUM | Async implementation, caching, batch processing |
| Cross-language parity delays | LOW | Python-first is acceptable, port incrementally |
| User confusion (pattern vs technique) | LOW | Clear documentation, educational materials |

---

## 💡 Quick Start Command

If you want to start RIGHT NOW with CoT:

```bash
# 1. Create structure
mkdir -p agenkit/techniques/reasoning
touch agenkit/techniques/__init__.py
touch agenkit/techniques/reasoning/__init__.py

# 2. Create the file
cat > agenkit/techniques/reasoning/chain_of_thought.py << 'EOF'
# Copy the CoT implementation from Day 3-4 above
EOF

# 3. Run tests (after creating test file)
pytest tests/techniques/reasoning/test_chain_of_thought.py -v

# 4. Try the example
python examples/techniques/reasoning/cot_example.py
```

---

## 📞 Questions to Answer Before Starting

1. **Priority**: Start with CoT (reasoning), MCP (protocols), or Compositions?
2. **Pace**: Implement one at a time with user feedback, or batch implement?
3. **Language strategy**: Python-first or multi-language from start?
4. **Testing**: What's acceptable coverage? (Recommend 90%+)
5. **Documentation**: Write before implementing (TDD-style) or after?

## My Specific Recommendation

**Start with Chain-of-Thought (#231) this week:**
- Day 1-2: Infrastructure + docs
- Day 3-4: Implementation
- Day 5: Tests
- Day 6: Example + polish

**Outcome**: Working CoT technique by end of week, validates architecture, provides immediate value.

---

## 📋 Related Issues to Review

Before implementing, review these issues for complete context:
- **#231**: Chain-of-Thought implementation details
- **#232**: Tree-of-Thought (understand tree search approach)
- **#233**: Self-Consistency (understand how it builds on CoT)
- **#237**: MCP protocol (if considering protocol-first approach)
- **#239**: Compositions (UPDATED with 3 new recipes)
- **#240**: Documentation (NEW - infrastructure guides)

All issues in Milestone #38: https://github.com/scttfrdmn/agenkit/milestone/38

---

## 🆕 Recent Updates (Dec 9, 2025)

### Books Analyzed
We've now analyzed **4 major books** on agentic systems:
1. Gulli (2025): "Agentic Design Patterns"
2. Alto (2025): "AI Agents in Practice"
3. Rothman (2025): "Context Engineering for Multi-Agent Systems"
4. Albada (2025): "Building Applications with AI Agents"

**Verdict**: Agenkit's Techniques Library plan covers EVERYTHING valuable from all 4 books!

### Enhancements Added
- **Issue #239 updated**: 3 new compositions (RAG with citations, context optimization, actor-critic)
- **Issue #240 created**: Infrastructure documentation (testing, security, deployment)
- **Total effort**: Now 20 weeks (up from 18) with ~4,800 LOC (up from ~4,210)

---

**Ready to start? Review the issues, choose your approach, and let's build!** 🚀
