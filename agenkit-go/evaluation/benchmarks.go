package evaluation

import (
	"fmt"
	"strings"
)

// TestCase represents a single test case for evaluation.
//
// Contains input, expected output, and metadata.
type TestCase struct {
	Input    string
	Expected interface{} // String or validation function
	Metadata map[string]interface{}
	Tags     []string
}

// ToDict converts test case to dictionary.
func (t *TestCase) ToDict() map[string]interface{} {
	expected := t.Expected
	if _, ok := expected.(func(interface{}) bool); ok {
		expected = "<function>"
	}

	return map[string]interface{}{
		"input":    t.Input,
		"expected": expected,
		"metadata": t.Metadata,
		"tags":     t.Tags,
	}
}

// Benchmark is the interface for benchmarks.
//
// Benchmarks define test suites for evaluating specific capabilities.
type Benchmark interface {
	// Name returns the benchmark name.
	Name() string

	// Description returns the benchmark description.
	Description() string

	// GenerateTestCases generates test cases for this benchmark.
	//
	// Returns:
	//   List of test cases
	GenerateTestCases() ([]*TestCase, error)
}

// SimpleQABenchmark is a simple question-answering benchmark.
//
// Tests basic knowledge and reasoning.
type SimpleQABenchmark struct{}

// NewSimpleQABenchmark creates a new simple Q&A benchmark.
func NewSimpleQABenchmark() *SimpleQABenchmark {
	return &SimpleQABenchmark{}
}

// Name returns the benchmark name.
func (b *SimpleQABenchmark) Name() string {
	return "simple_qa"
}

// Description returns the benchmark description.
func (b *SimpleQABenchmark) Description() string {
	return "Basic question-answering tasks"
}

// GenerateTestCases generates simple Q&A test cases.
func (b *SimpleQABenchmark) GenerateTestCases() ([]*TestCase, error) {
	return []*TestCase{
		{
			Input:    "What is 2+2?",
			Expected: "4",
			Metadata: map[string]interface{}{},
			Tags:     []string{"math", "easy"},
		},
		{
			Input:    "What is the capital of France?",
			Expected: "Paris",
			Metadata: map[string]interface{}{},
			Tags:     []string{"knowledge", "easy"},
		},
		{
			Input:    "What is the largest planet in our solar system?",
			Expected: "Jupiter",
			Metadata: map[string]interface{}{},
			Tags:     []string{"knowledge", "easy"},
		},
		{
			Input:    "If a train leaves at 2pm and travels for 3 hours, when does it arrive?",
			Expected: "5", // "5pm" or "5:00pm" both match
			Metadata: map[string]interface{}{},
			Tags:     []string{"reasoning", "easy"},
		},
		{
			Input:    "What comes next in the sequence: 2, 4, 6, 8, ?",
			Expected: "10",
			Metadata: map[string]interface{}{},
			Tags:     []string{"reasoning", "easy"},
		},
	}, nil
}

// NeedleInHaystackBenchmark is a needle-in-haystack benchmark for context retrieval.
//
// Tests ability to retrieve specific information from large contexts.
// Essential for extreme-scale systems like endless.
type NeedleInHaystackBenchmark struct {
	contextLength      int
	needleCount        int
	haystackMultiplier int
}

// NewNeedleInHaystackBenchmark creates a new needle-in-haystack benchmark.
//
// Args:
//
//	contextLength: Target context length in tokens
//	needleCount: Number of needles to hide
//	haystackMultiplier: How much filler per needle
//
// Example:
//
//	benchmark := NewNeedleInHaystackBenchmark(10000, 5, 10)
func NewNeedleInHaystackBenchmark(contextLength, needleCount, haystackMultiplier int) *NeedleInHaystackBenchmark {
	return &NeedleInHaystackBenchmark{
		contextLength:      contextLength,
		needleCount:        needleCount,
		haystackMultiplier: haystackMultiplier,
	}
}

// Name returns the benchmark name.
func (b *NeedleInHaystackBenchmark) Name() string {
	return fmt.Sprintf("needle_in_haystack_%d", b.contextLength)
}

// Description returns the benchmark description.
func (b *NeedleInHaystackBenchmark) Description() string {
	return fmt.Sprintf("Retrieve %d facts from %d token context", b.needleCount, b.contextLength)
}

