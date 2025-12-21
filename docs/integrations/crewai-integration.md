# Bidirectional CrewAI + Agenkit Integration

Complete guide for using Agenkit with CrewAI in both directions.

## Overview

This guide shows **bidirectional** integration between CrewAI and Agenkit:

1. **Agenkit → CrewAI**: Use Agenkit agents as CrewAI crew members
2. **CrewAI → Agenkit**: Use CrewAI crews within Agenkit workflows
3. **Hybrid Architecture**: Combine role-based and pattern-based agents

> **Note**: For migrating entirely from CrewAI to Agenkit, see [Migration Guide](../migrations/crewai-to-agenkit.md).

---

## 1. Agenkit Agent as CrewAI Crew Member

Use Agenkit agents as specialized crew members in CrewAI teams.

### Basic Integration

```python
from crewai import Agent as CrewAgent, Task, Crew
from agenkit import Agent as AgenkitAgent, Message
import asyncio

class AgenkitCrewMember(CrewAgent):
    """Wrap Agenkit agent as CrewAI crew member."""

    def __init__(self, agenkit_agent: AgenkitAgent, role: str, goal: str, backstory: str):
        self.agenkit_agent = agenkit_agent

        # Initialize CrewAI agent
        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True,
            allow_delegation=False
        )

    def execute_task(self, task: Task) -> str:
        """Execute task using Agenkit agent."""
        # Convert CrewAI task to Agenkit message
        message = Message(
            role="user",
            content=task.description,
            metadata={
                "task_id": task.id,
                "expected_output": task.expected_output
            }
        )

        # Process with Agenkit agent
        response = asyncio.run(self.agenkit_agent.process(message))

        return response.content

# Example: Agenkit agents in CrewAI crew
from agenkit.patterns import ReActAgent, AnalysisAgent
from agenkit.adapters import OpenAIAdapter

llm = OpenAIAdapter(api_key="key", model="gpt-4")

# Create Agenkit agents
researcher_agent = ReActAgent(llm=llm)
analyst_agent = AnalysisAgent(llm=llm)

# Wrap as CrewAI crew members
researcher = AgenkitCrewMember(
    agenkit_agent=researcher_agent,
    role="Researcher",
    goal="Conduct thorough research on topics",
    backstory="Expert researcher with deep analytical skills"
)

analyst = AgenkitCrewMember(
    agenkit_agent=analyst_agent,
    role="Data Analyst",
    goal="Analyze data and provide insights",
    backstory="Experienced data analyst with statistical expertise"
)

# Create tasks
research_task = Task(
    description="Research the latest AI trends",
    agent=researcher,
    expected_output="Comprehensive research report"
)

analysis_task = Task(
    description="Analyze the research findings",
    agent=analyst,
    expected_output="Data-driven insights"
)

# Create crew with Agenkit agents
crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analysis_task],
    verbose=True
)

# Execute
result = crew.kickoff()
print(result)
```

### With Agenkit Middleware

```python
from agenkit.middleware import RetryMiddleware, CachingMiddleware

class AgenkitCrewMemberWithMiddleware(CrewAgent):
    """CrewAI member with Agenkit middleware benefits."""

    def __init__(self, agenkit_agent: AgenkitAgent, role: str, goal: str, backstory: str):
        # Wrap Agenkit agent with middleware
        agent = RetryMiddleware(agenkit_agent, max_retries=3)
        agent = CachingMiddleware(agent, ttl=3600)

        self.agenkit_agent = agent

        super().__init__(
            role=role,
            goal=goal,
            backstory=backstory,
            verbose=True
        )

    def execute_task(self, task: Task) -> str:
        message = Message(role="user", content=task.description)
        response = asyncio.run(self.agenkit_agent.process(message))
        return response.content

# Now your CrewAI agents have:
# ✅ Automatic retries on failure
# ✅ Response caching for efficiency
# ✅ All Agenkit middleware benefits!
```

---

## 2. CrewAI Crew in Agenkit Workflow

Use CrewAI crews as components within Agenkit orchestration.

