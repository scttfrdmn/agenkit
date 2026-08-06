package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-lambda-go/lambdacontext"
	"github.com/aws/aws-xray-sdk-go/xray"

	// The toolkit's Go types live in the agenkit package, not at the module root:
	// `github.com/scttfrdmn/agenkit/agenkit-go` contains no .go files, so this
	// import used to name a package that does not exist (#857, same class as #839).
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
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
func createReActAgent(_ context.Context) (agenkit.Agent, error) {
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
func createConversationalAgent(_ context.Context) (agenkit.Agent, error) {
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

	// Routing is done by a ClassifierAgent, not a bare func: NewRouterPattern(fn,
	// map, nil) never existed. See patterns.RouterConfig.
	router, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: &KeywordClassifier{},
		Agents: map[string]agenkit.Agent{
			"calculator":     reactAgent,
			"conversational": convAgent,
			"react":          reactAgent,
		},
		DefaultKey: "react",
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create router: %w", err)
	}

	return router, nil
}

// KeywordClassifier routes on simple keyword matches. A production deployment
// would classify with an LLM; this keeps the example dependency-free.
type KeywordClassifier struct{}

func (k *KeywordClassifier) Name() string           { return "keyword-classifier" }
func (k *KeywordClassifier) Capabilities() []string { return []string{"classification"} }

func (k *KeywordClassifier) Introspect() *agenkit.IntrospectionResult {
	result, err := agenkit.NewIntrospectionResult(k.Name(), k.Capabilities(), nil, nil, nil)
	if err != nil {
		return nil
	}
	return result
}

// Classify implements patterns.ClassifierAgent.
func (k *KeywordClassifier) Classify(_ context.Context, message *agenkit.Message) (string, error) {
	content := strings.ToLower(message.ContentString())
	switch {
	case containsAny(content, []string{"calculate", "math"}):
		return "calculator", nil
	case containsAny(content, []string{"chat", "talk"}):
		return "conversational", nil
	default:
		return "react", nil
	}
}

// Process satisfies agenkit.Agent by returning the classification as content.
func (k *KeywordClassifier) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	category, err := k.Classify(ctx, message)
	if err != nil {
		return nil, err
	}
	return agenkit.NewMessage("assistant", category), nil
}

// ============================================================
// Mock Implementations (Replace with real LLM)
// ============================================================

// MockLLM implements Agent interface for testing
type MockLLM struct {
	name string
}

func (m *MockLLM) Name() string           { return m.name }
func (m *MockLLM) Capabilities() []string { return []string{"text-generation"} }

// Introspect satisfies agenkit.Agent; every agent-shaped type must implement it.
func (m *MockLLM) Introspect() *agenkit.IntrospectionResult {
	result, err := agenkit.NewIntrospectionResult(m.name, m.Capabilities(), nil, nil, nil)
	if err != nil {
		return nil
	}
	return result
}

func (m *MockLLM) Process(_ context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// In production, replace with OpenAI, Anthropic, Bedrock, etc.
	return &agenkit.Message{
		Role:    "assistant",
		Content: fmt.Sprintf("Processed: %s", message.ContentString()),
		Metadata: map[string]interface{}{
			"model": m.name,
		},
	}, nil
}

// MockLLMClient implements patterns.ChatLLMClient. The signature is
// Chat(ctx, []*Message) (*Message, error) — the old Chat(messages) (string, error)
// matched no contract the toolkit accepts, so NewConversationalAgent rejected it.
type MockLLMClient struct{}

func (m *MockLLMClient) Chat(_ context.Context, messages []*agenkit.Message) (*agenkit.Message, error) {
	if len(messages) == 0 {
		return agenkit.NewMessage("assistant", "Hello! How can I help you?"), nil
	}
	lastMsg := messages[len(messages)-1]
	return agenkit.NewMessage("assistant", fmt.Sprintf("Response to: %s", lastMsg.ContentString())), nil
}

// CalculatorTool implements Tool interface
type CalculatorTool struct{}

func (c *CalculatorTool) Name() string        { return "calculator" }
func (c *CalculatorTool) Description() string { return "Performs basic arithmetic operations" }

func (c *CalculatorTool) Execute(_ context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
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
			return agenkit.NewToolError("division by zero"), nil
		}
		result = a / b
	default:
		return agenkit.NewToolError(fmt.Sprintf("unknown operation: %s", op)), nil
	}

	// ToolResult's payload field is Data, not Output — and it must be constructed
	// with Success: true, which the struct literal did not set. NewToolResult /
	// NewToolError do both.
	return agenkit.NewToolResult(fmt.Sprintf("%.2f", result)), nil
}

// ============================================================
// Lambda Handler
// ============================================================

// handleRequest processes API Gateway requests.
//
// X-Ray on Lambda: the Lambda runtime owns the segment and passes it in through the
// trace header, so a function must only open *subsegments*. This used to call
// xray.BeginSegment, which is for standalone processes and conflicts with the
// runtime-provided segment.
func handleRequest(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
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
	ctx, agentSeg := beginSubsegment(ctx, fmt.Sprintf("create-agent-%s", agentType))

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
	ctx, execSeg := beginSubsegment(ctx, "agent-execution")

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
		lambdaMeta := map[string]interface{}{
			"request_id":      lc.AwsRequestID,
			"function_name":   lambdacontext.FunctionName,
			"memory_limit_mb": lambdacontext.MemoryLimitInMB,
		}
		// The remaining time comes from the context deadline, not from
		// LambdaContext: LambdaContext has no Deadline field, and there is no
		// package-level lambdacontext.Deadline — the old expression referenced both.
		if deadline, hasDeadline := ctx.Deadline(); hasDeadline {
			lambdaMeta["remaining_time_ms"] = time.Until(deadline).Milliseconds()
		}
		response.Metadata["lambda"] = lambdaMeta
	}

	// Convert to response. Message.Content is `any` (it can carry structured
	// content), so it cannot be assigned to a string field directly.
	resp := Response{
		Role:     response.Role,
		Content:  response.ContentString(),
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

// beginSubsegment opens an X-Ray subsegment when a parent segment exists.
//
// Outside Lambda — `make test`, `sam local`, or any local run — there is no
// runtime-provided segment, and xray.BeginSubsegment then invokes the
// context-missing strategy, which by default logs an error per call (and can be
// configured to panic). Returning a nil *Segment is safe: Segment.Close is a no-op
// on nil.
func beginSubsegment(ctx context.Context, name string) (context.Context, *xray.Segment) {
	if xray.GetSegment(ctx) == nil {
		return ctx, nil
	}
	return xray.BeginSubsegment(ctx, name)
}

// containsAny reports whether s contains any of the given substrings.
func containsAny(s string, substrings []string) bool {
	for _, substr := range substrings {
		if strings.Contains(s, substr) {
			return true
		}
	}
	return false
}

// ============================================================
// Main
// ============================================================

func main() {
	// xray.Handler wraps an http.Handler, not a Lambda handler — passing
	// handleRequest to it did not compile. On Lambda, tracing is enabled by the
	// function's TracingConfig (see template.yaml: Tracing: Active); the code only
	// needs to open subsegments, which handleRequest does.
	lambda.Start(handleRequest)
}
