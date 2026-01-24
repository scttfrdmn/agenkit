package transports

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/protocols/agui"
)

func TestWebSocketMessageFormat_FormatEvent(t *testing.T) {
	formatter := WebSocketMessageFormat{}

	event := agui.NewTextMessageChunk("msg-1", "Hello")
	result, err := formatter.FormatEvent(event)
	if err != nil {
		t.Fatalf("FormatEvent() error = %v", err)
	}

	// Verify it's valid JSON
	var parsed map[string]interface{}
	if err := json.Unmarshal(result, &parsed); err != nil {
		t.Fatalf("Result is not valid JSON: %v", err)
	}

	// Check for expected fields
	if eventType, ok := parsed["event_type"].(string); !ok || eventType != "text_message_chunk" {
		t.Errorf("event_type = %v, want text_message_chunk", parsed["event_type"])
	}

	if content, ok := parsed["content"].(string); !ok || content != "Hello" {
		t.Errorf("content = %v, want Hello", parsed["content"])
	}
}

func TestWebSocketMessageFormat_ParseMessage(t *testing.T) {
	formatter := WebSocketMessageFormat{}

	tests := []struct {
		name      string
		message   string
		wantErr   bool
		wantField string
		wantValue string
	}{
		{
			name:      "Valid message",
			message:   `{"type":"message","content":"Hello"}`,
			wantErr:   false,
			wantField: "type",
			wantValue: "message",
		},
		{
			name:    "Invalid JSON",
			message: `{invalid json}`,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := formatter.ParseMessage([]byte(tt.message))

			if tt.wantErr {
				if err == nil {
					t.Error("ParseMessage() expected error, got nil")
				}
				return
			}

			if err != nil {
				t.Fatalf("ParseMessage() error = %v", err)
			}

			if tt.wantField != "" {
				if val, ok := result[tt.wantField].(string); !ok || val != tt.wantValue {
					t.Errorf("result[%s] = %v, want %s", tt.wantField, result[tt.wantField], tt.wantValue)
				}
			}
		})
	}
}

func TestNewAGUIWebSocketHandler(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	upgrader := websocket.Upgrader{}
	config := AGUIWebSocketHandlerConfig{
		AgentName: "CustomAgent",
	}

	handler := NewAGUIWebSocketHandler(agent, upgrader, config)

	if handler == nil {
		t.Fatal("NewAGUIWebSocketHandler() returned nil")
	}

	if handler.adapter == nil {
		t.Error("Handler adapter is nil")
	}
}

func TestAGUIWebSocketHandler_ServeHTTP(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
	config := AGUIWebSocketHandlerConfig{
		HeartbeatInterval: 100 * time.Millisecond,
		ReadTimeout:       5 * time.Second,
		WriteTimeout:      5 * time.Second,
	}

	handler := NewAGUIWebSocketHandler(agent, upgrader, config)

	// Create test server
	server := httptest.NewServer(handler)
	defer server.Close()

	// Convert http:// to ws://
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")

	// Connect as client
	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer func() { _ = client.Close() }()

	// Send message
	clientMsg := map[string]string{
		"type":    "message",
		"content": "Hi there",
	}
	msgJSON, _ := json.Marshal(clientMsg)

	if err := client.WriteMessage(websocket.TextMessage, msgJSON); err != nil {
		t.Fatalf("Failed to send message: %v", err)
	}

	// Read responses
	receivedEvents := []string{}
	timeout := time.After(2 * time.Second)
	completionReceived := false

	for !completionReceived {
		select {
		case <-timeout:
			t.Fatal("Timeout waiting for responses")
		default:
			// Set read deadline
			if err := client.SetReadDeadline(time.Now().Add(500 * time.Millisecond)); err != nil {
				t.Fatalf("Failed to set read deadline: %v", err)
			}

			_, message, err := client.ReadMessage()
			if err != nil {
				// Check if it's a timeout (expected when stream completes)
				if netErr, ok := err.(interface{ Timeout() bool }); ok && netErr.Timeout() {
					break
				}
				t.Fatalf("Failed to read message: %v", err)
			}

			// Parse response
			var response map[string]interface{}
			if err := json.Unmarshal(message, &response); err != nil {
				t.Fatalf("Failed to parse response: %v", err)
			}

			// Check for completion
			if msgType, ok := response["type"].(string); ok && msgType == "stream_complete" {
				completionReceived = true
				break
			}

			// Record event type
			if eventType, ok := response["event_type"].(string); ok {
				receivedEvents = append(receivedEvents, eventType)
			}
		}
	}

	// Verify we received expected events
	expectedEvents := []string{
		"metadata",
		"text_message_start",
		// May have one or more chunks
		// "text_message_chunk",
		// Will have complete
		// "text_message_complete",
	}

	for _, expected := range expectedEvents {
		found := false
		for _, received := range receivedEvents {
			if received == expected {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected event %s not received. Got: %v", expected, receivedEvents)
		}
	}

	if len(receivedEvents) == 0 {
		t.Error("No events received")
	}
}

func TestAGUIWebSocketHandler_PingPong(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}

	handler := NewAGUIWebSocketHandler(agent, upgrader, AGUIWebSocketHandlerConfig{
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	})

	// Create test server
	server := httptest.NewServer(handler)
	defer server.Close()

	// Connect as client
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")
	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer func() { _ = client.Close() }()

	// Send ping
	ping := map[string]string{"type": "ping"}
	pingJSON, _ := json.Marshal(ping)

	if err := client.WriteMessage(websocket.TextMessage, pingJSON); err != nil {
		t.Fatalf("Failed to send ping: %v", err)
	}

	// Read pong
	if err := client.SetReadDeadline(time.Now().Add(1 * time.Second)); err != nil {
		t.Fatalf("Failed to set read deadline: %v", err)
	}

	_, message, err := client.ReadMessage()
	if err != nil {
		t.Fatalf("Failed to read pong: %v", err)
	}

	// Parse pong
	var response map[string]interface{}
	if err := json.Unmarshal(message, &response); err != nil {
		t.Fatalf("Failed to parse pong: %v", err)
	}

	if msgType, ok := response["type"].(string); !ok || msgType != "pong" {
		t.Errorf("Expected pong, got: %v", response)
	}
}

