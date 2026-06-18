//! Error Tracking — per-step error rate and failure compounding.
//!
//! Long-running agents execute many steps; even a small per-step error rate
//! compounds into a high probability of at least one failure over a long run.
//! [`ErrorTracker`] records the outcome of each step and exposes the two core
//! quantities from the agent-failure-rate analysis:
//!
//! - `p_a` ([`ErrorTracker::per_step_error_rate`]) — the per-step error rate,
//!   `failed_steps / total_steps`.
//! - `P_error` ([`ErrorTracker::cumulative_failure_probability`]) — the
//!   probability of at least one failure across `n` independent steps,
//!   `1 - (1 - p_a).powi(n)`. With `None`, `n` is the number of recorded steps
//!   (observed cumulative failure probability); pass `Some(N)` to project the
//!   compounding over a planned run of `N` steps.
//!
//! Tracking is opt-in: construct an `ErrorTracker::new(true)` and call
//! [`ErrorTracker::record_step`] as steps complete. When disabled (the
//! default), `record_step` is a no-op and the metrics report zero, so the
//! tracker is cheap to leave wired in.
//!
//! # Example
//!
//! ```
//! use agenkit::evaluation::error_tracker::ErrorTracker;
//!
//! let mut tracker = ErrorTracker::new(true);
//! tracker.record_step(true);
//! tracker.record_step(false);
//! assert_eq!(tracker.per_step_error_rate(), 0.5);
//! ```

/// Outcome of a single agent step.
#[derive(Debug, Clone)]
pub struct StepResult {
    /// Whether the step completed without error.
    pub success: bool,
    /// Optional step label (useful for per-step breakdowns later).
    pub name: Option<String>,
    /// Optional error description when `success` is `false`.
    pub error: Option<String>,
}

impl StepResult {
    /// Creates a step result with optional `name` and `error`.
    pub fn new(success: bool, name: Option<String>, error: Option<String>) -> Self {
        Self {
            success,
            name,
            error,
        }
    }
}

/// Records step outcomes and computes error-rate / compounding metrics.
///
/// When `enabled` is `false` (the default), [`record_step`](Self::record_step)
/// is a no-op and all metrics report `0.0` / `0` — tracking is strictly opt-in.
#[derive(Debug, Clone, Default)]
pub struct ErrorTracker {
    enabled: bool,
    step_results: Vec<StepResult>,
}

impl ErrorTracker {
    /// Creates a new tracker.
    ///
    /// # Arguments
    ///
    /// * `enabled` - When `false`, [`record_step`](Self::record_step) is a
    ///   no-op and all metrics report zero.
    pub fn new(enabled: bool) -> Self {
        Self {
            enabled,
            step_results: Vec::new(),
        }
    }

    /// Records the outcome of one step (no-op when disabled).
    ///
    /// Convenience for the common case of recording only success/failure. To
    /// attach a step label or error description, use [`record`](Self::record).
    pub fn record_step(&mut self, success: bool) {
        self.record(StepResult::new(success, None, None));
    }

    /// Records a fully-specified step result (no-op when disabled).
    ///
    /// Mirrors the Python `record_step(success, *, name, error)` signature via
    /// a [`StepResult`] argument.
    pub fn record(&mut self, result: StepResult) {
        if !self.enabled {
            return;
        }
        self.step_results.push(result);
    }

    /// Number of recorded steps.
    pub fn total_steps(&self) -> usize {
        self.step_results.len()
    }

    /// Number of recorded steps that failed.
    pub fn failed_steps(&self) -> usize {
        self.step_results.iter().filter(|r| !r.success).count()
    }

    /// Per-step error rate `p_a` = `failed_steps / total_steps`.
    ///
    /// Returns `0.0` when no steps have been recorded.
    pub fn per_step_error_rate(&self) -> f64 {
        let total = self.total_steps();
        if total == 0 {
            return 0.0;
        }
        self.failed_steps() as f64 / total as f64
    }

    /// Probability of at least one failure over `steps` steps.
    ///
    /// `P_error = 1 - (1 - p_a).powi(n)` where `n` is `steps` if given,
    /// otherwise the number of recorded steps. Models error compounding:
    /// independent steps each succeed with probability `1 - p_a`, so the run
    /// succeeds only if all `n` succeed.
    ///
    /// # Arguments
    ///
    /// * `steps` - Project the compounding over this many steps. Defaults
    ///   (`None`) to the number of recorded steps (observed cumulative
    ///   probability).
    ///
    /// Returns a probability in `[0.0, 1.0]`. Returns `0.0` if `p_a` is 0 or
    /// `n == 0`.
    pub fn cumulative_failure_probability(&self, steps: Option<usize>) -> f64 {
        let n = steps.unwrap_or_else(|| self.total_steps());
        if n == 0 {
            return 0.0;
        }
        let p_a = self.per_step_error_rate();
        1.0 - (1.0 - p_a).powi(n as i32)
    }

