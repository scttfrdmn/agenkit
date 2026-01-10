//! Durable agent wrapper with automatic checkpointing.

use crate::checkpointing::{CheckpointManager, InMemoryCheckpointStorage};
use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

/// Durable agent configuration.
#[derive(Debug, Clone)]
pub struct DurableAgentConfig {
    /// Checkpoint interval (number of steps)
    pub checkpoint_interval: usize,
    /// Auto-resume on first process call
    pub auto_resume: bool,
}

impl Default for DurableAgentConfig {
    fn default() -> Self {
        Self {
            checkpoint_interval: 5,
            auto_resume: true,
        }
    }
}

/// Durable agent wrapper providing automatic checkpointing.
pub struct DurableAgent<A: Agent> {
    agent: Arc<A>,
    agent_name: String,
    config: DurableAgentConfig,
    manager: Arc<Mutex<CheckpointManager>>,

    // Per-session tracking
    session_state: Arc<Mutex<HashMap<String, serde_json::Value>>>,
    session_steps: Arc<Mutex<HashMap<String, usize>>>,
    session_messages: Arc<Mutex<HashMap<String, Vec<Message>>>>,
    session_resumed: Arc<Mutex<HashMap<String, bool>>>,
}

impl<A: Agent + 'static> DurableAgent<A> {
    /// Create a new durable agent with in-memory storage.
    pub fn new(agent: A, agent_name: String) -> Self {
        let storage = Box::new(InMemoryCheckpointStorage::new());
        let manager = CheckpointManager::new(storage);

        Self {
            agent: Arc::new(agent),
            agent_name,
            config: DurableAgentConfig::default(),
            manager: Arc::new(Mutex::new(manager)),
            session_state: Arc::new(Mutex::new(HashMap::new())),
            session_steps: Arc::new(Mutex::new(HashMap::new())),
            session_messages: Arc::new(Mutex::new(HashMap::new())),
            session_resumed: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Create a new durable agent with custom manager and configuration.
    pub fn with_manager_and_config(
        agent: A,
        agent_name: String,
        manager: CheckpointManager,
        config: DurableAgentConfig,
    ) -> Self {
        Self {
            agent: Arc::new(agent),
            agent_name,
            config,
            manager: Arc::new(Mutex::new(manager)),
            session_state: Arc::new(Mutex::new(HashMap::new())),
            session_steps: Arc::new(Mutex::new(HashMap::new())),
            session_messages: Arc::new(Mutex::new(HashMap::new())),
            session_resumed: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Process a message with automatic checkpointing.
    pub async fn process(
        &self,
        message: &Message,
        session_id: &str,
    ) -> Result<Message, AgentError> {
        // Auto-resume on first call
        if self.config.auto_resume {
            let mut resumed = self.session_resumed.lock().await;
            if !resumed.contains_key(session_id) {
                drop(resumed); // Release lock before resuming
                if let Err(e) = self.resume(session_id, None).await {
                    eprintln!("Auto-resume failed: {}", e);
                }
                let mut resumed = self.session_resumed.lock().await;
                resumed.insert(session_id.to_string(), true);
            }
        }

        // Increment step counter
        let current_step = {
            let mut steps = self.session_steps.lock().await;
            let step = steps.entry(session_id.to_string()).or_insert(0);
            *step += 1;
            *step
        };

        // Add input message to history
        {
            let mut messages = self.session_messages.lock().await;
            let msg_list = messages
                .entry(session_id.to_string())
                .or_insert_with(Vec::new);
            msg_list.push(message.clone());
        }

        // Call wrapped agent
        let response = match self.agent.process(message.clone()).await {
            Ok(resp) => resp,
            Err(err) => {
                // On error, try to rollback to latest checkpoint
                eprintln!("Agent process error: {}, attempting rollback", err);
                if let Err(rollback_err) = self.resume(session_id, None).await {
                    eprintln!("Rollback failed: {}", rollback_err);
                }
                return Err(err);
            }
        };

        // Add response to history
        {
            let mut messages = self.session_messages.lock().await;
            if let Some(msg_list) = messages.get_mut(session_id) {
                msg_list.push(response.clone());
            }
        }

        // Update session state
        self.update_state(session_id, message, &response).await;

        // Auto-checkpoint if interval reached
        if current_step % self.config.checkpoint_interval == 0 {
            if let Err(e) = self.checkpoint(session_id, None).await {
                eprintln!("Auto-checkpoint failed: {}", e);
            }
        }

        Ok(response)
    }

    /// Create a checkpoint.
    pub async fn checkpoint(
        &self,
        session_id: &str,
        metadata: Option<serde_json::Value>,
    ) -> Result<String, Box<dyn std::error::Error>> {
        let state = self.get_state(session_id).await?;
        let messages = self.get_messages(session_id).await?;
        let step_number = {
            let steps = self.session_steps.lock().await;
            steps.get(session_id).copied().unwrap_or(0)
        };

        let mut manager = self.manager.lock().await;
        let checkpoint_id = manager
            .create_checkpoint(
                session_id.to_string(),
                self.agent_name.clone(),
                step_number,
                state,
                messages,
                metadata,
                None,
            )
            .await?;

        Ok(checkpoint_id)
    }

    /// Resume from a checkpoint.
    pub async fn resume(
        &self,
        session_id: &str,
        checkpoint_id: Option<&str>,
    ) -> Result<Option<serde_json::Value>, Box<dyn std::error::Error>> {
        let manager = self.manager.lock().await;

        let checkpoint = if let Some(id) = checkpoint_id {
            manager.load_checkpoint(id).await?
        } else {
            manager.get_latest(session_id).await?
        };

        if let Some(checkpoint) = checkpoint {
            // Restore state
            let mut state_map = self.session_state.lock().await;
            state_map.insert(session_id.to_string(), checkpoint.state.clone());

            // Restore messages
            let mut messages_map = self.session_messages.lock().await;
            messages_map.insert(session_id.to_string(), checkpoint.messages.clone());

            // Restore step counter
            let mut steps = self.session_steps.lock().await;
            steps.insert(session_id.to_string(), checkpoint.step_number);

            Ok(Some(checkpoint.state))
        } else {
            Ok(None)
        }
    }

    /// Get current state for a session.
    pub async fn get_state(
        &self,
        session_id: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let state_map = self.session_state.lock().await;
        Ok(state_map
            .get(session_id)
            .cloned()
            .unwrap_or(serde_json::json!({})))
    }

    /// Set state for a session.
    pub async fn set_state(
        &self,
        session_id: &str,
        state: serde_json::Value,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let mut state_map = self.session_state.lock().await;
        state_map.insert(session_id.to_string(), state);
        Ok(())
    }

    /// Get messages for a session.
    pub async fn get_messages(
        &self,
        session_id: &str,
    ) -> Result<Vec<Message>, Box<dyn std::error::Error>> {
        let messages_map = self.session_messages.lock().await;
        Ok(messages_map.get(session_id).cloned().unwrap_or_default())
    }

    /// Reset a session (clear all state).
    pub async fn reset_session(&self, session_id: &str) {
        let mut state_map = self.session_state.lock().await;
        let mut messages_map = self.session_messages.lock().await;
        let mut steps = self.session_steps.lock().await;
        let mut resumed = self.session_resumed.lock().await;

        state_map.remove(session_id);
        messages_map.remove(session_id);
        steps.remove(session_id);
        resumed.remove(session_id);
    }

    /// List checkpoints for a session.
    pub async fn list_checkpoints(
        &self,
        session_id: &str,
        limit: Option<usize>,
    ) -> Result<Vec<crate::checkpointing::Checkpoint>, Box<dyn std::error::Error>> {
        let manager = self.manager.lock().await;
        Ok(manager.list_checkpoints(session_id, limit).await?)
    }

    /// Delete all checkpoints for a session.
    pub async fn delete_checkpoints(
        &self,
        session_id: &str,
    ) -> Result<usize, Box<dyn std::error::Error>> {
        let mut manager = self.manager.lock().await;
        Ok(manager.delete_session(session_id).await?)
    }

    /// Get session statistics.
    pub async fn get_session_stats(
        &self,
        session_id: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let manager = self.manager.lock().await;
        Ok(manager.get_session_stats(session_id).await?)
    }

    /// Update state based on message exchange.
    async fn update_state(&self, session_id: &str, input: &Message, output: &Message) {
        let mut state_map = self.session_state.lock().await;
        let messages_map = self.session_messages.lock().await;

        let message_count = messages_map.get(session_id).map(|m| m.len()).unwrap_or(0);

        let state = serde_json::json!({
            "message_count": message_count,
            "last_input": input.content_as_str().unwrap_or(""),
            "last_output": output.content_as_str().unwrap_or(""),
            "last_metadata": output.metadata.clone(),
        });

        state_map.insert(session_id.to_string(), state);
    }
}

// DurableAgent also implements Agent trait for compatibility
#[async_trait]
impl<A: Agent + 'static> Agent for DurableAgent<A> {
    fn name(&self) -> &str {
        &self.agent_name
    }

    fn capabilities(&self) -> Vec<String> {
        self.agent.capabilities()
    }

    fn introspect(&self) -> IntrospectionResult {
        let mut result = self.agent.introspect();
        result.metadata.insert(
            "durable".to_string(),
            serde_json::json!({
                "checkpoint_interval": self.config.checkpoint_interval,
                "auto_resume": self.config.auto_resume,
            }),
        );
        result
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Default session ID for Agent trait compatibility
        self.process(&message, "default").await
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestAgent;

    #[async_trait]
    impl Agent for TestAgent {
        fn name(&self) -> &str {
            "test"
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text(
                "assistant",
                format!("Echo: {}", message.content_as_str().unwrap_or("")),
            ))
        }
    }

    #[tokio::test]
    async fn test_durable_agent_basic() {
        let agent = TestAgent;
        let durable = DurableAgent::new(agent, "test-durable".to_string());

        let msg = Message::with_text("user", "Hello");
        let response = durable.process(&msg, "session-1").await.unwrap();

        assert_eq!(response.content_as_str(), Some("Echo: Hello"));
    }

    #[tokio::test]
    async fn test_durable_agent_checkpoint_and_resume() {
        let agent = TestAgent;
        let durable = DurableAgent::new(agent, "test-durable".to_string());

        // Send a few messages
        for i in 1..=3 {
            let msg = Message::with_text("user", format!("Message {}", i));
            let _ = durable.process(&msg, "session-1").await.unwrap();
        }

        // Create checkpoint
        let checkpoint_id = durable.checkpoint("session-1", None).await.unwrap();

        // Send more messages
        for i in 4..=5 {
            let msg = Message::with_text("user", format!("Message {}", i));
            let _ = durable.process(&msg, "session-1").await.unwrap();
        }

        // Resume from checkpoint
        let state = durable
            .resume("session-1", Some(&checkpoint_id))
            .await
            .unwrap();
        assert!(state.is_some());

        // Verify message count restored
        let messages = durable.get_messages("session-1").await.unwrap();
        assert_eq!(messages.len(), 6); // 3 input + 3 output from before checkpoint
    }

    #[tokio::test]
    async fn test_durable_agent_auto_checkpoint() {
        let agent = TestAgent;
        let config = DurableAgentConfig {
            checkpoint_interval: 2,
            auto_resume: false,
        };

        let storage = Box::new(InMemoryCheckpointStorage::new());
        let manager = CheckpointManager::new(storage);
        let durable = DurableAgent::with_manager_and_config(agent, "test".to_string(), manager, config);

        // Send 4 messages (should create 2 auto-checkpoints at steps 2 and 4)
        for i in 1..=4 {
            let msg = Message::with_text("user", format!("Message {}", i));
            let _ = durable.process(&msg, "session-1").await.unwrap();
        }

        // Verify checkpoints were created
        let checkpoints = durable.list_checkpoints("session-1", None).await.unwrap();
        assert!(checkpoints.len() >= 2);
    }
}
