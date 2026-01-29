# Advanced Architectures: Pattern Compositions and Multi-Agent Systems

**One-line**: Practical guide to composing patterns and building complex multi-agent systems  
**Prerequisites**: Familiarity with the [18 core patterns](../../agent-patterns-book)  
**Reference**: Agent Patterns Book, Chapters 39-49

---

## Quick Reference

| Architecture | One-liner | When to Use | Book Chapter |
|--------------|-----------|-------------|--------------|
| Composition Principles | Guidelines for combining patterns | Building complex systems | 39 |
| Agent Swarms | Many simple agents, emergent coordination | Massive parallelization | 40 |
| Hierarchical Systems | Multi-level management hierarchy | Clear organizational structure | 41 |
| Agent Meshes | Peer-to-peer agent network | Decentralized coordination | 42 |
| Hybrid Architectures | Agents + traditional code | Production systems (most common) | 43 |
| Distributed Networks | Agents across multiple machines | Scale beyond single machine | 46 |

For comprehensive coverage, see the [Agent Patterns Book](../../agent-patterns-book), Chapters 39-49.

---

## Composition Principles

**One-line**: Guidelines for combining multiple patterns effectively  
**Reference**: Chapter 39

### Composition Levels

```
Level 1: Single pattern (ReAct)
Level 2: Pattern + middleware (ReAct + Retry)
Level 3: Multiple patterns (ReAct + Sequential)
Level 4: Composition patterns (Supervisor + Workers)
Level 5: Hybrid systems (Agents + Traditional code)
```

### Example: Incremental Composition (Python)

```python
from agenkit.patterns import ReActAgent, SequentialAgent
from agenkit.middleware import RetryDecorator, TimeoutDecorator

# Level 1: Single pattern
research_agent = ReActAgent(llm, tools)

# Level 2: Add middleware
research_agent = RetryDecorator(research_agent, max_attempts=3)
research_agent = TimeoutDecorator(research_agent, timeout_ms=30000)

# Level 3: Compose with Sequential
pipeline = SequentialAgent([
    research_agent,           # Research with tools
    SummarizerAgent(llm),     # Summarize findings
    EditorAgent(llm),         # Edit for clarity
])

result = await pipeline.process(message)
```

**See Chapter 39** for compatibility matrix, anti-patterns, and composition best practices.

---

## Agent Swarms

**One-line**: Many simple agents with emergent coordination  
**Reference**: Chapter 40

### Example: Independent Parallel Swarm (Python)

```python
import asyncio
from agenkit import Agent, Message

async def swarm_process(documents: list[str], agent: Agent) -> list[Message]:
    """Process documents in parallel using agent swarm."""
    tasks = [
        agent.process(Message(role="user", content=doc))
        for doc in documents
    ]
    return await asyncio.gather(*tasks)

# Process 1000 documents in parallel
documents = load_documents()  # 1000 documents
agent = ClassificationAgent(llm)
results = await swarm_process(documents, agent)
```

### Example: Shared State Swarm (TypeScript)

```typescript
class SharedState {
  private findings = new Map<string, string>();
  
  addFinding(agentId: string, finding: string) {
    this.findings.set(agentId, finding);
  }
}

async function swarmWithSharedState(
  queries: string[],
  agents: Agent[],
  state: SharedState
): Promise<void> {
  const tasks = queries.map(async (query, i) => {
    const result = await agents[i % agents.length].process({
      role: 'user',
      content: query
    });
    state.addFinding(`agent-${i}`, result.content);
  });
  
  await Promise.all(tasks);
}
```

**See Chapter 40** for pheromone-inspired patterns, message passing, and coordination strategies.

---

## Hierarchical Agent Systems

**One-line**: Multi-level hierarchy with managers, specialists, and workers  
**Reference**: Chapter 41

### Example: Three-Level Hierarchy (Python)

```python
class ExecutiveAgent(Agent):
    """Top level: Strategic decisions."""
    def __init__(self, llm, managers: list[Agent]):
        self.managers = managers

class ManagerAgent(Agent):
    """Middle level: Tactical execution."""
    def __init__(self, llm, workers: list[Agent]):
        self.workers = workers

# Build hierarchy
workers = [SpecialistAgent(llm) for _ in range(4)]
managers = [ManagerAgent(llm, workers[:2]), ManagerAgent(llm, workers[2:])]
executive = ExecutiveAgent(llm, managers)

# Execute top-down
result = await executive.process(Message(role="user", content="Analyze Q4 performance"))
```

**See Chapter 41** for delegation patterns, span of control, and hierarchy trade-offs.

---

## Agent Meshes

**One-line**: Peer-to-peer network where agents communicate directly  
**Reference**: Chapter 42

### Example: Service Discovery Mesh (TypeScript)

```typescript
class AgentMesh {
  private agents = new Map<string, Agent>();
  private capabilities = new Map<string, Set<string>>();
  
  register(name: string, agent: Agent, capabilities: string[]) {
    this.agents.set(name, agent);
    for (const cap of capabilities) {
      if (!this.capabilities.has(cap)) {
        this.capabilities.set(cap, new Set());
      }
      this.capabilities.get(cap)!.add(name);
    }
  }
  
  discover(capability: string): Agent | undefined {
    const names = this.capabilities.get(capability);
    if (!names || names.size === 0) return undefined;
    return this.agents.get(Array.from(names)[0]);
  }
}

// Usage
const mesh = new AgentMesh();
mesh.register('planner-1', new PlanningAgent(llm), ['planning']);
mesh.register('executor-1', new ExecutionAgent(llm), ['execution']);

const planner = mesh.discover('planning');
const result = await planner!.process(task);
```

**See Chapter 42** for full mesh vs partial mesh, service registry patterns, and fault tolerance.

