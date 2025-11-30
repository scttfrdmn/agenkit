//! Router Pattern - Conditional Agent Selection
//!
//! Implements conditional agent selection based on message classification.
//! A classifier determines the intent/category, then routes the request to
//! an appropriate specialist agent.
//!
//! # Key Concepts
//!
//! - **Intent classification**: Determine message category/intent
//! - **Conditional routing**: Route to specialists based on classification
//! - **Single execution**: Only one agent executes per request
//! - **Dynamic selection**: Agent selected based on input
//!
//! # Use Cases
//!
//! - Customer service: route to billing, technical, account agents
//! - Content moderation: route to spam, abuse, quality agents
//! - Language routing: route to language-specific agents
//! - Skill-based routing: route to domain expert agents
//! - Intent-based chatbots: route to booking, info, support agents
//!
//! # Performance Characteristics
//!
//! - **Time**: O(classification + selected agent)
//! - **Memory**: O(1) - only one agent executes
//! - Efficient single-path execution
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{RouterAgent, RouterConfig, LLMClassifier};
//! use std::sync::Arc;
//! use std::collections::HashMap;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let classifier_agent: Arc<dyn Agent> = todo!();
//! # let billing_agent: Arc<dyn Agent> = todo!();
//! # let technical_agent: Arc<dyn Agent> = todo!();
//! let categories = vec!["billing".to_string(), "technical".to_string()];
//! let classifier = LLMClassifier::new(classifier_agent, categories);
//!
//! let mut agents = HashMap::new();
//! agents.insert("billing".to_string(), billing_agent);
//! agents.insert("technical".to_string(), technical_agent);
//!
//! let router = RouterAgent::new(RouterConfig {
//!     classifier: Arc::new(classifier),
//!     agents,
//!     default_key: None,
//! })?;
//!
//! let result = router.process(Message::with_text("user", "I have a billing question")).await?;
//! # Ok(())
//! # }
//! ```

use std::collections::HashMap;
use std::sync::Arc;

use crate::core::{Agent, AgentError, Message};
use serde_json::json;

/// ClassifierAgent is responsible for determining routing decisions.
///
/// The classifier analyzes the input message and returns a category/intent
/// that determines which specialist agent should handle the request.
#[async_trait::async_trait]
pub trait ClassifierAgent: Agent {
    /// Classify determines the category/intent for routing.
    ///
    /// # Arguments
    ///
    /// * `message` - Message to classify
    ///
    /// # Returns
    ///
    /// Category/intent string that maps to a specialist agent
    async fn classify(&self, message: &Message) -> Result<String, AgentError>;
}

/// Configuration for RouterAgent.
pub struct RouterConfig {
    /// Classifier determines which agent to route to
    pub classifier: Arc<dyn ClassifierAgent>,
    /// Agents maps categories to specialist agents
    pub agents: HashMap<String, Arc<dyn Agent>>,
    /// DefaultKey specifies fallback agent when classification doesn't match (optional)
    pub default_key: Option<String>,
}

/// Router agent that routes messages based on classification.
///
/// The router uses a classifier to determine message intent/category, then
/// delegates to the corresponding specialist agent. This enables efficient
/// conditional processing without executing all agents.
///
/// The router pattern is ideal when requests have clear categories and
/// different agents handle different types of requests.
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{RouterAgent, RouterConfig, SimpleClassifier};
/// use std::sync::Arc;
/// use std::collections::HashMap;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let classifier_agent: Arc<dyn Agent> = todo!();
/// # let spam_agent: Arc<dyn Agent> = todo!();
/// # let quality_agent: Arc<dyn Agent> = todo!();
/// let mut keywords = HashMap::new();
/// keywords.insert("spam".to_string(), vec!["buy".to_string(), "discount".to_string()]);
/// keywords.insert("quality".to_string(), vec!["improve".to_string(), "better".to_string()]);
/// let classifier = SimpleClassifier::new(classifier_agent, keywords);
///
/// let mut agents = HashMap::new();
/// agents.insert("spam".to_string(), spam_agent);
/// agents.insert("quality".to_string(), quality_agent);
///
/// let router = RouterAgent::new(RouterConfig {
///     classifier: Arc::new(classifier),
///     agents,
///     default_key: Some("quality".to_string()),
/// })?;
/// # Ok(())
/// # }
/// ```
pub struct RouterAgent {
    classifier: Arc<dyn ClassifierAgent>,
    agents: HashMap<String, Arc<dyn Agent>>,
    default_key: Option<String>,
}

