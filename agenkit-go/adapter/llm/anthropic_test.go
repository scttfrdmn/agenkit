package llm

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// capturedRequest records what the fake Anthropic server received.
type capturedRequest struct {
	Path    string
	Header  http.Header
	RawBody []byte
	Body    map[string]interface{}
}

// fakeAnthropicServer starts an httptest server that records every request and
// replies with respond. The returned func returns the captured requests.
func fakeAnthropicServer(t *testing.T, respond func(w http.ResponseWriter, body map[string]interface{})) (*httptest.Server, func() []capturedRequest) {
	t.Helper()
	var (
		mu       sync.Mutex
		captured []capturedRequest
	)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		raw, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		var body map[string]interface{}
		if err := json.Unmarshal(raw, &body); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		mu.Lock()
		captured = append(captured, capturedRequest{
			Path:    r.URL.Path,
			Header:  r.Header.Clone(),
			RawBody: raw,
			Body:    body,
		})
		mu.Unlock()
		respond(w, body)
	}))
	t.Cleanup(srv.Close)
	return srv, func() []capturedRequest {
		mu.Lock()
		defer mu.Unlock()
		out := make([]capturedRequest, len(captured))
		copy(out, captured)
		return out
	}
}

func writeCompletion(w http.ResponseWriter, _ map[string]interface{}) {
	w.Header().Set("Content-Type", "application/json")
	_, _ = io.WriteString(w, `{
		"id": "msg_test_123",
		"type": "message",
		"role": "assistant",
		"content": [{"type": "text", "text": "Hello there!"}],
		"model": "claude-sonnet-5-20260101",
		"stop_reason": "end_turn",
		"usage": {"input_tokens": 12, "output_tokens": 4}
	}`)
}

func writeStream(w http.ResponseWriter, _ map[string]interface{}) {
	w.Header().Set("Content-Type", "text/event-stream")
	events := []string{
		`{"type":"message_start","message":{"id":"msg_s","type":"message","role":"assistant","content":[],"model":"claude-sonnet-5","usage":{"input_tokens":5,"output_tokens":0}}}`,
		`{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}`,
		`{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Hel"}}`,
		`{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"lo"}}`,
		`{"type":"content_block_stop","index":0}`,
		`{"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":2}}`,
		`{"type":"message_stop"}`,
	}
	for _, e := range events {
		var typ struct {
			Type string `json:"type"`
		}
		_ = json.Unmarshal([]byte(e), &typ)
		if _, err := fmt.Fprintf(w, "event: %s\ndata: %s\n\n", typ.Type, e); err != nil {
			return
		}
	}
}

func testMessages() []*agenkit.Message {
	return []*agenkit.Message{
		agenkit.NewMessage("system", "You are terse."),
		agenkit.NewMessage("user", "Hi"),
	}
}

func TestAnthropicLLMInterface(t *testing.T) {
	var _ LLM = &AnthropicLLM{}
}

func TestAnthropicComplete(t *testing.T) {
	srv, requests := fakeAnthropicServer(t, writeCompletion)
	a := NewAnthropicLLM("test-key", "claude-sonnet-5", WithBaseURL(srv.URL))

	resp, err := a.Complete(context.Background(), testMessages(), WithMaxTokens(256))
	if err != nil {
		t.Fatalf("Complete returned error: %v", err)
	}

	if got := resp.ContentString(); got != "Hello there!" {
		t.Errorf("content = %q, want %q", got, "Hello there!")
	}
	if got := resp.Metadata["stop_reason"]; got != "end_turn" {
		t.Errorf("stop_reason = %v, want end_turn", got)
	}
	if got := resp.Metadata["id"]; got != "msg_test_123" {
		t.Errorf("id = %v, want msg_test_123", got)
	}
	if got := resp.Metadata[agenkit.MetadataKeyResponseModel]; got != "claude-sonnet-5-20260101" {
		t.Errorf("response model = %v, want claude-sonnet-5-20260101", got)
	}
	usage, ok := resp.Metadata["usage"].(map[string]interface{})
	if !ok {
		t.Fatalf("usage metadata missing or wrong type: %T", resp.Metadata["usage"])
	}
	if usage["input_tokens"] != 12 || usage["output_tokens"] != 4 {
		t.Errorf("usage = %v, want input 12 / output 4", usage)
	}

	reqs := requests()
	if len(reqs) != 1 {
		t.Fatalf("server received %d requests, want 1", len(reqs))
	}
	r := reqs[0]
	if r.Path != "/messages" {
		t.Errorf("path = %q, want /messages", r.Path)
	}
	if got := r.Header.Get("x-api-key"); got != "test-key" {
		t.Errorf("x-api-key = %q, want test-key", got)
	}
	if got := r.Body["model"]; got != "claude-sonnet-5" {
		t.Errorf("model = %v, want claude-sonnet-5", got)
	}
	if got := r.Body["max_tokens"]; got != float64(256) {
		t.Errorf("max_tokens = %v, want 256", got)
	}
	if got := r.Body["system"]; got != "You are terse." {
		t.Errorf("system = %v, want %q", got, "You are terse.")
	}
	if _, ok := r.Body["stream"]; ok {
		t.Errorf("stream should be omitted for Complete, body: %s", r.RawBody)
	}
}

func TestAnthropicAPIVersionHeader(t *testing.T) {
	srv, requests := fakeAnthropicServer(t, writeCompletion)
	a := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))

	if _, err := a.Complete(context.Background(), testMessages()); err != nil {
		t.Fatalf("Complete returned error: %v", err)
	}
	// Pinned version must stay 2023-06-01 until the Phase 2 migration (#1075).
	if got := requests()[0].Header.Get("anthropic-version"); got != "2023-06-01" {
		t.Errorf("anthropic-version = %q, want 2023-06-01", got)
	}
}

