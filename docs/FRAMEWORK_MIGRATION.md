# Framework Migration Guide

**Migrate from LangChain, LangGraph, CrewAI, AutoGen, Haystack, and other frameworks to agenkit.**

---

## Table of Contents

- [Introduction](#introduction)
- [Why Migrate to Agenkit?](#why-migrate-to-agenkit)
- [Migration Paths](#migration-paths)
  - [LangChain → Agenkit](#langchain--agenkit)
  - [LangGraph → Agenkit](#langgraph--agenkit)
  - [CrewAI → Agenkit](#crewai--agenkit)
  - [AutoGen → Agenkit](#autogen--agenkit)
  - [Haystack → Agenkit](#haystack--agenkit)
  - [Custom Framework → Agenkit](#custom-framework--agenkit)
- [Common Patterns](#common-patterns)
- [Gradual Migration Strategy](#gradual-migration-strategy)
- [Testing Your Migration](#testing-your-migration)

---

## Introduction

Agenkit provides a **cross-language, framework-agnostic** approach to building AI agents. Unlike monolithic frameworks, agenkit gives you:

- **100% feature parity** across 6 languages (Python, Go, TypeScript, Rust, C++, Zig)
- **Composable patterns** instead of opinionated abstractions
- **No vendor lock-in** - escape hatches everywhere
- **Production-ready** - 100% test coverage, used in real systems
- **Framework overhead <0.01%** of LLM call time

This guide helps you migrate from existing frameworks to agenkit while preserving functionality.

---

## Why Migrate to Agenkit?

### Problems with Existing Frameworks

**LangChain:**
- ❌ Monolithic (all-or-nothing adoption)
- ❌ Python-only (no cross-language support)
- ❌ Opinionated abstractions (hard to customize)
- ❌ Breaking changes frequently

**LangGraph:**
- ❌ Complex state management
- ❌ Steep learning curve
- ❌ Python-only
- ❌ Overkill for simple workflows

**CrewAI:**
- ❌ Python-only
- ❌ Limited to agent crews
- ❌ Not composable
- ❌ Inflexible patterns

**AutoGen:**
- ❌ Complex conversation management
- ❌ Python-only
- ❌ Heavy abstractions
- ❌ Limited pattern support

**Haystack:**
- ❌ Document-focused (not general agents)
- ❌ Python-only
- ❌ Complex pipeline syntax
- ❌ Limited agent patterns

### Benefits of Agenkit

✅ **Cross-language**: Same code works in 6 languages
✅ **Modular**: Use only what you need
✅ **Composable**: Mix and match patterns
✅ **Escape hatches**: Never locked in
✅ **Production-ready**: 100% test coverage
✅ **Fast**: <0.01% framework overhead
✅ **18 patterns**: More than any framework
✅ **Simple**: Clear, minimal abstractions

---

## Migration Paths

### LangChain → Agenkit

LangChain is the most popular framework. Migration is straightforward since agenkit patterns map cleanly to LangChain concepts.

#### Concept Mapping

| LangChain | Agenkit | Notes |
|-----------|---------|-------|
| `Chain` | `SequentialAgent` | Sequential processing |
| `LLMChain` | `TaskAgent` + LLM | Single LLM call |
| `SequentialChain` | `SequentialAgent` | Multi-stage pipeline |
| `Router Chain` | `RouterAgent` | Conditional routing |
| `Agent` (ReAct) | `ReActAgent` | Reasoning + tools |
| `ConversationalChain` | `ConversationalAgent` | Multi-turn dialogue |
| `Memory` | `ConversationalAgent.history` | Built-in memory |
| `Tool` | `Tool` | Same concept |
| `Prompt Template` | String formatting | No abstraction needed |

#### Example Migration: Simple Chain

**Before (LangChain):**
```python
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

# Create prompt template
prompt = PromptTemplate(
    input_variables=["product"],
    template="What is a good name for a company that makes {product}?",
)

# Create chain
llm = OpenAI(temperature=0.9)
chain = LLMChain(llm=llm, prompt=prompt)

# Run chain
result = chain.run(product="eco-friendly water bottles")
print(result)
```

**After (Agenkit):**
```python
from agenkit import Agent, Message
from agenkit.adapters import OpenAIAdapter

class CompanyNamer(Agent):
    def __init__(self, llm):
        self.llm = llm

    @property
    def name(self) -> str:
        return "company-namer"

    async def process(self, message: Message) -> Message:
        product = message.content
        prompt = f"What is a good name for a company that makes {product}?"

        response = await self.llm.complete(prompt, temperature=0.9)
        return Message(role="assistant", content=response)

# Create agent
llm = OpenAIAdapter(model="gpt-4")
agent = CompanyNamer(llm)

# Run agent
result = await agent.process(Message(role="user", content="eco-friendly water bottles"))
print(result.content)
```

**Why Better:**
- ✅ No prompt template abstraction (just string formatting)
- ✅ Clear control flow
- ✅ Easy to test
- ✅ Works in all 6 languages

#### Example Migration: Sequential Chain

**Before (LangChain):**
```python
from langchain.chains import SimpleSequentialChain
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate

# Chain 1: Generate synopsis
llm = OpenAI(temperature=0.7)
synopsis_template = """You are a playwright. Given the title of play, write a synopsis.

Title: {title}
Synopsis:"""
synopsis_prompt = PromptTemplate(input_variables=["title"], template=synopsis_template)
synopsis_chain = LLMChain(llm=llm, prompt=synopsis_prompt)

# Chain 2: Generate review
review_template = """You are a critic. Given the synopsis of play, write a review.

Synopsis: {synopsis}
Review:"""
review_prompt = PromptTemplate(input_variables=["synopsis"], template=review_template)
review_chain = LLMChain(llm=llm, prompt=review_prompt)

# Combine chains
overall_chain = SimpleSequentialChain(
    chains=[synopsis_chain, review_chain],
    verbose=True
)

# Run
review = overall_chain.run("Hamlet")
print(review)
```

**After (Agenkit):**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message
from agenkit.adapters import OpenAIAdapter

class SynopsisWriter(Agent):
    def __init__(self, llm):
        self.llm = llm

    @property
    def name(self) -> str:
        return "synopsis-writer"

    async def process(self, message: Message) -> Message:
        title = message.content
        prompt = f"""You are a playwright. Given the title of play, write a synopsis.

Title: {title}
Synopsis:"""
        synopsis = await self.llm.complete(prompt, temperature=0.7)
        return Message(role="assistant", content=synopsis)

class ReviewWriter(Agent):
    def __init__(self, llm):
        self.llm = llm

    @property
    def name(self) -> str:
        return "review-writer"

    async def process(self, message: Message) -> Message:
        synopsis = message.content
        prompt = f"""You are a critic. Given the synopsis of play, write a review.

Synopsis: {synopsis}
Review:"""
        review = await self.llm.complete(prompt, temperature=0.7)
        return Message(role="assistant", content=review)

# Create pipeline
llm = OpenAIAdapter(model="gpt-4")
pipeline = SequentialAgent(
    agents=[
        SynopsisWriter(llm),
        ReviewWriter(llm)
    ],
    name="play-reviewer"
)

# Run
result = await pipeline.process(Message(role="user", content="Hamlet"))
print(result.content)
```

**Why Better:**
- ✅ Explicit agent boundaries
- ✅ Testable components
- ✅ No template abstraction
- ✅ Clear data flow
- ✅ Works in all languages

#### Example Migration: ReAct Agent

**Before (LangChain):**
```python
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.llms import OpenAI

def search(query: str) -> str:
    return f"Search results for: {query}"

def calculator(expression: str) -> str:
    return str(eval(expression))

tools = [
    Tool(
        name="Search",
        func=search,
        description="Search the web"
    ),
    Tool(
        name="Calculator",
        func=calculator,
        description="Do math"
    )
]

llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

result = agent.run("What is 15% of the GDP of France?")
print(result)
```

**After (Agenkit):**
```python
from agenkit.patterns import ReActAgent
from agenkit import Tool, Message
from agenkit.adapters import OpenAIAdapter

def search(query: str) -> str:
    return f"Search results for: {query}"

def calculator(expression: str) -> str:
    return str(eval(expression))

tools = [
    Tool(name="search", func=search, description="Search the web"),
    Tool(name="calculator", func=calculator, description="Do math")
]

llm = OpenAIAdapter(model="gpt-4")
agent = ReActAgent(
    llm=llm,
    tools=tools,
    max_iterations=10,
    verbose=True
)

result = await agent.process(Message(role="user", content="What is 15% of the GDP of France?"))
print(result.content)
```

**Why Better:**
- ✅ Same concept, cleaner API
- ✅ Explicit configuration
- ✅ Works in all languages
- ✅ Better control over iterations

#### Migration Checklist: LangChain → Agenkit

- [ ] Replace `Chain` with `Agent` classes
- [ ] Replace `SequentialChain` with `SequentialAgent`
- [ ] Replace `Router` with `RouterAgent`
- [ ] Replace `Agent` (ReAct) with `ReActAgent`
- [ ] Replace `ConversationalChain` with `ConversationalAgent`
- [ ] Remove `PromptTemplate` (use f-strings or format())
- [ ] Replace `LangChain.Memory` with `ConversationalAgent.history`
- [ ] Tools stay the same (same concept)
- [ ] Test each component independently

---

### LangGraph → Agenkit

LangGraph uses state graphs for complex workflows. Agenkit's `OrchestrationAgent` provides similar functionality with simpler API.

#### Concept Mapping

| LangGraph | Agenkit | Notes |
|-----------|---------|-------|
| `StateGraph` | `OrchestrationAgent` | Workflow automation |
| `Node` | Stage in workflow | Each stage has agents |
| `Edge` | Workflow definition | Declarative stages |
| `Conditional Edge` | `condition` in stage | If-then-else logic |
| `State` | Message metadata | Passed through workflow |

#### Example Migration: State Graph

**Before (LangGraph):**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    input: str
    analysis: str
    decision: str

def analyze(state: State) -> State:
    # Analyze input
    state["analysis"] = f"Analysis of: {state['input']}"
    return state

def decide(state: State) -> State:
    # Make decision
    state["decision"] = "Approved" if "important" in state["analysis"] else "Rejected"
    return state

def route(state: State) -> str:
    return "approve" if state["decision"] == "Approved" else "reject"

# Build graph
workflow = StateGraph(State)
workflow.add_node("analyze", analyze)
workflow.add_node("decide", decide)
workflow.add_edge("analyze", "decide")
workflow.add_conditional_edges("decide", route, {
    "approve": "approve_node",
    "reject": "reject_node"
})

app = workflow.compile()
result = app.invoke({"input": "Important proposal"})
```

**After (Agenkit):**
```python
from agenkit.patterns import OrchestrationAgent, WorkflowDefinition
from agenkit import Agent, Message

class Analyzer(Agent):
    @property
    def name(self) -> str:
        return "analyzer"

    async def process(self, message: Message) -> Message:
        analysis = f"Analysis of: {message.content}"
        return Message(
            role="assistant",
            content=analysis,
            metadata={"analysis": analysis}
        )

class DecisionMaker(Agent):
    @property
    def name(self) -> str:
        return "decision-maker"

    async def process(self, message: Message) -> Message:
        analysis = message.content
        decision = "Approved" if "important" in analysis else "Rejected"
        return Message(
            role="assistant",
            content=decision,
            metadata={"decision": decision}
        )

# Define workflow
workflow = WorkflowDefinition({
    "stages": [
        {
            "name": "analyze",
            "agents": ["analyzer"],
            "execution": "sequential"
        },
        {
            "name": "decide",
            "agents": ["decision-maker"],
            "execution": "sequential"
        },
        {
            "name": "approve",
            "agents": ["approver"],
            "condition": "decide.metadata['decision'] == 'Approved'"
        },
        {
            "name": "reject",
            "agents": ["rejector"],
            "condition": "decide.metadata['decision'] == 'Rejected'"
        }
    ]
})

# Create orchestrator
orchestrator = OrchestrationAgent(
    agents={
        "analyzer": Analyzer(),
        "decision-maker": DecisionMaker(),
        "approver": ApproverAgent(),
        "rejector": RejectorAgent()
    },
    workflow=workflow
)

# Run
result = await orchestrator.process(Message(role="user", content="Important proposal"))
```

**Why Better:**
- ✅ Simpler API (no graph building)
- ✅ Declarative workflow definition
- ✅ Same functionality, clearer intent
- ✅ Works in all languages

#### Migration Checklist: LangGraph → Agenkit

- [ ] Replace `StateGraph` with `OrchestrationAgent`
- [ ] Replace `Node` with workflow stages
- [ ] Replace `Edge` with workflow stage sequence
- [ ] Replace `Conditional Edge` with stage `condition`
- [ ] Replace `State` dict with `Message.metadata`
- [ ] Test workflow execution thoroughly

---

### CrewAI → Agenkit

CrewAI focuses on agent crews. Agenkit's `MultiagentSystem` and `Collaborative` patterns provide similar functionality with more flexibility.

#### Concept Mapping

| CrewAI | Agenkit | Notes |
|--------|---------|-------|
| `Agent` | `Agent` | Same concept |
| `Task` | Message + Pattern | Tasks become messages |
| `Crew` | `MultiagentSystem` or `Collaborative` | Agent coordination |
| `Process.sequential` | `SequentialAgent` | Sequential execution |
| `Process.hierarchical` | `SupervisorAgent` | Supervised execution |

#### Example Migration: Crew

**Before (CrewAI):**
```python
from crewai import Agent, Task, Crew, Process

# Define agents
researcher = Agent(
    role='Researcher',
    goal='Research the topic thoroughly',
    backstory='Expert researcher',
    verbose=True
)

writer = Agent(
    role='Writer',
    goal='Write engaging content',
    backstory='Professional writer',
    verbose=True
)

# Define tasks
research_task = Task(
    description='Research AI trends',
    agent=researcher
)

writing_task = Task(
    description='Write article about AI trends',
    agent=writer
)

# Create crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential
)

# Execute
result = crew.kickoff()
print(result)
```

**After (Agenkit):**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class Researcher(Agent):
    @property
    def name(self) -> str:
        return "researcher"

    async def process(self, message: Message) -> Message:
        topic = message.content
        # Research the topic
        research = f"Research findings on {topic}: ..."
        return Message(role="assistant", content=research)

class Writer(Agent):
    @property
    def name(self) -> str:
        return "writer"

    async def process(self, message: Message) -> Message:
        research = message.content
        # Write article based on research
        article = f"Article based on: {research}"
        return Message(role="assistant", content=article)

# Create sequential workflow
crew = SequentialAgent(
    agents=[
        Researcher(),
        Writer()
    ],
    name="research-crew"
)

# Execute
result = await crew.process(Message(role="user", content="AI trends"))
print(result.content)
```

**Why Better:**
- ✅ Simpler API
- ✅ More flexible (any pattern, not just sequential)
- ✅ Works in all languages
- ✅ Testable components

#### Migration Checklist: CrewAI → Agenkit

- [ ] Replace `Agent` with agenkit `Agent` classes
- [ ] Replace `Task` with `Message` objects
- [ ] Replace `Crew` with appropriate pattern (Sequential, Multiagent, etc.)
- [ ] Remove `backstory` (just focus on `process()` logic)
- [ ] Test agent interactions

---

### AutoGen → Agenkit

AutoGen focuses on multi-agent conversations. Agenkit's `MultiagentSystem` and `Collaborative` patterns provide similar functionality.

#### Concept Mapping

| AutoGen | Agenkit | Notes |
|---------|---------|-------|
| `AssistantAgent` | `Agent` | Base agent |
| `UserProxyAgent` | `HumanInLoopAgent` | Human interaction |
| `ConversableAgent` | `ConversationalAgent` | Multi-turn dialogue |
| `GroupChat` | `MultiagentSystem` | Multi-agent coordination |
| `GroupChatManager` | `SupervisorAgent` | Coordination oversight |

#### Example Migration: Group Chat

**Before (AutoGen):**
```python
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# Create agents
assistant = AssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant"
)

coder = AssistantAgent(
    name="coder",
    system_message="You write code"
)

user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="NEVER"
)

# Create group chat
groupchat = GroupChat(
    agents=[user_proxy, assistant, coder],
    messages=[],
    max_round=10
)

manager = GroupChatManager(groupchat=groupchat)

# Start conversation
user_proxy.initiate_chat(
    manager,
    message="Write a Python function to calculate fibonacci"
)
```

**After (Agenkit):**
```python
from agenkit.patterns import MultiagentSystem
from agenkit import Agent, Message

class Assistant(Agent):
    @property
    def name(self) -> str:
        return "assistant"

    async def process(self, message: Message) -> Message:
        # Process as helpful assistant
        response = f"As an assistant, I suggest: {message.content}"
        return Message(role="assistant", content=response)

class Coder(Agent):
    @property
    def name(self) -> str:
        return "coder"

    async def process(self, message: Message) -> Message:
        # Write code
        code = f"def fibonacci(n):\n    # Implementation based on: {message.content}"
        return Message(role="assistant", content=code)

# Create multi-agent system
team = MultiagentSystem(
    agents=[
        Assistant(),
        Coder()
    ],
    coordination="debate",  # Agents discuss
    rounds=3
)

# Start conversation
result = await team.process(Message(
    role="user",
    content="Write a Python function to calculate fibonacci"
))

print(result.content)
```

**Why Better:**
- ✅ Simpler conversation management
- ✅ More flexible coordination strategies
- ✅ Works in all languages
- ✅ Clear agent roles

#### Migration Checklist: AutoGen → Agenkit

- [ ] Replace `AssistantAgent` with agenkit `Agent`
- [ ] Replace `UserProxyAgent` with `HumanInLoopAgent`
- [ ] Replace `GroupChat` with `MultiagentSystem`
- [ ] Remove `GroupChatManager` (built into `MultiagentSystem`)
- [ ] Simplify conversation management

---

### Haystack → Agenkit

Haystack focuses on document processing pipelines. Agenkit can handle similar workflows with more general patterns.

#### Concept Mapping

| Haystack | Agenkit | Notes |
|----------|---------|-------|
| `Pipeline` | `SequentialAgent` | Processing pipeline |
| `Node` | `Agent` | Processing step |
| `Retriever` | Custom `Agent` | Document retrieval |
| `Reader` | Custom `Agent` | Question answering |
| `Generator` | `TaskAgent` + LLM | Text generation |

#### Example Migration: QA Pipeline

**Before (Haystack):**
```python
from haystack import Pipeline
from haystack.nodes import BM25Retriever, FARMReader

# Create pipeline
pipeline = Pipeline()

# Add retriever
retriever = BM25Retriever(document_store=document_store)
pipeline.add_node(component=retriever, name="Retriever", inputs=["Query"])

# Add reader
reader = FARMReader(model_name_or_path="deepset/roberta-base-squad2")
pipeline.add_node(component=reader, name="Reader", inputs=["Retriever"])

# Run pipeline
result = pipeline.run(
    query="What is the capital of France?",
    params={"Retriever": {"top_k": 10}, "Reader": {"top_k": 5}}
)
```

**After (Agenkit):**
```python
from agenkit.patterns import SequentialAgent
from agenkit import Agent, Message

class Retriever(Agent):
    def __init__(self, document_store, top_k=10):
        self.document_store = document_store
        self.top_k = top_k

    @property
    def name(self) -> str:
        return "retriever"

    async def process(self, message: Message) -> Message:
        query = message.content
        # Retrieve documents
        docs = self.document_store.search(query, top_k=self.top_k)
        return Message(
            role="assistant",
            content=docs,
            metadata={"docs": docs}
        )

class Reader(Agent):
    def __init__(self, model, top_k=5):
        self.model = model
        self.top_k = top_k

    @property
    def name(self) -> str:
        return "reader"

    async def process(self, message: Message) -> Message:
        docs = message.metadata["docs"]
        query = message.metadata.get("original_query", "")

        # Answer question from documents
        answer = self.model.answer(query, docs, top_k=self.top_k)
        return Message(role="assistant", content=answer)

# Create pipeline
pipeline = SequentialAgent(
    agents=[
        Retriever(document_store, top_k=10),
        Reader(reader_model, top_k=5)
    ],
    name="qa-pipeline"
)

# Run pipeline
result = await pipeline.process(Message(
    role="user",
    content="What is the capital of France?",
    metadata={"original_query": "What is the capital of France?"}
))

print(result.content)
```

**Why Better:**
- ✅ More flexible (not document-specific)
- ✅ Works with any data type
- ✅ Cross-language support
- ✅ Composable with other patterns

#### Migration Checklist: Haystack → Agenkit

- [ ] Replace `Pipeline` with `SequentialAgent`
- [ ] Replace each `Node` with custom `Agent`
- [ ] Adapt document store interactions to agent `process()`
- [ ] Use `Message.metadata` for passing context
- [ ] Test pipeline with sample documents

---

### Custom Framework → Agenkit

If you've built a custom agent framework, migration depends on your architecture. Follow these general steps:

#### Migration Strategy

1. **Identify Core Abstractions**
   - What is your "agent" concept?
   - How do agents communicate?
   - What patterns do you use?

2. **Map to Agenkit Patterns**
   - Sequential processing → `SequentialAgent`
   - Parallel processing → `ParallelAgent`
   - Routing → `RouterAgent`
   - Reflection → `ReflectionAgent`
   - Tool usage → `ReActAgent`
   - etc.

3. **Implement Agent Interface**
   ```python
   class MyAgent(Agent):
       @property
       def name(self) -> str:
           return "my-agent"

       async def process(self, message: Message) -> Message:
           # Your logic here
           return Message(...)
   ```

4. **Use Patterns for Orchestration**
   - Replace custom orchestration with agenkit patterns
   - Use `OrchestrationAgent` for complex workflows

5. **Test Incrementally**
   - Migrate one component at a time
   - Test each component independently
   - Verify end-to-end behavior

---

## Common Patterns

### From Framework Chains to Agenkit Agents

**General Pattern:**
```python
# Framework chain
chain = Framework.Chain([step1, step2, step3])
result = chain.run(input)

# Agenkit equivalent
pipeline = SequentialAgent(agents=[agent1, agent2, agent3])
result = await pipeline.process(Message(role="user", content=input))
```

### From Framework Tools to Agenkit Tools

**General Pattern:**
```python
# Framework tool
tool = Framework.Tool(name="search", func=search_func, description="Search")

# Agenkit tool (same!)
tool = Tool(name="search", func=search_func, description="Search")
```

### From Framework Memory to Agenkit Memory

**General Pattern:**
```python
# Framework memory
memory = Framework.ConversationalMemory()
agent = Framework.Agent(memory=memory)

# Agenkit equivalent
agent = ConversationalAgent(llm=my_llm, max_history=50)
# Memory management is built-in
```

---

## Gradual Migration Strategy

Don't migrate everything at once. Use this phased approach:

### Phase 1: Identify Components (Week 1)
- [ ] List all agents/chains in current system
- [ ] Identify dependencies between components
- [ ] Map to agenkit patterns
- [ ] Prioritize migration order (start with leaf nodes)

### Phase 2: Migrate Core Agents (Week 2-3)
- [ ] Migrate simplest agents first
- [ ] Create agenkit `Agent` classes
- [ ] Write unit tests for each agent
- [ ] Verify behavior matches original

### Phase 3: Migrate Patterns (Week 3-4)
- [ ] Replace framework chains with `SequentialAgent`
- [ ] Replace framework routers with `RouterAgent`
- [ ] Replace framework orchestrators with `OrchestrationAgent`
- [ ] Test pattern compositions

### Phase 4: Integration Testing (Week 4)
- [ ] Run end-to-end tests
- [ ] Compare outputs with original system
- [ ] Performance benchmark
- [ ] Fix any discrepancies

### Phase 5: Gradual Rollout (Week 5+)
- [ ] Deploy to staging
- [ ] A/B test (old vs new)
- [ ] Monitor metrics
- [ ] Gradual production rollout

### Hybrid Approach (During Migration)

You can run both systems in parallel:

```python
# Gradual migration: some agents in agenkit, some in old framework
from agenkit import Agent, Message
from old_framework import OldAgent

class HybridAgent(Agent):
    """Wrapper for old framework agent."""

    def __init__(self, old_agent):
        self.old_agent = old_agent

    @property
    def name(self) -> str:
        return self.old_agent.name

    async def process(self, message: Message) -> Message:
        # Adapt agenkit message to old framework
        old_input = self.adapt_to_old(message)

        # Use old agent
        old_output = self.old_agent.run(old_input)

        # Adapt back to agenkit message
        return self.adapt_from_old(old_output)

# Use hybrid agents in agenkit patterns
pipeline = SequentialAgent(
    agents=[
        NewAgenkitAgent(),  # New
        HybridAgent(old_agent),  # Wrapped old agent
        AnotherNewAgent()  # New
    ]
)
```

---

## Testing Your Migration

### Unit Tests

Test each agent independently:

```python
import pytest
from agenkit import Message

@pytest.mark.asyncio
async def test_agent():
    agent = MyMigratedAgent()
    result = await agent.process(Message(role="user", content="test"))
    assert result.content == "expected"
```

### Integration Tests

Test agent interactions:

```python
@pytest.mark.asyncio
async def test_pipeline():
    pipeline = SequentialAgent(agents=[agent1, agent2, agent3])
    result = await pipeline.process(Message(role="user", content="input"))
    assert result.content == "final output"
```

### Regression Tests

Compare outputs with original framework:

```python
@pytest.mark.asyncio
async def test_migration_equivalence():
    # Original framework
    old_result = old_framework_agent.run("test input")

    # Agenkit
    new_result = await new_agenkit_agent.process(
        Message(role="user", content="test input")
    )

    # Compare
    assert new_result.content == old_result
```

### Performance Tests

Verify no performance regression:

```python
import time

async def benchmark():
    start = time.time()
    await agent.process(Message(role="user", content="benchmark"))
    elapsed = time.time() - start
    assert elapsed < 1.0  # Should complete in <1s
```

---

## Conclusion

Migrating to agenkit provides:
- **Cross-language support** - Same agents work in 6 languages
- **Better composability** - Mix and match patterns
- **Production readiness** - 100% test coverage
- **Performance** - <0.01% framework overhead
- **Flexibility** - No vendor lock-in

### Migration Difficulty

| Framework | Difficulty | Time Estimate | Notes |
|-----------|-----------|---------------|-------|
| **LangChain** | ⭐⭐ Easy | 1-2 weeks | Clean mapping to patterns |
| **LangGraph** | ⭐⭐⭐ Medium | 2-3 weeks | Workflow definition more complex |
| **CrewAI** | ⭐⭐ Easy | 1-2 weeks | Similar agent concepts |
| **AutoGen** | ⭐⭐⭐ Medium | 2-3 weeks | Conversation management differs |
| **Haystack** | ⭐⭐⭐ Medium | 2-3 weeks | Document-specific patterns |
| **Custom** | ⭐⭐⭐⭐ Variable | 3-6 weeks | Depends on complexity |

### Next Steps

1. **Review your current framework** - Understand what you're migrating from
2. **Map to agenkit patterns** - Use this guide to identify equivalents
3. **Start small** - Migrate one component first
4. **Test thoroughly** - Unit, integration, regression tests
5. **Iterate** - Gradually migrate remaining components
6. **Deploy** - Gradual rollout with monitoring

### Resources

- **Getting Started**: `docs/getting-started/PYTHON.md` (and other languages)
- **Pattern Guide**: `docs/PATTERN_GUIDE.md`
- **Cross-Language Migration**: `docs/CROSS_LANGUAGE_MIGRATION.md`
- **Examples**: `examples/` directory
- **API Reference**: Coming in v0.47.0

---

**Happy migrating! 🚀**