func TestAGUIWebSocketHandler_InvalidMessage(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}

	handler := NewAGUIWebSocketHandler(agent, upgrader, AGUIWebSocketHandlerConfig{
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	})

	// Create test server
	server := httptest.NewServer(handler)
	defer server.Close()

	// Connect as client
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")
	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer func() { _ = client.Close() }()

	// Send invalid JSON
	if err := client.WriteMessage(websocket.TextMessage, []byte("invalid json")); err != nil {
		t.Fatalf("Failed to send message: %v", err)
	}

	// Read error response
	if err := client.SetReadDeadline(time.Now().Add(1 * time.Second)); err != nil {
		t.Fatalf("Failed to set read deadline: %v", err)
	}

	_, message, err := client.ReadMessage()
	if err != nil {
		t.Fatalf("Failed to read error: %v", err)
	}

	// Parse error
	var response map[string]interface{}
	if err := json.Unmarshal(message, &response); err != nil {
		t.Fatalf("Failed to parse error: %v", err)
	}

	// Should be an error event
	if eventType, ok := response["event_type"].(string); !ok || eventType != "error" {
		t.Errorf("Expected error event, got: %v", response)
	}
}

func TestCreateWebSocketHandler(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}

	handler := CreateWebSocketHandler(agent, upgrader)

	if handler == nil {
		t.Fatal("CreateWebSocketHandler() returned nil")
	}
}

func TestCreateWebSocketHandlerFunc(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}

	handlerFunc := CreateWebSocketHandlerFunc(agent, upgrader)

	if handlerFunc == nil {
		t.Fatal("CreateWebSocketHandlerFunc() returned nil")
	}
}

func TestStreamWebSocketEvents(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello world")
	adapter := agui.NewAGUIAdapter(agent)
	message := agenkit.NewMessage("user", "Hi")

	// Create a mock WebSocket connection using httptest
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		upgrader := websocket.Upgrader{}
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			t.Fatalf("Upgrade failed: %v", err)
			return
		}
		defer func() { _ = conn.Close() }()

		ctx := context.Background()
		if err := StreamWebSocketEvents(ctx, conn, adapter, message); err != nil {
			t.Errorf("StreamWebSocketEvents() error = %v", err)
		}
	}))
	defer server.Close()

	// Connect as client
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")
	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer func() { _ = client.Close() }()

	// Read events
	eventCount := 0
	timeout := time.After(2 * time.Second)

	for eventCount < 10 { // Limit iterations
		select {
		case <-timeout:
			// Timeout is OK, we got some events
			if eventCount == 0 {
				t.Error("No events received")
			}
			return
		default:
			if err := client.SetReadDeadline(time.Now().Add(100 * time.Millisecond)); err != nil {
				return
			}

			_, _, err := client.ReadMessage()
			if err != nil {
				// Timeout or connection closed - we're done
				if eventCount > 0 {
					return // Success
				}
				t.Errorf("Failed to read any messages: %v", err)
				return
			}
			eventCount++
		}
	}

	if eventCount == 0 {
		t.Error("No events received")
	}
}

func TestAGUIWebSocketHandler_Heartbeats(t *testing.T) {
	agent := NewMockAgent("TestAgent", "Hello")
	upgrader := websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}

	// Short heartbeat interval for testing
	handler := NewAGUIWebSocketHandler(agent, upgrader, AGUIWebSocketHandlerConfig{
		HeartbeatInterval: 100 * time.Millisecond,
		ReadTimeout:       5 * time.Second,
	})

	// Create test server
	server := httptest.NewServer(handler)
	defer server.Close()

	// Connect as client
	wsURL := "ws" + strings.TrimPrefix(server.URL, "http")
	client, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("Failed to connect: %v", err)
	}
	defer func() { _ = client.Close() }()

	// Wait for heartbeats
	heartbeatReceived := false
	timeout := time.After(500 * time.Millisecond)

	for !heartbeatReceived {
		select {
		case <-timeout:
			t.Error("No heartbeat received within timeout")
			return
		default:
			if err := client.SetReadDeadline(time.Now().Add(200 * time.Millisecond)); err != nil {
				continue
			}

			_, message, err := client.ReadMessage()
			if err != nil {
				continue
			}

			// Parse message
			var response map[string]interface{}
			if err := json.Unmarshal(message, &response); err != nil {
				continue
			}

			// Check if it's a heartbeat
			if eventType, ok := response["event_type"].(string); ok && eventType == "heartbeat" {
				heartbeatReceived = true
			}
		}
	}

	if !heartbeatReceived {
		t.Error("Did not receive heartbeat event")
	}
}