// GenerateTestCases generates needle-in-haystack test cases.
func (b *NeedleInHaystackBenchmark) GenerateTestCases() ([]*TestCase, error) {
	testCases := make([]*TestCase, 0)

	// Generate needles (specific facts to retrieve)
	needles := make([]string, b.needleCount)
	for i := 0; i < b.needleCount; i++ {
		needles[i] = fmt.Sprintf("The secret code for vault %d is ALPHA-%04d-OMEGA.", i, i)
	}

	// Generate haystack (filler content)
	haystack := b.generateHaystack(b.contextLength)

	// Embed needles at random positions
	context := b.embedNeedles(haystack, needles)

	// Create test cases asking for each needle
	for i := range needles {
		testCases = append(testCases, &TestCase{
			Input:    fmt.Sprintf("Context: %s\n\nQuestion: What is the secret code for vault %d?", context, i),
			Expected: fmt.Sprintf("ALPHA-%04d-OMEGA", i),
			Metadata: map[string]interface{}{
				"context_length":  len(strings.Fields(context)) / 4, // Rough token estimate
				"needle_position": i,
				"total_needles":   b.needleCount,
			},
			Tags: []string{"retrieval", "context", fmt.Sprintf("length_%d", b.contextLength)},
		})
	}

	return testCases, nil
}

// generateHaystack generates filler content for haystack.
func (b *NeedleInHaystackBenchmark) generateHaystack(targetTokens int) string {
	// Simple filler paragraphs
	paragraphs := []string{
		"This is a paragraph of filler content. It contains general information that is not relevant to the specific queries we will ask. " +
			"The purpose of this content is to create a large context that the agent must search through. ",
		"Here is another paragraph with different content. It discusses various topics without providing the specific information we're looking for. " +
			"This helps test the agent's ability to find needles in haystacks. ",
		"Additional filler text to expand the context. This paragraph talks about unrelated subjects and serves to increase the total context length. " +
			"The agent must be able to filter through this content efficiently. ",
	}

	// Repeat paragraphs to reach target length
	haystack := ""
	tokensPerParagraph := 0
	for _, p := range paragraphs {
		tokensPerParagraph += len(strings.Fields(p))
	}

	repetitions := (targetTokens / tokensPerParagraph) + 1

	for i := 0; i < repetitions; i++ {
		for _, paragraph := range paragraphs {
			haystack += paragraph
		}
	}

	return haystack
}

// embedNeedles embeds needles at regular intervals in haystack.
func (b *NeedleInHaystackBenchmark) embedNeedles(haystack string, needles []string) string {
	words := strings.Fields(haystack)
	interval := len(words) / (len(needles) + 1)

	embedded := make([]string, 0)
	needleIdx := 0

	for i, word := range words {
		// Insert needle at intervals
		if needleIdx < len(needles) && i == interval*(needleIdx+1) {
			embedded = append(embedded, needles[needleIdx])
			needleIdx++
		}
		embedded = append(embedded, word)
	}

	return strings.Join(embedded, " ")
}

// ExtremeScaleBenchmark is an extreme-scale benchmark for testing at 1M-25M+ tokens.
//
// Designed specifically for endless and similar systems that
// operate at unprecedented context lengths.
type ExtremeScaleBenchmark struct {
	testLengths      []int
	needlesPerLength int
}

// NewExtremeScaleBenchmark creates a new extreme-scale benchmark.
//
// Args:
//
//	testLengths: Context lengths to test (defaults to 1M, 10M, 25M)
//	needlesPerLength: Number of needles per context length
//
// Example:
//
//	benchmark := NewExtremeScaleBenchmark([]int{1000000, 10000000}, 10)
func NewExtremeScaleBenchmark(testLengths []int, needlesPerLength int) *ExtremeScaleBenchmark {
	if testLengths == nil {
		testLengths = []int{
			1_000_000,  // 1M tokens
			10_000_000, // 10M tokens
			25_000_000, // 25M tokens (endless scale)
		}
	}

	return &ExtremeScaleBenchmark{
		testLengths:      testLengths,
		needlesPerLength: needlesPerLength,
	}
}

// Name returns the benchmark name.
func (b *ExtremeScaleBenchmark) Name() string {
	return "extreme_scale"
}

// Description returns the benchmark description.
func (b *ExtremeScaleBenchmark) Description() string {
	maxLength := b.testLengths[0]
	for _, length := range b.testLengths {
		if length > maxLength {
			maxLength = length
		}
	}
	return fmt.Sprintf("Test retrieval and quality at 1M-%dM tokens", maxLength/1_000_000)
}

