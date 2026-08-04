//! Statistical A/B testing framework for agent comparison
//!
//! This module provides rigorous statistical testing for comparing agent versions.
//!
//! # Features
//!
//! - **Parametric tests**: t-test for normal distributions
//! - **Non-parametric tests**: Mann-Whitney for skewed distributions
//! - **Bootstrap CI**: Confidence intervals via resampling
//! - **Effect size**: Cohen's d for practical significance
//! - **Sample size calculator**: Plan experiments with appropriate power
//!
//! # Example
//!
//! ```no_run
//! use agenkit::evaluation::ab_testing::{ABTest, StatisticalTestType, SignificanceLevel};
//! use agenkit::core::Agent;
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let control_agent: Arc<dyn Agent> = todo!();
//! # let treatment_agent: Arc<dyn Agent> = todo!();
//! # let test_cases = vec![];
//! // Create A/B test with t-test and 95% confidence
//! let ab_test = ABTest::new(StatisticalTestType::TTest, SignificanceLevel::P005);
//!
//! // Run test
//! let result = ab_test.run(
//!     control_agent,
//!     treatment_agent,
//!     &test_cases,
//!     "accuracy"
//! ).await?;
//!
//! if result.is_significant {
//!     println!("Winner: {}", result.winner);
//!     println!("Effect size: {} (Cohen's d)", result.effect_size);
//! }
//! # Ok(())
//! # }
//! ```

use crate::core::{Agent, AgentError, Message};
use crate::evaluation::context_metrics::{ContextMetrics, LatencyMetric};
use crate::evaluation::core::Metric;
use crate::evaluation::quality_metrics::{AccuracyMetric, QualityMetrics};
use rand::RngExt;
use serde::{Deserialize, Serialize};
use statrs::distribution::{ContinuousCDF, Normal, StudentsT};
use statrs::statistics::Statistics;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Instant;

/// Statistical test types for A/B testing
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum StatisticalTestType {
    /// Student's t-test (parametric, assumes normal distribution)
    TTest,
    /// Mann-Whitney U test (non-parametric, robust to outliers)
    MannWhitney,
    /// Chi-square test (for categorical outcomes)
    ChiSquare,
    /// Bootstrap resampling (minimal assumptions)
    Bootstrap,
}

/// Significance levels (alpha) for hypothesis testing
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SignificanceLevel {
    /// 99.9% confidence (p < 0.001)
    P0001 = 1,
    /// 99% confidence (p < 0.01)
    P001 = 2,
    /// 95% confidence (p < 0.05) - Standard
    P005 = 5,
    /// 90% confidence (p < 0.10)
    P010 = 10,
}

impl SignificanceLevel {
    /// Get the alpha value (e.g., 0.05 for P005)
    pub fn alpha(&self) -> f64 {
        match self {
            SignificanceLevel::P0001 => 0.001,
            SignificanceLevel::P001 => 0.01,
            SignificanceLevel::P005 => 0.05,
            SignificanceLevel::P010 => 0.10,
        }
    }
}

/// Statistics for a single A/B test variant
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ABVariant {
    /// Variant name ("control" or "treatment")
    pub name: String,
    /// All measurement samples
    pub samples: Vec<f64>,
    /// Sample mean
    pub mean: f64,
    /// Sample standard deviation
    pub std_dev: f64,
    /// Number of samples
    pub sample_size: usize,
}

impl ABVariant {
    /// Create a new variant
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            samples: Vec::new(),
            mean: 0.0,
            std_dev: 0.0,
            sample_size: 0,
        }
    }

    /// Add a measurement sample
    pub fn add_sample(&mut self, value: f64) {
        self.samples.push(value);
    }

    /// Calculate statistics from samples
    pub fn calculate_statistics(&mut self) {
        if self.samples.is_empty() {
            return;
        }

        self.sample_size = self.samples.len();
        self.mean = self.samples.clone().mean();
        self.std_dev = self.samples.clone().std_dev();
    }
}

/// Results from an A/B test
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ABResult {
    /// Control variant statistics
    pub control: ABVariant,
    /// Treatment variant statistics
    pub treatment: ABVariant,
    /// P-value from statistical test
    pub p_value: f64,
    /// Effect size (Cohen's d)
    pub effect_size: f64,
    /// 95% confidence interval for difference
    pub confidence_interval: (f64, f64),
    /// Whether difference is statistically significant
    pub is_significant: bool,
    /// Winner variant name or "inconclusive"
    pub winner: String,
}

