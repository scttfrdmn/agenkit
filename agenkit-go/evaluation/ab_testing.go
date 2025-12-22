// Package evaluation provides A/B testing framework for comparing agent variants.
//
// A/B Testing Framework provides statistical significance testing, effect size
// calculation, and automated experiment orchestration for comparing agent performance.
//
// Example:
//
//	// Create A/B test
//	abTest := evaluation.NewABTest(
//	    "prompt_comparison",
//	    controlAgent,
//	    treatmentAgent,
//	    []string{"accuracy"},
//	    evaluation.SignificanceLevel005,
//	    evaluation.TestTypeTTest,
//	)
//
//	// Run experiment
//	results, _ := abTest.Run(testCases, 50, true)
//
//	// Check significance
//	if results["accuracy"].IsSignificant() {
//	    fmt.Printf("Winner: %s\n", results["accuracy"].Winner())
//	}
package evaluation

import (
	"context"
	"fmt"
	"math"
	"math/rand"
	"sort"
	"time"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
	"gonum.org/v1/gonum/stat"
)

// SignificanceLevel represents statistical significance thresholds.
type SignificanceLevel float64

const (
	// SignificanceLevel0001 represents 99.9% confidence
	SignificanceLevel0001 SignificanceLevel = 0.001
	// SignificanceLevel001 represents 99% confidence
	SignificanceLevel001 SignificanceLevel = 0.01
	// SignificanceLevel005 represents 95% confidence (default)
	SignificanceLevel005 SignificanceLevel = 0.05
	// SignificanceLevel010 represents 90% confidence
	SignificanceLevel010 SignificanceLevel = 0.10
)

// StatisticalTestType represents types of statistical tests.
type StatisticalTestType string

const (
	// TestTypeTTest is a parametric test assuming normal distribution
	TestTypeTTest StatisticalTestType = "t_test"
	// TestTypeMannWhitney is a non-parametric test
	TestTypeMannWhitney StatisticalTestType = "mann_whitney"
)

// ABVariant represents a variant in an A/B test.
type ABVariant struct {
	Name     string
	Agent    agenkit.Agent
	Samples  []float64
	Metadata map[string]interface{}
}

// NewABVariant creates a new A/B variant.
func NewABVariant(name string, agent agenkit.Agent) *ABVariant {
	return &ABVariant{
		Name:     name,
		Agent:    agent,
		Samples:  []float64{},
		Metadata: make(map[string]interface{}),
	}
}

// AddSample adds a measurement sample.
func (v *ABVariant) AddSample(value float64) {
	v.Samples = append(v.Samples, value)
}

// Mean returns the mean of samples.
func (v *ABVariant) Mean() float64 {
	if len(v.Samples) == 0 {
		return 0.0
	}
	return stat.Mean(v.Samples, nil)
}

// StdDev returns the standard deviation of samples.
func (v *ABVariant) StdDev() float64 {
	if len(v.Samples) <= 1 {
		return 0.0
	}
	return stat.StdDev(v.Samples, nil)
}

// SampleSize returns the number of samples.
func (v *ABVariant) SampleSize() int {
	return len(v.Samples)
}

// ABResult contains results of an A/B test with statistical analysis.
type ABResult struct {
	ExperimentName     string
	ControlVariant     *ABVariant
	TreatmentVariant   *ABVariant
	MetricName         string
	PValue             float64
	TestType           StatisticalTestType
	SignificanceLevel  SignificanceLevel
	EffectSize         float64
	ConfidenceInterval [2]float64
	Timestamp          time.Time
}

// IsSignificant checks if result is statistically significant.
func (r *ABResult) IsSignificant() bool {
	return r.PValue < float64(r.SignificanceLevel)
}

// Winner returns the winner variant name if significant, otherwise empty string.
func (r *ABResult) Winner() string {
	if !r.IsSignificant() {
		return ""
	}

	if r.TreatmentVariant.Mean() > r.ControlVariant.Mean() {
		return r.TreatmentVariant.Name
	}
	return r.ControlVariant.Name
}

// ImprovementPercent returns percent improvement of treatment over control.
func (r *ABResult) ImprovementPercent() float64 {
	if r.ControlVariant.Mean() == 0 {
		return 0.0
	}
	return ((r.TreatmentVariant.Mean() - r.ControlVariant.Mean()) / math.Abs(r.ControlVariant.Mean())) * 100
}

