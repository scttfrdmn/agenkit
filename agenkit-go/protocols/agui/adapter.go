package agui

import (
	"context"
	"fmt"
	"strings"

	"github.com/google/uuid"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// metadataSchemaVersion is agenkit's own metadata-event schema version --
// NOT a version of the AG-UI wire protocol itself. AG-UI (docs.ag-ui.com)
// has no numbered spec revision to align with, so this was previously a
// made-up "1.0" that looked like an upstream protocol version but wasn't
// (agenkit#781 item D: "a wrong version is worse than an absent one"). One
// named constant per language, so all emitters advertise the same value
// and a bump can't drift between them.
const metadataSchemaVersion = "1.0"

// AGUIAdapter wraps an Agenkit agent to produce AG-UI protocol events.
//
// Converts standard Agent.Process() calls into streaming AG-UI events
// that can be consumed by frontends implementing the AG-UI protocol.
//
// Features:
//   - Automatic event generation from agent responses
//   - Streaming text message support
//   - Error handling with ErrorEvents
//   - Metadata emission for agent capabilities
//   - Message ID tracking for correlation
//
// Example:
//
//	// Wrap any agent
//	agent := NewMyAgent()
//	adapter := agui.NewAGUIAdapter(agent)
//
//	// Stream events to frontend
//	message := agenkit.NewMessage("user", "What's the weather?")
//	ctx := context.Background()
//	for event := range adapter.StreamEvents(ctx, message) {
//	    // Send event to frontend via HTTP/SSE or WebSocket
//	    json, _ := event.ToJSON()
//	    sendToFrontend(json)
//	}
type AGUIAdapter struct {
	agent             agenkit.Agent
	agentName         string
	emitHeartbeats    bool
	heartbeatInterval float64
	heartbeatSequence int64
}

// AGUIAdapterConfig holds configuration for AGUIAdapter
type AGUIAdapterConfig struct {
	// Optional name for the agent (defaults to agent.Name())
	AgentName string

	// Whether to emit heartbeat events
	EmitHeartbeats bool

	// Seconds between heartbeat events (if enabled)
	HeartbeatInterval float64
}

// NewAGUIAdapter creates a new AG-UI adapter for an agent
func NewAGUIAdapter(agent agenkit.Agent) *AGUIAdapter {
	return NewAGUIAdapterWithConfig(agent, AGUIAdapterConfig{})
}

// NewAGUIAdapterWithConfig creates a new AG-UI adapter with custom configuration
func NewAGUIAdapterWithConfig(agent agenkit.Agent, config AGUIAdapterConfig) *AGUIAdapter {
	agentName := config.AgentName
	if agentName == "" {
		agentName = agent.Name()
	}

	heartbeatInterval := config.HeartbeatInterval
	if heartbeatInterval == 0 {
		heartbeatInterval = 30.0
	}

	return &AGUIAdapter{
		agent:             agent,
		agentName:         agentName,
		emitHeartbeats:    config.EmitHeartbeats,
		heartbeatInterval: heartbeatInterval,
		heartbeatSequence: 0,
	}
}

// Agent returns the wrapped agent
func (a *AGUIAdapter) Agent() agenkit.Agent {
	return a.agent
}

// AgentName returns the agent's name
func (a *AGUIAdapter) AgentName() string {
	return a.agentName
}

// StreamEventsConfig holds options for streaming events
type StreamEventsConfig struct {
	// Optional message ID (auto-generated if not provided)
	MessageID string

	// Whether to emit metadata event first
	EmitMetadata bool
}

// StreamEvents processes message and streams AG-UI events.
//
// Converts agent's response into a stream of AG-UI events:
//  1. MetadataEvent (optional) - Agent capabilities
//  2. TextMessageStart - Beginning of response
//  3. TextMessageChunk(s) - Streaming content
//  4. TextMessageComplete - End of response
//
// Example:
//
//	for event := range adapter.StreamEvents(ctx, message) {
//	    switch e := event.(type) {
//	    case *TextMessageChunk:
//	        fmt.Print(e.ContentString())
//	    case *TextMessageComplete:
//	        fmt.Printf("\n[Finished: %s]\n", e.FinishReason)
//	    }
//	}
func (a *AGUIAdapter) StreamEvents(ctx context.Context, message *agenkit.Message) <-chan AGUIEvent {
	return a.StreamEventsWithConfig(ctx, message, StreamEventsConfig{EmitMetadata: true})
}

// StreamEventsWithConfig streams events with custom configuration
func (a *AGUIAdapter) StreamEventsWithConfig(
	ctx context.Context,
	message *agenkit.Message,
	config StreamEventsConfig,
) <-chan AGUIEvent {
	eventChan := make(chan AGUIEvent, 10)

	go func() {
		defer close(eventChan)

		msgID := config.MessageID
		if msgID == "" {
			msgID = a.generateMessageID()
		}

		// Emit metadata about agent capabilities
		if config.EmitMetadata {
			select {
			case eventChan <- a.createMetadataEvent():
			case <-ctx.Done():
				return
			}
		}

		// Emit text message start
		startEvent := NewTextMessageStart(msgID, "assistant")
		startEvent.Metadata["agent_name"] = a.agentName
		select {
		case eventChan <- startEvent:
		case <-ctx.Done():
			return
		}

		// Process message with agent
		response, err := a.agent.Process(ctx, message)
		if err != nil {
			// Convert error to error event
			errorEvent := a.createErrorEvent(msgID, err)
			select {
			case eventChan <- errorEvent:
			case <-ctx.Done():
				return
			}

			// Also emit a completion with error
			completeEvent := NewTextMessageComplete(msgID, "", "error")
			completeEvent.Metadata["error"] = err.Error()
			select {
			case eventChan <- completeEvent:
			case <-ctx.Done():
				return
			}
			return
		}

		// Extract content
		content := response.ContentString()

		// Stream content in chunks (simulating streaming)
		// In a real streaming implementation, this would yield as content arrives
		chunkSize := 50 // Characters per chunk
		chunkIndex := 0
		for i := 0; i < len(content); i += chunkSize {
			end := i + chunkSize
			if end > len(content) {
				end = len(content)
			}
			chunk := content[i:end]

			chunkEvent := NewTextMessageChunk(msgID, chunk)
			chunkEvent.Metadata["chunk_index"] = chunkIndex
			select {
			case eventChan <- chunkEvent:
			case <-ctx.Done():
				return
			}
			chunkIndex++
		}

		// Emit completion
		completeEvent := NewTextMessageComplete(msgID, content, "stop")
		completeEvent.Metadata["agent_name"] = a.agentName
		if response.Metadata != nil {
			completeEvent.Metadata["response_metadata"] = response.Metadata
		}
		select {
		case eventChan <- completeEvent:
		case <-ctx.Done():
			return
		}
	}()

	return eventChan
}

// Process processes message and returns final result (non-streaming).
//
// Convenience method that consumes all events and returns the
// final message. Use StreamEvents() if you need streaming.
func (a *AGUIAdapter) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return a.ProcessWithMessageID(ctx, message, "")
}

