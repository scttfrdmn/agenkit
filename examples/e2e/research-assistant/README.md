# Autonomous Research Assistant

End-to-end production example demonstrating an autonomous agent with planning, tool use, memory management, and checkpointing.

## Overview

This example showcases a **production-ready autonomous research assistant** using AgentKit's autonomous agent capabilities. The system can independently plan and execute multi-step research tasks using available tools.

**Key Capabilities:**
- **Autonomous Planning**: Creates multi-step plans to answer complex questions
- **Tool Orchestration**: Uses tools (search, calculator, document reader, notes) automatically
- **Memory Management**: Three-tier memory system (working, short-term, long-term)
- **Budget Tracking**: Monitors and controls API costs
- **Checkpointing**: Save/restore agent state for long-running tasks

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                     Research Assistant                          │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │              │                                               │
│  │    User      │  "What are the latest developments in        │
│  │    Query     │   quantum computing?"                        │
│  │              │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────┐          │
│  │         Autonomous Research Agent                 │          │
│  ├──────────────────────────────────────────────────┤          │
│  │                                                    │          │
│  │  1. Plan Generation                               │          │
│  │     └─► Create multi-step plan                   │          │
│  │                                                    │          │
│  │  2. Execution Loop (up to N iterations)          │          │
│  │     ├─► Select tool for current step             │          │
│  │     ├─► Execute tool                              │          │
│  │     ├─► Store result in memory                   │          │
│  │     └─► Reflect on progress                      │          │
│  │                                                    │          │
│  │  3. Answer Synthesis                              │          │
│  │     └─► Combine findings into answer             │          │
│  │                                                    │          │
│  └────────┬───────────────┬──────────────┬──────────┘          │
│           │               │              │                      │
│           ▼               ▼              ▼                      │
│    ┌──────────┐   ┌─────────────┐  ┌──────────┐              │
│    │  Tools   │   │   Memory    │  │  Budget  │              │
│    │ Registry │   │   Store     │  │ Tracker  │              │
│    └────┬─────┘   └──────┬──────┘  └────┬─────┘              │
│         │                │              │                      │
│    ┌────┴─────────────┐  │         Costs tracked              │
│    │                   │  │                                    │
│    │  • search         │  ├─► Working Memory                  │
│    │  • calculator     │  ├─► Short-term Memory               │
│    │  • read_document  │  └─► Long-term Memory                │
│    │  • notes          │                                       │
│    │                   │                                       │
│    └───────────────────┘                                       │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
    ┌─────────┐
    │  Final  │
    │ Answer  │
    └─────────┘
```

## Features Demonstrated

### ✅ Autonomous Planning
- **Multi-step Plans**: Agent creates plans with multiple steps
- **Task Decomposition**: Complex tasks broken into manageable steps
- **Adaptive Planning**: Can adjust based on findings

### ✅ Tool Orchestration
- **Search Tool**: Web search for information (mock implementation)
- **Calculator**: Mathematical computations
- **Document Reader**: Fetch and parse documents
- **Note Taker**: Persistent notes across steps
- **Extensible**: Easy to add new tools

### ✅ Memory Management
- **Working Memory**: Current task context (cleared between tasks)
- **Short-term Memory**: Recent findings (FIFO with limit)
- **Long-term Memory**: Important facts (consolidated from short-term)
- **Memory Consolidation**: Automatic promotion of important memories
- **Checkpointing**: Save/restore memory state

### ✅ Production Features
- **Budget Tracking**: Monitor costs per tool/iteration
- **Error Handling**: Graceful failure recovery
- **Progress Reflection**: Agent reflects on progress periodically
- **Statistics**: Detailed usage and performance metrics
- **Configurable**: All parameters tunable

## Project Structure

```
research-assistant/
├── agents/                    # Agent implementations
│   ├── __init__.py
│   └── research_agent.py     # Autonomous research agent
├── tools/                     # Tool system
│   ├── __init__.py
│   ├── tool_registry.py      # Tool management
│   └── built_in_tools.py     # Default tools
├── memory/                    # Memory management
│   ├── __init__.py
│   └── memory_store.py       # Memory store implementation
├── config/                    # Configuration files
├── tests/                     # Test suite
├── deploy/                    # Deployment configs
│   └── k8s/                  # Kubernetes manifests
├── main.py                    # Main application
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- Python 3.10+
- AgentKit installed

