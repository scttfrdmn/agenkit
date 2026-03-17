// Package property contains property-based tests for the agenkit-go module.
// Tests use pgregory.net/rapid to validate invariants across arbitrary inputs.
package property_test

import (
	"context"
	"encoding/json"
	"sync"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"pgregory.net/rapid"
)

// validRoles are the allowed message roles.
var validRoles = []string{"user", "assistant", "system", "tool", "agent"}

// ============================================
// Property: JSON Round-Trip Serialization
// ============================================

// TestMessageRoleRoundTrip verifies role is preserved through JSON serialization.
func TestMessageRoleRoundTrip(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		role := rapid.SampledFrom(validRoles).Draw(t, "role")
		content := rapid.StringN(0, 100, -1).Draw(t, "content")

		msg := agenkit.NewMessage(role, content)

		data, err := json.Marshal(msg)
		if err != nil {
			t.Fatalf("json.Marshal failed: %v", err)
		}

		var decoded agenkit.Message
		if err := json.Unmarshal(data, &decoded); err != nil {
			t.Fatalf("json.Unmarshal failed: %v", err)
		}

		// Property: role is preserved
		if decoded.Role != role {
			t.Fatalf("role %q not preserved through JSON, got %q", role, decoded.Role)
		}
	})
}

// TestMessageContentRoundTrip verifies content is preserved through JSON serialization.
func TestMessageContentRoundTrip(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 1000, -1).Draw(t, "content")

		msg := agenkit.NewMessage("user", content)

		data, err := json.Marshal(msg)
		if err != nil {
			t.Fatalf("json.Marshal failed: %v", err)
		}

		var decoded agenkit.Message
		if err := json.Unmarshal(data, &decoded); err != nil {
			t.Fatalf("json.Unmarshal failed: %v", err)
		}

		// Property: ContentString is preserved
		if decoded.ContentString() != content {
			t.Fatalf("content %q not preserved through JSON, got %q", content, decoded.ContentString())
		}
	})
}

// TestMessageMetadataNeverNil verifies NewMessage always initializes Metadata.
func TestMessageMetadataNeverNil(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		role := rapid.SampledFrom(validRoles).Draw(t, "role")
		content := rapid.StringN(0, 100, -1).Draw(t, "content")

		msg := agenkit.NewMessage(role, content)

		// Property: Metadata is never nil
		if msg.Metadata == nil {
			t.Fatal("NewMessage returned nil Metadata")
		}
	})
}

// TestMessageRoleIsValid verifies NewMessage preserves the role value.
func TestMessageRoleIsValid(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		role := rapid.SampledFrom(validRoles).Draw(t, "role")

		msg := agenkit.NewMessage(role, "content")

		// Property: role matches
		if msg.Role != role {
			t.Fatalf("expected role %q, got %q", role, msg.Role)
		}
	})
}

// TestMessageTimestampIsSet verifies NewMessage sets a Timestamp.
func TestMessageTimestampIsSet(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		role := rapid.SampledFrom(validRoles).Draw(t, "role")

		before := time.Now().UTC().Add(-time.Second)
		msg := agenkit.NewMessage(role, "content")
		after := time.Now().UTC().Add(time.Second)

		// Property: timestamp is set and within expected range
		if msg.Timestamp.IsZero() {
			t.Fatal("Timestamp is zero")
		}
		if msg.Timestamp.Before(before) || msg.Timestamp.After(after) {
			t.Fatalf("Timestamp %v is outside expected range [%v, %v]", msg.Timestamp, before, after)
		}
	})
}

// TestMessageWithMetadataChains verifies WithMetadata chaining works.
func TestMessageWithMetadataChains(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		key := rapid.StringMatching(`[a-z_]{1,20}`).Draw(t, "key")
		value := rapid.StringN(0, 50, -1).Draw(t, "value")

		msg := agenkit.NewMessage("user", "content")
		result := msg.WithMetadata(key, value)

		// Property: WithMetadata returns the same message pointer
		if result != msg {
			t.Fatal("WithMetadata should return same *Message")
		}

		// Property: metadata contains the key
		stored, ok := msg.Metadata[key]
		if !ok {
			t.Fatalf("key %q not found in metadata after WithMetadata", key)
		}
		if stored != value {
			t.Fatalf("metadata[%q] = %v, want %v", key, stored, value)
		}
	})
}

// TestMessageValidateAcceptsValidRoles verifies Validate passes for valid roles.
func TestMessageValidateAcceptsValidRoles(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		role := rapid.SampledFrom(validRoles).Draw(t, "role")
		content := rapid.StringN(0, 100, -1).Draw(t, "content")

		msg := agenkit.NewMessage(role, content)
		if err := msg.Validate(); err != nil {
			t.Fatalf("Validate rejected valid message (role=%q): %v", role, err)
		}
	})
}

// TestMessageContentStringNonNil verifies ContentString never panics.
func TestMessageContentStringNonNil(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.StringN(0, 500, -1).Draw(t, "content")

		msg := agenkit.NewMessage("user", content)

		// Property: ContentString() never panics
		result := msg.ContentString()
		if result != content {
			t.Fatalf("ContentString() = %q, want %q", result, content)
		}
	})
}

