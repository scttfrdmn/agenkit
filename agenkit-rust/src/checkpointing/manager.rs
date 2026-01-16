//! Checkpoint manager for high-level checkpoint operations.

use crate::checkpointing::{Checkpoint, CheckpointStorage};
use crate::core::Message;
use std::collections::HashMap;

/// Checkpoint manager configuration.
#[derive(Debug, Clone)]
pub struct CheckpointManagerConfig {
    /// Auto-checkpoint interval (number of steps)
    pub auto_checkpoint_interval: Option<usize>,
}

impl Default for CheckpointManagerConfig {
    fn default() -> Self {
        Self {
            auto_checkpoint_interval: None,
        }
    }
}

/// High-level checkpoint manager.
pub struct CheckpointManager {
    storage: Box<dyn CheckpointStorage>,
    config: CheckpointManagerConfig,
    session_steps: HashMap<String, usize>,
    session_last_checkpoint: HashMap<String, String>,
}

impl CheckpointManager {
    /// Create a new checkpoint manager.
    pub fn new(storage: Box<dyn CheckpointStorage>) -> Self {
        Self {
            storage,
            config: CheckpointManagerConfig::default(),
            session_steps: HashMap::new(),
            session_last_checkpoint: HashMap::new(),
        }
    }

    /// Create a new checkpoint manager with configuration.
    pub fn with_config(
        storage: Box<dyn CheckpointStorage>,
        config: CheckpointManagerConfig,
    ) -> Self {
        Self {
            storage,
            config,
            session_steps: HashMap::new(),
            session_last_checkpoint: HashMap::new(),
        }
    }

    /// Create a checkpoint.
    pub async fn create_checkpoint(
        &mut self,
        session_id: String,
        agent_name: String,
        step_number: usize,
        state: serde_json::Value,
        messages: Vec<Message>,
        metadata: Option<serde_json::Value>,
        parent_checkpoint_id: Option<String>,
    ) -> Result<String, Box<dyn std::error::Error>> {
        // Determine parent checkpoint ID
        let parent_id =
            parent_checkpoint_id.or_else(|| self.session_last_checkpoint.get(&session_id).cloned());

        // Create checkpoint
        let mut checkpoint =
            Checkpoint::new(session_id.clone(), agent_name, step_number, state, messages);

        if let Some(metadata) = metadata {
            checkpoint = checkpoint.with_metadata(metadata);
        }

        if let Some(parent_id) = parent_id {
            checkpoint = checkpoint.with_parent(parent_id);
        }

        // Save checkpoint
        self.storage.save(&checkpoint).await?;

        // Update tracking
        self.session_last_checkpoint
            .insert(session_id.clone(), checkpoint.checkpoint_id.clone());
        self.session_steps.insert(session_id, step_number);

        Ok(checkpoint.checkpoint_id)
    }

    /// Check if auto-checkpoint should be created.
    pub fn should_checkpoint(&self, session_id: &str, current_step: usize) -> bool {
        if let Some(interval) = self.config.auto_checkpoint_interval {
            if let Some(&last_step) = self.session_steps.get(session_id) {
                return current_step - last_step >= interval;
            }
            return true; // First checkpoint
        }
        false
    }

    /// Get the latest checkpoint for a session.
    pub async fn get_latest(
        &self,
        session_id: &str,
    ) -> Result<Option<Checkpoint>, Box<dyn std::error::Error>> {
        Ok(self.storage.get_latest(session_id).await?)
    }

    /// Load a checkpoint by ID.
    pub async fn load_checkpoint(
        &self,
        checkpoint_id: &str,
    ) -> Result<Option<Checkpoint>, Box<dyn std::error::Error>> {
        Ok(self.storage.load(checkpoint_id).await?)
    }

    /// List checkpoints for a session.
    pub async fn list_checkpoints(
        &self,
        session_id: &str,
        limit: Option<usize>,
    ) -> Result<Vec<Checkpoint>, Box<dyn std::error::Error>> {
        Ok(self.storage.list_checkpoints(session_id, limit).await?)
    }

    /// Restore state from a checkpoint.
    pub async fn restore_state(
        &self,
        checkpoint: &Checkpoint,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        Ok(checkpoint.state.clone())
    }

    /// Delete a checkpoint.
    pub async fn delete_checkpoint(
        &self,
        checkpoint_id: &str,
    ) -> Result<bool, Box<dyn std::error::Error>> {
        Ok(self.storage.delete(checkpoint_id).await?)
    }

    /// Delete all checkpoints for a session.
    pub async fn delete_session(
        &mut self,
        session_id: &str,
    ) -> Result<usize, Box<dyn std::error::Error>> {
        let count = self.storage.delete_session(session_id).await?;

        // Clean up tracking
        self.session_steps.remove(session_id);
        self.session_last_checkpoint.remove(session_id);

        Ok(count)
    }

    /// Get checkpoint history.
    pub async fn get_checkpoint_history(
        &self,
        checkpoint_id: &str,
        max_depth: usize,
    ) -> Result<Vec<Checkpoint>, Box<dyn std::error::Error>> {
        Ok(self
            .storage
            .get_checkpoint_history(checkpoint_id, max_depth)
            .await?)
    }

    /// Prune old checkpoints, keeping only the most recent N.
    pub async fn prune_old_checkpoints(
        &mut self,
        session_id: &str,
        keep_last: usize,
    ) -> Result<usize, Box<dyn std::error::Error>> {
        let checkpoints = self.storage.list_checkpoints(session_id, None).await?;

        if checkpoints.len() <= keep_last {
            return Ok(0);
        }

        let to_delete = checkpoints.len() - keep_last;
        let mut deleted = 0;

        // Delete oldest checkpoints
        for checkpoint in checkpoints.iter().skip(keep_last) {
            if self.storage.delete(&checkpoint.checkpoint_id).await? {
                deleted += 1;
            }
        }

        Ok(deleted)
    }