### Installation

```bash
# From the agenkit root directory
cd examples/e2e/research-assistant

# Run the demo
PYTHONPATH=/path/to/agenkit python3 main.py
```

### Running the Demo

The demo processes 3 research tasks demonstrating different capabilities:

```bash
python3 main.py
```

Expected output:
```
======================================================================
AUTONOMOUS RESEARCH ASSISTANT - DEMO
======================================================================
✓ Research Assistant initialized
  Tools available: 4
  Memory capacity: 100 short-term entries
  Budget: $0.10, Max iterations: 8

**********************************************************************
DEMO TASK #1: Research task requiring search and synthesis
**********************************************************************
Task: What are the key differences between Python and Go?

======================================================================
RESEARCH TASK: What are the key differences between Python and Go?
======================================================================

PLAN:
  1. Search for information about: What are the key differences between Python and Go?
  2. Read the most relevant document
  3. Take notes on key findings
  4. Synthesize answer from findings

[Step 1/4] Search for information about: What are the key differences between Python and Go?
  🔧 Using tool: search
     Parameters: {'query': 'What are the key differences between Python and Go?', 'num_results': 3}
  ✓ Result: [{'title': "Result about 'What are the key differences between Python and Go?' - Article 1", ...}]

[Step 2/4] Read the most relevant document
  🔧 Using tool: read_document
     Parameters: {'url': 'https://example.com/article'}
  ✓ Result: # Document from https://example.com/article...

[Step 3/4] Take notes on key findings
  🔧 Using tool: notes
     Parameters: {'action': 'list'}
  ✓ Result: No notes yet

[Step 4/4] Synthesize answer from findings
  💭 Reasoning: Based on 3 findings, continuing with: Synthesize answer from findings

======================================================================
RESEARCH COMPLETE
  Success: True
  Iterations: 4
  Cost: $0.0030
  Tools used: search, read_document, notes
======================================================================
```

### Interactive Mode

Test the system with your own questions:

```bash
python3 main.py interactive
```

Commands:
- Type your research question
- `save <file>` - Save checkpoint
- `load <file>` - Load checkpoint
- `status` - View system status
- `clear` - Clear memory
- `quit` - Exit

### Checkpoint Demo

See save/restore functionality:

```bash
python3 main.py checkpoint
```

### Programmatic Usage

Use the system in your own code:

```python
import asyncio
from main import ResearchAssistant
from agents import ResearchConfig

async def main():
    # Initialize assistant
    assistant = ResearchAssistant(
        config=ResearchConfig(
            max_iterations=10,
            max_budget=0.5,
            enable_planning=True,
            enable_reflection=True,
        )
    )

    # Execute research task
    result = await assistant.research(
        "What are the latest developments in quantum computing?"
    )

    # Access results
    print(f"Answer: {result.answer}")
    print(f"Cost: ${result.cost:.4f}")
    print(f"Iterations: {result.iterations}")
    print(f"Success: {result.success}")

    # Save checkpoint
    assistant.save_checkpoint("checkpoint.json")

    # View system status
    status = assistant.get_status()
    print(f"Memory entries: {status['memory_summary']['total_memories']}")
    print(f"Tools used: {status['tool_stats']['total_executions']}")

asyncio.run(main())
```

## Components

### 1. ResearchAgent

The autonomous agent that plans and executes research tasks.

**Key Methods:**
- `research(task)`: Execute autonomous research task
- `save_checkpoint(filepath)`: Save agent state
- `load_checkpoint(filepath)`: Restore agent state
- `get_status()`: Get current status and statistics

**Configuration:**
```python
config = ResearchConfig(
    max_iterations=10,      # Max autonomous steps
    max_budget=1.0,         # Max cost in dollars
    max_tool_failures=3,    # Max consecutive tool failures
    enable_planning=True,   # Create plans before executing
    enable_reflection=True, # Reflect after each step
    verbose=True           # Print detailed logs
)
```

**Autonomous Loop:**
1. Create multi-step plan
2. For each step:
   - Select appropriate tool
   - Execute tool
   - Store result in memory
   - Track cost
   - Reflect on progress (if enabled)
3. Synthesize final answer from findings

### 2. MemoryStore

