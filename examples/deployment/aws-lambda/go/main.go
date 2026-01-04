package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-lambda-go/lambdacontext"
	"github.com/aws/aws-xray-sdk-go/xray"

	"github.com/scttfrdmn/agenkit/agenkit-go"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// Request represents the Lambda request body
type Request struct {
	AgentType string          `json:"agent_type"` // react, conversational, router
	Message   agenkit.Message `json:"message"`
}

// Response represents the Lambda response body
type Response struct {
	Role     string                 `json:"role"`
	Content  string                 `json:"content"`
	Metadata map[string]interface{} `json:"metadata"`
}

// ============================================================
// Agent Creation Functions
// ============================================================

// createReActAgent creates a ReAct agent with tools
func createReActAgent(ctx context.Context) (agenkit.Agent, error) {
	// Mock LLM (replace with real LLM in production)
	mockLLM := &MockLLM{name: "mock-llm"}

	// Example calculator tool
	calcTool := &CalculatorTool{}

	agent, err := patterns.NewReActAgent(&patterns.ReActConfig{
		Agent:    mockLLM,
		Tools:    []agenkit.Tool{calcTool},
		MaxSteps: 5,
		Verbose:  true,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create ReAct agent: %w", err)
	}

	return agent, nil
}

// createConversationalAgent creates a conversational agent with memory
func createConversationalAgent(ctx context.Context) (agenkit.Agent, error) {
	mockLLM := &MockLLMClient{}

	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:    mockLLM,
		MaxHistory:   10,
		SystemPrompt: "You are a helpful AI assistant deployed on AWS Lambda.",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create conversational agent: %w", err)
	}

	return agent, nil
}

// createRouterAgent creates a router that delegates to specialists
func createRouterAgent(ctx context.Context) (agenkit.Agent, error) {
	// Create specialist agents
	reactAgent, err := createReActAgent(ctx)
	if err != nil {
		return nil, err
	}

	convAgent, err := createConversationalAgent(ctx)
	if err != nil {
		return nil, err
	}

	// Router function
	routerFn := func(msg *agenkit.Message) string {
		content := msg.Content
		if containsAny(content, []string{"calculate", "math"}) {
			return "calculator"
		} else if containsAny(content, []string{"chat", "talk"}) {
			return "conversational"
		}
		return "react"
	}

	router, err := patterns.NewRouterPattern(
		routerFn,
		map[string]agenkit.Agent{
			"calculator":     reactAgent,
			"conversational": convAgent,
			"react":          reactAgent,
		},
		nil,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create router: %w", err)
	}

	return router, nil
}

// ============================================================
// Mock Implementations (Replace with real LLM)
// ============================================================

// MockLLM implements Agent interface for testing
type MockLLM struct {
	name string
}

func (m *MockLLM) Name() string                 { return m.name }
func (m *MockLLM) Capabilities() []string       { return []string{"text-generation"} }
func (m *MockLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// In production, replace with OpenAI, Anthropic, Bedrock, etc.
	return &agenkit.Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Processed: %s", message.Content),
		Metadata: map[string]interface{}{
			"model": m.name,
		},
	}, nil
}

// MockLLMClient implements conversational LLM client
type MockLLMClient struct{}

func (m *MockLLMClient) Chat(messages []*agenkit.Message) (string, error) {
	if len(messages) == 0 {
		return "Hello! How can I help you?", nil
	}
	lastMsg := messages[len(messages)-1]
	return fmt.Sprintf("Response to: %s", lastMsg.Content), nil
}

// CalculatorTool implements Tool interface
type CalculatorTool struct{}

func (c *CalculatorTool) Name() string        { return "calculator" }
func (c *CalculatorTool) Description() string { return "Performs basic arithmetic operations" }

func (c *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	op, _ := params["operation"].(string)
	a, _ := params["a"].(float64)
	b, _ := params["b"].(float64)

	var result float64
	switch op {
	case "add":
		result = a + b
	case "subtract":
		result = a - b
	case "multiply":
		result = a * b
	case "divide":
		if b == 0 {
			return &agenkit.ToolResult{Error: "Division by zero"}, nil
		}
		result = a / b
	default:
		return &agenkit.ToolResult{Error: fmt.Sprintf("Unknown operation: %s", op)}, nil
	}

	return &agenkit.ToolResult{
		Output: fmt.Sprintf("%.2f", result),
	}, nil
}

