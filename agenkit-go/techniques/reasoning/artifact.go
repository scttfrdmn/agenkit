// Package reasoning provides reasoning techniques for AI agents.
package reasoning

import (
	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// reasoningArtifact implements agenkit.ReasoningArtifact.
type reasoningArtifact struct {
	technique  string
	sessionID  string
	candidates []agenkit.ScoredCandidate
	metadata   map[string]interface{}
}

// newArtifact creates a new reasoningArtifact.
func newArtifact(technique, sessionID string, candidates []agenkit.ScoredCandidate, meta map[string]interface{}) agenkit.ReasoningArtifact {
	if meta == nil {
		meta = make(map[string]interface{})
	}
	copied := make([]agenkit.ScoredCandidate, len(candidates))
	copy(copied, candidates)
	return &reasoningArtifact{
		technique:  technique,
		sessionID:  sessionID,
		candidates: copied,
		metadata:   meta,
	}
}

// Technique returns the reasoning technique name.
func (a *reasoningArtifact) Technique() string {
	return a.technique
}

// SessionID returns the session identifier.
func (a *reasoningArtifact) SessionID() string {
	return a.sessionID
}

// Candidates returns all scored candidates.
func (a *reasoningArtifact) Candidates() []agenkit.ScoredCandidate {
	return a.candidates
}

// BestCandidate returns the candidate with the highest score.
// Returns a zero-value ScoredCandidate if there are no candidates.
func (a *reasoningArtifact) BestCandidate() agenkit.ScoredCandidate {
	if len(a.candidates) == 0 {
		return agenkit.ScoredCandidate{}
	}
	best := a.candidates[0]
	for _, c := range a.candidates[1:] {
		if c.Score > best.Score {
			best = c
		}
	}
	return best
}

// Metadata returns the artifact metadata map.
func (a *reasoningArtifact) Metadata() map[string]interface{} {
	return a.metadata
}
