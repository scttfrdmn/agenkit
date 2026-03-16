//go:build ignore

// minicopilotkit demonstrates CopilotKit-equivalent streaming UI agent patterns
// using Agenkit.
//
// CopilotKit popularised three primitives for integrating AI into interactive
// applications:
//
//	useCopilotState    → shared state that the agent can read/write
//	useCoAgent         → streaming token-by-token text from the backend agent
//	useCopilotAction   → human-in-the-loop approval before destructive ops
//
// This file maps those primitives onto Go types and demonstrates them by
// streaming NDJSON (newline-delimited JSON) events to an io.Writer:
//
//	StateHook          → shared key-value store with RWMutex (useCopilotState)
//	CopilotAgent       → agent that emits text_chunk / state_update / done events
//	ApprovalGate       → channel-based request/response for human approval
//
// Since Go has no AG-UI package, all events are written as NDJSON to stdout.
// A real implementation would pipe this stream over SSE or WebSocket to a
// React front-end.
//
// Prerequisites (optional — demo degrades gracefully if unavailable):
//
//	ollama serve && ollama pull llama3.2
//
// Run with:
//
//	go run main.go
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/adapter/llm"
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ---------------------------------------------------------------------------
// StreamEvent — NDJSON envelope
// ---------------------------------------------------------------------------

// StreamEvent is a single line of NDJSON emitted by the agent.
// The client decodes each line independently as it arrives.
//
// Type values:
//
//	"text_chunk"       — a fragment of the assistant's reply
//	"tool_call"        — agent invoked an internal tool
//	"state_update"     — shared state changed (useCopilotState)
//	"approval_request" — agent requires human confirmation
//	"done"             — stream is complete
type StreamEvent struct {
	Type    string      `json:"type"`
	Content interface{} `json:"content,omitempty"`
}

// emit serialises ev as a single JSON line (NDJSON) and writes it to w.
func emit(w io.Writer, ev StreamEvent) error {
	data, err := json.Marshal(ev)
	if err != nil {
		return fmt.Errorf("failed to marshal event: %w", err)
	}
	if _, err := fmt.Fprintf(w, "%s\n", data); err != nil {
		return fmt.Errorf("failed to write event: %w", err)
	}
	return nil
}

// ---------------------------------------------------------------------------
// StateHook — shared state with concurrent access (useCopilotState)
// ---------------------------------------------------------------------------

// StateHook is a thread-safe key-value store shared between the agent and the
// UI layer. Equivalent to CopilotKit's useCopilotState / useCoAgentState.
type StateHook struct {
	mu    sync.RWMutex
	state map[string]interface{}
}

// NewStateHook creates a new, empty StateHook.
func NewStateHook() *StateHook {
	return &StateHook{state: make(map[string]interface{})}
}

// Get returns the value stored under key, or nil if absent.
func (h *StateHook) Get(key string) interface{} {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return h.state[key]
}

// Set stores val under key.
func (h *StateHook) Set(key string, val interface{}) {
	h.mu.Lock()
	defer h.mu.Unlock()
	h.state[key] = val
}

// Snapshot returns a shallow copy of the current state map.
func (h *StateHook) Snapshot() map[string]interface{} {
	h.mu.RLock()
	defer h.mu.RUnlock()
	snap := make(map[string]interface{}, len(h.state))
	for k, v := range h.state {
		snap[k] = v
	}
	return snap
}

// ---------------------------------------------------------------------------
// ApprovalGate — human-in-the-loop approval (useCopilotAction)
// ---------------------------------------------------------------------------

// ApprovalRequest is the data sent to the UI when the agent requires explicit
// human approval before proceeding.
type ApprovalRequest struct {
	Title   string   `json:"title"`
	Message string   `json:"message"`
	Options []string `json:"options"`
}

// ApprovalGate serialises approval round-trips through a pair of channels.
// The agent calls Request(); a separate goroutine (or test) calls Respond().
// Equivalent to CopilotKit's useCopilotAction with render=UI component.
type ApprovalGate struct {
	requests chan ApprovalRequest
	results  chan bool
}

// NewApprovalGate creates a gate with buffered channels to avoid deadlock in
// demos where request and response happen in the same goroutine timeline.
func NewApprovalGate() *ApprovalGate {
	return &ApprovalGate{
		requests: make(chan ApprovalRequest, 1),
		results:  make(chan bool, 1),
	}
}

