//! Benchmark Suites
//!
//! Provides standardized benchmarks for evaluating agent capabilities.
//!
//! Includes simple Q&A, needle-in-haystack retrieval, and extreme-scale tests
//! for systems operating at 1M-25M+ tokens.
//!
//! # Example
//!
//! ```
//! use agenkit::evaluation::benchmarks::{Benchmark, SimpleQABenchmark};
//!
//! let benchmark = SimpleQABenchmark::new();
//! let test_cases = benchmark.generate_test_cases();
//! println!("{} test cases generated", test_cases.len());
//! ```

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Single test case for evaluation.
///
/// Contains input, expected output, and metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCase {
    /// Input text
    pub input: String,
    /// Expected output (string or pattern)
    pub expected: String,
    /// Additional metadata
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
    /// Tags for categorization
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub tags: Vec<String>,
}

impl TestCase {
    /// Creates a new test case.
    pub fn new(input: impl Into<String>, expected: impl Into<String>) -> Self {
        Self {
            input: input.into(),
            expected: expected.into(),
            metadata: HashMap::new(),
            tags: Vec::new(),
        }
    }

    /// Adds a tag.
    pub fn with_tag(mut self, tag: impl Into<String>) -> Self {
        self.tags.push(tag.into());
        self
    }

    /// Adds metadata.
    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }

    /// Validates agent output against this test case's expected value.
    ///
    /// `expected` is a **fragment to find** in the output, compared
    /// **case-insensitively** — not the whole output. An agent answering
    /// `"The answer is 42."` passes `expected = "42"`. Benchmarks store the fact to
    /// look for; agents answer in prose. This matches `AccuracyMetric` in this core
    /// and `TestCase::validate` in every other, per `docs/DEFAULTS.md` (#820).
    ///
    /// An empty `expected` matches anything, following `str::contains("")`.
    ///
    /// For exact or case-sensitive comparison, use `AccuracyMetric`'s `validator`.
    ///
    /// # Example
    ///
    /// ```
    /// use agenkit::evaluation::benchmarks::TestCase;
    ///
    /// let case = TestCase::new("What is 2+2?", "4");
    /// assert!(case.validate("The answer is 4."));
    /// assert!(!case.validate("The answer is 5."));
    /// ```
    pub fn validate(&self, actual: &str) -> bool {
        actual
            .to_lowercase()
            .contains(&self.expected.to_lowercase())
    }

    /// Converts test case to dictionary.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert("input".to_string(), serde_json::json!(self.input));
        result.insert("expected".to_string(), serde_json::json!(self.expected));
        result.insert("metadata".to_string(), serde_json::json!(self.metadata));
        result.insert("tags".to_string(), serde_json::json!(self.tags));
        result
    }
}

/// Benchmark interface.
///
/// Benchmarks define test suites for evaluating specific capabilities.
pub trait Benchmark {
    /// Returns the benchmark name.
    fn name(&self) -> &str;

    /// Returns the benchmark description.
    fn description(&self) -> &str;

    /// Generates test cases for this benchmark.
    fn generate_test_cases(&self) -> Vec<TestCase>;
}

/// Simple question-answering benchmark.
///
/// Tests basic knowledge and reasoning.
///
/// # Example
///
/// ```
/// use agenkit::evaluation::benchmarks::{Benchmark, SimpleQABenchmark};
///
/// let benchmark = SimpleQABenchmark::new();
/// let cases = benchmark.generate_test_cases();
/// assert_eq!(cases.len(), 5);
/// ```
pub struct SimpleQABenchmark;

impl SimpleQABenchmark {
    /// Creates a new simple Q&A benchmark.
    pub fn new() -> Self {
        Self
    }
}

impl Default for SimpleQABenchmark {
    fn default() -> Self {
        Self::new()
    }
}

impl Benchmark for SimpleQABenchmark {
    fn name(&self) -> &str {
        "simple_qa"
    }

    fn description(&self) -> &str {
        "Basic question-answering tasks"
    }

