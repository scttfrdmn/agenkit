package evaluation

import (
	"context"
	"fmt"
	"testing"

	"github.com/scttfrdmn/agenkit/agenkit-go/agenkit"
)

// cannedAgent answers every prompt with the same reply.
type cannedAgent struct {
	reply string
}

func (a *cannedAgent) Name() string { return "canned" }

func (a *cannedAgent) Capabilities() []string { return []string{"canned"} }

func (a *cannedAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func (a *cannedAgent) Process(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
	return &agenkit.Message{Role: "agent", Content: a.reply}, nil
}

// failingAgent returns (nil, err), which is what every Agent in this repo does on
// failure. ContentString dereferences its receiver, so any unguarded read of the
// response panics.
type failingAgent struct{}

func (a *failingAgent) Name() string { return "failing" }

func (a *failingAgent) Capabilities() []string { return []string{"failing"} }

func (a *failingAgent) Introspect() *agenkit.IntrospectionResult {
	return agenkit.DefaultIntrospectionResult(a)
}

func (a *failingAgent) Process(_ context.Context, _ *agenkit.Message) (*agenkit.Message, error) {
	return nil, fmt.Errorf("upstream is down")
}

func newTest(control, treatment agenkit.Agent) *ABTest {
	return NewABTest("t", control, treatment, nil, SignificanceLevel005, TestTypeTTest)
}

// TestABTestScoresCorrectButVerboseAgent covers the docs/DEFAULTS.md contract at the
// A/B scoring site: Expected is a fragment to find, so an agent answering in prose
// must score 1.0. Every benchmark in this package stores fragments ("4", "Paris",
// ALPHA-0000-OMEGA), so getting this wrong makes A/B runs over the package's own data
// measure nothing (#822).
func TestABTestScoresCorrectButVerboseAgent(t *testing.T) {
	cases := []map[string]interface{}{
		{"input": "What is 2+2?", "expected": "4"},
		{"input": "What is 3+1?", "expected": "4"},
	}

	ab := newTest(&cannedAgent{reply: "Well, the answer is 4."}, &cannedAgent{reply: "No idea."})
	results, err := ab.Run(cases, 0, false)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	got := results["accuracy"]
	if got.ControlVariant.Mean() != 1.0 {
		t.Errorf("verbose-but-correct control mean = %v, want 1.0", got.ControlVariant.Mean())
	}
	if got.TreatmentVariant.Mean() != 0.0 {
		t.Errorf("wrong treatment mean = %v, want 0.0", got.TreatmentVariant.Mean())
	}
}

// TestABTestScoringIsUnicodeAware pins the bug this replaced. The old hand-rolled
// stringToLower built its buffer with make([]rune, len(s)) — byte length — while
// ranging by byte offset, so every multi-byte rune left NUL padding:
//
//	"ПАРИЖ"   -> "П\x00А\x00Р\x00И\x00Ж\x00"
//	"Ähnlich" -> "Ä\x00hnlich"
//
// A Cyrillic or umlauted Expected therefore scored 0.0 for *both* arms, which reports
// no winner while looking like a completed experiment.
func TestABTestScoringIsUnicodeAware(t *testing.T) {
	for _, tc := range []struct{ expected, reply string }{
		{"paris", "Naturally, PARIS."},
		{"москва", "Ответ: МОСКВА"},
		{"ähnlich", "Das ist ÄHNLICH."},
		{"café", "The CAFÉ on the corner."},
	} {
		t.Run(tc.expected, func(t *testing.T) {
			agent := &cannedAgent{reply: tc.reply}
			ab := newTest(agent, agent)

			results, err := ab.Run([]map[string]interface{}{
				{"input": "q", "expected": tc.expected},
			}, 0, false)
			if err != nil {
				t.Fatalf("Run: %v", err)
			}

			if mean := results["accuracy"].ControlVariant.Mean(); mean != 1.0 {
				t.Errorf("expected %q in reply %q scored %v, want 1.0",
					tc.expected, tc.reply, mean)
			}
		})
	}
}

// TestABTestScoringAgreesWithTestCaseValidate checks the two Go comparison paths do
// not drift. The A/B site now delegates to TestCase.Validate; this fails if it is ever
// open-coded again.
func TestABTestScoringAgreesWithTestCaseValidate(t *testing.T) {
	for _, tc := range []struct{ expected, reply string }{
		{"4", "The answer is 4."},
		{"Paris", "paris, of course"},
		{"москва", "Ответ: МОСКВА"},
		{"Jupiter", "Saturn"},
		{"", "anything at all"},
	} {
		agent := &cannedAgent{reply: tc.reply}
		ab := newTest(agent, agent)

		results, err := ab.Run([]map[string]interface{}{
			{"input": "q", "expected": tc.expected},
		}, 0, false)
		if err != nil {
			t.Fatalf("Run(%q): %v", tc.expected, err)
		}

		want := 0.0
		if (&TestCase{Expected: tc.expected}).Validate(tc.reply) {
			want = 1.0
		}

		if got := results["accuracy"].ControlVariant.Mean(); got != want {
			t.Errorf("ab score for expected=%q reply=%q = %v, TestCase.Validate says %v",
				tc.expected, tc.reply, got, want)
		}
	}
}

// TestABTestSurvivesAnErroringAgent is a regression test for a hard SIGSEGV. The
// results map called response.ContentString() unconditionally, outside the err == nil
// branch, so any agent whose Process failed crashed the process — the one case an A/B
// comparison most needs to survive, since a broken treatment arm is a normal outcome.
func TestABTestSurvivesAnErroringAgent(t *testing.T) {
	ab := newTest(&cannedAgent{reply: "4"}, &failingAgent{})

	results, err := ab.Run([]map[string]interface{}{
		{"input": "What is 2+2?", "expected": "4"},
	}, 0, false)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	got := results["accuracy"]
	if got.ControlVariant.Mean() != 1.0 {
		t.Errorf("control mean = %v, want 1.0", got.ControlVariant.Mean())
	}
	if got.TreatmentVariant.Mean() != 0.0 {
		t.Errorf("erroring treatment mean = %v, want 0.0", got.TreatmentVariant.Mean())
	}
}

// TestABTestErroringAgentScoresZeroEvenWithNoExpected guards the err check on the
// accuracy branch specifically. With a non-empty Expected a failed Process is caught
// anyway, because actual is "" and Validate finds nothing — so dropping the err check
// would still look correct. An absent Expected matches anything (docs/DEFAULTS.md), so
// only this case distinguishes "did not answer" from "answered acceptably".
func TestABTestErroringAgentScoresZeroEvenWithNoExpected(t *testing.T) {
	ab := newTest(&cannedAgent{reply: "4"}, &failingAgent{})

	results, err := ab.Run([]map[string]interface{}{{"input": "q"}}, 0, false)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	if mean := results["accuracy"].TreatmentVariant.Mean(); mean != 0.0 {
		t.Errorf("a failed Process with no expected scored %v, want 0.0", mean)
	}
}

// TestABTestMissingExpectedKeyScoresAsSuccess pins current behaviour rather than
// endorsing it: an absent Expected counts as a pass, matching Python's A/B site.
// TypeScript scores it 0.0 for the identical case. Converging the two is #827, which
// is why this asserts today's answer and points at the issue instead of picking a
// third one here.
func TestABTestMissingExpectedKeyScoresAsSuccess(t *testing.T) {
	agent := &cannedAgent{reply: "whatever"}
	ab := newTest(agent, agent)

	results, err := ab.Run([]map[string]interface{}{{"input": "q"}}, 0, false)
	if err != nil {
		t.Fatalf("Run: %v", err)
	}

	if mean := results["accuracy"].ControlVariant.Mean(); mean != 1.0 {
		t.Errorf("absent expected scored %v, want 1.0 (see #827)", mean)
	}
}

// TestABTestRecordsActualResponse checks the "actual" field still carries the
// response, since it is now read through a local rather than a second
// ContentString() call.
func TestABTestRecordsActualResponse(t *testing.T) {
	ab := newTest(&cannedAgent{reply: "The answer is 4."}, &failingAgent{})

	control, err := ab.evaluateVariant(context.Background(), ab.Control,
		[]map[string]interface{}{{"input": "q", "expected": "4"}})
	if err != nil {
		t.Fatalf("evaluateVariant: %v", err)
	}
	if got := control[0]["actual"]; got != "The answer is 4." {
		t.Errorf("actual = %q, want the agent's reply", got)
	}

	// A failed Process has no response to record; it must be empty, not a panic.
	treatment, err := ab.evaluateVariant(context.Background(), ab.Treatment,
		[]map[string]interface{}{{"input": "q", "expected": "4"}})
	if err != nil {
		t.Fatalf("evaluateVariant: %v", err)
	}
	if got := treatment[0]["actual"]; got != "" {
		t.Errorf("actual on error = %q, want empty", got)
	}
}
