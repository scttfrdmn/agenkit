# Agent-to-Agent (A2A) Protocol Examples

This directory contains comprehensive examples demonstrating the Agent-to-Agent (A2A) protocol for cross-platform agent communication.

## Overview

The A2A protocol enables seamless communication between AI agents across different platforms, frameworks, and cloud services. These examples show you how to:

- Create A2A-enabled agents
- Send and receive messages between agents
- Use discovery services for agent coordination
- Integrate with cloud platforms (Vertex AI, AWS Bedrock)
- Implement custom message handlers
- Build multi-agent workflows

## Examples

### 1. Basic Communication (`01_basic_communication.py`)

**What it demonstrates:**
- Creating A2A-enabled agents
- Wrapping agents as A2A servers
- Standard protocol actions (PING, CAPABILITIES, STATUS, PROCESS)
- Request-response message patterns

**Run it:**
```bash
python examples/techniques/protocols/a2a/01_basic_communication.py
```

**Key concepts:**
- `A2AServer`: Wraps an Agenkit agent to handle A2A messages
- `A2AAgent`: Client agent for sending A2A messages
- `create_request()`: Creates request messages
- Standard actions: PING, CAPABILITIES, STATUS, PROCESS

### 2. Multi-Agent Discovery (`02_multi_agent_discovery.py`)

**What it demonstrates:**
- Agent registration with discovery service
- Discovering agents by capability
- Coordinating multiple specialized agents
- Agent status management

**Run it:**
```bash
python examples/techniques/protocols/a2a/02_multi_agent_discovery.py
```

**Key concepts:**
- `InMemoryDiscoveryService`: Service for agent registration and discovery
- `AgentInfo`: Agent metadata (ID, capabilities, endpoint)
- Capability-based discovery
- Multi-agent workflows (Analyze → Summarize → Translate)

### 3. Vertex AI Integration (`03_vertex_ai_integration.py`)

**What it demonstrates:**
- Wrapping Agenkit agents for Google Cloud Vertex AI
- Configuration for Vertex AI deployment
- A2A protocol integration with Vertex AI Agent Builder

**Run it:**
```bash
python examples/techniques/protocols/a2a/03_vertex_ai_integration.py
```

**Key concepts:**
- `VertexAIAdapter`: Wrapper for Vertex AI integration
- `create_vertex_agent()`: Convenience function
- Deployment configuration (project, location, endpoint)
- Local testing before cloud deployment

**Requirements:**
- Google Cloud project with Vertex AI enabled
- `google-cloud-aiplatform` SDK (for actual deployment)

### 4. Bedrock Integration (`04_bedrock_integration.py`)

**What it demonstrates:**
- Wrapping Agenkit agents for AWS Bedrock
- Configuration for Bedrock deployment
- A2A protocol integration with AWS Bedrock Agents

**Run it:**
```bash
python examples/techniques/protocols/a2a/04_bedrock_integration.py
```

**Key concepts:**
- `BedrockAdapter`: Wrapper for Bedrock integration
- `create_bedrock_agent()`: Convenience function
- Deployment configuration (region, account, endpoint)
- Integration architecture

**Requirements:**
- AWS account with Bedrock enabled
- `boto3` SDK (for actual deployment)
- Proper IAM permissions

### 5. Custom Handlers (`05_custom_handlers.py`)

**What it demonstrates:**
- Registering custom action handlers
- Handling different message types
- Error handling and responses
- Agent collaboration patterns

**Run it:**
```bash
python examples/techniques/protocols/a2a/05_custom_handlers.py
```

**Key concepts:**
- `@agent.on_action()`: Register custom handlers
- `message.create_response()`: Create success responses
- `message.create_error()`: Create error responses
- Custom actions (store, retrieve, aggregate)
- Notifications (fire-and-forget)

## Running All Examples

To run all examples in sequence:

```bash
# Run all examples
for example in examples/techniques/protocols/a2a/0*.py; do
    echo "Running $example..."
    python "$example"
    echo ""
done
```

## A2A Protocol Basics

### Message Structure

Every A2A message contains:

```python
{
    "message_id": "unique-uuid",
    "from_agent": "sender-id",
    "to_agent": "recipient-id",
    "message_type": "request|response|notification|error",
    "action": "process|query|command|...",
    "content": {"key": "value"},
    "metadata": {},
    "correlation_id": "parent-message-id",
    "timestamp": "2024-01-01T00:00:00Z",
}
```

