# Quick Start

Build your first Agenkit agent in less than 5 minutes!

## Your First Agent

=== "Python"

    Create a file `my_agent.py`:

    ```python
    from agenkit import Agent, Message
    import asyncio

    class EchoAgent(Agent):
        """A simple agent that echoes messages."""

        @property
        def name(self) -> str:
            return "echo-agent"

        @property
        def capabilities(self) -> list[str]:
            return ["echo", "text-processing"]

        async def process(self, message: Message) -> Message:
            """Process the message and return a response."""
            response_content = f"Echo: {message.content}"
            return Message(
                role="agent",
                content=response_content,
                metadata={"processed_by": self.name}
            )

    # Use the agent
    async def main():
        agent = EchoAgent()

        # Create a message
        user_message = Message(
            role="user",
            content="Hello, Agenkit!"
        )

        # Process it
        response = await agent.process(user_message)
        print(f"Agent: {response.content}")
        # Output: "Agent: Echo: Hello, Agenkit!"

    if __name__ == "__main__":
        asyncio.run(main())
    ```

    Run it:
    ```bash
    python my_agent.py
    ```

=== "Go"

    Create a file `my_agent.go`:

    ```go
    package main

    import (
        "context"
        "fmt"
        "github.com/agenkit/agenkit-go/agenkit"
    )

    // EchoAgent is a simple agent that echoes messages
    type EchoAgent struct{}

    func (a *EchoAgent) Name() string {
        return "echo-agent"
    }

    func (a *EchoAgent) Capabilities() []string {
        return []string{"echo", "text-processing"}
    }

    func (a *EchoAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
        responseContent := fmt.Sprintf("Echo: %s", msg.Content)

        return &agenkit.Message{
            Role:    "agent",
            Content: responseContent,
            Metadata: map[string]interface{}{
                "processed_by": a.Name(),
            },
        }, nil
    }

    func main() {
        agent := &EchoAgent{}

        // Create a message
        userMessage := &agenkit.Message{
            Role:    "user",
            Content: "Hello, Agenkit!",
        }

        // Process it
        response, err := agent.Process(context.Background(), userMessage)
        if err != nil {
            panic(err)
        }

        fmt.Printf("Agent: %s\n", response.Content)
        // Output: "Agent: Echo: Hello, Agenkit!"
    }
    ```

    Run it:
    ```bash
    go run my_agent.go
    ```

---

## Understanding the Code

### 1. The Agent Interface

Every agent implements the `Agent` interface with two required methods:

- **`name`** - A unique identifier for the agent
- **`process(message)`** - The core method that processes messages

### 2. The Message Type

Messages are the universal data format in Agenkit:

```python
Message(
    role="user",           # Who sent it: "user", "agent", "system", "tool"
    content="...",         # The actual content (any type)
    metadata={}            # Optional metadata dict
)
```

### 3. Processing Flow

```
User Message → Agent.process() → Agent Response
```

Simple as that!

---

## Adding Middleware

Let's add retry logic to make our agent more resilient:

=== "Python"

    ```python
    from agenkit.middleware import RetryDecorator, RetryConfig

    # Create the agent
    agent = EchoAgent()

    # Wrap with retry middleware
    resilient_agent = RetryDecorator(
        agent,
        RetryConfig(
            max_attempts=3,
            initial_backoff=1.0
        )
    )

    # Use it (retries automatically on failure)
    response = await resilient_agent.process(message)
    ```

=== "Go"

    ```go
    import "github.com/agenkit/agenkit-go/middleware"

    // Create the agent
    agent := &EchoAgent{}

    // Wrap with retry middleware
    resilientAgent := middleware.NewRetryDecorator(
        agent,
        middleware.RetryConfig{
            MaxAttempts:     3,
            InitialBackoff:  time.Second,
        },
    )

    // Use it (retries automatically on failure)
    response, _ := resilientAgent.Process(ctx, message)
    ```

---

## Remote Communication

Connect to a remote agent over HTTP:

=== "Python"

    ```python
    from agenkit.adapters.python.remote_agent import RemoteAgent

    # Connect to remote agent
    remote_agent = RemoteAgent(
        name="remote-echo",
        endpoint="http://localhost:8080"
    )

    # Use it exactly like a local agent!
    response = await remote_agent.process(message)
    ```

=== "Go"

    ```go
    import "github.com/agenkit/agenkit-go/adapter/http"

    // Connect to remote agent
    remoteAgent := http.NewHTTPAgent(
        "remote-echo",
        "http://localhost:8080",
    )

    // Use it exactly like a local agent!
    response, _ := remoteAgent.Process(ctx, message)
    ```

---

## Composition

Combine multiple agents into a workflow:

=== "Python"

    ```python
    from agenkit.composition import SequentialAgent

    # Create a pipeline: validator → processor → formatter
    pipeline = SequentialAgent([
        ValidatorAgent(),
        ProcessorAgent(),
        FormatterAgent()
    ])

    # Process flows through all three
    result = await pipeline.process(message)
    ```

=== "Go"

    ```go
    import "github.com/agenkit/agenkit-go/composition"

    // Create a pipeline
    pipeline := composition.NewSequentialAgent([]agenkit.Agent{
        &ValidatorAgent{},
        &ProcessorAgent{},
        &FormatterAgent{},
    })

    // Process flows through all three
    result, _ := pipeline.Process(ctx, message)
    ```

---

## What's Next?

🎉 Congratulations! You've built your first Agenkit agent.

**Continue learning:**

- **[Architecture](../core-concepts/architecture.md)** - Understand how the layers work together
- **[Middleware Guide](../features/middleware.md)** - Add resilience and observability
- **[Composition Patterns](../features/composition.md)** - Build multi-agent workflows
- **[Examples](../examples/index.md)** - Explore 28+ comprehensive examples

**Ready for production?**

- **[Deployment Guide](../guides/deployment.md)** - Deploy with Docker and Kubernetes
- **[Observability Guide](../features/observability.md)** - Add tracing and metrics
- **[Best Practices](../guides/best-practices.md)** - Production patterns and tips
