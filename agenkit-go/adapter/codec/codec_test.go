package codec

import (
	"testing"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
)

func TestEncodeDecodeMessage(t *testing.T) {
	// Create a message
	msg := agenkit.NewMessage("user", "test content").
		WithMetadata("key1", "value1").
		WithMetadata("key2", 123)

	// Encode
	encoded := EncodeMessage(msg)

	// Verify encoded fields
	if encoded.Role != "user" {
		t.Errorf("Expected role 'user', got '%s'", encoded.Role)
	}
	if encoded.Content != "test content" {
		t.Errorf("Expected content 'test content', got '%s'", encoded.Content)
	}
	if encoded.Metadata["key1"] != "value1" {
		t.Errorf("Expected metadata key1='value1', got '%v'", encoded.Metadata["key1"])
	}

	// Decode
	decoded, err := DecodeMessage(encoded)
	if err != nil {
		t.Fatalf("Failed to decode message: %v", err)
	}

	// Verify decoded fields
	if decoded.Role != msg.Role {
		t.Errorf("Expected role '%s', got '%s'", msg.Role, decoded.Role)
	}
	if decoded.Content != msg.Content {
		t.Errorf("Expected content '%s', got '%s'", msg.Content, decoded.Content)
	}
	if decoded.Metadata["key1"] != msg.Metadata["key1"] {
		t.Errorf("Metadata mismatch")
	}
}

func TestEncodeDecodeToolResult(t *testing.T) {
	// Test successful result
	result := agenkit.NewToolResult("test data").
		WithMetadata("executed_at", time.Now().Unix())

	encoded := EncodeToolResult(result)
	decoded := DecodeToolResult(encoded)

	if decoded.Success != true {
		t.Error("Expected success=true")
	}
	if decoded.Data != "test data" {
		t.Errorf("Expected data 'test data', got '%v'", decoded.Data)
	}

	// Test error result
	errorResult := agenkit.NewToolError("test error")
	encodedError := EncodeToolResult(errorResult)
	decodedError := DecodeToolResult(encodedError)

	if decodedError.Success != false {
		t.Error("Expected success=false")
	}
	if decodedError.Error != "test error" {
		t.Errorf("Expected error 'test error', got '%s'", decodedError.Error)
	}
}

func TestCreateRequestEnvelope(t *testing.T) {
	payload := map[string]interface{}{
		"test_key": "test_value",
	}

	env := CreateRequestEnvelope("process", "test_agent", payload)

	if env.Version != ProtocolVersion {
		t.Errorf("Expected version '%s', got '%s'", ProtocolVersion, env.Version)
	}
	if env.Type != TypeRequest {
		t.Errorf("Expected type '%s', got '%s'", TypeRequest, env.Type)
	}
	if env.ID == "" {
		t.Error("Expected non-empty ID")
	}
	if env.Payload["method"] != "process" {
		t.Errorf("Expected method 'process', got '%v'", env.Payload["method"])
	}
	if env.Payload["agent_name"] != "test_agent" {
		t.Errorf("Expected agent_name 'test_agent', got '%v'", env.Payload["agent_name"])
	}
	if env.Payload["test_key"] != "test_value" {
		t.Errorf("Expected test_key 'test_value', got '%v'", env.Payload["test_key"])
	}
}

func TestCreateResponseEnvelope(t *testing.T) {
	requestID := "test-request-id"
	payload := map[string]interface{}{
		"result": "success",
	}

	env := CreateResponseEnvelope(requestID, payload)

	if env.Type != TypeResponse {
		t.Errorf("Expected type '%s', got '%s'", TypeResponse, env.Type)
	}
	if env.ID != requestID {
		t.Errorf("Expected ID '%s', got '%s'", requestID, env.ID)
	}
	if env.Payload["result"] != "success" {
		t.Errorf("Expected result 'success', got '%v'", env.Payload["result"])
	}
}

