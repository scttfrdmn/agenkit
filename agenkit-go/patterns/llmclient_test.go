// Tests that the patterns work with the LLM clients agenkit actually ships (#805).
//
// patterns.LLMClient used to require:
//
//	Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error)
//
// Not one of the adapters in adapter/llm has a Chat method — they all
// implement Complete(ctx, messages, opts...). So ConversationalAgent and
// PlanningAgent could not be constructed with any real LLM; the compiler rejected
// it. The only Chat implementors in the whole module were the test doubles
// themselves, each written against the call site rather than against the contract,
// which is exactly why the seam had full coverage and no test could ever have
// caught it.
//
// The load-bearing tests here are the ones driving a pattern with a client shaped
// like a real adapter. adapterShapedClient's Complete signature is copied from
// adapter/llm/anthropic.go and must stay identical to it.
package patterns

import (
	"context"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// adapterShapedClient has exactly the signature of every client in adapter/llm.
type adapterShapedClient struct {
	response string
	calls    [][]*agenkit.Message
	optsSeen [][]agenkit.CallOption
}

func (a *adapterShapedClient) Complete(
	_ context.Context,
	messages []*agenkit.Message,
	opts ...agenkit.CallOption,
) (*agenkit.Message, error) {
	snapshot := make([]*agenkit.Message, len(messages))
	copy(snapshot, messages)
	a.calls = append(a.calls, snapshot)
	a.optsSeen = append(a.optsSeen, opts)

	response := a.response
	if response == "" {
		response = "adapter response"
	}
	return &agenkit.Message{Role: "assistant", Content: response}, nil
}

// chatOnlyClient is the deprecated shape — what every old double looked like.
type chatOnlyClient struct {
	calls [][]*agenkit.Message
}

func (c *chatOnlyClient) Chat(_ context.Context, messages []*agenkit.Message) (*agenkit.Message, error) {
	c.calls = append(c.calls, messages)
	return &agenkit.Message{Role: "assistant", Content: "chat response"}, nil
}

// agentBackend is an agent used as an LLM, as the Rust core does.
type agentBackend struct {
	received []*agenkit.Message
}

func (a *agentBackend) Name() string { return "agent_backend" }

func (a *agentBackend) Capabilities() []string { return nil }

func (a *agentBackend) Process(_ context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.received = append(a.received, message)
	return &agenkit.Message{Role: "assistant", Content: "agent response"}, nil
}

// noContractClient implements none of the three accepted contracts.
type noContractClient struct{}

// ============================================================================
// Real adapter contract — the tests that would have caught #805
// ============================================================================

func TestConversationalAgent_AcceptsAdapterShapedClient(t *testing.T) {
	// Before the fix this did not compile: *adapterShapedClient does not
	// implement patterns.LLMClient (missing method Chat).
	llm := &adapterShapedClient{response: "Hello!"}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{LLMClient: llm})
	if err != nil {
		t.Fatalf("NewConversationalAgent: %v", err)
	}

	response, err := agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Hi"})
	if err != nil {
		t.Fatalf("Process: %v", err)
	}
	if got := response.ContentString(); got != "Hello!" {
		t.Errorf("response = %q, want %q", got, "Hello!")
	}
	if len(llm.calls) != 1 {
		t.Errorf("adapter called %d times, want 1", len(llm.calls))
	}
}

func TestConversationalAgent_AdapterReceivesRealHistory(t *testing.T) {
	// Not just "it didn't error" — the adapter must get the right shape, which is
	// how #802 (a str where a message list was expected) went unnoticed.
	llm := &adapterShapedClient{}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     llm,
		MaxHistory:    10,
		SystemPrompt:  "Be terse.",
		IncludeSystem: true,
	})
	if err != nil {
		t.Fatalf("NewConversationalAgent: %v", err)
	}

	ctx := context.Background()
	if _, err := agent.Process(ctx, &agenkit.Message{Role: "user", Content: "Q1"}); err != nil {
		t.Fatalf("Process turn 1: %v", err)
	}
	if _, err := agent.Process(ctx, &agenkit.Message{Role: "user", Content: "Q2"}); err != nil {
		t.Fatalf("Process turn 2: %v", err)
	}

	if len(llm.calls) != 2 {
		t.Fatalf("adapter called %d times, want 2", len(llm.calls))
	}
	wantFirst := []string{"system", "user"}
	if got := roles(llm.calls[0]); !equalStrings(got, wantFirst) {
		t.Errorf("turn 1 roles = %v, want %v", got, wantFirst)
	}
	// Turn 2 must carry the first exchange — that is the entire point of the pattern.
	wantSecond := []string{"system", "user", "assistant", "user"}
	if got := roles(llm.calls[1]); !equalStrings(got, wantSecond) {
		t.Errorf("turn 2 roles = %v, want %v", got, wantSecond)
	}
}