    /// Get session statistics.
    pub async fn get_session_stats(
        &self,
        session_id: &str,
    ) -> Result<serde_json::Value, Box<dyn std::error::Error>> {
        let checkpoints = self.storage.list_checkpoints(session_id, None).await?;

        let total_checkpoints = checkpoints.len();
        let current_step = self.session_steps.get(session_id).copied().unwrap_or(0);
        let latest_checkpoint_id = self.session_last_checkpoint.get(session_id).cloned();

        Ok(serde_json::json!({
            "session_id": session_id,
            "total_checkpoints": total_checkpoints,
            "current_step": current_step,
            "latest_checkpoint_id": latest_checkpoint_id,
        }))
    }

    /// Replay from a checkpoint.
    pub async fn replay_from_checkpoint<F, Fut>(
        &self,
        checkpoint_id: &str,
        replay_fn: F,
        up_to_step: Option<usize>,
    ) -> Result<Vec<serde_json::Value>, Box<dyn std::error::Error>>
    where
        F: Fn(Checkpoint, serde_json::Value) -> Fut,
        Fut: std::future::Future<Output = Result<serde_json::Value, Box<dyn std::error::Error>>>,
    {
        // Get checkpoint history
        let history = self
            .storage
            .get_checkpoint_history(checkpoint_id, usize::MAX)
            .await?;

        let mut results = Vec::new();

        // Replay in chronological order (reverse history)
        for checkpoint in history.iter().rev() {
            if let Some(max_step) = up_to_step {
                if checkpoint.step_number > max_step {
                    break;
                }
            }

            let state = checkpoint.state.clone();
            let result = replay_fn(checkpoint.clone(), state).await?;
            results.push(result);
        }

        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::checkpointing::InMemoryCheckpointStorage;

    #[tokio::test]
    async fn test_checkpoint_manager_create() {
        let storage = Box::new(InMemoryCheckpointStorage::new());
        let mut manager = CheckpointManager::new(storage);

        let checkpoint_id = manager
            .create_checkpoint(
                "session-1".to_string(),
                "test-agent".to_string(),
                1,
                serde_json::json!({"counter": 1}),
                vec![],
                None,
                None,
            )
            .await
            .unwrap();

        assert!(!checkpoint_id.is_empty());

        // Load the checkpoint
        let checkpoint = manager.load_checkpoint(&checkpoint_id).await.unwrap();
        assert!(checkpoint.is_some());
    }

    #[tokio::test]
    async fn test_checkpoint_manager_auto_parent() {
        let storage = Box::new(InMemoryCheckpointStorage::new());
        let mut manager = CheckpointManager::new(storage);

        // Create first checkpoint
        let checkpoint_id1 = manager
            .create_checkpoint(
                "session-1".to_string(),
                "test-agent".to_string(),
                1,
                serde_json::json!({}),
                vec![],
                None,
                None,
            )
            .await
            .unwrap();

        // Create second checkpoint (should auto-link to first)
        let checkpoint_id2 = manager
            .create_checkpoint(
                "session-1".to_string(),
                "test-agent".to_string(),
                2,
                serde_json::json!({}),
                vec![],
                None,
                None, // No explicit parent
            )
            .await
            .unwrap();

        let checkpoint2 = manager
            .load_checkpoint(&checkpoint_id2)
            .await
            .unwrap()
            .unwrap();
        assert_eq!(checkpoint2.parent_checkpoint_id, Some(checkpoint_id1));
    }

    #[tokio::test]
    async fn test_checkpoint_manager_auto_checkpoint() {
        let storage = Box::new(InMemoryCheckpointStorage::new());
        let config = CheckpointManagerConfig {
            auto_checkpoint_interval: Some(5),
        };
        let mut manager = CheckpointManager::with_config(storage, config);

        // Should checkpoint on first step
        assert!(manager.should_checkpoint("session-1", 1));

        // Create checkpoint at step 1
        manager
            .create_checkpoint(
                "session-1".to_string(),
                "test-agent".to_string(),
                1,
                serde_json::json!({}),
                vec![],
                None,
                None,
            )
            .await
            .unwrap();

        // Should not checkpoint at step 2-5
        assert!(!manager.should_checkpoint("session-1", 2));
        assert!(!manager.should_checkpoint("session-1", 5));

        // Should checkpoint at step 6 (1 + 5)
        assert!(manager.should_checkpoint("session-1", 6));
    }

    #[tokio::test]
    async fn test_checkpoint_manager_prune() {
        let storage = Box::new(InMemoryCheckpointStorage::new());
        let mut manager = CheckpointManager::new(storage);

        // Create 5 checkpoints
        for i in 1..=5 {
            manager
                .create_checkpoint(
                    "session-1".to_string(),
                    "test-agent".to_string(),
                    i,
                    serde_json::json!({"step": i}),
                    vec![],
                    None,
                    None,
                )
                .await
                .unwrap();
        }

        // Prune to keep last 2
        let deleted = manager.prune_old_checkpoints("session-1", 2).await.unwrap();
        assert_eq!(deleted, 3);

        // Verify only 2 remain
        let remaining = manager.list_checkpoints("session-1", None).await.unwrap();
        assert_eq!(remaining.len(), 2);
    }
}