    fn generate_test_cases(&self) -> Vec<TestCase> {
        vec![
            TestCase::new("What is 2+2?", "4")
                .with_tag("math")
                .with_tag("easy"),
            TestCase::new("What is the capital of France?", "Paris")
                .with_tag("knowledge")
                .with_tag("easy"),
            TestCase::new("What is the largest planet in our solar system?", "Jupiter")
                .with_tag("knowledge")
                .with_tag("easy"),
            TestCase::new(
                "If a train leaves at 2pm and travels for 3 hours, when does it arrive?",
                "5",
            )
            .with_tag("reasoning")
            .with_tag("easy"),
            TestCase::new("What comes next in the sequence: 2, 4, 6, 8, ?", "10")
                .with_tag("reasoning")
                .with_tag("easy"),
        ]
    }
}

/// Needle-in-haystack benchmark for context retrieval.
///
/// Tests ability to retrieve specific information from large contexts.
/// Essential for extreme-scale systems.
///
/// # Example
///
/// ```
/// use agenkit::evaluation::benchmarks::{Benchmark, NeedleInHaystackBenchmark};
///
/// let benchmark = NeedleInHaystackBenchmark::new(10000, 5);
/// let cases = benchmark.generate_test_cases();
/// assert_eq!(cases.len(), 5);
/// ```
pub struct NeedleInHaystackBenchmark {
    context_length: usize,
    needle_count: usize,
    /// Precomputed `needle_in_haystack_{context_length}`.
    ///
    /// Held as a field because [`Benchmark::name`] returns `&str` and so cannot format
    /// on demand. The name is a registry key in some cores, so it has to encode
    /// `context_length` to match them — see #790.
    name: String,
}

impl NeedleInHaystackBenchmark {
    /// Creates a new needle-in-haystack benchmark.
    ///
    /// # Arguments
    ///
    /// * `context_length` - Target context length in tokens
    /// * `needle_count` - Number of needles to hide
    pub fn new(context_length: usize, needle_count: usize) -> Self {
        Self {
            context_length,
            needle_count,
            name: format!("needle_in_haystack_{context_length}"),
        }
    }

    /// Generates filler content for haystack.
    fn generate_haystack(&self, target_tokens: usize) -> String {
        let paragraphs = vec![
            "This is a paragraph of filler content. It contains general information that is not relevant to the specific queries we will ask. \
             The purpose of this content is to create a large context that the agent must search through. ",
            "Here is another paragraph with different content. It discusses various topics without providing the specific information we're looking for. \
             This helps test the agent's ability to find needles in haystacks. ",
            "Additional filler text to expand the context. This paragraph talks about unrelated subjects and serves to increase the total context length. \
             The agent must be able to filter through this content efficiently. ",
        ];

        // Estimate tokens per paragraph
        let tokens_per_paragraph: usize = paragraphs
            .iter()
            .map(|p| p.split_whitespace().count())
            .sum();

        let repetitions = (target_tokens / tokens_per_paragraph) + 1;

        let mut haystack = String::new();
        for _ in 0..repetitions {
            for paragraph in &paragraphs {
                haystack.push_str(paragraph);
            }
        }

        haystack
    }

    /// Embeds needles at regular intervals in haystack.
    fn embed_needles(&self, haystack: &str, needles: &[String]) -> String {
        let words: Vec<&str> = haystack.split_whitespace().collect();
        let interval = words.len() / (needles.len() + 1);

        let mut embedded = Vec::new();
        let mut needle_idx = 0;

        for (i, word) in words.iter().enumerate() {
            // Insert needle at intervals
            if needle_idx < needles.len() && i == interval * (needle_idx + 1) {
                embedded.push(needles[needle_idx].as_str());
                needle_idx += 1;
            }
            embedded.push(*word);
        }

        embedded.join(" ")
    }
}

impl Benchmark for NeedleInHaystackBenchmark {
    fn name(&self) -> &str {
        &self.name
    }

    fn description(&self) -> &str {
        "Retrieve facts from large context"
    }

    fn generate_test_cases(&self) -> Vec<TestCase> {
        // Generate needles (specific facts to retrieve)
        let needles: Vec<String> = (0..self.needle_count)
            .map(|i| format!("The secret code for vault {} is ALPHA-{:04}-OMEGA.", i, i))
            .collect();

        // Generate haystack (filler content)
        let haystack = self.generate_haystack(self.context_length);

        // Embed needles at random positions
        let context = self.embed_needles(&haystack, &needles);

        // Create test cases asking for each needle
        needles
            .iter()
            .enumerate()
            .map(|(i, _)| {
                let input = format!(
                    "Context: {}\n\nQuestion: What is the secret code for vault {}?",
                    context, i
                );
                let expected = format!("ALPHA-{:04}-OMEGA", i);

                TestCase::new(input, expected)
                    .with_metadata(
                        "context_length",
                        serde_json::json!(context.split_whitespace().count() / 4),
                    )
                    .with_metadata("needle_position", serde_json::json!(i))
                    .with_metadata("total_needles", serde_json::json!(self.needle_count))
                    .with_tag("retrieval")
                    .with_tag("context")
                    .with_tag(format!("length_{}", self.context_length))
            })
            .collect()
    }
}

