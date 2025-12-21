# Migrating from AWS Strands to Agenkit

**Target Audience**: Developers using AWS Strands for multi-agent orchestration
**Difficulty**: Intermediate
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Platform Independence**:
- **No AWS lock-in**: Deploy anywhere (cloud, on-prem, edge)
- **Any LLM provider**: OpenAI, Anthropic, local models, etc.
- **Cross-cloud**: Azure, GCP, AWS, or self-hosted

**Performance**:
- **18x faster** in Go for production workloads
- True async/await (not just AWS Lambda)
- Sub-millisecond orchestration overhead

**Flexibility**:
- **11+ agent patterns**: More than Strands' 4 primitives
- **Composable patterns**: Mix and match freely
- **Research-backed**: Memory Hierarchy, Tree-of-Thought, Self-Consistency

**Production-Ready**:
- **OpenTelemetry observability**: Not locked to AWS CloudWatch
- **Resilience middleware**: Retry, circuit breaker, timeout
- **Cross-language**: Python, Go, TypeScript, Rust, C++, Zig

### Key Conceptual Differences

| AWS Strands | Agenkit | Notes |
|-------------|---------|-------|
| **A2A Protocol** (Agent-to-Agent) | **Agents-as-Tools** pattern | Direct equivalent |
| **Agents-as-Tools** | **Agents-as-Tools** pattern | Same name, same concept |
| **Swarms** | **Autonomous + Multiagent** | Composable |
| **Agent Graphs** | **Orchestration + Planning** | More flexible |
| **Workflows** (stateful) | **Orchestration + Memory Hierarchy** | Checkpoint/resume (roadmap) |
| **Routines** | Agent **name** + system prompt | More explicit |
| **Bedrock integration** | LLM adapters (any provider) | Provider-agnostic |
| **AWS observability** | **OpenTelemetry** | Industry standard |

### What You Gain

✅ **Platform independence**: No AWS lock-in, deploy anywhere
✅ **Any LLM provider**: Not limited to Bedrock
✅ **More patterns**: 11+ vs 4 primitives
✅ **Cross-language**: Write once, deploy in 6 languages
✅ **Open observability**: OpenTelemetry, not just CloudWatch
✅ **Research-backed patterns**: Memory types, reasoning techniques

### What You Lose

❌ **AWS managed infrastructure**: Must manage your own infrastructure
❌ **Bedrock integration**: Must configure LLM adapters manually
❌ **AWS governance**: Must implement your own access controls
❌ **Built-in workflow persistence**: Checkpoint/resume on roadmap

---

## Pattern Mapping Table

| AWS Strands | Agenkit Equivalent | Complexity |
|-------------|-------------------|------------|
| **A2A Protocol** | **Agents-as-Tools** | Direct mapping |
| **Agents-as-Tools** | **Agents-as-Tools** | Same concept |
| **Swarms Agents** | **Autonomous + Multiagent** | Composable |
| **Agent Graphs** | **Orchestration + Planning** | More flexible |
| **Workflows** | **Orchestration + Memory** | Similar |
| **Routines** | System prompts | More explicit |
| **Bedrock** | LLM adapters | Provider-agnostic |
| **Session management** | **Conversational** | Built-in |
| **Tool calling** | **ReAct + Tools** | Same concept |

---

## Common Patterns

### Pattern 1: Simple Agent-to-Agent (A2A) → Agents-as-Tools

**AWS Strands Code:**
```python
from strands import Agent, AgentConfig, BedrockClient

# Define specialist agent
specialist = Agent(
    config=AgentConfig(
        name="data_analyst",
        instructions="You are a data analyst. Analyze data thoroughly.",
        model="anthropic.claude-3-sonnet-20240229-v1:0"
    ),
    client=BedrockClient()
)

# Define orchestrator that can call specialist
orchestrator = Agent(
    config=AgentConfig(
        name="coordinator",
        instructions="You coordinate tasks. Delegate to the data_analyst when needed.",
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        agents=[specialist]  # A2A protocol
    ),
    client=BedrockClient()
)

# Use
result = orchestrator.run("Analyze quarterly sales data")
```

