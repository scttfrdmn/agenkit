// Chain-of-Thought Reasoning Technique
//
// Chain-of-Thought applies structured prompting to encourage step-by-step reasoning,
// optionally parsing and tracking individual reasoning steps.
//
// Reference: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
// Wei et al., 2022 - https://arxiv.org/abs/2201.11903

use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use regex::Regex;
use serde_json::json;
use std::sync::Arc;

/// Configuration for Chain-of-Thought.
pub struct ChainOfThoughtConfig {
    /// Prompt template with {query} placeholder (default: "Let's think step by step:\n{query}")
    pub prompt_template: String,

    /// Whether to extract and track individual reasoning steps (default: true)
    pub parse_steps: bool,

    /// Delimiter for splitting steps (default: "\n")
    pub step_delimiter: String,

    /// Maximum number of reasoning steps to extract (optional)
    pub max_steps: Option<usize>,
}

impl Default for ChainOfThoughtConfig {
    fn default() -> Self {
        Self {
            prompt_template: "Let's think step by step:\n{query}".to_string(),
            parse_steps: true,
            step_delimiter: "\n".to_string(),
            max_steps: None,
        }
    }
}

/// Chain-of-Thought agent that wraps a base agent.
///
/// This technique encourages step-by-step reasoning through structured prompting,
/// leading to more accurate and explainable results.
///
/// Particularly effective for:
/// - Mathematical reasoning
/// - Logical deduction
/// - Complex problem-solving
/// - Multi-step tasks requiring explanation
///
/// # Example
///
/// ```no_run
/// use agenkit::techniques::reasoning::{ChainOfThoughtAgent, ChainOfThoughtConfig};
/// use std::sync::Arc;
///
/// let base_agent = Arc::new(my_agent);
/// let config = ChainOfThoughtConfig {
///     prompt_template: "Solve step by step:\n{query}".to_string(),
///     max_steps: Some(5),
///     ..Default::default()
/// };
///
/// let cot = ChainOfThoughtAgent::new(base_agent, config);
/// let response = cot.process(message).await?;
/// // Access reasoning_steps from metadata
/// ```
pub struct ChainOfThoughtAgent {
    agent: Arc<dyn Agent>,
    prompt_template: String,
    parse_steps: bool,
    step_delimiter: String,
    max_steps: Option<usize>,
}

impl ChainOfThoughtAgent {
    /// Create a new Chain-of-Thought agent.
    pub fn new(agent: Arc<dyn Agent>, config: ChainOfThoughtConfig) -> Self {
        Self {
            agent,
            prompt_template: config.prompt_template,
            parse_steps: config.parse_steps,
            step_delimiter: config.step_delimiter,
            max_steps: config.max_steps,
        }
    }

    /// Extract reasoning steps from response text.
    ///
    /// Supports multiple common step formats:
    /// - Numbered steps (1. Step one, 2. Step two)
    /// - Numbered steps with parentheses (1) Step one, 2) Step two)
    /// - Bullet points (- Step, * Step, • Step)
    /// - Newline-separated thoughts (fallback)
    fn extract_steps(&self, text: &str) -> Vec<String> {
        // Try numbered steps first (1. 2. 3. or 1) 2) 3))
        let numbered_regex = Regex::new(r"(?m)^\d+[.)]\s*(.+)$").unwrap();
        let numbered_matches: Vec<String> = numbered_regex
            .captures_iter(text)
            .filter_map(|cap| cap.get(1).map(|m| m.as_str().trim().to_string()))
            .collect();

        if numbered_matches.len() >= 2 {
            return self.limit_steps(numbered_matches);
        }

        // Try bullet points (-, *, •)
        let bullet_regex = Regex::new(r"(?m)^[•\-\*]\s*(.+)$").unwrap();
        let bullet_matches: Vec<String> = bullet_regex
            .captures_iter(text)
            .filter_map(|cap| cap.get(1).map(|m| m.as_str().trim().to_string()))
            .collect();

        if bullet_matches.len() >= 2 {
            return self.limit_steps(bullet_matches);
        }

        // Fall back to delimiter-based splitting
        let steps: Vec<String> = text
            .split(&self.step_delimiter)
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .collect();

        self.limit_steps(steps)
    }

    /// Apply max_steps limit if configured.
    fn limit_steps(&self, mut steps: Vec<String>) -> Vec<String> {
        if let Some(max) = self.max_steps {
            steps.truncate(max);
        }
        steps
    }
}