impl ABResult {
    /// Get summary string
    pub fn summary(&self) -> String {
        format!(
            "Control: {:.4} ± {:.4} (n={}), Treatment: {:.4} ± {:.4} (n={})\n\
             P-value: {:.6}, Effect size: {:.3}, Winner: {}",
            self.control.mean,
            self.control.std_dev,
            self.control.sample_size,
            self.treatment.mean,
            self.treatment.std_dev,
            self.treatment.sample_size,
            self.p_value,
            self.effect_size,
            self.winner
        )
    }
}

/// Test case for A/B testing
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCase {
    /// Input to agent
    pub input: String,
    /// Expected output
    pub expected: String,
    /// Additional metadata
    #[serde(default)]
    pub metadata: std::collections::HashMap<String, serde_json::Value>,
}

impl TestCase {
    /// Create a new test case
    pub fn new(input: impl Into<String>, expected: impl Into<String>) -> Self {
        Self {
            input: input.into(),
            expected: expected.into(),
            metadata: std::collections::HashMap::new(),
        }
    }
}

/// A/B testing framework
pub struct ABTest {
    test_type: StatisticalTestType,
    alpha: SignificanceLevel,
}

impl ABTest {
    /// Create a new A/B test
    ///
    /// # Arguments
    ///
    /// * `test_type` - Statistical test to use
    /// * `alpha` - Significance level
    pub fn new(test_type: StatisticalTestType, alpha: SignificanceLevel) -> Self {
        Self { test_type, alpha }
    }

    /// Get the configured statistical test type.
    pub fn test_type(&self) -> StatisticalTestType {
        self.test_type
    }

    /// Get the configured significance level.
    pub fn significance_level(&self) -> SignificanceLevel {
        self.alpha
    }

    /// Run A/B test comparing two agents
    ///
    /// # Arguments
    ///
    /// * `control` - Control (baseline) agent
    /// * `treatment` - Treatment (improved) agent
    /// * `test_cases` - Test cases to evaluate
    /// * `metric_name` - Metric to compare: `"accuracy"`, `"quality"`, `"latency"` or
    ///   `"context_length"`. An unrecognised name is an
    ///   [`AgentError::InvalidInput`], not a silent fallback to accuracy.
    pub async fn run(
        &self,
        control: Arc<dyn Agent>,
        treatment: Arc<dyn Agent>,
        test_cases: &[TestCase],
        metric_name: &str,
    ) -> Result<ABResult, AgentError> {
        if test_cases.is_empty() {
            return Err(AgentError::InvalidInput(
                "No test cases provided".to_string(),
            ));
        }

        // Collect samples for both variants
        let mut control_variant = ABVariant::new("control");
        let mut treatment_variant = ABVariant::new("treatment");

        // Evaluate control
        for test_case in test_cases {
            let score = self
                .evaluate_agent(control.clone(), test_case, metric_name)
                .await?;
            control_variant.add_sample(score);
        }

        // Evaluate treatment
        for test_case in test_cases {
            let score = self
                .evaluate_agent(treatment.clone(), test_case, metric_name)
                .await?;
            treatment_variant.add_sample(score);
        }

        // Calculate statistics
        control_variant.calculate_statistics();
        treatment_variant.calculate_statistics();

        // Run statistical test
        let p_value =
            self.run_statistical_test(&control_variant.samples, &treatment_variant.samples)?;

        // Calculate effect size
        let effect_size = self.cohens_d(&control_variant, &treatment_variant);

        // Calculate confidence interval
        let confidence_interval =
            self.bootstrap_ci(&control_variant.samples, &treatment_variant.samples, 0.95)?;

        // Determine significance and winner
        let is_significant = p_value < self.alpha.alpha();
        let winner = if is_significant {
            if treatment_variant.mean > control_variant.mean {
                "treatment".to_string()
            } else {
                "control".to_string()
            }
        } else {
            "inconclusive".to_string()
        };

        Ok(ABResult {
            control: control_variant,
            treatment: treatment_variant,
            p_value,
            effect_size,
            confidence_interval,
            is_significant,
            winner,
        })
    }

