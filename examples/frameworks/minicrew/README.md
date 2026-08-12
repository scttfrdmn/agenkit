# MiniCrew - CrewAI Patterns on Agenkit

**~250-300 LOC demonstration of how to build CrewAI-like multi-agent coordination ON TOP of Agenkit primitives.**

## Key Insight

CrewAI's features (roles, tasks, crews) are just **orchestration patterns** for coordinating multiple agents. You don't need a framework - just task management + agent coordination.

## What is MiniCrew?

MiniCrew demonstrates that multi-agent orchestration can be built as **lightweight patterns** using Agenkit's minimal interface:

- **CrewMember**: Role-based agent with specific responsibilities
- **Task**: Unit of work with inputs, outputs, and dependencies
- **Crew**: Orchestrator managing multiple agents
- **ProcessType**: Execution strategy (sequential, hierarchical, parallel)

## Architecture Comparison

### CrewAI Way
```python
from crewai import Agent, Task, Crew

researcher = Agent(role="Researcher", goal="...", backstory="...")
writer = Agent(role="Writer", goal="...", backstory="...")

task1 = Task(description="Research...", agent=researcher)
task2 = Task(description="Write...", agent=writer)

crew = Crew(agents=[researcher, writer], tasks=[task1, task2])
result = crew.kickoff()
```

### MiniCrew Way
```python
from agenkit.adapters.llm import OpenAILLM
from minicrew import CrewMember, Task, Crew, ProcessType

llm = OpenAILLM()

researcher = CrewMember(agent=llm, role="Researcher", goal="...", backstory="...")
writer = CrewMember(agent=llm, role="Writer", goal="...", backstory="...")

tasks = [
    Task(description="Research...", assigned_to="Researcher"),
    Task(description="Write...", assigned_to="Writer"),
]

crew = Crew(members=[researcher, writer], tasks=tasks)
result = await crew.execute()
```

**Differences:**
- ✅ Simpler - Just agents + coordination
- ✅ No framework lock-in - You own the patterns
- ✅ Explicit - Clear what's happening
- ✅ Minimal - ~300 LOC vs thousands in CrewAI

## Core Components

### 1. CrewMember

```python
researcher = CrewMember(
    agent=openai_agent,
    role="Researcher",
    goal="Gather accurate information and validate sources",
    backstory="You are an experienced researcher with a keen eye for detail",
)
```

A crew member is:
- An Agenkit agent with a specific role
- A goal that guides their behavior
- A backstory that shapes their personality

### 2. Task

```python
task = Task(
    description="Research key facts about quantum computing",
    assigned_to="Researcher",
    dependencies=["previous_task"],  # Optional
)
```

A task is:
- Work to be done
- Assignment to a role
- Optional dependencies (must complete first)

### 3. Process Types

#### Sequential
```python
crew = Crew(
    members=[researcher, writer, editor],
    tasks=[research, write, edit],
    process=ProcessType.SEQUENTIAL,
)
```

Tasks execute one after another. Output of each becomes input to next.

**Use when:** Steps depend on previous results.

#### Hierarchical
```python
crew = Crew(
    members=[researcher, writer],
    tasks=[research, write],
    process=ProcessType.HIERARCHICAL,
    manager=manager_agent,
)
```

Manager reviews and approves each task output.

**Use when:** Quality oversight is critical.

#### Parallel
```python
crew = Crew(
    members=[researcher1, researcher2, researcher3],
    tasks=[task_a, task_b, task_c],
    process=ProcessType.PARALLEL,
)
```

Independent tasks run concurrently for speed.

**Use when:** Tasks are independent.

## Examples

### Example 1: Research Team ([01_research_team.py](01_research_team.py))

```python
# Create team
researcher = create_researcher(llm)
writer = create_writer(llm)
editor = create_editor(llm)

# Define workflow
tasks = [
    Task(description="Research topic", assigned_to="Researcher"),
    Task(description="Write article", assigned_to="Writer"),
    Task(description="Edit for clarity", assigned_to="Editor"),
]

# Execute sequentially
crew = Crew(members=[researcher, writer, editor], tasks=tasks)
result = await crew.execute("Topic: AI")
```

**Demonstrates:**
- Sequential workflow (research → write → edit)
- Role-based specialization
- Context passing between tasks

### Example 2: Hierarchical Process ([02_hierarchical_process.py](02_hierarchical_process.py))

```python
# Create team with manager
manager = create_manager(llm)
researcher = create_researcher(llm)
writer = create_writer(llm)

# Manager reviews each output
crew = Crew(
    members=[researcher, writer],
    tasks=[research, write],
    process=ProcessType.HIERARCHICAL,
    manager=manager,
)

result = await crew.execute()
# Each task output is reviewed by manager
```

**Demonstrates:**
- Manager oversight and approval
- Quality assurance workflow
- Task delegation

