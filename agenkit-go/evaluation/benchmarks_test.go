package evaluation

import (
	"context"
	"strings"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// echoAgent returns a fixed response, so a test's pass/fail depends only on the
// Expected value under test.
type echoAgent struct {
	response string
}

func (a *echoAgent) Name() string { return "echo" }

func (a *echoAgent) Capabilities() []string { return []string{"echo"} }

func (a *echoAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func (a *echoAgent) Process(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{Role: "agent", Content: a.response}, nil
}

// TestTestCaseValidateMatchesFragmentInProse checks the docs/DEFAULTS.md contract:
// Expected is the fact to look for, not the whole answer.
func TestTestCaseValidateMatchesFragmentInProse(t *testing.T) {
	tc := &TestCase{Input: "What is 15 + 27?", Expected: "42"}

	cases := []struct {
		actual string
		want   bool
	}{
		{"42", true},
		{"The answer is 42.", true},
		{"15 + 27 = 42, so the total is 42 items.", true},
		{"The answer is 41.", false},
		// A prefix of the fragment is not a match — the needle must appear whole.
		{"4", false},
	}

	for _, c := range cases {
		if got := tc.Validate(c.actual); got != c.want {
			t.Errorf("Validate(%q) = %v, want %v", c.actual, got, c.want)
		}
	}
}

// TestTestCaseValidateIsCaseInsensitive checks case-insensitivity across scripts.
//
// The non-ASCII cases are the regression: checkTest used to lower via a hand-rolled
// helper that only mapped ASCII A-Z, so a Greek or umlauted Expected failed there
// while AccuracyMetric (strings.ToLower) scored it 1.0 in the same run (#823).
func TestTestCaseValidateIsCaseInsensitive(t *testing.T) {
	cases := []struct {
		expected string
		actual   string
		want     bool
	}{
		{"Paris", "paris", true},
		{"Paris", "PARIS", true},
		{"Paris", "The capital is PaRiS.", true},
		{"Paris", "Lyon", false},
		// Non-ASCII: these are what the ASCII-only lowering got wrong.
		{"αθηνα", "ΑΘΗΝΑ is the capital", true},
		{"μοσχα", "MOSCOW is ΜΟΣΧΑ", true},
		{"öüä", "Ünïcode ÖÜÄ here", true},
		{"αθηνα", "Sparta", false},
	}

	for _, c := range cases {
		tc := &TestCase{Expected: c.expected}
		if got := tc.Validate(c.actual); got != c.want {
			t.Errorf("TestCase{Expected: %q}.Validate(%q) = %v, want %v",
				c.expected, c.actual, got, c.want)
		}
	}
}

// TestTestCaseValidateAgreesWithAccuracyMetric pins the two comparison sites
// together. They disagreed on non-ASCII case before this fix, and a second
// almost-identical implementation is exactly how #820's divergence arose.
func TestTestCaseValidateAgreesWithAccuracyMetric(t *testing.T) {
	metric := NewAccuracyMetric(nil, false)
	agent := &echoAgent{}

	pairs := []struct {
		expected string
		actual   string
	}{
		{"42", "The answer is 42."},
		{"42", "The answer is 41."},
		{"Paris", "the capital is PARIS"},
		{"αθηνα", "ΑΘΗΝΑ is the capital"},
		{"öüä", "Ünïcode ÖÜÄ here"},
		{"μοσχα", "Sparta"},
		{"", "anything at all"},
	}

	for _, p := range pairs {
		tc := &TestCase{Expected: p.expected}
		viaValidate := tc.Validate(p.actual)

		outputMsg := &agenkit.Message{Role: "agent", Content: p.actual}
		ctx := map[string]interface{}{"expected": p.expected}
		score, err := metric.Measure(agent, nil, outputMsg, ctx)
		if err != nil {
			t.Fatalf("Measure(%q, %q) returned error: %v", p.expected, p.actual, err)
		}
		viaMetric := score == 1.0

		if viaValidate != viaMetric {
			t.Errorf("expected %q vs actual %q: Validate=%v but AccuracyMetric=%v — "+
				"the two comparison sites disagree", p.expected, p.actual, viaValidate, viaMetric)
		}
	}
}

// TestTestCaseValidateEmptyExpectedMatchesAnything documents the contract in
// docs/DEFAULTS.md: strings.Contains(x, "") is true, so an empty Expected follows
// suit rather than being special-cased.
func TestTestCaseValidateEmptyExpectedMatchesAnything(t *testing.T) {
	tc := &TestCase{Expected: ""}

	if !tc.Validate("") {
		t.Error("empty Expected should match an empty output")
	}
	if !tc.Validate("anything at all") {
		t.Error("empty Expected should match any output")
	}
}

// TestTestCaseValidateNilExpectedPasses covers the case where nothing was asked
// for, matching Python's _check_test and TypeScript's checkTest.
func TestTestCaseValidateNilExpectedPasses(t *testing.T) {
	tc := &TestCase{Input: "no expectation"}

	if !tc.Validate("literally anything") {
		t.Error("a TestCase with no Expected value should pass")
	}
}

// TestTestCaseValidateValidatorFunc checks the escape hatch for exact or
// case-sensitive comparison.
func TestTestCaseValidateValidatorFunc(t *testing.T) {
	exact := func(actual interface{}) bool {
		s, ok := actual.(string)
		return ok && s == "Paris"
	}
	tc := &TestCase{Expected: exact}

	if !tc.Validate("Paris") {
		t.Error("validator should accept the exact string")
	}
	if tc.Validate("paris") {
		t.Error("validator should reject a case difference it did not allow")
	}
	if tc.Validate("The capital is Paris.") {
		t.Error("validator should reject a substring match it did not allow")
	}
}

// TestTestCaseValidateNonStringExpected covers the fmt %v fallback, matching
// AccuracyMetric's handling of a JSON number.
func TestTestCaseValidateNonStringExpected(t *testing.T) {
	tc := &TestCase{Expected: 42}

	if !tc.Validate("The answer is 42.") {
		t.Error("a numeric Expected should match its default-formatted form in the output")
	}
	if tc.Validate("The answer is 41.") {
		t.Error("a numeric Expected should not match a different number")
	}
}

// TestEvaluatorCheckTestUsesValidate verifies the runner's pass count reflects the
// contract, non-ASCII included — the end-to-end form of the #823 divergence.
func TestEvaluatorCheckTestUsesValidate(t *testing.T) {
	agent := &echoAgent{response: "ΑΘΗΝΑ is the capital"}
	evaluator := NewEvaluator(agent, nil, "")

	result, err := evaluator.Evaluate([]map[string]interface{}{
		{"input": "capital?", "expected": "αθηνα"},
	}, "")
	if err != nil {
		t.Fatalf("Evaluate returned error: %v", err)
	}

	if result.PassedTests != 1 || result.FailedTests != 0 {
		t.Errorf("passed=%d failed=%d, want passed=1 failed=0 — a non-ASCII expected "+
			"value must be matched case-insensitively, as AccuracyMetric already did",
			result.PassedTests, result.FailedTests)
	}
}

// TestEvaluatorCountsWrongAnswerAsFailed guards the pass count against drifting
// back to "the agent did not error".
func TestEvaluatorCountsWrongAnswerAsFailed(t *testing.T) {
	agent := &echoAgent{response: "Lyon"}
	evaluator := NewEvaluator(agent, nil, "")

	result, err := evaluator.Evaluate([]map[string]interface{}{
		{"input": "capital?", "expected": "Paris"},
	}, "")
	if err != nil {
		t.Fatalf("Evaluate returned error: %v", err)
	}

	if result.PassedTests != 0 || result.FailedTests != 1 {
		t.Errorf("passed=%d failed=%d, want passed=0 failed=1 — a wrong answer must "+
			"not count as a pass", result.PassedTests, result.FailedTests)
	}
	if result.SuccessRate() != 0.0 {
		t.Errorf("SuccessRate() = %v, want 0.0", result.SuccessRate())
	}
}

// TestBenchmarkExpectedValuesAreFragments checks the shipped benchmark data
// actually depends on substring matching, so the contract is not merely asserted
// in the abstract.
func TestBenchmarkExpectedValuesAreFragments(t *testing.T) {
	benchmark := NewSimpleQABenchmark()
	cases, err := benchmark.GenerateTestCases()
	if err != nil {
		t.Fatalf("GenerateTestCases returned error: %v", err)
	}
	if len(cases) == 0 {
		t.Fatal("expected at least one test case")
	}

	for _, tc := range cases {
		expected, ok := tc.Expected.(string)
		if !ok {
			continue
		}
		embedded := "Well, " + strings.ToUpper(expected) + ", as it happens."
		if !tc.Validate(embedded) {
			t.Errorf("expected %q should be found in %q", expected, embedded)
		}
	}
}