    /// Calculate required sample size for test
    ///
    /// # Arguments
    ///
    /// * `baseline_mean` - Expected control mean
    /// * `min_detectable_effect` - Minimum effect to detect (as fraction)
    /// * `alpha` - Significance level
    /// * `power` - Statistical power (1 - β)
    /// * `std_dev` - Expected standard deviation
    pub fn calculate_sample_size(
        baseline_mean: f64,
        min_detectable_effect: f64,
        alpha: f64,
        power: f64,
        std_dev: f64,
    ) -> usize {
        // Use normal approximation for sample size calculation
        let normal = Normal::new(0.0, 1.0).unwrap();
        let z_alpha = normal.inverse_cdf(1.0 - alpha / 2.0);
        let z_beta = normal.inverse_cdf(power);

        let effect_size = (baseline_mean * min_detectable_effect) / std_dev;
        let n = 2.0 * ((z_alpha + z_beta) / effect_size).powi(2);

        n.ceil() as usize
    }

    /// Resolves a metric name to the [`Metric`] implementation that computes it.
    ///
    /// `None` for an unknown name, which [`ABTest::run`] turns into an error rather
    /// than silently scoring something else — see [`ABTest::evaluate_agent`].
    fn metric_for(metric_name: &str) -> Option<Box<dyn Metric>> {
        match metric_name {
            "accuracy" => Some(Box::new(AccuracyMetric::new(None, false))),
            "quality" => Some(Box::new(QualityMetrics::new(false, None, None))),
            "latency" => Some(Box::new(LatencyMetric::new())),
            "context_length" => Some(Box::new(ContextMetrics::new())),
            _ => None,
        }
    }

    /// Evaluate agent on a single test case
    ///
    /// Scores by delegating to the [`Metric`] named by `metric_name`, so an A/B test
    /// measures the same thing an [`Evaluator`](super::core::Evaluator) run would.
    ///
    /// This used to open-code `response.trim() == expected.trim()` — trimmed,
    /// case-sensitive, whole-string equality, a third semantics distinct both from the
    /// substring contract in `docs/DEFAULTS.md` and from this core's own
    /// `AccuracyMetric`. Since `expected` holds a *fragment*
    /// (`SimpleQABenchmark` uses `"4"`, `"Paris"`; needle-in-haystack uses
    /// `ALPHA-0000-OMEGA`), a correct agent answering in prose scored `0.0` — for both
    /// arms, which reports `winner = "inconclusive"` with nothing to indicate the
    /// scoring never worked (#822).
    ///
    /// It also ignored `metric_name` outright (the parameter was `_metric_name`): the
    /// caller named a metric and got hardcoded accuracy regardless.
    async fn evaluate_agent(
        &self,
        agent: Arc<dyn Agent>,
        test_case: &TestCase,
        metric_name: &str,
    ) -> Result<f64, AgentError> {
        let metric = Self::metric_for(metric_name).ok_or_else(|| {
            AgentError::InvalidInput(format!(
                "unknown metric {metric_name:?}; expected one of \
                 \"accuracy\", \"quality\", \"latency\", \"context_length\""
            ))
        })?;

        let input = Message::with_text("user", test_case.input.clone());

        let started = Instant::now();
        let output = agent.process(input.clone()).await?;
        let latency_ms = started.elapsed().as_secs_f64() * 1000.0;

        // `expected` reaches AccuracyMetric through the context map, which is also how
        // `Evaluator` passes it. `latency_ms` is what LatencyMetric reads; supplying it
        // unconditionally keeps `metric_name = "latency"` from silently measuring 0.0.
        let mut ctx: HashMap<String, serde_json::Value> = test_case.metadata.clone();
        ctx.insert(
            "expected".to_string(),
            serde_json::json!(test_case.expected),
        );
        ctx.insert("latency_ms".to_string(), serde_json::json!(latency_ms));

        metric.measure(agent, &input, &output, &ctx).await
    }

    /// Run the appropriate statistical test
    fn run_statistical_test(&self, sample1: &[f64], sample2: &[f64]) -> Result<f64, AgentError> {
        match self.test_type {
            StatisticalTestType::TTest => self.t_test(sample1, sample2),
            StatisticalTestType::MannWhitney => self.mann_whitney(sample1, sample2),
            StatisticalTestType::ChiSquare => self.chi_square(sample1, sample2),
            StatisticalTestType::Bootstrap => Ok(self.bootstrap_p_value(sample1, sample2)?),
        }
    }

