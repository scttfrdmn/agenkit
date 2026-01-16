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
/// let benchmark = NeedleInHaystackBenchmark::new(10000, 5, 10);
/// let cases = benchmark.generate_test_cases();
/// assert_eq!(cases.len(), 5);
/// ```
pub struct NeedleInHaystackBenchmark {
    context_length: usize,
    needle_count: usize,
    haystack_multiplier: usize,
}

impl NeedleInHaystackBenchmark {
    /// Creates a new needle-in-haystack benchmark.
    ///
    /// # Arguments
    ///
    /// * `context_length` - Target context length in tokens
    /// * `needle_count` - Number of needles to hide
    /// * `haystack_multiplier` - How much filler per needle
    pub fn new(context_length: usize, needle_count: usize, haystack_multiplier: usize) -> Self {
        Self {
            context_length,
            needle_count,
            haystack_multiplier,
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
        "needle_in_haystack"
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
/// let benchmark = ExtremeScaleBenchmark::new(None, 10);
/// let cases = benchmark.generate_test_cases();
/// // Tests at 1M, 10M, 25M tokens by default
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
            let benchmark = NeedleInHaystackBenchmark::new(length, self.needles_per_length, 10);
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
        let benchmark = NeedleInHaystackBenchmark::new(1000, 3, 10);

        assert_eq!(benchmark.name(), "needle_in_haystack");

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
        let benchmark = NeedleInHaystackBenchmark::new(100, 2, 10);
        let haystack = benchmark.generate_haystack(100);

        // Should generate some content
        assert!(!haystack.is_empty());
        assert!(haystack.split_whitespace().count() > 0);
    }

    #[test]
    fn test_needle_embedding() {
        let benchmark = NeedleInHaystackBenchmark::new(100, 2, 10);
        let haystack = "one two three four five six seven eight nine ten";
        let needles = vec!["NEEDLE1".to_string(), "NEEDLE2".to_string()];

        let embedded = benchmark.embed_needles(haystack, &needles);

        assert!(embedded.contains("NEEDLE1"));
        assert!(embedded.contains("NEEDLE2"));
        assert!(embedded.contains("one"));
        assert!(embedded.contains("ten"));
    }
}