impl RouterAgent {
    /// Create a new router agent.
    ///
    /// # Arguments
    ///
    /// * `config` - Router configuration with classifier and agents
    ///
    /// The classifier's classify method should return category strings that
    /// match keys in the agents map. If default_key is specified, requests with
    /// unmatched categories will be routed to that agent instead of failing.
    ///
    /// # Errors
    ///
    /// Returns an error if agents map is empty or default_key is invalid.
    pub fn new(config: RouterConfig) -> Result<Self, AgentError> {
        if config.agents.is_empty() {
            return Err(AgentError::InvalidInput(
                "at least one agent is required".to_string(),
            ));
        }

        // Validate default key if provided
        if let Some(ref default_key) = config.default_key {
            if !config.agents.contains_key(default_key) {
                return Err(AgentError::InvalidInput(format!(
                    "default key '{}' not found in agents map",
                    default_key
                )));
            }
        }

        Ok(Self {
            classifier: config.classifier,
            agents: config.agents,
            default_key: config.default_key,
        })
    }

    /// Get the classifier.
    pub fn classifier(&self) -> &Arc<dyn ClassifierAgent> {
        &self.classifier
    }

    /// Get the specialist agents.
    pub fn agents(&self) -> &HashMap<String, Arc<dyn Agent>> {
        &self.agents
    }

    /// Get the default key.
    pub fn default_key(&self) -> Option<&str> {
        self.default_key.as_deref()
    }
}

#[async_trait::async_trait]
impl Agent for RouterAgent {
    fn name(&self) -> &str {
        "RouterAgent"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut cap_set = std::collections::HashSet::new();

        // Add classifier capabilities
        for cap in self.classifier.capabilities() {
            cap_set.insert(cap);
        }

        // Add agent capabilities
        for agent in self.agents.values() {
            for cap in agent.capabilities() {
                cap_set.insert(cap);
            }
        }

        let mut capabilities: Vec<String> = cap_set.into_iter().collect();
        capabilities.push("router".to_string());
        capabilities.push("conditional".to_string());
        capabilities.push("classification".to_string());

        capabilities
    }

    /// Classify the message and route to appropriate agent.
    ///
    /// The process follows these steps:
    /// 1. Classification: Determine message category/intent
    /// 2. Route selection: Look up corresponding agent
    /// 3. Execution: Delegate to selected agent
    ///
    /// If classification fails, an error is returned. If the classified category
    /// doesn't match any agent and no default is configured, an error is returned.
    ///
    /// The final message includes metadata about the routing decision.
    ///
    /// # Arguments
    ///
    /// * `message` - Input message
    ///
    /// # Returns
    ///
    /// Response from the selected specialist agent
    ///
    /// # Errors
    ///
    /// Returns an error if classification fails or no matching agent found.
    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Step 1: Classify the message
        let mut category = self.classifier.classify(&message).await.map_err(|e| {
            AgentError::ProcessingError(format!("classification failed: {}", e))
        })?;

        // Step 2: Select agent based on category
        let agent = if let Some(agent) = self.agents.get(&category) {
            agent
        } else if let Some(ref default_key) = self.default_key {
            // Try default agent if configured
            category = default_key.clone();
            &self.agents[default_key]
        } else {
            let available_categories: Vec<_> = self.agents.keys().cloned().collect();
            return Err(AgentError::ProcessingError(format!(
                "no agent found for category '{}' (available: {})",
                category,
                available_categories.join(", ")
            )));
        };

        // Step 3: Execute selected agent
        let mut result = agent.process(message).await.map_err(|e| {
            AgentError::ProcessingError(format!(
                "agent '{}' (category: {}) failed: {}",
                agent.name(),
                category,
                e
            ))
        })?;

        // Add routing metadata
        result
            .metadata
            .insert("routed_category".to_string(), json!(category));
        result
            .metadata
            .insert("routed_agent".to_string(), json!(agent.name()));
        result
            .metadata
            .insert("available_routes".to_string(), json!(self.agents.len()));

        Ok(result)
    }
}

/// SimpleClassifier provides keyword-based classification.
///
/// This classifier uses simple string matching to determine categories.
/// For production use, consider implementing a custom ClassifierAgent with
/// ML-based classification or more sophisticated logic.
pub struct SimpleClassifier {
    agent: Arc<dyn Agent>,
    keywords: HashMap<String, Vec<String>>,
}

impl SimpleClassifier {
    /// Create a keyword-based classifier.
    ///
    /// # Arguments
    ///
    /// * `agent` - Fallback agent for complex classifications
    /// * `keywords` - Map of categories to keyword lists
    pub fn new(agent: Arc<dyn Agent>, keywords: HashMap<String, Vec<String>>) -> Self {
        Self { agent, keywords }
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }

    /// Get the keywords map.
    pub fn keywords(&self) -> &HashMap<String, Vec<String>> {
        &self.keywords
    }
}