// ToMap converts result to map for serialization.
func (r *ABResult) ToMap() map[string]interface{} {
	return map[string]interface{}{
		"experiment_name": r.ExperimentName,
		"metric":          r.MetricName,
		"control": map[string]interface{}{
			"name":        r.ControlVariant.Name,
			"mean":        r.ControlVariant.Mean(),
			"std":         r.ControlVariant.StdDev(),
			"sample_size": r.ControlVariant.SampleSize(),
		},
		"treatment": map[string]interface{}{
			"name":        r.TreatmentVariant.Name,
			"mean":        r.TreatmentVariant.Mean(),
			"std":         r.TreatmentVariant.StdDev(),
			"sample_size": r.TreatmentVariant.SampleSize(),
		},
		"statistics": map[string]interface{}{
			"p_value":             r.PValue,
			"test_type":           r.TestType,
			"significance_level":  r.SignificanceLevel,
			"is_significant":      r.IsSignificant(),
			"effect_size":         r.EffectSize,
			"confidence_interval": r.ConfidenceInterval,
		},
		"outcome": map[string]interface{}{
			"winner":              r.Winner(),
			"improvement_percent": r.ImprovementPercent(),
		},
		"timestamp": r.Timestamp,
	}
}

// ABTest orchestrates A/B experiments comparing agent variants.
type ABTest struct {
	Name              string
	Control           *ABVariant
	Treatment         *ABVariant
	Metrics           []string
	SignificanceLevel SignificanceLevel
	TestType          StatisticalTestType
	Results           map[string]*ABResult
}

// NewABTest creates a new A/B test.
func NewABTest(
	name string,
	controlAgent agenkit.Agent,
	treatmentAgent agenkit.Agent,
	metrics []string,
	significanceLevel SignificanceLevel,
	testType StatisticalTestType,
) *ABTest {
	if len(metrics) == 0 {
		metrics = []string{"accuracy"}
	}

	return &ABTest{
		Name:              name,
		Control:           NewABVariant("control", controlAgent),
		Treatment:         NewABVariant("treatment", treatmentAgent),
		Metrics:           metrics,
		SignificanceLevel: significanceLevel,
		TestType:          testType,
		Results:           make(map[string]*ABResult),
	}
}

// Run executes the A/B test experiment.
func (t *ABTest) Run(testCases []map[string]interface{}, sampleSize int, shuffle bool) (map[string]*ABResult, error) {
	// Prepare test cases
	cases := make([]map[string]interface{}, len(testCases))
	copy(cases, testCases)

	if shuffle {
		rand.Shuffle(len(cases), func(i, j int) {
			cases[i], cases[j] = cases[j], cases[i]
		})
	}

	if sampleSize > 0 && sampleSize < len(cases) {
		cases = cases[:sampleSize]
	}

	// Run both variants
	ctx := context.Background()
	controlResults, err := t.evaluateVariant(ctx, t.Control, cases)
	if err != nil {
		return nil, fmt.Errorf("control evaluation failed: %w", err)
	}

	treatmentResults, err := t.evaluateVariant(ctx, t.Treatment, cases)
	if err != nil {
		return nil, fmt.Errorf("treatment evaluation failed: %w", err)
	}

	// Store samples for each metric
	for _, metric := range t.Metrics {
		t.Control.Samples = []float64{}
		t.Treatment.Samples = []float64{}

		for _, r := range controlResults {
			if val, ok := r[metric].(float64); ok {
				t.Control.AddSample(val)
			}
		}

		for _, r := range treatmentResults {
			if val, ok := r[metric].(float64); ok {
				t.Treatment.AddSample(val)
			}
		}

		// Run statistical test
		result, err := t.runStatisticalTest(metric)
		if err != nil {
			return nil, fmt.Errorf("statistical test failed for %s: %w", metric, err)
		}

		t.Results[metric] = result
	}

	return t.Results, nil
}

