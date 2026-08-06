"""
Multi-Agent Coordination System

A coordinator agent that delegates tasks to specialized agents:
- ResearchAgent: Information gathering and fact-checking
- CalculatorAgent: Mathematical computations and data analysis
- WriterAgent: Content generation and formatting
- AnalystAgent: Data interpretation and insights
"""

import asyncio
from datetime import datetime
from typing import Any

from agenkit import Agent, Message


class ResearchAgent(Agent):
    """Agent specialized in information gathering and research."""

    @property
    def name(self) -> str:
        return "ResearchAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["research", "fact_checking", "information_gathering"]

    async def process(self, message: Message) -> Message:
        """Research information on a topic."""
        query = str(message.content)
        await asyncio.sleep(0.3)  # Simulate research time

        # Mock research results
        findings = f"""
Research findings on "{query}":

1. **Primary Information**: This topic relates to modern AI systems and their
   applications in real-world scenarios. Current research shows significant
   progress in this area.

2. **Key Statistics**:
   - Market growth: 40% year-over-year
   - Adoption rate: 65% in enterprise
   - Success rate: 78% in pilot programs

3. **Expert Consensus**: Industry experts agree that this approach offers
   substantial benefits for scalability and efficiency.

4. **Recent Developments**: Latest advances include improved algorithms and
   better integration capabilities.
"""

        return Message(
            role="assistant",
            content=findings,
            metadata={
                "agent": self.name,
                "research_quality": "high",
                "sources_consulted": 4,
                "confidence": 0.85,
            },
        )


class CalculatorAgent(Agent):
    """Agent specialized in mathematical computations and analysis."""

    @property
    def name(self) -> str:
        return "CalculatorAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["calculations", "data_analysis", "statistics"]

    async def process(self, message: Message) -> Message:
        """Perform calculations and analysis."""
        query = str(message.content)
        await asyncio.sleep(0.2)  # Simulate computation time

        # Extract numbers and perform calculations (simplified)
        words = query.split()
        numbers = [float(w) for w in words if w.replace(".", "").replace("-", "").isdigit()]

        calculations = f"""
Calculation results for "{query}":

**Numbers identified**: {numbers if numbers else "None"}

**Computed values**:
- Sum: {sum(numbers) if numbers else "N/A"}
- Average: {sum(numbers) / len(numbers) if numbers else "N/A"}
- Maximum: {max(numbers) if numbers else "N/A"}
- Minimum: {min(numbers) if numbers else "N/A"}

**Analysis**:
- Range: {max(numbers) - min(numbers) if numbers and len(numbers) > 1 else "N/A"}
- Standard deviation: ~{
            (sum((x - sum(numbers) / len(numbers)) ** 2 for x in numbers) / len(numbers)) ** 0.5
            if numbers and len(numbers) > 1
            else "N/A"
        }

**Interpretation**: The data shows {
            "consistent values"
            if numbers and max(numbers) - min(numbers) < 10
            else "varied distribution"
            if numbers
            else "no numerical data"
        }.
"""

        return Message(
            role="assistant",
            content=calculations,
            metadata={
                "agent": self.name,
                "numbers_processed": len(numbers),
                "computation_type": "statistical_analysis",
            },
        )


class WriterAgent(Agent):
    """Agent specialized in content generation and formatting."""

    @property
    def name(self) -> str:
        return "WriterAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["writing", "content_generation", "formatting", "summarization"]

    async def process(self, message: Message) -> Message:
        """Generate well-formatted content."""
        query = str(message.content)
        await asyncio.sleep(0.4)  # Simulate writing time

        # Generate formatted content
        content = f"""
# Executive Summary

Based on the query "{query}", here is a comprehensive analysis:

## Overview

The subject matter encompasses critical aspects of modern technology and its
applications. This analysis provides actionable insights and recommendations
for stakeholders.

## Key Points

1. **Strategic Importance**: This topic represents a significant opportunity
   for innovation and growth in the current market landscape.

2. **Implementation Considerations**: Successful deployment requires careful
   planning, adequate resources, and stakeholder alignment.

3. **Expected Outcomes**: When properly executed, this approach can deliver
   measurable improvements in efficiency, quality, and user satisfaction.

## Recommendations

- **Short-term** (0-3 months): Conduct feasibility study and pilot program
- **Medium-term** (3-6 months): Scale successful pilots and refine processes
- **Long-term** (6-12 months): Full deployment with continuous optimization

## Conclusion

The evidence supports moving forward with this initiative, with appropriate
risk mitigation and success metrics in place.

---
*Document prepared by WriterAgent*
"""

        return Message(
            role="assistant",
            content=content,
            metadata={
                "agent": self.name,
                "word_count": len(content.split()),
                "format": "markdown",
                "readability": "professional",
            },
        )