#[async_trait::async_trait]
impl Agent for SimpleClassifier {
    fn name(&self) -> &str {
        "SimpleClassifier"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = self.agent.capabilities();
        caps.push("classification".to_string());
        caps.push("keyword-matching".to_string());
        caps
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        self.agent.process(message).await
    }
}

#[async_trait::async_trait]
impl ClassifierAgent for SimpleClassifier {
    /// Classify determines category using keyword matching.
    async fn classify(&self, message: &Message) -> Result<String, AgentError> {
        let content = message
            .content_as_str()
            .ok_or_else(|| AgentError::InvalidInput("message content must be a string".to_string()))?
            .to_lowercase();

        // Check each category's keywords
        let mut max_matches = 0;
        let mut best_category = String::new();

        for (category, keywords) in &self.keywords {
            let matches = keywords
                .iter()
                .filter(|keyword| content.contains(&keyword.to_lowercase()))
                .count();

            if matches > max_matches {
                max_matches = matches;
                best_category = category.clone();
            }
        }

        if best_category.is_empty() {
            return Err(AgentError::ProcessingError(
                "unable to classify message - no keyword matches found".to_string(),
            ));
        }

        Ok(best_category)
    }
}

/// LLMClassifier uses an LLM agent for classification.
///
/// This classifier prompts an LLM to determine the category. The LLM is given
/// a list of valid categories and must respond with one of them.
pub struct LLMClassifier {
    agent: Arc<dyn Agent>,
    categories: Vec<String>,
    prompt_template: String,
}

impl LLMClassifier {
    /// Create an LLM-based classifier.
    ///
    /// # Arguments
    ///
    /// * `agent` - LLM agent for classification
    /// * `categories` - List of valid category names
    pub fn new(agent: Arc<dyn Agent>, categories: Vec<String>) -> Self {
        let categories = if categories.is_empty() {
            vec!["general".to_string()]
        } else {
            categories
        };

        let prompt_template = format!(
            "Classify the following message into one of these categories: {}\n\nReply with ONLY the category name, nothing else.\n\nMessage: ",
            categories.join(", ")
        );

        Self {
            agent,
            categories,
            prompt_template,
        }
    }

    /// Get the underlying agent.
    pub fn agent(&self) -> &Arc<dyn Agent> {
        &self.agent
    }

    /// Get the categories.
    pub fn categories(&self) -> &[String] {
        &self.categories
    }
}

#[async_trait::async_trait]
impl Agent for LLMClassifier {
    fn name(&self) -> &str {
        "LLMClassifier"
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = self.agent.capabilities();
        caps.push("classification".to_string());
        caps.push("llm-classification".to_string());
        caps
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        self.agent.process(message).await
    }
}

