package evaluation

import (
	"fmt"
	"math"
	"strings"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// ValidatorFunc is a custom validation function type.
type ValidatorFunc func(expected, actual string) bool

// AccuracyMetric measures task accuracy.
//
// Compares agent output to expected output to determine
// correctness. Supports multiple validation methods:
//   - Exact string matching
//   - Substring matching (case-insensitive)
//   - Custom validator functions
//
// Example:
//
//	metric := NewAccuracyMetric(nil, false)
//	score, _ := metric.Measure(
//	    agent,
//	    inputMsg,
//	    outputMsg,
//	    map[string]interface{}{"expected": "Paris"},
//	)
//	fmt.Printf("Accuracy: %.0f\n", score)  // 0.0 or 1.0
type AccuracyMetric struct {
	validator     ValidatorFunc
	caseSensitive bool
}

// NewAccuracyMetric creates a new accuracy metric.
//
// Args:
//
//	validator: Custom validation function(expected, actual) -> bool
//	caseSensitive: Whether string matching is case-sensitive
//
// Example:
//
//	metric := NewAccuracyMetric(nil, false)
func NewAccuracyMetric(validator ValidatorFunc, caseSensitive bool) *AccuracyMetric {
	return &AccuracyMetric{
		validator:     validator,
		caseSensitive: caseSensitive,
	}
}

// Name returns the metric name.
func (m *AccuracyMetric) Name() string {
	return "accuracy"
}

// Measure measures accuracy for single interaction.
//
// Args:
//
//	agent: Agent being evaluated
//	inputMessage: Input to agent
//	outputMessage: Agent's response
//	ctx: Must contain "expected" key with expected output
//
// Returns:
//
//	1.0 if correct, 0.0 if incorrect
func (m *AccuracyMetric) Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error) {
	expected, ok := ctx["expected"]
	if !ok {
		return 1.0, nil // No expected output = always correct
	}

	actual := outputMessage.Content

	// Custom validator
	if m.validator != nil {
		expectedStr := fmt.Sprintf("%v", expected)
		if m.validator(expectedStr, actual) {
			return 1.0, nil
		}
		return 0.0, nil
	}

	// String matching
	expectedStr := fmt.Sprintf("%v", expected)
	if !m.caseSensitive {
		expectedStr = strings.ToLower(expectedStr)
		actual = strings.ToLower(actual)
	}

	if strings.Contains(actual, expectedStr) {
		return 1.0, nil
	}
	return 0.0, nil
}

// Aggregate aggregates accuracy measurements.
//
// Args:
//
//	measurements: List of 0.0/1.0 values
//
// Returns:
//
//	Accuracy statistics: accuracy, total, correct, incorrect
func (m *AccuracyMetric) Aggregate(measurements []float64) map[string]float64 {
	if len(measurements) == 0 {
		return map[string]float64{
			"accuracy":  0.0,
			"total":     0.0,
			"correct":   0.0,
			"incorrect": 0.0,
		}
	}

	total := float64(len(measurements))
	correct := sum(measurements)

	return map[string]float64{
		"accuracy":  correct / total,
		"total":     total,
		"correct":   correct,
		"incorrect": total - correct,
	}
}

// QualityMetrics provides comprehensive quality scoring.
//
// Evaluates multiple quality dimensions:
//   - Relevance: How relevant is response to query?
//   - Completeness: Does response answer all parts?
//   - Coherence: Is response logically structured?
//   - Accuracy: Is information factually correct?
//
// Uses rule-based scoring.
//
// Example:
//
//	metric := NewQualityMetrics(false, "", nil)
//	score, _ := metric.Measure(agent, inputMsg, outputMsg, nil)
//	fmt.Printf("Quality: %.2f\n", score)  // 0.0 to 1.0
type QualityMetrics struct {
	useLLMJudge bool
	judgeModel  string
	weights     map[string]float64
}

// NewQualityMetrics creates a new quality metrics instance.
//
// Args:
//
//	useLLMJudge: Use LLM to judge quality (not yet implemented)
//	judgeModel: Model to use for judging (e.g., "claude-sonnet-4")
//	weights: Weights for each dimension (relevance, completeness, etc.)
//
// Example:
//
//	metric := NewQualityMetrics(false, "", nil)
func NewQualityMetrics(useLLMJudge bool, judgeModel string, weights map[string]float64) *QualityMetrics {
	if weights == nil {
		weights = map[string]float64{
			"relevance":    0.3,
			"completeness": 0.3,
			"coherence":    0.2,
			"accuracy":     0.2,
		}
	}

	return &QualityMetrics{
		useLLMJudge: useLLMJudge,
		judgeModel:  judgeModel,
		weights:     weights,
	}
}

