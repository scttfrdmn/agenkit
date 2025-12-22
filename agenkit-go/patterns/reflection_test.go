package patterns

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// MockAgent is a simple mock agent for testing
type MockAgent struct {
	name         string
	responses    []string
	responseIdx  int
	capabilities []string
	processFunc  func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error)
}

func NewMockAgent(name string, responses []string) *MockAgent {
	return &MockAgent{
		name:         name,
		responses:    responses,
		responseIdx:  0,
		capabilities: []string{"mock"},
	}
}

func (m *MockAgent) Name() string {
	return m.name
}

func (m *MockAgent) Capabilities() []string {
	return m.capabilities
}

func (m *MockAgent) Introspect() *agenkit.IntrospectionResult {
	return &agenkit.IntrospectionResult{
		AgentName:    m.Name(),
		Capabilities: m.Capabilities(),
	}
}

func (m *MockAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	if m.processFunc != nil {
		return m.processFunc(ctx, message)
	}

	if m.responseIdx >= len(m.responses) {
		return nil, fmt.Errorf("no more mock responses available")
	}

	response := m.responses[m.responseIdx]
	m.responseIdx++

	return agenkit.NewMessage("assistant", response), nil
}

// TestNewReflectionAgent tests the creation of ReflectionAgent
func TestNewReflectionAgent(t *testing.T) {
	tests := []struct {
		name        string
		config      ReflectionConfig
		expectError bool
		errorMsg    string
	}{
		{
			name: "valid configuration",
			config: ReflectionConfig{
				Generator:            NewMockAgent("generator", []string{"output"}),
				Critic:               NewMockAgent("critic", []string{`{"score": 0.8, "feedback": "good"}`}),
				MaxIterations:        5,
				QualityThreshold:     0.9,
				ImprovementThreshold: 0.05,
				CritiqueFormat:       CritiqueStructured,
			},
			expectError: false,
		},
		{
			name: "nil generator",
			config: ReflectionConfig{
				Critic:        NewMockAgent("critic", []string{}),
				MaxIterations: 5,
			},
			expectError: true,
			errorMsg:    "generator agent is required",
		},
		{
			name: "nil critic",
			config: ReflectionConfig{
				Generator:     NewMockAgent("generator", []string{}),
				MaxIterations: 5,
			},
			expectError: true,
			errorMsg:    "critic agent is required",
		},
		{
			name: "invalid max iterations",
			config: ReflectionConfig{
				Generator:     NewMockAgent("generator", []string{}),
				Critic:        NewMockAgent("critic", []string{}),
				MaxIterations: 0,
			},
			expectError: true,
			errorMsg:    "max_iterations must be at least 1",
		},
		{
			name: "invalid quality threshold - too low",
			config: ReflectionConfig{
				Generator:        NewMockAgent("generator", []string{}),
				Critic:           NewMockAgent("critic", []string{}),
				MaxIterations:    5,
				QualityThreshold: -0.1,
			},
			expectError: true,
			errorMsg:    "quality_threshold must be between 0.0 and 1.0",
		},
		{
			name: "invalid quality threshold - too high",
			config: ReflectionConfig{
				Generator:        NewMockAgent("generator", []string{}),
				Critic:           NewMockAgent("critic", []string{}),
				MaxIterations:    5,
				QualityThreshold: 1.5,
			},
			expectError: true,
			errorMsg:    "quality_threshold must be between 0.0 and 1.0",
		},
		{
			name: "invalid improvement threshold",
			config: ReflectionConfig{
				Generator:            NewMockAgent("generator", []string{}),
				Critic:               NewMockAgent("critic", []string{}),
				MaxIterations:        5,
				QualityThreshold:     0.9,
				ImprovementThreshold: 1.5,
			},
			expectError: true,
			errorMsg:    "improvement_threshold must be between 0.0 and 1.0",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			agent, err := NewReflectionAgent(tt.config)

			if tt.expectError {
				if err == nil {
					t.Errorf("expected error but got none")
				} else if !strings.Contains(err.Error(), tt.errorMsg) {
					t.Errorf("expected error containing %q, got %q", tt.errorMsg, err.Error())
				}
			} else {
				if err != nil {
					t.Errorf("unexpected error: %v", err)
				}
				if agent == nil {
					t.Errorf("expected agent but got nil")
				}
			}
		})
	}
}