// ProcessWithMessageID processes message with custom message ID
func (a *AGUIAdapter) ProcessWithMessageID(
	ctx context.Context,
	message *agenkit.Message,
	messageID string,
) (*agenkit.Message, error) {
	var finalContent string
	var finalMetadata map[string]interface{}

	config := StreamEventsConfig{
		MessageID:    messageID,
		EmitMetadata: false,
	}

	for event := range a.StreamEventsWithConfig(ctx, message, config) {
		if complete, ok := event.(*TextMessageComplete); ok {
			finalContent = complete.Content
			finalMetadata = complete.Metadata
		}
	}

	return &agenkit.Message{
		Role:     "assistant",
		Content:  finalContent,
		Metadata: finalMetadata,
	}, nil
}

// generateMessageID generates a unique message ID
func (a *AGUIAdapter) generateMessageID() string {
	id := uuid.New().String()
	// Take first 12 characters of hex representation
	parts := strings.Split(id, "-")
	if len(parts) > 0 {
		return "msg-" + parts[0]
	}
	return "msg-" + id[:12]
}

// createMetadataEvent creates metadata event with agent capabilities
func (a *AGUIAdapter) createMetadataEvent() *MetadataEvent {
	data := map[string]interface{}{
		"agent_name":       a.agentName,
		"agent_type":       fmt.Sprintf("%T", a.agent),
		"capabilities":     a.agent.Capabilities(),
		"protocol_version": metadataSchemaVersion,
	}
	return NewMetadataEvent(data)
}

// createErrorEvent creates error event from error
func (a *AGUIAdapter) createErrorEvent(messageID string, err error) *ErrorEvent {
	errorType := fmt.Sprintf("%T", err)

	event := NewErrorEvent(errorType, err.Error(), true)
	event.ErrorDetails["message_id"] = messageID
	event.ErrorDetails["agent_name"] = a.agentName
	event.ErrorDetails["exception_type"] = errorType

	return event
}

// createHeartbeatEvent creates heartbeat event
func (a *AGUIAdapter) createHeartbeatEvent() *HeartbeatEvent {
	a.heartbeatSequence++
	return NewHeartbeatEvent(a.heartbeatSequence)
}
