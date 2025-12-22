"""
AWS Bedrock Integration Example.

Demonstrates:
- Wrapping Agenkit agents for AWS Bedrock
- Configuring Bedrock deployment
- A2A protocol integration with AWS Bedrock Agents

Note: This example shows the setup. Actual deployment requires:
- AWS Account with Bedrock enabled
- Proper IAM permissions and authentication
- boto3 SDK (pip install boto3)
"""

import asyncio

from agenkit import Message
from agenkit.techniques.protocols.a2a import (
    A2AAction,
    BedrockAdapter,
    create_request,
)

# ==============================================================================
# Custom Agent for Bedrock
# ==============================================================================


class TravelAssistantAgent:
    """
    Travel assistant agent that can be deployed to AWS Bedrock.
    """

    def __init__(self):
        self.name = "travel_assistant_agent"
        self.capabilities = ["travel-planning", "booking-assistance", "destination-info"]

    async def process(self, message: Message) -> Message:
        """Process travel-related queries."""
        query = message.content.lower()

        # Simple demo responses
        if "flight" in query or "flights" in query:
            response = (
                "I can help you search for flights. "
                "Please provide: departure city, destination, and travel dates."
            )
        elif "hotel" in query or "accommodation" in query:
            response = (
                "I can assist with hotel bookings. "
                "What city are you traveling to and what are your check-in dates?"
            )
        elif "weather" in query:
            response = (
                "I can provide weather information for your destination. "
                "Which city would you like to know about?"
            )
        elif "recommend" in query or "suggestion" in query:
            response = (
                "I'd be happy to recommend destinations! "
                "What type of trip are you planning? (Beach, City, Adventure, etc.)"
            )
        elif "hello" in query or "hi" in query:
            response = (
                "Hello! I'm your travel assistant. "
                "I can help with flights, hotels, destinations, and travel planning."
            )
        else:
            response = (
                "I'm here to help with your travel needs! "
                "I can assist with flights, hotels, destination info, and recommendations."
            )

        return Message(role="assistant", content=response, metadata={"assistance_type": "travel"})


# ==============================================================================
# Example: Bedrock Integration
# ==============================================================================


async def bedrock_integration_example():
    """Demonstrate AWS Bedrock integration."""

    print("=" * 70)
    print("AWS Bedrock Integration Example")
    print("=" * 70)

    # Create custom agent
    agent = TravelAssistantAgent()

    print("\n1. Creating Bedrock adapter...")

    # Create Bedrock adapter
    adapter = BedrockAdapter.from_agent(
        agent=agent,
        region="us-east-1",  # AWS region
        agent_id="travel-assistant-001",
        capabilities=agent.capabilities,
        account_id="123456789012",  # Your AWS account ID (optional)
    )

    print(f"   Agent ID: {adapter.agent_id}")
    print(f"   Region: {adapter.region}")
    if adapter.account_id:
        print(f"   Account ID: {adapter.account_id}")
    print(f"   Capabilities: {', '.join(adapter.capabilities)}")

    # Get Bedrock configuration
    print("\n2. Bedrock configuration:")
    config = adapter.get_bedrock_config()
    for key, value in config.items():
        print(f"   {key}: {value}")

    # Test the agent before deployment
    print("\n3. Testing agent locally (before Bedrock deployment)...")

    test_queries = [
        "Hello!",
        "I need to book a flight",
        "Can you recommend a beach destination?",
        "What's the weather like in Paris?",
        "Help me find a hotel in Tokyo",
    ]

    for query in test_queries:
        print(f"\n   Query: {query}")

        # Create A2A request
        request = create_request(
            from_agent="test-client",
            to_agent=adapter.agent_id,
            action=A2AAction.PROCESS.value,
            content={"text": query},
        )

        # Process through adapter's server
        response = await adapter.server.handle_message(request)

        print(f"   Response: {response.content['content']}")

    # Show deployment instructions
    print("\n" + "=" * 70)
    print("DEPLOYMENT INSTRUCTIONS")
    print("=" * 70)

    print(
        """
To deploy this agent to AWS Bedrock:

1. Install required dependencies:
   pip install boto3

2. Configure AWS credentials:
   aws configure
   # Or set environment variables:
   # AWS_ACCESS_KEY_ID=...
   # AWS_SECRET_ACCESS_KEY=...
   # AWS_DEFAULT_REGION=us-east-1

3. Deploy the agent:

   # In your application code:
   async def deploy():
       adapter = BedrockAdapter.from_agent(
           agent=agent,
           region="us-east-1",
           agent_id="travel-assistant-001"
       )

       # Start A2A server (listens for Bedrock connections)
       await adapter.deploy(host="0.0.0.0", port=8080)

   asyncio.run(deploy())

4. Register with AWS Bedrock Agents:

   Option A - AWS Console:
   - Go to: https://console.aws.amazon.com/bedrock/home#/agents
   - Create new agent or add to existing agent
   - Configure agent action group with your A2A endpoint
   - Add endpoint: http://YOUR_HOST:8080/a2a
   - Define agent capabilities and actions

   Option B - AWS CLI:
   aws bedrock-agent create-agent \\
       --agent-name "TravelAssistant" \\
       --description "AI travel assistant" \\
       --foundation-model "anthropic.claude-v2"

   aws bedrock-agent create-agent-action-group \\
       --agent-id AGENT_ID \\
       --agent-version DRAFT \\
       --action-group-name "TravelActions" \\
       --action-group-executor http://YOUR_HOST:8080/a2a

5. Test integration:
   - Use Bedrock console to test your agent
   - Agent will receive A2A messages from Bedrock
   - Responses will be sent back via A2A protocol

For production deployment:
- Use AWS Lambda + API Gateway or ECS for hosting
- Enable HTTPS with AWS Certificate Manager
- Configure IAM roles and policies
- Set up CloudWatch monitoring and logging
- Implement API Gateway rate limiting
- Use AWS Secrets Manager for credentials
"""
    )

    # Create convenience function example
    print("\n" + "=" * 70)
    print("CONVENIENCE FUNCTION EXAMPLE")
    print("=" * 70)

    print(
        """
You can also use the convenience function:

    from agenkit.techniques.protocols.a2a import create_bedrock_agent

    # Quick setup
    adapter = create_bedrock_agent(
        agent=your_agent,
        region="us-east-1"
    )

    # Deploy
    await adapter.deploy(port=8080)
"""
    )

    # Show integration architecture
    print("\n" + "=" * 70)
    print("INTEGRATION ARCHITECTURE")
    print("=" * 70)

    print(
        """
Architecture Overview:

┌─────────────────┐
│  AWS Bedrock    │
│     Agent       │
└────────┬────────┘
         │ A2A Protocol
         │ (HTTP/JSON)
         v
┌─────────────────┐
│  A2A Server     │
│  (Your Host)    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Agenkit Agent  │
│  (Python)       │
└─────────────────┘

Benefits:
- Seamless integration with AWS Bedrock ecosystem
- Use existing Agenkit agents without modification
- Standard A2A protocol for interoperability
- Easy to test locally before deployment
- Supports all Bedrock features (guardrails, knowledge bases, etc.)
"""
    )

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


# ==============================================================================
# Run Example
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(bedrock_integration_example())
