package patterns

import (
	"context"
	"fmt"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// LLMClient is the interface for LLM clients used by the patterns.
//
// It declares Complete with exactly the signature every shipped adapter already
// has, so *llm.AnthropicLLM, *llm.OpenAILLM and the rest satisfy it structurally —
// no import of adapter/llm, and no wrapper for callers to write.
//
// Until v0.86.0 this interface declared:
//
//	Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error)
//
// which not one shipped adapter had. Every adapter implements Complete. So
// ConversationalAgent and PlanningAgent could not be used with any real LLM, and
// the only Chat implementors in the module were mockLLMClient in
// conversational_test.go and planningMockLLMClient in planning_test.go — doubles
// shaped like the call site rather than the contract, which is why the tests
// covered the seam and could never have caught it. See #805.
//
// Deliberately not defined as `llm.LLM`: adapter/llm transitively imports the AWS
// SDK (~20 packages) for the Bedrock adapter, and patterns depends on the agenkit
// core package alone. Structural typing gets the compatibility without the
// dependency — which is also why agenkit.CallOption had to move to the core package
// rather than stay in adapter/llm.
type LLMClient interface {
	// Complete generates a response given a conversation history.
	Complete(ctx context.Context, messages []*agenkit.Message, opts ...agenkit.CallOption) (*agenkit.Message, error)
}

// ChatLLMClient is the deprecated client interface.
//
// Deprecated: implement LLMClient (Complete) instead. Accepted for one release
// cycle so existing code and the published examples keep working. See #805.
type ChatLLMClient interface {
	// Chat generates a response given a conversation history.
	Chat(ctx context.Context, messages []*agenkit.Message) (*agenkit.Message, error)
}

// AgentLLMClient is an agent used as an LLM backend.
//
// Accepting this lets any agent — a reasoning technique, another pattern — serve as
// a conversational backend, which is what the Rust core does
// (agenkit-rust/src/patterns/conversational.rs). The history is flattened into the
// single message the Agent contract takes.
type AgentLLMClient interface {
	Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error)
}

// FlattenHistory collapses a conversation into the single message Process takes.
//
// The "{role}: {content}" form matches the Rust and Python cores so the three do
// not drift.
func FlattenHistory(messages []*agenkit.Message) *agenkit.Message {
	rendered := ""
	for i, msg := range messages {
		if i > 0 {
			rendered += "\n"
		}
		rendered += fmt.Sprintf("%s: %s", msg.Role, msg.ContentString())
	}
	return &agenkit.Message{Role: "user", Content: rendered}
}

// checkLLMClient reports whether a client implements one of the accepted contracts.
//
// Constructors call this so an unusable client fails at construction, where the
// caller can still fix it, rather than at the first Process call in production.
func checkLLMClient(client any) error {
	switch client.(type) {
	case LLMClient, AgentLLMClient, ChatLLMClient:
		return nil
	default:
		return fmt.Errorf(
			"llm client %T must implement Complete(ctx, messages, opts...) (the "+
				"adapter contract, satisfied by every agenkit adapter/llm client), "+
				"Process(ctx, message) (the Agent contract), or the deprecated "+
				"Chat(ctx, messages)", client)
	}
}

// completeMessages sends a conversation to a client and returns the response.
//
// Dispatches in contract-priority order: Complete (what all adapters implement),
// then Process (the Agent contract), then the deprecated Chat. This is the single
// place that resolves "what does this client respond to", so a fourth spelling has
// one place to be rejected instead of several places to appear (#805).
//
// The client is typed as `any` because the three accepted contracts cannot be
// expressed as one Go interface; the type switch below is the check, and an
// unrecognised client is a hard error rather than a nil response.
func completeMessages(
	ctx context.Context,
	client any,
	messages []*agenkit.Message,
	opts ...agenkit.CallOption,
) (*agenkit.Message, error) {
	switch c := client.(type) {
	case LLMClient:
		return c.Complete(ctx, messages, opts...)
	case AgentLLMClient:
		if len(opts) > 0 {
			// Refuse rather than drop: the Agent contract has no options parameter,
			// and silently ignoring them is the failure #801 was filed about.
			return nil, fmt.Errorf(
				"per-call options cannot be applied through %T: the Agent contract is "+
					"Process(ctx, message) with no options parameter", client)
		}
		return c.Process(ctx, FlattenHistory(messages))
	case ChatLLMClient:
		return c.Chat(ctx, messages)
	default:
		return nil, fmt.Errorf(
			"llm client %T must implement Complete(ctx, messages, opts...) (the "+
				"adapter contract), Process(ctx, message) (the Agent contract), or the "+
				"deprecated Chat(ctx, messages)", client)
	}
}
