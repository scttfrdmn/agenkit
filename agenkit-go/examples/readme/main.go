// Command readme is the compiled source of truth for the snippets in
// agenkit-go/README.md.
//
// Every code block in that README is copied from a function here, so a snippet
// cannot reference an API that does not exist: `go build ./...` and `go vet ./...`
// fail first. Before #839 the README documented eleven constructors and nine of
// them were wrong — `NewRetryMiddleware` (really `NewRetryDecorator`),
// `ConversationalConfig` (really `ConversationalAgentConfig`), config structs for
// the reasoning techniques (which take functional options), and the packages
// `transport/http` and `transport/grpc`, which never existed. All of it was
// plausible, which is why review never caught it.
//
// When you change a snippet in the README, change it here and keep the two in
// sync. Running this file is not the point; compiling it is.
package main

import (
	"context"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/grpc"
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/http"
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/remote"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/middleware"
	"github.com/scttfrdmn/agenkit/agenkit-go/observability"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
	"github.com/scttfrdmn/agenkit/agenkit-go/techniques/reasoning"
)

// --- Basic Agent ---------------------------------------------------------

// EchoAgent is the minimal Agent implementation: the four methods the interface
// requires and nothing else.
type EchoAgent struct{}

func (a *EchoAgent) Name() string {
	return "echo-agent"
}

func (a *EchoAgent) Capabilities() []string {
	return []string{"echo", "simple"}
}

func (a *EchoAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Content is `any`, so read it through ContentString() rather than using the
	// field directly — string operations on Content do not compile.
	return agenkit.NewMessage("assistant", fmt.Sprintf("Echo: %s", message.ContentString())), nil
}