### Standard Actions

- **PING**: Health check
- **CAPABILITIES**: Get agent capabilities
- **STATUS**: Get agent status
- **PROCESS**: Process content (main action)
- **QUERY**: Query for information
- **COMMAND**: Execute command
- **DELEGATE**: Delegate task to specialist
- **COLLABORATE**: Collaborative work

### Message Types

- **REQUEST**: Expects a response
- **RESPONSE**: Reply to a request
- **NOTIFICATION**: No response expected
- **ERROR**: Error response

## Integration Patterns

### 1. Simple Request-Response

```python
from agenkit.techniques.protocols.a2a import create_request, A2AServer

# Client sends request
request = create_request(
    from_agent="client-001", to_agent="server-001", action="process", content={"text": "Hello"}
)

# Server processes
response = await server.handle_message(request)
```

### 2. Discovery-Based Communication

```python
from agenkit.techniques.protocols.a2a import InMemoryDiscoveryService

# Register agents
await discovery.register(agent_info)

# Discover by capability
agents = await discovery.discover("summarization")

# Send to discovered agent
response = await client.send_to_agent(
    to_agent=agents[0].agent_id, action="process", content={"text": "Document..."}
)
```

### 3. Custom Handler Pattern

```python
from agenkit.techniques.protocols.a2a import A2AAgent

agent = A2AAgent(agent_id="custom-001", capabilities=["data"])


@agent.on_action("store")
async def handle_store(message):
    # Custom logic
    return message.create_response({"status": "stored"})
```

### 4. Cloud Platform Integration

```python
from agenkit.techniques.protocols.a2a import create_vertex_agent

# Vertex AI
adapter = create_vertex_agent(agent=my_agent, project_id="my-project", location="us-central1")
await adapter.deploy(port=8080)
```

```python
from agenkit.techniques.protocols.a2a import create_bedrock_agent

# AWS Bedrock
adapter = create_bedrock_agent(agent=my_agent, region="us-east-1")
await adapter.deploy(port=8080)
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│              A2A Protocol Layer                 │
│  (Messages, Transport, Discovery, Adapters)     │
└─────────────────┬───────────────────────────────┘
                  │
       ┌──────────┼──────────┐
       │          │          │
┌──────▼─────┐ ┌──▼────────┐ ┌─▼──────────┐
│   Agent    │ │  Agent    │ │   Agent    │
│  (Python)  │ │  (Cloud)  │ │ (Framework)│
└────────────┘ └───────────┘ └────────────┘
```

## Best Practices

1. **Always validate agent IDs**: Use alphanumeric + hyphens/underscores
2. **Use capability-based discovery**: Makes agents discoverable
3. **Handle errors gracefully**: Return proper error responses
4. **Test locally first**: Before deploying to cloud platforms
5. **Use meaningful action names**: Follow verb-noun pattern (e.g., "store-data", "analyze-text")
6. **Set appropriate timeouts**: Default is 30s, adjust based on use case
7. **Implement retry logic**: For production systems
8. **Monitor message flow**: Log requests/responses for debugging

## Troubleshooting

### Common Issues

**Issue: Agent not found**
- Solution: Ensure agent is registered with discovery service
- Check: Agent ID matches exactly

**Issue: Timeout errors**
- Solution: Increase timeout or optimize agent processing
- Check: Agent is actually running and reachable

**Issue: Invalid message format**
- Solution: Use `create_request()` helper functions
- Check: All required fields are present

**Issue: Cloud deployment fails**
- Solution: Verify credentials and permissions
- Check: Endpoint is publicly accessible (firewall rules)

## Further Reading

- [A2A Protocol Specification](../../docs/protocols/a2a_specification.md)
- [Agent Patterns Guide](../../docs/patterns/)
- [Agenkit Documentation](https://github.com/scttfrdmn/agenkit)
- [Vertex AI Agent Builder](https://cloud.google.com/vertex-ai/docs/agents)
- [AWS Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

## Contributing

Found a bug or have a suggestion? Please open an issue on the [Agenkit repository](https://github.com/scttfrdmn/agenkit/issues).

## License

These examples are part of the Agenkit project and are provided under the same license.