### Example 3: Parallel Processing ([03_parallel_processing.py](03_parallel_processing.py))

```python
# Create specialist team
tech_researcher = CrewMember(agent=llm, role="Tech Researcher", ...)
market_researcher = CrewMember(agent=llm, role="Market Researcher", ...)
competitor_analyst = CrewMember(agent=llm, role="Competitor Analyst", ...)

# Independent research tasks
tasks = [
    Task(description="Research tech specs", assigned_to="Tech Researcher"),
    Task(description="Analyze market", assigned_to="Market Researcher"),
    Task(description="Study competitors", assigned_to="Competitor Analyst"),
]

# Execute in parallel for speed
crew = Crew(members=[...], tasks=tasks, process=ProcessType.PARALLEL)
result = await crew.execute()
```

**Demonstrates:**
- Concurrent execution
- Speed benefits (~3x faster)
- Result aggregation
- Dependency-aware scheduling

## Common Role Patterns

MiniCrew provides helpers for common roles:

```python
researcher = create_researcher(llm)
writer = create_writer(llm)
editor = create_editor(llm)
manager = create_manager(llm)
```

Or create custom roles:

```python
data_analyst = CrewMember(
    agent=llm,
    role="Data Analyst",
    goal="Extract insights from data",
    backstory="Expert in statistical analysis with 10 years experience",
)
```

## Task Dependencies

Tasks can depend on other tasks:

```python
task_a = Task(description="Research", assigned_to="Researcher")
task_b = Task(description="Analyze", assigned_to="Analyst")
task_c = Task(
    description="Synthesize",
    assigned_to="Writer",
    dependencies=[task_a.description, task_b.description],
)
```

**Parallel execution** respects dependencies:
- Phase 1: A and B run concurrently
- Phase 2: C runs after A and B complete

## Performance

### Sequential
- **Latency**: Sum of all task times
- **Use when**: Tasks depend on previous results

### Parallel
- **Latency**: Longest task time (not sum!)
- **Speedup**: ~3x for 3 independent tasks
- **Use when**: Tasks are independent

### Hierarchical
- **Latency**: Task time + review time
- **Use when**: Quality oversight is critical

## Why MiniCrew?

### 1. **Educational**
Shows that "multi-agent frameworks" are just coordination patterns. You can build them when needed.

### 2. **No Lock-In**
You own the code. Extend it, modify it, or replace it as your needs evolve.

### 3. **Transparent**
~300 LOC you can read and understand in an afternoon. No magic, no surprises.

### 4. **Production-Ready**
These patterns are used in production systems. They're not toys.

## When to Use MiniCrew Patterns

✅ **Use these patterns when:**
- You need multi-agent coordination
- You want role-based specialization
- You need sequential, hierarchical, or parallel execution
- You value code clarity over framework features

❌ **Use CrewAI when:**
- You need their pre-built integrations
- You want their extensive tooling
- You need CrewAI-specific features
- Team is already familiar with it

## Migration from CrewAI

### Agents → CrewMembers
```python
# CrewAI
from crewai import Agent

agent = Agent(role="Researcher", goal="...", backstory="...")

# MiniCrew
from minicrew import CrewMember

member = CrewMember(agent=llm, role="Researcher", goal="...", backstory="...")
```

### Tasks
```python
# CrewAI
task = Task(description="...", agent=agent)

# MiniCrew
task = Task(description="...", assigned_to="Researcher")
```

### Crews
```python
# CrewAI
crew = Crew(agents=[agent1, agent2], tasks=[task1, task2])
result = crew.kickoff()

# MiniCrew
crew = Crew(members=[member1, member2], tasks=[task1, task2])
result = await crew.execute()
```

**Same patterns, simpler implementation.**

## Files

- `minicrew.py` - Core implementation (~300 LOC)
- `01_research_team.py` - Sequential workflow (~200 LOC)
- `02_hierarchical_process.py` - Manager coordination (~200 LOC)
- `03_parallel_processing.py` - Concurrent execution (~200 LOC)
- `README.md` - This file

**Total: ~900 LOC** (including examples)

## Running Examples

```bash
# Set API key
export OPENAI_API_KEY=your-key-here

# Run examples
python 01_research_team.py
python 02_hierarchical_process.py
python 03_parallel_processing.py
```

## Key Takeaways

1. **Frameworks are patterns** - Multi-agent coordination is just task orchestration
2. **Roles are prompts** - CrewMember is just an agent with a system message
3. **Crews are orchestrators** - Simple coordination logic, not framework magic
4. **You own it** - Extend, modify, or replace as needed

## Next Steps

- Try the examples
- Read the source (`minicrew.py`)
- Build your own crew patterns
- Compare with CrewAI's implementation

**Remember:** This is a demonstration, not a production framework. Use these patterns as inspiration for building exactly what you need.
