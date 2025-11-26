//! Conversational Pattern - Multi-turn Dialogue Management
//!
//! The Conversational pattern maintains context across multiple turns of conversation,
//! managing message history and ensuring responses take into account previous exchanges.
//!
//! # Key Concepts
//!
//! - **Message History**: Stores previous messages for context
//! - **Context Window**: Limits how many messages to retain
//! - **Automatic Pruning**: Removes oldest messages when limit exceeded
//! - **System Prompt Preservation**: Always keeps system messages
//!
//! # Use Cases
//!
//! - Chatbots and virtual assistants
//! - Customer support agents
//! - Interactive tutoring systems
//! - Any multi-turn conversation requiring context
//!
//! # Example
//!
//! ```no_run
//! use agenkit::core::{Agent, Message};
//! use agenkit::patterns::{ConversationalAgent, ConversationalConfig};
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let llm: Arc<dyn Agent> = todo!();
//! let agent = ConversationalAgent::new(ConversationalConfig {
//!     llm,
//!     max_history: 10,
//!     system_prompt: Some("You are a helpful assistant.".to_string()),
//!     include_system: true,
//! })?;
//!
//! // First turn
//! let response1 = agent.process(
//!     Message::with_text("user", "My name is Alice")
//! ).await?;
//!
//! // Second turn - agent remembers the name
//! let response2 = agent.process(
//!     Message::with_text("user", "What's my name?")
//! ).await?;
//! // Response: "Your name is Alice."
//! # Ok(())
//! # }
//! ```
//!
//! # References
//!
//! - LangChain: Conversation memory patterns
//! - ChatGPT: Multi-turn conversation management

use async_trait::async_trait;
use std::sync::{Arc, Mutex};

use crate::core::{Agent, AgentError, Message};

/// Configuration for ConversationalAgent.
pub struct ConversationalConfig {
    /// LLM agent that implements the chat interface
    pub llm: Arc<dyn Agent>,
    /// Maximum number of messages to retain (default: 10)
    pub max_history: usize,
    /// Optional system prompt to prepend to conversations
    pub system_prompt: Option<String>,
    /// Whether to include system prompt in history count (default: true)
    pub include_system: bool,
}

impl Default for ConversationalConfig {
    fn default() -> Self {
        Self {
            llm: Arc::new(DummyAgent), // Will be replaced
            max_history: 10,
            system_prompt: None,
            include_system: true,
        }
    }
}

// Dummy agent for default config (will never be used)
struct DummyAgent;

#[async_trait]
impl Agent for DummyAgent {
    fn name(&self) -> &str {
        "dummy"
    }

    fn capabilities(&self) -> Vec<String> {
        vec![]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        Err(AgentError::InvalidInput(
            "DummyAgent should never be called".to_string(),
        ))
    }
}

/// Agent that maintains conversation history for context-aware responses.
///
/// This agent stores previous messages and includes them when processing new messages,
/// allowing the LLM to maintain context across multiple turns.
///
/// # History Management
///
/// - Messages are pruned when history exceeds max_history
/// - System messages are always preserved
/// - Oldest user/assistant messages are removed first
/// - Both input and response messages are added to history
///
/// # Performance Characteristics
///
/// - O(1) message append
/// - O(n) history pruning (only when limit exceeded)
/// - Memory: O(max_history) messages
///
/// # Example
///
/// ```no_run
/// use agenkit::core::{Agent, Message};
/// use agenkit::patterns::{ConversationalAgent, ConversationalConfig};
/// use std::sync::Arc;
///
/// # async fn example() -> Result<(), Box<dyn std::error::Error>> {
/// # let llm: Arc<dyn Agent> = todo!();
/// let mut agent = ConversationalAgent::new(ConversationalConfig {
///     llm,
///     max_history: 10,
///     system_prompt: Some("You are a helpful assistant.".to_string()),
///     include_system: true,
/// })?;
///
/// let response = agent.process(
///     Message::with_text("user", "Hello!")
/// ).await?;
/// # Ok(())
/// # }
/// ```
pub struct ConversationalAgent {
    name: String,
    llm: Arc<dyn Agent>,
    max_history: usize,
    system_prompt: Option<String>,
    include_system: bool,
    history: Arc<Mutex<Vec<Message>>>,
}

impl ConversationalAgent {
    /// Creates a new conversational agent.
    ///
    /// # Arguments
    ///
    /// * `config` - Configuration for the agent
    ///
    /// # Errors
    ///
    /// Returns an error if max_history is 0.
    pub fn new(config: ConversationalConfig) -> Result<Self, AgentError> {
        if config.max_history == 0 {
            return Err(AgentError::InvalidInput(
                "max_history must be greater than 0".to_string(),
            ));
        }

        let mut history = Vec::new();

        // Add system prompt to history if provided
        if let Some(ref prompt) = config.system_prompt {
            if config.include_system {
                history.push(Message::with_text("system", prompt));
            }
        }

        Ok(Self {
            name: "ConversationalAgent".to_string(),
            llm: config.llm,
            max_history: config.max_history,
            system_prompt: config.system_prompt,
            include_system: config.include_system,
            history: Arc::new(Mutex::new(history)),
        })
    }

