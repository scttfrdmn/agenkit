// Package main demonstrates A/B testing with the evaluation framework.
//
// A/B testing compares two versions of an agent on identical inputs
// to determine which performs better. This is essential for:
//   - Validating improvements before deployment
//   - Comparing different LLM models
//   - Testing prompt variations
//   - Evaluating configuration changes
//
// Run with: go run ab_testing_example.go
package main

import (
	"context"
	"fmt"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"github.com/scttfrdmn/agenkit/agenkit-go/evaluation"
)

// AgentV1 represents version 1 of the agent (current production)
type AgentV1 struct{}

func (a *AgentV1) Name() string {
	return "agent-v1"
}

func (a *AgentV1) Capabilities() []string {
	return []string{"qa"}
}

func (a *AgentV1) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *AgentV1) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simple responses
	query := strings.ToLower(message.Content)
	var response string

	if strings.Contains(query, "weather") {
		response = "I don't have access to weather information."
	} else if strings.Contains(query, "help") {
		response = "I can assist you with questions."
	} else {
		response = "I'll help you with that."
	}

	return &agenkit.Message{Role: "assistant", Content: response}, nil
}

// AgentV2 represents version 2 of the agent (new candidate)
type AgentV2 struct{}

func (a *AgentV2) Name() string {
	return "agent-v2"
}

func (a *AgentV2) Capabilities() []string {
	return []string{"qa"}
}

func (a *AgentV2) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    a.Name(),
		Capabilities: a.Capabilities(),
	}
}

func (a *AgentV2) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Improved responses with more detail
	query := strings.ToLower(message.Content)
	var response string

	if strings.Contains(query, "weather") {
		response = "I don't currently have access to real-time weather information. However, I recommend checking weather.com or your local weather service for the most accurate forecast."
	} else if strings.Contains(query, "help") {
		response = "I'd be happy to help! I can answer questions, provide information, and assist with various tasks. What would you like to know?"
	} else {
		response = "I'll be glad to assist you with that. Could you provide more details so I can give you the most helpful response?"
	}

	return &agenkit.Message{Role: "assistant", Content: response}, nil
}

