//! Model optimizer for intelligent routing based on query complexity.

use crate::budget::pricing::ModelPricing;
use crate::core::Message;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Query complexity level.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ComplexityLevel {
    /// Simple queries (FAQ, basic info)
    Simple,
    /// Medium complexity (analysis, summarization)
    Medium,
    /// Complex queries (reasoning, code generation)
    Complex,
}

/// Optimizer configuration.
#[derive(Debug, Clone)]
pub struct OptimizerConfig {
    /// Model to use for simple queries
    pub simple_model: String,

    /// Model to use for medium complexity queries
    pub medium_model: String,

    /// Model to use for complex queries
    pub complex_model: String,

    /// Complexity thresholds
    pub simple_threshold: f64,
    pub complex_threshold: f64,
}

impl Default for OptimizerConfig {
    fn default() -> Self {
        Self {
            simple_model: "gpt-3.5-turbo".to_string(),
            medium_model: "gpt-4-turbo".to_string(),
            complex_model: "gpt-4".to_string(),
            simple_threshold: 0.30,
            complex_threshold: 0.60,
        }
    }
}

/// Model optimizer for routing queries to appropriate models.
pub struct ModelOptimizer {
    config: OptimizerConfig,
    pricing: ModelPricing,
}

impl ModelOptimizer {
    /// Create a new model optimizer.
    pub fn new(config: OptimizerConfig) -> Self {
        Self {
            config,
            pricing: ModelPricing::new(),
        }
    }

    /// Analyze query complexity.
    pub fn analyze_complexity(&self, message: &Message) -> ComplexityLevel {
        let content = message.content_as_str().unwrap_or("");
        let score = self.calculate_complexity_score(content);

        if score < self.config.simple_threshold {
            ComplexityLevel::Simple
        } else if score < self.config.complex_threshold {
            ComplexityLevel::Medium
        } else {
            ComplexityLevel::Complex
        }
    }

    /// Calculate complexity score (0.0 - 1.0).
    fn calculate_complexity_score(&self, content: &str) -> f64 {
        let mut score: f64 = 0.0;

        // Length factor (0.0 - 0.25)
        let length = content.len();
        let length_score = if length > 1000 {
            0.25
        } else if length > 500 {
            0.20
        } else if length > 200 {
            0.15
        } else {
            0.05
        };
        score += length_score;

        // Complexity keywords (0.0 - 0.35)
        let complex_keywords = [
            "analyze",
            "explain",
            "compare",
            "evaluate",
            "design",
            "implement",
            "optimize",
            "debug",
            "refactor",
            "architect",
            "algorithm",
            "system",
            "complex",
            "detailed",
            "comprehensive",
            "performance",
            "characteristics",
            "distributed",
            "trade-offs",
        ];

        let keyword_count = complex_keywords
            .iter()
            .filter(|&kw| content.to_lowercase().contains(kw))
            .count();

        let keyword_score = if keyword_count >= 5 {
            0.35
        } else if keyword_count >= 3 {
            0.30
        } else if keyword_count >= 2 {
            0.25
        } else if keyword_count >= 1 {
            0.15
        } else {
            0.0
        };
        score += keyword_score;

        // Question complexity (0.0 - 0.20)
        let question_marks = content.matches('?').count();
        let question_score = if question_marks > 2 {
            0.05 // Multiple questions might actually indicate simpler FAQs
        } else if question_marks == 1 {
            0.10 // Single question
        } else {
            0.20 // Statements often more complex than questions
        };
        score += question_score;

        // Code presence (0.0 - 0.20)
        let code_score =
            if content.contains("```") || content.contains("def ") || content.contains("function ")
            {
                0.20
            } else {
                0.0
            };
        score += code_score;

        score.min(1.0)
    }

    /// Select the best model for a message.
    pub fn select_model(&self, message: &Message) -> String {
        let complexity = self.analyze_complexity(message);

        match complexity {
            ComplexityLevel::Simple => self.config.simple_model.clone(),
            ComplexityLevel::Medium => self.config.medium_model.clone(),
            ComplexityLevel::Complex => self.config.complex_model.clone(),
        }
    }

    /// Estimate cost for a message with the selected model.
    pub async fn estimate_cost(
        &self,
        message: &Message,
        estimated_output_tokens: usize,
    ) -> Result<(String, f64), String> {
        let model = self.select_model(message);
        let content = message.content_as_str().unwrap_or("");

        // Rough estimate: 1 token ≈ 4 characters
        let input_tokens = content.len() / 4;

        let cost = self
            .pricing
            .calculate(&model, input_tokens, estimated_output_tokens)
            .await?;

        Ok((model, cost))
    }

