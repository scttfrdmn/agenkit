package agenkit

import (
	"context"
	"testing"
)

// optionsAgent implements OptionsAgent and records which path it was entered by.
//
// Recording the path matters as much as recording the options: the bug this file
// guards against is a caller that takes the plain Process path and silently drops
// what it was handed, which a test that only inspects the returned message cannot
// distinguish from success (#801).
type optionsAgent struct {
	processCalls     int
	processWithCalls int
	lastOpts         []CallOption
}

func (a *optionsAgent) Name() string { return "options_agent" }

func (a *optionsAgent) Capabilities() []string { return []string{"options"} }

func (a *optionsAgent) Introspect() *IntrospectionResult {
	return DefaultIntrospectionResult(a)
}

func (a *optionsAgent) Process(ctx context.Context, message *Message) (*Message, error) {
	a.processCalls++
	return NewMessage("assistant", "plain"), nil
}

func (a *optionsAgent) ProcessWith(
	ctx context.Context,
	message *Message,
	opts ...CallOption,
) (*Message, error) {
	a.processWithCalls++
	a.lastOpts = opts
	return NewMessage("assistant", "with-options"), nil
}

var _ OptionsAgent = (*optionsAgent)(nil)

func TestSupportsOptions(t *testing.T) {
	if SupportsOptions(NewSimpleAgent()) {
		t.Error("a plain Agent reports it supports options; it has nowhere to put them")
	}
	if !SupportsOptions(&optionsAgent{}) {
		t.Error("an OptionsAgent reports it does not support options")
	}
}

func TestProcessWithOptions_ReachesOptionsAgent(t *testing.T) {
	agent := &optionsAgent{}
	response, err := ProcessWithOptions(
		context.Background(),
		agent,
		NewMessage("user", "Q"),
		WithTemperature(0.0), // 0.0 is a real request (greedy), not "unset"
		WithMaxTokens(32),
	)
	if err != nil {
		t.Fatalf("ProcessWithOptions: %v", err)
	}
	if agent.processWithCalls != 1 || agent.processCalls != 0 {
		t.Fatalf("took the plain path: ProcessWith=%d Process=%d",
			agent.processWithCalls, agent.processCalls)
	}
	if response.ContentString() != "with-options" {
		t.Errorf("response = %q, want the ProcessWith response", response.ContentString())
	}

	built := BuildCallOptions(agent.lastOpts...)
	if built.Temperature == nil {
		t.Fatal("temperature was dropped; 0.0 must survive as a set value")
	}
	if *built.Temperature != 0.0 {
		t.Errorf("temperature = %v, want 0", *built.Temperature)
	}
	if built.MaxTokens == nil || *built.MaxTokens != 32 {
		t.Errorf("maxTokens = %v, want 32", built.MaxTokens)
	}
}

func TestProcessWithOptions_NoOptionsSkipsTheOptionsPath(t *testing.T) {
	// An empty options set is indistinguishable from not asking, so an
	// OptionsAgent must not be handed an empty CallOptions just because the
	// helper was used.
	agent := &optionsAgent{}
	if _, err := ProcessWithOptions(context.Background(), agent, NewMessage("user", "Q")); err != nil {
		t.Fatalf("ProcessWithOptions: %v", err)
	}
	if agent.processWithCalls != 0 || agent.processCalls != 1 {
		t.Errorf("with no options: ProcessWith=%d Process=%d, want 0 and 1",
			agent.processWithCalls, agent.processCalls)
	}
}

func TestProcessWithOptions_PlainAgentStillProcesses(t *testing.T) {
	// The options cannot be applied — a plain Agent has nowhere to put them — but
	// the call must still succeed. Callers that need to know whether the options
	// landed check SupportsOptions; that is what makes the drop visible rather
	// than silent.
	response, err := ProcessWithOptions(
		context.Background(),
		NewSimpleAgent(),
		NewMessage("user", "Q"),
		WithTemperature(0.7),
	)
	if err != nil {
		t.Fatalf("ProcessWithOptions: %v", err)
	}
	if response.ContentString() != "Processed: Q" {
		t.Errorf("response = %q, want the plain Process response", response.ContentString())
	}
}
