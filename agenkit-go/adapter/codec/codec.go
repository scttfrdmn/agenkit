// Package codec provides message serialization and deserialization for the protocol adapter.
package codec

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/google/uuid"
)

const ProtocolVersion = "1.0"

// Envelope types
const (
	TypeRequest     = "request"
	TypeResponse    = "response"
	TypeError       = "error"
	TypeHeartbeat   = "heartbeat"
	TypeRegister    = "register"
	TypeUnregister  = "unregister"
	TypeStreamChunk = "stream_chunk"
	TypeStreamEnd   = "stream_end"
)

// Envelope represents a protocol message envelope.
type Envelope struct {
	Version   string                 `json:"version"`
	Type      string                 `json:"type"`
	ID        string                 `json:"id"`
	Timestamp string                 `json:"timestamp"`
	Payload   map[string]interface{} `json:"payload"`
}

// MessageData represents the serialized form of a Message.
type MessageData struct {
	Role      string                 `json:"role"`
	Content   string                 `json:"content"`
	Metadata  map[string]interface{} `json:"metadata"`
	Timestamp string                 `json:"timestamp"`
}

// ToolResultData represents the serialized form of a ToolResult.
type ToolResultData struct {
	Success  bool                   `json:"success"`
	Data     interface{}            `json:"data,omitempty"`
	Error    string                 `json:"error,omitempty"`
	Metadata map[string]interface{} `json:"metadata"`
}

// EncodeMessage converts a Message to its serializable form.
func EncodeMessage(msg *agenkit.Message) MessageData {
	return MessageData{
		Role:      msg.Role,
		Content:   msg.Content,
		Metadata:  msg.Metadata,
		Timestamp: msg.Timestamp.Format(time.RFC3339Nano),
	}
}

// DecodeMessage converts serialized message data to a Message.
func DecodeMessage(data MessageData) (*agenkit.Message, error) {
	timestamp, err := time.Parse(time.RFC3339Nano, data.Timestamp)
	if err != nil {
		timestamp = time.Now().UTC()
	}

	return &agenkit.Message{
		Role:      data.Role,
		Content:   data.Content,
		Metadata:  data.Metadata,
		Timestamp: timestamp,
	}, nil
}

// EncodeToolResult converts a ToolResult to its serializable form.
func EncodeToolResult(result *agenkit.ToolResult) ToolResultData {
	return ToolResultData{
		Success:  result.Success,
		Data:     result.Data,
		Error:    result.Error,
		Metadata: result.Metadata,
	}
}

// DecodeToolResult converts serialized tool result data to a ToolResult.
func DecodeToolResult(data ToolResultData) *agenkit.ToolResult {
	return &agenkit.ToolResult{
		Success:  data.Success,
		Data:     data.Data,
		Error:    data.Error,
		Metadata: data.Metadata,
	}
}

// CreateRequestEnvelope creates a protocol request envelope.
func CreateRequestEnvelope(method string, agentName string, payload map[string]interface{}) *Envelope {
	if payload == nil {
		payload = make(map[string]interface{})
	}

	payload["method"] = method
	if agentName != "" {
		payload["agent_name"] = agentName
	}

	return &Envelope{
		Version:   ProtocolVersion,
		Type:      TypeRequest,
		ID:        uuid.New().String(),
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Payload:   payload,
	}
}

// CreateResponseEnvelope creates a protocol response envelope.
func CreateResponseEnvelope(requestID string, payload map[string]interface{}) *Envelope {
	if payload == nil {
		payload = make(map[string]interface{})
	}

	return &Envelope{
		Version:   ProtocolVersion,
		Type:      TypeResponse,
		ID:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Payload:   payload,
	}
}

// CreateErrorEnvelope creates a protocol error envelope.
func CreateErrorEnvelope(requestID, errorCode, errorMessage string, errorDetails map[string]interface{}) *Envelope {
	if errorDetails == nil {
		errorDetails = make(map[string]interface{})
	}

	payload := map[string]interface{}{
		"error_code":    errorCode,
		"error_message": errorMessage,
		"error_details": errorDetails,
	}

	return &Envelope{
		Version:   ProtocolVersion,
		Type:      TypeError,
		ID:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Payload:   payload,
	}
}

// CreateStreamChunkEnvelope creates a protocol stream chunk envelope.
func CreateStreamChunkEnvelope(requestID string, message MessageData) *Envelope {
	payload := map[string]interface{}{
		"message": message,
	}

	return &Envelope{
		Version:   ProtocolVersion,
		Type:      TypeStreamChunk,
		ID:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Payload:   payload,
	}
}

// CreateStreamEndEnvelope creates a protocol stream end envelope.
func CreateStreamEndEnvelope(requestID string) *Envelope {
	return &Envelope{
		Version:   ProtocolVersion,
		Type:      TypeStreamEnd,
		ID:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Payload:   make(map[string]interface{}),
	}
}

// ValidateEnvelope validates a protocol envelope.
func ValidateEnvelope(env *Envelope) error {
	if env.Version == "" {
		return fmt.Errorf("missing 'version' field in envelope")
	}

	if env.Version != ProtocolVersion {
		return fmt.Errorf("unsupported protocol version: %s", env.Version)
	}

	if env.Type == "" {
		return fmt.Errorf("missing 'type' field in envelope")
	}

	validTypes := map[string]bool{
		TypeRequest:     true,
		TypeResponse:    true,
		TypeError:       true,
		TypeHeartbeat:   true,
		TypeRegister:    true,
		TypeUnregister:  true,
		TypeStreamChunk: true,
		TypeStreamEnd:   true,
	}

	if !validTypes[env.Type] {
		return fmt.Errorf("invalid message type: %s", env.Type)
	}

	if env.ID == "" {
		return fmt.Errorf("missing 'id' field in envelope")
	}

	if env.Payload == nil {
		return fmt.Errorf("missing 'payload' field in envelope")
	}

	return nil
}

// EncodeBytes encodes an envelope to bytes for transmission.
func EncodeBytes(env *Envelope) ([]byte, error) {
	return json.Marshal(env)
}

// DecodeBytes decodes bytes to an envelope.
func DecodeBytes(data []byte) (*Envelope, error) {
	var env Envelope
	if err := json.Unmarshal(data, &env); err != nil {
		return nil, fmt.Errorf("failed to decode JSON: %w", err)
	}

	if err := ValidateEnvelope(&env); err != nil {
		return nil, err
	}

	return &env, nil
}
