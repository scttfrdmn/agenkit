// Package transport provides network transport abstractions for the protocol adapter.
package transport

import (
	"context"
	"encoding/json"
	"fmt"
	"net/url"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/adapter/errors"
	"github.com/agenkit/agenkit-go/proto/agentpb"
)

// GRPCTransport implements transport over gRPC.
type GRPCTransport struct {
	url           string
	host          string
	port          string
	conn          *grpc.ClientConn
	client        agentpb.AgentServiceClient
	mu            sync.Mutex
	connected     bool
	responseQueue chan []byte
}

// NewGRPCTransport creates a new gRPC transport.
// URL format: grpc://host:port
func NewGRPCTransport(endpoint string) (*GRPCTransport, error) {
	// Parse URL
	u, err := url.Parse(endpoint)
	if err != nil {
		return nil, fmt.Errorf("invalid gRPC URL: %w", err)
	}

	if u.Scheme != "grpc" {
		return nil, fmt.Errorf("invalid gRPC URL scheme: %s", u.Scheme)
	}

	if u.Hostname() == "" {
		return nil, fmt.Errorf("missing hostname in gRPC URL: %s", endpoint)
	}

	port := u.Port()
	if port == "" {
		port = "50051" // Default gRPC port
	}

	return &GRPCTransport{
		url:           endpoint,
		host:          u.Hostname(),
		port:          port,
		responseQueue: make(chan []byte, 100),
	}, nil
}

// Connect establishes connection to gRPC endpoint.
func (t *GRPCTransport) Connect(ctx context.Context) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.connected {
		return nil
	}

	// Create gRPC connection
	target := fmt.Sprintf("%s:%s", t.host, t.port)
	conn, err := grpc.NewClient(target, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return errors.NewConnectionError(fmt.Sprintf("failed to connect to %s", target), err)
	}

	t.conn = conn
	t.client = agentpb.NewAgentServiceClient(conn)
	t.connected = true

	return nil
}

// SendFramed sends a framed message via gRPC.
// This method converts the JSON envelope to protobuf, makes the gRPC call,
// and stores the response(s) in the response queue.
func (t *GRPCTransport) SendFramed(ctx context.Context, data []byte) error {
	t.mu.Lock()
	if !t.connected {
		t.mu.Unlock()
		return errors.NewConnectionError("not connected", nil)
	}
	client := t.client
	t.mu.Unlock()

	// Decode JSON envelope
	var envelope codec.Envelope
	if err := json.Unmarshal(data, &envelope); err != nil {
		return errors.NewInvalidMessageError(fmt.Sprintf("failed to decode JSON: %v", err), nil)
	}

	// Convert JSON envelope to protobuf Request
	pbRequest, err := t.jsonToProtobufRequest(&envelope)
	if err != nil {
		return err
	}

	// Determine if this is a streaming request
	method, _ := envelope.Payload["method"].(string)
	isStreaming := method == "stream"

	if isStreaming {
		// Use ProcessStream RPC
		stream, err := client.ProcessStream(ctx, pbRequest)
		if err != nil {
			// Convert gRPC error to JSON error envelope
			t.handleGRPCError(envelope.ID, err)
			return nil
		}

		// Process stream chunks
		for {
			chunk, err := stream.Recv()
			if err != nil {
				if err.Error() == "EOF" {
					// Stream ended normally
					break
				}
				// Convert gRPC error to JSON error envelope
				t.handleGRPCError(envelope.ID, err)
				break
			}

			// Convert protobuf StreamChunk to JSON envelope
			jsonEnvelope := t.protobufChunkToJSON(chunk)
			jsonBytes, err := json.Marshal(jsonEnvelope)
			if err != nil {
				return errors.NewInvalidMessageError(fmt.Sprintf("failed to encode JSON: %v", err), nil)
			}

			select {
			case t.responseQueue <- jsonBytes:
			case <-ctx.Done():
				return ctx.Err()
			}
		}
	} else {
		// Use unary Process RPC
		pbResponse, err := client.Process(ctx, pbRequest)
		if err != nil {
			// Convert gRPC error to JSON error envelope
			t.handleGRPCError(envelope.ID, err)
			return nil
		}

		// Convert protobuf Response to JSON envelope
		jsonEnvelope := t.protobufResponseToJSON(pbResponse)
		jsonBytes, err := json.Marshal(jsonEnvelope)
		if err != nil {
			return errors.NewInvalidMessageError(fmt.Sprintf("failed to encode JSON: %v", err), nil)
		}

		select {
		case t.responseQueue <- jsonBytes:
		case <-ctx.Done():
			return ctx.Err()
		}
	}

	return nil
}