// Name returns the metric name.
func (m *QualityMetrics) Name() string {
	return "quality"
}

// Measure measures response quality.
//
// Args:
//
//	agent: Agent being evaluated
//	inputMessage: Input query
//	outputMessage: Agent response
//	ctx: Optional context
//
// Returns:
//
//	Quality score (0.0 to 1.0)
func (m *QualityMetrics) Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error) {
	return m.ruleBasedQuality(inputMessage, outputMessage, ctx), nil
}

// ruleBasedQuality performs rule-based quality scoring.
//
// Uses heuristics to evaluate quality:
//   - Relevance: Response mentions query terms
//   - Completeness: Response length vs query complexity
//   - Coherence: Proper structure, no repetition
//   - Accuracy: Matches expected output if provided
//
// Returns:
//
//	Quality score (0.0 to 1.0)
func (m *QualityMetrics) ruleBasedQuality(inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) float64 {
	inputText := strings.ToLower(inputMessage.Content)
	outputText := strings.ToLower(outputMessage.Content)

	scores := make(map[string]float64)

	// Relevance: Does response mention query terms?
	queryTerms := strings.Fields(inputText)
	outputTerms := strings.Fields(outputText)

	queryTermSet := make(map[string]bool)
	for _, term := range queryTerms {
		queryTermSet[term] = true
	}

	outputTermSet := make(map[string]bool)
	for _, term := range outputTerms {
		outputTermSet[term] = true
	}

	overlap := 0
	for term := range queryTermSet {
		if outputTermSet[term] {
			overlap++
		}
	}

	relevance := float64(overlap) / math.Max(float64(len(queryTermSet)), 1)
	if relevance > 1.0 {
		relevance = 1.0
	}
	scores["relevance"] = relevance

	// Completeness: Is response substantial?
	expectedLength := math.Max(float64(len(inputText)*2), 100) // At least 2x input
	completeness := float64(len(outputText)) / expectedLength
	if completeness > 1.0 {
		completeness = 1.0
	}
	scores["completeness"] = completeness

	// Coherence: Basic checks
	hasStructure := len(outputText) > 20 // Non-trivial response
	noRepetition := !m.hasRepetition(outputText)

	coherence := 0.0
	if hasStructure {
		coherence += 0.5
	}
	if noRepetition {
		coherence += 0.5
	}
	scores["coherence"] = coherence

	// Accuracy: Compare to expected if available
	accuracy := 0.5 // Neutral if no expected output
	if ctx != nil {
		if expected, ok := ctx["expected"]; ok {
			expectedStr := strings.ToLower(fmt.Sprintf("%v", expected))
			if strings.Contains(outputText, expectedStr) {
				accuracy = 1.0
			} else {
				accuracy = 0.0
			}
		}
	}
	scores["accuracy"] = accuracy

	// Weighted average
	totalScore := 0.0
	for dim, score := range scores {
		totalScore += score * m.weights[dim]
	}

	return totalScore
}

// hasRepetition checks for excessive repetition in text.
func (m *QualityMetrics) hasRepetition(text string) bool {
	words := strings.Fields(text)
	if len(words) < 10 {
		return false
	}

	// Check for repeated phrases (3+ word sequences)
	seenPhrases := make(map[string]bool)
	for i := 0; i < len(words)-2; i++ {
		phrase := strings.Join(words[i:i+3], " ")
		if seenPhrases[phrase] {
			return true
		}
		seenPhrases[phrase] = true
	}

	return false
}

// Aggregate aggregates quality measurements.
//
// Args:
//
//	measurements: List of quality scores
//
// Returns:
//
//	Statistics: mean, min, max, std
func (m *QualityMetrics) Aggregate(measurements []float64) map[string]float64 {
	if len(measurements) == 0 {
		return map[string]float64{
			"mean": 0.0,
			"min":  0.0,
			"max":  0.0,
			"std":  0.0,
		}
	}

	mean := sum(measurements) / float64(len(measurements))

	variance := 0.0
	for _, x := range measurements {
		variance += (x - mean) * (x - mean)
	}
	variance /= float64(len(measurements))
	std := math.Sqrt(variance)

	return map[string]float64{
		"mean": mean,
		"min":  minFloat64(measurements),
		"max":  maxFloat64(measurements),
		"std":  std,
	}
}

