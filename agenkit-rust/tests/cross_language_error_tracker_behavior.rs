//! Cross-language error tracker behavior tests for Rust.
//!
//! Validates that Agenkit's Rust `ErrorTracker` (p_a / P_error) behaves
//! consistently with the cross-language error tracker behavior specification
//! (#652, follow-up to #321).

use agenkit::evaluation::error_tracker::ErrorTracker;
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Deserialize)]
struct ErrorTrackerTestCase {
    id: String,
    #[allow(dead_code)]
    name: String,
    #[serde(default)]
    steps: Option<Vec<bool>>,
    #[serde(default)]
    steps_spec: Option<StepsSpec>,
    expected: ExpectedBehavior,
}

#[derive(Debug, Deserialize)]
struct StepsSpec {
    fail: usize,
    success: usize,
}

#[derive(Debug, Deserialize)]
struct ExpectedBehavior {
    total_steps: usize,
    failed_steps: usize,
    per_step_error_rate: f64,
    cumulative_failure_probability_observed: Option<f64>,
    cumulative_failure_probability_steps: HashMap<String, f64>,
    tolerance: Option<f64>,
}

#[derive(Debug, Deserialize)]
struct ErrorTrackerFixtures {
    #[allow(dead_code)]
    version: String,
    #[allow(dead_code)]
    description: String,
    test_cases: Vec<ErrorTrackerTestCase>,
}

fn load_fixtures() -> ErrorTrackerFixtures {
    let mut fixtures_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    fixtures_path.pop(); // Go up to agenkit/
    fixtures_path.push("tests/cross_language/fixtures/error_tracker_behavior.json");

    let data = fs::read_to_string(&fixtures_path)
        .unwrap_or_else(|e| panic!("Failed to read fixtures from {:?}: {}", fixtures_path, e));

    serde_json::from_str(&data).expect("Failed to parse fixtures JSON")
}

fn build_steps(test_case: &ErrorTrackerTestCase) -> Vec<bool> {
    if let Some(steps) = &test_case.steps {
        return steps.clone();
    }
    let spec = test_case
        .steps_spec
        .as_ref()
        .expect("test case must have steps or steps_spec");
    let mut steps = Vec::with_capacity(spec.fail + spec.success);
    steps.extend(std::iter::repeat(false).take(spec.fail));
    steps.extend(std::iter::repeat(true).take(spec.success));
    steps
}

#[test]
fn test_error_tracker_behavior_matches_fixture() {
    let fixtures = load_fixtures();
    assert!(!fixtures.test_cases.is_empty());

    for test_case in &fixtures.test_cases {
        let expected = &test_case.expected;
        let tolerance = expected.tolerance.unwrap_or(1e-6);

        let mut tracker = ErrorTracker::new(true);
        for success in build_steps(test_case) {
            tracker.record_step(success);
        }

        assert_eq!(
            tracker.total_steps(),
            expected.total_steps,
            "[{}] total_steps",
            test_case.id
        );
        assert_eq!(
            tracker.failed_steps(),
            expected.failed_steps,
            "[{}] failed_steps",
            test_case.id
        );
        assert!(
            (tracker.per_step_error_rate() - expected.per_step_error_rate).abs() <= tolerance,
            "[{}] per_step_error_rate: expected {}, got {}",
            test_case.id,
            expected.per_step_error_rate,
            tracker.per_step_error_rate()
        );

        if let Some(expected_observed) = expected.cumulative_failure_probability_observed {
            let observed = tracker.cumulative_failure_probability(None);
            assert!(
                (observed - expected_observed).abs() <= tolerance,
                "[{}] cumulative_failure_probability_observed: expected {}, got {}",
                test_case.id,
                expected_observed,
                observed
            );
        }

        for (steps_str, expected_p) in &expected.cumulative_failure_probability_steps {
            let n: usize = steps_str.parse().expect("steps key must be numeric");
            let got = tracker.cumulative_failure_probability(Some(n));
            assert!(
                (got - expected_p).abs() <= tolerance,
                "[{}] cumulative_failure_probability_steps[{}]: expected {}, got {}",
                test_case.id,
                n,
                expected_p,
                got
            );
        }
    }
}