func (a *EchoAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func basicAgent(ctx context.Context) error {
	agent := &EchoAgent{}

	message := agenkit.NewMessage("user", "Hello!")
	response, err := agent.Process(ctx, message)
	if err != nil {
		return err
	}

	fmt.Println(response.ContentString()) // "Echo: Hello!"
	return nil
}

// --- Resilience middleware ----------------------------------------------

// resilience wraps an agent in retry, circuit-breaker and timeout decorators.
//
// The decorators take their config by value and return an agent, so they compose
// by reassignment.
func resilience(ctx context.Context, message *agenkit.Message) error {
	var agent agenkit.Agent = &EchoAgent{}

	agent = middleware.NewRetryDecorator(agent, middleware.RetryConfig{
		MaxRetries:        3,
		InitialRetryDelay: 100 * time.Millisecond,
		RetryMultiplier:   2.0,
	})

	agent = middleware.NewCircuitBreakerDecorator(agent, middleware.CircuitBreakerConfig{
		FailureThreshold: 5,
		RecoveryTimeout:  60 * time.Second,
	})

	agent = middleware.NewTimeoutDecorator(agent, middleware.TimeoutConfig{
		Timeout: 30 * time.Second,
	})

	response, err := agent.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(response.ContentString())
	return nil
}

// --- Sequential pipeline -------------------------------------------------

func sequentialPipeline(ctx context.Context, message *agenkit.Message) error {
	// Data flows: Agent1 -> Agent2 -> Agent3
	pipeline, err := patterns.NewSequentialAgent([]agenkit.Agent{
		&EchoAgent{},
		&EchoAgent{},
	})
	if err != nil {
		return err
	}

	result, err := pipeline.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

// --- Parallel execution --------------------------------------------------

func parallelExecution(ctx context.Context, message *agenkit.Message) error {
	// Execute multiple agents concurrently using goroutines.
	//
	// The aggregator is mandatory — passing nil returns an error rather than
	// selecting a default. Pick one from patterns.DefaultAggregators (First,
	// Concatenate, MajorityVote) or supply your own AggregatorFunc.
	parallel, err := patterns.NewParallelAgent([]agenkit.Agent{
		&EchoAgent{},
		&EchoAgent{},
	}, patterns.DefaultAggregators.Concatenate)
	if err != nil {
		return err
	}

	result, err := parallel.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

// --- Conversational agent ------------------------------------------------

func conversational(ctx context.Context, apiKey string) error {
	// LLMClient accepts anything implementing Complete — every shipped adapter
	// does, structurally, with no wrapper.
	agent, err := patterns.NewConversationalAgent(&patterns.ConversationalAgentConfig{
		LLMClient:    llm.NewAnthropicLLM(apiKey, "claude-sonnet-4-5"),
		SystemPrompt: "You are a helpful assistant.",
		MaxHistory:   10,
	})
	if err != nil {
		return err
	}

	if _, err := agent.Process(ctx, agenkit.NewMessage("user", "What's the capital of France?")); err != nil {
		return err
	}
	// The agent remembers context from the previous turn.
	second, err := agent.Process(ctx, agenkit.NewMessage("user", "What's its population?"))
	if err != nil {
		return err
	}
	fmt.Println(second.ContentString())
	return nil
}

// --- Router --------------------------------------------------------------

// KeywordClassifier routes on keywords. Routing is an *agent*, not a function:
// a ClassifierAgent is an Agent that also implements Classify.
type KeywordClassifier struct{}

func (c *KeywordClassifier) Name() string { return "keyword-classifier" }

func (c *KeywordClassifier) Capabilities() []string { return []string{"classify"} }

func (c *KeywordClassifier) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	key, err := c.Classify(ctx, message)
	if err != nil {
		return nil, err
	}
	return agenkit.NewMessage("assistant", key), nil
}

func (c *KeywordClassifier) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(c)
}

// Classify returns the routing key. An empty string falls through to DefaultKey.
func (c *KeywordClassifier) Classify(ctx context.Context, message *agenkit.Message) (string, error) {
	content := strings.ToLower(message.ContentString())
	if strings.Contains(content, "invoice") || strings.Contains(content, "refund") {
		return "billing", nil
	}
	return "", nil
}

func router(ctx context.Context, message *agenkit.Message) error {
	r, err := patterns.NewRouterAgent(&patterns.RouterConfig{
		Classifier: &KeywordClassifier{},
		Agents: map[string]agenkit.Agent{
			"billing":   &EchoAgent{},
			"technical": &EchoAgent{},
		},
		DefaultKey: "technical",
	})
	if err != nil {
		return err
	}

	result, err := r.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

// --- ReAct ---------------------------------------------------------------

// CalculatorTool is a minimal Tool implementation.
type CalculatorTool struct{}

func (t *CalculatorTool) Name() string { return "calculator" }

func (t *CalculatorTool) Description() string { return "Evaluates mathematical expressions" }

func (t *CalculatorTool) Execute(ctx context.Context, params map[string]interface{}) (*agenkit.ToolResult, error) {
	return agenkit.NewToolResult("360"), nil
}

func react(ctx context.Context, message *agenkit.Message) error {
	// The reasoning backend is an Agent (field Agent), and the step budget is
	// MaxSteps.
	agent, err := patterns.NewReActAgent(&patterns.ReActConfig{
		Agent:    &EchoAgent{},
		Tools:    []agenkit.Tool{&CalculatorTool{}},
		MaxSteps: 5,
	})
	if err != nil {
		return err
	}

	result, err := agent.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

// --- Reasoning techniques ------------------------------------------------

// chainOfThought shows the functional-options API the techniques use. There is no
// ChainOfThoughtConfig struct.
func chainOfThought(ctx context.Context) error {
	cot := reasoning.NewChainOfThought(
		&EchoAgent{},
		reasoning.WithMaxSteps(5),
	)

	result, err := cot.Process(ctx, agenkit.NewMessage("user", "What is 15 * 24?"))
	if err != nil {
		return err
	}

	// reasoning_steps is only set when steps were parsed out of the response.
	if steps, ok := result.Metadata["reasoning_steps"].([]string); ok {
		fmt.Println(steps)
	}
	return nil
}

func treeOfThought(ctx context.Context, message *agenkit.Message) error {
	tot := reasoning.NewTreeOfThought(
		&EchoAgent{},
		reasoning.WithBranchingFactor(3),
		reasoning.WithMaxDepth(4),
	)

	result, err := tot.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

func selfConsistency(ctx context.Context, message *agenkit.Message) error {
	sc := reasoning.NewSelfConsistency(
		&EchoAgent{},
		reasoning.WithNumSamples(7),
		reasoning.WithVotingStrategy(reasoning.VotingStrategyMajority),
	)

	result, err := sc.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

// --- Observability -------------------------------------------------------

// tracing wraps an agent in a span. NewTracingMiddleware takes the span *name*;
// it resolves the tracer itself. Passing "" derives "agent.<name>.process".
func tracing(ctx context.Context, message *agenkit.Message) error {
	agent := observability.NewTracingMiddleware(&EchoAgent{}, "process_request")

	result, err := agent.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

// --- Servers -------------------------------------------------------------

// httpServer exposes an agent over HTTP. The lifecycle is Start(ctx)/Stop(),
// not ListenAndServe.
func httpServer(ctx context.Context) error {
	server := http.NewHTTPAgent(&EchoAgent{}, ":8080")

	if err := server.Start(ctx); err != nil {
		return err
	}
	defer func() { _ = server.Stop() }()
	return nil
}

// grpcServer exposes an agent over gRPC. Same lifecycle as httpServer above:
// cancelling ctx shuts the server down, and Stop() is the explicit path.
func grpcServer(ctx context.Context) error {
	server, err := grpc.NewGRPCServer(&EchoAgent{}, ":50051")
	if err != nil {
		return err
	}

	if err := server.Start(ctx); err != nil {
		return err
	}
	defer func() { _ = server.Stop() }()
	return nil
}

// --- Cross-language ------------------------------------------------------

// callPythonAgent treats an agent in another language as a local Agent.
func callPythonAgent(ctx context.Context, message *agenkit.Message) error {
	pythonAgent, err := remote.NewRemoteAgent("python-agent", "http://localhost:8000", 30*time.Second)
	if err != nil {
		return err
	}
	defer func() { _ = pythonAgent.Close() }()

	result, err := pythonAgent.Process(ctx, message)
	if err != nil {
		return err
	}
	fmt.Println(result.ContentString())
	return nil
}

func main() {
	ctx := context.Background()
	message := agenkit.NewMessage("user", "Hello!")

	// Only the snippets that need neither a network nor an API key are run; the
	// rest are here to be compiled.
	for name, fn := range map[string]func() error{
		"basic":      func() error { return basicAgent(ctx) },
		"resilience": func() error { return resilience(ctx, message) },
		"sequential": func() error { return sequentialPipeline(ctx, message) },
		"parallel":   func() error { return parallelExecution(ctx, message) },
		"router":     func() error { return router(ctx, agenkit.NewMessage("user", "I need a refund")) },
		"cot":        func() error { return chainOfThought(ctx) },
	} {
		if err := fn(); err != nil {
			log.Fatalf("%s: %v", name, err)
		}
	}

	// Compile-only: these need a server, an API key, or a peer process.
	_ = conversational
	_ = react
	_ = treeOfThought
	_ = selfConsistency
	_ = tracing
	_ = httpServer
	_ = grpcServer
	_ = callPythonAgent
}