#[async_trait::async_trait]
impl ClassifierAgent for LLMClassifier {
    /// Classify uses LLM to determine category.
    async fn classify(&self, message: &Message) -> Result<String, AgentError> {
        let content = message
            .content_as_str()
            .ok_or_else(|| AgentError::InvalidInput("message content must be a string".to_string()))?;

        // Build classification prompt
        let classification_msg = Message::with_text("user", format!("{}{}", self.prompt_template, content));

        // Get LLM classification
        let result = self.agent.process(classification_msg).await.map_err(|e| {
            AgentError::ProcessingError(format!("llm classification failed: {}", e))
        })?;

        let category = result
            .content_as_str()
            .ok_or_else(|| AgentError::ProcessingError("llm returned non-string content".to_string()))?
            .trim();

        // Validate category is in allowed list
        for valid_cat in &self.categories {
            if category.eq_ignore_ascii_case(valid_cat) {
                return Ok(valid_cat.clone());
            }
        }

        Err(AgentError::ProcessingError(format!(
            "llm returned invalid category '{}' (valid: {})",
            category,
            self.categories.join(", ")
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Mock agent for testing
    struct MockAgent {
        name: String,
        response: String,
    }

    #[async_trait::async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            &self.name
        }

        fn capabilities(&self) -> Vec<String> {
            vec![format!("{}_capability", self.name)]
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", &self.response))
        }
    }

    // Mock classifier for testing
    struct MockClassifier {
        category: String,
    }

    #[async_trait::async_trait]
    impl Agent for MockClassifier {
        fn name(&self) -> &str {
            "MockClassifier"
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            Ok(message)
        }
    }

    #[async_trait::async_trait]
    impl ClassifierAgent for MockClassifier {
        async fn classify(&self, _message: &Message) -> Result<String, AgentError> {
            Ok(self.category.clone())
        }
    }

    #[tokio::test]
    async fn test_router_basic() {
        let classifier = Arc::new(MockClassifier {
            category: "billing".to_string(),
        });

        let billing_agent = Arc::new(MockAgent {
            name: "billing".to_string(),
            response: "Billing response".to_string(),
        });

        let technical_agent = Arc::new(MockAgent {
            name: "technical".to_string(),
            response: "Technical response".to_string(),
        });

        let mut agents = HashMap::new();
        agents.insert("billing".to_string(), billing_agent as Arc<dyn Agent>);
        agents.insert("technical".to_string(), technical_agent as Arc<dyn Agent>);

        let router = RouterAgent::new(RouterConfig {
            classifier,
            agents,
            default_key: None,
        })
        .unwrap();

        let message = Message::with_text("user", "billing question");
        let result = router.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Billing response"));
        assert_eq!(
            result.metadata.get("routed_category"),
            Some(&json!("billing"))
        );
    }

    #[tokio::test]
    async fn test_router_with_default() {
        let classifier = Arc::new(MockClassifier {
            category: "unknown".to_string(),
        });

        let billing_agent = Arc::new(MockAgent {
            name: "billing".to_string(),
            response: "Billing response".to_string(),
        });

        let mut agents = HashMap::new();
        agents.insert("billing".to_string(), billing_agent as Arc<dyn Agent>);

        let router = RouterAgent::new(RouterConfig {
            classifier,
            agents,
            default_key: Some("billing".to_string()),
        })
        .unwrap();

        let message = Message::with_text("user", "some question");
        let result = router.process(message).await.unwrap();

        assert_eq!(result.content_as_str(), Some("Billing response"));
        assert_eq!(
            result.metadata.get("routed_category"),
            Some(&json!("billing"))
        );
    }

    #[tokio::test]
    async fn test_router_no_match_no_default() {
        let classifier = Arc::new(MockClassifier {
            category: "unknown".to_string(),
        });

        let billing_agent = Arc::new(MockAgent {
            name: "billing".to_string(),
            response: "Billing response".to_string(),
        });

        let mut agents = HashMap::new();
        agents.insert("billing".to_string(), billing_agent as Arc<dyn Agent>);

        let router = RouterAgent::new(RouterConfig {
            classifier,
            agents,
            default_key: None,
        })
        .unwrap();

        let message = Message::with_text("user", "some question");
        let result = router.process(message).await;

        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("no agent found"));
    }

    #[tokio::test]
    async fn test_simple_classifier() {
        let agent = Arc::new(MockAgent {
            name: "base".to_string(),
            response: "response".to_string(),
        });

        let mut keywords = HashMap::new();
        keywords.insert(
            "billing".to_string(),
            vec!["invoice".to_string(), "payment".to_string()],
        );
        keywords.insert(
            "technical".to_string(),
            vec!["bug".to_string(), "error".to_string()],
        );

        let classifier = SimpleClassifier::new(agent, keywords);

        let message = Message::with_text("user", "I have a payment issue");
        let category = classifier.classify(&message).await.unwrap();
        assert_eq!(category, "billing");

        let message2 = Message::with_text("user", "Found a bug in the system");
        let category2 = classifier.classify(&message2).await.unwrap();
        assert_eq!(category2, "technical");
    }

    #[tokio::test]
    async fn test_simple_classifier_no_match() {
        let agent = Arc::new(MockAgent {
            name: "base".to_string(),
            response: "response".to_string(),
        });

        let mut keywords = HashMap::new();
        keywords.insert("billing".to_string(), vec!["invoice".to_string()]);

        let classifier = SimpleClassifier::new(agent, keywords);

        let message = Message::with_text("user", "random question");
        let result = classifier.classify(&message).await;

        assert!(result.is_err());
        assert!(result
            .unwrap_err()
            .to_string()
            .contains("no keyword matches"));
    }

    #[tokio::test]
    async fn test_llm_classifier() {
        let agent = Arc::new(MockAgent {
            name: "llm".to_string(),
            response: "billing".to_string(),
        });

        let categories = vec!["billing".to_string(), "technical".to_string()];
        let classifier = LLMClassifier::new(agent, categories);

        let message = Message::with_text("user", "payment question");
        let category = classifier.classify(&message).await.unwrap();
        assert_eq!(category, "billing");
    }

    #[tokio::test]
    async fn test_router_capabilities() {
        let classifier = Arc::new(MockClassifier {
            category: "billing".to_string(),
        });

        let billing_agent = Arc::new(MockAgent {
            name: "billing".to_string(),
            response: "response".to_string(),
        });

        let mut agents = HashMap::new();
        agents.insert("billing".to_string(), billing_agent as Arc<dyn Agent>);

        let router = RouterAgent::new(RouterConfig {
            classifier,
            agents,
            default_key: None,
        })
        .unwrap();

        let caps = router.capabilities();
        assert!(caps.contains(&"router".to_string()));
        assert!(caps.contains(&"conditional".to_string()));
        assert!(caps.contains(&"classification".to_string()));
    }
}
