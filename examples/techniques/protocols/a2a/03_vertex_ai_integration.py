"""
Google Cloud Vertex AI Integration Example.

Demonstrates:
- Wrapping Agenkit agents for Vertex AI
- Configuring Vertex AI deployment
- A2A protocol integration with Vertex AI Agent Builder

Note: This example shows the setup. Actual deployment requires:
- Google Cloud Project with Vertex AI enabled
- Proper authentication (gcloud auth or service account)
- google-cloud-aiplatform SDK (pip install google-cloud-aiplatform)
"""

import asyncio

from agenkit import Message
from agenkit.techniques.protocols.a2a import A2AAction, VertexAIAdapter, create_request

# ==============================================================================
# Custom Agent for Vertex AI
# ==============================================================================


class CustomerSupportAgent:
    """
    Customer support agent that can be deployed to Vertex AI.
    """

    def __init__(self):
        self.name = "customer_support_agent"
        self.capabilities = ["question-answering", "customer-support", "order-tracking"]

    async def process(self, message: Message) -> Message:
        """Process customer support inquiries."""
        query = message.content.lower()

        # Simple demo responses
        if "order" in query or "tracking" in query:
            response = (
                "I can help you track your order. "
                "Please provide your order number (format: ORD-XXXXX)."
            )
        elif "return" in query or "refund" in query:
            response = (
                "I can assist with returns and refunds. "
                "Our return policy allows returns within 30 days of purchase."
            )
        elif "shipping" in query:
            response = (
                "We offer free shipping on orders over $50. "
                "Standard shipping takes 5-7 business days."
            )
        elif "hello" in query or "hi" in query:
            response = "Hello! I'm your customer support assistant. How can I help you today?"
        else:
            response = (
                "I'm here to help! I can assist with orders, "
                "returns, shipping, and general inquiries."
            )

        return Message(role="assistant", content=response, metadata={"support_type": "general"})


# ==============================================================================
# Example: Vertex AI Integration
# ==============================================================================


async def vertex_ai_integration_example():
    """Demonstrate Vertex AI integration."""

    print("=" * 70)
    print("Vertex AI Integration Example")
    print("=" * 70)

    # Create custom agent
    agent = CustomerSupportAgent()

    print("\n1. Creating Vertex AI adapter...")

    # Create Vertex AI adapter
    adapter = VertexAIAdapter.from_agent(
        agent=agent,
        project_id="my-gcp-project",  # Your GCP project ID
        location="us-central1",  # GCP region
        agent_id="customer-support-001",
        capabilities=agent.capabilities,
    )

    print(f"   Agent ID: {adapter.agent_id}")
    print(f"   Project: {adapter.project_id}")
    print(f"   Location: {adapter.location}")
    print(f"   Capabilities: {', '.join(adapter.capabilities)}")

    # Get Vertex AI configuration
    print("\n2. Vertex AI configuration:")
    config = adapter.get_vertex_config()
    for key, value in config.items():
        print(f"   {key}: {value}")

    # Test the agent before deployment
    print("\n3. Testing agent locally (before Vertex AI deployment)...")

    test_queries = [
        "Hello!",
        "How can I track my order?",
        "What is your return policy?",
        "Do you offer free shipping?",
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
To deploy this agent to Vertex AI:

1. Install required dependencies:
   pip install google-cloud-aiplatform

2. Authenticate with Google Cloud:
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID

3. Deploy the agent:

   # In your application code:
   async def deploy():
       adapter = VertexAIAdapter.from_agent(
           agent=agent,
           project_id="your-project-id",
           location="us-central1"
       )

       # Start A2A server (listens for Vertex AI connections)
       await adapter.deploy(host="0.0.0.0", port=8080)

   asyncio.run(deploy())

4. Register with Vertex AI Agent Builder:
   - Go to: https://console.cloud.google.com/vertex-ai/agents
   - Create new agent or add to existing agent
   - Register your A2A endpoint: http://YOUR_HOST:8080/a2a
   - Configure agent capabilities and actions

5. Test integration:
   - Use Vertex AI console to test your agent
   - Agent will receive A2A messages from Vertex AI
   - Responses will be sent back via A2A protocol

For production deployment:
- Use Cloud Run or GKE for hosting
- Enable HTTPS with SSL certificates
- Configure authentication (service account)
- Set up monitoring and logging
- Implement retry logic and error handling
"""
    )

    # Create convenience function example
    print("\n" + "=" * 70)
    print("CONVENIENCE FUNCTION EXAMPLE")
    print("=" * 70)

    print(
        """
You can also use the convenience function:

    from agenkit.techniques.protocols.a2a import create_vertex_agent

    # Quick setup
    adapter = create_vertex_agent(
        agent=your_agent,
        project_id="your-project-id",
        location="us-central1"
    )

    # Deploy
    await adapter.deploy(port=8080)
"""
    )

    print("\n" + "=" * 70)
    print("Example completed successfully!")
    print("=" * 70)


# ==============================================================================
# Run Example
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(vertex_ai_integration_example())