    /// Clears all recorded step results.
    pub fn reset(&mut self) {
        self.step_results.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const EPSILON: f64 = 1e-9;

    fn approx(a: f64, b: f64) {
        assert!((a - b).abs() < EPSILON, "expected {b}, got {a}");
    }

    #[test]
    fn test_default_disabled() {
        let mut tracker = ErrorTracker::default();
        tracker.record_step(false);
        tracker.record_step(true);
        // Disabled: nothing recorded.
        assert_eq!(tracker.total_steps(), 0);
        assert_eq!(tracker.failed_steps(), 0);
        approx(tracker.per_step_error_rate(), 0.0);
    }

    #[test]
    fn test_disabled_no_op() {
        let mut tracker = ErrorTracker::new(false);
        for _ in 0..10 {
            tracker.record_step(false);
        }
        assert_eq!(tracker.total_steps(), 0);
        approx(tracker.cumulative_failure_probability(Some(100)), 0.0);
    }

    #[test]
    fn test_per_step_error_rate_empty() {
        let tracker = ErrorTracker::new(true);
        approx(tracker.per_step_error_rate(), 0.0);
    }

    #[test]
    fn test_per_step_error_rate_all_pass() {
        let mut tracker = ErrorTracker::new(true);
        for _ in 0..4 {
            tracker.record_step(true);
        }
        approx(tracker.per_step_error_rate(), 0.0);
    }

    #[test]
    fn test_per_step_error_rate_all_fail() {
        let mut tracker = ErrorTracker::new(true);
        for _ in 0..4 {
            tracker.record_step(false);
        }
        approx(tracker.per_step_error_rate(), 1.0);
    }

    #[test]
    fn test_per_step_error_rate_mixed() {
        let mut tracker = ErrorTracker::new(true);
        tracker.record_step(true);
        tracker.record_step(false);
        tracker.record_step(true);
        tracker.record_step(true);
        // 1 failure out of 4 => 0.25
        approx(tracker.per_step_error_rate(), 0.25);
    }

    #[test]
    fn test_compounding_one_percent_over_hundred() {
        // p_a = 0.01 observed over 100 steps -> ~0.634.
        let mut tracker = ErrorTracker::new(true);
        tracker.record(StepResult::new(false, None, Some("boom".to_string())));
        for _ in 0..99 {
            tracker.record_step(true);
        }
        approx(tracker.per_step_error_rate(), 0.01);
        let p = tracker.cumulative_failure_probability(None);
        assert!((p - 0.634).abs() < 1e-3, "expected ~0.634, got {p}");
    }

    #[test]
    fn test_compounding_projected() {
        // p_a = 0.01, project over 100 steps.
        let mut tracker = ErrorTracker::new(true);
        tracker.record_step(false);
        for _ in 0..99 {
            tracker.record_step(true);
        }
        let projected = tracker.cumulative_failure_probability(Some(100));
        approx(projected, 1.0 - 0.99_f64.powi(100));
        assert!((projected - 0.634).abs() < 1e-3);
    }

    #[test]
    fn test_compounding_observed() {
        // Observed: n = total recorded steps (2), p_a = 0.5.
        let mut tracker = ErrorTracker::new(true);
        tracker.record_step(true);
        tracker.record_step(false);
        let observed = tracker.cumulative_failure_probability(None);
        approx(observed, 1.0 - 0.5_f64.powi(2)); // 0.75
    }

    #[test]
    fn test_compounding_zero_rate() {
        let mut tracker = ErrorTracker::new(true);
        for _ in 0..10 {
            tracker.record_step(true);
        }
        approx(tracker.cumulative_failure_probability(None), 0.0);
        approx(tracker.cumulative_failure_probability(Some(1000)), 0.0);
    }

    #[test]
    fn test_compounding_full_rate() {
        let mut tracker = ErrorTracker::new(true);
        for _ in 0..3 {
            tracker.record_step(false);
        }
        // p_a = 1.0 -> 1 - 0^n = 1.0
        approx(tracker.cumulative_failure_probability(None), 1.0);
        approx(tracker.cumulative_failure_probability(Some(5)), 1.0);
    }

    #[test]
    fn test_compounding_n_zero() {
        let mut tracker = ErrorTracker::new(true);
        tracker.record_step(false);
        // Explicit n == 0 short-circuits to 0.0 even with p_a > 0.
        approx(tracker.cumulative_failure_probability(Some(0)), 0.0);
        // Observed n == 0 when nothing recorded.
        let empty = ErrorTracker::new(true);
        approx(empty.cumulative_failure_probability(None), 0.0);
    }

    #[test]
    fn test_compounding_in_unit_interval() {
        // Invariant: P_error is always within [0.0, 1.0].
        let mut tracker = ErrorTracker::new(true);
        tracker.record_step(false);
        tracker.record_step(true);
        tracker.record_step(false);
        tracker.record_step(true);
        tracker.record_step(true);
        for n in [0usize, 1, 5, 10, 100, 10_000] {
            let p = tracker.cumulative_failure_probability(Some(n));
            assert!(
                (0.0..=1.0).contains(&p),
                "P_error {p} out of [0,1] for n={n}"
            );
        }
    }

    #[test]
    fn test_record_with_name_and_error() {
        let mut tracker = ErrorTracker::new(true);
        tracker.record(StepResult::new(
            false,
            Some("fetch".to_string()),
            Some("timeout".to_string()),
        ));
        assert_eq!(tracker.total_steps(), 1);
        assert_eq!(tracker.failed_steps(), 1);
    }

    #[test]
    fn test_reset() {
        let mut tracker = ErrorTracker::new(true);
        tracker.record_step(false);
        tracker.record_step(true);
        assert_eq!(tracker.total_steps(), 2);
        tracker.reset();
        assert_eq!(tracker.total_steps(), 0);
        assert_eq!(tracker.failed_steps(), 0);
        approx(tracker.per_step_error_rate(), 0.0);
        // Still enabled after reset.
        tracker.record_step(false);
        assert_eq!(tracker.total_steps(), 1);
    }
}
