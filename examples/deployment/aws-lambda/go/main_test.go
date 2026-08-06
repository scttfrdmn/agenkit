package main

import (
	"context"
	"encoding/json"
	"strings"
	"testing"

	"github.com/aws/aws-lambda-go/events"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// This module had no go.mod and no test file, so nothing compiled main.go — it
// imported a package that does not exist and called four APIs with the wrong
// shapes. These tests make `make test` (a documented target) actually exercise the
// handler rather than only type-check it (#857).

// testEvent mirrors the body the Makefile's events/test-event.json target writes.
func testEvent(agentType string) events.APIGatewayProxyRequest {
	body := `{"agent_type": "` + agentType +
		`", "message": {"role": "user", "content": "Calculate 10 + 5"}}`
	return events.APIGatewayProxyRequest{Body: body}
}

func TestHandleRequestAllAgentTypes(t *testing.T) {
	// "" exercises the default (react); the rest are the types the README documents.
	for _, agentType := range []string{"", "react", "conversational", "router"} {
		resp, err := handleRequest(context.Background(), testEvent(agentType))
		if err != nil {
			t.Fatalf("agent_type=%q: handler returned error: %v", agentType, err)
		}
		if resp.StatusCode != 200 {
			t.Fatalf("agent_type=%q: status %d, body %s", agentType, resp.StatusCode, resp.Body)
		}

		var out Response
		if err := json.Unmarshal([]byte(resp.Body), &out); err != nil {
			t.Fatalf("agent_type=%q: response body is not valid JSON: %v", agentType, err)
		}
		if strings.TrimSpace(out.Content) == "" {
			t.Errorf("agent_type=%q: empty response content", agentType)
		}
	}
}

func TestHandleRequestRejectsUnknownAgentType(t *testing.T) {
	resp, err := handleRequest(context.Background(), testEvent("does-not-exist"))
	if err != nil {
		t.Fatalf("handler should report a bad request, not an error: %v", err)
	}
	if resp.StatusCode != 400 {
		t.Errorf("expected 400 for an unknown agent type, got %d (%s)", resp.StatusCode, resp.Body)
	}
}

func TestHandleRequestRejectsMalformedBody(t *testing.T) {
	resp, err := handleRequest(context.Background(), events.APIGatewayProxyRequest{Body: "not json"})
	if err != nil {
		t.Fatalf("handler should report a bad request, not an error: %v", err)
	}
	if resp.StatusCode != 400 {
		t.Errorf("expected 400 for a malformed body, got %d (%s)", resp.StatusCode, resp.Body)
	}
}

// TestKeywordClassifierRoutes pins the routing table the router agent depends on.
func TestKeywordClassifierRoutes(t *testing.T) {
	cases := map[string]string{
		"Calculate 10 + 5":         "calculator",
		"do some MATH for me":      "calculator",
		"let's chat about the day": "conversational",
		"I want to talk":           "conversational",
		"summarise this document":  "react",
	}

	k := &KeywordClassifier{}
	for input, want := range cases {
		got, err := k.Classify(context.Background(), agenkit.NewMessage("user", input))
		if err != nil {
			t.Fatalf("Classify(%q) failed: %v", input, err)
		}
		if got != want {
			t.Errorf("Classify(%q) = %q, want %q", input, got, want)
		}
	}
}

// TestCalculatorToolDivideByZero: the error path must report failure, not a result.
func TestCalculatorToolDivideByZero(t *testing.T) {
	c := &CalculatorTool{}

	result, err := c.Execute(context.Background(), map[string]interface{}{
		"operation": "divide", "a": 1.0, "b": 0.0,
	})
	if err != nil {
		t.Fatalf("Execute should return a failed ToolResult, not an error: %v", err)
	}
	if result.Success {
		t.Error("divide by zero should not be a successful ToolResult")
	}
	if result.Error == "" {
		t.Error("divide by zero should populate ToolResult.Error")
	}
}

// TestCalculatorToolSuccessSetsData guards the Output-vs-Data mix-up: a literal
// without Success: true reports failure even when the arithmetic worked.
func TestCalculatorToolSuccessSetsData(t *testing.T) {
	c := &CalculatorTool{}

	result, err := c.Execute(context.Background(), map[string]interface{}{
		"operation": "add", "a": 10.0, "b": 5.0,
	})
	if err != nil {
		t.Fatalf("Execute failed: %v", err)
	}
	if !result.Success {
		t.Error("a successful calculation must set Success")
	}
	if got, ok := result.Data.(string); !ok || got != "15.00" {
		t.Errorf("expected Data == \"15.00\", got %#v", result.Data)
	}
}
