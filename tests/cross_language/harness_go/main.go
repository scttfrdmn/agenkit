package main

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

const (
	protocolVersion = "1.0"
	version         = "0.44.0"
)

// Protocol types
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
	Error           *ErrorDetail           `json:"error,omitempty"`
}

type ErrorDetail struct {
	Type       string                 `json:"type"`
	Message    string                 `json:"message"`
	Details    map[string]interface{} `json:"details,omitempty"`
	StackTrace string                 `json:"stack_trace,omitempty"`
}

// MockAgent provides deterministic responses for testing
type MockAgent struct {
	name      string
	responses []string
	callCount int
}

func NewMockAgent(name string, responses []string) *MockAgent {
	if len(responses) == 0 {
		responses = []string{
			"1. First, let's analyze the problem.\n2. Then, we'll solve it step by step.\n3. Finally, we arrive at the answer: 42.",
		}
	}
	return &MockAgent{
		name:      name,
		responses: responses,
		callCount: 0,
	}
}

func (m *MockAgent) Name() string {
	return m.name
}

func (m *MockAgent) Capabilities() []string {
	return []string{"mock", "test"}
}

func (m *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockAgent) Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error) {
	// For conversational agent - check last message
	if len(messages) == 0 {
		return agenkit.NewMessage("assistant", "No messages"), nil
	}
	lastMessage := messages[len(messages)-1]
	contentLower := strings.ToLower(lastMessage.ContentString())

	// Check if asking about name - extract from history
	if strings.Contains(contentLower, "name") {
		for i := 0; i < len(messages)-1; i++ {
			msg := messages[i]
			re := regexp.MustCompile(`(?i)(?:name is|I'm|I am)\s+(\w+)`)
			if match := re.FindStringSubmatch(msg.ContentString()); match != nil {
				name := match[1]
				return agenkit.NewMessage("assistant", fmt.Sprintf("Your name is %s", name)), nil
			}
		}
	}

	// Default response
	responseText := m.responses[m.callCount%len(m.responses)]
	m.callCount++
	return agenkit.NewMessage("assistant", responseText), nil
}

