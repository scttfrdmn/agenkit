package evaluation

import (
	"context"
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ContextMetrics tracks context length and growth over agent lifecycle.
//
// Essential for extreme-scale systems (endless) that operate at
// 1M-25M+ token contexts. Measures:
//   - Raw context token count
//   - Compressed context token count (if compression used)
//   - Compression ratio
//   - Context growth rate
//
// Example:
//
//	metrics := NewContextMetrics()
//	result, _ := metrics.Measure(agent, inputMsg, outputMsg, ctx)
//	fmt.Printf("Context length: %.0f tokens\n", result)
type ContextMetrics struct{}

// NewContextMetrics creates a new context metrics instance.
func NewContextMetrics() *ContextMetrics {
	return &ContextMetrics{}
}

// Name returns the metric name.
func (m *ContextMetrics) Name() string {
	return "context_length"
}

// Measure measures context length metrics.
//
// Args:
//
//	agent: Agent being evaluated
//	inputMessage: Input message
//	outputMessage: Agent response
//	ctx: Additional context with session history
//
// Returns:
//
//	Current context length in tokens (or compressed tokens if available)
func (m *ContextMetrics) Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error) {
	// Check metadata for context length
	if inputMessage.Metadata != nil {
		if contextLength, ok := inputMessage.Metadata["context_length"]; ok {
			if length, ok := contextLength.(float64); ok {
				return length, nil
			}
			if length, ok := contextLength.(int); ok {
				return float64(length), nil
			}
		}
	}

	// Fallback: estimate from conversation history
	if conversationHistory, ok := ctx["conversation_history"]; ok {
		if history, ok := conversationHistory.([]*agenkit.Message); ok {
			totalTokens := 0
			for _, msg := range history {
				totalTokens += m.estimateTokens(msg.Content)
			}
			return float64(totalTokens), nil
		}
	}

	return 0.0, nil
}

// Aggregate aggregates context length measurements.
//
// Args:
//
//	measurements: List of context lengths over time
//
// Returns:
//
//	Statistics: mean, min, max, final, growth_rate
func (m *ContextMetrics) Aggregate(measurements []float64) map[string]float64 {
	if len(measurements) == 0 {
		return map[string]float64{
			"mean":        0.0,
			"min":         0.0,
			"max":         0.0,
			"final":       0.0,
			"growth_rate": 0.0,
		}
	}

	growthRate := 0.0
	if len(measurements) > 1 {
		growthRate = (measurements[len(measurements)-1] - measurements[0]) / float64(len(measurements))
	}

	return map[string]float64{
		"mean":        sum(measurements) / float64(len(measurements)),
		"min":         minFloat64(measurements),
		"max":         maxFloat64(measurements),
		"final":       measurements[len(measurements)-1],
		"growth_rate": growthRate,
	}
}

// estimateTokens rough token estimation (4 chars ≈ 1 token).
func (m *ContextMetrics) estimateTokens(content string) int {
	return len(content) / 4
}

// CompressionStats contains statistics from compression evaluation.
type CompressionStats struct {
	RawTokens           int
	CompressedTokens    int
	CompressionRatio    float64
	RetrievalAccuracy   float64
	ContextLengthTested int
	Timestamp           time.Time
}

// ToDict converts stats to dictionary.
func (c *CompressionStats) ToDict() map[string]interface{} {
	return map[string]interface{}{
		"raw_tokens":            c.RawTokens,
		"compressed_tokens":     c.CompressedTokens,
		"compression_ratio":     c.CompressionRatio,
		"retrieval_accuracy":    c.RetrievalAccuracy,
		"context_length_tested": c.ContextLengthTested,
		"timestamp":             c.Timestamp.Format(time.RFC3339),
	}
}

// CompressionMetrics measures compression quality at extreme scale.
//
// Critical for endless and similar systems that use 100x-1000x
// compression at 25M+ tokens. Measures:
//   - Compression ratio achieved
//   - Information retention after compression
//   - Retrieval accuracy from compressed context
//   - Quality degradation as context grows
//
// Example:
//
//	metrics := NewCompressionMetrics([]int{1000000, 10000000, 25000000}, 10)
//	stats, _ := metrics.EvaluateAtLengths(agent, "session-123", nil)
//	for length, stat := range stats {
//	    fmt.Printf("%dM tokens: %.1fx compression\n", length/1e6, stat.CompressionRatio)
//	}
type CompressionMetrics struct {
	testLengths []int
	needleCount int
}

