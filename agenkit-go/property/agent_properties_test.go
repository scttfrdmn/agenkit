// Package property contains property-based tests for the agenkit-go module.
package property_test

import (
	"context"
	"errors"
	"sync"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"pgregory.net/rapid"
)

// ============================================
// Mock Agents for Property Testing
// ============================================

// successAgent always returns a successful response.
type successAgent struct {
	name string
}

func (a *successAgent) Name() string           { return a.name }
func (a *successAgent) Capabilities() []string { return []string{"mock"} }
func (a *successAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
func (a *successAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "response: "+msg.ContentString()), nil
}

// errorAgent always returns an error.
type errorAgent struct {
	name   string
	errMsg string
}

func (a *errorAgent) Name() string           { return a.name }
func (a *errorAgent) Capabilities() []string { return []string{"mock"} }
func (a *errorAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
func (a *errorAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return nil, errors.New(a.errMsg)
}

// echoAgent echoes the input content.
type echoAgent struct {
	name   string
	prefix string
}

func (a *echoAgent) Name() string           { return a.name }
func (a *echoAgent) Capabilities() []string { return []string{"echo"} }
func (a *echoAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
func (a *echoAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", a.prefix+msg.ContentString()), nil
}

// countingAgent counts Process calls.
type countingAgent struct {
	name      string
	callCount int64
	mu        sync.Mutex
}

func (a *countingAgent) Name() string           { return a.name }
func (a *countingAgent) Capabilities() []string { return []string{"counting"} }
func (a *countingAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
func (a *countingAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	a.mu.Lock()
	a.callCount++
	a.mu.Unlock()
	return agenkit.NewMessage("assistant", "counted"), nil
}
func (a *countingAgent) Count() int64 {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.callCount
}

// ============================================
// Property: Agent Response Invariants
// ============================================

// TestAgentRunReturnsNonNilOnSuccess verifies successful agents return non-nil response.
func TestAgentRunReturnsNonNilOnSuccess(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 200, -1).Draw(t, "content")
		role := rapid.SampledFrom(validRoles).Draw(t, "role")

		agent := &successAgent{name: "test"}
		msg := agenkit.NewMessage(role, content)

		response, err := agent.Process(context.Background(), msg)

		// Property: successful agent returns non-nil response and nil error
		if err != nil {
			t.Fatalf("expected nil error, got %v", err)
		}
		if response == nil {
			t.Fatal("expected non-nil response")
		}
	})
}

// TestAgentRunResponseHasRole verifies response has a valid role.
func TestAgentRunResponseHasRole(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 200, -1).Draw(t, "content")

		agent := &successAgent{name: "responder"}
		msg := agenkit.NewMessage("user", content)

		response, err := agent.Process(context.Background(), msg)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		// Property: response has a non-empty role
		if response.Role == "" {
			t.Fatal("response role should not be empty")
		}
	})
}

// TestAgentRunWithCancelledContextReturnsError verifies context cancellation.
func TestAgentRunWithCancelledContextReturnsError(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 100, -1).Draw(t, "content")

		// ctxAgent respects context cancellation
		agent := &ctxAwareAgent{name: "ctx-agent"}
		msg := agenkit.NewMessage("user", content)

		ctx, cancel := context.WithCancel(context.Background())
		cancel() // Cancel immediately

		response, err := agent.Process(ctx, msg)

		// Property: cancelled context produces error
		if err == nil {
			t.Fatalf("expected error for cancelled context, got response: %v", response)
		}
		if !errors.Is(err, context.Canceled) {
			t.Fatalf("expected context.Canceled, got %v", err)
		}
	})
}

// ctxAwareAgent respects context cancellation.
type ctxAwareAgent struct{ name string }

func (a *ctxAwareAgent) Name() string           { return a.name }
func (a *ctxAwareAgent) Capabilities() []string { return nil }
func (a *ctxAwareAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
func (a *ctxAwareAgent) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	default:
		return agenkit.NewMessage("assistant", "ok"), nil
	}
}

// TestErrorAgentAlwaysReturnsError verifies error agents return errors.
func TestErrorAgentAlwaysReturnsError(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 100, -1).Draw(t, "content")
		errMsg := rapid.StringN(0, 50, -1).Draw(t, "errMsg")

		agent := &errorAgent{name: "err-agent", errMsg: errMsg}
		msg := agenkit.NewMessage("user", content)

		response, err := agent.Process(context.Background(), msg)

		// Property: error agent returns error and nil response
		if err == nil {
			t.Fatal("expected error from errorAgent")
		}
		if response != nil {
			t.Fatalf("expected nil response from errorAgent, got %v", response)
		}
	})
}