func (m *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	contentLower := strings.ToLower(message.ContentString())

	// ReAct pattern - calculation (15 * 24 = 360)
	isCalcQuery := (strings.Contains(message.ContentString(), "15 * 24") || strings.Contains(message.ContentString(), "What is 15")) &&
		!strings.Contains(contentLower, "color")
	isCalcFollowup := strings.Contains(message.ContentString(), "What's your next thought/action?") &&
		strings.Contains(message.ContentString(), "360")

	if isCalcQuery || isCalcFollowup {
		hasActualObservation := strings.Contains(message.ContentString(), "Observation: 360") ||
			strings.Contains(message.ContentString(), "What's your next thought/action?")

		if hasActualObservation {
			return agenkit.NewMessage("assistant",
				"Thought: I now have the calculation result\nAction: Final Answer\nAction Input: The result of 15 * 24 is 360."), nil
		}
		return agenkit.NewMessage("assistant",
			`Thought: I need to use the calculator tool to compute 15 * 24
Action: calculator
Action Input: {"a": 15, "b": 24}`), nil
	}

	// ReAct pattern - multi-step with tools (weather + convert)
	isWeatherQuery := strings.Contains(contentLower, "weather") &&
		strings.Contains(contentLower, "paris") &&
		(strings.Contains(contentLower, "fahrenheit") || strings.Contains(contentLower, "convert"))
	isWeatherFollowup := strings.Contains(message.ContentString(), "What's your next thought/action?") &&
		(strings.Contains(contentLower, "paris") || strings.Contains(contentLower, "temperature") ||
			strings.Contains(contentLower, "20°c") || strings.Contains(contentLower, "68°f"))

	if isWeatherQuery || isWeatherFollowup {
		if !strings.Contains(message.ContentString(), "What's your next thought/action?") {
			return agenkit.NewMessage("assistant",
				`Thought: First I need to search for the current weather in Paris
Action: search
Action Input: {"query": "weather Paris"}`), nil
		} else if strings.Contains(message.ContentString(), "Temperature in Paris: 20°C") || strings.Contains(contentLower, "20°c") {
			return agenkit.NewMessage("assistant",
				`Thought: Now I need to convert the temperature from Celsius to Fahrenheit
Action: unit_converter
Action Input: {"from_unit": "celsius", "to_unit": "fahrenheit", "value": 20}`), nil
		}
		return agenkit.NewMessage("assistant",
			"Thought: I have the weather data and the conversion\nAction: Final Answer\nAction Input: The weather in Paris is 20°C, which converts to 68°F."), nil
	}

	// ReAct pattern - simple factual questions (no tools needed)
	if strings.Contains(contentLower, "color") && strings.Contains(contentLower, "sky") {
		return agenkit.NewMessage("assistant",
			"Thought: This is a simple factual question I can answer directly\nAction: Final Answer\nAction Input: The sky is blue during the day due to Rayleigh scattering of sunlight."), nil
	}

	// Task pattern - impossible task (should fail)
	if strings.Contains(contentLower, "impossible") {
		return nil, fmt.Errorf("Task cannot be completed")
	}

	// Task pattern - email extraction
	if strings.Contains(contentLower, "extract") && strings.Contains(contentLower, "email") {
		re := regexp.MustCompile(`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`)
		emails := re.FindAllString(message.ContentString(), -1)
		if len(emails) > 0 {
			return agenkit.NewMessage("assistant",
				fmt.Sprintf("Extracted email addresses: %s", strings.Join(emails, ", "))), nil
		}
	}

	// Reflection pattern - poetry about technology
	if strings.Contains(contentLower, "poem") && strings.Contains(contentLower, "technology") {
		return agenkit.NewMessage("assistant",
			"Here's a poem about technology:\n\nCircuits hum with electric dreams,\nConnecting worlds through digital streams.\nInnovation's spark lights up the night,\nTechnology guides us to new height."), nil
	}

	// Reflection pattern - critique prompt
	if strings.Contains(contentLower, "critique") || strings.Contains(contentLower, "improve") {
		return agenkit.NewMessage("assistant",
			"Quality Score: 7/10\n\nFeedback: The poem captures technology well but could be more specific. Consider adding more vivid imagery.\n\nSuggestion: Add references to specific technologies or their impact on society."), nil
	}

	// Default response for generic ReAct queries
	isGenericReactQuery := (strings.Contains(message.ContentString(), "You are a helpful assistant that uses tools") ||
		strings.Contains(message.ContentString(), "Available tools:")) &&
		!strings.Contains(message.ContentString(), "15") &&
		!strings.Contains(contentLower, "weather") &&
		!strings.Contains(contentLower, "sky")
	isGenericReactFollowup := strings.Contains(message.ContentString(), "What's your next thought/action?") &&
		strings.Contains(contentLower, "mock result")

	if isGenericReactQuery || isGenericReactFollowup {
		obsCount := strings.Count(message.ContentString(), "What's your next thought/action?")
		if obsCount == 0 {
			return agenkit.NewMessage("assistant",
				"Thought: Let me try using a tool\nAction: tool1\nAction Input: {}"), nil
		}
		return agenkit.NewMessage("assistant",
			"Thought: I've reached my limit\nAction: Final Answer\nAction Input: Task completed within max iterations."), nil
	}

	// Regular default response
	responseText := m.responses[m.callCount%len(m.responses)]
	m.callCount++
	return agenkit.NewMessage("assistant", responseText), nil
}

// FailingMockAgent always fails for testing error scenarios
type FailingMockAgent struct {
	name string
}

func NewFailingMockAgent(name string) *FailingMockAgent {
	return &FailingMockAgent{name: name}
}

func (f *FailingMockAgent) Name() string {
	return f.name
}

func (f *FailingMockAgent) Capabilities() []string {
	return []string{"mock", "test", "failing"}
}

func (f *FailingMockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    f.Name(),
		Capabilities: f.Capabilities(),
	}
}

func (f *FailingMockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return nil, fmt.Errorf("%s always fails", f.name)
}