// NewCompressionMetrics creates a new compression metrics instance.
//
// Args:
//
//	testLengths: Context lengths to test (defaults to 1M, 10M, 25M)
//	needleCount: Number of "needle" facts to test retrieval
//
// Example:
//
//	metrics := NewCompressionMetrics([]int{1000000, 10000000}, 10)
func NewCompressionMetrics(testLengths []int, needleCount int) *CompressionMetrics {
	if testLengths == nil {
		testLengths = []int{
			1_000_000,  // 1M tokens
			10_000_000, // 10M tokens
			25_000_000, // 25M tokens (endless scale)
		}
	}

	return &CompressionMetrics{
		testLengths: testLengths,
		needleCount: needleCount,
	}
}

// Name returns the metric name.
func (m *CompressionMetrics) Name() string {
	return "compression_quality"
}

// Measure measures compression quality for single interaction.
//
// Returns:
//
//	Compression ratio (raw_tokens / compressed_tokens)
func (m *CompressionMetrics) Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error) {
	// Check metadata for compression ratio
	if outputMessage.Metadata != nil {
		if compressionRatio, ok := outputMessage.Metadata["compression_ratio"]; ok {
			if ratio, ok := compressionRatio.(float64); ok {
				return ratio, nil
			}
		}
	}

	return 1.0, nil // No compression
}

// Aggregate aggregates compression ratios.
//
// Args:
//
//	measurements: List of compression ratios
//
// Returns:
//
//	Statistics: mean, min, max, std
func (m *CompressionMetrics) Aggregate(measurements []float64) map[string]float64 {
	if len(measurements) == 0 {
		return map[string]float64{
			"mean": 1.0,
			"min":  1.0,
			"max":  1.0,
			"std":  0.0,
		}
	}

	meanRatio := sum(measurements) / float64(len(measurements))

	variance := 0.0
	for _, x := range measurements {
		variance += (x - meanRatio) * (x - meanRatio)
	}
	variance /= float64(len(measurements))
	std := math.Sqrt(variance)

	return map[string]float64{
		"mean": meanRatio,
		"min":  minFloat64(measurements),
		"max":  maxFloat64(measurements),
		"std":  std,
	}
}

// EvaluateAtLengths evaluates compression quality at multiple context lengths.
//
// Tests compression and retrieval at 1M, 10M, 25M tokens to
// detect quality degradation as context grows.
//
// Args:
//
//	agent: Agent with compression capability
//	sessionID: Session to evaluate
//	needleContent: Specific facts to test retrieval (optional)
//
// Returns:
//
//	Dictionary mapping context_length -> CompressionStats
func (m *CompressionMetrics) EvaluateAtLengths(agent agenkit.Agent, sessionID string, needleContent []string) (map[int]*CompressionStats, error) {
	results := make(map[int]*CompressionStats)

	if needleContent == nil {
		needleContent = m.defaultNeedles()
	}

	for _, length := range m.testLengths {
		// Create test messages to reach target length
		testMessages := m.generateTestContext(length, needleContent)

		// Process messages through agent
		for _, msg := range testMessages {
			message := &agenkit.Message{
				Role:    "user",
				Content: msg,
			}
			_, err := agent.Process(context.Background(), message)
			if err != nil {
				return nil, err
			}
		}

		// Test retrieval accuracy
		accuracy, err := m.testRetrieval(agent, sessionID, needleContent)
		if err != nil {
			return nil, err
		}

		results[length] = &CompressionStats{
			RawTokens:           length,
			CompressedTokens:    length / 100, // Placeholder
			CompressionRatio:    100.0,        // Placeholder
			RetrievalAccuracy:   accuracy,
			ContextLengthTested: length,
			Timestamp:           time.Now().UTC(),
		}
	}

	return results, nil
}

