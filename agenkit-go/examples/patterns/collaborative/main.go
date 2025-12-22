// Package main demonstrates the Collaborative pattern for peer collaboration.
//
// The Collaborative pattern enables multiple agents to work together
// iteratively, each contributing their perspective and refining the
// collective output through multiple rounds until consensus is reached.
//
// This example shows:
//   - Iterative peer-to-peer collaboration
//   - Consensus detection strategies
//   - Result merging approaches
//   - Code review and document editing workflows
//
// Run with: go run collaborative_pattern.go
package main

import (
	"context"
	"fmt"
	"log"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/patterns"
)

// EditorAgent provides editorial feedback
type EditorAgent struct {
	name  string
	focus string
}

func (e *EditorAgent) Name() string {
	return e.name
}

func (e *EditorAgent) Capabilities() []string {
	return []string{"editing", "review", e.focus}
}

func (e *EditorAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    e.Name(),
		Capabilities: e.Capabilities(),
	}
}

func (e *EditorAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   📝 %s reviewing...\n", e.name)

	// Extract round from message if present
	round := 0
	content := message.Content
	if strings.Contains(content, "Round") {
		_, _ = fmt.Sscanf(content, "=== Collaboration Round %d ===", &round)
	}

	var feedback string
	switch e.focus {
	case "grammar":
		if round == 0 {
			feedback = "Grammar Review: Good structure overall. Suggest improving punctuation and tense consistency."
		} else {
			feedback = "Grammar Review: Improvements applied. Text now has consistent punctuation and tense. Approved."
		}
	case "clarity":
		if round == 0 {
			feedback = "Clarity Review: Some sentences are complex. Recommend simplification for better readability."
		} else {
			feedback = "Clarity Review: Much clearer now. Sentences are concise and easy to understand. Approved."
		}
	case "style":
		if round == 0 {
			feedback = "Style Review: Tone is appropriate but could be more engaging. Add more active voice."
		} else {
			feedback = "Style Review: Excellent improvements. Active voice makes the text more engaging. Approved."
		}
	}

	return agenkit.NewMessage("agent", feedback), nil
}

// CodeReviewerAgent reviews code
type CodeReviewerAgent struct {
	name      string
	expertise string
}

func (c *CodeReviewerAgent) Name() string {
	return c.name
}

func (c *CodeReviewerAgent) Capabilities() []string {
	return []string{"code-review", c.expertise}
}

func (c *CodeReviewerAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    c.Name(),
		Capabilities: c.Capabilities(),
	}
}

func (c *CodeReviewerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   👨‍💻 %s reviewing...\n", c.name)

	// Simulate review based on round
	round := 0
	if strings.Contains(message.Content, "Round") {
		_, _ = fmt.Sscanf(message.Content, "=== Collaboration Round %d ===", &round)
	}

	var review string
	switch c.expertise {
	case "security":
		if round == 0 {
			review = "Security Review: Found potential SQL injection vulnerability. Input validation needed."
		} else {
			review = "Security Review: Input validation added. No security issues found. LGTM."
		}
	case "performance":
		if round == 0 {
			review = "Performance Review: O(n²) algorithm detected. Consider using hash map for O(n)."
		} else {
			review = "Performance Review: Optimized to O(n). Good improvement. LGTM."
		}
	case "testing":
		if round == 0 {
			review = "Testing Review: Coverage at 60%. Need tests for edge cases and error paths."
		} else {
			review = "Testing Review: Coverage improved to 95%. Comprehensive test suite. LGTM."
		}
	}

	return agenkit.NewMessage("agent", review), nil
}

// AnalystAgent provides analysis
type AnalystAgent struct {
	name        string
	perspective string
	approved    bool
}

func (a *AnalystAgent) Name() string {
	return a.name
}

func (a *AnalystAgent) Capabilities() []string {
	return []string{"analysis", a.perspective}
}

func (a *AnalystAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *AnalystAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	fmt.Printf("   🔍 %s analyzing...\n", a.name)

	var analysis string
	if !a.approved {
		analysis = fmt.Sprintf("%s Analysis: Initial review shows room for improvement. Key issues identified.", a.perspective)
		a.approved = true // Approve in next round
	} else {
		analysis = fmt.Sprintf("%s Analysis: All issues addressed. Ready for approval. ✅", a.perspective)
	}

	return agenkit.NewMessage("agent", analysis), nil
}

