// Package benchmarks provides performance benchmarks for agent patterns
// These benchmarks measure framework overhead using simple mock agents (EchoAgent)
// to isolate pattern logic from LLM latency.
package benchmarks

import (
	"context"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// echoAgent is a simple agent that echoes input for benchmarking
type echoAgent struct {
	name string
}

func (e *echoAgent) Name() string {
	if e.name != "" {
		return e.name
	}
	return "echo"
}

func (e *echoAgent) Capabilities() []string {
	return []string{"echo"}
}

func (e *echoAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	// Simple echo - return input as output
	return agenkit.NewMessage("assistant", msg.Content), nil
}

func (e *echoAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    e.Name(),
		Capabilities: e.Capabilities(),
	}
}

// echoLLMClient implements LLMClient for Conversational and Planning patterns
type echoLLMClient struct{}

func (e *echoLLMClient) Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error) {
	if len(messages) > 0 {
		return agenkit.NewMessage("assistant", messages[len(messages)-1].Content), nil
	}
	return agenkit.NewMessage("assistant", "echo"), nil
}

// ==============================================================================
// Pattern Benchmarks
// ==============================================================================

// BenchmarkReflection measures Reflection pattern overhead (2 iterations)
func BenchmarkReflection(b *testing.B) {
	generator := &echoAgent{name: "generator"}
	critic := &echoAgent{name: "critic"}

	agent, err := patterns.NewReflectionAgent(patterns.ReflectionConfig{
		Generator:     generator,
		Critic:        critic,
		MaxIterations: 2,
	})
	if err != nil {
		b.Fatalf("failed to create reflection agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = agent.Process(ctx, msg)
	}
}

// BenchmarkReAct measures ReAct pattern overhead (3 steps)
func BenchmarkReAct(b *testing.B) {
	agent := &echoAgent{}
	tool := &mockTool{name: "test", description: "test tool", response: "result"}

	reactAgent, err := patterns.NewReActAgent(&patterns.ReActConfig{
		Agent:    agent,
		Tools:    []agenkit.Tool{tool},
		MaxSteps: 3,
	})
	if err != nil {
		b.Fatalf("failed to create react agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = reactAgent.Process(ctx, msg)
	}
}

// BenchmarkAgentsAsTools measures Agents-as-Tools pattern overhead
func BenchmarkAgentsAsTools(b *testing.B) {
	agent := &echoAgent{}

	tool, err := patterns.NewAgentTool(patterns.AgentToolConfig{
		Agent:       agent,
		Name:        "test_tool",
		Description: "Test tool",
	})
	if err != nil {
		b.Fatalf("failed to create agent tool: %v", err)
	}

	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = tool.Execute(ctx, map[string]interface{}{"input": "test"})
	}
}

// BenchmarkReasoningWithTools measures Reasoning with Tools pattern overhead
func BenchmarkReasoningWithTools(b *testing.B) {
	agent := &echoAgent{}
	tool := &mockTool{name: "test", description: "test tool", response: "result"}

	reasoningAgent := patterns.NewReasoningWithToolsAgent(
		agent,
		[]agenkit.Tool{tool},
		&patterns.ReasoningWithToolsConfig{
			MaxReasoningSteps: 5,
		},
	)

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = reasoningAgent.Process(ctx, msg)
	}
}

// BenchmarkConversational measures Conversational pattern overhead (10 history)
func BenchmarkConversational(b *testing.B) {
	llmClient := &echoLLMClient{}

	convAgent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:  llmClient,
		MaxHistory: 10,
	})
	if err != nil {
		b.Fatalf("failed to create conversational agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = convAgent.Process(ctx, msg)
		// Clear history after each iteration to prevent accumulation
		convAgent.ClearHistory(false)
	}
}

// BenchmarkTask measures Task pattern overhead (one-shot)
func BenchmarkTask(b *testing.B) {
	agent := &echoAgent{}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		task := patterns.NewTask(agent, &patterns.TaskConfig{
			Retries: 0,
		})
		_, _ = task.Execute(ctx, msg)
	}
}

// BenchmarkMultiagent measures Multiagent pattern overhead (2 sequential)
func BenchmarkMultiagent(b *testing.B) {
	agent1 := &echoAgent{name: "agent1"}
	agent2 := &echoAgent{name: "agent2"}

	multiAgent := patterns.NewMultiAgentOrchestrator(patterns.StrategySequential)
	multiAgent.RegisterAgent("agent1", agent1)
	multiAgent.RegisterAgent("agent2", agent2)

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = multiAgent.Process(ctx, msg)
	}
}

// BenchmarkPlanning measures Planning pattern overhead (plan + execute)
func BenchmarkPlanning(b *testing.B) {
	llmClient := &echoLLMClient{}
	executor := &patterns.DefaultStepExecutor{}

	planningAgent := patterns.NewPlanningAgent(llmClient, executor, &patterns.PlanningAgentConfig{
		MaxSteps: 5,
	})

	msg := agenkit.NewMessage("user", "create a plan")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = planningAgent.Process(ctx, msg)
	}
}