// GenerateTestCases generates extreme-scale test cases.
func (b *ExtremeScaleBenchmark) GenerateTestCases() ([]*TestCase, error) {
	testCases := make([]*TestCase, 0)

	for _, length := range b.testLengths {
		// Create needle-in-haystack tests at this scale
		benchmark := NewNeedleInHaystackBenchmark(length, b.needlesPerLength, 10)

		cases, err := benchmark.GenerateTestCases()
		if err != nil {
			return nil, err
		}

		// Tag with scale
		for _, testCase := range cases {
			testCase.Tags = append(testCase.Tags, "extreme_scale")
			testCase.Tags = append(testCase.Tags, fmt.Sprintf("scale_%dM", length/1_000_000))
			testCase.Metadata["benchmark"] = "extreme_scale"
		}

		testCases = append(testCases, cases...)
	}

	return testCases, nil
}

// InformationRetentionBenchmark tests information retention across long conversations.
//
// Verifies that agents remember and can recall information
// from earlier in the conversation, even after compression.
type InformationRetentionBenchmark struct {
	conversationLength int
	recallPoints       []int
}

// NewInformationRetentionBenchmark creates a new information retention benchmark.
//
// Args:
//
//	conversationLength: Number of conversation turns
//	recallPoints: Turns at which to test recall (defaults to checkpoints)
//
// Example:
//
//	benchmark := NewInformationRetentionBenchmark(100, []int{10, 25, 50, 75, 100})
func NewInformationRetentionBenchmark(conversationLength int, recallPoints []int) *InformationRetentionBenchmark {
	if recallPoints == nil {
		recallPoints = []int{10, 25, 50, 75, 100}
	}

	return &InformationRetentionBenchmark{
		conversationLength: conversationLength,
		recallPoints:       recallPoints,
	}
}

// Name returns the benchmark name.
func (b *InformationRetentionBenchmark) Name() string {
	return "information_retention"
}

// Description returns the benchmark description.
func (b *InformationRetentionBenchmark) Description() string {
	return fmt.Sprintf("Test recall of facts across %d turns", b.conversationLength)
}

// GenerateTestCases generates information retention test cases.
func (b *InformationRetentionBenchmark) GenerateTestCases() ([]*TestCase, error) {
	testCases := make([]*TestCase, 0)

	// Plant facts at regular intervals
	facts := [][3]string{
		{"favorite_color", "blue", "My favorite color is blue."},
		{"birth_city", "Paris", "I was born in Paris."},
		{"occupation", "engineer", "I work as an engineer."},
		{"pet_name", "Max", "My dog's name is Max."},
		{"hobby", "painting", "I enjoy painting in my free time."},
	}

	factIndex := 0

	// Create conversation with embedded facts
	for turn := 0; turn < b.conversationLength; turn++ {
		// Plant fact every 20 turns
		if turn > 0 && turn%20 == 0 && factIndex < len(facts) {
			fact := facts[factIndex]
			factKey := fact[0]
			factValue := fact[1]
			factStatement := fact[2]
			factIndex++

			testCases = append(testCases, &TestCase{
				Input:    factStatement,
				Expected: "I'll remember that", // Acknowledgment
				Metadata: map[string]interface{}{
					"turn":       turn,
					"type":       "fact_plant",
					"fact_key":   factKey,
					"fact_value": factValue,
				},
				Tags: []string{"retention", "plant"},
			})
		}

		// Test recall at checkpoints
		if containsIntSlice(b.recallPoints, turn) {
			testCases = append(testCases, &TestCase{
				Input:    "What's the weather like?",
				Expected: nil, // Any response
				Metadata: map[string]interface{}{
					"turn": turn,
					"type": "filler",
				},
				Tags: []string{"retention", "filler"},
			})
		}
	}

	// Final recall tests
	// Ask about all planted facts
	factQuestions := [][3]string{
		{"favorite_color", "blue", "What did I say my favorite color was?"},
		{"birth_city", "Paris", "Where did I tell you I was born?"},
		{"occupation", "engineer", "What is my occupation?"},
		{"pet_name", "Max", "What is my dog's name?"},
		{"hobby", "painting", "What hobby did I mention?"},
	}

	for _, factQuestion := range factQuestions {
		factKey := factQuestion[0]
		expectedValue := factQuestion[1]
		question := factQuestion[2]

		testCases = append(testCases, &TestCase{
			Input:    question,
			Expected: expectedValue,
			Metadata: map[string]interface{}{
				"turn":     b.conversationLength,
				"type":     "recall_test",
				"fact_key": factKey,
			},
			Tags: []string{"retention", "recall"},
		})
	}

	return testCases, nil
}