// ReceiveFramed receives a framed message via gRPC.
// This retrieves the response that was stored during SendFramed().
func (t *GRPCTransport) ReceiveFramed(ctx context.Context) ([]byte, error) {
	t.mu.Lock()
	if !t.connected {
		t.mu.Unlock()
		return nil, errors.NewConnectionError("not connected", nil)
	}
	t.mu.Unlock()

	select {
	case data := <-t.responseQueue:
		return data, nil
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}

// Close closes the gRPC connection.
func (t *GRPCTransport) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.conn != nil {
		err := t.conn.Close()
		t.conn = nil
		t.client = nil
		t.connected = false
		return err
	}
	return nil
}

// IsConnected returns whether the transport is connected.
func (t *GRPCTransport) IsConnected() bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	return t.connected && t.conn != nil && t.client != nil
}

// jsonToProtobufRequest converts a JSON request envelope to protobuf Request.
func (t *GRPCTransport) jsonToProtobufRequest(envelope *codec.Envelope) (*agentpb.Request, error) {
	payload := envelope.Payload
	if payload == nil {
		payload = make(map[string]interface{})
	}

	// Create protobuf Request
	request := &agentpb.Request{
		Version:   envelope.Version,
		Id:        envelope.ID,
		Timestamp: envelope.Timestamp,
		Method:    getStringFromMap(payload, "method", "process"),
		AgentName: getStringFromMap(payload, "agent_name", ""),
		Metadata:  make(map[string]string),
	}

	// Convert messages if present
	// Check for "messages" (plural) first
	if messagesRaw, ok := payload["messages"]; ok {
		if messages, ok := messagesRaw.([]interface{}); ok {
			for _, msgRaw := range messages {
				if msgMap, ok := msgRaw.(map[string]interface{}); ok {
					pbMsg := &agentpb.Message{
						Role:      getStringFromMap(msgMap, "role", ""),
						Content:   t.serializeContent(msgMap["content"]),
						Timestamp: getStringFromMap(msgMap, "timestamp", ""),
						Metadata:  make(map[string]string),
					}

					// Add metadata
					if metadataRaw, ok := msgMap["metadata"]; ok {
						if metadata, ok := metadataRaw.(map[string]interface{}); ok {
							for k, v := range metadata {
								pbMsg.Metadata[k] = fmt.Sprintf("%v", v)
							}
						}
					}

					request.Messages = append(request.Messages, pbMsg)
				}
			}
		}
	} else if messageRaw, ok := payload["message"]; ok {
		// Check for single "message" (singular) - used by RemoteAgent
		if msgMap, ok := messageRaw.(map[string]interface{}); ok {
			pbMsg := &agentpb.Message{
				Role:      getStringFromMap(msgMap, "role", ""),
				Content:   t.serializeContent(msgMap["content"]),
				Timestamp: getStringFromMap(msgMap, "timestamp", ""),
				Metadata:  make(map[string]string),
			}

			// Add metadata
			if metadataRaw, ok := msgMap["metadata"]; ok {
				if metadata, ok := metadataRaw.(map[string]interface{}); ok {
					for k, v := range metadata {
						pbMsg.Metadata[k] = fmt.Sprintf("%v", v)
					}
				}
			}

			request.Messages = append(request.Messages, pbMsg)
		}
	}

	// Convert tool_call if present
	if toolCallRaw, ok := payload["tool_call"]; ok {
		if toolCall, ok := toolCallRaw.(map[string]interface{}); ok {
			pbToolCall := &agentpb.ToolCall{
				Name:     getStringFromMap(toolCall, "name", ""),
				Metadata: make(map[string]string),
			}

			// Serialize arguments
			if args, ok := toolCall["arguments"]; ok {
				argsJSON, err := json.Marshal(args)
				if err != nil {
					return nil, errors.NewInvalidMessageError(fmt.Sprintf("failed to serialize tool arguments: %v", err), nil)
				}
				pbToolCall.Arguments = string(argsJSON)
			}

			// Add metadata
			if metadataRaw, ok := toolCall["metadata"]; ok {
				if metadata, ok := metadataRaw.(map[string]interface{}); ok {
					for k, v := range metadata {
						pbToolCall.Metadata[k] = fmt.Sprintf("%v", v)
					}
				}
			}

			request.ToolCall = pbToolCall
		}
	}

	// Add metadata
	if metadataRaw, ok := payload["metadata"]; ok {
		if metadata, ok := metadataRaw.(map[string]interface{}); ok {
			for k, v := range metadata {
				request.Metadata[k] = fmt.Sprintf("%v", v)
			}
		}
	}

	return request, nil
}