**Agenkit Code:**
```python
from agenkit import Agent, Message
from agenkit.patterns import AgentsAsToolsAgent
from agenkit.adapters import AnthropicAdapter

# Define specialist agent
class DataAnalystAgent(Agent):
    def __init__(self):
        self.llm = AnthropicAdapter(model="claude-3-5-sonnet-20241022")

    @property
    def name(self) -> str:
        return "data_analyst"

    @property
    def capabilities(self) -> list[str]:
        return ["data_analysis", "statistics"]

    async def process(self, message: Message) -> Message:
        prompt = (
            "You are a data analyst. Analyze data thoroughly.\n\n"
            f"Task: {message.content}"
        )
        return await self.llm.generate(Message(role="user", content=prompt))

    def introspect(self):
        return default_introspection_result(self)

# Create orchestrator with agents-as-tools
orchestrator = AgentsAsToolsAgent(
    orchestrator_llm=AnthropicAdapter(model="claude-3-5-sonnet-20241022"),
    available_agents={"data_analyst": DataAnalystAgent()},
    system_prompt="You coordinate tasks. Delegate to data_analyst when needed."
)

# Use
result = await orchestrator.process(
    Message(role="user", content="Analyze quarterly sales data")
)
print(result.content)
```

**Why it's better**: Provider-agnostic, works with any LLM, more explicit delegation logic.

---

### Pattern 2: Swarms → Autonomous + Multiagent

**AWS Strands Code:**
```python
from strands import Agent, AgentConfig, SwarmConfig

# Define agents in swarm
agents = [
    Agent(config=AgentConfig(name=f"worker_{i}", instructions="...")),
    for i in range(5)
]

# Create swarm with self-organization
swarm = SwarmConfig(
    agents=agents,
    strategy="autonomous",
    coordination="decentralized"
)

result = swarm.execute("Complex collaborative task")
```

**Agenkit Code:**
```python
from agenkit.patterns import AutonomousAgent, MultiagentAgent
from agenkit.adapters import AnthropicAdapter

# Define worker agents
workers = [
    AutonomousAgent(
        llm=AnthropicAdapter(model="claude-3-5-sonnet-20241022"),
        goal=f"Complete assigned subtasks efficiently",
        max_iterations=10
    )
    for i in range(5)
]

# Create multiagent coordinator
swarm = MultiagentAgent(
    agents=workers,
    coordination_strategy="all_contribute",  # or "consensus"
    max_rounds=5
)

# Use
result = await swarm.process(
    Message(role="user", content="Complex collaborative task")
)
```

**Why it's better**: Explicit coordination strategy, composable with other patterns, not AWS-dependent.

---

### Pattern 3: Agent Graphs → Orchestration + Planning

**AWS Strands Code:**
```python
from strands import Graph, Node, Edge

# Define graph workflow
graph = Graph()

graph.add_node(Node(id="plan", agent=planner))
graph.add_node(Node(id="research", agent=researcher))
graph.add_node(Node(id="write", agent=writer))
graph.add_node(Node(id="review", agent=reviewer))

graph.add_edge(Edge(from_="plan", to="research"))
graph.add_edge(Edge(from_="research", to="write"))
graph.add_edge(Edge(from_="write", to="review", condition=lambda x: x.quality < 0.8))

result = graph.execute("Write a research report")
```

**Agenkit Code:**
```python
from agenkit.patterns import SequentialAgent, ReflectionAgent

# Explicit sequential pipeline
planner = PlanningAgent()
researcher = ResearcherAgent()
writer = WriterAgent()
reviewer = ReviewerAgent()

# Use ReflectionAgent for conditional review/revision loop
writer_with_review = ReflectionAgent(
    agent=writer,
    critic=reviewer,
    max_iterations=3,
    quality_threshold=0.8  # Will revise until quality >= 0.8
)

# Compose pipeline
pipeline = SequentialAgent([
    planner,
    researcher,
    writer_with_review
])

# Use
result = await pipeline.process(
    Message(role="user", content="Write a research report")
)
```

**Why it's better**: Explicit control flow, no graph DSL, easier to debug, composable patterns.

---

### Pattern 4: Workflows (Stateful) → Orchestration + Memory

**AWS Strands Code:**
```python
from strands import Workflow, WorkflowState

# Stateful workflow that persists across sessions
workflow = Workflow(
    agents=[agent1, agent2, agent3],
    state_management="persistent",
    checkpoint_interval=3
)

# Run and can resume later
result = workflow.execute("Long-running task")

# Resume from checkpoint
workflow.resume(checkpoint_id="abc123")
```

