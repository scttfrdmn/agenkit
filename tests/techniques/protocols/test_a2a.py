"""
Tests for Agent-to-Agent (A2A) Protocol.

Tests all A2A components:
- Message serialization/deserialization
- Protocol validation and utilities
- Agent communication
- Server request handling
- Discovery services
- Transport layers
- Platform adapters
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agenkit import Message
from agenkit.techniques.protocols.a2a import (  # Agent; Message types; Server; Protocol; Transport
    A2AAction,
    A2AAgent,
    A2ADiscoveryClient,
    A2AException,
    A2AMessage,
    A2AServer,
    AgentA2AServer,
    AgentInfo,
    AgentNotFoundError,
    BedrockAdapter,
    CapabilityNotSupportedError,
    ErrorCode,
    HTTPTransport,
    InMemoryDiscoveryService,
    MessagePriority,
    MessageType,
    TimeoutError,
    VertexAIAdapter,
    create_bedrock_agent,
    create_capabilities_response,
    create_notification,
    create_ping_response,
    create_request,
    create_status_response,
    create_transport,
    create_vertex_agent,
    validate_agent_id,
    validate_capability,
)

# ============================================================================
# Message Tests
# ============================================================================


class TestA2AMessage:
    """Test A2A message creation and serialization."""

    def test_create_request(self):
        """Test creating a request message."""
        message = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={"text": "Hello"}
        )

        assert message.message_type == MessageType.REQUEST
        assert message.from_agent == "agent-1"
        assert message.to_agent == "agent-2"
        assert message.action == "process"
        assert message.content == {"text": "Hello"}
        assert message.message_id is not None
        assert message.timestamp is not None

    def test_create_notification(self):
        """Test creating a notification message."""
        message = create_notification(
            from_agent="agent-1",
            to_agent="agent-2",
            action="status_update",
            content={"status": "ready"},
        )

        assert message.message_type == MessageType.NOTIFICATION
        assert message.from_agent == "agent-1"
        assert message.to_agent == "agent-2"
        assert message.action == "status_update"

    def test_message_to_dict(self):
        """Test message serialization to dict."""
        message = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={"data": "test"}
        )

        data = message.to_dict()

        assert data["message_type"] == "request"
        assert data["from_agent"] == "agent-1"
        assert data["to_agent"] == "agent-2"
        assert data["action"] == "process"
        assert data["content"] == {"data": "test"}
        assert "message_id" in data
        assert "timestamp" in data

    def test_message_from_dict(self):
        """Test message deserialization from dict."""
        data = {
            "message_type": "request",
            "from_agent": "agent-1",
            "to_agent": "agent-2",
            "action": "process",
            "content": {"data": "test"},
            "message_id": "msg-123",
            "timestamp": "2024-01-01T00:00:00Z",
        }

        message = A2AMessage.from_dict(data)

        assert message.message_type == MessageType.REQUEST
        assert message.from_agent == "agent-1"
        assert message.to_agent == "agent-2"
        assert message.action == "process"
        assert message.content == {"data": "test"}
        assert message.message_id == "msg-123"

    def test_create_response(self):
        """Test creating a response message."""
        request = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={"input": "test"}
        )

        response = request.create_response(content={"output": "result"})

        assert response.message_type == MessageType.RESPONSE
        assert response.from_agent == "agent-2"
        assert response.to_agent == "agent-1"
        assert response.correlation_id == request.message_id

    def test_create_error_response(self):
        """Test creating an error response."""
        request = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={}
        )

        error_response = request.create_error(
            error_code="PROCESSING_ERROR", error_message="Failed to process"
        )

        assert error_response.message_type == MessageType.ERROR
        assert error_response.content["error_code"] == "PROCESSING_ERROR"
        assert error_response.content["error_message"] == "Failed to process"
        assert error_response.correlation_id == request.message_id

    def test_to_agenkit_message(self):
        """Test conversion to Agenkit Message."""
        a2a_message = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={"text": "Hello"}
        )
        a2a_message.metadata = {"key": "value"}

        agenkit_message = a2a_message.to_agenkit_message()

        assert agenkit_message.role == "user"
        assert agenkit_message.content == "Hello"
        assert agenkit_message.metadata["a2a_action"] == "process"
        assert agenkit_message.metadata["a2a_from_agent"] == "agent-1"
        assert agenkit_message.metadata["key"] == "value"

    def test_from_agenkit_message(self):
        """Test conversion from Agenkit Message."""
        agenkit_message = Message(role="assistant", content="Response text")

        a2a_message = A2AMessage.from_agenkit_message(
            msg=agenkit_message, from_agent="agent-1", to_agent="agent-2"
        )

        assert a2a_message.from_agent == "agent-1"
        assert a2a_message.to_agent == "agent-2"
        assert a2a_message.content["role"] == "assistant"
        assert a2a_message.content["content"] == "Response text"

    def test_message_priority(self):
        """Test message priority."""
        high_priority = create_request(
            from_agent="agent-1",
            to_agent="agent-2",
            action="urgent",
            content={},
            priority=MessagePriority.HIGH,
        )

        assert high_priority.priority == MessagePriority.HIGH


class TestAgentInfo:
    """Test AgentInfo serialization."""

    def test_agent_info_creation(self):
        """Test creating agent info."""
        info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["text-analysis", "summarization"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        assert info.agent_id == "agent-1"
        assert info.name == "Test Agent"
        assert len(info.capabilities) == 2
        assert info.endpoint == "http://localhost:8080/a2a"

    def test_agent_info_to_dict(self):
        """Test agent info serialization."""
        info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        data = info.to_dict()

        assert data["agent_id"] == "agent-1"
        assert data["name"] == "Test Agent"
        assert data["capabilities"] == ["analysis"]

    def test_agent_info_from_dict(self):
        """Test agent info deserialization."""
        data = {
            "agent_id": "agent-1",
            "name": "Test Agent",
            "capabilities": ["analysis"],
            "endpoint": "http://localhost:8080/a2a",
            "transport": "http",
        }

        info = AgentInfo.from_dict(data)

        assert info.agent_id == "agent-1"
        assert info.name == "Test Agent"
        assert "analysis" in info.capabilities


# ============================================================================
# Protocol Tests
# ============================================================================


class TestProtocol:
    """Test protocol validation and utilities."""

    def test_validate_agent_id_valid(self):
        """Test valid agent ID."""
        assert validate_agent_id("agent-1") is True
        assert validate_agent_id("my-agent-123") is True
        assert validate_agent_id("agent_test") is True

    def test_validate_agent_id_invalid(self):
        """Test invalid agent ID."""
        assert validate_agent_id("") is False
        assert validate_agent_id("agent with spaces") is False

    def test_validate_capability_valid(self):
        """Test valid capability."""
        assert validate_capability("text-analysis") is True
        assert validate_capability("image-processing") is True
        assert validate_capability("data-transform") is True

    def test_validate_capability_invalid(self):
        """Test invalid capability."""
        assert validate_capability("") is False
        assert validate_capability("cap with spaces") is False
        assert validate_capability("UPPERCASE") is False

    def test_create_capabilities_response(self):
        """Test creating capabilities response."""
        capabilities = ["text-analysis", "summarization"]
        response_data = create_capabilities_response(capabilities)

        assert "capabilities" in response_data
        assert response_data["capabilities"] == capabilities
        assert "protocol_version" in response_data

    def test_create_status_response(self):
        """Test creating status response."""
        response_data = create_status_response(status="online", agent_id="agent-1")

        assert response_data["status"] == "online"
        assert response_data["agent_id"] == "agent-1"

    def test_create_ping_response(self):
        """Test creating ping response."""
        response_data = create_ping_response(agent_id="agent-1")

        assert response_data["agent_id"] == "agent-1"
        assert "timestamp" in response_data

    def test_error_codes(self):
        """Test error code enum."""
        assert ErrorCode.TIMEOUT.value == "408"
        assert ErrorCode.NOT_FOUND.value == "404"
        assert ErrorCode.PROTOCOL_ERROR.value == "600"

    def test_exceptions(self):
        """Test A2A exceptions."""
        with pytest.raises(A2AException):
            raise A2AException(ErrorCode.INTERNAL_ERROR, "Test error")

        with pytest.raises(TimeoutError):
            raise TimeoutError("Timeout")

        with pytest.raises(AgentNotFoundError):
            raise AgentNotFoundError("agent-1")

        with pytest.raises(CapabilityNotSupportedError):
            raise CapabilityNotSupportedError("unsupported-cap")


# ============================================================================
# Transport Tests
# ============================================================================


class TestTransport:
    """Test transport layer."""

    def test_create_http_transport(self):
        """Test creating HTTP transport."""
        transport = create_transport("http")
        assert isinstance(transport, HTTPTransport)

    def test_create_invalid_transport(self):
        """Test creating invalid transport."""
        with pytest.raises(ValueError, match=r"Unknown transport type"):
            create_transport("invalid")

    @pytest.mark.asyncio
    async def test_http_transport_send(self):
        """Test HTTP transport send."""
        transport = HTTPTransport()
        message = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={"text": "test"}
        )

        # Mock httpx
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "message_type": "response",
                "from_agent": "agent-2",
                "to_agent": "agent-1",
                "content": {"result": "ok"},
                "message_id": "msg-2",
                "timestamp": "2024-01-01T00:00:00Z",
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            response = await transport.send(message, "http://localhost:8080/a2a")

            assert response.message_type == MessageType.RESPONSE
            assert response.content["result"] == "ok"


# ============================================================================
# Agent Tests
# ============================================================================


class TestA2AAgent:
    """Test A2A agent."""

    @pytest.mark.asyncio
    async def test_agent_creation(self):
        """Test creating A2A agent."""
        agent = A2AAgent(agent_id="agent-1", capabilities=["text-analysis"], transport="http")

        assert agent.agent_id == "agent-1"
        assert "text-analysis" in agent.capabilities
        assert agent.transport_type == "http"

    @pytest.mark.asyncio
    async def test_agent_send(self):
        """Test agent send message."""
        agent = A2AAgent(agent_id="agent-1", capabilities=["analysis"], transport="http")

        message = create_request(
            from_agent="agent-1", to_agent="agent-2", action="process", content={"text": "test"}
        )

        # Mock transport
        with patch.object(agent.transport, "send") as mock_send:
            response_msg = message.create_response(content={"result": "ok"})
            mock_send.return_value = response_msg

            response = await agent.send(message, "http://localhost:8080/a2a")

            assert response.message_type == MessageType.RESPONSE
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_discover(self):
        """Test agent discovery."""
        agent = A2AAgent(
            agent_id="agent-1",
            capabilities=["analysis"],
            transport="http",
            discovery_url="http://localhost:9000",
        )

        # Mock discovery client
        mock_agent_info = AgentInfo(
            agent_id="agent-2",
            name="Test Agent",
            capabilities=["summarization"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        with patch(
            "agenkit.techniques.protocols.a2a.discovery.A2ADiscoveryClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.discover = AsyncMock(return_value=[mock_agent_info])
            mock_client_class.return_value = mock_client

            # Discover agents
            agents = await agent.discover("summarization")

            assert len(agents) == 1
            assert agents[0].agent_id == "agent-2"

    @pytest.mark.asyncio
    async def test_agent_send_to_agent_with_discovery(self):
        """Test sending to agent by ID using discovery."""
        agent = A2AAgent(
            agent_id="agent-1",
            capabilities=["analysis"],
            transport="http",
            discovery_url="http://localhost:9000",
        )

        # Mock discovery
        mock_agent_info = AgentInfo(
            agent_id="agent-2",
            name="Target Agent",
            capabilities=["processing"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        with patch(
            "agenkit.techniques.protocols.a2a.discovery.A2ADiscoveryClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_client.find_by_id = AsyncMock(return_value=[mock_agent_info])
            mock_client_class.return_value = mock_client

            # Mock transport
            with patch.object(agent.transport, "send") as mock_send:
                response_msg = create_request(
                    from_agent="agent-2", to_agent="agent-1", action="process", content={}
                ).create_response(content={"result": "ok"})
                mock_send.return_value = response_msg

                response = await agent.send_to_agent(
                    to_agent="agent-2", action="process", content={"data": "test"}
                )

                assert response.content["result"] == "ok"


# ============================================================================
# Server Tests
# ============================================================================


class TestA2AServer:
    """Test A2A server."""

    @pytest.mark.asyncio
    async def test_server_creation(self):
        """Test creating A2A server."""
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value=Message(role="assistant", content="result"))

        server = A2AServer(agent_id="agent-1", agent=mock_agent, capabilities=["processing"])

        assert server.agent_id == "agent-1"
        assert "processing" in server.capabilities

    @pytest.mark.asyncio
    async def test_server_handle_ping(self):
        """Test server handling ping."""
        mock_agent = Mock()
        server = A2AServer(agent_id="agent-1", agent=mock_agent, capabilities=["processing"])

        request = create_request(
            from_agent="agent-2", to_agent="agent-1", action=A2AAction.PING.value, content={}
        )

        response = await server.handle_message(request)

        assert response.message_type == MessageType.RESPONSE
        assert response.content["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_server_handle_capabilities(self):
        """Test server handling capabilities request."""
        mock_agent = Mock()
        server = A2AServer(
            agent_id="agent-1", agent=mock_agent, capabilities=["text-analysis", "summarization"]
        )

        request = create_request(
            from_agent="agent-2",
            to_agent="agent-1",
            action=A2AAction.CAPABILITIES.value,
            content={},
        )

        response = await server.handle_message(request)

        assert response.message_type == MessageType.RESPONSE
        assert "text-analysis" in response.content["capabilities"]
        assert "summarization" in response.content["capabilities"]

    @pytest.mark.asyncio
    async def test_server_handle_status(self):
        """Test server handling status request."""
        mock_agent = Mock()
        server = A2AServer(agent_id="agent-1", agent=mock_agent, capabilities=["processing"])

        request = create_request(
            from_agent="agent-2", to_agent="agent-1", action=A2AAction.STATUS.value, content={}
        )

        response = await server.handle_message(request)

        assert response.message_type == MessageType.RESPONSE
        assert response.content["status"] == "offline"  # Server not started yet
        assert response.content["agent_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_server_handle_process(self):
        """Test server handling process request."""
        mock_agent = Mock()
        mock_agent.process = AsyncMock(
            return_value=Message(role="assistant", content="Processed result")
        )

        server = A2AServer(agent_id="agent-1", agent=mock_agent, capabilities=["processing"])

        request = create_request(
            from_agent="agent-2",
            to_agent="agent-1",
            action=A2AAction.PROCESS.value,
            content={"text": "input data"},
        )

        response = await server.handle_message(request)

        assert response.message_type == MessageType.RESPONSE
        assert response.content["role"] == "assistant"
        assert response.content["content"] == "Processed result"
        mock_agent.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_a2a_server_wrapper(self):
        """Test AgentA2AServer convenience wrapper."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["processing"]
        mock_agent.process = AsyncMock(return_value=Message(role="assistant", content="ok"))

        wrapper = AgentA2AServer(agent=mock_agent)

        assert wrapper.server.agent_id == "test-agent"
        assert "processing" in wrapper.server.capabilities


