package codec

import (
	"encoding/json"
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

// Additional tests to match Python's 25 codec tests

func TestEncodeMessage(t *testing.T) {
	msg := agenkit.NewMessage("user", "test").
		WithMetadata("key", "value")

	encoded := EncodeMessage(msg)

	if encoded.Role != "user" {
		t.Errorf("Expected role 'user', got '%s'", encoded.Role)
	}
	if encoded.Content != "test" {
		t.Errorf("Expected content 'test', got '%s'", encoded.Content)
	}
	if encoded.Metadata["key"] != "value" {
		t.Error("Metadata not encoded correctly")
	}
	if encoded.Timestamp == "" {
		t.Error("Timestamp not encoded")
	}
}

func TestDecodeMessage(t *testing.T) {
	data := MessageData{
		Role:      "agent",
		Content:   "response",
		Metadata:  map[string]interface{}{"key": "value"},
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
	}

	msg, err := DecodeMessage(data)
	if err != nil {
		t.Fatalf("Failed to decode: %v", err)
	}

	if msg.Role != "agent" {
		t.Errorf("Expected role 'agent', got '%s'", msg.Role)
	}
	if msg.Content != "response" {
		t.Errorf("Expected content 'response', got '%s'", msg.Content)
	}
}

func TestDecodeMessageMissingTimestamp(t *testing.T) {
	data := MessageData{
		Role:     "user",
		Content:  "test",
		Metadata: map[string]interface{}{},
		// No timestamp
	}

	msg, err := DecodeMessage(data)
	if err != nil {
		t.Fatalf("Should handle missing timestamp: %v", err)
	}

	// Should use current time
	if msg.Timestamp.IsZero() {
		t.Error("Expected non-zero timestamp")
	}
}

func TestDecodeMessageMalformed(t *testing.T) {
	data := MessageData{
		Role: "user",
		// Missing required content field
		Metadata:  map[string]interface{}{},
		Timestamp: time.Now().Format(time.RFC3339Nano),
	}

	msg, err := DecodeMessage(data)
	// Should succeed but have empty content
	if err != nil {
		t.Fatalf("Unexpected error: %v", err)
	}
	if msg.Content != "" {
		t.Errorf("Expected empty content, got '%s'", msg.Content)
	}
}

func TestRoundtripMessage(t *testing.T) {
	original := agenkit.NewMessage("user", "roundtrip test").
		WithMetadata("key1", "value1").
		WithMetadata("key2", 42)

	// Encode
	encoded := EncodeMessage(original)

	// Decode
	decoded, err := DecodeMessage(encoded)
	if err != nil {
		t.Fatalf("Roundtrip failed: %v", err)
	}

	// Verify
	if decoded.Role != original.Role {
		t.Errorf("Role mismatch: %s != %s", decoded.Role, original.Role)
	}
	if decoded.Content != original.Content {
		t.Errorf("Content mismatch: %s != %s", decoded.Content, original.Content)
	}
	if decoded.Metadata["key1"] != original.Metadata["key1"] {
		t.Error("Metadata key1 mismatch")
	}
}

func TestEncodeToolResultSuccess(t *testing.T) {
	result := agenkit.NewToolResult("success data").
		WithMetadata("time", 123)

	encoded := EncodeToolResult(result)

	if !encoded.Success {
		t.Error("Expected success=true")
	}
	if encoded.Data != "success data" {
		t.Errorf("Expected data 'success data', got '%v'", encoded.Data)
	}
	if encoded.Error != "" {
		t.Error("Expected empty error")
	}
}

func TestEncodeToolResultFailure(t *testing.T) {
	result := agenkit.NewToolError("failure message")

	encoded := EncodeToolResult(result)

	if encoded.Success {
		t.Error("Expected success=false")
	}
	if encoded.Error != "failure message" {
		t.Errorf("Expected error 'failure message', got '%s'", encoded.Error)
	}
	if encoded.Data != nil {
		t.Error("Expected nil data")
	}
}

func TestDecodeToolResultSuccess(t *testing.T) {
	data := ToolResultData{
		Success:  true,
		Data:     "result data",
		Metadata: map[string]interface{}{},
	}

	result := DecodeToolResult(data)

	if !result.Success {
		t.Error("Expected success=true")
	}
	if result.Data != "result data" {
		t.Errorf("Expected data 'result data', got '%v'", result.Data)
	}
}

func TestDecodeToolResultFailure(t *testing.T) {
	data := ToolResultData{
		Success:  false,
		Error:    "error message",
		Metadata: map[string]interface{}{},
	}

	result := DecodeToolResult(data)

	if result.Success {
		t.Error("Expected success=false")
	}
	if result.Error != "error message" {
		t.Errorf("Expected error 'error message', got '%s'", result.Error)
	}
}

func TestDecodeToolResultMalformed(t *testing.T) {
	// Missing required Success field is handled by Go's zero value (false)
	data := ToolResultData{
		Data:     "some data",
		Metadata: map[string]interface{}{},
	}

	result := DecodeToolResult(data)

	// Should succeed with success=false (zero value)
	if result.Success {
		t.Error("Expected success=false for malformed data")
	}
}

func TestRoundtripToolResult(t *testing.T) {
	original := agenkit.NewToolResult(map[string]interface{}{
		"count": 42,
		"items": []string{"a", "b", "c"},
	}).WithMetadata("timestamp", time.Now().Unix())

	// Encode
	encoded := EncodeToolResult(original)

	// Decode
	decoded := DecodeToolResult(encoded)

	// Verify
	if decoded.Success != original.Success {
		t.Error("Success mismatch")
	}
	// Data comparison would need deep comparison, just check it exists
	if decoded.Data == nil {
		t.Error("Data was lost in roundtrip")
	}
}

func TestValidateValidEnvelope(t *testing.T) {
	env := &Envelope{
		Version: ProtocolVersion,
		Type:    TypeRequest,
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}

	if err := ValidateEnvelope(env); err != nil {
		t.Errorf("Valid envelope should pass: %v", err)
	}
}

func TestValidateMissingVersion(t *testing.T) {
	env := &Envelope{
		Type:    TypeRequest,
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}

	if err := ValidateEnvelope(env); err == nil {
		t.Error("Should error on missing version")
	}
}

func TestValidateUnsupportedVersion(t *testing.T) {
	env := &Envelope{
		Version: "99.0",
		Type:    TypeRequest,
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}

	if err := ValidateEnvelope(env); err == nil {
		t.Error("Should error on unsupported version")
	}
}

func TestValidateInvalidType(t *testing.T) {
	env := &Envelope{
		Version: ProtocolVersion,
		Type:    "unknown_type",
		ID:      "test-id",
		Payload: map[string]interface{}{},
	}

	if err := ValidateEnvelope(env); err == nil {
		t.Error("Should error on invalid type")
	}
}

func TestValidateMissingID(t *testing.T) {
	env := &Envelope{
		Version: ProtocolVersion,
		Type:    TypeRequest,
		Payload: map[string]interface{}{},
	}

	if err := ValidateEnvelope(env); err == nil {
		t.Error("Should error on missing ID")
	}
}

func TestValidateMissingPayload(t *testing.T) {
	env := &Envelope{
		Version: ProtocolVersion,
		Type:    TypeRequest,
		ID:      "test-id",
	}

	if err := ValidateEnvelope(env); err == nil {
		t.Error("Should error on missing payload")
	}
}

func TestEncodeBytes(t *testing.T) {
	env := CreateRequestEnvelope("process", "agent", map[string]interface{}{
		"key": "value",
	})

	bytes, err := EncodeBytes(env)
	if err != nil {
		t.Fatalf("Encode failed: %v", err)
	}

	if len(bytes) == 0 {
		t.Error("Expected non-empty bytes")
	}

	// Should be valid JSON
	var decoded map[string]interface{}
	if err := json.Unmarshal(bytes, &decoded); err != nil {
		t.Errorf("Encoded bytes not valid JSON: %v", err)
	}
}

func TestDecodeBytes(t *testing.T) {
	// Create valid JSON envelope
	jsonStr := `{
		"version": "1.0",
		"type": "request",
		"id": "test-123",
		"timestamp": "2024-01-01T00:00:00Z",
		"payload": {"method": "test"}
	}`

	env, err := DecodeBytes([]byte(jsonStr))
	if err != nil {
		t.Fatalf("Decode failed: %v", err)
	}

	if env.ID != "test-123" {
		t.Errorf("Expected ID 'test-123', got '%s'", env.ID)
	}
}

func TestDecodeInvalidUTF8(t *testing.T) {
	// Invalid UTF-8 byte sequence
	invalidUTF8 := []byte{0xff, 0xfe, 0xfd}

	_, err := DecodeBytes(invalidUTF8)
	if err == nil {
		t.Error("Should error on invalid UTF-8")
	}
}

func TestRoundtripBytes(t *testing.T) {
	original := CreateResponseEnvelope("req-123", map[string]interface{}{
		"result": "success",
		"data":   map[string]interface{}{"count": 42},
	})

	// Encode
	bytes, err := EncodeBytes(original)
	if err != nil {
		t.Fatalf("Encode failed: %v", err)
	}

	// Decode
	decoded, err := DecodeBytes(bytes)
	if err != nil {
		t.Fatalf("Decode failed: %v", err)
	}

	// Verify
	if decoded.Version != original.Version {
		t.Error("Version mismatch")
	}
	if decoded.Type != original.Type {
		t.Error("Type mismatch")
	}
	if decoded.ID != original.ID {
		t.Error("ID mismatch")
	}
}