    /// Prune history to stay within max_history limit.
    ///
    /// System messages are preserved, and oldest user/assistant messages
    /// are removed first.
    fn prune_history(&self) {
        let mut history = self.history.lock().unwrap();

        if history.len() <= self.max_history {
            return;
        }

        // Separate system messages from conversation
        let mut system_messages = Vec::new();
        let mut conversation_messages = Vec::new();

        for msg in history.iter() {
            if msg.role == "system" {
                system_messages.push(msg.clone());
            } else {
                conversation_messages.push(msg.clone());
            }
        }

        // Keep only the most recent conversation messages
        let messages_to_keep = self.max_history.saturating_sub(system_messages.len());
        let kept_conversation = if conversation_messages.len() > messages_to_keep {
            let skip_count = conversation_messages.len() - messages_to_keep;
            conversation_messages.into_iter().skip(skip_count).collect()
        } else {
            conversation_messages
        };

        // Rebuild history with system messages first
        history.clear();
        history.extend(system_messages);
        history.extend(kept_conversation);
    }

    /// Clear conversation history.
    ///
    /// # Arguments
    ///
    /// * `keep_system` - If true, preserves system prompt (default: true)
    pub fn clear_history(&self, keep_system: bool) {
        let mut history = self.history.lock().unwrap();
        history.clear();

        if keep_system {
            if let Some(ref prompt) = self.system_prompt {
                if self.include_system {
                    history.push(Message::with_text("system", prompt));
                }
            }
        }
    }

    /// Get a copy of the current conversation history.
    pub fn get_history(&self) -> Vec<Message> {
        self.history.lock().unwrap().clone()
    }

    /// Get the current number of messages in history.
    pub fn history_length(&self) -> usize {
        self.history.lock().unwrap().len()
    }

    /// Set maximum history size.
    ///
    /// If new max is smaller than current history, history will be pruned immediately.
    pub fn set_max_history(&mut self, max: usize) {
        self.max_history = max;
        self.prune_history();
    }

    /// Export history in a serializable format.
    pub fn export_history(&self) -> Vec<serde_json::Value> {
        self.history
            .lock()
            .unwrap()
            .iter()
            .map(|msg| {
                serde_json::json!({
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata,
                })
            })
            .collect()
    }

    /// Import conversation history from serialized format.
    ///
    /// Useful for resuming conversations or testing.
    pub fn import_history(&self, history: Vec<serde_json::Value>) -> Result<(), AgentError> {
        let messages: Result<Vec<Message>, AgentError> = history
            .into_iter()
            .map(|msg| {
                let role = msg["role"].as_str().ok_or_else(|| {
                    AgentError::InvalidInput("Missing role in message".to_string())
                })?;

                let content = msg["content"].clone();

                let mut message = Message {
                    role: role.to_string(),
                    content,
                    metadata: std::collections::HashMap::new(),
                    timestamp: chrono::Utc::now(),
                };

                if let Some(metadata) = msg.get("metadata") {
                    if let Some(obj) = metadata.as_object() {
                        for (k, v) in obj {
                            message.metadata.insert(k.clone(), v.clone());
                        }
                    }
                }

                Ok::<Message, AgentError>(message)
            })
            .collect();

        let mut hist = self.history.lock().unwrap();
        *hist = messages?;

        Ok(())
    }
}

#[async_trait]
impl Agent for ConversationalAgent {
    fn name(&self) -> &str {
        &self.name
    }

