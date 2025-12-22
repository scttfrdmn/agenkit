package http

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// TestAgent is a simple test agent for testing
type testHealthAgent struct{}

func (a *testHealthAgent) Name() string {
	return "test-agent"
}

func (a *testHealthAgent) Capabilities() []string {
	return []string{}
}

func (a *testHealthAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *testHealthAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "assistant",
		Content: "Echo: " + message.Content,
	}, nil
}

func TestHealthEndpoint(t *testing.T) {
	agent := &testHealthAgent{}
	httpAgent := NewHTTPAgent(agent, "localhost:8080")

	// Create a request
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()

	// Call handler
	httpAgent.handleHealth(rec, req)

	// Check response
	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	// Parse JSON response
	var data map[string]interface{}
	if err := json.Unmarshal(rec.Body.Bytes(), &data); err != nil {
		t.Fatalf("Failed to parse JSON response: %v", err)
	}

	// Verify response structure
	if status, ok := data["status"].(string); !ok || status != "healthy" {
		t.Errorf("Expected status=healthy, got %v", data["status"])
	}

	if version, ok := data["version"].(string); !ok || version != AgenkitVersion {
		t.Errorf("Expected version=%s, got %v", AgenkitVersion, data["version"])
	}

	if _, ok := data["uptime"]; !ok {
		t.Error("Missing uptime in health response")
	}

	if agentName, ok := data["agent"].(string); !ok || agentName != "test-agent" {
		t.Errorf("Expected agent=test-agent, got %v", data["agent"])
	}

	t.Logf("✓ /health response: %v", data)
}

func TestReadyEndpoint(t *testing.T) {
	agent := &testHealthAgent{}
	httpAgent := NewHTTPAgent(agent, "localhost:8080")

	// Create a request
	req := httptest.NewRequest(http.MethodGet, "/ready", nil)
	rec := httptest.NewRecorder()

	// Call handler
	httpAgent.handleReady(rec, req)

	// Check response
	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	// Parse JSON response
	var data map[string]interface{}
	if err := json.Unmarshal(rec.Body.Bytes(), &data); err != nil {
		t.Fatalf("Failed to parse JSON response: %v", err)
	}

	// Verify response structure
	if ready, ok := data["ready"].(bool); !ok || !ready {
		t.Errorf("Expected ready=true, got %v", data["ready"])
	}

	if _, ok := data["checks"]; !ok {
		t.Error("Missing checks in ready response")
	}

	t.Logf("✓ /ready response: %v", data)
}

func TestLiveEndpoint(t *testing.T) {
	agent := &testHealthAgent{}
	httpAgent := NewHTTPAgent(agent, "localhost:8080")

	// Create a request
	req := httptest.NewRequest(http.MethodGet, "/live", nil)
	rec := httptest.NewRecorder()

	// Call handler
	httpAgent.handleLive(rec, req)

	// Check response
	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200, got %d", rec.Code)
	}

	// Parse JSON response
	var data map[string]interface{}
	if err := json.Unmarshal(rec.Body.Bytes(), &data); err != nil {
		t.Fatalf("Failed to parse JSON response: %v", err)
	}

	// Verify response structure
	if alive, ok := data["alive"].(bool); !ok || !alive {
		t.Errorf("Expected alive=true, got %v", data["alive"])
	}

	t.Logf("✓ /live response: %v", data)
}

func TestUptimeTracking(t *testing.T) {
	agent := &testHealthAgent{}
	httpAgent := NewHTTPAgent(agent, "localhost:8080")

	// Wait a bit to accumulate uptime
	time.Sleep(1 * time.Second)

	// Create a request
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()

	// Call handler
	httpAgent.handleHealth(rec, req)

	// Parse JSON response
	var data map[string]interface{}
	if err := json.Unmarshal(rec.Body.Bytes(), &data); err != nil {
		t.Fatalf("Failed to parse JSON response: %v", err)
	}

	// Check that uptime is at least 1 second
	uptime, ok := data["uptime"].(float64)
	if !ok {
		t.Fatalf("Uptime is not a number: %v", data["uptime"])
	}

	if uptime < 1 {
		t.Errorf("Expected uptime >= 1 second, got %v", uptime)
	}

	t.Logf("✓ Uptime tracking works: %v seconds", uptime)
}

func TestHealthEndpointMethods(t *testing.T) {
	agent := &testHealthAgent{}
	httpAgent := NewHTTPAgent(agent, "localhost:8080")

	// Test that POST is not allowed
	req := httptest.NewRequest(http.MethodPost, "/health", nil)
	rec := httptest.NewRecorder()
	httpAgent.handleHealth(rec, req)

	if rec.Code != http.StatusMethodNotAllowed {
		t.Errorf("Expected status 405 for POST, got %d", rec.Code)
	}

	// Test that HEAD is allowed
	req = httptest.NewRequest(http.MethodHead, "/health", nil)
	rec = httptest.NewRecorder()
	httpAgent.handleHealth(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("Expected status 200 for HEAD, got %d", rec.Code)
	}

	t.Log("✓ Method restrictions work correctly")
}
