package agenkit

import (
	"context"
	"testing"
)

// The distinction under test is that "not assessed" must survive construction
// as something other than "failed". A bool Passed cannot carry it, so these
// tests are mostly about what Verdict preserves that Passed throws away (#769).

func TestNotAssessedIsDistinguishableFromFailed(t *testing.T) {
	notChecked := NotAssessed("no ground truth")
	checkedAndWrong := NewVerificationResult(false, 0.0, "wrong answer")

	// Passed collapses them — which is why it cannot be the only signal.
	if notChecked.Passed != checkedAndWrong.Passed {
		t.Fatalf("precondition: both should report Passed=false, got %v and %v",
			notChecked.Passed, checkedAndWrong.Passed)
	}

	// Verdict keeps them apart.
	if notChecked.Verdict == checkedAndWrong.Verdict {
		t.Errorf("not-assessed and failed share verdict %q; the third state is lost",
			notChecked.Verdict)
	}
	if notChecked.Verdict != VerdictNotAssessed {
		t.Errorf("Verdict = %q, want VerdictNotAssessed", notChecked.Verdict)
	}
	if checkedAndWrong.Verdict != VerdictFailed {
		t.Errorf("Verdict = %q, want VerdictFailed", checkedAndWrong.Verdict)
	}
}

func TestZeroValueAssertsNothing(t *testing.T) {
	// A VerificationResult{} must not claim the answer is wrong. This is why
	// VerdictNotAssessed is the empty string: it is also the zero value.
	var result VerificationResult

	if result.Verdict != VerdictNotAssessed {
		t.Errorf("zero Verdict = %q, want VerdictNotAssessed", result.Verdict)
	}
	if result.Verdict == VerdictFailed {
		t.Error("zero value reads as failed; that is a claim nobody made")
	}
	if result.Assessed() {
		t.Error("Assessed() = true for the zero value, want false")
	}
}