// TestReflectionAgentName tests the Name method
func TestReflectionAgentName(t *testing.T) {
	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:     NewMockAgent("generator", []string{}),
		Critic:        NewMockAgent("critic", []string{}),
		MaxIterations: 5,
	})

	if agent.Name() != "ReflectionAgent" {
		t.Errorf("expected name 'ReflectionAgent', got %q", agent.Name())
	}
}

// TestReflectionAgentCapabilities tests the Capabilities method
func TestReflectionAgentCapabilities(t *testing.T) {
	generator := NewMockAgent("generator", []string{})
	generator.capabilities = []string{"generate", "llm"}

	critic := NewMockAgent("critic", []string{})
	critic.capabilities = []string{"critique", "evaluate"}

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:     generator,
		Critic:        critic,
		MaxIterations: 5,
	})

	caps := agent.Capabilities()

	// Should include all capabilities
	expectedCaps := map[string]bool{
		"generate":      true,
		"llm":           true,
		"critique":      true,
		"evaluate":      true,
		"reflection":    true,
		"self-critique": true,
	}

	for _, cap := range caps {
		if !expectedCaps[cap] {
			t.Errorf("unexpected capability: %s", cap)
		}
	}

	if len(caps) != len(expectedCaps) {
		t.Errorf("expected %d capabilities, got %d", len(expectedCaps), len(caps))
	}
}

// TestReflectionQualityThresholdMet tests stopping when quality threshold is met
func TestReflectionQualityThresholdMet(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Initial output",
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 0.95, "feedback": "Excellent work!"}`,
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:        generator,
		Critic:           critic,
		MaxIterations:    5,
		QualityThreshold: 0.9,
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	result, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check metadata
	if result.Metadata["reflection_iterations"] != 1 {
		t.Errorf("expected 1 iteration, got %v", result.Metadata["reflection_iterations"])
	}

	if result.Metadata["stop_reason"] != string(StopQualityThreshold) {
		t.Errorf("expected stop reason %q, got %q", StopQualityThreshold, result.Metadata["stop_reason"])
	}

	if result.Metadata["final_quality_score"] != 0.95 {
		t.Errorf("expected final score 0.95, got %v", result.Metadata["final_quality_score"])
	}
}

// TestReflectionPerfectScore tests stopping when perfect score is achieved
func TestReflectionPerfectScore(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Perfect output",
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 1.0, "feedback": "Perfect!"}`,
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:        generator,
		Critic:           critic,
		MaxIterations:    5,
		QualityThreshold: 0.9,
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	result, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Metadata["stop_reason"] != string(StopPerfectScore) {
		t.Errorf("expected stop reason %q, got %q", StopPerfectScore, result.Metadata["stop_reason"])
	}
}

// TestReflectionMinimalImprovement tests stopping when improvement is minimal
func TestReflectionMinimalImprovement(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Output v1",
		"Output v2",
		"Output v3",
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 0.70, "feedback": "Good start"}`,
		`{"score": 0.71, "feedback": "Minor improvement"}`, // Only 0.01 improvement
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:            generator,
		Critic:               critic,
		MaxIterations:        5,
		QualityThreshold:     0.9,
		ImprovementThreshold: 0.05, // Requires at least 0.05 improvement
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	result, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Metadata["reflection_iterations"] != 2 {
		t.Errorf("expected 2 iterations, got %v", result.Metadata["reflection_iterations"])
	}

	if result.Metadata["stop_reason"] != string(StopMinimalImprovement) {
		t.Errorf("expected stop reason %q, got %q", StopMinimalImprovement, result.Metadata["stop_reason"])
	}
}

// TestReflectionMaxIterations tests stopping when max iterations is reached
func TestReflectionMaxIterations(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Output v1", // Initial generation
		"Output v2", // Refinement after iteration 1
		"Output v3", // Refinement after iteration 2
		"Output v4", // Refinement after iteration 3 (needed but won't be used as it's the last iteration)
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 0.5, "feedback": "Needs work"}`, // Iteration 1
		`{"score": 0.6, "feedback": "Better"}`,     // Iteration 2
		`{"score": 0.7, "feedback": "Improving"}`,  // Iteration 3
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:            generator,
		Critic:               critic,
		MaxIterations:        3,
		QualityThreshold:     0.9,
		ImprovementThreshold: 0.05,
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	result, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if result.Metadata["reflection_iterations"] != 3 {
		t.Errorf("expected 3 iterations, got %v", result.Metadata["reflection_iterations"])
	}

	if result.Metadata["stop_reason"] != string(StopMaxIterations) {
		t.Errorf("expected stop reason %q, got %q", StopMaxIterations, result.Metadata["stop_reason"])
	}
}