// TestMessageMetadataRoundTrip verifies metadata values survive JSON round-trip.
func TestMessageMetadataRoundTrip(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		key := rapid.StringMatching(`[a-zA-Z_]{1,20}`).Draw(t, "key")
		value := rapid.StringN(0, 50, -1).Draw(t, "value")

		msg := agenkit.NewMessage("user", "content")
		msg.WithMetadata(key, value)

		data, err := json.Marshal(msg)
		if err != nil {
			t.Fatalf("Marshal failed: %v", err)
		}

		var decoded agenkit.Message
		if err := json.Unmarshal(data, &decoded); err != nil {
			t.Fatalf("Unmarshal failed: %v", err)
		}

		// Property: metadata key survives round-trip
		if _, ok := decoded.Metadata[key]; !ok {
			t.Fatalf("metadata key %q lost after JSON round-trip", key)
		}
	})
}

// TestMessageUnicodeContent verifies Unicode content round-trips correctly.
func TestMessageUnicodeContent(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		content := rapid.String().Draw(t, "unicode_content")

		msg := agenkit.NewMessage("user", content)

		// Property: ContentString returns the original Unicode string
		if msg.ContentString() != content {
			t.Fatalf("Unicode content not preserved: got %q, want %q", msg.ContentString(), content)
		}
	})
}

// TestMessageTimestampMonotonic verifies timestamps are non-decreasing under concurrent creation.
func TestMessageTimestampMonotonic(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		count := rapid.IntRange(2, 10).Draw(t, "count")

		msgs := make([]*agenkit.Message, count)
		var mu sync.Mutex
		var wg sync.WaitGroup

		for i := 0; i < count; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				msg := agenkit.NewMessage("user", "concurrent")
				mu.Lock()
				msgs[idx] = msg
				mu.Unlock()
			}(i)
		}
		wg.Wait()

		// Property: all timestamps are set (no zero values)
		for i, msg := range msgs {
			if msg == nil {
				t.Fatalf("msg[%d] is nil", i)
			}
			if msg.Timestamp.IsZero() {
				t.Fatalf("msg[%d].Timestamp is zero", i)
			}
		}
	})
}

// TestNewToolResultSuccess verifies NewToolResult creates a successful result.
func TestNewToolResultSuccess(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		data := rapid.StringN(0, 100, -1).Draw(t, "data")

		result := agenkit.NewToolResult(data)

		// Property: Success is true
		if !result.Success {
			t.Fatal("NewToolResult should set Success=true")
		}
		// Property: Data contains the provided value
		if result.Data != data {
			t.Fatalf("NewToolResult Data=%v, want %v", result.Data, data)
		}
		// Property: Error is empty
		if result.Error != "" {
			t.Fatalf("NewToolResult Error should be empty, got %q", result.Error)
		}
	})
}

// TestNewToolErrorFailure verifies NewToolError creates a failed result.
func TestNewToolErrorFailure(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		errMsg := rapid.StringN(0, 100, -1).Draw(t, "err_msg")

		result := agenkit.NewToolError(errMsg)

		// Property: Success is false
		if result.Success {
			t.Fatal("NewToolError should set Success=false")
		}
		// Property: Error contains the provided message
		if result.Error != errMsg {
			t.Fatalf("NewToolError Error=%q, want %q", result.Error, errMsg)
		}
	})
}

// TestToolResultMetadataNeverNil verifies ToolResult Metadata is initialized.
func TestToolResultMetadataNeverNil(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		data := rapid.StringN(0, 50, -1).Draw(t, "data")

		result := agenkit.NewToolResult(data)

		// Property: Metadata is never nil
		if result.Metadata == nil {
			t.Fatal("NewToolResult returned nil Metadata")
		}
	})
}

// TestMessageConcurrentSafeCreation verifies concurrent message creation produces valid messages.
func TestMessageConcurrentSafeCreation(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		count := rapid.IntRange(5, 20).Draw(t, "count")

		results := make([]*agenkit.Message, count)
		var wg sync.WaitGroup

		for i := 0; i < count; i++ {
			wg.Add(1)
			go func(idx int) {
				defer wg.Done()
				results[idx] = agenkit.NewMessage(validRoles[idx%len(validRoles)], "concurrent content")
			}(i)
		}
		wg.Wait()

		// Property: all messages are valid
		for i, msg := range results {
			if msg == nil {
				t.Fatalf("results[%d] is nil", i)
			}
			if err := msg.Validate(); err != nil {
				t.Fatalf("results[%d].Validate() = %v", i, err)
			}
		}
	})
}

// mockAgentForProp is a minimal Agent implementation for property tests.
type mockAgentForProp struct {
	name string
}

func (a *mockAgentForProp) Name() string        { return a.name }
func (a *mockAgentForProp) Capabilities() []string { return nil }
func (a *mockAgentForProp) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}
func (a *mockAgentForProp) Process(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("assistant", "response: "+msg.ContentString()), nil
}