### CrewAI as Agenkit Agent

```python
from crewai import Crew, Agent as CrewAgent, Task
from agenkit import Agent, Message

class CrewAIAgent(Agent):
    """Wrap CrewAI crew as Agenkit agent."""

    def __init__(self, crew: Crew):
        self.crew = crew

    @property
    def name(self) -> str:
        return "crewai-crew"

    @property
    def capabilities(self) -> list[str]:
        return ["team-collaboration", "role-based-execution"]

    async def process(self, message: Message) -> Message:
        """Execute CrewAI crew and return result."""
        # Extract task from message
        task_description = message.content

        # Update crew tasks
        if self.crew.tasks:
            self.crew.tasks[0].description = task_description

        # Execute crew
        result = self.crew.kickoff()

        return Message(
            role="assistant",
            content=str(result),
            metadata={
                "crew_size": len(self.crew.agents),
                "tasks_executed": len(self.crew.tasks)
            }
        )

# Create CrewAI crew
researcher = CrewAgent(
    role="Researcher",
    goal="Research topics",
    backstory="Expert researcher"
)

writer = CrewAgent(
    role="Writer",
    goal="Write content",
    backstory="Skilled writer"
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[
        Task(description="Research AI", agent=researcher),
        Task(description="Write article", agent=writer)
    ]
)

# Wrap as Agenkit agent
crewai_agent = CrewAIAgent(crew)

# Use in Agenkit patterns
from agenkit.patterns import SequentialAgent
from agenkit.middleware import TracingMiddleware

# Add Agenkit patterns on top of CrewAI
pipeline = SequentialAgent([
    preprocessing_agent,  # Agenkit agent
    crewai_agent,         # CrewAI crew
    postprocessing_agent  # Agenkit agent
])

# Add observability
pipeline = TracingMiddleware(pipeline, service_name="hybrid-crew")

# Execute
response = await pipeline.process(Message(
    role="user",
    content="Research and write about quantum computing"
))
```

### Dynamic Crew Creation

```python
class DynamicCrewAgent(Agent):
    """Agenkit agent that creates CrewAI crews dynamically."""

    def __init__(self, agent_factory):
        self.agent_factory = agent_factory

    @property
    def name(self) -> str:
        return "dynamic-crew"

    async def process(self, message: Message) -> Message:
        # Parse requirements from message
        required_roles = self._extract_roles(message.content)

        # Create crew dynamically
        agents = []
        tasks = []

        for i, role in enumerate(required_roles):
            agent = self.agent_factory.create_agent(role)
            agents.append(agent)

            task = Task(
                description=f"Execute {role} responsibilities",
                agent=agent
            )
            tasks.append(task)

        crew = Crew(agents=agents, tasks=tasks)

        # Execute
        result = crew.kickoff()

        return Message(
            role="assistant",
            content=str(result),
            metadata={"roles_used": required_roles}
        )

    def _extract_roles(self, content: str) -> list[str]:
        """Extract required roles from content."""
        # Simplified - would use LLM in practice
        roles = []
        if "research" in content.lower():
            roles.append("Researcher")
        if "write" in content.lower():
            roles.append("Writer")
        if "analyze" in content.lower():
            roles.append("Analyst")
        return roles

# Usage
agent = DynamicCrewAgent(agent_factory)
response = await agent.process(Message(
    role="user",
    content="I need to research, analyze, and write about AI"
))
# Automatically creates crew with Researcher, Analyst, Writer!
```

---

## 3. Hybrid Architectures

### Pattern: CrewAI for Teams, Agenkit for Orchestration