# ============================================================================
# Discovery Tests
# ============================================================================


class TestInMemoryDiscoveryService:
    """Test in-memory discovery service."""

    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test registering an agent."""
        service = InMemoryDiscoveryService()

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        await service.register(agent_info)

        agents = await service.list_all()
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_unregister_agent(self):
        """Test unregistering an agent."""
        service = InMemoryDiscoveryService()

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        await service.register(agent_info)
        await service.unregister("agent-1")

        agents = await service.list_all()
        assert len(agents) == 0

    @pytest.mark.asyncio
    async def test_discover_by_capability(self):
        """Test discovering agents by capability."""
        service = InMemoryDiscoveryService()

        # Register agents with different capabilities
        agent1 = AgentInfo(
            agent_id="agent-1",
            name="Analyzer",
            capabilities=["text-analysis", "sentiment"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )
        agent2 = AgentInfo(
            agent_id="agent-2",
            name="Summarizer",
            capabilities=["summarization", "text-analysis"],
            endpoint="http://localhost:8081/a2a",
            transport="http",
        )

        await service.register(agent1)
        await service.register(agent2)

        # Discover by text-analysis
        agents = await service.discover("text-analysis")
        assert len(agents) == 2

        # Discover by sentiment
        agents = await service.discover("sentiment")
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-1"

        # Discover by summarization
        agents = await service.discover("summarization")
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-2"

    @pytest.mark.asyncio
    async def test_find_by_id(self):
        """Test finding agent by ID."""
        service = InMemoryDiscoveryService()

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        await service.register(agent_info)

        # Find existing agent
        agents = await service.find_by_id("agent-1")
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-1"

        # Find non-existing agent
        agents = await service.find_by_id("agent-999")
        assert len(agents) == 0

    @pytest.mark.asyncio
    async def test_update_status(self):
        """Test updating agent status."""
        service = InMemoryDiscoveryService()

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
            status="online",
        )

        await service.register(agent_info)
        await service.update_status("agent-1", "busy")

        agents = await service.find_by_id("agent-1")
        assert agents[0].status == "busy"

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        """Test heartbeat."""
        service = InMemoryDiscoveryService()

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        await service.register(agent_info)

        # Heartbeat for existing agent
        await service.heartbeat("agent-1")

        # Heartbeat for non-existing agent
        with pytest.raises(KeyError):
            await service.heartbeat("agent-999")

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all registrations."""
        service = InMemoryDiscoveryService()

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        await service.register(agent_info)
        service.clear()

        agents = await service.list_all()
        assert len(agents) == 0


