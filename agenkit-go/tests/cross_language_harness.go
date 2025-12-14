package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"time"
)

const (
	ProtocolVersion = "1.0"
	Version         = "0.41.0"

	// Exit codes
	ExitSuccess         = 0
	ExitError           = 1
	ExitProtocolError   = 2
	ExitTimeout         = 3
	ExitInternalError   = 4
)

// Protocol message structures

type Request struct {
	ProtocolVersion string                 `json:"protocol_version"`
	RequestID       string                 `json:"request_id"`
	Command         string                 `json:"command"`
	Payload         map[string]interface{} `json:"payload"`
}

type Response struct {
	ProtocolVersion string                 `json:"protocol_version"`
	RequestID       string                 `json:"request_id"`
	Status          string                 `json:"status"`
	Result          map[string]interface{} `json:"result,omitempty"`
	Error           *ErrorInfo             `json:"error,omitempty"`
}

type ErrorInfo struct {
	Type       string                 `json:"type"`
	Message    string                 `json:"message"`
	Details    map[string]interface{} `json:"details,omitempty"`
	StackTrace string                 `json:"stack_trace,omitempty"`
}

type TestPayload struct {
	Pattern    string                 `json:"pattern"`
	ScenarioID string                 `json:"scenario_id"`
	Input      map[string]interface{} `json:"input"`
}

type Message struct {
	Role     string                 `json:"role"`
	Content  string                 `json:"content"`
	Metadata map[string]interface{} `json:"metadata"`
}

type BehaviorData struct {
	Turns      int      `json:"turns,omitempty"`
	ToolCalls  []string `json:"tool_calls,omitempty"`
	SubAgents  []string `json:"sub_agents,omitempty"`
	Iterations int      `json:"iterations,omitempty"`
}

type ExecutionInfo struct {
	DurationMs  float64 `json:"duration_ms"`
	LLMCalls    int     `json:"llm_calls,omitempty"`
	TokensUsed  int     `json:"tokens_used,omitempty"`
	MemoryBytes int64   `json:"memory_bytes,omitempty"`
}

// Pattern registry
var supportedPatterns = map[string]bool{
	"reflection":           true,
	"sequential":           true,
	"parallel":             true,
	"router":               true,
	"react":                true,
	"conversational":       true,
	"agents_as_tools":      true,
	"fallback":             true,
	"supervisor":           true,
	"planning":             true,
	"task":                 true,
	"collaborative":        true,
	"human_in_loop":        true,
	"autonomous":           true,
	"multiagent":           true,
	"orchestration":        true,
	"memory":               true,
	"reasoning_with_tools": true,
}

func main() {
	// Read request from stdin
	requestData, err := io.ReadAll(os.Stdin)
	if err != nil {
		writeErrorResponse("", "InternalError", fmt.Sprintf("Failed to read stdin: %v", err))
		os.Exit(ExitInternalError)
	}

	// Parse request
	var request Request
	if err := json.Unmarshal(requestData, &request); err != nil {
		writeErrorResponse("", "ProtocolError", fmt.Sprintf("Invalid JSON: %v", err))
		os.Exit(ExitProtocolError)
	}

	// Handle request
	response := handleRequest(&request)

	// Write response
	responseData, err := json.Marshal(response)
	if err != nil {
		writeErrorResponse(request.RequestID, "InternalError", fmt.Sprintf("Failed to marshal response: %v", err))
		os.Exit(ExitInternalError)
	}

	fmt.Println(string(responseData))

	// Exit with appropriate code
	if response.Status == "success" {
		os.Exit(ExitSuccess)
	}
	os.Exit(ExitError)
}

func handleRequest(request *Request) *Response {
	// Validate protocol version
	if request.ProtocolVersion != ProtocolVersion {
		return &Response{
			ProtocolVersion: ProtocolVersion,
			RequestID:       request.RequestID,
			Status:          "error",
			Error: &ErrorInfo{
				Type:    "ProtocolError",
				Message: fmt.Sprintf("Protocol version mismatch: expected %s, got %s", ProtocolVersion, request.ProtocolVersion),
			},
		}
	}

	// Route command
	var result map[string]interface{}
	var err *ErrorInfo

	switch request.Command {
	case "execute_test":
		result, err = executeTest(request.Payload)
	case "get_info":
		result, err = getInfo()
	case "health_check":
		result, err = healthCheck()
	default:
		err = &ErrorInfo{
			Type:    "CommandNotFound",
			Message: fmt.Sprintf("Unknown command: %s", request.Command),
		}
	}

	// Build response
	response := &Response{
		ProtocolVersion: ProtocolVersion,
		RequestID:       request.RequestID,
	}

	if err != nil {
		response.Status = "error"
		response.Error = err
	} else {
		response.Status = "success"
		response.Result = result
	}

	return response
}