// PrecisionRecallStats contains precision and recall statistics.
type PrecisionRecallStats struct {
	TruePositives  int
	FalsePositives int
	FalseNegatives int
	TrueNegatives  int
}

// Precision calculates precision.
func (s *PrecisionRecallStats) Precision() float64 {
	if s.TruePositives+s.FalsePositives == 0 {
		return 0.0
	}
	return float64(s.TruePositives) / float64(s.TruePositives+s.FalsePositives)
}

// Recall calculates recall.
func (s *PrecisionRecallStats) Recall() float64 {
	if s.TruePositives+s.FalseNegatives == 0 {
		return 0.0
	}
	return float64(s.TruePositives) / float64(s.TruePositives+s.FalseNegatives)
}

// F1Score calculates F1 score.
func (s *PrecisionRecallStats) F1Score() float64 {
	p := s.Precision()
	r := s.Recall()
	if p+r == 0 {
		return 0.0
	}
	return 2 * (p * r) / (p + r)
}

// ToDict converts stats to dictionary.
func (s *PrecisionRecallStats) ToDict() map[string]float64 {
	return map[string]float64{
		"true_positives":  float64(s.TruePositives),
		"false_positives": float64(s.FalsePositives),
		"false_negatives": float64(s.FalseNegatives),
		"true_negatives":  float64(s.TrueNegatives),
		"precision":       s.Precision(),
		"recall":          s.Recall(),
		"f1_score":        s.F1Score(),
	}
}

// PrecisionRecallMetric measures precision and recall for classification tasks.
//
// Useful for agents that categorize, filter, or make binary decisions.
//
// Example:
//
//	metric := NewPrecisionRecallMetric()
//	// Agent classifies documents as relevant/not relevant
//	for _, doc := range testDocs {
//	    score, _ := metric.Measure(agent, doc, output, ctx)
//	}
type PrecisionRecallMetric struct {
	truePositives  int
	falsePositives int
	falseNegatives int
	trueNegatives  int
}

// NewPrecisionRecallMetric creates a new precision/recall metric.
func NewPrecisionRecallMetric() *PrecisionRecallMetric {
	return &PrecisionRecallMetric{}
}

// Name returns the metric name.
func (m *PrecisionRecallMetric) Name() string {
	return "precision_recall"
}

// Measure measures precision/recall for single classification.
//
// Context must contain:
//   - "true_label": Ground truth (True/False or 1/0)
//   - "predicted_label": Agent's prediction (True/False or 1/0)
//
// Returns:
//
//	1.0 if correct classification, 0.0 if incorrect
func (m *PrecisionRecallMetric) Measure(agent agenkit.Agent, inputMessage, outputMessage *agenkit.Message, ctx map[string]interface{}) (float64, error) {
	if ctx == nil {
		return 1.0, nil
	}

	trueLabelRaw, ok1 := ctx["true_label"]
	predictedLabelRaw, ok2 := ctx["predicted_label"]

	if !ok1 || !ok2 {
		return 1.0, nil // No labels = always correct
	}

	trueLabel := toBool(trueLabelRaw)
	predictedLabel := toBool(predictedLabelRaw)

	// Update confusion matrix
	if trueLabel && predictedLabel {
		m.truePositives++
		return 1.0, nil
	} else if !trueLabel && predictedLabel {
		m.falsePositives++
		return 0.0, nil
	} else if trueLabel && !predictedLabel {
		m.falseNegatives++
		return 0.0, nil
	} else { // !trueLabel && !predictedLabel
		m.trueNegatives++
		return 1.0, nil
	}
}

// Aggregate aggregates precision/recall metrics.
//
// Returns:
//
//	Precision, recall, F1 score, and confusion matrix counts
func (m *PrecisionRecallMetric) Aggregate(measurements []float64) map[string]float64 {
	stats := &PrecisionRecallStats{
		TruePositives:  m.truePositives,
		FalsePositives: m.falsePositives,
		FalseNegatives: m.falseNegatives,
		TrueNegatives:  m.trueNegatives,
	}

	return stats.ToDict()
}

// Reset resets confusion matrix counts.
func (m *PrecisionRecallMetric) Reset() {
	m.truePositives = 0
	m.falsePositives = 0
	m.falseNegatives = 0
	m.trueNegatives = 0
}

// Helper functions

func toBool(v interface{}) bool {
	switch val := v.(type) {
	case bool:
		return val
	case int:
		return val != 0
	case float64:
		return val != 0
	case string:
		return val == "true" || val == "True" || val == "1"
	default:
		return false
	}
}
