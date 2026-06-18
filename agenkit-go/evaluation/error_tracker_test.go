package evaluation

import (
	"math"
	"testing"
)

const epsilon = 1e-9

func approxEqual(a, b float64) bool {
	return math.Abs(a-b) < epsilon
}

// ---------------------------------------------------------------------------
// StepResult
// ---------------------------------------------------------------------------

func TestStepResultDefaults(t *testing.T) {
	r := StepResult{Success: true}
	if !r.Success {
		t.Errorf("Success = %v, want true", r.Success)
	}
	if r.Name != "" {
		t.Errorf("Name = %q, want empty", r.Name)
	}
	if r.Error != "" {
		t.Errorf("Error = %q, want empty", r.Error)
	}
}

func TestStepResultFailureFields(t *testing.T) {
	r := StepResult{Success: false, Name: "fetch", Error: "timeout"}
	if r.Success {
		t.Errorf("Success = %v, want false", r.Success)
	}
	if r.Name != "fetch" {
		t.Errorf("Name = %q, want %q", r.Name, "fetch")
	}
	if r.Error != "timeout" {
		t.Errorf("Error = %q, want %q", r.Error, "timeout")
	}
}

// ---------------------------------------------------------------------------
// Opt-in / disabled behavior
// ---------------------------------------------------------------------------

func TestDisabledByDefaultRecordsNothing(t *testing.T) {
	tracker := &ErrorTracker{}
	if tracker.Enabled {
		t.Errorf("Enabled = %v, want false (zero value)", tracker.Enabled)
	}
	tracker.RecordStep(false, WithStepError("boom"))
	if tracker.TotalSteps() != 0 {
		t.Errorf("TotalSteps = %d, want 0", tracker.TotalSteps())
	}
	if tracker.FailedSteps() != 0 {
		t.Errorf("FailedSteps = %d, want 0", tracker.FailedSteps())
	}
	if got := tracker.PerStepErrorRate(); got != 0.0 {
		t.Errorf("PerStepErrorRate = %v, want 0.0", got)
	}
	if got := tracker.CumulativeFailureProbability(); got != 0.0 {
		t.Errorf("CumulativeFailureProbability = %v, want 0.0", got)
	}
}

func TestEnabledRecordsSteps(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(true)
	tracker.RecordStep(false, WithStepError("x"))
	if tracker.TotalSteps() != 2 {
		t.Errorf("TotalSteps = %d, want 2", tracker.TotalSteps())
	}
	if tracker.FailedSteps() != 1 {
		t.Errorf("FailedSteps = %d, want 1", tracker.FailedSteps())
	}
}

func TestRecordStepNameOption(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(false, WithStepName("fetch"), WithStepError("timeout"))
	if got := tracker.stepResults[0].Name; got != "fetch" {
		t.Errorf("Name = %q, want %q", got, "fetch")
	}
	if got := tracker.stepResults[0].Error; got != "timeout" {
		t.Errorf("Error = %q, want %q", got, "timeout")
	}
}

// ---------------------------------------------------------------------------
// PerStepErrorRate (p_a)
// ---------------------------------------------------------------------------

func TestPerStepErrorRateEmptyIsZero(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	if got := tracker.PerStepErrorRate(); got != 0.0 {
		t.Errorf("PerStepErrorRate = %v, want 0.0", got)
	}
}

func TestPerStepErrorRateAllSuccess(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	for i := 0; i < 5; i++ {
		tracker.RecordStep(true)
	}
	if got := tracker.PerStepErrorRate(); got != 0.0 {
		t.Errorf("PerStepErrorRate = %v, want 0.0", got)
	}
}

func TestPerStepErrorRateAllFail(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	for i := 0; i < 4; i++ {
		tracker.RecordStep(false)
	}
	if got := tracker.PerStepErrorRate(); got != 1.0 {
		t.Errorf("PerStepErrorRate = %v, want 1.0", got)
	}
}

func TestPerStepErrorRateMixed(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	// 2 failures out of 8 -> 0.25
	outcomes := []bool{true, false, true, true, false, true, true, true}
	for _, ok := range outcomes {
		tracker.RecordStep(ok)
	}
	if got := tracker.PerStepErrorRate(); !approxEqual(got, 0.25) {
		t.Errorf("PerStepErrorRate = %v, want 0.25", got)
	}
}

// ---------------------------------------------------------------------------
// CumulativeFailureProbability (P_error = 1 - (1 - p_a)^n)
// ---------------------------------------------------------------------------

func TestCumulativeEmptyIsZero(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	if got := tracker.CumulativeFailureProbability(); got != 0.0 {
		t.Errorf("CumulativeFailureProbability = %v, want 0.0", got)
	}
}