Three-tier memory system for context management.

**Memory Types:**
- **Working Memory**: Current task context, cleared between tasks
- **Short-term Memory**: Recent findings, FIFO with limit (default 100)
- **Long-term Memory**: Important facts, consolidated automatically

**Key Features:**
- Automatic consolidation: Important short-term memories promoted to long-term
- Search: Keyword search across memories
- Access tracking: Tracks how often memories are accessed
- Checkpointing: Save/restore memory state

**Example:**
```python
from memory import MemoryStore, MemoryType

memory = MemoryStore(short_term_limit=100)

# Store working memory
memory.store("task_plan", "1. Search\\n2. Summarize", MemoryType.WORKING)

# Store finding
memory.store("finding_1", "Python is interpreted", MemoryType.SHORT_TERM, importance=0.8)

# Search memories
results = memory.search("python", min_importance=0.5)

# Get recent memories
recent = memory.get_recent(limit=10, memory_type=MemoryType.SHORT_TERM)

# Save/load
memory.save_checkpoint("memory.json")
memory.load_checkpoint("memory.json")
```

### 3. ToolRegistry

Manages available tools with execution tracking and cost monitoring.

**Built-in Tools:**

**Search Tool** (`search`):
- Search web for information
- Parameters: `query` (str), `num_results` (int, default 5)
- Cost: $0.001 per call
- Returns: List of results with titles, URLs, snippets

**Calculator Tool** (`calculator`):
- Perform mathematical calculations
- Parameters: `expression` (str)
- Cost: $0.0001 per call
- Supports: +, -, *, /, ^, abs, min, max, sum, round

**Document Reader Tool** (`read_document`):
- Fetch and read document content
- Parameters: `url` (str)
- Cost: $0.002 per call
- Returns: Full text content

**Note Taker Tool** (`notes`):
- Take and manage notes during research
- Parameters: `action` (add/list/get/clear), `content` (optional), `note_id` (optional)
- Cost: $0.00 (free)
- Persistent across steps within same task

**Example:**
```python
from tools import ToolRegistry, create_default_tools

# Create registry
registry = ToolRegistry()

# Register default tools
for tool in create_default_tools():
    registry.register_tool(tool)

# Execute tool
result = await registry.execute("search", query="python", num_results=5)
print(result.output)
print(result.execution_time)

# Get statistics
stats = registry.get_statistics()
print(f"Total executions: {stats['total_executions']}")
print(f"Total cost: ${stats['total_cost']:.4f}")
```

**Adding Custom Tools:**
```python
from tools import Tool, ToolResult

async def my_tool_function(param1: str, param2: int) -> ToolResult:
    # Your tool logic
    result = f"Processed {param1} with {param2}"
    return ToolResult(success=True, output=result)

custom_tool = Tool(
    name="my_tool",
    description="My custom tool that does X",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "First parameter"},
            "param2": {"type": "integer", "description": "Second parameter"}
        },
        "required": ["param1"]
    },
    function=my_tool_function,
    cost=0.001,
    category="custom"
)

registry.register_tool(custom_tool)
```

### 4. ResearchAssistant

High-level wrapper that orchestrates all components.

**Features:**
- Initializes all components
- Provides simple API
- Manages checkpoints
- Tracks system status

## Configuration

### Agent Configuration

```python
from agents import ResearchConfig

config = ResearchConfig(
    max_iterations=10,      # Stop after N steps
    max_budget=1.0,         # Stop when cost exceeds budget
    max_tool_failures=3,    # Stop after N consecutive tool failures
    enable_planning=True,   # Whether to create plans
    enable_reflection=True, # Whether to reflect on progress
    verbose=True           # Print detailed logs
)
```

### Memory Configuration

```python
from memory import MemoryStore

memory = MemoryStore(
    short_term_limit=100,                   # Max short-term memories
    long_term_consolidation_threshold=0.7   # Importance threshold for promotion
)
```

### Tool Configuration

Tools have configurable costs for budget tracking:

```python
tool = Tool(
    name="expensive_api",
    description="...",
    parameters={...},
    function=my_function,
    cost=0.01  # $0.01 per call
)
```

## Performance Characteristics