// evaluateVariant evaluates a variant on test cases.
func (t *ABTest) evaluateVariant(ctx context.Context, variant *ABVariant, testCases []map[string]interface{}) ([]map[string]interface{}, error) {
	results := make([]map[string]interface{}, 0, len(testCases))

	for _, testCase := range testCases {
		input, ok := testCase["input"].(string)
		if !ok {
			input = ""
		}

		expected, ok := testCase["expected"].(string)
		if !ok {
			expected = ""
		}

		// Create message
		message := agenkit.NewMessage("user", input)

		// Measure latency
		startTime := time.Now()

		// Process message
		response, err := variant.Agent.Process(ctx, message)
		latencyMs := float64(time.Since(startTime).Milliseconds())

		var accuracy float64
		if err != nil {
			accuracy = 0.0
		} else {
			// Simple accuracy check (contains expected)
			actual := response.Content
			if expected != "" {
				if stringContainsIgnoreCase(actual, expected) {
					accuracy = 1.0
				} else {
					accuracy = 0.0
				}
			} else {
				accuracy = 1.0 // No expected value means success
			}
		}

		results = append(results, map[string]interface{}{
			"accuracy":   accuracy,
			"latency_ms": latencyMs,
			"input":      input,
			"expected":   expected,
			"actual":     response.Content,
		})
	}

	return results, nil
}

// runStatisticalTest performs statistical significance testing.
func (t *ABTest) runStatisticalTest(metricName string) (*ABResult, error) {
	controlSamples := t.Control.Samples
	treatmentSamples := t.Treatment.Samples

	var pValue float64
	var effectSize float64
	var confidenceInterval [2]float64

	switch t.TestType {
	case TestTypeTTest:
		// Independent samples t-test
		pValue = tTest(controlSamples, treatmentSamples)

		// Cohen's d effect size
		pooledStd := math.Sqrt((t.Control.StdDev()*t.Control.StdDev() + t.Treatment.StdDev()*t.Treatment.StdDev()) / 2)
		if pooledStd > 0 {
			effectSize = (t.Treatment.Mean() - t.Control.Mean()) / pooledStd
		}

		// Confidence interval (simplified)
		diff := t.Treatment.Mean() - t.Control.Mean()
		margin := 1.96 * pooledStd // 95% confidence
		confidenceInterval = [2]float64{diff - margin, diff + margin}

	case TestTypeMannWhitney:
		// Mann-Whitney U test
		pValue = mannWhitneyU(controlSamples, treatmentSamples)

		// Effect size (rank-biserial correlation, simplified)
		effectSize = (t.Treatment.Mean() - t.Control.Mean()) / (t.Control.StdDev() + t.Treatment.StdDev())

		// Bootstrap confidence interval (simplified)
		confidenceInterval = bootstrapCI(controlSamples, treatmentSamples, 0.05)
	}

	return &ABResult{
		ExperimentName:     t.Name,
		ControlVariant:     t.Control,
		TreatmentVariant:   t.Treatment,
		MetricName:         metricName,
		PValue:             pValue,
		TestType:           t.TestType,
		SignificanceLevel:  t.SignificanceLevel,
		EffectSize:         effectSize,
		ConfidenceInterval: confidenceInterval,
		Timestamp:          time.Now(),
	}, nil
}

// GetSummary returns experiment summary.
func (t *ABTest) GetSummary() map[string]interface{} {
	resultsMap := make(map[string]interface{})
	for metric, result := range t.Results {
		resultsMap[metric] = result.ToMap()
	}

	return map[string]interface{}{
		"experiment_name": t.Name,
		"variants": map[string]string{
			"control":   t.Control.Name,
			"treatment": t.Treatment.Name,
		},
		"metrics": t.Metrics,
		"results": resultsMap,
	}
}

// CalculateSampleSize calculates required sample size for A/B test.
func CalculateSampleSize(baselineMean, minimumDetectableEffect, alpha, power float64, stdDev *float64) int {
	var sd float64
	if stdDev == nil {
		// Estimate std dev as 25% of baseline mean if not provided
		sd = baselineMean * 0.25
	} else {
		sd = *stdDev
	}

	// Z-scores for alpha and beta (using normal approximation)
	zAlpha := 1.96 // For alpha = 0.05 (two-tailed)
	zBeta := 0.84  // For power = 0.80

	if alpha <= 0.001 {
		zAlpha = 3.29
	} else if alpha <= 0.01 {
		zAlpha = 2.58
	}

	if power >= 0.95 {
		zBeta = 1.645
	} else if power >= 0.90 {
		zBeta = 1.28
	}

	// Sample size calculation
	n := (zAlpha + zBeta) * (zAlpha + zBeta) * 2 * sd * sd / (minimumDetectableEffect * minimumDetectableEffect)

	return int(n) + 1
}

// Helper functions

// stringContainsIgnoreCase checks if s contains substr (case-insensitive).
func stringContainsIgnoreCase(s, substr string) bool {
	s = stringToLower(s)
	substr = stringToLower(substr)
	return stringContains(s, substr)
}

