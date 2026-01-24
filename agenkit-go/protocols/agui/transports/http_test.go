package transports

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

// MockAgent for testing
type MockAgent struct {
	name     string
	response string
	err      error
}

func NewMockAgent(name, response string) *MockAgent {
	return &MockAgent{
		name:     name,
		response: response,
	}
}

func (m *MockAgent) Name() string {
	return m.name
}

func (m *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.err != nil {
		return nil, m.err
	}
	return &agenkit.Message{
		Role:     "assistant",
		Content:  m.response,
		Metadata: make(map[string]interface{}),
	}, nil
}

func (m *MockAgent) Capabilities() []string {
	return []string{"chat"}
}

func (m *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:     m.name,
		Capabilities:  m.Capabilities(),
		InternalState: make(map[string]interface{}),
		Metadata:      make(map[string]interface{}),
	}
}

func TestSSEFormatter_FormatEvent(t *testing.T) {
	formatter := SSEFormatter{}

	tests := []struct {
		name              string
		event             agui.AGUIEvent
		includeEventName  bool
		wantContains      []string
		wantNotContains   []string
	}{
		{
			name:             "TextMessageChunk without event name",
			event:            agui.NewTextMessageChunk("msg-1", "Hello"),
			includeEventName: false,
			wantContains:     []string{"data:", "text_message_chunk", "Hello", "\n\n"},
			wantNotContains:  []string{"event:"},
		},
		{
			name:             "TextMessageChunk with event name",
			event:            agui.NewTextMessageChunk("msg-1", "Hello"),
			includeEventName: true,
			wantContains:     []string{"event:", "text_message_chunk", "data:", "Hello", "\n\n"},
		},
		{
			name:             "MetadataEvent",
			event:            agui.NewMetadataEvent(map[string]interface{}{"key": "value"}),
			includeEventName: false,
			wantContains:     []string{"data:", "metadata", "\n\n"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := formatter.FormatEvent(tt.event, tt.includeEventName)
			if err != nil {
				t.Fatalf("FormatEvent() error = %v", err)
			}

			for _, want := range tt.wantContains {
				if !strings.Contains(result, want) {
					t.Errorf("FormatEvent() result should contain %q, got: %s", want, result)
				}
			}

			for _, notWant := range tt.wantNotContains {
				if strings.Contains(result, notWant) {
					t.Errorf("FormatEvent() result should not contain %q, got: %s", notWant, result)
				}
			}

			// Verify ends with \n\n
			if !strings.HasSuffix(result, "\n\n") {
				t.Errorf("FormatEvent() result should end with \\n\\n, got: %q", result[len(result)-5:])
			}
		})
	}
}

func TestSSEFormatter_FormatComment(t *testing.T) {
	formatter := SSEFormatter{}

	result := formatter.FormatComment("test comment")

	if !strings.HasPrefix(result, ":") {
		t.Errorf("Comment should start with ':', got: %s", result)
	}

	if !strings.Contains(result, "test comment") {
		t.Errorf("Comment should contain 'test comment', got: %s", result)
	}

	if !strings.HasSuffix(result, "\n\n") {
		t.Errorf("Comment should end with \\n\\n, got: %s", result)
	}
}

func TestSSEFormatter_FormatRetry(t *testing.T) {
	formatter := SSEFormatter{}

	result := formatter.FormatRetry(5000)

	if !strings.Contains(result, "retry: 5000") {
		t.Errorf("Retry should contain 'retry: 5000', got: %s", result)
	}

	if !strings.HasSuffix(result, "\n\n") {
		t.Errorf("Retry should end with \\n\\n, got: %s", result)
	}
}

func TestAGUISSEHandler_ServeHTTP_Success(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	handler := NewAGUISSEHandler(agent, AGUISSEHandlerConfig{})

	// Create request
	reqBody := map[string]string{
		"message": "Hi",
	}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	// Create response recorder
	rr := httptest.NewRecorder()

	// Handle request
	handler.ServeHTTP(rr, req)

	// Check status code
	if rr.Code != http.StatusOK {
		t.Errorf("Status code = %d, want %d", rr.Code, http.StatusOK)
	}

	// Check content type
	contentType := rr.Header().Get("Content-Type")
	if contentType != "text/event-stream" {
		t.Errorf("Content-Type = %s, want text/event-stream", contentType)
	}

	// Check response body contains expected events
	body := rr.Body.String()

	expectedPatterns := []string{
		"data:",                     // SSE format
		"metadata",                  // MetadataEvent
		"text_message_start",        // TextMessageStart
		"text_message_chunk",        // TextMessageChunk
		"text_message_complete",     // TextMessageComplete
		"stream_complete",           // Completion comment
	}

	for _, pattern := range expectedPatterns {
		if !strings.Contains(body, pattern) {
			t.Errorf("Response should contain %q, got: %s", pattern, body[:min(len(body), 500)])
		}
	}

	// Verify it contains actual message content
	if !strings.Contains(body, "Hello world") {
		t.Errorf("Response should contain 'Hello world', got: %s", body)
	}
}

