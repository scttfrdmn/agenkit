// Package grpc provides gRPC server implementation for agent communication.
package grpc

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	"github.com/agenkit/agenkit-go/adapter/codec"
	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/proto/agentpb"
)

// GRPCServer implements a gRPC server for agent communication.
type GRPCServer struct {
	agentpb.UnimplementedAgentServiceServer
	agent    agenkit.Agent
	listener net.Listener
	server   *grpc.Server
	mu       sync.Mutex
	running  bool
}

// NewGRPCServer creates a new gRPC server.
func NewGRPCServer(agent agenkit.Agent, address string) (*GRPCServer, error) {
	listener, err := net.Listen("tcp", address)
	if err != nil {
		return nil, fmt.Errorf("failed to listen on %s: %w", address, err)
	}

	server := grpc.NewServer()
	grpcServer := &GRPCServer{
		agent:    agent,
		listener: listener,
		server:   server,
	}

	agentpb.RegisterAgentServiceServer(server, grpcServer)

	return grpcServer, nil
}

// Start starts the gRPC server.
func (s *GRPCServer) Start() error {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("server already running")
	}
	s.running = true
	s.mu.Unlock()

	go func() {
		if err := s.server.Serve(s.listener); err != nil {
			// Server stopped
		}
	}()

	return nil
}

// Stop stops the gRPC server.
func (s *GRPCServer) Stop() error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.running {
		return nil
	}

	s.server.GracefulStop()
	s.running = false

	return nil
}

// Process handles unary Process RPC.
func (s *GRPCServer) Process(ctx context.Context, req *agentpb.Request) (*agentpb.Response, error) {
	// Convert protobuf Request to agenkit Message
	message, err := s.protobufRequestToMessage(req)
	if err != nil {
		return nil, status.Errorf(codes.InvalidArgument, "invalid request: %v", err)
	}

	// Process with agent
	response, err := s.agent.Process(ctx, message)
	if err != nil {
		return s.createErrorResponse(req.Id, "AGENT_ERROR", err.Error()), nil
	}

	// Convert response to protobuf
	return s.messageToProtobufResponse(req.Id, response), nil
}

// ProcessStream handles streaming ProcessStream RPC.
func (s *GRPCServer) ProcessStream(req *agentpb.Request, stream agentpb.AgentService_ProcessStreamServer) error {
	// Check if agent supports streaming
	streamer, ok := s.agent.(interface {
		Stream(context.Context, *agenkit.Message) (<-chan *agenkit.Message, <-chan error)
	})
	if !ok {
		// Fall back to unary processing
		response, err := s.Process(stream.Context(), req)
		if err != nil {
			return err
		}

		// Convert response to stream chunk
		chunk := &agentpb.StreamChunk{
			Version:   response.Version,
			Id:        response.Id,
			Timestamp: response.Timestamp,
			Type:      agentpb.ChunkType_CHUNK_TYPE_MESSAGE,
			Message:   response.Message,
		}

		if err := stream.Send(chunk); err != nil {
			return err
		}

		// Send end chunk
		endChunk := &agentpb.StreamChunk{
			Version:   codec.ProtocolVersion,
			Id:        req.Id,
			Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
			Type:      agentpb.ChunkType_CHUNK_TYPE_END,
		}

		return stream.Send(endChunk)
	}

	// Convert protobuf Request to agenkit Message
	message, err := s.protobufRequestToMessage(req)
	if err != nil {
		return status.Errorf(codes.InvalidArgument, "invalid request: %v", err)
	}

	// Stream with agent
	messageChan, errorChan := streamer.Stream(stream.Context(), message)

	// Forward messages to gRPC stream
	for {
		select {
		case msg, ok := <-messageChan:
			if !ok {
				// Channel closed, send end chunk
				endChunk := &agentpb.StreamChunk{
					Version:   codec.ProtocolVersion,
					Id:        req.Id,
					Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
					Type:      agentpb.ChunkType_CHUNK_TYPE_END,
				}
				return stream.Send(endChunk)
			}

			// Convert message to stream chunk
			pbMsg := s.messageToProtobufMessage(msg)
			chunk := &agentpb.StreamChunk{
				Version:   codec.ProtocolVersion,
				Id:        req.Id,
				Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
				Type:      agentpb.ChunkType_CHUNK_TYPE_MESSAGE,
				Message:   pbMsg,
			}

			if err := stream.Send(chunk); err != nil {
				return err
			}

		case err, ok := <-errorChan:
			if !ok {
				// Error channel closed
				continue
			}
			if err != nil {
				// Send error chunk
				errorChunk := &agentpb.StreamChunk{
					Version:   codec.ProtocolVersion,
					Id:        req.Id,
					Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
					Type:      agentpb.ChunkType_CHUNK_TYPE_ERROR,
					Error: &agentpb.Error{
						Code:    "AGENT_ERROR",
						Message: err.Error(),
						Details: make(map[string]string),
					},
				}
				return stream.Send(errorChunk)
			}

		case <-stream.Context().Done():
			return stream.Context().Err()
		}
	}
}