// ============================================================
// Lambda Handler
// ============================================================

// handleRequest processes API Gateway requests
func handleRequest(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	// Start X-Ray segment
	ctx, seg := xray.BeginSegment(ctx, "agenkit-lambda-go")
	defer seg.Close(nil)

	// Log request
	log.Printf("Processing request: %s", request.RequestContext.RequestID)

	// Parse request body
	var req Request
	if err := json.Unmarshal([]byte(request.Body), &req); err != nil {
		return errorResponse(400, fmt.Sprintf("Invalid request body: %v", err)), nil
	}

	// Validate agent type
	agentType := req.AgentType
	if agentType == "" {
		agentType = "react"
	}

	// X-Ray subsegment for agent creation
	ctx, agentSeg := xray.BeginSubsegment(ctx, fmt.Sprintf("create-agent-%s", agentType))

	var agent agenkit.Agent
	var err error

	switch agentType {
	case "react":
		agent, err = createReActAgent(ctx)
	case "conversational":
		agent, err = createConversationalAgent(ctx)
	case "router":
		agent, err = createRouterAgent(ctx)
	default:
		agentSeg.Close(nil)
		return errorResponse(400, fmt.Sprintf("Unknown agent type: %s", agentType)), nil
	}

	agentSeg.Close(err)

	if err != nil {
		return errorResponse(500, fmt.Sprintf("Failed to create agent: %v", err)), nil
	}

	// X-Ray subsegment for agent execution
	ctx, execSeg := xray.BeginSubsegment(ctx, "agent-execution")

	// Execute agent
	response, err := agent.Process(ctx, &req.Message)
	execSeg.Close(err)

	if err != nil {
		return errorResponse(500, fmt.Sprintf("Agent execution failed: %v", err)), nil
	}

	// Add Lambda context metadata
	if lc, ok := lambdacontext.FromContext(ctx); ok {
		if response.Metadata == nil {
			response.Metadata = make(map[string]interface{})
		}
		response.Metadata["lambda"] = map[string]interface{}{
			"request_id":         lc.AwsRequestID,
			"function_name":      lambdacontext.FunctionName,
			"memory_limit_mb":    lambdacontext.MemoryLimitInMB,
			"remaining_time_ms":  lc.Deadline.UnixMilli() - lambdacontext.Deadline.UnixMilli(),
		}
	}

	// Convert to response
	resp := Response{
		Role:     response.Role,
		Content:  response.Content,
		Metadata: response.Metadata,
	}

	respBody, err := json.Marshal(resp)
	if err != nil {
		return errorResponse(500, fmt.Sprintf("Failed to marshal response: %v", err)), nil
	}

	return events.APIGatewayProxyResponse{
		StatusCode: 200,
		Headers: map[string]string{
			"Content-Type": "application/json",
			"X-Agent-Type": agentType,
		},
		Body: string(respBody),
	}, nil
}

// errorResponse creates an error response
func errorResponse(statusCode int, message string) events.APIGatewayProxyResponse {
	errBody := map[string]string{
		"error":   "request_failed",
		"message": message,
	}
	body, _ := json.Marshal(errBody)

	return events.APIGatewayProxyResponse{
		StatusCode: statusCode,
		Headers: map[string]string{
			"Content-Type": "application/json",
		},
		Body: string(body),
	}
}

// Helper function
func containsAny(s string, substrings []string) bool {
	for _, substr := range substrings {
		if len(s) >= len(substr) {
			for i := 0; i <= len(s)-len(substr); i++ {
				if s[i:i+len(substr)] == substr {
					return true
				}
			}
		}
	}
	return false
}

// ============================================================
// Main
// ============================================================

func main() {
	// Wrap handler with X-Ray
	lambda.Start(xray.Handler(xray.NewFixedSegmentNamer(os.Getenv("AWS_LAMBDA_FUNCTION_NAME")), handleRequest))
}