func executeTest(payload map[string]interface{}) map[string]interface{} {
	patternName, _ := payload["pattern"].(string)
	inputData, _ := payload["input"].(map[string]interface{})

	// Parse input message
	var message *agenkit.Message
	if messagesData, ok := inputData["messages"].([]interface{}); ok && len(messagesData) > 0 {
		// Multiple messages for conversational pattern
		lastMsg := messagesData[len(messagesData)-1].(map[string]interface{})
		message = parseMessage(lastMsg)
	} else if messageData, ok := inputData["message"].(map[string]interface{}); ok {
		message = parseMessage(messageData)
	} else {
		message = agenkit.NewMessage("user", "")
	}

	config, _ := inputData["config"].(map[string]interface{})

	ctx := context.Background()
	startTime := time.Now()

	// Create mock agents
	mockAgent := NewMockAgent("mock_agent", []string{
		"1. First approach: analyze directly.\n2. Calculate step by step.\n3. Result: 42",
		"- Alternative method: work backwards.\n- Apply the formula.\n- Answer: 42",
		"Step 1: Identify key variables.\nStep 2: Solve systematically.\nStep 3: Verify result is 42",
	})

	// Execute pattern based on type
	var outputMessage *agenkit.Message
	var err error

	switch patternName {
	case "Reflection":
		outputMessage, err = executeReflection(ctx, mockAgent, message, config)
	case "Sequential":
		outputMessage, err = executeSequential(ctx, mockAgent, message, config)
	case "Parallel":
		outputMessage, err = executeParallel(ctx, mockAgent, message, config)
	case "ReAct":
		outputMessage, err = executeReAct(ctx, mockAgent, message, config)
	case "Conversational":
		outputMessage, err = executeConversational(ctx, mockAgent, message, config, inputData)
	case "Task":
		outputMessage, err = executeTask(ctx, mockAgent, message, config)
	default:
		return map[string]interface{}{
			"status": "not_implemented",
			"result": nil,
			"error": map[string]interface{}{
				"type":    "PatternNotFound",
				"message": fmt.Sprintf("Pattern '%s' not implemented in Go harness", patternName),
			},
		}
	}

	if err != nil {
		return map[string]interface{}{
			"status": "error",
			"result": nil,
			"error": map[string]interface{}{
				"type":    "ExecutionError",
				"message": err.Error(),
				"details": map[string]interface{}{},
			},
		}
	}

	durationMs := time.Since(startTime).Milliseconds()

	// Extract behavior metadata
	turns := 1
	toolCalls := []string{}
	subAgents := []string{}

	if outputMessage.Metadata != nil {
		// ReAct pattern
		if reactSteps, ok := outputMessage.Metadata["react_steps"].([]interface{}); ok {
			toolCallsMap := make(map[string]bool)
			for _, step := range reactSteps {
				stepMap := step.(map[string]interface{})
				action := stepMap["action"].(string)
				if strings.ToLower(action) != "final answer" {
					toolCallsMap[action] = true
				}
			}
			for tool := range toolCallsMap {
				toolCalls = append(toolCalls, tool)
			}
			turns = len(reactSteps)*2 + 1
		}

		// Sub-agents metadata
		if subAgentsList, ok := outputMessage.Metadata["sub_agents"].([]string); ok {
			subAgents = subAgentsList
		}

		// Sequential pattern
		if pipelineStages, ok := outputMessage.Metadata["pipeline_stages"].([]interface{}); ok {
			for _, stage := range pipelineStages {
				stageMap := stage.(map[string]interface{})
				subAgents = append(subAgents, stageMap["agent"].(string))
			}
		}

		// Parallel pattern
		if parallelAgents, ok := outputMessage.Metadata["parallel_agents"].([]interface{}); ok {
			for _, agent := range parallelAgents {
				if agentName, ok := agent.(string); ok {
					subAgents = append(subAgents, agentName)
				}
			}
		}

		// Reflection pattern
		if iterations, ok := outputMessage.Metadata["reflection_iterations"].(float64); ok {
			turns = int(iterations) * 2
		} else if iterations, ok := outputMessage.Metadata["reflection_iterations"].(int); ok {
			turns = iterations * 2
		}
	}

	return map[string]interface{}{
		"status": "success",
		"result": map[string]interface{}{
			"output": map[string]interface{}{
				"message": map[string]interface{}{
					"role":     outputMessage.Role,
					"content":  outputMessage.Content,
					"metadata": outputMessage.Metadata,
				},
				"behavior": map[string]interface{}{
					"turns":      turns,
					"tool_calls": toolCalls,
					"sub_agents": subAgents,
				},
			},
			"execution_info": map[string]interface{}{
				"duration_ms": durationMs,
				"llm_calls":   0,
				"tokens_used": 0,
			},
		},
		"error": nil,
	}
}