// BenchmarkSuite is a collection of benchmarks for comprehensive evaluation.
//
// Provides standard and extreme-scale benchmark suites.
type BenchmarkSuite struct {
	benchmarks []Benchmark
	suiteName  string
}

// NewBenchmarkSuite creates a new benchmark suite.
//
// Args:
//
//	benchmarks: List of benchmarks to include
//	name: Suite name
//
// Example:
//
//	suite := NewBenchmarkSuite([]Benchmark{NewSimpleQABenchmark()}, "custom")
func NewBenchmarkSuite(benchmarks []Benchmark, name string) *BenchmarkSuite {
	if benchmarks == nil {
		benchmarks = []Benchmark{}
	}

	return &BenchmarkSuite{
		benchmarks: benchmarks,
		suiteName:  name,
	}
}

// BenchmarkSuiteStandard creates a standard benchmark suite.
//
// Includes basic Q&A and small-scale retrieval tests.
func BenchmarkSuiteStandard() *BenchmarkSuite {
	return NewBenchmarkSuite([]Benchmark{
		NewSimpleQABenchmark(),
		NewNeedleInHaystackBenchmark(10_000, 5, 10),
		NewInformationRetentionBenchmark(50, nil),
	}, "standard")
}

// BenchmarkSuiteExtremeScale creates an extreme-scale benchmark suite for endless.
//
// Tests at 1M-25M+ tokens with compression and retrieval.
func BenchmarkSuiteExtremeScale() *BenchmarkSuite {
	return NewBenchmarkSuite([]Benchmark{
		NewExtremeScaleBenchmark([]int{1_000_000, 10_000_000, 25_000_000}, 10),
		NewInformationRetentionBenchmark(1000, nil),
	}, "extreme_scale")
}

// BenchmarkSuiteQuick creates a quick benchmark suite for fast iteration.
//
// Small test set for rapid feedback during development.
func BenchmarkSuiteQuick() *BenchmarkSuite {
	return NewBenchmarkSuite([]Benchmark{
		NewSimpleQABenchmark(),
		NewNeedleInHaystackBenchmark(1_000, 3, 10),
	}, "quick")
}

// GenerateAllTestCases generates all test cases from all benchmarks.
//
// Returns:
//
//	Combined list of test cases from all benchmarks
func (s *BenchmarkSuite) GenerateAllTestCases() ([]map[string]interface{}, error) {
	allCases := make([]map[string]interface{}, 0)

	for _, benchmark := range s.benchmarks {
		cases, err := benchmark.GenerateTestCases()
		if err != nil {
			return nil, err
		}

		// Convert to map format and tag with benchmark name
		for _, testCase := range cases {
			caseMap := map[string]interface{}{
				"input":    testCase.Input,
				"expected": testCase.Expected,
				"metadata": testCase.Metadata,
				"tags":     testCase.Tags,
			}

			// Add benchmark metadata
			if caseMap["metadata"] == nil {
				caseMap["metadata"] = make(map[string]interface{})
			}
			metadata := caseMap["metadata"].(map[string]interface{})
			metadata["benchmark_name"] = benchmark.Name()
			metadata["suite_name"] = s.suiteName

			allCases = append(allCases, caseMap)
		}
	}

	return allCases, nil
}

// GetBenchmark gets benchmark by name.
func (s *BenchmarkSuite) GetBenchmark(name string) Benchmark {
	for _, benchmark := range s.benchmarks {
		if benchmark.Name() == name {
			return benchmark
		}
	}
	return nil
}

// AddBenchmark adds benchmark to suite.
func (s *BenchmarkSuite) AddBenchmark(benchmark Benchmark) {
	s.benchmarks = append(s.benchmarks, benchmark)
}

// RemoveBenchmark removes benchmark from suite.
func (s *BenchmarkSuite) RemoveBenchmark(name string) {
	filtered := make([]Benchmark, 0)
	for _, b := range s.benchmarks {
		if b.Name() != name {
			filtered = append(filtered, b)
		}
	}
	s.benchmarks = filtered
}

// ToDict converts suite to dictionary.
func (s *BenchmarkSuite) ToDict() map[string]interface{} {
	benchmarkInfos := make([]map[string]string, 0)
	for _, b := range s.benchmarks {
		benchmarkInfos = append(benchmarkInfos, map[string]string{
			"name":        b.Name(),
			"description": b.Description(),
		})
	}

	return map[string]interface{}{
		"suite_name": s.suiteName,
		"benchmarks": benchmarkInfos,
	}
}

// Helper function

func containsIntSlice(slice []int, value int) bool {
	for _, v := range slice {
		if v == value {
			return true
		}
	}
	return false
}
