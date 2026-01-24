# Multi-Agent Coordination

Production-ready example demonstrating multiple specialized agents working together through AG-UI protocol.

## 🎯 Overview

This example showcases a coordinator agent that orchestrates multiple specialized agents to handle complex tasks requiring diverse capabilities. Perfect for understanding multi-agent systems and task delegation.

### Key Features

- ✅ **Task Delegation**: Intelligent routing to appropriate agents
- ✅ **Parallel Execution**: Agents work simultaneously
- ✅ **Result Aggregation**: Coherent synthesis of multiple outputs
- ✅ **Real-time Visualization**: See agents coordinate live
- ✅ **4 Specialized Agents**: Research, Calculator, Writer, Analyst
- ✅ **Production Ready**: Comprehensive coordination logic

## 🏗️ Architecture

```
┌────────────────────┐                  ┌─────────────────────────┐
│                    │   WebSocket      │                         │
│  User Interface    │◄─────────────────►│  Coordinator Agent      │
│                    │                  │                         │
│  - Query Input     │                  │  Analyzes query &       │
│  - Agent Status    │                  │  selects agents         │
│  - Results Display │                  │                         │
└────────────────────┘                  └─────────────────────────┘
                                                    │
                                                    │ Delegates to
                                                    ▼
                                        ┌───────────────────────────┐
                                        │   Specialized Agents      │
                                        │   (Parallel Execution)    │
                                        ├───────────────────────────┤
                                        │  • ResearchAgent          │
                                        │  • CalculatorAgent        │
                                        │  • WriterAgent            │
                                        │  • AnalystAgent           │
                                        └───────────────────────────┘
                                                    │
                                                    │ Results
                                                    ▼
                                        ┌───────────────────────────┐
                                        │  Aggregation & Synthesis  │
                                        │  Return to User           │
                                        └───────────────────────────┘
```

## 📋 Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional)

## 🚀 Quick Start

### Docker (Recommended)

```bash
docker-compose up --build
open http://localhost:3000
```

### Local Setup

```bash
# Backend
cd backend
pip install -e ../../../../
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
python -m http.server 3000
```

## 🎮 Usage

### 1. Open Interface

Navigate to http://localhost:3000 and see:
- **Left Panel**: Specialized agents with capabilities
- **Right Panel**: Query input and coordination results
- **Top Bar**: Coordination statistics

### 2. Ask Complex Questions

The coordinator automatically selects appropriate agents:

**Research Queries** → ResearchAgent
- "What is multi-agent coordination?"
- "Research AI agent frameworks"

**Calculations** → CalculatorAgent
- "Calculate 156 + 234 and analyze"
- "What's the average of 10, 20, 30?"

**Content Creation** → WriterAgent
- "Write a report about multi-agent systems"
- "Create a summary of coordination strategies"

**Analysis** → AnalystAgent
- "Analyze and recommend strategy for deployment"
- "What insights can you provide?"

**Complex Queries** → Multiple Agents
- "Research AI trends, calculate growth rate, and write a report"
- "Analyze data and recommend next steps"

### 3. Watch Coordination

As agents work:
- Agent cards highlight in **orange** (working)
- Turn **green** when complete (done)
- Results aggregate in real-time

## 💬 Example Coordination

### Query: "Research AI agent frameworks and write a summary"

**Agents Selected**: ResearchAgent + WriterAgent

**Execution Flow**:
1. Coordinator analyzes query
2. Selects Research + Writer agents
3. Executes both in parallel
4. Aggregates results

**Result**:
```
# Multi-Agent Coordination Results

Query: "Research AI agent frameworks and write a summary"
Agents Involved: research, writer
Total Execution Time: 0.7s

---

## Research Results

Research findings on "AI agent frameworks":
1. Primary Information: Modern AI systems and applications...
2. Key Statistics: 40% market growth, 65% enterprise adoption...
3. Expert Consensus: Substantial benefits for scalability...

Execution time: 0.3s | Confidence: 85%

## Writer Results

# Executive Summary

Based on the query "Research AI agent frameworks", here is a
comprehensive analysis:

## Overview
The subject matter encompasses critical aspects of modern technology...

## Recommendations
- Short-term: Conduct feasibility study
- Medium-term: Scale successful pilots
- Long-term: Full deployment with optimization

Execution time: 0.4s | Word count: 247

---

## Coordination Summary
- Agents Completed: 2/2
- Success Rate: 100%
- Average Confidence: 85%
```

## 🔧 Configuration

### Add New Specialized Agent

1. **Create agent class** in `backend/agent.py`:

```python
class CustomAgent(Agent):
    @property
    def name(self) -> str:
        return "CustomAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["custom_capability"]

    async def process(self, message: Message) -> Message:
        # Your custom logic
        return Message(role="assistant", content="...")
```

2. **Register in coordinator**:

```python
self._agents = {
    ...,
    "custom": CustomAgent(),
}
```

3. **Update selection logic**:

```python
def _select_agents(self, query: str):
    if "custom_keyword" in query:
        selected.append(("custom", self._agents["custom"]))
```

### Modify Coordination Strategy

Edit `backend/agent.py`:

```python
# Sequential execution instead of parallel
async def _execute_coordination(self, query, selected_agents):
    results = []
    for agent_name, agent in selected_agents:
        result = await self._execute_agent(agent_name, agent, message)
        results.append(result)
    return results
```

## 📊 AG-UI Events

### MetadataEvent