// Request blocks until a response is received via Respond() or ctx is
// cancelled. The request is published on the requests channel (non-blocking
// — dropped if no reader is ready) so a UI goroutine can observe it, but
// the call does not require anyone to read from requests to make progress.
func (g *ApprovalGate) Request(ctx context.Context, req ApprovalRequest) (bool, error) {
	// Non-blocking publish so callers without a reader goroutine don't deadlock.
	select {
	case g.requests <- req:
	default:
		// No reader waiting — that is fine; the event was already emitted as
		// an approval_request stream event before this call.
	}

	select {
	case approved := <-g.results:
		return approved, nil
	case <-ctx.Done():
		return false, ctx.Err()
	}
}

// Respond sends the human's decision back to the waiting Request call.
func (g *ApprovalGate) Respond(approved bool) {
	g.results <- approved
}

// ---------------------------------------------------------------------------
// CopilotAgent — streaming agent with state and approval
// ---------------------------------------------------------------------------

// CopilotAgent is an LLM-backed agent that emits NDJSON events to a writer.
// It integrates state hooks (useCopilotState) and an approval gate
// (useCopilotAction) to demonstrate CopilotKit's full interaction model.
type CopilotAgent struct {
	llmClient llm.LLM
	hooks     map[string]*StateHook
	gate      *ApprovalGate
}

// NewCopilotAgent creates an agent backed by the given LLM.
func NewCopilotAgent(llmClient llm.LLM) *CopilotAgent {
	return &CopilotAgent{
		llmClient: llmClient,
		hooks:     make(map[string]*StateHook),
	}
}

// AddHook registers a named StateHook.
func (a *CopilotAgent) AddHook(name string, hook *StateHook) {
	a.hooks[name] = hook
}

// SetGate attaches an ApprovalGate for human-in-the-loop confirmation.
func (a *CopilotAgent) SetGate(gate *ApprovalGate) {
	a.gate = gate
}

// StreamChat processes input and streams events to out.
//
// Event sequence:
//  1. state_update with the current state snapshot
//  2. approval_request + wait (only when input contains "delete" or "danger")
//  3. text_chunk events (one per word in the LLM reply)
//  4. state_update with the incremented message_count
//  5. done
func (a *CopilotAgent) StreamChat(ctx context.Context, input string, out io.Writer) error {
	// 1. Emit initial state snapshot.
	state := a.mergedState()
	if err := emit(out, StreamEvent{Type: "state_update", Content: state}); err != nil {
		return err
	}

	// 2. Approval gate for destructive operations.
	lower := strings.ToLower(input)
	if strings.Contains(lower, "delete") || strings.Contains(lower, "danger") {
		if a.gate == nil {
			return fmt.Errorf("destructive operation requested but no approval gate configured")
		}

		req := ApprovalRequest{
			Title:   "Confirm destructive operation",
			Message: fmt.Sprintf("The agent wants to: %s", input),
			Options: []string{"Approve", "Deny"},
		}

		if err := emit(out, StreamEvent{Type: "approval_request", Content: req}); err != nil {
			return err
		}

		approved, err := a.gate.Request(ctx, req)
		if err != nil {
			return fmt.Errorf("approval gate error: %w", err)
		}
		if !approved {
			return emit(out, StreamEvent{Type: "done", Content: map[string]interface{}{
				"status": "denied",
				"reason": "user did not approve the destructive operation",
			}})
		}
	}

	// 3. Generate a reply and stream it word-by-word.
	replyText := a.generateReply(ctx, input)

	words := strings.Fields(replyText)
	for i, word := range words {
		chunk := word
		if i < len(words)-1 {
			chunk += " "
		}
		if err := emit(out, StreamEvent{Type: "text_chunk", Content: chunk}); err != nil {
			return err
		}
	}

	// 4. Increment message_count and emit updated state.
	if counter, ok := a.hooks["counter"]; ok {
		count := 0
		if v, ok := counter.Get("message_count").(int); ok {
			count = v
		}
		counter.Set("message_count", count+1)
	}

	if err := emit(out, StreamEvent{Type: "state_update", Content: a.mergedState()}); err != nil {
		return err
	}

	// 5. Signal end of stream.
	return emit(out, StreamEvent{Type: "done", Content: map[string]interface{}{"status": "ok"}})
}

// mergedState collects snapshots from all registered hooks into one map.
func (a *CopilotAgent) mergedState() map[string]interface{} {
	merged := make(map[string]interface{})
	for name, hook := range a.hooks {
		snap := hook.Snapshot()
		for k, v := range snap {
			merged[fmt.Sprintf("%s.%s", name, k)] = v
		}
	}
	return merged
}