```python
from agenkit.patterns import OrchestrationAgent

class HybridTeamOrchestrator(Agent):
    """
    Use CrewAI for specialized teams,
    Agenkit for high-level orchestration.
    """

    def __init__(self, teams: dict[str, Crew], orchestrator: OrchestrationAgent):
        self.teams = teams
        self.orchestrator = orchestrator

    @property
    def name(self) -> str:
        return "hybrid-team-orchestrator"

    async def process(self, message: Message) -> Message:
        # 1. Use Agenkit orchestrator to plan
        plan_msg = Message(
            role="user",
            content=f"Create execution plan for: {message.content}"
        )
        plan = await self.orchestrator.process(plan_msg)

        # 2. Determine which CrewAI team to use
        team_name = self._select_team(plan.content)

        # 3. Execute with appropriate team
        if team_name in self.teams:
            crew = self.teams[team_name]
            result = crew.kickoff()
        else:
            result = "No suitable team found"

        return Message(
            role="assistant",
            content=str(result),
            metadata={
                "plan": plan.content,
                "team_used": team_name
            }
        )

    def _select_team(self, plan: str) -> str:
        # Select team based on plan
        if "content" in plan.lower():
            return "content_team"
        elif "technical" in plan.lower():
            return "engineering_team"
        return "general_team"

# Create specialized teams
content_team = Crew(
    agents=[writer, editor, seo_specialist],
    tasks=[writing_task, editing_task, seo_task]
)

engineering_team = Crew(
    agents=[architect, developer, tester],
    tasks=[design_task, code_task, test_task]
)

# Create hybrid system
orchestrator = OrchestrationAgent(llm=llm_adapter)
hybrid = HybridTeamOrchestrator(
    teams={
        "content_team": content_team,
        "engineering_team": engineering_team
    },
    orchestrator=orchestrator
)

# Execute
response = await hybrid.process(Message(
    role="user",
    content="Build a new feature for our app"
))
# Agenkit plans, CrewAI executes with appropriate team!
```

### Pattern: Agenkit for Tools, CrewAI for Coordination

```python
class HybridToolCoordination:
    """CrewAI coordinates, Agenkit provides tools."""

    def __init__(self, agenkit_tools: dict[str, Agent]):
        self.tools = agenkit_tools

        # Create CrewAI agents that use Agenkit tools
        self.coordinator = CrewAgent(
            role="Coordinator",
            goal="Coordinate tool usage",
            backstory="Expert coordinator",
            tools=self._wrap_tools_for_crewai()
        )

    def _wrap_tools_for_crewai(self):
        """Wrap Agenkit agents as CrewAI tools."""
        from crewai_tools import BaseTool

        tools = []
        for name, agent in self.tools.items():
            tool = type(
                f"AgenkitTool_{name}",
                (BaseTool,),
                {
                    "name": name,
                    "description": f"Agenkit {name} tool",
                    "_run": lambda query, ag=agent: asyncio.run(
                        ag.process(Message(role="user", content=query))
                    ).content
                }
            )()
            tools.append(tool)

        return tools

    def execute(self, task_description: str) -> str:
        """Execute task using hybrid system."""
        task = Task(
            description=task_description,
            agent=self.coordinator
        )

        crew = Crew(
            agents=[self.coordinator],
            tasks=[task]
        )

        return crew.kickoff()

# Create Agenkit tools
tools = {
    "search": SearchAgent(llm_adapter),
    "calculate": CalculatorAgent(),
    "analyze": AnalysisAgent(llm_adapter),
}

# Create hybrid system
hybrid = HybridToolCoordination(tools)

# CrewAI coordinates, Agenkit tools execute!
result = hybrid.execute("Search for data, calculate statistics, and analyze results")
```

---

## 4. When to Use Each Approach

### Use Agenkit → CrewAI When:
- You have existing Agenkit agents to reuse
- You want CrewAI's role-based collaboration
- You need Agenkit's middleware in CrewAI context
- Gradual migration to CrewAI

### Use CrewAI → Agenkit When:
- You want Agenkit's orchestration patterns
- You need cross-language support
- You want better observability
- Existing CrewAI crews to integrate

### Use Hybrid Architecture When:
- Large teams with specialized roles (CrewAI)
- Complex orchestration (Agenkit)
- Best of both frameworks
- Enterprise-scale applications

---

## 5. Performance Comparison