// BenchmarkAutonomous measures Autonomous pattern overhead (5 iterations)
func BenchmarkAutonomous(b *testing.B) {
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		// Create fresh agent for each iteration
		agent := patterns.NewAutonomousAgent("complete objective", 5)
		agent.AddGoal("goal1", 1)
		agent.AddGoal("goal2", 1)
		_, _ = agent.Run(ctx)
	}
}

// BenchmarkMemoryWorking measures Memory: Working pattern overhead
func BenchmarkMemoryWorking(b *testing.B) {
	b.Run("Store", func(b *testing.B) {
		memory, err := patterns.NewWorkingMemory(10)
		if err != nil {
			b.Fatalf("failed to create working memory: %v", err)
		}

		ctx := context.Background()

		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			entry := patterns.CreateMemoryEntry("test content", map[string]interface{}{"priority": 0.5}, 0.5, "")
			_ = memory.Store(ctx, entry)
		}
	})

	b.Run("Retrieve", func(b *testing.B) {
		memory, err := patterns.NewWorkingMemory(10)
		if err != nil {
			b.Fatalf("failed to create working memory: %v", err)
		}

		ctx := context.Background()

		// Pre-populate
		for i := 0; i < 5; i++ {
			entry := patterns.CreateMemoryEntry("test content", map[string]interface{}{"priority": 0.5}, 0.5, "")
			_ = memory.Store(ctx, entry)
		}

		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			_, _ = memory.Retrieve(ctx, "test", 5)
		}
	})
}

// BenchmarkMemoryShortTerm measures Memory: Short-Term pattern overhead
func BenchmarkMemoryShortTerm(b *testing.B) {
	b.Run("Store", func(b *testing.B) {
		memory, err := patterns.NewShortTermMemory(100, 3600)
		if err != nil {
			b.Fatalf("failed to create short-term memory: %v", err)
		}

		ctx := context.Background()

		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			entry := patterns.CreateMemoryEntry("test content", map[string]interface{}{"priority": 0.5}, 0.5, "")
			_ = memory.Store(ctx, entry)
		}
	})

	b.Run("Retrieve", func(b *testing.B) {
		memory, err := patterns.NewShortTermMemory(100, 3600)
		if err != nil {
			b.Fatalf("failed to create short-term memory: %v", err)
		}

		ctx := context.Background()

		// Pre-populate
		for i := 0; i < 10; i++ {
			entry := patterns.CreateMemoryEntry("test content", map[string]interface{}{"priority": 0.5}, 0.5, "")
			_ = memory.Store(ctx, entry)
		}

		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			_, _ = memory.Retrieve(ctx, "test", 5)
		}
	})
}

// BenchmarkMemoryHierarchy measures Memory: Hierarchy pattern overhead
func BenchmarkMemoryHierarchy(b *testing.B) {
	b.Run("Store", func(b *testing.B) {
		working, _ := patterns.NewWorkingMemory(10)
		shortTerm, _ := patterns.NewShortTermMemory(100, 3600)
		longTerm, _ := patterns.NewLongTermMemory(nil, nil, 0.5)

		memory := patterns.NewMemoryHierarchy(working, shortTerm, longTerm)

		ctx := context.Background()

		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			_, _ = memory.Store(ctx, "test content", map[string]interface{}{"priority": 0.7}, 0.7, "")
		}
	})

	b.Run("Retrieve", func(b *testing.B) {
		working, _ := patterns.NewWorkingMemory(10)
		shortTerm, _ := patterns.NewShortTermMemory(100, 3600)
		longTerm, _ := patterns.NewLongTermMemory(nil, nil, 0.5)

		memory := patterns.NewMemoryHierarchy(working, shortTerm, longTerm)

		ctx := context.Background()

		// Pre-populate
		for i := 0; i < 10; i++ {
			_, _ = memory.Store(ctx, "test content", map[string]interface{}{"priority": 0.7}, 0.7, "")
		}

		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			_, _ = memory.Retrieve(ctx, "test", 5, nil)
		}
	})
}