---

## Hybrid Architectures

**One-line**: Combining agent patterns with traditional code and systems  
**Reference**: Chapter 43

### Pattern 1: Agent + Rule Engine

```python
class RuleEngine:
    def evaluate(self, input: dict) -> tuple[bool, str | None]:
        # Clear-cut rules (fast, deterministic)
        if input["amount"] < 100:
            return (True, "Auto-approved")
        if input["risk_score"] > 0.8:
            return (True, "Auto-rejected")
        return (False, None)  # Need AI

class HybridAgent(Agent):
    def __init__(self, llm, rule_engine: RuleEngine):
        self.llm = llm
        self.rules = rule_engine
    
    async def process(self, message: Message) -> Message:
        input_data = parse_message(message)
        
        # Try rules first (fast path)
        handled, result = self.rules.evaluate(input_data)
        if handled:
            return Message(role="assistant", content=result, 
                         metadata={"source": "rules"})
        
        # Fall back to LLM for unclear cases
        llm_result = await self.llm.complete([message])
        llm_result.metadata["source"] = "llm"
        return llm_result
```

### Pattern 2: Agent + Database

```typescript
class DatabaseAugmentedAgent implements Agent {
  constructor(
    private llm: LLM,
    private db: Database
  ) {}
  
  async process(message: Message): Promise<Message> {
    // Step 1: LLM determines what data is needed
    const queryPlan = await this.planQuery(message);
    
    // Step 2: Execute SQL (deterministic, fast)
    const data = await this.db.query(queryPlan.sql);
    
    // Step 3: LLM synthesizes answer from data
    return await this.synthesizeAnswer(message.content, data);
  }
}
```

**See Chapter 43** for 5 hybrid patterns, integration strategies, and cost optimization.

---

## Multi-Pattern Compositions

**One-line**: Combining multiple patterns in sophisticated ways  
**Reference**: Chapter 44

### Composition 1: ReAct + Fallback

```python
from agenkit.patterns import ReActAgent, FallbackAgent

# Primary: GPT-4 with tools
primary = ReActAgent(OpenAILLM(model="gpt-4-turbo"), tools)

# Backup: Claude with same tools
backup = ReActAgent(AnthropicLLM(model="claude-3-5-sonnet-20241022"), tools)

# Compose with fallback
reliable_agent = FallbackAgent([primary, backup])

# If GPT-4 fails, automatically uses Claude
result = await reliable_agent.process(message)
```

### Composition 2: Supervisor + Parallel Workers

```typescript
import { SupervisorAgent, ParallelAgent } from 'agenkit/patterns';

// Workers execute in parallel
const workers = new ParallelAgent([
  new DataCollectionAgent(llm),
  new AnalysisAgent(llm),
  new VisualizationAgent(llm)
]);

// Supervisor coordinates
const supervisor = new SupervisorAgent(llm, workers);

// Supervisor delegates, monitors progress
const result = await supervisor.process({
  role: 'user',
  content: 'Research climate impact on agriculture'
});
```

**See Chapter 44** for 8 common compositions, compatibility rules, and composition patterns.

---

## Distributed Agent Networks

**One-line**: Agents running across multiple machines/regions for scale  
**Reference**: Chapter 46

### Pattern: Message Queue Distribution

```python
import aio_pika  # RabbitMQ

class DistributedAgent:
    def __init__(self, agent: Agent, queue_url: str):
        self.agent = agent
        self.queue_url = queue_url
    
    async def run_worker(self):
        """Run as distributed worker."""
        connection = await aio_pika.connect_robust(self.queue_url)
        channel = await connection.channel()
        queue = await channel.declare_queue("agent_tasks", durable=True)
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    task = Message.from_json(message.body.decode())
                    result = await self.agent.process(task)
                    # Publish result...

# Deploy multiple workers across machines
worker = DistributedAgent(ClassificationAgent(llm), "amqp://queue")
await worker.run_worker()
```

**See Chapter 46** for stateless agent farms, service registries, and multi-region deployments.

---

## Best Practices

### 1. Start Simple, Compose Incrementally

```python
# ❌ WRONG: Too complex at once
agent = TimeoutDecorator(RetryDecorator(FallbackAgent([...])))

# ✅ CORRECT: Build incrementally
agent = Worker()                                    # Step 1
agent = FallbackAgent([agent, Backup()])           # Step 2
agent = RetryDecorator(agent, max_attempts=3)      # Step 3
agent = TimeoutDecorator(agent, timeout_ms=30000)  # Step 4
# Test at each step!
```

### 2. Match Pattern to Scale

| Scale | Pattern |
|-------|---------|
| 1-10 items | Sequential or Parallel |
| 10-100 items | Swarm (Independent) |
| 100-1000 items | Distributed (Queue) |
| 1000+ items | Multi-Region |

### 3. Monitor Composition Depth

```
Depth 1: Single pattern ✅ Simple
Depth 2: Pattern + middleware ✅ Good
Depth 3: Multiple patterns ⚠️ Test carefully
Depth 4+: Compositions of compositions ❌ Refactor
```

### 4. Use Hybrid for Production

Most production systems benefit from hybrid:
- **Rules** for clear cases (fast, cheap)
- **Agents** for unclear cases (flexible)
- **Traditional code** for deterministic ops

---

## Further Reading

- **[Agent Patterns Book](../../agent-patterns-book)**: Chapters 39-49 for comprehensive coverage
- **Getting Started Guides**: See `docs/getting-started/` for the 18 core patterns
- **Examples**: Check `examples/` for production implementations

---

**Version**: v0.50.0  
**Last Updated**: January 28, 2026  
**Reference**: Agent Patterns Book, Chapters 39-49

For help: https://github.com/yourusername/agenkit/issues