func TestCreateErrorEnvelope(t *testing.T) {
	requestID := "test-request-id"
	errorCode := "TEST_ERROR"
	errorMessage := "Test error message"
	errorDetails := map[string]interface{}{
		"detail1": "value1",
	}

	env := CreateErrorEnvelope(requestID, errorCode, errorMessage, errorDetails)

	if env.Type != TypeError {
		t.Errorf("Expected type '%s', got '%s'", TypeError, env.Type)
	}
	if env.ID != requestID {
		t.Errorf("Expected ID '%s', got '%s'", requestID, env.ID)
	}
	if env.Payload["error_code"] != errorCode {
		t.Errorf("Expected error_code '%s', got '%v'", errorCode, env.Payload["error_code"])
	}
	if env.Payload["error_message"] != errorMessage {
		t.Errorf("Expected error_message '%s', got '%v'", errorMessage, env.Payload["error_message"])
	}
}

func TestCreateStreamEnvelopes(t *testing.T) {
	requestID := "test-stream-id"
	msg := agenkit.NewMessage("agent", "chunk content")
	msgData := EncodeMessage(msg)

	// Test stream chunk
	chunkEnv := CreateStreamChunkEnvelope(requestID, msgData)
	if chunkEnv.Type != TypeStreamChunk {
		t.Errorf("Expected type '%s', got '%s'", TypeStreamChunk, chunkEnv.Type)
	}
	if chunkEnv.ID != requestID {
		t.Errorf("Expected ID '%s', got '%s'", requestID, chunkEnv.ID)
	}

	// Test stream end
	endEnv := CreateStreamEndEnvelope(requestID)
	if endEnv.Type != TypeStreamEnd {
		t.Errorf("Expected type '%s', got '%s'", TypeStreamEnd, endEnv.Type)
	}
	if endEnv.ID != requestID {
		t.Errorf("Expected ID '%s', got '%s'", requestID, endEnv.ID)
	}
}

func TestValidateEnvelope(t *testing.T) {
	// Valid envelope
	validEnv := &Envelope{
		Version: ProtocolVersion,
		Type:    TypeRequest,
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}

	if err := ValidateEnvelope(validEnv); err != nil {
		t.Errorf("Valid envelope failed validation: %v", err)
	}

	// Missing version
	invalidEnv := &Envelope{
		Type:    TypeRequest,
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}
	if err := ValidateEnvelope(invalidEnv); err == nil {
		t.Error("Expected error for missing version")
	}

	// Wrong version
	wrongVersion := &Envelope{
		Version: "2.0",
		Type:    TypeRequest,
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}
	if err := ValidateEnvelope(wrongVersion); err == nil {
		t.Error("Expected error for wrong version")
	}

	// Invalid type
	invalidType := &Envelope{
		Version: ProtocolVersion,
		Type:    "invalid_type",
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}
	if err := ValidateEnvelope(invalidType); err == nil {
		t.Error("Expected error for invalid type")
	}

	// Missing ID
	missingID := &Envelope{
		Version: ProtocolVersion,
		Type:    TypeRequest,
		Payload: map[string]interface{}{},
	}
	if err := ValidateEnvelope(missingID); err == nil {
		t.Error("Expected error for missing ID")
	}

	// Missing payload
	missingPayload := &Envelope{
		Version: ProtocolVersion,
		Type:    TypeRequest,
		ID:      "test-id",
	}
	if err := ValidateEnvelope(missingPayload); err == nil {
		t.Error("Expected error for missing payload")
	}
}

func TestEncodeBytesDecodeBytes(t *testing.T) {
	// Create envelope
	env := CreateRequestEnvelope("process", "test_agent", map[string]interface{}{
		"data": "test data",
	})

	// Encode to bytes
	bytes, err := EncodeBytes(env)
	if err != nil {
		t.Fatalf("Failed to encode bytes: %v", err)
	}

	// Decode from bytes
	decoded, err := DecodeBytes(bytes)
	if err != nil {
		t.Fatalf("Failed to decode bytes: %v", err)
	}

	// Verify
	if decoded.Type != env.Type {
		t.Errorf("Type mismatch: expected '%s', got '%s'", env.Type, decoded.Type)
	}
	if decoded.ID != env.ID {
		t.Errorf("ID mismatch: expected '%s', got '%s'", env.ID, decoded.ID)
	}
	if decoded.Payload["method"] != "process" {
		t.Errorf("Method mismatch: expected 'process', got '%v'", decoded.Payload["method"])
	}
}

func TestDecodeBytesInvalidJSON(t *testing.T) {
	invalidJSON := []byte("{invalid json")

	_, err := DecodeBytes(invalidJSON)
	if err == nil {
		t.Error("Expected error for invalid JSON")
	}
}