// TestParseStructuredCritique tests structured JSON critique parsing
func TestParseStructuredCritique(t *testing.T) {
	agent := &ReflectionAgent{
		critiqueFormat: CritiqueStructured,
	}

	tests := []struct {
		name             string
		input            string
		expectedScore    float64
		expectedFeedback string
	}{
		{
			name:             "valid JSON",
			input:            `{"score": 0.8, "feedback": "Good work"}`,
			expectedScore:    0.8,
			expectedFeedback: "Good work",
		},
		{
			name:             "JSON in markdown code block",
			input:            "```json\n{\"score\": 0.7, \"feedback\": \"Needs improvement\"}\n```",
			expectedScore:    0.7,
			expectedFeedback: "Needs improvement",
		},
		{
			name:             "score out of range - clamped to 0",
			input:            `{"score": -0.5, "feedback": "Test"}`,
			expectedScore:    0.0,
			expectedFeedback: "Test",
		},
		{
			name:             "score out of range - clamped to 1",
			input:            `{"score": 1.5, "feedback": "Test"}`,
			expectedScore:    1.0,
			expectedFeedback: "Test",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			score, feedback, err := agent.parseStructuredCritique(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if score != tt.expectedScore {
				t.Errorf("expected score %f, got %f", tt.expectedScore, score)
			}

			if !strings.Contains(feedback, tt.expectedFeedback) {
				t.Errorf("expected feedback to contain %q, got %q", tt.expectedFeedback, feedback)
			}
		})
	}
}

// TestParseFreeFormCritique tests free-form critique parsing
func TestParseFreeFormCritique(t *testing.T) {
	agent := &ReflectionAgent{
		critiqueFormat: CritiqueFreeForm,
	}

	tests := []struct {
		name          string
		input         string
		expectedScore float64
	}{
		{
			name:          "score with colon",
			input:         "Score: 0.8 - This is good",
			expectedScore: 0.8,
		},
		{
			name:          "rating with colon",
			input:         "Rating: 7.5 out of 10",
			expectedScore: 0.75,
		},
		{
			name:          "x/10 format",
			input:         "I would rate this 8/10",
			expectedScore: 0.8,
		},
		{
			name:          "x/1.0 format",
			input:         "Quality: 0.85/1.0",
			expectedScore: 0.85,
		},
		{
			name:          "no score found - default",
			input:         "This looks pretty good",
			expectedScore: 0.5,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			score, _, err := agent.parseFreeFormCritique(tt.input)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if score != tt.expectedScore {
				t.Errorf("expected score %f, got %f", tt.expectedScore, score)
			}
		})
	}
}

// TestReflectionVerboseMode tests verbose mode with history
func TestReflectionVerboseMode(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Output v1",
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 0.95, "feedback": "Great!"}`,
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:        generator,
		Critic:           critic,
		MaxIterations:    5,
		QualityThreshold: 0.9,
		Verbose:          true, // Enable verbose mode
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	result, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Check that history is included in metadata
	history, ok := result.Metadata["reflection_history"]
	if !ok {
		t.Errorf("expected reflection_history in metadata")
	}

	historySlice, ok := history.([]ReflectionStep)
	if !ok {
		t.Errorf("expected reflection_history to be []ReflectionStep")
	}

	if len(historySlice) != 1 {
		t.Errorf("expected 1 step in history, got %d", len(historySlice))
	}
}

// TestGetHistoryAndClearHistory tests history management
func TestGetHistoryAndClearHistory(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Output v1",
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 0.95, "feedback": "Great!"}`,
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:        generator,
		Critic:           critic,
		MaxIterations:    5,
		QualityThreshold: 0.9,
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	_, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Get history
	history := agent.GetHistory()
	if len(history) != 1 {
		t.Errorf("expected 1 step in history, got %d", len(history))
	}

	// Clear history
	agent.ClearHistory()
	history = agent.GetHistory()
	if len(history) != 0 {
		t.Errorf("expected 0 steps after clear, got %d", len(history))
	}
}

