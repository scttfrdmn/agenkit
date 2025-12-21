# Bidirectional AutoGen + Agenkit Integration

Guide for using Agenkit with AutoGen in both directions.

## Overview

**Bidirectional integration** between AutoGen and Agenkit:

1. **Agenkit → AutoGen**: Use Agenkit agents in AutoGen conversations
2. **AutoGen → Agenkit**: Use AutoGen agents within Agenkit workflows
3. **Hybrid**: Combine conversational AI with pattern-based orchestration

---

## 1. Agenkit Agent in AutoGen Conversation

```python
from autogen import ConversableAgent, UserProxyAgent
from agenkit import Agent, Message
import asyncio

class AgenkitAutoGenAgent(ConversableAgent):
    """Wrap Agenkit agent as AutoGen conversable agent."""

    def __init__(self, agenkit_agent: Agent, name: str, **kwargs):
        self.agenkit_agent = agenkit_agent

        super().__init__(
            name=name,
            llm_config=False,  # We handle LLM through Agenkit
            **kwargs
        )

    def generate_reply(self, messages, sender, **kwargs):
        """Generate reply using Agenkit agent."""
        # Get last message
        last_message = messages[-1]["content"]

        # Process with Agenkit
        message = Message(role="user", content=last_message)
        response = asyncio.run(self.agenkit_agent.process(message))

        return response.content

# Example usage
from agenkit.patterns import ReActAgent
from agenkit.adapters import OpenAIAdapter

llm = OpenAIAdapter(api_key="key", model="gpt-4")
react_agent = ReActAgent(llm=llm)

# Wrap as AutoGen agent
autogen_agent = AgenkitAutoGenAgent(react_agent, name="agenkit_assistant")

# Create conversation
user_proxy = UserProxyAgent(name="user", human_input_mode="NEVER")

# Start conversation
user_proxy.initiate_chat(
    autogen_agent,
    message="Help me plan a project"
)
```

---

## 2. AutoGen Agent in Agenkit Workflow

```python
from autogen import AssistantAgent
from agenkit import Agent, Message

class AutoGenAgent(Agent):
    """Wrap AutoGen agent as Agenkit agent."""

    def __init__(self, autogen_agent: AssistantAgent):
        self.autogen_agent = autogen_agent
        self.conversation_history = []

    @property
    def name(self) -> str:
        return self.autogen_agent.name

    async def process(self, message: Message) -> Message:
        """Process message through AutoGen agent."""
        # Add to history
        self.conversation_history.append({
            "role": "user",
            "content": message.content
        })

        # Generate reply
        reply = self.autogen_agent.generate_reply(
            messages=self.conversation_history,
            sender=None
        )

        # Add reply to history
        self.conversation_history.append({
            "role": "assistant",
            "content": reply
        })

        return Message(role="assistant", content=reply)

# Usage in Agenkit pipeline
from agenkit.patterns import SequentialAgent

autogen_assistant = AssistantAgent(
    name="assistant",
    llm_config={"model": "gpt-4"}
)

pipeline = SequentialAgent([
    preprocessing_agent,       # Agenkit agent
    AutoGenAgent(autogen_assistant),  # AutoGen agent
    postprocessing_agent      # Agenkit agent
])
```

---

## 3. Hybrid: Multi-Agent Conversation with Agenkit Orchestration

```python
from autogen import GroupChat, GroupChatManager
from agenkit.patterns import OrchestrationAgent

class HybridConversationalOrchestrator(Agent):
    """
    Use AutoGen for multi-agent conversations,
    Agenkit for orchestration and control flow.
    """

    def __init__(self, autogen_agents: list, orchestrator: OrchestrationAgent):
        # Create AutoGen group chat
        self.group_chat = GroupChat(
            agents=autogen_agents,
            messages=[],
            max_round=10
        )
        self.manager = GroupChatManager(groupchat=self.group_chat)
        self.orchestrator = orchestrator

    @property
    def name(self) -> str:
        return "hybrid-conversational-orchestrator"

    async def process(self, message: Message) -> Message:
        # 1. Use Agenkit to plan conversation strategy
        plan_msg = Message(
            role="user",
            content=f"Plan conversation strategy for: {message.content}"
        )
        plan = await self.orchestrator.process(plan_msg)

        # 2. Execute AutoGen conversation
        self.group_chat.messages.append({
            "role": "user",
            "content": message.content
        })

        result = self.manager.run()

        return Message(
            role="assistant",
            content=result,
            metadata={"plan": plan.content}
        )

# Example
agents = [
    AssistantAgent(name="researcher", llm_config={"model": "gpt-4"}),
    AssistantAgent(name="critic", llm_config={"model": "gpt-4"}),
    AssistantAgent(name="writer", llm_config={"model": "gpt-4"})
]

orchestrator = OrchestrationAgent(llm=llm_adapter)
hybrid = HybridConversationalOrchestrator(agents, orchestrator)

# Agenkit orchestrates, AutoGen handles conversations!
```

---

## 4. When to Use Each

**Agenkit → AutoGen**: Multi-agent conversations, code execution
**AutoGen → Agenkit**: Middleware, observability, cross-language
**Hybrid**: Complex systems needing both capabilities

---

## Resources

- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [Migration Guide](../migrations/autogen-to-agenkit.md)

**Combine for powerful conversational AI with robust patterns!** 🤝