/// Extreme-scale benchmark for testing at 1M-25M+ tokens.
///
/// Designed specifically for systems that operate at unprecedented
/// context lengths.
///
/// # Example
///
/// ```
/// use agenkit::evaluation::benchmarks::{Benchmark, ExtremeScaleBenchmark};
///
/// // Pass explicit lengths in a doctest. `None` defaults to 1M/10M/25M tokens,
/// // and `generate_test_cases()` materialises those haystacks for real — that
/// // one line took ~9 minutes and dominated the entire doctest suite, which is
/// // why doctests could not be a CI gate before #773.
/// let benchmark = ExtremeScaleBenchmark::new(Some(vec![1_000]), 2);
/// let cases = benchmark.generate_test_cases();
/// assert!(!cases.is_empty());
/// ```
pub struct ExtremeScaleBenchmark {
    test_lengths: Vec<usize>,
    needles_per_length: usize,
}

impl ExtremeScaleBenchmark {
    /// Creates a new extreme-scale benchmark.
    ///
    /// # Arguments
    ///
    /// * `test_lengths` - Context lengths to test (defaults to 1M, 10M, 25M)
    /// * `needles_per_length` - Number of needles per context length
    pub fn new(test_lengths: Option<Vec<usize>>, needles_per_length: usize) -> Self {
        let test_lengths = test_lengths.unwrap_or_else(|| {
            vec![
                1_000_000,  // 1M tokens
                10_000_000, // 10M tokens
                25_000_000, // 25M tokens
            ]
        });

        Self {
            test_lengths,
            needles_per_length,
        }
    }
}

impl Benchmark for ExtremeScaleBenchmark {
    fn name(&self) -> &str {
        "extreme_scale"
    }

    fn description(&self) -> &str {
        "Test retrieval and quality at extreme scale"
    }