// TestReflectionTotalImprovement tests total improvement calculation
func TestReflectionTotalImprovement(t *testing.T) {
	generator := NewMockAgent("generator", []string{
		"Output v1", // Initial generation
		"Output v2", // Refinement after iteration 1
		"Output v3", // Refinement after iteration 2 (needed but won't be used as it reaches max iterations)
	})

	critic := NewMockAgent("critic", []string{
		`{"score": 0.60, "feedback": "Needs work"}`,  // Iteration 1
		`{"score": 0.85, "feedback": "Much better"}`, // Iteration 2
	})

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:            generator,
		Critic:               critic,
		MaxIterations:        2, // Only 2 iterations since we have 2 responses
		QualityThreshold:     0.9,
		ImprovementThreshold: 0.05,
	})

	ctx := context.Background()
	msg := agenkit.NewMessage("user", "Write a test")

	result, err := agent.Process(ctx, msg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	initialScore := result.Metadata["initial_quality_score"].(float64)
	finalScore := result.Metadata["final_quality_score"].(float64)
	totalImprovement := result.Metadata["total_improvement"].(float64)

	expectedImprovement := finalScore - initialScore

	if totalImprovement != expectedImprovement {
		t.Errorf("expected total improvement %f, got %f", expectedImprovement, totalImprovement)
	}

	if initialScore != 0.60 {
		t.Errorf("expected initial score 0.60, got %f", initialScore)
	}

	if finalScore != 0.85 {
		t.Errorf("expected final score 0.85, got %f", finalScore)
	}
}

// TestReflectionContextCancellation tests context cancellation handling
func TestReflectionContextCancellation(t *testing.T) {
	generator := NewMockAgent("generator", []string{})
	generator.processFunc = func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		time.Sleep(100 * time.Millisecond)
		return agenkit.NewMessage("assistant", "output"), nil
	}

	critic := NewMockAgent("critic", []string{})
	critic.processFunc = func(ctx context.Context, msg *agenkit.Message) (*agenkit.Message, error) {
		// Check for cancellation
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
			return agenkit.NewMessage("assistant", `{"score": 0.5, "feedback": "ok"}`), nil
		}
	}

	agent, _ := NewReflectionAgent(ReflectionConfig{
		Generator:     generator,
		Critic:        critic,
		MaxIterations: 5,
	})

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	msg := agenkit.NewMessage("user", "Write a test")

	_, err := agent.Process(ctx, msg)
	if err != context.Canceled {
		t.Errorf("expected context.Canceled error, got %v", err)
	}
}

// TestReflectionStepSerialization tests ReflectionStep JSON serialization
func TestReflectionStepSerialization(t *testing.T) {
	step := ReflectionStep{
		Iteration:    1,
		Output:       "test output",
		Critique:     "test critique",
		QualityScore: 0.8,
		Improvement:  0.1,
		Timestamp:    time.Now().UTC(),
	}

	// Serialize
	data, err := json.Marshal(step)
	if err != nil {
		t.Fatalf("failed to serialize: %v", err)
	}

	// Deserialize
	var decoded ReflectionStep
	err = json.Unmarshal(data, &decoded)
	if err != nil {
		t.Fatalf("failed to deserialize: %v", err)
	}

	// Verify
	if decoded.Iteration != step.Iteration {
		t.Errorf("iteration mismatch: expected %d, got %d", step.Iteration, decoded.Iteration)
	}
	if decoded.QualityScore != step.QualityScore {
		t.Errorf("score mismatch: expected %f, got %f", step.QualityScore, decoded.QualityScore)
	}
}