| Feature | CrewAI Only | Agenkit Only | Hybrid |
|---------|-------------|--------------|--------|
| **Role-based** | ✅ | ⚠️ (manual) | ✅ |
| **Middleware** | ❌ | ✅ | ✅ |
| **Delegation** | ✅ | ⚠️ (manual) | ✅ |
| **Observability** | ⚠️ (basic) | ✅ | ✅ |
| **Cross-language** | ❌ | ✅ | ✅ |
| **Team Management** | ✅ | ⚠️ (manual) | ✅ |

---

## 6. Migration Strategy

### Gradual Migration

```python
# Phase 1: Add Agenkit agents to CrewAI
crew_with_agenkit = Crew(
    agents=[AgenkitCrewMember(my_agent, "Role", "Goal", "Story")],
    tasks=[task]
)

# Phase 2: Use CrewAI in Agenkit workflows
agenkit_with_crew = SequentialAgent([
    preprocessing,
    CrewAIAgent(crew),
    postprocessing
])

# Phase 3: Hybrid architecture
hybrid = HybridTeamOrchestrator(crews, orchestrator)

# Phase 4: Full Agenkit (if desired)
pure_agenkit = MultiagentAgent(...)
```

---

## 7. Complete Example

```python
"""
Production hybrid system:
- CrewAI for specialized teams with clear roles
- Agenkit for orchestration, middleware, and observability
"""

from crewai import Agent as CrewAgent, Task, Crew
from agenkit.patterns import OrchestrationAgent
from agenkit.middleware import TracingMiddleware, RetryMiddleware

class ProductionHybridCrewSystem:
    """Production-ready CrewAI + Agenkit system."""

    def __init__(self):
        # Create specialized CrewAI teams
        self.content_crew = self._create_content_crew()
        self.technical_crew = self._create_technical_crew()

        # Create Agenkit orchestrator
        llm = OpenAIAdapter(api_key="key", model="gpt-4")
        orchestrator = OrchestrationAgent(llm=llm)

        # Add Agenkit middleware
        orchestrator = TracingMiddleware(orchestrator, service_name="hybrid-crew")
        orchestrator = RetryMiddleware(orchestrator, max_retries=3)

        self.orchestrator = orchestrator

    def _create_content_crew(self) -> Crew:
        """Create content creation team."""
        writer = CrewAgent(
            role="Content Writer",
            goal="Write engaging content",
            backstory="Professional writer with 10 years experience"
        )

        editor = CrewAgent(
            role="Editor",
            goal="Edit and polish content",
            backstory="Detail-oriented editor"
        )

        return Crew(
            agents=[writer, editor],
            tasks=[
                Task(description="Write article", agent=writer),
                Task(description="Edit article", agent=editor)
            ]
        )

    def _create_technical_crew(self) -> Crew:
        """Create technical team."""
        architect = CrewAgent(
            role="Software Architect",
            goal="Design system architecture",
            backstory="Senior architect"
        )

        developer = CrewAgent(
            role="Developer",
            goal="Implement features",
            backstory="Full-stack developer"
        )

        return Crew(
            agents=[architect, developer],
            tasks=[
                Task(description="Design system", agent=architect),
                Task(description="Implement features", agent=developer)
            ]
        )

    async def execute(self, task: str) -> str:
        """Execute task using hybrid system."""
        # 1. Use Agenkit to plan
        plan_msg = Message(role="user", content=f"Plan: {task}")
        plan = await self.orchestrator.process(plan_msg)

        # 2. Select appropriate crew
        if "content" in task.lower():
            crew = self.content_crew
        elif "technical" in task.lower():
            crew = self.technical_crew
        else:
            return "No suitable crew"

        # 3. Execute with crew
        result = crew.kickoff()

        return str(result)

# Usage
system = ProductionHybridCrewSystem()
result = await system.execute("Write technical documentation")
```

---

## Resources

- [CrewAI Documentation](https://docs.crewai.com/)
- [Agenkit Documentation](https://agenkit.dev)
- [Migration Guide](../migrations/crewai-to-agenkit.md)

---

**Best Practice**: Use CrewAI for role-based teams, Agenkit for patterns and middleware. Together they're powerful! 🚀