    /// Student's t-test (parametric)
    fn t_test(&self, sample1: &[f64], sample2: &[f64]) -> Result<f64, AgentError> {
        let n1 = sample1.len() as f64;
        let n2 = sample2.len() as f64;

        let mean1 = sample1.to_vec().mean();
        let mean2 = sample2.to_vec().mean();

        let var1 = sample1.to_vec().variance();
        let var2 = sample2.to_vec().variance();

        // Welch's t-test (unequal variances)
        let se = ((var1 / n1) + (var2 / n2)).sqrt();

        // A degenerate sample has no t-statistic to speak of. Two ordinary cases reach
        // here: both arms scoring identically (`se == 0.0` — and since accuracy samples
        // are 0.0/1.0, ties are common, not exotic), and a single test case per arm
        // (`statrs` returns NaN variance for n = 1, so `se` is NaN). Either way the
        // Welch-Satterthwaite `df` comes out NaN, `StudentsT::new` rejects it, and the
        // whole run used to fail with "Degrees of freedom are NaN". Report "no
        // detectable difference" instead, matching the `se == 0` and `n == 0` guards
        // Go's `tTest` already has.
        //
        // `!se.is_finite()` covers the n = 1 case via that NaN variance, so there is no
        // separate `n < 2` check — adding one would be unreachable.
        if se == 0.0 || !se.is_finite() {
            return Ok(1.0);
        }

        let t_stat = (mean1 - mean2) / se;

        // Welch-Satterthwaite degrees of freedom
        let df = ((var1 / n1 + var2 / n2).powi(2))
            / ((var1 / n1).powi(2) / (n1 - 1.0) + (var2 / n2).powi(2) / (n2 - 1.0));

        // Two-tailed p-value
        let t_dist = StudentsT::new(0.0, 1.0, df).map_err(|e| {
            AgentError::ProcessingError(format!("Failed to create t-distribution: {}", e))
        })?;

        let p_value = 2.0 * (1.0 - t_dist.cdf(t_stat.abs()));

        Ok(p_value)
    }

    /// Mann-Whitney U test (non-parametric)
    fn mann_whitney(&self, sample1: &[f64], sample2: &[f64]) -> Result<f64, AgentError> {
        let n1 = sample1.len();
        let n2 = sample2.len();

        // Combine and rank
        let mut combined: Vec<(f64, usize)> = sample1
            .iter()
            .map(|&x| (x, 0))
            .chain(sample2.iter().map(|&x| (x, 1)))
            .collect();

        combined.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());

        // Calculate ranks (handle ties)
        let mut ranks = vec![0.0; combined.len()];
        let mut i = 0;
        while i < combined.len() {
            let mut j = i;
            while j < combined.len() && combined[j].0 == combined[i].0 {
                j += 1;
            }
            let avg_rank = ((i + 1) + j) as f64 / 2.0;
            for rank in ranks[i..j].iter_mut() {
                *rank = avg_rank;
            }
            i = j;
        }

        // Sum ranks for sample1
        let r1: f64 = combined
            .iter()
            .zip(ranks.iter())
            .filter(|((_, group), _)| *group == 0)
            .map(|(_, rank)| rank)
            .sum();

        // U statistic
        let u1 = r1 - (n1 * (n1 + 1)) as f64 / 2.0;
        let u2 = (n1 * n2) as f64 - u1;
        let u = u1.min(u2);

        // Normal approximation for p-value
        let mu_u = (n1 * n2) as f64 / 2.0;
        let sigma_u = ((n1 * n2 * (n1 + n2 + 1)) as f64 / 12.0).sqrt();
        let z = (u - mu_u) / sigma_u;

        let normal = Normal::new(0.0, 1.0).map_err(|e| {
            AgentError::ProcessingError(format!("Failed to create normal distribution: {}", e))
        })?;

        let p_value = 2.0 * (1.0 - normal.cdf(z.abs()));