// BidirectionalStream handles bidirectional streaming (not implemented yet).
func (s *GRPCServer) BidirectionalStream(stream agentpb.AgentService_BidirectionalStreamServer) error {
	return status.Errorf(codes.Unimplemented, "bidirectional streaming not implemented")
}

// protobufRequestToMessage converts protobuf Request to agenkit Message.
func (s *GRPCServer) protobufRequestToMessage(req *agentpb.Request) (*agenkit.Message, error) {
	// For now, we'll use the first message in the request
	// This is a simplified implementation
	if len(req.Messages) == 0 {
		return nil, fmt.Errorf("no messages in request")
	}

	pbMsg := req.Messages[0]
	content := s.deserializeContent(pbMsg.Content)

	// Parse timestamp
	timestamp, err := time.Parse(time.RFC3339Nano, pbMsg.Timestamp)
	if err != nil {
		timestamp = time.Now().UTC()
	}

	message := &agenkit.Message{
		Role:      pbMsg.Role,
		Content:   fmt.Sprintf("%v", content),
		Metadata:  make(map[string]interface{}),
		Timestamp: timestamp,
	}

	// Add metadata
	for k, v := range pbMsg.Metadata {
		message.Metadata[k] = v
	}

	return message, nil
}

// messageToProtobufResponse converts agenkit Message to protobuf Response.
func (s *GRPCServer) messageToProtobufResponse(requestID string, message *agenkit.Message) *agentpb.Response {
	pbMsg := s.messageToProtobufMessage(message)

	return &agentpb.Response{
		Version:   codec.ProtocolVersion,
		Id:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Type:      agentpb.ResponseType_RESPONSE_TYPE_MESSAGE,
		Message:   pbMsg,
		Metadata:  make(map[string]string),
	}
}

// messageToProtobufMessage converts agenkit Message to protobuf Message.
func (s *GRPCServer) messageToProtobufMessage(message *agenkit.Message) *agentpb.Message {
	pbMsg := &agentpb.Message{
		Role:      message.Role,
		Content:   s.serializeContent(message.Content),
		Timestamp: message.Timestamp.Format(time.RFC3339Nano),
		Metadata:  make(map[string]string),
	}

	// Add metadata
	for k, v := range message.Metadata {
		pbMsg.Metadata[k] = fmt.Sprintf("%v", v)
	}

	return pbMsg
}

// createErrorResponse creates an error Response.
func (s *GRPCServer) createErrorResponse(requestID string, errorCode string, errorMessage string) *agentpb.Response {
	return &agentpb.Response{
		Version:   codec.ProtocolVersion,
		Id:        requestID,
		Timestamp: time.Now().UTC().Format(time.RFC3339Nano),
		Type:      agentpb.ResponseType_RESPONSE_TYPE_ERROR,
		Error: &agentpb.Error{
			Code:    errorCode,
			Message: errorMessage,
			Details: make(map[string]string),
		},
		Metadata: make(map[string]string),
	}
}

// serializeContent serializes content to string for protobuf.
func (s *GRPCServer) serializeContent(content interface{}) string {
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
func (s *GRPCServer) deserializeContent(content string) interface{} {
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