class AnalystAgent(Agent):
    """Agent specialized in data interpretation and insights."""

    @property
    def name(self) -> str:
        return "AnalystAgent"

    @property
    def capabilities(self) -> list[str]:
        return ["analysis", "insights", "pattern_recognition", "recommendations"]

    async def process(self, message: Message) -> Message:
        """Analyze data and provide insights."""
        query = str(message.content)
        await asyncio.sleep(0.35)  # Simulate analysis time

        insights = f"""
Analytical insights for "{query}":

## Pattern Analysis

**Observed Trends**:
- Increasing adoption rate over past 6 months
- Strong correlation between implementation quality and success
- Regional variations in effectiveness (±15%)

## Risk Assessment

**Low Risk** (20%):
- Technical implementation
- User training

**Medium Risk** (15%):
- Budget overruns
- Timeline delays

**High Impact Opportunities** (65%):
- Process optimization
- Market expansion
- Competitive advantage

## Data-Driven Recommendations

1. **Prioritize Quick Wins**: Focus on high-impact, low-effort initiatives
   to build momentum and demonstrate value.

2. **Invest in Infrastructure**: Allocate 30% of budget to foundational
   capabilities that enable long-term success.

3. **Monitor Key Metrics**: Track user adoption (target: 80%), satisfaction
   (target: 4.2/5), and ROI (target: 150%).

## Predictive Outlook

Based on current trajectories:
- 6-month projection: 40% improvement in key metrics
- 12-month projection: Market leadership position achievable
- Risk-adjusted confidence: 78%
"""

        return Message(
            role="assistant",
            content=insights,
            metadata={
                "agent": self.name,
                "analysis_depth": "comprehensive",
                "confidence_level": 0.78,
                "recommendations_count": 3,
            },
        )


