//! Dynamic budget allocation for extended thinking modes.

use crate::core::Message;
use serde::{Deserialize, Serialize};

/// Thinking mode for extended reasoning.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ThinkingMode {
    /// Normal processing without extended thinking
    Normal,
    /// Light thinking for straightforward problems
    Light,
    /// Medium thinking for moderate complexity
    Medium,
    /// Deep thinking for complex reasoning
    Deep,
}

/// Thinking mode detector.
pub struct ThinkingModeDetector {
    /// Threshold for light thinking
    light_threshold: f64,
    /// Threshold for medium thinking
    medium_threshold: f64,
    /// Threshold for deep thinking
    deep_threshold: f64,
}

impl ThinkingModeDetector {
    /// Create a new thinking mode detector.
    pub fn new() -> Self {
        Self {
            light_threshold: 0.25,
            medium_threshold: 0.50,
            deep_threshold: 0.64,
        }
    }

    /// Create a detector with custom thresholds.
    pub fn with_thresholds(light: f64, medium: f64, deep: f64) -> Self {
        Self {
            light_threshold: light,
            medium_threshold: medium,
            deep_threshold: deep,
        }
    }

    /// Detect required thinking mode for a message.
    pub fn detect_mode(&self, message: &Message) -> ThinkingMode {
        let content = message.content_as_str().unwrap_or("");
        let score = self.calculate_thinking_score(content);

        if score < self.light_threshold {
            ThinkingMode::Normal
        } else if score < self.medium_threshold {
            ThinkingMode::Light
        } else if score < self.deep_threshold {
            ThinkingMode::Medium
        } else {
            ThinkingMode::Deep
        }
    }

    /// Calculate thinking requirement score (0.0 - 1.0).
    fn calculate_thinking_score(&self, content: &str) -> f64 {
        let mut score: f64 = 0.0;

        // Reasoning keywords (0.0 - 0.35)
        let reasoning_keywords = [
            "why", "how", "explain", "reason", "prove", "derive",
            "logical", "analyze", "deduce", "infer", "conclude",
            "theorem", "proof", "chain", "step-by-step",
        ];

        let reasoning_count = reasoning_keywords
            .iter()
            .filter(|&kw| content.to_lowercase().contains(kw))
            .count();

        let reasoning_score = if reasoning_count >= 4 {
            0.35
        } else if reasoning_count >= 2 {
            0.30
        } else if reasoning_count >= 1 {
            0.20
        } else {
            0.0
        };
        score += reasoning_score;

        // Multi-step indicators (0.0 - 0.30)
        let multi_step_keywords = [
            "first", "second", "then", "next", "finally",
            "step", "process", "workflow", "procedure",
        ];

        let step_count = multi_step_keywords
            .iter()
            .filter(|&kw| content.to_lowercase().contains(kw))
            .count();

        let step_score = if step_count >= 3 {
            0.30
        } else if step_count >= 1 {
            0.20
        } else {
            0.0
        };
        score += step_score;

        // Mathematical/logical content (0.0 - 0.20)
        let has_math = content.contains('=') || content.contains('+') || content.contains('*');
        let math_score = if has_math {
            0.20
        } else {
            0.0
        };
        score += math_score;

        // Complexity indicators (0.0 - 0.15)
        let complexity_keywords = ["complex", "difficult", "challenging", "intricate"];
        let has_complexity = complexity_keywords
            .iter()
            .any(|&kw| content.to_lowercase().contains(kw));

        let complexity_score = if has_complexity {
            0.15
        } else {
            0.0
        };
        score += complexity_score;

        score.min(1.0)
    }
}

impl Default for ThinkingModeDetector {
    fn default() -> Self {
        Self::new()
    }
}

/// Thinking budget allocator.
pub struct ThinkingBudgetAllocator {
    /// Base budget per request (USD)
    base_budget: f64,
    /// Budget multipliers for each thinking mode
    light_multiplier: f64,
    medium_multiplier: f64,
    deep_multiplier: f64,
}

impl ThinkingBudgetAllocator {
    /// Create a new budget allocator.
    pub fn new(base_budget: f64) -> Self {
        Self {
            base_budget,
            light_multiplier: 1.5,
            medium_multiplier: 3.0,
            deep_multiplier: 5.0,
        }
    }

    /// Create an allocator with custom multipliers.
    pub fn with_multipliers(
        base_budget: f64,
        light: f64,
        medium: f64,
        deep: f64,
    ) -> Self {
        Self {
            base_budget,
            light_multiplier: light,
            medium_multiplier: medium,
            deep_multiplier: deep,
        }
    }

    /// Allocate budget for a thinking mode.
    pub fn allocate_budget(&self, mode: ThinkingMode) -> f64 {
        match mode {
            ThinkingMode::Normal => self.base_budget,
            ThinkingMode::Light => self.base_budget * self.light_multiplier,
            ThinkingMode::Medium => self.base_budget * self.medium_multiplier,
            ThinkingMode::Deep => self.base_budget * self.deep_multiplier,
        }
    }

    /// Estimate total budget for a message.
    pub fn estimate_budget(&self, message: &Message, detector: &ThinkingModeDetector) -> f64 {
        let mode = detector.detect_mode(message);
        self.allocate_budget(mode)
    }

    /// Get budget breakdown for all modes.
    pub fn get_budget_breakdown(&self) -> Vec<(ThinkingMode, f64)> {
        vec![
            (ThinkingMode::Normal, self.allocate_budget(ThinkingMode::Normal)),
            (ThinkingMode::Light, self.allocate_budget(ThinkingMode::Light)),
            (ThinkingMode::Medium, self.allocate_budget(ThinkingMode::Medium)),
            (ThinkingMode::Deep, self.allocate_budget(ThinkingMode::Deep)),
        ]
    }