func TestAGUISSEHandler_ServeHTTP_MethodNotAllowed(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	handler := NewAGUISSEHandler(agent, AGUISSEHandlerConfig{})

	req := httptest.NewRequest(http.MethodGet, "/chat", nil)
	rr := httptest.NewRecorder()

	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusMethodNotAllowed {
		t.Errorf("Status code = %d, want %d", rr.Code, http.StatusMethodNotAllowed)
	}
}

func TestAGUISSEHandler_ServeHTTP_InvalidJSON(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	handler := NewAGUISSEHandler(agent, AGUISSEHandlerConfig{})

	req := httptest.NewRequest(http.MethodPost, "/chat", strings.NewReader("invalid json"))
	req.Header.Set("Content-Type", "application/json")
	rr := httptest.NewRecorder()

	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("Status code = %d, want %d", rr.Code, http.StatusBadRequest)
	}
}

func TestAGUISSEHandler_WithEventNames(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	config := AGUISSEHandlerConfig{
		IncludeEventNames: true,
	}
	handler := NewAGUISSEHandler(agent, config)

	reqBody := map[string]string{"message": "Hi"}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	body := rr.Body.String()

	// Should contain "event:" lines
	if !strings.Contains(body, "event:") {
		t.Error("Response should contain 'event:' lines when IncludeEventNames is true")
	}
}

func TestAGUISSEHandler_WithCORS(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	config := AGUISSEHandlerConfig{
		CORSOrigins: []string{"http://localhost:3000"},
	}
	handler := NewAGUISSEHandler(agent, config)

	reqBody := map[string]string{"message": "Hi"}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Origin", "http://localhost:3000")

	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	// Check CORS headers
	allowOrigin := rr.Header().Get("Access-Control-Allow-Origin")
	if allowOrigin != "http://localhost:3000" {
		t.Errorf("Access-Control-Allow-Origin = %s, want http://localhost:3000", allowOrigin)
	}
}

func TestAGUISSEHandler_WithTimeout(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	config := AGUISSEHandlerConfig{
		Timeout: 1 * time.Millisecond, // Very short timeout
	}
	handler := NewAGUISSEHandler(agent, config)

	reqBody := map[string]string{"message": "Hi"}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	// Should still complete (timeout happens during streaming)
	// Response should be present
	if rr.Code != http.StatusOK {
		t.Errorf("Status code = %d, want %d", rr.Code, http.StatusOK)
	}
}

func TestStreamSSEEvents(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	adapter := agui.NewAGUIAdapter(agent)
	message := agenkit.NewMessage("user", "Hi")

	var buf bytes.Buffer
	ctx := context.Background()

	err := StreamSSEEvents(ctx, &buf, adapter, message, false)
	if err != nil {
		t.Fatalf("StreamSSEEvents() error = %v", err)
	}

	result := buf.String()

	// Check for expected content
	if !strings.Contains(result, "data:") {
		t.Error("Result should contain 'data:'")
	}

	if !strings.Contains(result, "Hello world") {
		t.Error("Result should contain 'Hello world'")
	}

	if !strings.Contains(result, "stream_complete") {
		t.Error("Result should contain 'stream_complete'")
	}
}

func TestCreateSSEHandler(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	handler := CreateSSEHandler(agent)

	if handler == nil {
		t.Fatal("CreateSSEHandler() returned nil")
	}

	// Test that it's a valid http.Handler
	reqBody := map[string]string{"message": "Hi"}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("Status code = %d, want %d", rr.Code, http.StatusOK)
	}
}

func TestCreateSSEHandlerFunc(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	handlerFunc := CreateSSEHandlerFunc(agent)

	if handlerFunc == nil {
		t.Fatal("CreateSSEHandlerFunc() returned nil")
	}

	// Test that it's a valid http.HandlerFunc
	reqBody := map[string]string{"message": "Hi"}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	handlerFunc(rr, req)

	if rr.Code != http.StatusOK {
		t.Errorf("Status code = %d, want %d", rr.Code, http.StatusOK)
	}
}

func TestAGUISSEHandler_ResponseHeaders(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	handler := NewAGUISSEHandler(agent, AGUISSEHandlerConfig{})

	reqBody := map[string]string{"message": "Hi"}
	bodyBytes, _ := json.Marshal(reqBody)
	req := httptest.NewRequest(http.MethodPost, "/chat", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")

	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	// Check required SSE headers
	headers := map[string]string{
		"Content-Type":      "text/event-stream",
		"Cache-Control":     "no-cache",
		"Connection":        "keep-alive",
		"X-Accel-Buffering": "no",
	}

	for key, expected := range headers {
		got := rr.Header().Get(key)
		if got != expected {
			t.Errorf("Header %s = %s, want %s", key, got, expected)
		}
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