// BenchmarkSequential measures Sequential pattern overhead (3 agents)
func BenchmarkSequential(b *testing.B) {
	agent1 := &echoAgent{name: "agent1"}
	agent2 := &echoAgent{name: "agent2"}
	agent3 := &echoAgent{name: "agent3"}

	sequential, err := patterns.NewSequentialAgent([]agenkit.Agent{agent1, agent2, agent3})
	if err != nil {
		b.Fatalf("failed to create sequential agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = sequential.Process(ctx, msg)
	}
}

// BenchmarkParallel measures Parallel pattern overhead (3 agents)
func BenchmarkParallel(b *testing.B) {
	agent1 := &echoAgent{name: "agent1"}
	agent2 := &echoAgent{name: "agent2"}
	agent3 := &echoAgent{name: "agent3"}

	// Simple aggregator: return first result
	aggregator := func(results []*agenkit.Message) *agenkit.Message {
		if len(results) > 0 {
			return results[0]
		}
		return agenkit.NewMessage("assistant", "")
	}

	parallel, err := patterns.NewParallelAgent([]agenkit.Agent{agent1, agent2, agent3}, aggregator)
	if err != nil {
		b.Fatalf("failed to create parallel agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = parallel.Process(ctx, msg)
	}
}

// BenchmarkRouter measures Router pattern overhead (2 routes)
func BenchmarkRouter(b *testing.B) {
	classifier := &echoClassifier{}
	agent1 := &echoAgent{name: "agent1"}
	agent2 := &echoAgent{name: "agent2"}

	router, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: classifier,
		Agents: map[string]agenkit.Agent{
			"route1": agent1,
			"route2": agent2,
		},
	})
	if err != nil {
		b.Fatalf("failed to create router agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = router.Process(ctx, msg)
	}
}

// BenchmarkFallback measures Fallback pattern overhead (2 agents)
func BenchmarkFallback(b *testing.B) {
	agent1 := &echoAgent{name: "agent1"}
	agent2 := &echoAgent{name: "agent2"}

	fallback, err := patterns.NewFallbackAgent([]agenkit.Agent{agent1, agent2})
	if err != nil {
		b.Fatalf("failed to create fallback agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = fallback.Process(ctx, msg)
	}
}

// BenchmarkCollaborative measures Collaborative pattern overhead (2 rounds)
func BenchmarkCollaborative(b *testing.B) {
	agent1 := &echoAgent{name: "agent1"}
	agent2 := &echoAgent{name: "agent2"}

	// Simple merge function
	mergeFunc := func(messages []*agenkit.Message) *agenkit.Message {
		if len(messages) > 0 {
			return messages[0]
		}
		return agenkit.NewMessage("assistant", "")
	}

	collaborative, err := patterns.NewCollaborativeAgent(&patterns.CollaborativeConfig{
		Agents:    []agenkit.Agent{agent1, agent2},
		MaxRounds: 2,
		MergeFunc: mergeFunc,
	})
	if err != nil {
		b.Fatalf("failed to create collaborative agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = collaborative.Process(ctx, msg)
	}
}

// BenchmarkHumanInLoop measures Human-in-Loop pattern overhead (auto-approve)
func BenchmarkHumanInLoop(b *testing.B) {
	agent := &echoAgent{}

	// Auto-approve callback for benchmarking
	approvalFunc := func(ctx context.Context, req *patterns.ApprovalRequest) (*patterns.ApprovalResponse, error) {
		return &patterns.ApprovalResponse{Approved: true, Feedback: "approved"}, nil
	}

	hil, err := patterns.NewHumanInLoopAgent(&patterns.HumanInLoopConfig{
		Agent:             agent,
		ApprovalFunc:      approvalFunc,
		ApprovalThreshold: 0.8,
	})
	if err != nil {
		b.Fatalf("failed to create human-in-loop agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = hil.Process(ctx, msg)
	}
}

// BenchmarkSupervisor measures Supervisor pattern overhead (2 specialists)
func BenchmarkSupervisor(b *testing.B) {
	echo := &echoAgent{}
	planner := patterns.NewSimplePlanner(echo)

	specialists := map[string]agenkit.Agent{
		"specialist1": &echoAgent{name: "specialist1"},
		"specialist2": &echoAgent{name: "specialist2"},
	}

	supervisor, err := patterns.NewSupervisorAgent(planner, specialists)
	if err != nil {
		b.Fatalf("failed to create supervisor agent: %v", err)
	}

	msg := agenkit.NewMessage("user", "test")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = supervisor.Process(ctx, msg)
	}
}

// ==============================================================================
// Helper Types
// ==============================================================================

// mockTool is a simple tool for benchmarking
type mockTool struct {
	name        string
	description string
	response    string
}

func (t *mockTool) Name() string {
	return t.name
}

func (t *mockTool) Description() string {
	return t.description
}

func (t *mockTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	return &agenkit.ToolResult{
		Data:    t.response,
		Success: true,
	}, nil
}

// echoClassifier is a simple classifier for router benchmarks
type echoClassifier struct{}

func (c *echoClassifier) Name() string {
	return "echo-classifier"
}

func (c *echoClassifier) Capabilities() []string {
	return []string{"classify"}
}

func (c *echoClassifier) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "route1"), nil
}

func (c *echoClassifier) Classify(ctx context.Context, msg *agenkit.Message) (string, error) {
	return "route1", nil
}

func (c *echoClassifier) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}