func stringToLower(s string) string {
	result := make([]rune, len(s))
	for i, r := range s {
		if r >= 'A' && r <= 'Z' {
			result[i] = r + ('a' - 'A')
		} else {
			result[i] = r
		}
	}
	return string(result)
}

func stringContains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(substr) == 0 || indexOfSubstring(s, substr) >= 0)
}

func indexOfSubstring(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

// tTest performs independent samples t-test (simplified).
func tTest(sample1, sample2 []float64) float64 {
	n1 := float64(len(sample1))
	n2 := float64(len(sample2))

	if n1 == 0 || n2 == 0 {
		return 1.0
	}

	mean1 := stat.Mean(sample1, nil)
	mean2 := stat.Mean(sample2, nil)

	var1 := stat.Variance(sample1, nil)
	var2 := stat.Variance(sample2, nil)

	// Pooled standard error
	se := math.Sqrt(var1/n1 + var2/n2)

	if se == 0 {
		return 1.0 // No difference
	}

	// T-statistic
	t := (mean1 - mean2) / se

	// Degrees of freedom (Welch's approximation)
	varRatio1 := var1 / n1
	varRatio2 := var2 / n2
	df := (varRatio1 + varRatio2) * (varRatio1 + varRatio2) / (varRatio1*varRatio1/(n1-1) + varRatio2*varRatio2/(n2-1))

	// Approximate p-value using t-distribution (simplified)
	pValue := 2 * (1 - tCDF(math.Abs(t), df))

	return pValue
}

// mannWhitneyU performs Mann-Whitney U test (simplified).
func mannWhitneyU(sample1, sample2 []float64) float64 {
	n1 := len(sample1)
	n2 := len(sample2)

	if n1 == 0 || n2 == 0 {
		return 1.0
	}

	// Combine samples with group labels
	type rankedValue struct {
		value float64
		group int
	}

	combined := make([]rankedValue, 0, n1+n2)
	for _, v := range sample1 {
		combined = append(combined, rankedValue{v, 1})
	}
	for _, v := range sample2 {
		combined = append(combined, rankedValue{v, 2})
	}

	// Sort by value
	sort.Slice(combined, func(i, j int) bool {
		return combined[i].value < combined[j].value
	})

	// Calculate U statistic
	r1 := 0.0
	for i, rv := range combined {
		if rv.group == 1 {
			r1 += float64(i + 1)
		}
	}

	u1 := r1 - float64(n1*(n1+1))/2

	// Calculate p-value (normal approximation)
	meanU := float64(n1*n2) / 2
	stdU := math.Sqrt(float64(n1*n2*(n1+n2+1)) / 12)

	if stdU == 0 {
		return 1.0
	}

	z := (u1 - meanU) / stdU
	pValue := 2 * (1 - normalCDF(math.Abs(z)))

	return pValue
}

// bootstrapCI calculates bootstrap confidence interval (simplified).
func bootstrapCI(sample1, sample2 []float64, alpha float64) [2]float64 {
	nIterations := 1000
	differences := make([]float64, nIterations)

	for i := 0; i < nIterations; i++ {
		// Resample with replacement
		resample1 := make([]float64, len(sample1))
		resample2 := make([]float64, len(sample2))

		for j := range sample1 {
			resample1[j] = sample1[rand.Intn(len(sample1))]
		}
		for j := range sample2 {
			resample2[j] = sample2[rand.Intn(len(sample2))]
		}

		diff := stat.Mean(resample2, nil) - stat.Mean(resample1, nil)
		differences[i] = diff
	}

	// Sort differences
	sort.Float64s(differences)

	// Calculate confidence interval
	lowerIdx := int(float64(nIterations) * (alpha / 2))
	upperIdx := int(float64(nIterations) * (1 - alpha/2))

	return [2]float64{differences[lowerIdx], differences[upperIdx]}
}

// tCDF approximates the t-distribution CDF (simplified).
func tCDF(t, df float64) float64 {
	// Use normal approximation for large df
	if df > 30 {
		return normalCDF(t)
	}

	// Simplified approximation
	x := df / (df + t*t)
	return 1 - 0.5*math.Pow(x, df/2)
}

// normalCDF approximates the standard normal CDF.
func normalCDF(x float64) float64 {
	// Using the error function approximation
	return 0.5 * (1 + math.Erf(x/math.Sqrt2))
}