func parseMessage(msgData map[string]interface{}) *agenkit.Message {
	role, _ := msgData["role"].(string)
	if role == "" {
		role = "user"
	}
	content, _ := msgData["content"].(string)

	msg := agenkit.NewMessage(role, content)

	if metadata, ok := msgData["metadata"].(map[string]interface{}); ok {
		msg.Metadata = metadata
	}

	return msg
}

func executeReflection(ctx context.Context, mockAgent *MockAgent, message *agenkit.Message, config map[string]interface{}) (*agenkit.Message, error) {
	maxIterations := 3
	if maxIter, ok := config["max_iterations"].(float64); ok {
		maxIterations = int(maxIter)
	}

	reflectionConfig := patterns.ReflectionConfig{
		Generator:            mockAgent,
		Critic:               mockAgent,
		MaxIterations:        maxIterations,
		QualityThreshold:     0.9,
		ImprovementThreshold: 0.1,
		CritiqueFormat:       patterns.CritiqueFreeForm,
		Verbose:              false,
	}

	agent, err := patterns.NewReflectionAgent(reflectionConfig)
	if err != nil {
		return nil, err
	}

	return agent.Process(ctx, message)
}

func executeSequential(ctx context.Context, mockAgent *MockAgent, message *agenkit.Message, config map[string]interface{}) (*agenkit.Message, error) {
	var agents []agenkit.Agent

	if agentConfigs, ok := config["agents"].([]interface{}); ok && len(agentConfigs) > 0 {
		for _, agentConfig := range agentConfigs {
			agentMap := agentConfig.(map[string]interface{})
			agentName, _ := agentMap["name"].(string)
			agents = append(agents, NewMockAgent(agentName, []string{message.ContentString()}))
		}
	} else {
		agents = []agenkit.Agent{mockAgent, mockAgent}
	}

	agent, err := patterns.NewSequentialAgent(agents)
	if err != nil {
		return nil, err
	}
	return agent.Process(ctx, message)
}

func executeParallel(ctx context.Context, mockAgent *MockAgent, message *agenkit.Message, config map[string]interface{}) (*agenkit.Message, error) {
	var agents []agenkit.Agent

	if agentConfigs, ok := config["agents"].([]interface{}); ok && len(agentConfigs) > 0 {
		for _, agentConfig := range agentConfigs {
			agentMap := agentConfig.(map[string]interface{})
			agentName, _ := agentMap["name"].(string)
			agents = append(agents, NewMockAgent(agentName, []string{message.ContentString()}))
		}
	} else {
		agents = []agenkit.Agent{mockAgent, mockAgent}
	}

	aggregator := func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) == 0 {
			return agenkit.NewMessage("assistant", "No results")
		}
		var contents []string
		for _, msg := range messages {
			contents = append(contents, msg.ContentString())
		}
		result := agenkit.NewMessage("assistant", strings.Join(contents, " "))
		result.Metadata["aggregated"] = true
		return result
	}

	agent, err := patterns.NewParallelAgent(agents, aggregator)
	if err != nil {
		return nil, err
	}
	return agent.Process(ctx, message)
}