// generateTestContext generates test context with embedded needles.
//
// Args:
//
//	targetTokens: Target context length
//	needles: Facts to embed for retrieval testing
//
// Returns:
//
//	List of messages totaling ~target_tokens
func (m *CompressionMetrics) generateTestContext(targetTokens int, needles []string) []string {
	messages := make([]string, 0)
	currentTokens := 0

	// Insert needles at regular intervals
	needleInterval := targetTokens / (len(needles) + 1)
	nextNeedleAt := needleInterval
	needleIdx := 0

	// Generate filler content
	filler := strings.Repeat("This is filler content for context expansion. ", 20)
	fillerTokens := len(filler) / 4

	for currentTokens < targetTokens {
		// Insert needle if at interval
		if currentTokens >= nextNeedleAt && needleIdx < len(needles) {
			messages = append(messages, needles[needleIdx])
			currentTokens += len(needles[needleIdx]) / 4
			needleIdx++
			nextNeedleAt += needleInterval
		} else {
			// Add filler
			messages = append(messages, filler)
			currentTokens += fillerTokens
		}
	}

	return messages
}

// testRetrieval tests retrieval accuracy of needles from context.
//
// Args:
//
//	agent: Agent to test
//	sessionID: Session with context
//	needles: Facts that should be retrievable
//
// Returns:
//
//	Accuracy (0.0 to 1.0)
func (m *CompressionMetrics) testRetrieval(agent agenkit.Agent, sessionID string, needles []string) (float64, error) {
	correct := 0

	for _, needle := range needles {
		// Ask agent to retrieve the fact
		needlePreview := needle
		if len(needle) > 50 {
			needlePreview = needle[:50]
		}
		query := &agenkit.Message{
			Role:    "user",
			Content: fmt.Sprintf("Recall: What was mentioned about %s?", needlePreview),
		}

		response, err := agent.Process(context.Background(), query)
		if err != nil {
			continue
		}

		// Check if response contains needle content
		if strings.Contains(strings.ToLower(response.Content), strings.ToLower(needle)) {
			correct++
		}
	}

	if len(needles) == 0 {
		return 0.0, nil
	}
	return float64(correct) / float64(len(needles)), nil
}

// defaultNeedles generates default needle facts for testing.
func (m *CompressionMetrics) defaultNeedles() []string {
	needles := make([]string, m.needleCount)
	for i := 0; i < m.needleCount; i++ {
		needles[i] = fmt.Sprintf("NEEDLE FACT %d: The secret code is ALPHA-%04d-OMEGA.", i, i)
	}
	return needles
}

// LatencyMetric measures agent response latency.
//
// Tracks processing time per interaction. Critical for production
// systems where response time matters.
type LatencyMetric struct{}

// NewLatencyMetric creates a new latency metric instance.
func NewLatencyMetric() *LatencyMetric {
	return &LatencyMetric{}
}

// Name returns the metric name.
func (m *LatencyMetric) Name() string {
	return "latency"
}

// Measure gets latency for this interaction.
//
// Returns:
//
//	Latency in milliseconds
func (m *LatencyMetric) Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error) {
	if latencyMs, ok := ctx["latency_ms"]; ok {
		if latency, ok := latencyMs.(float64); ok {
			return latency, nil
		}
	}
	return 0.0, nil
}

// Aggregate aggregates latency measurements.
//
// Returns:
//
//	mean, p50, p95, p99, min, max
func (m *LatencyMetric) Aggregate(measurements []float64) map[string]float64 {
	if len(measurements) == 0 {
		return map[string]float64{
			"mean": 0.0,
			"p50":  0.0,
			"p95":  0.0,
			"p99":  0.0,
			"min":  0.0,
			"max":  0.0,
		}
	}

	sortedMeasurements := make([]float64, len(measurements))
	copy(sortedMeasurements, measurements)
	sort.Float64s(sortedMeasurements)

	n := len(sortedMeasurements)

	return map[string]float64{
		"mean": sum(measurements) / float64(n),
		"p50":  sortedMeasurements[int(float64(n)*0.50)],
		"p95":  sortedMeasurements[int(float64(n)*0.95)],
		"p99":  sortedMeasurements[int(float64(n)*0.99)],
		"min":  sortedMeasurements[0],
		"max":  sortedMeasurements[n-1],
	}
}

// Helper functions

func minFloat64(values []float64) float64 {
	if len(values) == 0 {
		return 0.0
	}
	minVal := values[0]
	for _, v := range values[1:] {
		if v < minVal {
			minVal = v
		}
	}
	return minVal
}

func maxFloat64(values []float64) float64 {
	if len(values) == 0 {
		return 0.0
	}
	maxVal := values[0]
	for _, v := range values[1:] {
		if v > maxVal {
			maxVal = v
		}
	}
	return maxVal
}