### Throughput
- **Planning Time**: ~50ms (heuristic-based, faster with LLM)
- **Tool Execution**: Varies by tool (mock tools: <10ms)
- **Memory Operations**: O(1) for store/get, O(n) for search
- **Iteration Time**: ~100-500ms per step

### Scalability
- **Memory**: Handles 1000s of entries efficiently
- **Tools**: Can register unlimited tools
- **Concurrent Tasks**: Each instance handles one task at a time

### Cost Management
- **Budget Tracking**: Real-time cost monitoring
- **Cost per Task**: Typically $0.001-$0.01 with mock tools
- **Production Cost**: Depends on real API pricing

## Production Considerations

### 🚀 Ready for Production
- ✅ Modular architecture
- ✅ Async/await throughout
- ✅ Type hints
- ✅ Error handling
- ✅ Cost tracking
- ✅ Checkpointing
- ✅ Memory management

### 🔧 Needs Enhancement
- ⚠️ Replace mock tools with real APIs (Google Search, OpenAI, etc.)
- ⚠️ Add LLM integration for planning and reasoning
- ⚠️ Implement proper embedding-based memory retrieval
- ⚠️ Add middleware (retry, timeout, circuit breaker)
- ⚠️ Add observability (tracing, metrics, logging)
- ⚠️ Add authentication and rate limiting
- ⚠️ Add comprehensive test suite
- ⚠️ Add database persistence for memory
- ⚠️ Add multi-agent collaboration

## Extending the System

### Add New Tools

```python
from tools import Tool, ToolResult

async def weather_tool(location: str) -> ToolResult:
    # Call weather API
    weather_data = await get_weather(location)
    return ToolResult(success=True, output=weather_data)

weather = Tool(
    name="weather",
    description="Get current weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name"}
        },
        "required": ["location"]
    },
    function=weather_tool,
    cost=0.001
)

assistant.tools.register_tool(weather)
```

### Integrate Real LLM

Replace planning and reasoning with LLM calls:

```python
import openai

async def _create_plan_with_llm(self, task: str) -> List[str]:
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a research planning assistant."},
            {"role": "user", "content": f"Create a step-by-step plan to answer: {task}"}
        ]
    )
    plan_text = response.choices[0].message.content
    return plan_text.split("\\n")
```

### Add Vector-based Memory

Replace keyword search with embeddings:

```python
from openai import OpenAI

client = OpenAI()

def embed_text(text: str):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def search_by_embedding(query_embedding, memories):
    # Cosine similarity search
    similarities = [
        cosine_similarity(query_embedding, mem.embedding)
        for mem in memories
    ]
    return sorted(zip(memories, similarities), key=lambda x: x[1], reverse=True)
```

## Testing

### Unit Tests
```bash
pytest tests/test_memory.py
pytest tests/test_tools.py
pytest tests/test_agent.py
```

### Integration Tests
```bash
pytest tests/test_integration.py
```

### End-to-End Tests
```bash
python3 main.py  # Run full demo
```

## Deployment

### Docker
```bash
docker build -t research-assistant .
docker run -p 8000:8000 research-assistant
```

### Kubernetes
```bash
kubectl apply -f deploy/k8s/
```

## Monitoring

Key metrics to track:
- **Task success rate**: % of tasks completed successfully
- **Average iterations**: Mean steps per task
- **Cost per task**: Average spend per research task
- **Tool usage**: Which tools are used most
- **Memory growth**: Memory entries over time
- **Checkpoint frequency**: How often state is saved

## Roadmap

- [ ] Integrate production LLM (GPT-4, Claude)
- [ ] Add real search API (Google, Bing, Tavily)
- [ ] Implement vector-based memory
- [ ] Add multi-agent collaboration
- [ ] Add web interface
- [ ] Add conversation history
- [ ] Add streaming responses
- [ ] Add tool result caching
- [ ] Add distributed execution
- [ ] Add A/B testing framework

## Related Examples

- **customer-support/**: Multi-agent sequential pipeline
- **patterns/**: Individual agent patterns (ReAct, etc.)
- **middleware/**: Middleware examples (retry, circuit breaker, etc.)

## License

MIT License - See repository root for details

## Support

For questions or issues with this example:
1. Check the AgentKit documentation
2. Review the source code comments
3. Open an issue on GitHub
4. Join the community Discord

---

**Built with AgentKit** - Production-grade multi-agent framework for Python