func TestConversationalAgent_NoOptionsMeansNoOptions(t *testing.T) {
	// An unset option must be omitted, not forwarded as a zero value — that is
	// the whole invariant CallOptions exists for (#801).
	llm := &adapterShapedClient{}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{LLMClient: llm})
	if err != nil {
		t.Fatalf("NewConversationalAgent: %v", err)
	}

	if _, err := agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Q"}); err != nil {
		t.Fatalf("Process: %v", err)
	}
	if len(llm.optsSeen[0]) != 0 {
		t.Errorf("adapter received %d options, want 0", len(llm.optsSeen[0]))
	}
}

func TestPlanningAgent_AcceptsAdapterShapedClient(t *testing.T) {
	llm := &adapterShapedClient{response: `Goal: Ship it
Steps:
1. Write the code
2. Test the code`}
	agent := NewPlanningAgent(llm, &mockStepExecutor{failOnStep: -1}, nil)

	response, err := agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Ship it"})
	if err != nil {
		t.Fatalf("Process: %v", err)
	}
	if response == nil {
		t.Fatal("response is nil")
	}
	if len(llm.calls) == 0 {
		t.Error("adapter was never called")
	}
}

// ============================================================================
// Agent as a backend
// ============================================================================

func TestConversationalAgent_AcceptsAgentBackend(t *testing.T) {
	backend := &agentBackend{}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{LLMClient: backend})
	if err != nil {
		t.Fatalf("NewConversationalAgent: %v", err)
	}

	response, err := agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Q"})
	if err != nil {
		t.Fatalf("Process: %v", err)
	}
	if got := response.ContentString(); got != "agent response" {
		t.Errorf("response = %q, want %q", got, "agent response")
	}
}

func TestFlattenHistory(t *testing.T) {
	// Matches the Python and Rust cores so the three cannot drift.
	flat := FlattenHistory([]*agenkit.Message{
		{Role: "system", Content: "S"},
		{Role: "user", Content: "Q"},
	})

	if got, want := flat.ContentString(), "system: S\nuser: Q"; got != want {
		t.Errorf("flattened = %q, want %q", got, want)
	}
	if flat.Role != "user" {
		t.Errorf("flattened role = %q, want %q", flat.Role, "user")
	}
}

func TestConversationalAgent_AgentBackendGetsFlattenedMessage(t *testing.T) {
	// The Agent contract takes one Message, not a slice — handing it a slice is
	// the shape mismatch #802 was about.
	backend := &agentBackend{}
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{
		LLMClient:     backend,
		SystemPrompt:  "S",
		IncludeSystem: true,
		MaxHistory:    10,
	})
	if err != nil {
		t.Fatalf("NewConversationalAgent: %v", err)
	}

	if _, err := agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Q"}); err != nil {
		t.Fatalf("Process: %v", err)
	}

	if len(backend.received) != 1 {
		t.Fatalf("backend received %d messages, want 1", len(backend.received))
	}
	if got, want := backend.received[0].ContentString(), "system: S\nuser: Q"; got != want {
		t.Errorf("backend received %q, want %q", got, want)
	}
}

func TestCompleteMessages_AgentBackendRejectsOptions(t *testing.T) {
	// Refuse rather than silently drop: the Agent contract has no options
	// parameter, and a temperature that vanishes is worse than an error.
	_, err := completeMessages(
		context.Background(),
		&agentBackend{},
		[]*agenkit.Message{{Role: "user", Content: "Q"}},
		agenkit.WithTemperature(0.5),
	)
	if err == nil {
		t.Fatal("expected an error when options cannot be forwarded, got nil")
	}
	if !strings.Contains(err.Error(), "options cannot be applied") {
		t.Errorf("error = %q, want it to explain the options could not be applied", err)
	}
}

// ============================================================================
// Deprecated chat()
// ============================================================================