    fn capabilities(&self) -> Vec<String> {
        vec![
            "conversational".to_string(),
            "history-management".to_string(),
        ]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Add user message to history
        {
            let mut history = self.history.lock().unwrap();
            history.push(message.clone());
        }

        // Prune history if needed
        self.prune_history();

        // Create a prompt with full conversation history
        let history_snapshot = self.get_history();

        // Build a single context message with all history
        let context = history_snapshot
            .iter()
            .map(|msg| {
                format!(
                    "{}: {}",
                    msg.role,
                    msg.content_as_str().unwrap_or("[no content]")
                )
            })
            .collect::<Vec<_>>()
            .join("\n");

        // Generate response with full context
        let context_message = Message::with_text("user", context);
        let response = self.llm.process(context_message).await?;

        // Add response to history
        {
            let mut history = self.history.lock().unwrap();
            history.push(response.clone());
        }

        // Prune again after adding response
        self.prune_history();

        Ok(response)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    // Mock LLM agent for testing
    struct MockLLMAgent {
        response_template: String,
        call_count: Arc<AtomicUsize>,
    }

    #[async_trait]
    impl Agent for MockLLMAgent {
        fn name(&self) -> &str {
            "mock_llm"
        }

        fn capabilities(&self) -> Vec<String> {
            vec!["mock".to_string()]
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            self.call_count.fetch_add(1, Ordering::SeqCst);

            let content = message.content_as_str().unwrap_or("");

            // Check if context includes previous messages
            let response = if content.contains("user: My name is Alice")
                && content.contains("user: What's my name?")
            {
                "Your name is Alice."
            } else {
                &self.response_template
            };

            Ok(Message::with_text("assistant", response))
        }
    }

    #[tokio::test]
    async fn test_conversational_basic() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Hello!".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 10,
            system_prompt: Some("You are a helpful assistant.".to_string()),
            include_system: true,
        })
        .unwrap();

        // Initial history should have system message
        assert_eq!(agent.history_length(), 1);

        let message = Message::with_text("user", "Hello");
        let response = agent.process(message).await.unwrap();

        assert_eq!(response.content_as_str().unwrap(), "Hello!");

        // History should now have system + user + assistant
        assert_eq!(agent.history_length(), 3);
    }

    #[tokio::test]
    async fn test_conversational_memory() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "I understand.".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 10,
            system_prompt: None,
            include_system: true,
        })
        .unwrap();

        // First turn
        let message1 = Message::with_text("user", "My name is Alice");
        agent.process(message1).await.unwrap();

        // Second turn - should remember context
        let message2 = Message::with_text("user", "What's my name?");
        let response2 = agent.process(message2).await.unwrap();

        // The mock agent checks if context contains both messages
        assert_eq!(response2.content_as_str().unwrap(), "Your name is Alice.");
    }

    #[tokio::test]
    async fn test_history_pruning() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 5,
            system_prompt: Some("System".to_string()),
            include_system: true,
        })
        .unwrap();

        // System message takes 1 slot, so we can fit 4 conversation messages (2 pairs)
        assert_eq!(agent.history_length(), 1);

        // Add multiple messages
        for i in 0..4 {
            let msg = Message::with_text("user", format!("Message {}", i));
            agent.process(msg).await.unwrap();
        }

        // Should have pruned: system + 4 most recent (2 user + 2 assistant)
        assert_eq!(agent.history_length(), 5);

        let history = agent.get_history();
        assert_eq!(history[0].role, "system");
    }

    #[tokio::test]
    async fn test_clear_history() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 10,
            system_prompt: Some("System".to_string()),
            include_system: true,
        })
        .unwrap();

        // Add some messages
        agent
            .process(Message::with_text("user", "Test"))
            .await
            .unwrap();

        assert_eq!(agent.history_length(), 3);

        // Clear but keep system
        agent.clear_history(true);
        assert_eq!(agent.history_length(), 1);

        // Clear everything
        agent.clear_history(false);
        assert_eq!(agent.history_length(), 0);
    }

    #[tokio::test]
    async fn test_export_import_history() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent = ConversationalAgent::new(ConversationalConfig {
            llm: llm.clone(),
            max_history: 10,
            system_prompt: None,
            include_system: true,
        })
        .unwrap();

        // Add some messages
        agent
            .process(Message::with_text("user", "Test"))
            .await
            .unwrap();

        // Export history
        let exported = agent.export_history();
        assert_eq!(exported.len(), 2);

        // Create new agent and import
        let agent2 = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 10,
            system_prompt: None,
            include_system: true,
        })
        .unwrap();

        agent2.import_history(exported).unwrap();
        assert_eq!(agent2.history_length(), 2);
    }

    #[tokio::test]
    async fn test_validation() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        // Test max_history = 0
        let result = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 0,
            system_prompt: None,
            include_system: true,
        });

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_get_history() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let agent = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 10,
            system_prompt: Some("System".to_string()),
            include_system: true,
        })
        .unwrap();

        agent
            .process(Message::with_text("user", "Test"))
            .await
            .unwrap();

        let history = agent.get_history();
        assert_eq!(history.len(), 3);
        assert_eq!(history[0].role, "system");
        assert_eq!(history[1].role, "user");
        assert_eq!(history[2].role, "assistant");
    }

    #[tokio::test]
    async fn test_set_max_history() {
        let llm = Arc::new(MockLLMAgent {
            response_template: "Response".to_string(),
            call_count: Arc::new(AtomicUsize::new(0)),
        });

        let mut agent = ConversationalAgent::new(ConversationalConfig {
            llm,
            max_history: 10,
            system_prompt: None,
            include_system: true,
        })
        .unwrap();

        // Add several messages
        for _ in 0..5 {
            agent
                .process(Message::with_text("user", "Test"))
                .await
                .unwrap();
        }

        assert_eq!(agent.history_length(), 10);

        // Reduce max_history
        agent.set_max_history(4);
        assert_eq!(agent.history_length(), 4);
    }
}