```json
{
  "event_type": "metadata",
  "data": {
    "agent_name": "TaskCoordinator",
    "capabilities": ["coordination", "task_delegation", ...],
    "specialized_agents": [
      {"name": "research", "capabilities": ["research", "fact_checking"]},
      {"name": "calculator", "capabilities": ["calculations", "data_analysis"]},
      ...
    ],
    "coordination_strategy": "parallel_execution"
  }
}
```

### TextMessageComplete (Coordinated Result)

```json
{
  "event_type": "text_message_complete",
  "message_id": "msg_123",
  "content": "# Multi-Agent Coordination Results...",
  "metadata": {
    "coordination_count": 5,
    "agents_involved": ["research", "calculator", "writer"],
    "execution_plan": {
      "approach": "parallel_execution",
      "expected_duration": 0.9
    },
    "agent_results": [
      {"agent": "research", "status": "completed", "confidence": 0.85},
      {"agent": "calculator", "status": "completed", "confidence": 0.0},
      {"agent": "writer", "status": "completed", "confidence": 0.0}
    ]
  }
}
```

## 🧪 Testing

### Manual Testing

1. **Single Agent**: Query triggering one agent
2. **Multiple Agents**: Query triggering 2+ agents
3. **All Agents**: Query triggering all 4 agents
4. **Error Handling**: Simulate agent failure
5. **Parallel Execution**: Verify simultaneous execution

### Automated Testing

```bash
cd backend
pytest tests/
```

## 📚 Code Walkthrough

### Coordinator: Agent Selection

```python
def _select_agents(self, query: str) -> list[tuple[str, Agent]]:
    """Select appropriate agents based on query keywords."""
    selected = []

    if any(word in query for word in ["research", "find", "what"]):
        selected.append(("research", self._agents["research"]))

    if any(word in query for word in ["calculate", "number"]) or any(char.isdigit() for char in query):
        selected.append(("calculator", self._agents["calculator"]))

    # ... more selection logic

    return selected
```

### Coordinator: Parallel Execution

```python
async def _execute_coordination(self, query, selected_agents):
    """Execute agents in parallel using asyncio.gather."""
    tasks = []
    for agent_name, agent in selected_agents:
        tasks.append(self._execute_agent(agent_name, agent, message))

    results = await asyncio.gather(*tasks)
    return results
```

### Coordinator: Result Aggregation

```python
def _aggregate_results(self, query, results, plan):
    """Synthesize results from multiple agents."""
    lines = ["# Multi-Agent Coordination Results\n"]

    for result in results:
        if result["status"] == "success":
            lines.append(f"## {result['agent'].title()} Results\n")
            lines.append(result["content"])
            lines.append(f"\nExecution time: {result['execution_time']:.2f}s\n")

    return "\n".join(lines)
```

### Frontend: Agent Status Visualization

```javascript
setAgentStatus(agentName, status) {
    const agentCard = document.getElementById(`agent-${agentName}`);

    if (status === 'working') {
        agentCard.classList.add('active');  // Orange pulse
    } else if (status === 'done') {
        agentCard.classList.add('completed');  // Green
    }
}
```

## 🎨 Customization

### Change Coordination Strategy

**Sequential Execution**:
```python
# Execute one agent at a time
results = []
for agent_name, agent in selected_agents:
    result = await self._execute_agent(agent_name, agent, message)
    results.append(result)
```

**Conditional Execution**:
```python
# Use first agent's result to decide next agent
first_result = await self._execute_agent(...)
if first_result["confidence"] < 0.7:
    second_result = await self._execute_agent(...)
```

### Modify Agent Capabilities

Edit individual agent classes:
```python
class ResearchAgent(Agent):
    async def process(self, message: Message) -> Message:
        # Add custom research logic
        # Integrate real APIs, databases, etc.
        pass
```

## 🐛 Troubleshooting

### Agents Not Activating

- Check query keywords in `_select_agents()`
- Verify frontend `simulateAgentActivity()` logic
- Review browser console for errors

### Results Not Aggregating

```bash
# Check backend logs
docker-compose logs backend

# Look for coordination errors
grep "coordination" logs/backend.log
```

### Agent Selection Issues

- Ensure keywords are lowercase in selection logic
- Check that agents are properly registered in `_agents` dict
- Verify agent initialization in coordinator constructor

## 🚢 Production Deployment

### Scaling Considerations

- **Agent Pool**: Create multiple instances of specialized agents
- **Load Balancing**: Distribute queries across coordinator instances
- **Caching**: Cache common agent responses
- **Monitoring**: Track agent execution times and success rates

### Performance Optimization

```python
# Timeout for slow agents
async with asyncio.timeout(5.0):
    result = await agent.process(message)

# Limit parallel execution
semaphore = asyncio.Semaphore(10)
async with semaphore:
    result = await agent.process(message)
```

## 📈 Metrics & Monitoring

### Key Metrics

- Coordinations per minute
- Average agents per coordination
- Success rate by agent
- Average execution time
- Query complexity distribution

### Logging

Backend logs include:
- Coordination start/complete
- Agent selection decisions
- Individual agent execution times
- Errors and timeouts

## 🔗 Next Steps

Explore related examples:
1. **HITL Approval** - Add human approval to coordination
2. **Tool Dashboard** - Monitor agent tool usage
3. **Customer Support Bot** - Specialized multi-agent support

## 📄 License

Apache 2.0 - See [LICENSE](../../../../LICENSE)

---

**Built with ❤️ using Agenkit**