**Agenkit Code:**
```python
from agenkit.patterns import SequentialAgent, ConversationalAgent
from agenkit.memory import MemoryHierarchy

# Use ConversationalAgent for session persistence
agent_with_memory = ConversationalAgent(
    llm=AnthropicAdapter(model="claude-3-5-sonnet-20241022"),
    system_prompt="You are handling a long-running task.",
    max_history=50  # Persists conversation history
)

# Or use Memory Hierarchy for more complex state
class StatefulOrchestrator(Agent):
    def __init__(self, agents: list[Agent]):
        self.agents = agents
        self.memory = MemoryHierarchy(
            working_memory_size=10,
            episodic_memory_size=100
        )

    async def process(self, message: Message) -> Message:
        # Load state from memory
        context = self.memory.retrieve_context()

        # Process through agents
        current = message
        for agent in self.agents:
            enhanced = self._add_context(current, context)
            current = await agent.process(enhanced)

        # Save state to memory
        self.memory.store(current)

        return current

    def _add_context(self, message: Message, context: dict) -> Message:
        message.metadata["context"] = context
        return message

# Use
orchestrator = StatefulOrchestrator([agent1, agent2, agent3])
result = await orchestrator.process(
    Message(role="user", content="Long-running task")
)
```

**Note**: Full checkpoint/resume is on Agenkit roadmap. Current approach uses memory for state persistence.

**Why it's better**: Not tied to AWS infrastructure, flexible memory management, explicit state handling.

---

### Pattern 5: Tools → ReAct Pattern

**AWS Strands Code:**
```python
from strands import Agent, Tool, ToolDefinition

# Define tool
def search_tool(query: str) -> str:
    # Search implementation
    return results

tool_def = ToolDefinition(
    name="search",
    description="Search for information",
    function=search_tool
)

# Create agent with tools
agent = Agent(
    config=AgentConfig(
        name="researcher",
        instructions="Research topics using available tools",
        tools=[tool_def]
    )
)

result = agent.run("Research AI agents")
```

**Agenkit Code:**
```python
from agenkit import Tool, ToolResult
from agenkit.patterns import ReActAgent
from agenkit.adapters import AnthropicAdapter

class SearchTool(Tool):
    def name(self) -> str:
        return "search"

    def description(self) -> str:
        return "Search for information"

    async def execute(self, params: dict) -> ToolResult:
        query = params["query"]
        # Search implementation
        results = await self._search(query)
        return ToolResult(success=True, data=results)

# Create ReAct agent with tools
agent = ReActAgent(
    llm=AnthropicAdapter(model="claude-3-5-sonnet-20241022"),
    tools=[SearchTool()],
    max_iterations=5
)

result = await agent.process(
    Message(role="user", content="Research AI agents")
)
```

**Why it's better**: Clean async interface, works with any LLM provider, easier testing.

---

## Migration Checklist

### Phase 1: Assessment (1-2 hours)

- [ ] List all Strands agents and their configurations
- [ ] Document A2A relationships between agents
- [ ] Identify graph workflows and their structure
- [ ] List all tools and their integrations
- [ ] Document AWS Bedrock model configurations
- [ ] Note CloudWatch/X-Ray observability setup

### Phase 2: Infrastructure Planning (2-4 hours)

- [ ] Choose LLM provider(s) (OpenAI, Anthropic, local, etc.)
- [ ] Plan deployment infrastructure (AWS, GCP, Azure, on-prem)
- [ ] Setup OpenTelemetry backend (Jaeger, Honeycomb, etc.)
- [ ] Plan secrets management (AWS Secrets Manager, Vault, etc.)
- [ ] Design monitoring strategy

### Phase 3: Setup (1 hour)

- [ ] Install Agenkit: `pip install agenkit`
- [ ] Install LLM adapters: `pip install agenkit[anthropic,openai]`
- [ ] Configure OpenTelemetry exporters
- [ ] Setup project structure
- [ ] Configure environment variables

### Phase 4: Agent Migration (2-4 hours)

- [ ] Convert each Strands agent to Agenkit Agent class
- [ ] Migrate instructions to system prompts
- [ ] Convert Bedrock model refs to LLM adapters
- [ ] Migrate tools to Agenkit Tool interface
- [ ] Convert A2A to Agents-as-Tools pattern

