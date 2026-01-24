#!/usr/bin/env python3
"""
MiniAutoGen - AutoGen Equivalent Built on Agenkit

Demonstrates how AutoGen's conversational multi-agent patterns can be built
ON TOP of Agenkit primitives, showing toolkit philosophy.

Pattern Mappings: AutoGen ConversableAgent → ConversationalAgent with LLM,
GroupChat → Multi-agent orchestration, register_reply() → process() override

Migration guide: docs/migrations/autogen-to-agenkit.md

Usage: uv run python examples/frameworks/miniautogen.py
"""

import asyncio
from typing import Any, cast

from agenkit import Agent, Message
from agenkit.adapters.llm import LLM, OpenAILLM


class ConversableAgent(Agent):
    """
    Basic conversational agent with LLM (mirrors AutoGen.ConversableAgent).
    Pattern: AutoGen.ConversableAgent → Agenkit Agent with LLM and conversation state
    """

    def __init__(
        self, name: str, system_message: str, llm: LLM, max_consecutive_auto_reply: int = 10
    ) -> None:
        """Create conversable agent with LLM."""
        self._name = name
        self.system_message = system_message
        self.llm = llm
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.conversation_history: list[Message] = []

    @property
    def name(self) -> str:
        """Return agent's name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["conversation", "llm_generation"]

    async def process(self, message: Message) -> Message:
        """Process message with conversation context."""
        # Add to history
        self.conversation_history.append(message)

        # Build messages with system context
        messages = [Message(role="system", content=self.system_message)]
        messages.extend(self.conversation_history)

        # Get LLM response
        response = await self.llm.complete(messages)
        result = Message(
            role="agent",
            content=cast("str", response.content),
            metadata={"agent_name": self._name, "system_message": self.system_message},
        )

        # Add response to history
        self.conversation_history.append(result)
        return result

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []


class AssistantAgent(ConversableAgent):
    """
    Assistant agent with default helpful system message (mirrors AutoGen.AssistantAgent).
    Pattern: AutoGen.AssistantAgent → ConversableAgent with assistant role
    """

    def __init__(self, name: str, llm: LLM, system_message: str | None = None) -> None:
        """Create assistant agent with default helpful behavior."""
        default_message = "You are a helpful AI assistant. Solve tasks using your skills."
        super().__init__(name=name, system_message=system_message or default_message, llm=llm)


class UserProxyAgent(Agent):
    """
    User proxy agent for human input (mirrors AutoGen.UserProxyAgent).
    Pattern: AutoGen.UserProxyAgent → Agenkit Agent with human input
    Note: In real use, connect to actual input source; here we mock for examples.
    """

    def __init__(self, name: str, mock_responses: list[str] | None = None) -> None:
        """Create user proxy agent."""
        self._name = name
        self.mock_responses = mock_responses or []
        self.response_index = 0

    @property
    def name(self) -> str:
        """Return agent's name."""
        return self._name

    @property
    def capabilities(self) -> list[str]:
        """Return agent capabilities."""
        return ["human_input", "user_proxy"]

    async def process(self, message: Message) -> Message:
        """Get human input (mocked for examples)."""
        if self.response_index < len(self.mock_responses):
            response_content = self.mock_responses[self.response_index]
            self.response_index += 1
        else:
            response_content = "TERMINATE"  # AutoGen convention

        return Message(role="user", content=response_content, metadata={"agent_name": self._name})


class GroupChat:
    """
    Multi-agent conversation container (mirrors AutoGen.GroupChat).
    Pattern: AutoGen.GroupChat → Message history + agent list
    """

    def __init__(self, agents: list[Agent], max_round: int = 10) -> None:
        """
        Create group chat with agents.

        Args:
            agents: List of agents participating in the chat
            max_round: Maximum number of conversation rounds
        """
        self.agents = agents
        self.max_round = max_round
        self.messages: list[dict[str, Any]] = []

    def agent_by_name(self, name: str) -> Agent | None:
        """Find agent by name."""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def add_message(self, agent_name: str, content: str) -> None:
        """Add message to group chat history."""
        self.messages.append({"agent": agent_name, "content": content})


class GroupChatManager(Agent):
    """
    Orchestrates multi-agent group conversations (mirrors AutoGen.GroupChatManager).
    Pattern: AutoGen.GroupChatManager → Custom orchestration with speaker selection
    """

    def __init__(self, groupchat: GroupChat, selector: str = "round_robin") -> None:
        """
        Create group chat manager.

        Args:
            groupchat: GroupChat instance to manage
            selector: Speaker selection strategy ("round_robin" or "auto")
        """
        self.groupchat = groupchat
        self.selector = selector
        self.current_speaker_index = 0

    @property
    def name(self) -> str:
        """Return manager's name."""
        return "group_chat_manager"

    @property
    def capabilities(self) -> list[str]:
        """Return manager capabilities."""
        return ["orchestration", "speaker_selection"]

    async def process(self, message: Message) -> Message:
        """Orchestrate multi-agent conversation."""
        # Add initial message to history
        self.groupchat.add_message("user", cast("str", message.content))

        conversation_results = []
        current_message = message

        for round_num in range(self.groupchat.max_round):
            # Select next speaker
            speaker = self._select_speaker(current_message)

            if speaker is None:
                break

            # Agent processes message
            response = await speaker.process(current_message)

            # Check for termination
            if "TERMINATE" in cast("str", response.content).upper():
                conversation_results.append(f"{speaker.name}: {response.content}")
                break

            # Add to history
            self.groupchat.add_message(speaker.name, cast("str", response.content))
            conversation_results.append(f"{speaker.name}: {response.content}")

            # Update for next round
            current_message = response

        # Combine all responses
        final_output = "\n\n".join(conversation_results)

        return Message(
            role="agent",
            content=final_output,
            metadata={
                "rounds": round_num + 1,
                "total_agents": len(self.groupchat.agents),
                "selector": self.selector,
            },
        )

    def _select_speaker(self, message: Message) -> Agent | None:
        """Select next speaker based on strategy."""
        if self.selector == "round_robin":
            # Round-robin selection
            if not self.groupchat.agents:
                return None

            speaker = self.groupchat.agents[self.current_speaker_index]
            self.current_speaker_index = (self.current_speaker_index + 1) % len(
                self.groupchat.agents
            )
            return speaker

        elif self.selector == "auto":
            # Simple auto-selection based on message content
            content = cast("str", message.content).lower()

            # Simple keyword-based routing
            for agent in self.groupchat.agents:
                if agent.name.lower() in content:
                    return agent

            # Fallback to first agent
            return self.groupchat.agents[0] if self.groupchat.agents else None

        return None