class CoordinatorAgent(Agent):
    """
    Coordinator agent that delegates tasks to specialized agents.

    Analyzes user queries and routes them to appropriate specialized agents,
    then aggregates and presents the results.
    """

    def __init__(self, name: str = "CoordinatorAgent"):
        self._name = name
        self._coordination_count = 0

        # Initialize specialized agents
        self._agents = {
            "research": ResearchAgent(),
            "calculator": CalculatorAgent(),
            "writer": WriterAgent(),
            "analyst": AnalystAgent(),
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return [
            "coordination",
            "task_delegation",
            "multi_agent_orchestration",
            "result_aggregation",
        ]

    async def process(self, message: Message) -> Message:
        """
        Coordinate multiple agents to handle complex queries.

        Analyzes the query, selects appropriate agents, delegates tasks,
        and aggregates results.
        """
        self._coordination_count += 1
        query = str(message.content).lower()

        # Determine which agents to involve
        selected_agents = self._select_agents(query)

        # Create coordination plan
        plan = self._create_plan(query, selected_agents)

        # Execute tasks with selected agents
        results = await self._execute_coordination(query, selected_agents)

        # Aggregate results
        aggregated = self._aggregate_results(query, results, plan)

        return Message(
            role="assistant",
            content=aggregated,
            metadata={
                "coordination_count": self._coordination_count,
                "agents_involved": [agent_name for agent_name, _ in selected_agents],
                "execution_plan": plan,
                "agent_results": [
                    {
                        "agent": result["agent"],
                        "status": "completed",
                        "confidence": result.get("confidence", 0.0),
                    }
                    for result in results
                ],
            },
        )

    def _select_agents(self, query: str) -> list[tuple[str, Agent]]:
        """Select appropriate agents based on query content."""
        selected = []

        # Research for questions and information gathering
        if any(
            word in query
            for word in ["what", "who", "why", "research", "find", "information", "about"]
        ):
            selected.append(("research", self._agents["research"]))

        # Calculator for numerical queries
        if any(
            word in query
            for word in ["calculate", "compute", "number", "data", "statistic", "analyze"]
        ) or any(char.isdigit() for char in query):
            selected.append(("calculator", self._agents["calculator"]))

        # Writer for content generation
        if any(
            word in query for word in ["write", "create", "draft", "compose", "summary", "report"]
        ):
            selected.append(("writer", self._agents["writer"]))

        # Analyst for insights and recommendations
        if any(
            word in query
            for word in [
                "analyze",
                "insight",
                "recommend",
                "should",
                "strategy",
                "decision",
            ]
        ):
            selected.append(("analyst", self._agents["analyst"]))

        # Default: use research and analyst if no specific match
        if not selected:
            selected = [
                ("research", self._agents["research"]),
                ("analyst", self._agents["analyst"]),
            ]

        return selected

    def _create_plan(self, query: str, selected_agents: list[tuple[str, Agent]]) -> dict[str, Any]:
        """Create execution plan for coordination."""
        plan = {
            "query": query,
            "approach": "parallel_execution",
            "agents": [agent_name for agent_name, _ in selected_agents],
            "expected_duration": len(selected_agents) * 0.3,  # Approximate
            "coordination_strategy": "aggregate_results",
        }
        return plan

    async def _execute_coordination(
        self, query: str, selected_agents: list[tuple[str, Agent]]
    ) -> list[dict[str, Any]]:
        """Execute tasks across selected agents in parallel."""
        # Create message for each agent
        agent_message = Message(role="user", content=query)

        # Execute agents in parallel
        tasks = []
        for agent_name, agent in selected_agents:
            tasks.append(self._execute_agent(agent_name, agent, agent_message))

        results = await asyncio.gather(*tasks)
        return results

    async def _execute_agent(
        self, agent_name: str, agent: Agent, message: Message
    ) -> dict[str, Any]:
        """Execute a single agent and capture results."""
        start_time = datetime.utcnow()

        try:
            response = await agent.process(message)
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "agent": agent_name,
                "status": "success",
                "content": response.content,
                "metadata": response.metadata or {},
                "execution_time": execution_time,
                "confidence": (
                    response.metadata.get("confidence", 0.0) if response.metadata else 0.0
                ),
            }
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return {
                "agent": agent_name,
                "status": "error",
                "error": str(e),
                "execution_time": execution_time,
            }

    def _aggregate_results(
        self, query: str, results: list[dict[str, Any]], plan: dict[str, Any]
    ) -> str:
        """Aggregate results from multiple agents into coherent response."""
        lines = ["# Multi-Agent Coordination Results\n"]
        lines.append(f'**Query**: "{query}"\n')
        lines.append(f"**Agents Involved**: {', '.join(plan['agents'])}")
        lines.append(
            f"**Total Execution Time**: {sum(r.get('execution_time', 0) for r in results):.2f}s\n"
        )

        lines.append("---\n")

        # Present results from each agent
        for result in results:
            agent_name = result["agent"].title()
            status = result["status"]

            if status == "success":
                lines.append(f"## {agent_name} Results\n")
                lines.append(result["content"])
                lines.append(
                    f"\n*Execution time: {result['execution_time']:.2f}s | "
                    f"Confidence: {result.get('confidence', 0):.0%}*\n"
                )
            else:
                lines.append(f"## {agent_name} Results\n")
                lines.append(f"❌ Error: {result.get('error', 'Unknown error')}\n")

        # Summary
        lines.append("---\n")
        lines.append("## Coordination Summary\n")
        successful = sum(1 for r in results if r["status"] == "success")
        lines.append(
            f"- **Agents Completed**: {successful}/{len(results)}\n"
            f"- **Success Rate**: {successful / len(results):.0%}\n"
            f"- **Average Confidence**: "
            f"{sum(r.get('confidence', 0) for r in results) / len(results):.0%}"
        )

        return "\n".join(lines)