// protobufResponseToJSON converts protobuf Response to JSON response envelope.
func (t *GRPCTransport) protobufResponseToJSON(response *agentpb.Response) *codec.Envelope {
	payload := make(map[string]interface{})

	// Handle different response types
	switch response.Type {
	case agentpb.ResponseType_RESPONSE_TYPE_MESSAGE:
		if response.Message != nil {
			metadata := response.Message.Metadata
			if metadata == nil {
				metadata = make(map[string]string)
			}
			msgData := map[string]interface{}{
				"role":      response.Message.Role,
				"content":   t.deserializeContent(response.Message.Content),
				"metadata":  metadata,
				"timestamp": response.Message.Timestamp,
			}
			payload["message"] = msgData
		}

	case agentpb.ResponseType_RESPONSE_TYPE_TOOL_RESULT:
		if response.ToolResult != nil {
			toolResultData := map[string]interface{}{
				"success":  response.ToolResult.Success,
				"data":     t.deserializeContent(response.ToolResult.Data),
				"metadata": response.ToolResult.Metadata,
			}
			if response.ToolResult.Error != "" {
				toolResultData["error"] = response.ToolResult.Error
			}
			payload["tool_result"] = toolResultData
		}

	case agentpb.ResponseType_RESPONSE_TYPE_ERROR:
		if response.Error != nil {
			return &codec.Envelope{
				Version:   response.Version,
				Type:      codec.TypeError,
				ID:        response.Id,
				Timestamp: response.Timestamp,
				Payload: map[string]interface{}{
					"error_code":    response.Error.Code,
					"error_message": response.Error.Message,
					"error_details": response.Error.Details,
				},
			}
		}
	}

	// Add metadata
	if len(response.Metadata) > 0 {
		payload["metadata"] = response.Metadata
	}

	return &codec.Envelope{
		Version:   response.Version,
		Type:      codec.TypeResponse,
		ID:        response.Id,
		Timestamp: response.Timestamp,
		Payload:   payload,
	}
}