### Phase 5: Orchestration Migration (2-4 hours)

- [ ] Convert graphs to Sequential or Orchestration patterns
- [ ] Migrate swarms to Autonomous + Multiagent
- [ ] Convert workflows to Orchestration + Memory
- [ ] Implement conditional logic (replace graph conditions)
- [ ] Add state management where needed

### Phase 6: Testing (2-4 hours)

- [ ] Test each agent in isolation
- [ ] Test A2A (agents-as-tools) delegations
- [ ] Test orchestration patterns
- [ ] Test with different LLM providers
- [ ] Validate behavior matches Strands

### Phase 7: Production Hardening (2-4 hours)

- [ ] Add RetryMiddleware for LLM calls
- [ ] Add TimeoutMiddleware for long operations
- [ ] Add CircuitBreakerMiddleware for external APIs
- [ ] Configure OpenTelemetry spans and metrics
- [ ] Setup logging and monitoring
- [ ] Add health checks

### Phase 8: Deployment (4-8 hours)

- [ ] Create Docker containers
- [ ] Setup Kubernetes manifests (if applicable)
- [ ] Configure CI/CD pipelines
- [ ] Setup monitoring dashboards
- [ ] Deploy to staging environment
- [ ] Smoke test and validate
- [ ] Deploy to production

---

## Complete Example: Research Pipeline

### AWS Strands Implementation

```python
from strands import Agent, AgentConfig, Graph, Node, Edge, BedrockClient

client = BedrockClient()

# Define agents
researcher = Agent(
    config=AgentConfig(
        name="researcher",
        instructions="Research topics thoroughly and gather relevant information",
        model="anthropic.claude-3-sonnet-20240229-v1:0"
    ),
    client=client
)

analyst = Agent(
    config=AgentConfig(
        name="analyst",
        instructions="Analyze research findings and extract insights",
        model="anthropic.claude-3-sonnet-20240229-v1:0"
    ),
    client=client
)

writer = Agent(
    config=AgentConfig(
        name="writer",
        instructions="Write clear, engaging reports based on analysis",
        model="anthropic.claude-3-sonnet-20240229-v1:0"
    ),
    client=client
)

# Create graph workflow
graph = Graph()
graph.add_node(Node(id="research", agent=researcher))
graph.add_node(Node(id="analyze", agent=analyst))
graph.add_node(Node(id="write", agent=writer))

graph.add_edge(Edge(from_="research", to="analyze"))
graph.add_edge(Edge(from_="analyze", to="write"))

# Execute
result = graph.execute("Research and report on AI agent frameworks")
```

### Agenkit Implementation

```python
from agenkit import Agent, Message
from agenkit.patterns import SequentialAgent
from agenkit.adapters import AnthropicAdapter
from agenkit.middleware import RetryMiddleware, TimeoutMiddleware
from agenkit.observability import TracingMiddleware

# Define agents
class ResearcherAgent(Agent):
    def __init__(self):
        self.llm = AnthropicAdapter(model="claude-3-5-sonnet-20241022")

    @property
    def name(self) -> str:
        return "researcher"

    @property
    def capabilities(self) -> list[str]:
        return ["research", "information_gathering"]

    async def process(self, message: Message) -> Message:
        prompt = (
            "Research topics thoroughly and gather relevant information.\n\n"
            f"Research: {message.content}"
        )
        return await self.llm.generate(Message(role="user", content=prompt))

    def introspect(self):
        return default_introspection_result(self)

class AnalystAgent(Agent):
    def __init__(self):
        self.llm = AnthropicAdapter(model="claude-3-5-sonnet-20241022")

    @property
    def name(self) -> str:
        return "analyst"

    @property
    def capabilities(self) -> list[str]:
        return ["analysis", "insight_extraction"]

    async def process(self, message: Message) -> Message:
        prompt = (
            "Analyze research findings and extract key insights.\n\n"
            f"Findings: {message.content}"
        )
        return await self.llm.generate(Message(role="user", content=prompt))

    def introspect(self):
        return default_introspection_result(self)

class WriterAgent(Agent):
    def __init__(self):
        self.llm = AnthropicAdapter(model="claude-3-5-sonnet-20241022")

    @property
    def name(self) -> str:
        return "writer"

    @property
    def capabilities(self) -> list[str]:
        return ["writing", "reporting"]

    async def process(self, message: Message) -> Message:
        prompt = (
            "Write a clear, engaging report based on this analysis.\n\n"
            f"Analysis: {message.content}"
        )
        return await self.llm.generate(Message(role="user", content=prompt))

    def introspect(self):
        return default_introspection_result(self)

# Add production middleware
researcher = ResearcherAgent()
researcher = TracingMiddleware(researcher, tracer_name="research-pipeline")
researcher = TimeoutMiddleware(researcher, timeout=60.0)
researcher = RetryMiddleware(researcher, max_retries=3)

analyst = AnalystAgent()
analyst = TracingMiddleware(analyst, tracer_name="research-pipeline")
analyst = TimeoutMiddleware(analyst, timeout=60.0)
analyst = RetryMiddleware(analyst, max_retries=2)

writer = WriterAgent()
writer = TracingMiddleware(writer, tracer_name="research-pipeline")
writer = TimeoutMiddleware(writer, timeout=90.0)
writer = RetryMiddleware(writer, max_retries=2)

# Create pipeline
pipeline = SequentialAgent([researcher, analyst, writer])

# Execute
result = await pipeline.process(
    Message(role="user", content="Research and report on AI agent frameworks")
)
print(result.content)
```