    /// Get cost comparison across all models.
    pub async fn compare_models(
        &self,
        input_tokens: usize,
        output_tokens: usize,
    ) -> HashMap<String, f64> {
        let mut costs = HashMap::new();

        if let Ok(cost) = self
            .pricing
            .calculate(&self.config.simple_model, input_tokens, output_tokens)
            .await
        {
            costs.insert(self.config.simple_model.clone(), cost);
        }

        if let Ok(cost) = self
            .pricing
            .calculate(&self.config.medium_model, input_tokens, output_tokens)
            .await
        {
            costs.insert(self.config.medium_model.clone(), cost);
        }

        if let Ok(cost) = self
            .pricing
            .calculate(&self.config.complex_model, input_tokens, output_tokens)
            .await
        {
            costs.insert(self.config.complex_model.clone(), cost);
        }

        costs
    }

    /// Calculate potential savings.
    pub async fn calculate_savings(
        &self,
        message: &Message,
        estimated_output_tokens: usize,
    ) -> Result<f64, String> {
        let content = message.content_as_str().unwrap_or("");
        let input_tokens = content.len() / 4;

        let selected_model = self.select_model(message);
        let selected_cost = self
            .pricing
            .calculate(&selected_model, input_tokens, estimated_output_tokens)
            .await?;

        let expensive_cost = self
            .pricing
            .calculate(
                &self.config.complex_model,
                input_tokens,
                estimated_output_tokens,
            )
            .await?;

        Ok(expensive_cost - selected_cost)
    }
}

impl Default for ModelOptimizer {
    fn default() -> Self {
        Self::new(OptimizerConfig::default())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_complexity_analysis_simple() {
        let optimizer = ModelOptimizer::default();
        let msg = Message::with_text("user", "What is 2+2?");

        let complexity = optimizer.analyze_complexity(&msg);
        assert_eq!(complexity, ComplexityLevel::Simple);
    }

    #[test]
    fn test_complexity_analysis_complex() {
        let optimizer = ModelOptimizer::default();
        let msg = Message::with_text(
            "user",
            "Analyze the performance characteristics of different sorting algorithms \
             and explain when to use each one. Compare time and space complexity.",
        );

        let complexity = optimizer.analyze_complexity(&msg);
        assert_eq!(complexity, ComplexityLevel::Complex);
    }

    #[test]
    fn test_complexity_with_code() {
        let optimizer = ModelOptimizer::default();
        let msg = Message::with_text(
            "user",
            "Debug this code:\n```python\ndef factorial(n):\n    return n * factorial(n-1)\n```",
        );

        let complexity = optimizer.analyze_complexity(&msg);
        // Should be at least Medium due to code presence
        assert!(complexity == ComplexityLevel::Medium || complexity == ComplexityLevel::Complex);
    }

    #[test]
    fn test_model_selection() {
        let optimizer = ModelOptimizer::default();

        let simple_msg = Message::with_text("user", "Hello!");
        let complex_msg = Message::with_text(
            "user",
            "Design a distributed system architecture for real-time data processing \
             with high availability and fault tolerance. Explain the trade-offs.",
        );

        let simple_model = optimizer.select_model(&simple_msg);
        let complex_model = optimizer.select_model(&complex_msg);

        assert_eq!(simple_model, "gpt-3.5-turbo");
        assert_eq!(complex_model, "gpt-4");
    }

    #[tokio::test]
    async fn test_estimate_cost() {
        let optimizer = ModelOptimizer::default();
        let msg = Message::with_text("user", "What is the capital of France?");

        let result = optimizer.estimate_cost(&msg, 50).await;
        assert!(result.is_ok());

        let (model, cost) = result.unwrap();
        assert_eq!(model, "gpt-3.5-turbo"); // Simple query
        assert!(cost > 0.0);
    }

    #[tokio::test]
    async fn test_compare_models() {
        let optimizer = ModelOptimizer::default();
        let costs = optimizer.compare_models(1000, 500).await;

        assert!(costs.len() >= 2);
        assert!(costs.contains_key("gpt-3.5-turbo"));
        assert!(costs.contains_key("gpt-4"));

        // GPT-4 should be more expensive
        let cheap = costs.get("gpt-3.5-turbo").unwrap();
        let expensive = costs.get("gpt-4").unwrap();
        assert!(expensive > cheap);
    }

    #[tokio::test]
    async fn test_calculate_savings() {
        let optimizer = ModelOptimizer::default();
        let msg = Message::with_text("user", "What is 2+2?");

        let savings = optimizer.calculate_savings(&msg, 50).await.unwrap();

        // Should save money by using cheaper model for simple query
        assert!(savings > 0.0);
    }

    #[test]
    fn test_complexity_score_calculation() {
        let optimizer = ModelOptimizer::default();

        // Very short simple query
        let score1 = optimizer.calculate_complexity_score("Hello");
        assert!(score1 < 0.3);

        // Long complex query with keywords
        let score2 = optimizer.calculate_complexity_score(
            "Analyze and evaluate the design of this complex distributed system architecture. \
             Explain the trade-offs and optimize the implementation for performance.",
        );
        assert!(score2 >= 0.60); // Has many complexity keywords
    }
}