// generateReply calls the LLM or falls back to a canned reply.
func (a *CopilotAgent) generateReply(ctx context.Context, input string) string {
	resp, err := a.llmClient.Complete(ctx, []*agenkit.Message{
		agenkit.NewMessage("system", "You are a helpful assistant. Keep answers concise."),
		agenkit.NewMessage("user", input),
	})
	if err != nil {
		if strings.Contains(err.Error(), "connection refused") ||
			strings.Contains(err.Error(), "no such host") {
			return fmt.Sprintf("[LLM not running] mock reply to: %s", input)
		}
		return fmt.Sprintf("[LLM error: %v]", err)
	}
	return resp.ContentString()
}

// ---------------------------------------------------------------------------
// Demo helpers
// ---------------------------------------------------------------------------

func printSection(title string) {
	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println(title)
	fmt.Println(strings.Repeat("=", 60))
}

// captureStream runs StreamChat and prints each event line as it arrives.
func captureStream(ctx context.Context, agent *CopilotAgent, input string) {
	fmt.Printf("Input: %s\n\n", input)

	pr, pw := io.Pipe()

	// Writer goroutine
	errCh := make(chan error, 1)
	go func() {
		err := agent.StreamChat(ctx, input, pw)
		_ = pw.CloseWithError(err)
		errCh <- err
	}()

	// Reader — decode and pretty-print each NDJSON line.
	// Close pr when done so the writer goroutine can unblock if it is mid-write.
	decoder := json.NewDecoder(pr)
	for {
		var ev StreamEvent
		if err := decoder.Decode(&ev); err != nil {
			break
		}
		contentJSON, _ := json.Marshal(ev.Content)
		fmt.Printf("  event: %-20s content: %s\n", ev.Type, contentJSON)

		if ev.Type == "done" {
			break
		}
	}
	_ = pr.Close() // signal writer that we are done reading

	if err := <-errCh; err != nil {
		fmt.Fprintf(os.Stderr, "stream error: %v\n", err)
	}
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

func main() {
	ctx := context.Background()

	ollamaLLM := llm.NewOpenAICompatibleLLM(
		"http://localhost:11434/v1",
		"llama3.2",
		"ollama",
		"", // no API key required for local servers
	)

	fmt.Println("MiniCopilotKit — CopilotKit streaming UI agent with Agenkit")
	fmt.Println("Primitives: StateHook (useCopilotState) · streaming NDJSON · ApprovalGate (useCopilotAction)")

	// ------------------------------------------------------------------
	// Shared state: a counter hook that the agent increments per message.
	// ------------------------------------------------------------------
	counter := NewStateHook()
	counter.Set("message_count", 0)

	agent := NewCopilotAgent(ollamaLLM)
	agent.AddHook("counter", counter)

	gate := NewApprovalGate()
	agent.SetGate(gate)

	// ------------------------------------------------------------------
	// 1. Normal chat — no approval required.
	// ------------------------------------------------------------------
	printSection("1. Normal chat")
	captureStream(ctx, agent, "Hello, how are you?")

	// ------------------------------------------------------------------
	// 2. Second chat — shows state counter increment.
	// ------------------------------------------------------------------
	printSection("2. Follow-up chat (state counter increments)")
	captureStream(ctx, agent, "Tell me about Go.")

	fmt.Printf("\nCounter after 2 chats: %v\n", counter.Get("message_count"))

	// ------------------------------------------------------------------
	// 3. Destructive operation — approval gate fires.
	// ------------------------------------------------------------------
	printSection("3. Destructive operation (approval gate)")
	fmt.Println("Simulating human approval in a separate goroutine…")

	// Simulate the UI responding "approved" after a brief delay.
	go func() {
		time.Sleep(50 * time.Millisecond)
		fmt.Println("  [UI] user clicked Approve")
		gate.Respond(true)
	}()

	captureStream(ctx, agent, "Please delete all data")

	// ------------------------------------------------------------------
	// 4. Destructive operation — denied by user.
	// ------------------------------------------------------------------
	printSection("4. Destructive operation (denied)")

	go func() {
		time.Sleep(100 * time.Millisecond)
		fmt.Println("  [UI] user clicked Deny")
		gate.Respond(false)
	}()

	captureStream(ctx, agent, "This is a danger zone — proceed anyway?")

	fmt.Println()
	fmt.Println(strings.Repeat("=", 60))
	fmt.Println("MiniCopilotKit demo complete.")
	fmt.Println()
	fmt.Println("Key takeaways:")
	fmt.Println("  StateHook         → thread-safe shared state (useCopilotState)")
	fmt.Println("  StreamEvent/NDJSON → token-by-token streaming (useCoAgent)")
	fmt.Println("  ApprovalGate      → channel-based human-in-the-loop (useCopilotAction)")
	fmt.Println("  StreamChat()      → composes all three into one ordered event sequence")
}
