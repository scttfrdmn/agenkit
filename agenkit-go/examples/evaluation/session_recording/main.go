// Package main demonstrates session recording and replay for evaluation.
//
// Session recording captures all agent interactions (inputs, outputs, timing)
// for later replay, analysis, and A/B testing. This is essential for:
//   - Debugging agent behavior
//   - Comparing different agent versions
//   - Reproducing issues
//   - Building regression test suites
//   - Analyzing conversation patterns
//
// Run with: go run session_recording_example.go
package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// MockAgent is a simple agent for demonstration.
type MockAgent struct {
	name    string
	version string
}

func (a *MockAgent) Name() string {
	return a.name
}

func (a *MockAgent) Capabilities() []string {
	return []string{"chat"}
}

func (a *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simple echo agent with version-specific behavior
	response := fmt.Sprintf("[%s] You said: %s", a.version, message.Content)

	return &agenkit.Message{
		Role:    "assistant",
		Content: response,
	}, nil
}

func main() {
	fmt.Println("Session Recording and Replay Example")
	fmt.Println("=====================================")

	// Step 1: Create recorder with file storage
	fmt.Println("Step 1: Setting Up Session Recorder")
	fmt.Println("------------------------------------")
	storage := evaluation.NewFileRecordingStorage("./recordings")
	recorder := evaluation.NewSessionRecorder(storage)
	fmt.Println("✓ Recorder created with file storage: ./recordings/")

	// Step 2: Create agent and wrap with recorder
	fmt.Println("Step 2: Creating and Wrapping Agent")
	fmt.Println("------------------------------------")
	agentV1 := &MockAgent{name: "echo-agent", version: "v1"}
	wrappedAgent := recorder.Wrap(agentV1)
	fmt.Println("✓ Agent wrapped with recorder")

	// Step 3: Record a session
	fmt.Println("Step 3: Recording Agent Session")
	fmt.Println("--------------------------------")
	sessionID := "demo-session-001"

	interactions := []string{
		"Hello, how are you?",
		"What's the weather like today?",
		"Tell me a joke",
		"Thank you!",
	}

	fmt.Printf("Recording session: %s\n", sessionID)
	fmt.Println("Interactions:")
	for i, input := range interactions {
		message := &agenkit.Message{
			Role:    "user",
			Content: input,
			Metadata: map[string]interface{}{
				"session_id": sessionID,
			},
		}

		response, err := wrappedAgent.Process(context.Background(), message)
		if err != nil {
			fmt.Printf("  Error: %v\n", err)
			continue
		}

		fmt.Printf("  %d. User: %s\n", i+1, input)
		fmt.Printf("     Agent: %s\n", response.Content)
	}
	fmt.Println()

	// Step 4: Finalize and save recording
	fmt.Println("Step 4: Finalizing Recording")
	fmt.Println("-----------------------------")
	recording, err := recorder.FinalizeSession(sessionID)
	if err != nil {
		fmt.Printf("Error finalizing: %v\n", err)
		return
	}

	fmt.Printf("✓ Session recorded: %s\n", recording.SessionID)
	fmt.Printf("  Interactions: %d\n", recording.InteractionCount())
	fmt.Printf("  Duration: %.2fs\n", recording.DurationSeconds())
	fmt.Printf("  Total Latency: %.0fms\n\n", recording.TotalLatencyMs())

	// Step 5: Load and replay session
	fmt.Println("Step 5: Loading and Replaying Session")
	fmt.Println("--------------------------------------")
	loadedRecording, err := recorder.LoadRecording(sessionID)
	if err != nil {
		fmt.Printf("Error loading: %v\n", err)
		return
	}

	if loadedRecording == nil {
		fmt.Println("Recording not found")
		return
	}

	fmt.Printf("✓ Loaded recording: %s\n", loadedRecording.SessionID)
	fmt.Printf("  Agent: %s\n", loadedRecording.AgentName)
	fmt.Printf("  Interactions: %d\n\n", len(loadedRecording.Interactions))

	// Replay with original agent
	replay := evaluation.NewSessionReplay()
	fmt.Println("Replaying with original agent (v1)...")
	resultsV1, err := replay.Replay(loadedRecording, agentV1, "")
	if err != nil {
		fmt.Printf("Error replaying: %v\n", err)
		return
	}

	fmt.Printf("✓ Replay complete\n")
	fmt.Printf("  Total Latency: %.0fms\n", resultsV1["total_latency_ms"])
	fmt.Printf("  Errors: %d\n\n", resultsV1["error_count"])

	// Step 6: Replay with different agent version (A/B testing)
	fmt.Println("Step 6: A/B Testing with Different Agent Version")
	fmt.Println("-------------------------------------------------")
	agentV2 := &MockAgent{name: "echo-agent", version: "v2"}

	fmt.Println("Replaying with new agent version (v2)...")
	resultsV2, err := replay.Replay(loadedRecording, agentV2, "")
	if err != nil {
		fmt.Printf("Error replaying: %v\n", err)
		return
	}

	fmt.Printf("✓ Replay complete\n")
	fmt.Printf("  Total Latency: %.0fms\n", resultsV2["total_latency_ms"])
	fmt.Printf("  Errors: %d\n\n", resultsV2["error_count"])

	// Step 7: Compare results
	fmt.Println("Step 7: Comparing Results")
	fmt.Println("-------------------------")
	comparison := replay.Compare(resultsV1, resultsV2)

	fmt.Printf("Comparison:\n")
	fmt.Printf("  Interactions: %d\n", comparison["interaction_count"])
	fmt.Printf("  Latency Difference: %.0fms (%.1f%%)\n",
		comparison["latency_diff_ms"],
		comparison["latency_diff_percent"])
	fmt.Printf("  Error Difference: %d\n", comparison["error_diff"])

	outputDiffs := comparison["output_differences"].([]map[string]interface{})
	fmt.Printf("  Output Differences: %d\n", len(outputDiffs))

	if len(outputDiffs) > 0 {
		fmt.Println("\nDetailed Output Differences:")
		for _, diff := range outputDiffs {
			idx := diff["interaction_index"].(int)
			outputA := diff["output_a"].(string)
			outputB := diff["output_b"].(string)
			fmt.Printf("  Interaction %d:\n", idx+1)
			fmt.Printf("    v1: %s\n", outputA)
			fmt.Printf("    v2: %s\n", outputB)
		}
	}
	fmt.Println()

	// Step 8: List all recordings
	fmt.Println("Step 8: Listing All Recordings")
	fmt.Println("-------------------------------")
	recordings, err := recorder.ListRecordings(10, 0)
	if err != nil {
		fmt.Printf("Error listing: %v\n", err)
		return
	}

	fmt.Printf("Found %d recordings:\n", len(recordings))
	for i, rec := range recordings {
		fmt.Printf("  %d. %s (%s)\n", i+1, rec.SessionID, rec.AgentName)
		fmt.Printf("     Interactions: %d, Duration: %.2fs\n",
			rec.InteractionCount(), rec.DurationSeconds())
	}
	fmt.Println()

	// Summary
	fmt.Println(strings.Repeat("=", 70))
	fmt.Println("Summary: Session Recording and Replay")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nKey Capabilities:")
	fmt.Println("1. Record: Capture all agent interactions automatically")
	fmt.Println("2. Store: Save to file, memory, or custom storage backend")
	fmt.Println("3. Replay: Re-run recorded sessions through any agent")
	fmt.Println("4. Compare: A/B test different agent versions")
	fmt.Println("5. Analyze: Inspect timing, outputs, and errors")

	fmt.Println("\nStorage Backends:")
	fmt.Println("- FileRecordingStorage: JSON files on disk (production)")
	fmt.Println("- InMemoryRecordingStorage: In-memory (testing)")
	fmt.Println("- Custom: Implement RecordingStorage interface (Redis, S3, etc.)")

	fmt.Println("\nRecording Details:")
	fmt.Println("- Session ID: Unique identifier for grouping interactions")
	fmt.Println("- Interactions: Input message, output message, latency")
	fmt.Println("- Metadata: Custom key-value pairs per session/interaction")
	fmt.Println("- Timestamps: RFC3339 format for precise timing")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Wrap agents early in development lifecycle")
	fmt.Println("2. Use descriptive session IDs (e.g., user-id-timestamp)")
	fmt.Println("3. Finalize sessions promptly to free memory")
	fmt.Println("4. Store recordings in version control as regression tests")
	fmt.Println("5. Replay after every code change to detect regressions")
	fmt.Println("6. Use metadata to tag recordings (version, feature, user)")

	fmt.Println("\nReal-World Applications:")
	fmt.Println("- Debugging: Reproduce exact user interaction that caused error")
	fmt.Println("- Regression Testing: Verify new code doesn't break old sessions")
	fmt.Println("- A/B Testing: Compare agent versions on identical inputs")
	fmt.Println("- Quality Assurance: Review agent responses before deployment")
	fmt.Println("- Training: Build datasets from production interactions")
	fmt.Println("- Compliance: Audit trail of all agent interactions")

	fmt.Println("\nPerformance:")
	fmt.Println("- Overhead: <1ms per interaction for recording")
	fmt.Println("- Storage: ~1KB per interaction (JSON)")
	fmt.Println("- Replay: Same speed as original (can be parallelized)")
	fmt.Println("- Thread-safe: Safe for concurrent recording")
}
