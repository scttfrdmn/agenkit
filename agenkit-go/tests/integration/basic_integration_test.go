package integration

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

// SimpleEchoAgent is a simple echo agent for testing.
type SimpleEchoAgent struct{}

func (a *SimpleEchoAgent) Name() string {
	return "simple-echo"
}

func (a *SimpleEchoAgent) Capabilities() []string {
	return []string{"echo"}
}

func (a *SimpleEchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{
		Role:    "agent",
		Content: "Echo: " + message.Content,
		Metadata: map[string]interface{}{
			"original": message.Content,
			"language": "go",
			"agent":    a.Name(),
		},
	}, nil
}

func TestMessageCreation(t *testing.T) {
	msg := agenkit.NewMessage("user", "Hello")
	msg.Metadata["test"] = true

	if msg.Role != "user" {
		t.Errorf("Expected role='user', got '%s'", msg.Role)
	}
	if msg.Content != "Hello" {
		t.Errorf("Expected content='Hello', got '%s'", msg.Content)
	}
	if msg.Metadata["test"] != true {
		t.Errorf("Expected metadata['test']=true, got '%v'", msg.Metadata["test"])
	}
	if msg.Timestamp.IsZero() {
		t.Error("Expected timestamp to be set")
	}
}

func TestMessageSerialization(t *testing.T) {
	original := &agenkit.Message{
		Role:      "user",
		Content:   "Test message",
		Timestamp: time.Now(),
		Metadata: map[string]interface{}{
			"string": "value",
			"number": 42,
			"float":  3.14,
			"bool":   true,
			"nested": map[string]interface{}{"key": "value"},
			"list":   []interface{}{1, 2, 3},
		},
	}

	// Serialize to JSON (simulating transport)
	jsonBytes, err := json.Marshal(original)
	if err != nil {
		t.Fatalf("JSON marshal failed: %v", err)
	}

	// Deserialize
	var deserialized agenkit.Message
	if err := json.Unmarshal(jsonBytes, &deserialized); err != nil {
		t.Fatalf("JSON unmarshal failed: %v", err)
	}

	// Validate
	if deserialized.Role != "user" {
		t.Errorf("Expected role='user', got '%s'", deserialized.Role)
	}
	if deserialized.Content != "Test message" {
		t.Errorf("Expected content='Test message', got '%s'", deserialized.Content)
	}
	if deserialized.Metadata["string"] != "value" {
		t.Errorf("Expected metadata['string']='value', got '%v'", deserialized.Metadata["string"])
	}
	if deserialized.Metadata["number"].(float64) != 42 {
		t.Errorf("Expected metadata['number']=42, got '%v'", deserialized.Metadata["number"])
	}
}

func TestAgentBasicProcessing(t *testing.T) {
	agent := &SimpleEchoAgent{}

	if agent.Name() != "simple-echo" {
		t.Errorf("Expected name='simple-echo', got '%s'", agent.Name())
	}

	caps := agent.Capabilities()
	if len(caps) != 1 || caps[0] != "echo" {
		t.Errorf("Expected capabilities=['echo'], got %v", caps)
	}

	msg := agenkit.NewMessage("user", "Hello")
	ctx := context.Background()
	response, err := agent.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if response.Role != "agent" {
		t.Errorf("Expected role='agent', got '%s'", response.Role)
	}
	if response.Content != "Echo: Hello" {
		t.Errorf("Expected content='Echo: Hello', got '%s'", response.Content)
	}
	if response.Metadata["original"] != "Hello" {
		t.Errorf("Expected metadata['original']='Hello', got '%v'", response.Metadata["original"])
	}
	if response.Metadata["language"] != "go" {
		t.Errorf("Expected metadata['language']='go', got '%v'", response.Metadata["language"])
	}
}

