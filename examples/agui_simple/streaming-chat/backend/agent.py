"""
Conversational Chat Agent with Streaming Support

A friendly assistant agent that demonstrates basic AG-UI streaming
without additional complexity like HITL or tool usage.
"""

from agenkit import Agent, Message


class ChatAgent(Agent):
    """
    Simple conversational agent for demonstrating streaming capabilities.

    This agent provides helpful, contextual responses and demonstrates
    token-by-token streaming through AG-UI protocol.
    """

    def __init__(self, name: str = "ChatAgent"):
        self._name = name
        self._conversation_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return ["chat", "conversation", "streaming", "q&a"]

    async def process(self, message: Message) -> Message:
        """
        Process user message and generate contextual response.

        Args:
            message: User message with content to respond to

        Returns:
            Message with assistant's response
        """
        self._conversation_count += 1
        content = str(message.content).lower().strip()

        # Generate contextual response
        response_text = self._generate_response(content)

        return Message(
            role="assistant",
            content=response_text,
            metadata={
                "conversation_count": self._conversation_count,
                "response_type": self._classify_response(content),
                "streaming": True,
            },
        )

    def _generate_response(self, content: str) -> str:
        """Generate contextual response based on user input."""
        # Greetings
        if any(word in content for word in ["hello", "hi", "hey", "greetings"]):
            return (
                "Hello! 👋 I'm your AI assistant, here to help with questions, "
                "provide information, or just have a friendly chat. What would you like to know?"
            )

        # Farewells
        if any(word in content for word in ["bye", "goodbye", "see you"]):
            return (
                "Goodbye! It was great chatting with you. Feel free to return anytime "
                "if you have more questions. Have a wonderful day! 👋"
            )

        # Help/about
        if any(word in content for word in ["help", "what can you do", "capabilities"]):
            return (
                "I'm a conversational AI assistant demonstrating the AG-UI streaming protocol. "
                "I can:\n\n"
                "• Answer questions on various topics\n"
                "• Provide explanations and information\n"
                "• Have friendly conversations\n"
                "• Demonstrate real-time streaming responses\n\n"
                "Notice how my responses appear token-by-token? That's AG-UI streaming in action! "
                "Try asking me anything, and you'll see the smooth streaming experience."
            )

        # AG-UI specific
        if "ag-ui" in content or "agui" in content or "streaming" in content:
            return (
                "AG-UI (Agent-User Interaction) is a protocol for streaming agent responses "
                "to frontends in real-time. Key features include:\n\n"
                "**Streaming**: Responses appear token-by-token as they're generated, "
                "providing immediate feedback to users.\n\n"
                "**Events**: Different event types (metadata, text chunks, tool calls, interrupts) "
                "enable rich interactions.\n\n"
                "**Transport**: Works over WebSockets or Server-Sent Events (SSE) for "
                "flexible deployment.\n\n"
                "**Interactivity**: Supports bidirectional communication for human-in-the-loop "
                "workflows, approvals, and interactive tools.\n\n"
                "You're experiencing AG-UI streaming right now!"
            )

        # Agenkit specific
        if "agenkit" in content:
            return (
                "Agenkit is a minimal, composable toolkit for building AI agents across "
                "multiple programming languages. It provides:\n\n"
                "**Core Abstractions**: Agent, Tool, Memory, and Message interfaces that work "
                "consistently across Python, Go, TypeScript, Rust, C++, and Zig.\n\n"
                "**Design Patterns**: Pre-built patterns like ReAct, Planning, Human-in-the-Loop, "
                "Multi-Agent, and Reflection.\n\n"
                "**Protocol Support**: AG-UI protocol for streaming to frontends, enabling "
                "real-time user experiences.\n\n"
                "**Zero Lock-in**: Use any LLM provider, any framework, any deployment target. "
                "Agenkit stays out of your way.\n\n"
                "Want to learn more about a specific feature?"
            )

        # Technical questions
        if "?" in content or any(
            word in content for word in ["how", "what", "why", "when", "where", "who"]
        ):
            return (
                f"That's an interesting question about '{content[:50]}...'! "
                "As a demonstration agent, I provide general responses to showcase "
                "the AG-UI streaming protocol. In a production system, I would connect to "
                "a large language model (LLM) like GPT-4, Claude, or Gemini to provide "
                "detailed, accurate answers.\n\n"
                "Key capabilities you'd expect from a production chat agent:\n"
                "• Access to knowledge bases and documentation\n"
                "• Context retention across conversation\n"
                "• Tool usage for real-time information\n"
                "• Multi-turn reasoning and follow-ups\n\n"
                "For now, I'm here to demonstrate smooth, real-time streaming!"
            )

        # Default response
        return (
            f'I understand you said: "{content[:100]}{"..." if len(content) > 100 else ""}"\n\n'
            "As a demonstration agent, I'm showcasing AG-UI's streaming capabilities. "
            "Notice how this response appears smoothly, token by token? That's the power "
            "of AG-UI protocol enabling real-time user experiences.\n\n"
            "In a production deployment, I would be powered by a large language model "
            "to provide detailed, contextual responses to your queries. "
            "Try asking me about 'AG-UI', 'Agenkit', or request 'help' to see what I can demonstrate!"
        )

    def _classify_response(self, content: str) -> str:
        """Classify the type of response being generated."""
        if any(word in content for word in ["hello", "hi", "hey"]):
            return "greeting"
        elif any(word in content for word in ["bye", "goodbye"]):
            return "farewell"
        elif "help" in content or "capabilities" in content:
            return "help"
        elif "?" in content:
            return "question"
        else:
            return "general"
