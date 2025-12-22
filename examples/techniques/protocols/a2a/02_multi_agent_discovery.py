"""
Multi-Agent Coordination with Discovery Example.

Demonstrates:
- Agent registration with discovery service
- Discovering agents by capability
- Coordinating multiple agents
- Agent-to-agent message routing
"""

import asyncio

from agenkit import Message
from agenkit.techniques.protocols.a2a import (
    A2AAction,
    A2AServer,
    AgentInfo,
    InMemoryDiscoveryService,
    create_request,
)

# ==============================================================================
# Specialized Agents
# ==============================================================================

class SummarizerAgent:
    """Agent that summarizes text."""

    def __init__(self):
        self.name = "summarizer"
        self.capabilities = ["summarization", "text-processing"]

    async def process(self, message: Message) -> Message:
        """Summarize the input text."""
        text = message.content
        # Simple summarization (first 50 chars)
        summary = text[:50] + "..." if len(text) > 50 else text

        return Message(
            role="assistant",
            content=f"Summary: {summary}",
            metadata={"summarized": True}
        )


class TranslatorAgent:
    """Agent that 'translates' text (uppercases it as a demo)."""

    def __init__(self):
        self.name = "translator"
        self.capabilities = ["translation", "text-processing"]

    async def process(self, message: Message) -> Message:
        """Translate text (demo: uppercase)."""
        text = message.content
        translated = text.upper()

        return Message(
            role="assistant",
            content=f"Translated: {translated}",
            metadata={"translated": True}
        )


class AnalyzerAgent:
    """Agent that analyzes text."""

    def __init__(self):
        self.name = "analyzer"
        self.capabilities = ["text-analysis", "sentiment"]

    async def process(self, message: Message) -> Message:
        """Analyze text (demo: count words)."""
        text = message.content
        word_count = len(text.split())

        return Message(
            role="assistant",
            content=f"Analysis: {word_count} words",
            metadata={"word_count": word_count}
        )


# ==============================================================================
# Example: Multi-Agent Discovery
# ==============================================================================

async def multi_agent_discovery_example():
    """Demonstrate multi-agent coordination with discovery."""

    print("=" * 70)
    print("Multi-Agent Discovery Example")
    print("=" * 70)

    # Create discovery service
    discovery = InMemoryDiscoveryService()

    print("\n1. Setting up discovery service...")

    # Create agents
    summarizer = SummarizerAgent()
    translator = TranslatorAgent()
    analyzer = AnalyzerAgent()

    # Create A2A servers
    servers = [
        A2AServer(
            agent_id="summarizer-001",
            agent=summarizer,
            capabilities=summarizer.capabilities,
            name="Summarizer"
        ),
        A2AServer(
            agent_id="translator-001",
            agent=translator,
            capabilities=translator.capabilities,
            name="Translator"
        ),
        A2AServer(
            agent_id="analyzer-001",
            agent=analyzer,
            capabilities=analyzer.capabilities,
            name="Analyzer"
        )
    ]

    # Register agents with discovery
    print("\n2. Registering agents with discovery service...")
    for server in servers:
        agent_info = AgentInfo(
            agent_id=server.agent_id,
            name=server.name,
            capabilities=server.capabilities,
            endpoint=f"http://localhost:8080/a2a/{server.agent_id}",
            transport="http"
        )
        await discovery.register(agent_info)
        print(f"   Registered: {server.name} ({server.agent_id})")
        print(f"     Capabilities: {', '.join(server.capabilities)}")

    # List all agents
    print("\n3. Listing all registered agents...")
    all_agents = await discovery.list_all()
    print(f"   Total agents: {len(all_agents)}")
    for agent in all_agents:
        print(f"   - {agent.name}: {', '.join(agent.capabilities)}")

    # Discover agents by capability
    print("\n4. Discovering agents by capability...")

    print("\n   a) Finding 'summarization' agents:")
    summarizers = await discovery.discover("summarization")
    for agent in summarizers:
        print(f"      - {agent.name} ({agent.agent_id})")

    print("\n   b) Finding 'text-analysis' agents:")
    analyzers = await discovery.discover("text-analysis")
    for agent in analyzers:
        print(f"      - {agent.name} ({agent.agent_id})")

    print("\n   c) Finding 'translation' agents:")
    translators = await discovery.discover("translation")
    for agent in translators:
        print(f"      - {agent.name} ({agent.agent_id})")

    # Test coordinated workflow
    print("\n5. Testing coordinated workflow...")
    print("   Workflow: Analyze → Summarize → Translate")

    text = "The Agent-to-Agent protocol enables seamless communication between AI agents."

    print(f"\n   Input text: {text}")

    # Step 1: Analyze
    print("\n   Step 1: Analyze text")
    analyzer_agents = await discovery.discover("text-analysis")
    if analyzer_agents:
        analyzer_server = next(
            s for s in servers if s.agent_id == analyzer_agents[0].agent_id
        )

        analyze_request = create_request(
            from_agent="coordinator",
            to_agent=analyzer_server.agent_id,
            action=A2AAction.PROCESS.value,
            content={"text": text}
        )

        analyze_response = await analyzer_server.handle_message(analyze_request)
        print(f"   Result: {analyze_response.content['content']}")

    # Step 2: Summarize
    print("\n   Step 2: Summarize text")
    summarizer_agents = await discovery.discover("summarization")
    if summarizer_agents:
        summarizer_server = next(
            s for s in servers if s.agent_id == summarizer_agents[0].agent_id
        )

        summarize_request = create_request(
            from_agent="coordinator",
            to_agent=summarizer_server.agent_id,
            action=A2AAction.PROCESS.value,
            content={"text": text}
        )

        summarize_response = await summarizer_server.handle_message(summarize_request)
        summary = summarize_response.content['content']
        print(f"   Result: {summary}")

    # Step 3: Translate summary
    print("\n   Step 3: Translate summary")
    translator_agents = await discovery.discover("translation")
    if translator_agents:
        translator_server = next(
            s for s in servers if s.agent_id == translator_agents[0].agent_id
        )

        translate_request = create_request(
            from_agent="coordinator",
            to_agent=translator_server.agent_id,
            action=A2AAction.PROCESS.value,
            content={"text": summary}
        )

        translate_response = await translator_server.handle_message(translate_request)
        print(f"   Result: {translate_response.content['content']}")

    # Test agent status updates
    print("\n6. Testing agent status management...")
    await discovery.update_status("analyzer-001", "busy")
    updated_agent = (await discovery.find_by_id("analyzer-001"))[0]
    print(f"   Updated analyzer status: {updated_agent.status}")

    # Test heartbeat
    print("\n7. Sending heartbeat...")
    await discovery.heartbeat("summarizer-001")
    print("   Heartbeat sent successfully")

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


# ==============================================================================
# Run Example
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(multi_agent_discovery_example())