func TestAgentMetadataPreservation(t *testing.T) {
	agent := &SimpleEchoAgent{}

	msg := agenkit.NewMessage("user", "Test")
	msg.Metadata["request_id"] = "123"

	ctx := context.Background()
	response, err := agent.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Agent adds its own metadata
	if response.Metadata["original"] != "Test" {
		t.Errorf("Expected metadata['original']='Test', got '%v'", response.Metadata["original"])
	}
	if response.Metadata["language"] != "go" {
		t.Errorf("Expected metadata['language']='go', got '%v'", response.Metadata["language"])
	}
	if response.Metadata["agent"] != "simple-echo" {
		t.Errorf("Expected metadata['agent']='simple-echo', got '%v'", response.Metadata["agent"])
	}
}

func TestMultipleSequentialRequests(t *testing.T) {
	agent := &SimpleEchoAgent{}
	ctx := context.Background()

	for i := 0; i < 5; i++ {
		msg := agenkit.NewMessage("user", "Message "+string(rune('0'+i)))
		response, err := agent.Process(ctx, msg)

		if err != nil {
			t.Fatalf("Process %d failed: %v", i, err)
		}
		if response.Content != "Echo: Message "+string(rune('0'+i)) {
			t.Errorf("Request %d: expected 'Echo: Message %c', got '%s'", i, '0'+i, response.Content)
		}
	}
}

func TestAgentWithComplexMetadata(t *testing.T) {
	agent := &SimpleEchoAgent{}

	complexMetadata := map[string]interface{}{
		"trace_id": "abc-123",
		"user": map[string]interface{}{
			"id":   42,
			"name": "Test User",
			"preferences": map[string]interface{}{
				"language": "en",
				"timezone": "UTC",
			},
		},
		"tags":   []interface{}{"test", "integration", "metadata"},
		"counts": []interface{}{1, 2, 3, 4, 5},
	}

	msg := agenkit.NewMessage("user", "Complex test")
	msg.Metadata = complexMetadata

	ctx := context.Background()
	response, err := agent.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	// Response should have agent metadata
	if response.Metadata["original"] != "Complex test" {
		t.Errorf("Expected metadata['original']='Complex test', got '%v'", response.Metadata["original"])
	}
	if response.Metadata["language"] != "go" {
		t.Errorf("Expected metadata['language']='go', got '%v'", response.Metadata["language"])
	}
}

func TestAgentConsistency(t *testing.T) {
	agent := &SimpleEchoAgent{}
	msg := agenkit.NewMessage("user", "Consistency test")
	ctx := context.Background()

	// Process same message multiple times
	results := make([]string, 3)
	for i := 0; i < 3; i++ {
		response, err := agent.Process(ctx, msg)
		if err != nil {
			t.Fatalf("Process %d failed: %v", i, err)
		}
		results[i] = response.Content
	}

	// All results should be identical
	for i := 1; i < len(results); i++ {
		if results[i] != results[0] {
			t.Errorf("Inconsistent results: results[0]='%s', results[%d]='%s'", results[0], i, results[i])
		}
	}
	if results[0] != "Echo: Consistency test" {
		t.Errorf("Expected 'Echo: Consistency test', got '%s'", results[0])
	}
}

func TestEmptyContentHandling(t *testing.T) {
	agent := &SimpleEchoAgent{}
	msg := agenkit.NewMessage("user", "")
	ctx := context.Background()

	response, err := agent.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}
	if response.Role != "agent" {
		t.Errorf("Expected role='agent', got '%s'", response.Role)
	}
	if response.Content != "Echo: " {
		t.Errorf("Expected content='Echo: ', got '%s'", response.Content)
	}
	if response.Metadata["original"] != "" {
		t.Errorf("Expected metadata['original']='', got '%v'", response.Metadata["original"])
	}
}

func TestUnicodeContentHandling(t *testing.T) {
	agent := &SimpleEchoAgent{}
	unicodeContent := "Hello 世界 🌍 Привет"
	msg := agenkit.NewMessage("user", unicodeContent)
	ctx := context.Background()

	response, err := agent.Process(ctx, msg)

	if err != nil {
		t.Fatalf("Process failed: %v", err)
	}

	expected := "Echo: " + unicodeContent
	if response.Content != expected {
		t.Errorf("Expected content='%s', got '%s'", expected, response.Content)
	}
	if response.Metadata["original"] != unicodeContent {
		t.Errorf("Expected metadata['original']='%s', got '%v'", unicodeContent, response.Metadata["original"])
	}
}