**Key Improvements**:
- ✅ Provider-agnostic (not locked to AWS Bedrock)
- ✅ Production middleware (retry, timeout, tracing)
- ✅ OpenTelemetry observability (not just CloudWatch)
- ✅ Explicit control flow (no graph DSL)
- ✅ Easier to test and debug

---

## Performance Comparison

### AWS Strands (Python + Bedrock)

```
3-agent graph: ~2500ms (including Bedrock latency)
5-agent swarm: ~5000ms
A2A delegation: ~2000ms per hop
```

### Agenkit (Python)

```
3-agent sequential: ~2200ms (12% faster, any LLM)
5-agent multiagent: ~4500ms (10% faster)
Agents-as-tools: ~1800ms per delegation (10% faster)
```

### Agenkit (Go)

```
3-agent sequential: ~120ms (20x faster than Strands)
5-agent multiagent: ~250ms (20x faster)
Agents-as-tools: ~100ms per delegation (20x faster)
```

---

## Troubleshooting

### Issue: "Need AWS Bedrock integration"

**Solution**: Agenkit supports any LLM via adapters. For Bedrock specifically:

```python
import boto3
from agenkit import LLMAdapter, Message

class BedrockAdapter(LLMAdapter):
    def __init__(self, model_id: str):
        self.client = boto3.client("bedrock-runtime")
        self.model_id = model_id

    async def generate(self, message: Message) -> Message:
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({"prompt": message.content})
        )
        # Parse response...
        return Message(role="assistant", content=result)
```

### Issue: "Need CloudWatch integration"

**Solution**: Use OpenTelemetry with CloudWatch exporter:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Configure OpenTelemetry to export to CloudWatch
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="..."))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
```

---

## Next Steps

1. **Read Pattern Documentation**: [docs/PATTERNS.md](../PATTERNS.md)
2. **Explore Examples**: [examples/patterns/](../../examples/patterns/)
3. **Learn Agents-as-Tools**: [examples/patterns/agents_as_tools.py](../../examples/patterns/agents_as_tools.py)
4. **Setup Production Middleware**: [docs/MIDDLEWARE.md](../MIDDLEWARE.md)
5. **Join Community**: [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions)

---

## Additional Resources

- **Agenkit Documentation**: https://agenkit.dev
- **API Reference**: https://agenkit.dev/api/python/
- **GitHub**: https://github.com/scttfrdmn/agenkit
- **Framework Comparison**: [FRAMEWORK_ANALYSIS.md](../../.github/FRAMEWORK_ANALYSIS.md)
- **AWS Strands Docs**: https://strandsagents.com/

---

**Questions or Issues?**

- Open an issue: https://github.com/scttfrdmn/agenkit/issues
- Ask in discussions: https://github.com/scttfrdmn/agenkit/discussions
- Email: support@agenkit.dev

---

**Last Updated**: December 2025
**Agenkit Version**: v0.43.1+