    /// Calculate savings from using appropriate mode vs always deep.
    pub fn calculate_mode_savings(&self, mode: ThinkingMode) -> f64 {
        let deep_budget = self.allocate_budget(ThinkingMode::Deep);
        let actual_budget = self.allocate_budget(mode);
        deep_budget - actual_budget
    }
}

impl Default for ThinkingBudgetAllocator {
    fn default() -> Self {
        Self::new(0.10) // $0.10 base budget
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_thinking_mode_detection_normal() {
        let detector = ThinkingModeDetector::new();
        let msg = Message::with_text("user", "What is the capital of France?");

        let mode = detector.detect_mode(&msg);
        assert_eq!(mode, ThinkingMode::Normal);
    }

    #[test]
    fn test_thinking_mode_detection_light() {
        let detector = ThinkingModeDetector::new();
        let msg = Message::with_text("user", "Explain why the sky is blue.");

        let mode = detector.detect_mode(&msg);
        assert!(mode == ThinkingMode::Light || mode == ThinkingMode::Medium);
    }

    #[test]
    fn test_thinking_mode_detection_deep() {
        let detector = ThinkingModeDetector::new();
        let msg = Message::with_text(
            "user",
            "Prove the Pythagorean theorem using logical reasoning. \
             First, explain the underlying principles, then derive the proof step-by-step, \
             and finally conclude with the mathematical implications.",
        );

        let mode = detector.detect_mode(&msg);
        assert_eq!(mode, ThinkingMode::Deep);
    }

    #[test]
    fn test_budget_allocation() {
        let allocator = ThinkingBudgetAllocator::new(0.10);

        assert!((allocator.allocate_budget(ThinkingMode::Normal) - 0.10).abs() < 0.001);
        assert!((allocator.allocate_budget(ThinkingMode::Light) - 0.15).abs() < 0.001);
        assert!((allocator.allocate_budget(ThinkingMode::Medium) - 0.30).abs() < 0.001);
        assert!((allocator.allocate_budget(ThinkingMode::Deep) - 0.50).abs() < 0.001);
    }

    #[test]
    fn test_estimate_budget() {
        let detector = ThinkingModeDetector::new();
        let allocator = ThinkingBudgetAllocator::new(0.10);

        let simple_msg = Message::with_text("user", "Hello!");
        let budget = allocator.estimate_budget(&simple_msg, &detector);
        assert_eq!(budget, 0.10); // Normal mode

        let complex_msg = Message::with_text(
            "user",
            "Analyze the logical reasoning behind this complex mathematical proof.",
        );
        let budget = allocator.estimate_budget(&complex_msg, &detector);
        assert!(budget > 0.10); // Should use thinking mode
    }

    #[test]
    fn test_budget_breakdown() {
        let allocator = ThinkingBudgetAllocator::new(0.10);
        let breakdown = allocator.get_budget_breakdown();

        assert_eq!(breakdown.len(), 4);
        assert_eq!(breakdown[0].0, ThinkingMode::Normal);
        assert!((breakdown[0].1 - 0.10).abs() < 0.001);
        assert_eq!(breakdown[1].0, ThinkingMode::Light);
        assert!((breakdown[1].1 - 0.15).abs() < 0.001);
        assert_eq!(breakdown[2].0, ThinkingMode::Medium);
        assert!((breakdown[2].1 - 0.30).abs() < 0.001);
        assert_eq!(breakdown[3].0, ThinkingMode::Deep);
        assert!((breakdown[3].1 - 0.50).abs() < 0.001);
    }

    #[test]
    fn test_mode_savings() {
        let allocator = ThinkingBudgetAllocator::new(0.10);

        let normal_savings = allocator.calculate_mode_savings(ThinkingMode::Normal);
        assert_eq!(normal_savings, 0.40); // $0.50 - $0.10

        let light_savings = allocator.calculate_mode_savings(ThinkingMode::Light);
        assert_eq!(light_savings, 0.35); // $0.50 - $0.15

        let deep_savings = allocator.calculate_mode_savings(ThinkingMode::Deep);
        assert_eq!(deep_savings, 0.0); // No savings
    }

    #[test]
    fn test_custom_multipliers() {
        let allocator = ThinkingBudgetAllocator::with_multipliers(0.10, 2.0, 4.0, 8.0);

        assert_eq!(allocator.allocate_budget(ThinkingMode::Light), 0.20);
        assert_eq!(allocator.allocate_budget(ThinkingMode::Medium), 0.40);
        assert_eq!(allocator.allocate_budget(ThinkingMode::Deep), 0.80);
    }

    #[test]
    fn test_custom_thresholds() {
        let detector = ThinkingModeDetector::with_thresholds(0.4, 0.7, 0.9);

        // Test that custom thresholds affect mode detection
        let msg = Message::with_text("user", "Explain why this works.");
        let mode = detector.detect_mode(&msg);

        // With higher thresholds, should be less likely to use deep thinking
        assert!(mode != ThinkingMode::Deep);
    }

    #[test]
    fn test_thinking_score_with_math() {
        let detector = ThinkingModeDetector::new();

        let math_msg = "Calculate the derivative of f(x) = x^2 + 3x + 5";
        let score = detector.calculate_thinking_score(math_msg);

        // Math content should increase score
        assert!(score >= 0.20); // Has math operators
    }

    #[test]
    fn test_multi_step_detection() {
        let detector = ThinkingModeDetector::new();

        let multi_step = "First analyze the problem, then design a solution, \
                         next implement the code, and finally test it.";
        let score = detector.calculate_thinking_score(multi_step);

        // Multi-step content should increase score
        assert!(score >= 0.50); // Has reasoning + multi-step keywords
    }
}