func executeReAct(ctx context.Context, mockAgent *MockAgent, message *agenkit.Message, config map[string]interface{}) (*agenkit.Message, error) {
	var tools []agenkit.Tool

	if toolsConfig, ok := config["tools"].([]interface{}); ok {
		for _, toolSpec := range toolsConfig {
			toolMap := toolSpec.(map[string]interface{})
			toolName, _ := toolMap["name"].(string)
			toolDesc, _ := toolMap["description"].(string)

			switch toolName {
			case "calculator":
				tools = append(tools, &MockCalculator{})
			case "search":
				tools = append(tools, &MockSearch{})
			case "unit_converter":
				tools = append(tools, &MockUnitConverter{})
			default:
				tools = append(tools, &GenericMockTool{name: toolName, description: toolDesc})
			}
		}
	}

	maxSteps := 5
	if maxIter, ok := config["max_iterations"].(float64); ok {
		maxSteps = int(maxIter)
	}

	reactConfig := &patterns.ReActConfig{
		Agent:    mockAgent,
		Tools:    tools,
		MaxSteps: maxSteps,
		Verbose:  false,
	}

	agent, err := patterns.NewReActAgent(reactConfig)
	if err != nil {
		return nil, err
	}

	return agent.Process(ctx, message)
}

func executeConversational(ctx context.Context, mockAgent *MockAgent, message *agenkit.Message, config map[string]interface{}, inputData map[string]interface{}) (*agenkit.Message, error) {
	maxHistory := 10
	if maxHist, ok := config["max_history"].(float64); ok {
		maxHistory = int(maxHist)
	}

	systemPrompt := ""
	if sysPrmt, ok := config["system_prompt"].(string); ok {
		systemPrompt = sysPrmt
	}

	conversationalConfig := &patterns.ConversationalAgentConfig{
		LLMClient:    mockAgent,
		MaxHistory:   maxHistory,
		SystemPrompt: systemPrompt,
	}

	agent, err := patterns.NewConversationalAgent(conversationalConfig)
	if err != nil {
		return nil, err
	}

	// Pre-populate history
	if messagesData, ok := inputData["messages"].([]interface{}); ok && len(messagesData) > 1 {
		// Get access to agent's internal history via reflection-style approach
		// Since we can't access private fields, we need to manually add to history
		// by creating a mock conversational agent that exposes history management
		for i := 0; i < len(messagesData)-1; i++ {
			msgData := messagesData[i].(map[string]interface{})
			histMsg := parseMessage(msgData)
			// ConversationalAgent doesn't expose AddToHistory, so we need to use a different approach
			// For now, we'll just process with the last message and trust the history is in context
			_ = histMsg
		}
	}

	return agent.Process(ctx, message)
}

func executeTask(ctx context.Context, mockAgent *MockAgent, message *agenkit.Message, config map[string]interface{}) (*agenkit.Message, error) {
	// Task pattern wraps agent execution
	return mockAgent.Process(ctx, message)
}

// Mock tools for ReAct pattern
type MockCalculator struct{}

func (m *MockCalculator) Name() string {
	return "calculator"
}

func (m *MockCalculator) Description() string {
	return "Performs calculations"
}

func (m *MockCalculator) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	return agenkit.NewToolResult("360"), nil
}

type MockSearch struct{}

func (m *MockSearch) Name() string {
	return "search"
}

func (m *MockSearch) Description() string {
	return "Searches the web"
}

func (m *MockSearch) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	return agenkit.NewToolResult("Temperature in Paris: 20°C"), nil
}

type MockUnitConverter struct{}

func (m *MockUnitConverter) Name() string {
	return "unit_converter"
}

func (m *MockUnitConverter) Description() string {
	return "Converts units"
}

func (m *MockUnitConverter) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	return agenkit.NewToolResult("68°F"), nil
}

type GenericMockTool struct {
	name        string
	description string
}

func (g *GenericMockTool) Name() string {
	return g.name
}

func (g *GenericMockTool) Description() string {
	return g.description
}

func (g *GenericMockTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	return agenkit.NewToolResult("mock result"), nil
}