    fn generate_test_cases(&self) -> Vec<TestCase> {
        let mut test_cases = Vec::new();

        for &length in &self.test_lengths {
            // Create needle-in-haystack tests at this scale
            let benchmark = NeedleInHaystackBenchmark::new(length, self.needles_per_length);
            let mut cases = benchmark.generate_test_cases();

            // Tag with scale
            for case in &mut cases {
                case.tags.push("extreme_scale".to_string());
                case.tags.push(format!("scale_{}M", length / 1_000_000));
                case.metadata
                    .insert("benchmark".to_string(), serde_json::json!("extreme_scale"));
            }

            test_cases.extend(cases);
        }

        test_cases
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_test_case_creation() {
        let test_case = TestCase::new("input", "expected")
            .with_tag("test")
            .with_metadata("key", serde_json::json!("value"));

        assert_eq!(test_case.input, "input");
        assert_eq!(test_case.expected, "expected");
        assert_eq!(test_case.tags.len(), 1);
        assert_eq!(test_case.metadata.len(), 1);
    }

    #[test]
    fn test_validate_matches_a_fragment_inside_agent_prose() {
        // `expected` is the fact to look for, not the whole answer. This is what the
        // benchmarks in this file rely on: SimpleQABenchmark's expected values are
        // "42", "Paris", "Not necessarily" — an agent answering in prose must pass.
        let test_case = TestCase::new("What is 15 + 27?", "42");

        assert!(test_case.validate("42"));
        assert!(test_case.validate("The answer is 42."));
        assert!(test_case.validate("15 + 27 = 42, so the total is 42 items."));
        assert!(!test_case.validate("The answer is 41."));
    }

    #[test]
    fn test_validate_is_case_insensitive() {
        let test_case = TestCase::new("Capital of France?", "Paris");

        assert!(test_case.validate("paris"));
        assert!(test_case.validate("PARIS"));
        assert!(test_case.validate("The capital is PaRiS."));
        assert!(!test_case.validate("Lyon"));
    }

    #[test]
    fn test_validate_requires_the_whole_fragment() {
        // A prefix of the expected fragment is not a match — the needle must appear
        // whole, or "Paris" would be satisfied by "Par".
        let test_case = TestCase::new("Capital of France?", "Paris");

        assert!(!test_case.validate("Par"));
        assert!(!test_case.validate(""));
    }

    #[test]
    fn test_validate_with_an_empty_expected_matches_anything() {
        // Documented in docs/DEFAULTS.md: `"".contains("")` is true in every core, so
        // the contract follows suit rather than special-casing. Nothing was asked for.
        let test_case = TestCase::new("input", "");

        assert!(test_case.validate(""));
        assert!(test_case.validate("anything at all"));
    }

    #[test]
    fn test_validate_agrees_with_this_cores_accuracy_metric() {
        // The two comparison sites in this core must not drift: AccuracyMetric already
        // did case-insensitive `contains`, and a second, subtly different
        // implementation here is precisely how #820's three-way divergence arose.
        let benchmark = SimpleQABenchmark::new();

        for case in benchmark.generate_test_cases() {
            let embedded = format!("Well, {}, as it happens.", case.expected.to_uppercase());
            assert!(
                case.validate(&embedded),
                "expected {:?} should be found in {:?}",
                case.expected,
                embedded
            );
        }
    }

    #[test]
    fn test_simple_qa_benchmark() {
        let benchmark = SimpleQABenchmark::new();

        assert_eq!(benchmark.name(), "simple_qa");
        assert_eq!(benchmark.description(), "Basic question-answering tasks");

        let cases = benchmark.generate_test_cases();
        assert_eq!(cases.len(), 5);

        // Check first test case
        assert_eq!(cases[0].input, "What is 2+2?");
        assert_eq!(cases[0].expected, "4");
        assert!(cases[0].tags.contains(&"math".to_string()));
        assert!(cases[0].tags.contains(&"easy".to_string()));
    }

    #[test]
    fn test_needle_in_haystack_benchmark() {
        let benchmark = NeedleInHaystackBenchmark::new(1000, 3);

        // Encodes context_length to match Python, Go, C++ and TypeScript; this core used
        // to return a bare "needle_in_haystack" for every size (#790).
        assert_eq!(benchmark.name(), "needle_in_haystack_1000");
        assert_ne!(
            NeedleInHaystackBenchmark::new(500, 2).name(),
            NeedleInHaystackBenchmark::new(900, 2).name(),
            "benchmarks of different sizes must not share a registry key"
        );

        let cases = benchmark.generate_test_cases();
        assert_eq!(cases.len(), 3);

        // Check that each case has the expected structure
        for (i, case) in cases.iter().enumerate() {
            assert!(case.input.contains(&format!("vault {}", i)));
            assert_eq!(case.expected, format!("ALPHA-{:04}-OMEGA", i));
            assert!(case.tags.contains(&"retrieval".to_string()));
        }
    }

    #[test]
    fn test_extreme_scale_benchmark() {
        let test_lengths = vec![100, 200];
        let benchmark = ExtremeScaleBenchmark::new(Some(test_lengths), 2);

        assert_eq!(benchmark.name(), "extreme_scale");

        let cases = benchmark.generate_test_cases();
        assert_eq!(cases.len(), 4); // 2 lengths × 2 needles per length

        // Check that cases are tagged appropriately
        for case in &cases {
            assert!(case.tags.contains(&"extreme_scale".to_string()));
        }
    }

    #[test]
    fn test_haystack_generation() {
        let benchmark = NeedleInHaystackBenchmark::new(100, 2);
        let haystack = benchmark.generate_haystack(100);

        // Should generate some content
        assert!(!haystack.is_empty());
        assert!(haystack.split_whitespace().count() > 0);
    }

    #[test]
    fn test_needle_embedding() {
        let benchmark = NeedleInHaystackBenchmark::new(100, 2);
        let haystack = "one two three four five six seven eight nine ten";
        let needles = vec!["NEEDLE1".to_string(), "NEEDLE2".to_string()];

        let embedded = benchmark.embed_needles(haystack, &needles);

        assert!(embedded.contains("NEEDLE1"));
        assert!(embedded.contains("NEEDLE2"));
        assert!(embedded.contains("one"));
        assert!(embedded.contains("ten"));
    }
}