func TestCumulativeObservedUsesRecordedStepCount(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(true)
	tracker.RecordStep(false)
	// p_a = 0.5, n = 2 -> 1 - 0.5^2 = 0.75
	if got := tracker.CumulativeFailureProbability(); !approxEqual(got, 0.75) {
		t.Errorf("CumulativeFailureProbability = %v, want 0.75", got)
	}
}

func TestCumulativeProjectedSteps(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(true)
	tracker.RecordStep(false) // p_a = 0.5
	want := 1 - math.Pow(0.5, 10)
	if got := tracker.CumulativeFailureProbabilityOver(10); !approxEqual(got, want) {
		t.Errorf("CumulativeFailureProbabilityOver(10) = %v, want %v", got, want)
	}
}

func TestCumulativeCompoundingSmallRate(t *testing.T) {
	// The motivating case: a small per-step rate compounds over a long run.
	tracker := &ErrorTracker{Enabled: true}
	// p_a = 0.01 (1 failure in 100)
	tracker.RecordStep(false)
	for i := 0; i < 99; i++ {
		tracker.RecordStep(true)
	}
	if got := tracker.PerStepErrorRate(); !approxEqual(got, 0.01) {
		t.Errorf("PerStepErrorRate = %v, want 0.01", got)
	}
	// Over 100 steps: 1 - 0.99^100 ~= 0.634
	pError := tracker.CumulativeFailureProbabilityOver(100)
	want := 1 - math.Pow(0.99, 100)
	if !approxEqual(pError, want) {
		t.Errorf("CumulativeFailureProbabilityOver(100) = %v, want %v", pError, want)
	}
	if pError <= 0.63 || pError >= 0.64 {
		t.Errorf("P_error = %v, want 0.63 < P_error < 0.64", pError)
	}
}

func TestCumulativeZeroRateIsZero(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	for i := 0; i < 10; i++ {
		tracker.RecordStep(true)
	}
	if got := tracker.CumulativeFailureProbabilityOver(1000); got != 0.0 {
		t.Errorf("CumulativeFailureProbabilityOver(1000) = %v, want 0.0", got)
	}
}

func TestCumulativeFullRateIsOne(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(false)
	if got := tracker.CumulativeFailureProbabilityOver(5); !approxEqual(got, 1.0) {
		t.Errorf("CumulativeFailureProbabilityOver(5) = %v, want 1.0", got)
	}
}

func TestCumulativeNonpositiveStepsIsZero(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(false)
	if got := tracker.CumulativeFailureProbabilityOver(0); got != 0.0 {
		t.Errorf("CumulativeFailureProbabilityOver(0) = %v, want 0.0", got)
	}
	if got := tracker.CumulativeFailureProbabilityOver(-3); got != 0.0 {
		t.Errorf("CumulativeFailureProbabilityOver(-3) = %v, want 0.0", got)
	}
}

func TestCumulativeInUnitInterval(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	for _, ok := range []bool{true, false, true, false, false} {
		tracker.RecordStep(ok)
	}
	for n := 1; n < 50; n++ {
		p := tracker.CumulativeFailureProbabilityOver(n)
		if p < 0.0 || p > 1.0 {
			t.Errorf("CumulativeFailureProbabilityOver(%d) = %v, out of [0,1]", n, p)
		}
		if math.IsNaN(p) {
			t.Errorf("CumulativeFailureProbabilityOver(%d) = NaN", n)
		}
	}
}

// ---------------------------------------------------------------------------
// Reset + docstring example
// ---------------------------------------------------------------------------

func TestResetClearsSteps(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(true)
	tracker.RecordStep(false)
	tracker.Reset()
	if tracker.TotalSteps() != 0 {
		t.Errorf("TotalSteps = %d, want 0", tracker.TotalSteps())
	}
	if got := tracker.PerStepErrorRate(); got != 0.0 {
		t.Errorf("PerStepErrorRate = %v, want 0.0", got)
	}
}

func TestDocstringExampleValues(t *testing.T) {
	tracker := &ErrorTracker{Enabled: true}
	tracker.RecordStep(true)
	tracker.RecordStep(false, WithStepError("timeout"))
	if got := tracker.PerStepErrorRate(); got != 0.5 {
		t.Errorf("PerStepErrorRate = %v, want 0.5", got)
	}
	// round(P_error over 10, 4) == 0.999
	got := math.Round(tracker.CumulativeFailureProbabilityOver(10)*10000) / 10000
	if got != 0.999 {
		t.Errorf("rounded CumulativeFailureProbabilityOver(10) = %v, want 0.999", got)
	}
}