func getInfo() map[string]interface{} {
	return map[string]interface{}{
		"status": "success",
		"result": map[string]interface{}{
			"language": "go",
			"version":  version,
			"patterns_supported": []string{
				"Reflection",
				"Sequential",
				"Parallel",
				"ReAct",
				"Conversational",
				"Task",
			},
			"capabilities": map[string]interface{}{
				"streaming":     true,
				"async":         true,
				"llm_providers": []string{"openai", "anthropic"},
			},
		},
		"error": nil,
	}
}

func healthCheck() map[string]interface{} {
	return map[string]interface{}{
		"status": "success",
		"result": map[string]interface{}{
			"healthy":        true,
			"uptime_seconds": 0.0,
		},
		"error": nil,
	}
}

func handleRequest(request Request) Response {
	// Validate protocol version
	if request.ProtocolVersion != protocolVersion {
		return Response{
			ProtocolVersion: protocolVersion,
			RequestID:       request.RequestID,
			Status:          "error",
			Error: &ErrorDetail{
				Type:    "ProtocolError",
				Message: fmt.Sprintf("Protocol version mismatch: expected %s, got %s", protocolVersion, request.ProtocolVersion),
			},
		}
	}

	var result map[string]interface{}

	switch request.Command {
	case "execute_test":
		result = executeTest(request.Payload)
	case "get_info":
		result = getInfo()
	case "health_check":
		result = healthCheck()
	default:
		result = map[string]interface{}{
			"status": "error",
			"result": nil,
			"error": map[string]interface{}{
				"type":    "CommandNotFound",
				"message": fmt.Sprintf("Unknown command: %s", request.Command),
			},
		}
	}

	status, _ := result["status"].(string)
	delete(result, "status")

	var errorDetail *ErrorDetail
	if errData, ok := result["error"].(map[string]interface{}); ok && errData != nil {
		errorDetail = &ErrorDetail{
			Type:    errData["type"].(string),
			Message: errData["message"].(string),
		}
		if details, ok := errData["details"].(map[string]interface{}); ok {
			errorDetail.Details = details
		}
		delete(result, "error")
	}

	var resultData map[string]interface{}
	if res, ok := result["result"].(map[string]interface{}); ok {
		resultData = res
	}

	return Response{
		ProtocolVersion: protocolVersion,
		RequestID:       request.RequestID,
		Status:          status,
		Result:          resultData,
		Error:           errorDetail,
	}
}

func main() {
	scanner := bufio.NewScanner(os.Stdin)
	var inputLines []string

	// Read all input lines
	for scanner.Scan() {
		line := scanner.Text()
		if line != "" {
			inputLines = append(inputLines, line)
		}
	}

	if err := scanner.Err(); err != nil {
		errorResponse := Response{
			ProtocolVersion: protocolVersion,
			Status:          "error",
			Error: &ErrorDetail{
				Type:    "ProtocolError",
				Message: fmt.Sprintf("Error reading stdin: %v", err),
			},
		}
		output, _ := json.Marshal(errorResponse)
		fmt.Println(string(output))
		os.Exit(2)
	}

	// Join all lines and parse as single JSON
	requestJSON := strings.Join(inputLines, "\n")

	var request Request
	if err := json.Unmarshal([]byte(requestJSON), &request); err != nil {
		errorResponse := Response{
			ProtocolVersion: protocolVersion,
			Status:          "error",
			Error: &ErrorDetail{
				Type:    "ProtocolError",
				Message: fmt.Sprintf("Invalid JSON: %v", err),
			},
		}
		output, _ := json.Marshal(errorResponse)
		fmt.Println(string(output))
		os.Exit(2)
	}

	response := handleRequest(request)

	output, err := json.Marshal(response)
	if err != nil {
		errorResponse := Response{
			ProtocolVersion: protocolVersion,
			RequestID:       request.RequestID,
			Status:          "error",
			Error: &ErrorDetail{
				Type:    "InternalError",
				Message: fmt.Sprintf("Failed to marshal response: %v", err),
			},
		}
		output, _ = json.Marshal(errorResponse)
		fmt.Println(string(output))
		os.Exit(4)
	}

	fmt.Println(string(output))

	if response.Status == "success" {
		os.Exit(0)
	}
	os.Exit(1)
}
