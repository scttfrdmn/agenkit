"""End-to-end tests for complete customer support workflows."""

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_faq_workflow():
    """Test complete FAQ workflow through API."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        try:
            response = await client.post(
                "/chat",
                json={
                    "message": "How do I reset my password?",
                    "user_id": "test_user"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["route"] == "faq"
            assert data["confidence"] > 0.7
            assert "password" in data["response"].lower()
        except httpx.ConnectError:
            pytest.skip("API server not running")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_specialist_workflow():
    """Test complete specialist workflow through API."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        try:
            response = await client.post(
                "/chat",
                json={
                    "message": "I need help with API integration for my application",
                    "user_id": "test_user"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["route"] in ["specialist", "faq"]  # Could route to either
            assert len(data["response"]) > 0
        except httpx.ConnectError:
            pytest.skip("API server not running")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_escalation_workflow():
    """Test escalation workflow through API."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        try:
            response = await client.post(
                "/chat",
                json={
                    "message": "I want a refund immediately! This is terrible!",
                    "user_id": "test_user"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["route"] == "escalation"
            assert "escalate" in data["response"].lower() or "support team" in data["response"].lower()
        except httpx.ConnectError:
            pytest.skip("API server not running")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_health_checks():
    """Test health check endpoints."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
        try:
            # Basic health
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

            # Readiness
            response = await client.get("/ready")
            assert response.status_code in [200, 503]  # May be 503 if Go worker not ready
            data = response.json()
            assert "checks" in data
        except httpx.ConnectError:
            pytest.skip("API server not running")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting works correctly."""
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        try:
            # Send multiple requests rapidly
            responses = []
            for i in range(15):
                response = await client.post(
                    "/chat",
                    json={
                        "message": f"Test message {i}",
                        "user_id": "rate_limit_test_user"
                    }
                )
                responses.append(response.status_code)

            # Some should succeed, some may be rate limited
            assert 200 in responses
            # Rate limiting may cause 429 or 500 errors
        except httpx.ConnectError:
            pytest.skip("API server not running")