func main() {
	fmt.Println("=== Collaborative Pattern Demo ===")
	fmt.Println("Demonstrating peer-to-peer agent collaboration")

	ctx := context.Background()

	// Example 1: Document editing with consensus
	fmt.Println("📊 Example 1: Collaborative Document Editing")
	fmt.Println(strings.Repeat("-", 50))

	editors := []agenkit.Agent{
		&EditorAgent{name: "GrammarEditor", focus: "grammar"},
		&EditorAgent{name: "ClarityEditor", focus: "clarity"},
		&EditorAgent{name: "StyleEditor", focus: "style"},
	}

	// Create collaborative agent with consensus detection
	editTeam, err := patterns.NewCollaborativeAgent(&patterns.CollaborativeConfig{
		Agents:        editors,
		MaxRounds:     3,
		ConsensusFunc: patterns.DefaultConsensusFunc.MajorityAgreement,
		MergeFunc:     patterns.DefaultMergeFunc.Concatenate,
	})
	if err != nil {
		log.Fatalf("Failed to create edit team: %v", err)
	}

	document := agenkit.NewMessage("user",
		"Document to review: The team should be implementing the feature quickly.")

	fmt.Printf("\n📥 Document: %s\n", document.Content)
	fmt.Println("\nStarting collaborative editing with 3 editors...")

	result, err := editTeam.Process(ctx, document)
	if err != nil {
		log.Fatalf("Collaboration failed: %v", err)
	}

	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📤 Collaborative Review Result:")
	fmt.Println(result.Content)

	// Display collaboration metadata
	if rounds, ok := result.Metadata["collaboration_rounds"].(int); ok {
		fmt.Printf("\nCollaboration Metrics:\n")
		fmt.Printf("  Rounds: %d\n", rounds)
	}
	if agents, ok := result.Metadata["collaboration_agents"].(int); ok {
		fmt.Printf("  Agents: %d\n", agents)
	}
	if reason, ok := result.Metadata["stop_reason"].(string); ok {
		fmt.Printf("  Stop reason: %s\n", reason)
	}

	// Example 2: Code review until approval
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 2: Collaborative Code Review")
	fmt.Println(strings.Repeat("-", 50))

	reviewers := []agenkit.Agent{
		&CodeReviewerAgent{name: "SecurityReviewer", expertise: "security"},
		&CodeReviewerAgent{name: "PerformanceReviewer", expertise: "performance"},
		&CodeReviewerAgent{name: "TestingReviewer", expertise: "testing"},
	}

	// Custom consensus: all reviews must contain "LGTM"
	reviewConsensus := func(messages []*agenkit.Message) bool {
		for _, msg := range messages {
			if !strings.Contains(msg.Content, "LGTM") {
				return false
			}
		}
		return true
	}

	reviewTeam, err := patterns.NewCollaborativeAgent(&patterns.CollaborativeConfig{
		Agents:        reviewers,
		MaxRounds:     3,
		ConsensusFunc: reviewConsensus,
		MergeFunc:     patterns.DefaultMergeFunc.Concatenate,
	})
	if err != nil {
		log.Fatalf("Failed to create review team: %v", err)
	}

	codeSubmission := agenkit.NewMessage("user",
		"Code PR #123: New feature implementation ready for review")

	fmt.Printf("\n📥 Submission: %s\n", codeSubmission.Content)
	fmt.Println("\nStarting collaborative code review...")

	result, err = reviewTeam.Process(ctx, codeSubmission)
	if err != nil {
		log.Fatalf("Code review failed: %v", err)
	}

	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📤 Code Review Result:")
	fmt.Println(result.Content)

	if reason, ok := result.Metadata["stop_reason"].(string); ok {
		fmt.Printf("\nStatus: %s\n", reason)
	}

	// Example 3: Voting merge strategy
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 3: Voting-Based Collaboration")
	fmt.Println(strings.Repeat("-", 50))

	// Create agents with predefined opinions
	voters := []agenkit.Agent{
		&OpinionAgent{name: "Agent1", opinion: "Approve"},
		&OpinionAgent{name: "Agent2", opinion: "Approve"},
		&OpinionAgent{name: "Agent3", opinion: "Reject"},
		&OpinionAgent{name: "Agent4", opinion: "Approve"},
		&OpinionAgent{name: "Agent5", opinion: "Reject"},
	}

	votingTeam, err := patterns.NewCollaborativeAgent(&patterns.CollaborativeConfig{
		Agents:    voters,
		MaxRounds: 1, // Single round for voting
		MergeFunc: patterns.DefaultMergeFunc.Vote,
	})
	if err != nil {
		log.Fatalf("Failed to create voting team: %v", err)
	}

	proposal := agenkit.NewMessage("user", "Proposal: Adopt new development framework")

	fmt.Printf("\n📥 Proposal: %s\n", proposal.Content)
	fmt.Println("\nCollecting votes from 5 agents...")

	result, err = votingTeam.Process(ctx, proposal)
	if err != nil {
		log.Fatalf("Voting failed: %v", err)
	}

	fmt.Printf("\n📤 Voting Result: %s\n", result.Content)

	if votes, ok := result.Metadata["votes"].(int); ok {
		if total, ok := result.Metadata["total"].(int); ok {
			fmt.Printf("   Votes: %d/%d\n", votes, total)
		}
	}

	// Example 4: Max rounds without consensus
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 4: Maximum Rounds Limit")
	fmt.Println(strings.Repeat("-", 50))

	// Create agents that never agree
	disagreers := []agenkit.Agent{
		&AnalystAgent{name: "Analyst1", perspective: "Financial", approved: false},
		&AnalystAgent{name: "Analyst2", perspective: "Technical", approved: false},
		&AnalystAgent{name: "Analyst3", perspective: "Legal", approved: false},
	}

	// Consensus requires exact match (which won't happen)
	limitedTeam, err := patterns.NewCollaborativeAgent(&patterns.CollaborativeConfig{
		Agents:        disagreers,
		MaxRounds:     2,
		ConsensusFunc: patterns.DefaultConsensusFunc.ExactMatch,
		MergeFunc:     patterns.DefaultMergeFunc.Last,
	})
	if err != nil {
		log.Fatalf("Failed to create limited team: %v", err)
	}

	decision := agenkit.NewMessage("user", "Decision required: Proceed with acquisition?")

	fmt.Printf("\n📥 Decision: %s\n", decision.Content)
	fmt.Println("\nCollaborating until consensus or max rounds...")

	result, err = limitedTeam.Process(ctx, decision)
	if err != nil {
		log.Fatalf("Collaboration failed: %v", err)
	}

	fmt.Println("\n📤 Result (max rounds reached):")
	fmt.Println(result.Content)

	if rounds, ok := result.Metadata["collaboration_rounds"].(int); ok {
		fmt.Printf("\nCompleted %d rounds without full consensus\n", rounds)
	}

	// Example 5: Custom merge strategy
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("\n📊 Example 5: Custom Merge Strategy")
	fmt.Println(strings.Repeat("-", 50))

	// Custom merge that creates a summary
	customMerge := func(messages []*agenkit.Message) *agenkit.Message {
		var summary strings.Builder
		summary.WriteString("Collaboration Summary:\n\n")

		approvals := 0
		rejections := 0

		for i, msg := range messages {
			summary.WriteString(fmt.Sprintf("%d. %s\n", i+1, msg.Content))

			if strings.Contains(msg.Content, "Approved") || strings.Contains(msg.Content, "LGTM") {
				approvals++
			} else {
				rejections++
			}
		}

		summary.WriteString(fmt.Sprintf("\nTally: %d approvals, %d issues\n", approvals, rejections))

		if approvals > rejections {
			summary.WriteString("Decision: APPROVED ✅")
		} else {
			summary.WriteString("Decision: NEEDS WORK ⚠️")
		}

		return agenkit.NewMessage("agent", summary.String())
	}

	customTeam, err := patterns.NewCollaborativeAgent(&patterns.CollaborativeConfig{
		Agents:    reviewers,
		MaxRounds: 2,
		MergeFunc: customMerge,
	})
	if err != nil {
		log.Fatalf("Failed to create custom team: %v", err)
	}

	review := agenkit.NewMessage("user", "Final review of completed work")

	fmt.Printf("\n📥 Review: %s\n", review.Content)

	result, err = customTeam.Process(ctx, review)
	if err != nil {
		log.Fatalf("Custom collaboration failed: %v", err)
	}

	fmt.Println("\n📤 Custom Merge Result:")
	fmt.Println(result.Content)

	fmt.Println("\n✅ Collaborative pattern demo complete!")
}

// OpinionAgent has a fixed opinion
type OpinionAgent struct {
	name    string
	opinion string
}

func (o *OpinionAgent) Name() string {
	return o.name
}

func (o *OpinionAgent) Capabilities() []string {
	return []string{"opinion"}
}

func (o *OpinionAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    o.Name(),
		Capabilities: o.Capabilities(),
	}
}

func (o *OpinionAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	return agenkit.NewMessage("agent", o.opinion), nil
}