func TestAssessed(t *testing.T) {
	tests := []struct {
		name string
		res  VerificationResult
		want bool
	}{
		{"passed", NewVerificationResult(true, 1.0, ""), true},
		{"failed", NewVerificationResult(false, 0.0, ""), true},
		{"not assessed", NotAssessed(""), false},
		{"zero value", VerificationResult{}, false},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.res.Assessed(); got != tt.want {
				t.Errorf("Assessed() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestScoreZeroDoesNotImplyNotAssessed(t *testing.T) {
	// 0.0 is both the zero value and a legitimate score, so it cannot be used
	// to detect "unset". This is the sentinel collision Verdict replaces.
	scoredZero := NewVerificationResult(false, 0.0, "scored zero")
	unassessed := NotAssessed("")

	if scoredZero.Score != unassessed.Score {
		t.Fatalf("precondition: both scores should be 0.0, got %v and %v",
			scoredZero.Score, unassessed.Score)
	}
	if scoredZero.Verdict == unassessed.Verdict {
		t.Error("identical scores produced identical verdicts; read the verdict, not the score")
	}
}

func TestNewVerificationResultKeepsFieldsConsistent(t *testing.T) {
	tests := []struct {
		passed      bool
		wantVerdict Verdict
	}{
		{true, VerdictPassed},
		{false, VerdictFailed},
	}
	for _, tt := range tests {
		got := NewVerificationResult(tt.passed, 0.5, "reason")
		if got.Verdict != tt.wantVerdict {
			t.Errorf("NewVerificationResult(%v).Verdict = %q, want %q",
				tt.passed, got.Verdict, tt.wantVerdict)
		}
		if got.Passed != tt.passed {
			t.Errorf("NewVerificationResult(%v).Passed = %v, want %v",
				tt.passed, got.Passed, tt.passed)
		}
		// The invariant that ties the two together.
		if got.Passed != (got.Verdict == VerdictPassed) {
			t.Errorf("Passed=%v disagrees with Verdict=%q", got.Passed, got.Verdict)
		}
		if got.Score != 0.5 || got.Reason != "reason" {
			t.Errorf("Score/Reason not carried through: %+v", got)
		}
	}
}

func TestNotAssessedNeverReportsPassed(t *testing.T) {
	// A caller asking a yes/no question about an unverified answer cannot be
	// told "yes".
	if NotAssessed("skipped").Passed {
		t.Error("NotAssessed().Passed = true, want false")
	}
	if got := NotAssessed("skipped").Reason; got != "skipped" {
		t.Errorf("Reason = %q, want %q", got, "skipped")
	}
}

func TestVerdictWireValuesMatchOTELConvention(t *testing.T) {
	// docs/OTEL_CONVENTION.md specifies agenkit.verifier.verdict as exactly
	// these three strings. A verdict must be recordable on a span without
	// translation, so String() spells the zero value out rather than emitting "".
	tests := []struct {
		verdict Verdict
		want    string
	}{
		{VerdictPassed, "passed"},
		{VerdictFailed, "failed"},
		{VerdictNotAssessed, "not_assessed"},
	}
	for _, tt := range tests {
		if got := tt.verdict.String(); got != tt.want {
			t.Errorf("Verdict(%q).String() = %q, want %q", string(tt.verdict), got, tt.want)
		}
	}

	// The zero value must not emit an empty attribute.
	var zero Verdict
	if zero.String() != "not_assessed" {
		t.Errorf("zero Verdict String() = %q, want \"not_assessed\"", zero.String())
	}
}

// partialVerifier only knows the answer to one question. Everything else it
// declines to assess rather than failing.
type partialVerifier struct{}

func (partialVerifier) Verify(_ context.Context, question, answer string) (VerificationResult, error) {
	if question != "2+2" {
		return NotAssessed("no ground truth for " + question), nil
	}
	return NewVerificationResult(answer == "4", 1.0, ""), nil
}

func TestVerifierCanReportNotAssessed(t *testing.T) {
	// A verifier with no ground truth must be able to say so without asserting
	// the answer is wrong — the round-trip quarry needs (#711).
	var v Verifier = partialVerifier{}
	ctx := context.Background()

	knownGood, err := v.Verify(ctx, "2+2", "4")
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	if knownGood.Verdict != VerdictPassed {
		t.Errorf("Verdict = %q, want VerdictPassed", knownGood.Verdict)
	}

	knownBad, err := v.Verify(ctx, "2+2", "5")
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	if knownBad.Verdict != VerdictFailed {
		t.Errorf("Verdict = %q, want VerdictFailed", knownBad.Verdict)
	}

	unknown, err := v.Verify(ctx, "meaning of life", "42")
	if err != nil {
		t.Fatalf("Verify: %v", err)
	}
	if unknown.Assessed() {
		t.Error("Assessed() = true for an unverifiable question, want false")
	}
	// The caller can tell this apart from knownBad, which is the requirement.
	if unknown.Verdict == knownBad.Verdict {
		t.Errorf("unverifiable and incorrect share verdict %q", unknown.Verdict)
	}
}

func TestLegacyStructLiteralStillCompiles(t *testing.T) {
	// Existing call sites construct the struct directly; Verdict is additive,
	// so they must keep working. Such a literal leaves Verdict at its zero
	// value, so Passed and Verdict can disagree — which is exactly why the
	// constructors exist and the doc comment says to prefer them.
	legacy := VerificationResult{Passed: true, Score: 1.0}

	if !legacy.Passed {
		t.Error("Passed = false, want true")
	}
	if legacy.Verdict != VerdictNotAssessed {
		t.Errorf("Verdict = %q; a bare literal leaves it at the zero value", legacy.Verdict)
	}
	// Documented consequence, pinned so a future change to the zero value has
	// to confront it: this is the one construction where the two disagree.
	if legacy.Passed == (legacy.Verdict == VerdictPassed) {
		t.Error("expected the legacy literal to be the inconsistent case")
	}
}