func main() {
	fmt.Println("A/B Testing Example")
	fmt.Println("===================")

	// Step 1: Setup agents and test suite
	fmt.Println("Step 1: Setting Up A/B Test")
	fmt.Println("---------------------------")

	agentV1 := &AgentV1{}
	agentV2 := &AgentV2{}

	testCases := []map[string]interface{}{
		{"input": "What's the weather like today?"},
		{"input": "Can you help me?"},
		{"input": "I need assistance with my order"},
		{"input": "Tell me about your capabilities"},
		{"input": "How do I reset my password?"},
	}

	fmt.Printf("Agent A (Control): %s\n", agentV1.Name())
	fmt.Printf("Agent B (Variant): %s\n", agentV2.Name())
	fmt.Printf("Test Cases: %d\n\n", len(testCases))

	// Step 2: Record baseline session (V1)
	fmt.Println("Step 2: Recording Baseline Session (Agent V1)")
	fmt.Println("----------------------------------------------")

	recorderV1 := evaluation.NewSessionRecorder(nil)
	wrappedV1 := recorderV1.Wrap(agentV1)

	sessionID := "ab-test-session"
	for i, testCase := range testCases {
		input := testCase["input"].(string)
		message := &agenkit.Message{
			Role:    "user",
			Content: input,
			Metadata: map[string]interface{}{
				"session_id": sessionID,
			},
		}

		response, _ := wrappedV1.Process(context.Background(), message)
		fmt.Printf("  %d. Input: %s\n", i+1, input)
		fmt.Printf("     V1: %s\n", response.Content)
	}

	recordingV1, _ := recorderV1.FinalizeSession(sessionID)
	fmt.Printf("\n✓ Baseline recorded: %d interactions\n\n", len(recordingV1.Interactions))

	// Step 3: Replay with V2
	fmt.Println("Step 3: Replaying with Agent V2")
	fmt.Println("--------------------------------")

	replay := evaluation.NewSessionReplay()
	resultsV1, _ := replay.Replay(recordingV1, agentV1, "")
	resultsV2, _ := replay.Replay(recordingV1, agentV2, "")

	fmt.Println("Comparing outputs:")
	interactionsV1 := resultsV1["interactions"].([]map[string]interface{})
	interactionsV2 := resultsV2["interactions"].([]map[string]interface{})

	for i := 0; i < len(interactionsV1); i++ {
		outputV1 := interactionsV1[i]["replay_output"].(map[string]interface{})["content"].(string)
		outputV2 := interactionsV2[i]["replay_output"].(map[string]interface{})["content"].(string)

		input := interactionsV1[i]["input"].(map[string]interface{})["content"].(string)

		fmt.Printf("\n  %d. Input: %s\n", i+1, input)
		fmt.Printf("     V1: %s\n", outputV1)
		fmt.Printf("     V2: %s\n", outputV2)

		if len(outputV2) > len(outputV1) {
			improvement := float64(len(outputV2)-len(outputV1)) / float64(len(outputV1)) * 100
			fmt.Printf("     📈 V2 is %.0f%% longer (more detailed)\n", improvement)
		}
	}

	// Step 4: Compare metrics
	fmt.Println("\n\nStep 4: Comparing Performance Metrics")
	fmt.Println("--------------------------------------")
	comparison := replay.Compare(resultsV1, resultsV2)

	fmt.Printf("Interaction Count: %d\n", comparison["interaction_count"])
	fmt.Printf("Latency Difference: %.0fms (%.1f%%)\n",
		comparison["latency_diff_ms"],
		comparison["latency_diff_percent"])

	outputDiffs := comparison["output_differences"].([]map[string]interface{})
	fmt.Printf("Output Differences: %d/%d (%.0f%%)\n",
		len(outputDiffs),
		comparison["interaction_count"],
		float64(len(outputDiffs))/float64(comparison["interaction_count"].(int))*100)

	// Step 5: Quality evaluation
	fmt.Println("\n\nStep 5: Quality Evaluation")
	fmt.Println("--------------------------")

	qualityMetric := evaluation.NewQualityMetrics(false, "", nil)

	var totalQualityV1, totalQualityV2 float64
	for i := 0; i < len(testCases); i++ {
		inputMsg := &agenkit.Message{
			Role:    "user",
			Content: testCases[i]["input"].(string),
		}

		// V1 quality
		outputV1 := &agenkit.Message{
			Role:    "assistant",
			Content: interactionsV1[i]["replay_output"].(map[string]interface{})["content"].(string),
		}
		qualityV1, _ := qualityMetric.Measure(agentV1, inputMsg, outputV1, nil)
		totalQualityV1 += qualityV1

		// V2 quality
		outputV2 := &agenkit.Message{
			Role:    "assistant",
			Content: interactionsV2[i]["replay_output"].(map[string]interface{})["content"].(string),
		}
		qualityV2, _ := qualityMetric.Measure(agentV2, inputMsg, outputV2, nil)
		totalQualityV2 += qualityV2
	}

	avgQualityV1 := totalQualityV1 / float64(len(testCases))
	avgQualityV2 := totalQualityV2 / float64(len(testCases))

	fmt.Printf("Average Quality Scores:\n")
	fmt.Printf("  V1 (Control): %.3f\n", avgQualityV1)
	fmt.Printf("  V2 (Variant): %.3f\n", avgQualityV2)

	qualityImprovement := (avgQualityV2 - avgQualityV1) / avgQualityV1 * 100
	if qualityImprovement > 0 {
		fmt.Printf("  📈 V2 is %.1f%% better\n", qualityImprovement)
	} else {
		fmt.Printf("  📉 V2 is %.1f%% worse\n", -qualityImprovement)
	}

	// Step 6: Recommendation
	fmt.Println("\n\nStep 6: Deployment Recommendation")
	fmt.Println("----------------------------------")

	shouldDeploy := avgQualityV2 > avgQualityV1
	latencyIncrease := comparison["latency_diff_percent"].(float64)

	fmt.Println("Analysis:")
	if shouldDeploy {
		fmt.Println("  ✓ V2 shows quality improvement")
	} else {
		fmt.Println("  ✗ V2 does not show quality improvement")
	}

	if latencyIncrease < 10 {
		fmt.Println("  ✓ Latency increase is acceptable (<10%)")
	} else {
		fmt.Printf("  ⚠ Latency increased by %.1f%% (review required)\n", latencyIncrease)
	}

	fmt.Println("\nRecommendation:")
	if shouldDeploy && latencyIncrease < 10 {
		fmt.Println("  🚀 DEPLOY V2 - Shows improvement without significant latency cost")
	} else if shouldDeploy {
		fmt.Println("  ⚠ CONDITIONAL DEPLOY - Improvement present but review latency impact")
	} else {
		fmt.Println("  ❌ DO NOT DEPLOY - V2 does not show improvement over V1")
	}

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 70))
	fmt.Println("Summary: A/B Testing")
	fmt.Println(strings.Repeat("=", 70))

	fmt.Println("\nA/B Testing Process:")
	fmt.Println("1. Record baseline session with control agent (V1)")
	fmt.Println("2. Replay session with variant agent (V2)")
	fmt.Println("3. Compare outputs, latency, and quality")
	fmt.Println("4. Make data-driven deployment decision")

	fmt.Println("\nMetrics to Compare:")
	fmt.Println("- Quality Score: Rule-based or LLM-as-judge")
	fmt.Println("- Accuracy: Correctness on known answers")
	fmt.Println("- Latency: Response time (P50, P95, P99)")
	fmt.Println("- Cost: Token usage and API costs")
	fmt.Println("- Output Differences: Semantic similarity")

	fmt.Println("\nBest Practices:")
	fmt.Println("1. Use diverse test cases covering edge cases")
	fmt.Println("2. Run on production-like data, not synthetic")
	fmt.Println("3. Test with sufficient sample size (50+ interactions)")
	fmt.Println("4. Consider multiple metrics, not just one")
	fmt.Println("5. Set acceptance criteria before testing")
	fmt.Println("6. Run multiple trials for statistical significance")

	fmt.Println("\nDecision Criteria:")
	fmt.Println("Deploy if:")
	fmt.Println("  - Quality improvement >5%")
	fmt.Println("  - Latency increase <10%")
	fmt.Println("  - No increase in error rate")
	fmt.Println("  - Cost increase justified by quality gain")

	fmt.Println("\nReal-World Applications:")
	fmt.Println("- Model Selection: GPT-4 vs Claude vs Gemini")
	fmt.Println("- Prompt Engineering: Compare prompt variations")
	fmt.Println("- Configuration Tuning: Temperature, top_p, etc.")
	fmt.Println("- Feature Validation: New capabilities vs baseline")
	fmt.Println("- Cost Optimization: Cheaper model with same quality")
}