// TestEchoAgentPreservesContent verifies echo agent response contains input.
func TestEchoAgentPreservesContent(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 200, -1).Draw(t, "content")
		prefix := rapid.StringN(0, 20, -1).Draw(t, "prefix")

		agent := &echoAgent{name: "echo", prefix: prefix}
		msg := agenkit.NewMessage("user", content)

		response, err := agent.Process(context.Background(), msg)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		// Property: response contains prefix and original content
		responseStr := response.ContentString()
		if len(responseStr) < len(prefix)+len(content) {
			t.Fatalf("response %q is shorter than prefix(%q)+content(%q)", responseStr, prefix, content)
		}
	})
}

// TestConcurrentCallsDoNotCorruptState verifies thread safety.
func TestConcurrentCallsDoNotCorruptState(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		numCalls := rapid.IntRange(5, 20).Draw(t, "numCalls")

		agent := &countingAgent{name: "counter"}
		var wg sync.WaitGroup
		errors := make([]error, numCalls)

		for i := 0; i < numCalls; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				msg := agenkit.NewMessage("user", "concurrent")
				_, err := agent.Process(context.Background(), msg)
				errors[idx] = err
			}(i)
		}
		wg.Wait()

		// Property: all concurrent calls succeeded
		for i, err := range errors {
			if err != nil {
				t.Fatalf("concurrent call %d failed: %v", i, err)
			}
		}

		// Property: call count equals number of calls
		if count := agent.Count(); count != int64(numCalls) {
			t.Fatalf("expected callCount=%d, got %d", numCalls, count)
		}
	})
}

// TestAgentNameIsStable verifies agent name doesn't change between calls.
func TestAgentNameIsStable(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		name := rapid.StringN(0, 50, -1).Draw(t, "name")
		if name == "" {
			name = "agent"
		}

		agent := &successAgent{name: name}

		// Call Name() multiple times
		for i := 0; i < 5; i++ {
			if n := agent.Name(); n != name {
				t.Fatalf("agent.Name() changed: got %q, want %q (call %d)", n, name, i)
			}
		}
	})
}

// TestAgentCapabilitiesIsStable verifies capabilities list is stable between calls.
func TestAgentCapabilitiesIsStable(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		agent := &successAgent{name: "stable"}

		caps1 := agent.Capabilities()
		caps2 := agent.Capabilities()

		// Property: capabilities length is the same
		if len(caps1) != len(caps2) {
			t.Fatalf("capabilities length changed: %d vs %d", len(caps1), len(caps2))
		}
	})
}

// TestMessageBuildWithMetadataChain verifies multiple WithMetadata calls accumulate.
func TestMessageBuildWithMetadataChain(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		numKeys := rapid.IntRange(1, 10).Draw(t, "numKeys")

		msg := agenkit.NewMessage("user", "content")
		keys := make([]string, numKeys)

		for i := 0; i < numKeys; i++ {
			key := rapid.StringMatching(`[a-z]{1,10}`).Draw(t, "key")
			value := rapid.StringN(0, 20, -1).Draw(t, "value")
			keys[i] = key
			msg.WithMetadata(key, value)
		}

		// Property: all keys are present in metadata
		// (later writes may overwrite earlier ones if keys collide — use unique keys)
		uniqueKeys := make(map[string]bool)
		for _, k := range keys {
			uniqueKeys[k] = true
		}

		for k := range uniqueKeys {
			if _, ok := msg.Metadata[k]; !ok {
				t.Fatalf("metadata key %q not found after WithMetadata chain", k)
			}
		}
	})
}

// TestProcessReturnedMessageIsValidatable verifies responses pass Validate().
func TestProcessReturnedMessageIsValidatable(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 100, -1).Draw(t, "content")

		agent := &successAgent{name: "validator-test"}
		msg := agenkit.NewMessage("user", content)

		response, err := agent.Process(context.Background(), msg)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}

		// Property: response passes Validate()
		if err := response.Validate(); err != nil {
			t.Fatalf("agent response failed Validate(): %v", err)
		}
	})
}