func executeTest(payload map[string]interface{}) (map[string]interface{}, *ErrorInfo) {
	// Parse test payload
	pattern, ok := payload["pattern"].(string)
	if !ok {
		return nil, &ErrorInfo{
			Type:    "ValidationError",
			Message: "Pattern name is required",
		}
	}

	// Normalize pattern name to lowercase for case-insensitive matching
	patternLower := strings.ToLower(pattern)

	_, ok = payload["scenario_id"].(string)
	if !ok {
		return nil, &ErrorInfo{
			Type:    "ValidationError",
			Message: "Scenario ID is required",
		}
	}

	input, ok := payload["input"].(map[string]interface{})
	if !ok {
		return nil, &ErrorInfo{
			Type:    "ValidationError",
			Message: "Input is required",
		}
	}

	// Check if pattern is supported
	if !supportedPatterns[patternLower] {
		return nil, &ErrorInfo{
			Type:    "PatternNotFound",
			Message: fmt.Sprintf("Pattern '%s' not implemented in Go harness", pattern),
		}
	}

	// Parse input message
	messageData, ok := input["message"].(map[string]interface{})
	if !ok {
		return nil, &ErrorInfo{
			Type:    "ValidationError",
			Message: "Input message is required",
		}
	}

	role, _ := messageData["role"].(string)
	content, _ := messageData["content"].(string)
	metadata, _ := messageData["metadata"].(map[string]interface{})

	message := Message{
		Role:     role,
		Content:  content,
		Metadata: metadata,
	}

	// Get configuration
	config, _ := input["config"].(map[string]interface{})

	// Execute pattern
	ctx := context.Background()
	startTime := time.Now()

	result, err := executePattern(ctx, patternLower, message, config)
	if err != nil {
		return nil, &ErrorInfo{
			Type:    "ExecutionError",
			Message: err.Error(),
		}
	}

	duration := time.Since(startTime)

	// Build execution info
	executionInfo := ExecutionInfo{
		DurationMs: float64(duration.Milliseconds()),
		LLMCalls:   0, // TODO: Track actual LLM calls
		TokensUsed: 0, // TODO: Track actual token usage
	}

	// Return result
	return map[string]interface{}{
		"output": map[string]interface{}{
			"message": map[string]interface{}{
				"role":     result.Role,
				"content":  result.Content,
				"metadata": result.Metadata,
			},
			"behavior": map[string]interface{}{
				"turns":      1, // TODO: Track actual turns
				"tool_calls": []string{},
				"sub_agents": []string{},
			},
		},
		"execution_info": map[string]interface{}{
			"duration_ms": executionInfo.DurationMs,
			"llm_calls":   executionInfo.LLMCalls,
			"tokens_used": executionInfo.TokensUsed,
		},
	}, nil
}

func executePattern(ctx context.Context, patternName string, message Message, config map[string]interface{}) (*Message, error) {
	// This is a simplified implementation that returns mock responses
	// TODO: Implement actual pattern execution based on patternName and config

	switch patternName {
	case "reflection":
		return executeReflection(ctx, message, config)
	case "sequential":
		return executeSequential(ctx, message, config)
	case "parallel":
		return executeParallel(ctx, message, config)
	// Add other patterns...
	default:
		// Mock response for now
		return &Message{
			Role:    "assistant",
			Content: fmt.Sprintf("Mock response for %s pattern", patternName),
			Metadata: map[string]interface{}{
				"pattern":   patternName,
				"mock":      true,
			},
		}, nil
	}
}

func executeReflection(ctx context.Context, message Message, config map[string]interface{}) (*Message, error) {
	// TODO: Implement actual reflection pattern execution
	// For now, return a mock response

	maxIterations := 3
	if maxIter, ok := config["max_iterations"].(float64); ok {
		maxIterations = int(maxIter)
	}

	return &Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Reflected response to: %s", message.Content),
		Metadata: map[string]interface{}{
			"iterations": 1,
			"improved":   true,
			"max_iterations": maxIterations,
		},
	}, nil
}

func executeSequential(ctx context.Context, message Message, config map[string]interface{}) (*Message, error) {
	// TODO: Implement actual sequential pattern execution
	agents, _ := config["agents"].([]interface{})
	agentCount := len(agents)

	return &Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Sequential result: %s", message.Content),
		Metadata: map[string]interface{}{
			"agent_count": agentCount,
		},
	}, nil
}

func executeParallel(ctx context.Context, message Message, config map[string]interface{}) (*Message, error) {
	// TODO: Implement actual parallel pattern execution
	agents, _ := config["agents"].([]interface{})
	agentCount := len(agents)

	return &Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Parallel result: %s", message.Content),
		Metadata: map[string]interface{}{
			"agent_count": agentCount,
		},
	}, nil
}

func getInfo() (map[string]interface{}, *ErrorInfo) {
	return map[string]interface{}{
		"language": "go",
		"version":  Version,
		"patterns_supported": []string{
			"reflection",
			"sequential",
			"parallel",
			"router",
			"react",
			"conversational",
			"agents_as_tools",
			"fallback",
			"supervisor",
			"planning",
			"task",
			"collaborative",
			"human_in_loop",
			"autonomous",
			"multiagent",
			"orchestration",
			"memory",
			"reasoning_with_tools",
		},
		"capabilities": map[string]interface{}{
			"streaming":     true,
			"async":         true,
			"llm_providers": []string{"openai", "anthropic"},
		},
	}, nil
}

func healthCheck() (map[string]interface{}, *ErrorInfo) {
	return map[string]interface{}{
		"healthy":        true,
		"uptime_seconds": 0.0, // Stateless harness
	}, nil
}

func writeErrorResponse(requestID, errorType, message string) {
	response := Response{
		ProtocolVersion: ProtocolVersion,
		RequestID:       requestID,
		Status:          "error",
		Error: &ErrorInfo{
			Type:    errorType,
			Message: message,
		},
	}

	data, _ := json.Marshal(response)
	fmt.Println(string(data))
}