func TestAnthropicStream(t *testing.T) {
	srv, requests := fakeAnthropicServer(t, writeStream)
	a := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))

	stream, err := a.Stream(context.Background(), testMessages())
	if err != nil {
		t.Fatalf("Stream returned error: %v", err)
	}
	var sb strings.Builder
	for chunk := range stream {
		if e, ok := chunk.Metadata["error"]; ok {
			t.Fatalf("stream error chunk: %v", e)
		}
		if chunk.Metadata["streaming"] != true {
			t.Errorf("chunk missing streaming=true metadata")
		}
		sb.WriteString(chunk.ContentString())
	}
	if got := sb.String(); got != "Hello" {
		t.Errorf("streamed content = %q, want Hello", got)
	}

	reqs := requests()
	if len(reqs) != 1 {
		t.Fatalf("server received %d requests, want 1", len(reqs))
	}
	if got := reqs[0].Body["stream"]; got != true {
		t.Errorf("stream = %v, want true", got)
	}
}

// TestAnthropicOmitsSamplingParams asserts temperature and top_p are never sent,
// even when set: Anthropic API 2026-10-21 rejects them with HTTP 400 (#1071).
func TestAnthropicOmitsSamplingParams(t *testing.T) {
	sampling := []CallOption{WithTemperature(0.3), WithTopP(0.9), WithMaxTokens(100)}

	tests := []struct {
		name    string
		respond func(http.ResponseWriter, map[string]interface{})
		call    func(a *AnthropicLLM) error
	}{
		{
			name:    "complete",
			respond: writeCompletion,
			call: func(a *AnthropicLLM) error {
				_, err := a.Complete(context.Background(), testMessages(), sampling...)
				return err
			},
		},
		{
			name:    "stream",
			respond: writeStream,
			call: func(a *AnthropicLLM) error {
				stream, err := a.Stream(context.Background(), testMessages(), sampling...)
				if err != nil {
					return err
				}
				for range stream { // drain until the server closes the stream
				}
				return nil
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			srv, requests := fakeAnthropicServer(t, tt.respond)
			a := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))

			if err := tt.call(a); err != nil {
				t.Fatalf("call returned error: %v", err)
			}
			reqs := requests()
			if len(reqs) != 1 {
				t.Fatalf("server received %d requests, want 1", len(reqs))
			}
			body := reqs[0].Body
			for _, key := range []string{"temperature", "top_p", "top_k"} {
				if _, ok := body[key]; ok {
					t.Errorf("request body must not contain %q, got: %s", key, reqs[0].RawBody)
				}
			}
			// Non-sampling options are still forwarded.
			if got := body["max_tokens"]; got != float64(100) {
				t.Errorf("max_tokens = %v, want 100", got)
			}
		})
	}
}

// TestAnthropicSamplingWarnsOnce verifies the ignored-params warning is logged
// exactly once per adapter instance, and not at all when no sampling is set.
// It swaps the default slog logger, so it must not run in parallel.
func TestAnthropicSamplingWarnsOnce(t *testing.T) {
	var buf bytes.Buffer
	prev := slog.Default()
	slog.SetDefault(slog.New(slog.NewTextHandler(&buf, nil)))
	t.Cleanup(func() { slog.SetDefault(prev) })

	srv, _ := fakeAnthropicServer(t, writeCompletion)
	ctx := context.Background()

	quiet := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))
	if _, err := quiet.Complete(ctx, testMessages(), WithMaxTokens(10)); err != nil {
		t.Fatalf("Complete returned error: %v", err)
	}
	if strings.Contains(buf.String(), "temperature") {
		t.Fatalf("unexpected warning without sampling params: %s", buf.String())
	}

	a := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))
	for i := 0; i < 3; i++ {
		if _, err := a.Complete(ctx, testMessages(), WithTemperature(0.5)); err != nil {
			t.Fatalf("Complete returned error: %v", err)
		}
	}
	if _, err := a.Complete(ctx, testMessages(), WithTopP(0.5)); err != nil {
		t.Fatalf("Complete returned error: %v", err)
	}
	if n := strings.Count(buf.String(), "level=WARN"); n != 1 {
		t.Errorf("got %d warnings for one adapter, want 1; log: %s", n, buf.String())
	}

	// A second adapter instance warns independently.
	b := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))
	if _, err := b.Complete(ctx, testMessages(), WithTopP(0.5)); err != nil {
		t.Fatalf("Complete returned error: %v", err)
	}
	if n := strings.Count(buf.String(), "level=WARN"); n != 2 {
		t.Errorf("got %d warnings across two adapters, want 2; log: %s", n, buf.String())
	}
}

func TestAnthropicErrorStatus(t *testing.T) {
	srv, _ := fakeAnthropicServer(t, func(w http.ResponseWriter, _ map[string]interface{}) {
		http.Error(w, `{"type":"error","error":{"type":"invalid_request_error","message":"bad"}}`, http.StatusBadRequest)
	})
	a := NewAnthropicLLM("k", "claude-sonnet-5", WithBaseURL(srv.URL))

	_, err := a.Complete(context.Background(), testMessages())
	if err == nil {
		t.Fatal("expected error for HTTP 400, got nil")
	}
	if !strings.Contains(err.Error(), "status 400") {
		t.Errorf("error = %v, want it to mention status 400", err)
	}
}