class TestA2ADiscoveryClient:
    """Test A2A discovery client."""

    @pytest.mark.asyncio
    async def test_discovery_client_creation(self):
        """Test creating discovery client."""
        client = A2ADiscoveryClient("http://localhost:8080")
        assert client.service_url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_register(self):
        """Test registering with discovery service."""
        client = A2ADiscoveryClient("http://localhost:8080")

        agent_info = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            capabilities=["analysis"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            await client.register(agent_info)

    @pytest.mark.asyncio
    async def test_discover(self):
        """Test discovering agents."""
        client = A2ADiscoveryClient("http://localhost:8080")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {
                "agents": [
                    {
                        "agent_id": "agent-1",
                        "name": "Test Agent",
                        "capabilities": ["analysis"],
                        "endpoint": "http://localhost:8080/a2a",
                        "transport": "http",
                    }
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            agents = await client.discover("analysis")

            assert len(agents) == 1
            assert agents[0].agent_id == "agent-1"


# ============================================================================
# Platform Adapter Tests
# ============================================================================


class TestVertexAIAdapter:
    """Test Vertex AI adapter."""

    def test_adapter_creation(self):
        """Test creating Vertex AI adapter."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["analysis"]

        adapter = VertexAIAdapter.from_agent(
            agent=mock_agent, project_id="my-project", location="us-central1"
        )

        assert adapter.agent_id == "test-agent"
        assert adapter.project_id == "my-project"
        assert adapter.location == "us-central1"

    def test_get_vertex_config(self):
        """Test getting Vertex AI configuration."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["analysis"]

        adapter = VertexAIAdapter.from_agent(
            agent=mock_agent, project_id="my-project", location="us-central1"
        )

        config = adapter.get_vertex_config()

        assert config["agent_id"] == "test-agent"
        assert config["project_id"] == "my-project"
        assert config["location"] == "us-central1"
        assert config["protocol"] == "a2a"

    def test_create_vertex_agent_convenience(self):
        """Test convenience function."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["analysis"]

        adapter = create_vertex_agent(agent=mock_agent, project_id="my-project")

        assert isinstance(adapter, VertexAIAdapter)
        assert adapter.project_id == "my-project"


class TestBedrockAdapter:
    """Test Bedrock adapter."""

    def test_adapter_creation(self):
        """Test creating Bedrock adapter."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["analysis"]

        adapter = BedrockAdapter.from_agent(agent=mock_agent, region="us-east-1")

        assert adapter.agent_id == "test-agent"
        assert adapter.region == "us-east-1"

    def test_get_bedrock_config(self):
        """Test getting Bedrock configuration."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["analysis"]

        adapter = BedrockAdapter.from_agent(
            agent=mock_agent, region="us-east-1", account_id="123456789012"
        )

        config = adapter.get_bedrock_config()

        assert config["agent_id"] == "test-agent"
        assert config["region"] == "us-east-1"
        assert config["account_id"] == "123456789012"
        assert config["protocol"] == "a2a"

    def test_create_bedrock_agent_convenience(self):
        """Test convenience function."""
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.capabilities = ["analysis"]

        adapter = create_bedrock_agent(agent=mock_agent, region="us-west-2")

        assert isinstance(adapter, BedrockAdapter)
        assert adapter.region == "us-west-2"


# ============================================================================
# Integration Tests
# ============================================================================


class TestA2AIntegration:
    """End-to-end integration tests."""

    @pytest.mark.asyncio
    async def test_agent_to_agent_communication(self):
        """Test full agent-to-agent communication flow."""
        # Create discovery service
        discovery = InMemoryDiscoveryService()

        # Create mock Agenkit agent
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value=Message(role="assistant", content="Processed"))

        # Create A2A server
        server = A2AServer(agent_id="agent-2", agent=mock_agent, capabilities=["processing"])

        # Register agent-2
        agent2_info = AgentInfo(
            agent_id="agent-2",
            name="Processor",
            capabilities=["processing"],
            endpoint="http://localhost:8080/a2a",
            transport="http",
        )
        await discovery.register(agent2_info)

        # Create A2A client agent
        client_agent = A2AAgent(agent_id="agent-1", capabilities=["analysis"], transport="http")
        client_agent._discovery_service = discovery

        # Create request
        request = create_request(
            from_agent="agent-1",
            to_agent="agent-2",
            action=A2AAction.PROCESS.value,
            content={"text": "input data"},
        )

        # Server processes request
        response = await server.handle_message(request)

        # Verify response
        assert response.message_type == MessageType.RESPONSE
        assert response.from_agent == "agent-2"
        assert response.to_agent == "agent-1"
        assert response.content["role"] == "assistant"
        assert response.content["content"] == "Processed"
        mock_agent.process.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovery_and_communication(self):
        """Test discovering and communicating with agents."""
        # Create discovery service
        discovery = InMemoryDiscoveryService()

        # Register multiple agents
        for i in range(1, 4):
            agent_info = AgentInfo(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                capabilities=["processing"] if i % 2 == 0 else ["analysis"],
                endpoint=f"http://localhost:808{i}/a2a",
                transport="http",
            )
            await discovery.register(agent_info)

        # Discover processing agents
        agents = await discovery.discover("processing")
        assert len(agents) == 1
        assert agents[0].agent_id == "agent-2"

        # Discover analysis agents
        agents = await discovery.discover("analysis")
        assert len(agents) == 2

    @pytest.mark.asyncio
    async def test_platform_adapter_workflow(self):
        """Test platform adapter workflow."""
        # Create mock agent
        mock_agent = Mock()
        mock_agent.name = "my_agent"
        mock_agent.capabilities = ["text-processing"]
        mock_agent.process = AsyncMock(return_value=Message(role="assistant", content="result"))

        # Create Vertex AI adapter
        vertex_adapter = VertexAIAdapter.from_agent(
            agent=mock_agent, project_id="test-project", location="us-central1"
        )

        # Verify configuration
        config = vertex_adapter.get_vertex_config()
        assert config["project_id"] == "test-project"
        assert "text-processing" in config["capabilities"]

        # Test server can handle messages
        request = create_request(
            from_agent="external",
            to_agent=vertex_adapter.agent_id,
            action=A2AAction.PROCESS.value,
            content={"text": "test"},
        )

        response = await vertex_adapter.server.handle_message(request)
        assert response.message_type == MessageType.RESPONSE