#[async_trait]
impl Agent for ChainOfThoughtAgent {
    fn name(&self) -> &str {
        "chain_of_thought"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "reasoning".to_string(),
            "step_by_step".to_string(),
            "chain_of_thought".to_string(),
            "explainable_ai".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Validate prompt template
        if !self.prompt_template.contains("{query}") {
            return Err(AgentError::InvalidInput(
                "Prompt template must contain {query} placeholder".to_string(),
            ));
        }

        // Apply CoT prompting
        let query = message.content_as_str().unwrap_or("").to_string();
        let cot_prompt = self.prompt_template.replace("{query}", &query);

        // Get response from agent
        let prompt_message = Message::with_text("user", cot_prompt);
        let response = self.agent.process(prompt_message).await.map_err(|e| {
            AgentError::Internal(format!("Chain of thought processing failed: {}", e))
        })?;

        // Parse steps if requested
        let mut result = Message::with_text(
            "assistant",
            response.content_as_str().unwrap_or("").to_string(),
        );

        if self.parse_steps {
            let steps = self.extract_steps(result.content_as_str().unwrap_or(""));
            result
                .metadata
                .insert("reasoning_steps".to_string(), json!(steps));
            result
                .metadata
                .insert("num_steps".to_string(), json!(steps.len()));
        }

        result
            .metadata
            .insert("technique".to_string(), json!("chain_of_thought"));

        Ok(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    struct MockAgent {
        response: Mutex<String>,
    }

    impl MockAgent {
        fn new(response: impl Into<String>) -> Arc<Self> {
            Arc::new(Self {
                response: Mutex::new(response.into()),
            })
        }
    }

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        fn capabilities(&self) -> Vec<String> {
            vec![]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            let text = self.response.lock().unwrap().clone();
            Ok(Message::with_text("assistant", text))
        }
    }

    #[test]
    fn test_default_config() {
        let config = ChainOfThoughtConfig::default();
        assert!(config.prompt_template.contains("{query}"));
        assert!(config.parse_steps);
        assert_eq!(config.step_delimiter, "\n");
        assert!(config.max_steps.is_none());
    }

    #[test]
    fn test_agent_name_and_capabilities() {
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), ChainOfThoughtConfig::default());
        assert_eq!(agent.name(), "chain_of_thought");
        let caps = agent.capabilities();
        assert!(caps.contains(&"chain_of_thought".to_string()));
        assert!(caps.contains(&"reasoning".to_string()));
    }

    #[test]
    fn test_extract_steps_numbered() {
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), ChainOfThoughtConfig::default());
        let text = "1. First step\n2. Second step\n3. Third step";
        let steps = agent.extract_steps(text);
        assert_eq!(steps.len(), 3);
        assert_eq!(steps[0], "First step");
        assert_eq!(steps[2], "Third step");
    }

    #[test]
    fn test_extract_steps_parentheses() {
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), ChainOfThoughtConfig::default());
        let text = "1) Do this\n2) Do that\n3) Final step";
        let steps = agent.extract_steps(text);
        assert_eq!(steps.len(), 3);
        assert_eq!(steps[0], "Do this");
    }

    #[test]
    fn test_extract_steps_bullets() {
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), ChainOfThoughtConfig::default());
        let text = "- Step A\n- Step B\n- Step C";
        let steps = agent.extract_steps(text);
        assert_eq!(steps.len(), 3);
        assert_eq!(steps[0], "Step A");
    }

    #[test]
    fn test_extract_steps_fallback() {
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), ChainOfThoughtConfig::default());
        let text = "First thought\nSecond thought\nThird thought";
        let steps = agent.extract_steps(text);
        assert_eq!(steps.len(), 3);
    }

    #[test]
    fn test_max_steps_limit() {
        let config = ChainOfThoughtConfig {
            max_steps: Some(2),
            ..Default::default()
        };
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), config);
        let text = "1. Step one\n2. Step two\n3. Step three\n4. Step four";
        let steps = agent.extract_steps(text);
        assert_eq!(steps.len(), 2);
    }

    #[tokio::test]
    async fn test_process_adds_metadata() {
        let response_text = "1. First step\n2. Second step";
        let agent = ChainOfThoughtAgent::new(
            MockAgent::new(response_text),
            ChainOfThoughtConfig::default(),
        );
        let msg = Message::with_text("user", "What is 2+2?");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["technique"], "chain_of_thought");
        assert!(result.metadata.contains_key("reasoning_steps"));
        assert!(result.metadata.contains_key("num_steps"));
    }

    #[tokio::test]
    async fn test_process_invalid_template() {
        let config = ChainOfThoughtConfig {
            prompt_template: "No placeholder here".to_string(),
            ..Default::default()
        };
        let agent = ChainOfThoughtAgent::new(MockAgent::new("ok"), config);
        let msg = Message::with_text("user", "test");
        assert!(agent.process(msg).await.is_err());
    }

    #[tokio::test]
    async fn test_process_no_parse_steps() {
        let config = ChainOfThoughtConfig {
            parse_steps: false,
            ..Default::default()
        };
        let agent = ChainOfThoughtAgent::new(MockAgent::new("some response"), config);
        let msg = Message::with_text("user", "What is 2+2?");
        let result = agent.process(msg).await.unwrap();
        assert_eq!(result.metadata["technique"], "chain_of_thought");
        assert!(!result.metadata.contains_key("reasoning_steps"));
    }
}