func TestCompleteMessages_DeprecatedChatStillWorks(t *testing.T) {
	// Kept for one release cycle so published example code does not break outright.
	llm := &chatOnlyClient{}
	response, err := completeMessages(
		context.Background(), llm, []*agenkit.Message{{Role: "user", Content: "Q"}})
	if err != nil {
		t.Fatalf("completeMessages: %v", err)
	}
	if got := response.ContentString(); got != "chat response" {
		t.Errorf("response = %q, want %q", got, "chat response")
	}
}

func TestConversationalAgent_AcceptsDeprecatedChatClient(t *testing.T) {
	agent, err := NewConversationalAgent(&ConversationalAgentConfig{LLMClient: &chatOnlyClient{}})
	if err != nil {
		t.Fatalf("NewConversationalAgent: %v", err)
	}
	if _, err := agent.Process(context.Background(), &agenkit.Message{Role: "user", Content: "Q"}); err != nil {
		t.Fatalf("Process: %v", err)
	}
}

// ============================================================================
// Dispatch order and rejection
// ============================================================================

// bothContractsClient implements Complete and Chat. A real adapter that gains a
// Chat shim must keep going through Complete.
type bothContractsClient struct{}

func (b *bothContractsClient) Complete(
	_ context.Context, _ []*agenkit.Message, _ ...agenkit.CallOption,
) (*agenkit.Message, error) {
	return &agenkit.Message{Role: "assistant", Content: "via Complete"}, nil
}

func (b *bothContractsClient) Chat(_ context.Context, _ []*agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{Role: "assistant", Content: "via Chat"}, nil
}

func TestCompleteMessages_PrefersCompleteOverChat(t *testing.T) {
	response, err := completeMessages(
		context.Background(), &bothContractsClient{}, []*agenkit.Message{{Role: "user", Content: "Q"}})
	if err != nil {
		t.Fatalf("completeMessages: %v", err)
	}
	if got := response.ContentString(); got != "via Complete" {
		t.Errorf("dispatched %q, want %q", got, "via Complete")
	}
}

func TestCompleteMessages_NoContractNamesAllThree(t *testing.T) {
	// The error must say what to implement, not just that something failed.
	_, err := completeMessages(
		context.Background(), &noContractClient{}, []*agenkit.Message{{Role: "user", Content: "Q"}})
	if err == nil {
		t.Fatal("expected an error for a client with no contract, got nil")
	}
	for _, want := range []string{"Complete(", "Process(", "Chat("} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error %q does not name %s", err, want)
		}
	}
}

func TestNewConversationalAgent_RejectsClientWithNoContract(t *testing.T) {
	// Fail at construction, where the caller can still fix it — not at the first
	// Process call in production.
	_, err := NewConversationalAgent(&ConversationalAgentConfig{LLMClient: &noContractClient{}})
	if err == nil {
		t.Fatal("expected an error for a client with no contract, got nil")
	}
	if !strings.Contains(err.Error(), "Complete(") {
		t.Errorf("error %q does not name the contract to implement", err)
	}
}

// ============================================================================
// Options reach the adapter
// ============================================================================

func TestCompleteMessages_ForwardsOptionsToAdapter(t *testing.T) {
	llm := &adapterShapedClient{}
	_, err := completeMessages(
		context.Background(),
		llm,
		[]*agenkit.Message{{Role: "user", Content: "Q"}},
		agenkit.WithTemperature(0.0), // 0.0 is a real request (greedy), not "unset"
		agenkit.WithMaxTokens(64),
	)
	if err != nil {
		t.Fatalf("completeMessages: %v", err)
	}

	built := agenkit.BuildCallOptions(llm.optsSeen[0]...)
	if built.Temperature == nil {
		t.Fatal("temperature was dropped; 0.0 must survive as a set value")
	}
	if *built.Temperature != 0.0 {
		t.Errorf("temperature = %v, want 0", *built.Temperature)
	}
	if built.MaxTokens == nil || *built.MaxTokens != 64 {
		t.Errorf("maxTokens = %v, want 64", built.MaxTokens)
	}
}

// ============================================================================
// Helpers
// ============================================================================

func roles(messages []*agenkit.Message) []string {
	out := make([]string, len(messages))
	for i, msg := range messages {
		out[i] = msg.Role
	}
	return out
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}