async def example_two_agent_chat() -> None:
    """Example: Simple two-agent conversation."""
    print("=" * 60)
    print("Example 1: Two-Agent Chat (AutoGen-style)")
    print("=" * 60)

    # Create LLM (using test key for demo)
    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create assistant
    assistant = AssistantAgent(name="assistant", llm=llm)

    # Create user proxy (mocked)
    user_proxy = UserProxyAgent(name="user", mock_responses=["What is the capital of France?"])

    print("\n📝 AutoGen-style API:")
    print("   assistant = AssistantAgent(name='assistant', llm=llm)")
    print("   user_proxy = UserProxyAgent(name='user')")
    print("   result = await user_proxy.initiate_chat(assistant, message)")

    print("\n✅ Pattern: AutoGen two-agent → Direct agent.process() calls")
    print("   User sends message → Assistant responds → User replies")


async def example_group_chat() -> None:
    """Example: Multi-agent group chat."""
    print("\n\n" + "=" * 60)
    print("Example 2: Group Chat with Multiple Agents")
    print("=" * 60)

    llm = OpenAILLM(model="gpt-4o-mini", api_key="test-key")

    # Create specialist agents
    researcher = AssistantAgent(
        name="researcher",
        llm=llm,
        system_message="You are a researcher. Gather and present information.",
    )

    analyst = AssistantAgent(
        name="analyst",
        llm=llm,
        system_message="You are an analyst. Analyze data and provide insights.",
    )

    writer = AssistantAgent(
        name="writer",
        llm=llm,
        system_message="You are a writer. Create clear, engaging content.",
    )

    # Create group chat
    group_chat = GroupChat(agents=[researcher, analyst, writer], max_round=6)

    # Create manager
    manager = GroupChatManager(groupchat=group_chat, selector="round_robin")

    print("\n📝 AutoGen-style API:")
    print("   group_chat = GroupChat(agents=[researcher, analyst, writer],")
    print("                          max_round=6)")
    print("   manager = GroupChatManager(groupchat=group_chat)")
    print("   result = await manager.process(message)")

    print("\n✅ Pattern: AutoGen.GroupChat → Orchestration with speaker selection")
    print("   Manager coordinates agents in round-robin or auto-select mode")


async def example_speaker_selection() -> None:
    """Example: Custom speaker selection."""
    print("\n\n" + "=" * 60)
    print("Example 3: Custom Speaker Selection")
    print("=" * 60)

    print("\n📝 AutoGen Pattern:")
    print("   def custom_speaker_selection(last_speaker, groupchat):")
    print("       # Logic to select next speaker")
    print("       return groupchat.agent_by_name('Researcher')")

    print("\n✅ Agenkit Equivalent:")
    print("   # Extend GroupChatManager with custom _select_speaker() logic")
    print("   # Or use RouterAgent for more sophisticated routing")

    print("\n💡 Options:")
    print("   • Round-robin: Simple rotation through agents")
    print("   • Auto: Keyword-based or LLM-based speaker selection")
    print("   • Custom: Override _select_speaker() method")


async def main() -> None:
    """Run all examples."""
    print("\n╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MiniAutoGen - AutoGen Built on Agenkit" + " " * 9 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n🎯 Demonstrate: AutoGen conversational patterns on Agenkit")

    await example_two_agent_chat()
    await example_group_chat()
    await example_speaker_selection()

    print("\n\n" + "=" * 60)
    print("✅ MiniAutoGen Examples Complete")
    print("=" * 60)
    print("\n🔑 Key Takeaways:")
    print("   • Agenkit is a TOOLKIT for building multi-agent systems")
    print("   • AutoGen patterns map to Agenkit primitives:")
    print("     - ConversableAgent → Agent with LLM and conversation state")
    print("     - AssistantAgent → ConversableAgent with helpful system message")
    print("     - UserProxyAgent → Agent with human input (mocked here)")
    print("     - GroupChat → Message history + agent list")
    print("     - GroupChatManager → Orchestration with speaker selection")

    print("\n📚 Migration guide: docs/migrations/autogen-to-agenkit.md")
    print("\n💡 Why Agenkit over AutoGen?")
    print("   ✓ 6 languages (Python, Go, TypeScript, Rust, C++, Zig)")
    print("   ✓ 18x faster (Go) with true async/await")
    print("   ✓ Explicit control (no hidden GroupChat orchestration)")
    print("   ✓ Production-ready (OpenTelemetry, retry, circuit breaker)")
    print("   ✓ Composable patterns (mix conversation, planning, tools)")


if __name__ == "__main__":
    asyncio.run(main())
