// Error tracking infrastructure — per-step error rate and failure compounding.
//
// Long-running agents execute many steps; even a small per-step error rate
// compounds into a high probability of at least one failure over a long run.
// ErrorTracker records the outcome of each step and exposes the two core
// quantities from the agent-failure-rate analysis:
//
//   - p_a (PerStepErrorRate) — the per-step error rate, failedSteps / totalSteps.
//   - P_error (CumulativeFailureProbability) — the probability of at least one
//     failure across n independent steps, 1 - (1 - p_a)^n. With no argument, n is
//     the number of recorded steps (observed cumulative failure probability); use
//     CumulativeFailureProbabilityOver(n) to project the compounding over a
//     planned run of n steps.
//
// Tracking is opt-in: construct an ErrorTracker with Enabled set to true and
// call RecordStep as steps complete. When disabled (the zero value), RecordStep
// is a no-op and the metrics report zero, so the tracker is cheap to leave
// wired in.

package evaluation

import "math"

// StepResult captures the outcome of a single agent step.
type StepResult struct {
	// Success reports whether the step completed without error.
	Success bool
	// Name is an optional step label (useful for per-step breakdowns later).
	Name string
	// Error is an optional error description when Success is false.
	Error string
}

// ErrorTracker records step outcomes and computes error-rate / compounding
// metrics. The zero value is a disabled tracker: RecordStep is a no-op and all
// metrics report 0.0/0. Tracking is strictly opt-in — set Enabled to true.
//
// Example:
//
//	tracker := &evaluation.ErrorTracker{Enabled: true}
//	tracker.RecordStep(true)
//	tracker.RecordStep(false, evaluation.WithStepError("timeout"))
//	tracker.PerStepErrorRate() // 0.5
//	tracker.CumulativeFailureProbabilityOver(10) // ≈ 0.999
type ErrorTracker struct {
	// Enabled gates recording. When false (the default), RecordStep is a no-op
	// and all metrics report 0.0/0.
	Enabled bool

	stepResults []StepResult
}

// RecordStepOption configures the optional fields of a recorded step.
type RecordStepOption func(*StepResult)

// WithStepName sets an optional step label.
func WithStepName(name string) RecordStepOption {
	return func(r *StepResult) { r.Name = name }
}

// WithStepError sets an optional error description for a failed step.
func WithStepError(errMsg string) RecordStepOption {
	return func(r *StepResult) { r.Error = errMsg }
}

// RecordStep records the outcome of one step (a no-op when disabled).
//
// Optional step metadata (name, error) can be supplied via WithStepName and
// WithStepError, mirroring the keyword-only arguments of the Python reference.
func (t *ErrorTracker) RecordStep(success bool, opts ...RecordStepOption) {
	if !t.Enabled {
		return
	}
	result := StepResult{Success: success}
	for _, opt := range opts {
		opt(&result)
	}
	t.stepResults = append(t.stepResults, result)
}

// TotalSteps returns the number of recorded steps.
func (t *ErrorTracker) TotalSteps() int {
	return len(t.stepResults)
}

// FailedSteps returns the number of recorded steps that failed.
func (t *ErrorTracker) FailedSteps() int {
	failed := 0
	for _, r := range t.stepResults {
		if !r.Success {
			failed++
		}
	}
	return failed
}

// PerStepErrorRate returns the per-step error rate p_a = failedSteps /
// totalSteps. It returns 0.0 when no steps have been recorded.
func (t *ErrorTracker) PerStepErrorRate() float64 {
	total := t.TotalSteps()
	if total == 0 {
		return 0.0
	}
	return float64(t.FailedSteps()) / float64(total)
}

// CumulativeFailureProbability returns the probability of at least one failure
// over the number of recorded steps (the observed cumulative probability). It
// returns 0.0 if no steps have been recorded or p_a is 0.
//
// To project the compounding over a planned run of n steps, use
// CumulativeFailureProbabilityOver.
func (t *ErrorTracker) CumulativeFailureProbability() float64 {
	return t.CumulativeFailureProbabilityOver(t.TotalSteps())
}

// CumulativeFailureProbabilityOver returns the probability of at least one
// failure over n steps: P_error = 1 - (1 - p_a)^n. It models error compounding:
// independent steps each succeed with probability 1 - p_a, so the run succeeds
// only if all n succeed.
//
// It returns 0.0 if n <= 0 or p_a is 0. The result lies in [0.0, 1.0].
func (t *ErrorTracker) CumulativeFailureProbabilityOver(n int) float64 {
	if n <= 0 {
		return 0.0
	}
	pA := t.PerStepErrorRate()
	return 1.0 - math.Pow(1.0-pA, float64(n))
}

// Reset clears all recorded step results.
func (t *ErrorTracker) Reset() {
	t.stepResults = nil
}