// protobufChunkToJSON converts protobuf StreamChunk to JSON stream envelope.
func (t *GRPCTransport) protobufChunkToJSON(chunk *agentpb.StreamChunk) *codec.Envelope {
	switch chunk.Type {
	case agentpb.ChunkType_CHUNK_TYPE_END:
		return &codec.Envelope{
			Version:   chunk.Version,
			Type:      codec.TypeStreamEnd,
			ID:        chunk.Id,
			Timestamp: chunk.Timestamp,
			Payload:   make(map[string]interface{}),
		}

	case agentpb.ChunkType_CHUNK_TYPE_ERROR:
		if chunk.Error != nil {
			return &codec.Envelope{
				Version:   chunk.Version,
				Type:      codec.TypeError,
				ID:        chunk.Id,
				Timestamp: chunk.Timestamp,
				Payload: map[string]interface{}{
					"error_code":    chunk.Error.Code,
					"error_message": chunk.Error.Message,
					"error_details": chunk.Error.Details,
				},
			}
		}

	case agentpb.ChunkType_CHUNK_TYPE_MESSAGE:
		if chunk.Message != nil {
			metadata := chunk.Message.Metadata
			if metadata == nil {
				metadata = make(map[string]string)
			}
			msgData := map[string]interface{}{
				"role":      chunk.Message.Role,
				"content":   t.deserializeContent(chunk.Message.Content),
				"metadata":  metadata,
				"timestamp": chunk.Message.Timestamp,
			}
			return &codec.Envelope{
				Version:   chunk.Version,
				Type:      codec.TypeStreamChunk,
				ID:        chunk.Id,
				Timestamp: chunk.Timestamp,
				Payload: map[string]interface{}{
					"message": msgData,
				},
			}
		}
	}

	// Unknown chunk type
	return &codec.Envelope{
		Version:   chunk.Version,
		Type:      codec.TypeStreamChunk,
		ID:        chunk.Id,
		Timestamp: chunk.Timestamp,
		Payload:   make(map[string]interface{}),
	}
}

// serializeContent serializes content to string for protobuf.
func (t *GRPCTransport) serializeContent(content interface{}) string {
	if content == nil {
		return ""
	}
	if str, ok := content.(string); ok {
		return str
	}
	// Marshal to JSON
	data, err := json.Marshal(content)
	if err != nil {
		return fmt.Sprintf("%v", content)
	}
	return string(data)
}

// deserializeContent deserializes content from string.
func (t *GRPCTransport) deserializeContent(content string) interface{} {
	if content == "" {
		return content
	}

	// Try to parse as JSON, fall back to string
	var result interface{}
	if err := json.Unmarshal([]byte(content), &result); err == nil {
		return result
	}
	return content
}

// handleGRPCError converts a gRPC error to JSON error envelope and queues it.
func (t *GRPCTransport) handleGRPCError(requestID string, err error) {
	errorCode := "CONNECTION_FAILED"
	errorMessage := err.Error()

	// Convert gRPC status codes to error codes
	if st, ok := status.FromError(err); ok {
		errorCode = grpcStatusToErrorCode(st.Code())
		errorMessage = st.Message()
	}

	envelope := codec.CreateErrorEnvelope(requestID, errorCode, errorMessage, nil)
	jsonBytes, _ := json.Marshal(envelope)

	select {
	case t.responseQueue <- jsonBytes:
	default:
		// Queue full, drop error
	}
}

// grpcStatusToErrorCode converts gRPC status code to error code string.
func grpcStatusToErrorCode(code codes.Code) string {
	switch code {
	case codes.Unavailable:
		return "CONNECTION_FAILED"
	case codes.DeadlineExceeded:
		return "CONNECTION_TIMEOUT"
	case codes.Canceled:
		return "CONNECTION_CLOSED"
	case codes.NotFound:
		return "AGENT_NOT_FOUND"
	case codes.InvalidArgument:
		return "INVALID_MESSAGE"
	case codes.FailedPrecondition:
		return "AGENT_UNAVAILABLE"
	case codes.Unimplemented:
		return "UNSUPPORTED_VERSION"
	default:
		return "CONNECTION_FAILED"
	}
}

// getStringFromMap safely gets a string value from a map with a default.
func getStringFromMap(m map[string]interface{}, key string, defaultValue string) string {
	if v, ok := m[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
	}
	return defaultValue
}

// createErrorEnvelope creates a JSON error envelope.
func createErrorEnvelope(requestID string, errorCode string, errorMessage string) *codec.Envelope {
	return &codec.Envelope{
		Version:   codec.ProtocolVersion,
		Type:      codec.TypeError,
		ID:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Payload: map[string]interface{}{
			"error_code":    errorCode,
			"error_message": errorMessage,
			"error_details": make(map[string]interface{}),
		},
	}
}