        Ok(p_value)
    }

    /// Chi-square test (for categorical outcomes)
    fn chi_square(&self, sample1: &[f64], sample2: &[f64]) -> Result<f64, AgentError> {
        // Count successes (assuming binary outcomes: 0 or 1)
        let n1 = sample1.len() as f64;
        let n2 = sample2.len() as f64;
        let s1 = sample1.iter().filter(|&&x| x > 0.5).count() as f64;
        let s2 = sample2.iter().filter(|&&x| x > 0.5).count() as f64;
        let f1 = n1 - s1;
        let f2 = n2 - s2;

        // Chi-square statistic
        let n = n1 + n2;
        let expected_s = (s1 + s2) * n1 / n;
        let expected_f = (f1 + f2) * n1 / n;

        let chi2 = (s1 - expected_s).powi(2) / expected_s
            + (f1 - expected_f).powi(2) / expected_f
            + (s2 - (s1 + s2) * n2 / n).powi(2) / ((s1 + s2) * n2 / n)
            + (f2 - (f1 + f2) * n2 / n).powi(2) / ((f1 + f2) * n2 / n);

        // P-value from chi-square distribution (df=1)
        // Approximate using normal distribution
        let p_value = 1.0 - (chi2 / 2.0).exp();

        Ok(p_value.clamp(0.0, 1.0))
    }

    /// Bootstrap p-value
    fn bootstrap_p_value(&self, sample1: &[f64], sample2: &[f64]) -> Result<f64, AgentError> {
        let observed_diff = sample1.to_vec().mean() - sample2.to_vec().mean();
        let n_resamples = 10000;
        let mut rng = rand::rng();

        // Combine samples for permutation test
        let combined: Vec<f64> = sample1.iter().chain(sample2.iter()).copied().collect();
        let n1 = sample1.len();

        // Count how many permutations have diff >= observed
        let mut count = 0;
        for _ in 0..n_resamples {
            // Shuffle and split
            let mut shuffled = combined.clone();
            for i in (1..shuffled.len()).rev() {
                let j = rng.random_range(0..=i);
                shuffled.swap(i, j);
            }

            let perm1 = &shuffled[..n1];
            let perm2 = &shuffled[n1..];

            let perm_diff = perm1.to_vec().mean() - perm2.to_vec().mean();
            if perm_diff.abs() >= observed_diff.abs() {
                count += 1;
            }
        }

        let p_value = count as f64 / n_resamples as f64;
        Ok(p_value)
    }

    /// Calculate Cohen's d (effect size)
    fn cohens_d(&self, control: &ABVariant, treatment: &ABVariant) -> f64 {
        let mean_diff = treatment.mean - control.mean;

        // Pooled standard deviation
        let n1 = control.sample_size as f64;
        let n2 = treatment.sample_size as f64;
        let pooled_std = (((n1 - 1.0) * control.std_dev.powi(2)
            + (n2 - 1.0) * treatment.std_dev.powi(2))
            / (n1 + n2 - 2.0))
            .sqrt();

        if pooled_std == 0.0 {
            0.0
        } else {
            mean_diff / pooled_std
        }
    }

    /// Bootstrap confidence interval for difference
    fn bootstrap_ci(
        &self,
        sample1: &[f64],
        sample2: &[f64],
        confidence: f64,
    ) -> Result<(f64, f64), AgentError> {
        let n_resamples = 10000;
        let mut rng = rand::rng();
        let mut diffs = Vec::with_capacity(n_resamples);

        for _ in 0..n_resamples {
            // Resample with replacement
            let resample1: Vec<f64> = (0..sample1.len())
                .map(|_| sample1[rng.random_range(0..sample1.len())])
                .collect();
            let resample2: Vec<f64> = (0..sample2.len())
                .map(|_| sample2[rng.random_range(0..sample2.len())])
                .collect();

            let diff = resample2.clone().mean() - resample1.clone().mean();
            diffs.push(diff);
        }

        diffs.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let alpha = 1.0 - confidence;
        let lower_idx = (n_resamples as f64 * alpha / 2.0) as usize;
        let upper_idx = (n_resamples as f64 * (1.0 - alpha / 2.0)) as usize;

        Ok((diffs[lower_idx], diffs[upper_idx]))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;

    #[test]
    fn test_significance_levels() {
        assert_eq!(SignificanceLevel::P0001.alpha(), 0.001);
        assert_eq!(SignificanceLevel::P001.alpha(), 0.01);
        assert_eq!(SignificanceLevel::P005.alpha(), 0.05);
        assert_eq!(SignificanceLevel::P010.alpha(), 0.10);
    }

    #[test]
    fn test_ab_variant() {
        let mut variant = ABVariant::new("test");
        variant.add_sample(1.0);
        variant.add_sample(2.0);
        variant.add_sample(3.0);
        variant.calculate_statistics();

        assert_eq!(variant.sample_size, 3);
        assert_eq!(variant.mean, 2.0);
    }

    #[test]
    fn test_sample_size_calculation() {
        let n = ABTest::calculate_sample_size(0.75, 0.05, 0.05, 0.80, 0.05);
        assert!(n > 0);
        assert!(n < 1000); // Sanity check
    }

    /// Answers every prompt with the same canned reply.
    struct CannedAgent(&'static str);

    #[async_trait::async_trait]
    impl Agent for CannedAgent {
        fn name(&self) -> &str {
            "canned"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", self.0))
        }
    }

    /// Sleeps before answering, so a latency measurement has something to measure.
    struct SlowAgent(Duration);

    #[async_trait::async_trait]
    impl Agent for SlowAgent {
        fn name(&self) -> &str {
            "slow"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            tokio::time::sleep(self.0).await;
            Ok(Message::with_text("assistant", "4"))
        }
    }

    struct FailingAgent;

    #[async_trait::async_trait]
    impl Agent for FailingAgent {
        fn name(&self) -> &str {
            "failing"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Err(AgentError::ProcessingError("upstream is down".to_string()))
        }
    }

    fn ab_test() -> ABTest {
        ABTest::new(StatisticalTestType::TTest, SignificanceLevel::P005)
    }

    #[tokio::test]
    async fn test_scores_a_correct_but_verbose_agent() {
        // The bug this replaces: scoring was `response.trim() == expected.trim()`, so an
        // agent answering in prose scored 0.0 against a fragment `expected`. Every
        // benchmark in this crate stores fragments ("4", "Paris", ALPHA-0000-OMEGA), so
        // A/B tests over this crate's own data never measured anything (#822).
        let cases = vec![
            TestCase::new("What is 2+2?", "4"),
            TestCase::new("Capital of France?", "4"),
        ];

        let verbose: Arc<dyn Agent> = Arc::new(CannedAgent("Well, the answer is 4, I think."));
        let wrong: Arc<dyn Agent> = Arc::new(CannedAgent("I really could not say."));

        let result = ab_test()
            .run(verbose, wrong, &cases, "accuracy")
            .await
            .unwrap();

        assert_eq!(
            result.control.mean, 1.0,
            "verbose-but-correct must score 1.0"
        );
        assert_eq!(result.treatment.mean, 0.0);
    }

    #[tokio::test]
    async fn test_scoring_is_case_insensitive_and_unicode_aware() {
        // `to_lowercase` is Unicode-aware, unlike the ASCII-only hand-rolled helpers
        // that produced the divergences in #820 and #823.
        let cases = vec![
            TestCase::new("Capital of France?", "paris"),
            TestCase::new("Capital of Russia?", "москва"),
            TestCase::new("Wie ist es?", "ähnlich"),
        ];

        for case in &cases {
            let shouty = case.expected.to_uppercase();
            let agent: Arc<dyn Agent> = Arc::new(CannedAgent(Box::leak(
                format!("Naturally, {shouty}.").into_boxed_str(),
            )));

            let result = ab_test()
                .run(agent.clone(), agent, std::slice::from_ref(case), "accuracy")
                .await
                .unwrap();

            assert_eq!(
                result.control.mean, 1.0,
                "expected {:?} should match its own uppercasing",
                case.expected
            );
        }
    }

    #[tokio::test]
    async fn test_scoring_agrees_with_the_accuracy_metric() {
        // The two comparison paths must not drift: this site now *is* AccuracyMetric,
        // and this test fails if it is ever open-coded again.
        let case = TestCase::new("What is 2+2?", "4");
        let output = Message::with_text("assistant", "Roughly 4, give or take.");
        let agent: Arc<dyn Agent> = Arc::new(CannedAgent("Roughly 4, give or take."));

        let mut ctx = HashMap::new();
        ctx.insert("expected".to_string(), serde_json::json!(case.expected));
        let direct = AccuracyMetric::new(None, false)
            .measure(
                agent.clone(),
                &Message::with_text("user", case.input.clone()),
                &output,
                &ctx,
            )
            .await
            .unwrap();

        let via_ab = ab_test()
            .run(agent.clone(), agent, &[case], "accuracy")
            .await
            .unwrap();

        assert_eq!(via_ab.control.mean, direct);
    }

    #[tokio::test]
    async fn test_metric_name_selects_the_metric() {
        // `metric_name` used to be `_metric_name` — the caller named a metric and got
        // hardcoded accuracy regardless. "latency" must not return accuracy's 0.0/1.0.
        let cases = vec![TestCase::new("What is 2+2?", "definitely not this")];
        let agent: Arc<dyn Agent> = Arc::new(CannedAgent("4"));

        let accuracy = ab_test()
            .run(agent.clone(), agent.clone(), &cases, "accuracy")
            .await
            .unwrap();
        assert_eq!(accuracy.control.mean, 0.0, "the answer really is wrong");

        // A deliberately slow agent gives the latency assertion something to bite on.
        // `mean >= 0.0` would be vacuous: dropping `latency_ms` from the context makes
        // LatencyMetric return its 0.0 fallback, which satisfies it.
        let slow: Arc<dyn Agent> = Arc::new(SlowAgent(Duration::from_millis(25)));
        let latency = ab_test()
            .run(slow.clone(), slow, &cases, "latency")
            .await
            .unwrap();
        assert_eq!(latency.control.samples.len(), 1);
        assert!(
            latency.control.mean >= 20.0,
            "latency must be the measured elapsed time, got {} ms",
            latency.control.mean
        );
    }

    #[tokio::test]
    async fn test_unknown_metric_is_an_error_not_a_silent_fallback() {
        let cases = vec![TestCase::new("What is 2+2?", "4")];
        let agent: Arc<dyn Agent> = Arc::new(CannedAgent("4"));

        let err = ab_test()
            .run(agent.clone(), agent, &cases, "f1_score")
            .await
            .expect_err("an unrecognised metric name must not silently score accuracy");

        assert!(
            matches!(err, AgentError::InvalidInput(ref m) if m.contains("f1_score")),
            "error should name the metric, got {err:?}"
        );
    }

    #[tokio::test]
    async fn test_two_identical_agents_are_inconclusive_not_an_error() {
        // Zero variance in both arms makes the Welch-Satterthwaite `df` NaN, and
        // `StudentsT::new` rejects NaN — so comparing two agents that score the same
        // used to fail the entire run with "Degrees of freedom are NaN". Accuracy
        // samples are 0.0/1.0, so ties are the common case, not an edge case.
        let cases = vec![
            TestCase::new("What is 2+2?", "4"),
            TestCase::new("What is 3+1?", "4"),
        ];
        let agent: Arc<dyn Agent> = Arc::new(CannedAgent("The answer is 4."));

        let result = ab_test()
            .run(agent.clone(), agent, &cases, "accuracy")
            .await
            .expect("identical agents must be reportable, not an error");

        assert_eq!(result.control.mean, result.treatment.mean);
        assert_eq!(result.p_value, 1.0, "no difference to detect");
        assert!(!result.is_significant);
        assert_eq!(result.winner, "inconclusive");
        assert_eq!(result.effect_size, 0.0);
    }

    #[tokio::test]
    async fn test_a_single_test_case_is_inconclusive_not_an_error() {
        // n = 1 per arm divides by `n - 1` in the df denominator. One test case is a
        // perfectly ordinary way to call this API.
        let cases = vec![TestCase::new("What is 2+2?", "4")];
        let good: Arc<dyn Agent> = Arc::new(CannedAgent("The answer is 4."));
        let bad: Arc<dyn Agent> = Arc::new(CannedAgent("No idea."));

        let result = ab_test().run(good, bad, &cases, "accuracy").await.unwrap();

        assert_eq!(result.control.mean, 1.0);
        assert_eq!(result.treatment.mean, 0.0);
        assert_eq!(result.p_value, 1.0, "n=1 cannot establish significance");
        assert_eq!(result.winner, "inconclusive");
    }

    #[tokio::test]
    async fn test_an_erroring_agent_propagates_rather_than_scoring_zero() {
        let cases = vec![TestCase::new("What is 2+2?", "4")];
        let ok: Arc<dyn Agent> = Arc::new(CannedAgent("4"));
        let bad: Arc<dyn Agent> = Arc::new(FailingAgent);

        let err = ab_test()
            .run(ok, bad, &cases, "accuracy")
            .await
            .expect_err("a broken agent must surface, not silently sample 0.0");

        assert!(matches!(err, AgentError::ProcessingError(_)), "got {err:?}");
    }
}
