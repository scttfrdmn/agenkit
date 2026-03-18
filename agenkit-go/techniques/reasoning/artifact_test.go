package reasoning

import (
	"context"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/memory"
)

// mockReasoningMemory is a test double for memory.ReasoningMemory.
type mockReasoningMemory struct {
	stored    []agenkit.ReasoningArtifact
	retrieved map[string][]agenkit.ReasoningArtifact
}

func newMockReasoningMemory() *mockReasoningMemory {
	return &mockReasoningMemory{
		retrieved: make(map[string][]agenkit.ReasoningArtifact),
	}
}

func (m *mockReasoningMemory) Store(_ context.Context, _ string, _ agenkit.Message, _ map[string]interface{}) error {
	return nil
}

func (m *mockReasoningMemory) Retrieve(_ context.Context, _ string, _ memory.RetrieveOptions) ([]agenkit.Message, error) {
	return nil, nil
}

func (m *mockReasoningMemory) Summarize(_ context.Context, _ string, _ memory.SummarizeOptions) (agenkit.Message, error) {
	return agenkit.Message{}, nil
}

func (m *mockReasoningMemory) Clear(_ context.Context, _ string) error {
	return nil
}

func (m *mockReasoningMemory) Capabilities() []string {
	return []string{"basic_retrieval", "reasoning_artifacts"}
}

func (m *mockReasoningMemory) StoreArtifact(_ context.Context, _ string, artifact agenkit.ReasoningArtifact) error {
	m.stored = append(m.stored, artifact)
	return nil
}

func (m *mockReasoningMemory) RetrieveArtifacts(_ context.Context, _ string, technique string) ([]agenkit.ReasoningArtifact, error) {
	return m.retrieved[technique], nil
}

// mockVerifier is a test double for agenkit.Verifier.
type mockVerifier struct {
	result agenkit.VerificationResult
	err    error
}

func (v *mockVerifier) Verify(_ context.Context, _, _ string) (agenkit.VerificationResult, error) {
	return v.result, v.err
}

// TestArtifactTechnique verifies the Technique() accessor.
func TestArtifactTechnique(t *testing.T) {
	a := newArtifact("tree_of_thought", "s1", nil, nil)
	if a.Technique() != "tree_of_thought" {
		t.Errorf("expected technique='tree_of_thought', got=%q", a.Technique())
	}
}

// TestArtifactSessionID verifies the SessionID() accessor.
func TestArtifactSessionID(t *testing.T) {
	a := newArtifact("chain_of_thought", "session-42", nil, nil)
	if a.SessionID() != "session-42" {
		t.Errorf("expected sessionID='session-42', got=%q", a.SessionID())
	}
}

// TestArtifactCandidates verifies that Candidates() returns a copy of the input slice.
func TestArtifactCandidates(t *testing.T) {
	input := []agenkit.ScoredCandidate{
		{Text: "alpha", Score: 0.9},
		{Text: "beta", Score: 0.7},
	}
	a := newArtifact("self_consistency", "", input, nil)
	got := a.Candidates()
	if len(got) != 2 {
		t.Fatalf("expected 2 candidates, got %d", len(got))
	}
	if got[0].Text != "alpha" || got[0].Score != 0.9 {
		t.Errorf("unexpected candidate[0]: %+v", got[0])
	}
	if got[1].Text != "beta" || got[1].Score != 0.7 {
		t.Errorf("unexpected candidate[1]: %+v", got[1])
	}
}

// TestArtifactBestCandidate verifies that BestCandidate() returns the highest-scoring entry.
func TestArtifactBestCandidate(t *testing.T) {
	candidates := []agenkit.ScoredCandidate{
		{Text: "low", Score: 0.3},
		{Text: "high", Score: 0.95},
		{Text: "mid", Score: 0.6},
	}
	a := newArtifact("graph_of_thought", "", candidates, nil)
	best := a.BestCandidate()
	if best.Text != "high" || best.Score != 0.95 {
		t.Errorf("expected best={high,0.95}, got=%+v", best)
	}
}

// TestArtifactBestCandidateEmpty verifies that BestCandidate() returns a zero value when empty.
func TestArtifactBestCandidateEmpty(t *testing.T) {
	a := newArtifact("tree_of_thought", "", nil, nil)
	best := a.BestCandidate()
	if best.Text != "" || best.Score != 0.0 {
		t.Errorf("expected zero ScoredCandidate for empty slice, got=%+v", best)
	}
}

// TestArtifactMetadata verifies that Metadata() returns the provided map.
func TestArtifactMetadata(t *testing.T) {
	meta := map[string]interface{}{"key": "value", "count": 3}
	a := newArtifact("tree_of_thought", "", nil, meta)
	got := a.Metadata()
	if got["key"] != "value" {
		t.Errorf("expected metadata key='value', got=%v", got["key"])
	}
	if got["count"] != 3 {
		t.Errorf("expected metadata count=3, got=%v", got["count"])
	}
}

// TestArtifactNilMetadataDefaults verifies nil meta is initialised to an empty map.
func TestArtifactNilMetadataDefaults(t *testing.T) {
	a := newArtifact("chain_of_thought", "", nil, nil)
	if a.Metadata() == nil {
		t.Error("expected non-nil metadata map when nil was passed")
	}
}

// TestReasoningMemoryInterface is a compile-time check: mockReasoningMemory must satisfy
// memory.ReasoningMemory (which embeds memory.Memory).
func TestReasoningMemoryInterface(t *testing.T) {
	var _ memory.ReasoningMemory = (*mockReasoningMemory)(nil)
	t.Log("mockReasoningMemory satisfies memory.ReasoningMemory")
}
