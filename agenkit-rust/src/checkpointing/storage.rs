//! Checkpoint storage implementations.

use crate::checkpointing::Checkpoint;
use async_trait::async_trait;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::RwLock;

/// Checkpoint storage errors.
#[derive(Error, Debug)]
pub enum StorageError {
    #[error("checkpoint not found: {0}")]
    NotFound(String),

    #[error("I/O error: {0}")]
    Io(#[from] std::io::Error),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("storage error: {0}")]
    Other(String),
}

pub type StorageResult<T> = Result<T, StorageError>;

/// Abstract checkpoint storage interface.
#[async_trait]
pub trait CheckpointStorage: Send + Sync {
    /// Save a checkpoint.
    async fn save(&self, checkpoint: &Checkpoint) -> StorageResult<()>;

    /// Load a checkpoint by ID.
    async fn load(&self, checkpoint_id: &str) -> StorageResult<Option<Checkpoint>>;

    /// List checkpoints for a session (sorted by timestamp, most recent first).
    async fn list_checkpoints(
        &self,
        session_id: &str,
        limit: Option<usize>,
    ) -> StorageResult<Vec<Checkpoint>>;

    /// Get the latest checkpoint for a session.
    async fn get_latest(&self, session_id: &str) -> StorageResult<Option<Checkpoint>>;

    /// Delete a checkpoint.
    async fn delete(&self, checkpoint_id: &str) -> StorageResult<bool>;

    /// Delete all checkpoints for a session.
    async fn delete_session(&self, session_id: &str) -> StorageResult<usize>;

    /// Get checkpoint history (traverse parent links).
    async fn get_checkpoint_history(
        &self,
        checkpoint_id: &str,
        max_depth: usize,
    ) -> StorageResult<Vec<Checkpoint>>;
}

/// In-memory checkpoint storage (for testing and development).
pub struct InMemoryCheckpointStorage {
    checkpoints: Arc<RwLock<HashMap<String, Checkpoint>>>,
    session_checkpoints: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

impl InMemoryCheckpointStorage {
    /// Create a new in-memory storage.
    pub fn new() -> Self {
        Self {
            checkpoints: Arc::new(RwLock::new(HashMap::new())),
            session_checkpoints: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Get storage statistics.
    pub async fn get_stats(&self) -> HashMap<String, usize> {
        let checkpoints = self.checkpoints.read().await;
        let sessions = self.session_checkpoints.read().await;

        let mut stats = HashMap::new();
        stats.insert("total_checkpoints".to_string(), checkpoints.len());
        stats.insert("total_sessions".to_string(), sessions.len());
        stats
    }
}

impl Default for InMemoryCheckpointStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl CheckpointStorage for InMemoryCheckpointStorage {
    async fn save(&self, checkpoint: &Checkpoint) -> StorageResult<()> {
        let mut checkpoints = self.checkpoints.write().await;
        let mut session_checkpoints = self.session_checkpoints.write().await;

        // Add to checkpoint map
        checkpoints.insert(checkpoint.checkpoint_id.clone(), checkpoint.clone());

        // Add to session list (maintain sorted order)
        let session_list = session_checkpoints
            .entry(checkpoint.session_id.clone())
            .or_insert_with(Vec::new);

        session_list.push(checkpoint.checkpoint_id.clone());

        // Sort by timestamp (most recent first)
        session_list.sort_by(|a, b| {
            let cp_a = checkpoints.get(a).unwrap();
            let cp_b = checkpoints.get(b).unwrap();
            cp_b.timestamp.cmp(&cp_a.timestamp)
        });

        Ok(())
    }

    async fn load(&self, checkpoint_id: &str) -> StorageResult<Option<Checkpoint>> {
        let checkpoints = self.checkpoints.read().await;
        Ok(checkpoints.get(checkpoint_id).cloned())
    }

    async fn list_checkpoints(
        &self,
        session_id: &str,
        limit: Option<usize>,
    ) -> StorageResult<Vec<Checkpoint>> {
        let checkpoints = self.checkpoints.read().await;
        let session_checkpoints = self.session_checkpoints.read().await;

        if let Some(checkpoint_ids) = session_checkpoints.get(session_id) {
            let mut result: Vec<Checkpoint> = checkpoint_ids
                .iter()
                .filter_map(|id| checkpoints.get(id).cloned())
                .collect();

            // Sort by timestamp (most recent first)
            result.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));

            if let Some(limit) = limit {
                result.truncate(limit);
            }

            Ok(result)
        } else {
            Ok(Vec::new())
        }
    }

    async fn get_latest(&self, session_id: &str) -> StorageResult<Option<Checkpoint>> {
        let mut checkpoints = self.list_checkpoints(session_id, Some(1)).await?;
        Ok(checkpoints.pop())
    }

    async fn delete(&self, checkpoint_id: &str) -> StorageResult<bool> {
        let mut checkpoints = self.checkpoints.write().await;
        let mut session_checkpoints = self.session_checkpoints.write().await;

        if let Some(checkpoint) = checkpoints.remove(checkpoint_id) {
            // Remove from session list
            if let Some(session_list) = session_checkpoints.get_mut(&checkpoint.session_id) {
                session_list.retain(|id| id != checkpoint_id);
            }
            Ok(true)
        } else {
            Ok(false)
        }
    }

    async fn delete_session(&self, session_id: &str) -> StorageResult<usize> {
        let mut checkpoints = self.checkpoints.write().await;
        let mut session_checkpoints = self.session_checkpoints.write().await;

        if let Some(checkpoint_ids) = session_checkpoints.remove(session_id) {
            let count = checkpoint_ids.len();
            for id in checkpoint_ids {
                checkpoints.remove(&id);
            }
            Ok(count)
        } else {
            Ok(0)
        }
    }

    async fn get_checkpoint_history(
        &self,
        checkpoint_id: &str,
        max_depth: usize,
    ) -> StorageResult<Vec<Checkpoint>> {
        let checkpoints = self.checkpoints.read().await;
        let mut history = Vec::new();
        let mut current_id = Some(checkpoint_id.to_string());
        let mut depth = 0;

        while let Some(id) = current_id {
            if depth >= max_depth {
                break;
            }

            if let Some(checkpoint) = checkpoints.get(&id) {
                history.push(checkpoint.clone());
                current_id = checkpoint.parent_checkpoint_id.clone();
                depth += 1;
            } else {
                break;
            }
        }

        Ok(history)
    }
}

/// File-based checkpoint storage (persistent).
pub struct FileCheckpointStorage {
    checkpoint_dir: PathBuf,
}

impl FileCheckpointStorage {
    /// Create a new file-based storage.
    pub fn new(checkpoint_dir: PathBuf) -> StorageResult<Self> {
        // Create checkpoint directory
        std::fs::create_dir_all(&checkpoint_dir)?;

        Ok(Self { checkpoint_dir })
    }

    /// Get session directory path.
    fn session_dir(&self, session_id: &str) -> PathBuf {
        self.checkpoint_dir.join(session_id)
    }

    /// Get checkpoint file path.
    fn checkpoint_path(&self, session_id: &str, checkpoint_id: &str) -> PathBuf {
        self.session_dir(session_id).join(format!("{}.json", checkpoint_id))
    }

    /// Get storage statistics.
    pub async fn get_stats(&self) -> StorageResult<HashMap<String, usize>> {
        let mut stats = HashMap::new();
        let mut total_checkpoints = 0;
        let mut total_sessions = 0;
        let mut total_size = 0;

        // Read all sessions
        let entries = tokio::fs::read_dir(&self.checkpoint_dir).await?;
        let mut entries = entries;

        while let Some(entry) = entries.next_entry().await? {
            if entry.file_type().await?.is_dir() {
                total_sessions += 1;

                // Count checkpoints in session
                let session_entries = tokio::fs::read_dir(entry.path()).await?;
                let mut session_entries = session_entries;

                while let Some(checkpoint_entry) = session_entries.next_entry().await? {
                    if checkpoint_entry.path().extension().and_then(|s| s.to_str()) == Some("json") {
                        total_checkpoints += 1;
                        let metadata = checkpoint_entry.metadata().await?;
                        total_size += metadata.len() as usize;
                    }
                }
            }
        }

        stats.insert("total_sessions".to_string(), total_sessions);
        stats.insert("total_checkpoints".to_string(), total_checkpoints);
        stats.insert("total_size_bytes".to_string(), total_size);

        Ok(stats)
    }
}

#[async_trait]
impl CheckpointStorage for FileCheckpointStorage {
    async fn save(&self, checkpoint: &Checkpoint) -> StorageResult<()> {
        // Create session directory
        let session_dir = self.session_dir(&checkpoint.session_id);
        tokio::fs::create_dir_all(&session_dir).await?;

        // Write checkpoint file
        let checkpoint_path = self.checkpoint_path(&checkpoint.session_id, &checkpoint.checkpoint_id);
        let json = checkpoint.to_json()?;
        tokio::fs::write(checkpoint_path, json).await?;

        Ok(())
    }

    async fn load(&self, checkpoint_id: &str) -> StorageResult<Option<Checkpoint>> {
        // Search all sessions for this checkpoint
        let entries = tokio::fs::read_dir(&self.checkpoint_dir).await?;
        let mut entries = entries;

        while let Some(entry) = entries.next_entry().await? {
            if entry.file_type().await?.is_dir() {
                let checkpoint_path = entry.path().join(format!("{}.json", checkpoint_id));
                if checkpoint_path.exists() {
                    let content = tokio::fs::read_to_string(&checkpoint_path).await?;
                    let checkpoint = Checkpoint::from_json(&content)?;
                    return Ok(Some(checkpoint));
                }
            }
        }

        Ok(None)
    }

    async fn list_checkpoints(
        &self,
        session_id: &str,
        limit: Option<usize>,
    ) -> StorageResult<Vec<Checkpoint>> {
        let session_dir = self.session_dir(session_id);

        if !session_dir.exists() {
            return Ok(Vec::new());
        }

        let entries = tokio::fs::read_dir(&session_dir).await?;
        let mut entries = entries;
        let mut checkpoints = Vec::new();

        while let Some(entry) = entries.next_entry().await? {
            if entry.path().extension().and_then(|s| s.to_str()) == Some("json") {
                let content = tokio::fs::read_to_string(entry.path()).await?;
                if let Ok(checkpoint) = Checkpoint::from_json(&content) {
                    checkpoints.push(checkpoint);
                }
            }
        }

        // Sort by timestamp (most recent first)
        checkpoints.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));

        if let Some(limit) = limit {
            checkpoints.truncate(limit);
        }

        Ok(checkpoints)
    }

    async fn get_latest(&self, session_id: &str) -> StorageResult<Option<Checkpoint>> {
        let mut checkpoints = self.list_checkpoints(session_id, Some(1)).await?;
        Ok(checkpoints.pop())
    }

    async fn delete(&self, checkpoint_id: &str) -> StorageResult<bool> {
        // Search all sessions for this checkpoint
        let entries = tokio::fs::read_dir(&self.checkpoint_dir).await?;
        let mut entries = entries;

        while let Some(entry) = entries.next_entry().await? {
            if entry.file_type().await?.is_dir() {
                let checkpoint_path = entry.path().join(format!("{}.json", checkpoint_id));
                if checkpoint_path.exists() {
                    tokio::fs::remove_file(&checkpoint_path).await?;
                    return Ok(true);
                }
            }
        }

        Ok(false)
    }

    async fn delete_session(&self, session_id: &str) -> StorageResult<usize> {
        let session_dir = self.session_dir(session_id);

        if !session_dir.exists() {
            return Ok(0);
        }

        // Count checkpoints before deletion
        let checkpoints = self.list_checkpoints(session_id, None).await?;
        let count = checkpoints.len();

        // Remove directory
        tokio::fs::remove_dir_all(&session_dir).await?;

        Ok(count)
    }

    async fn get_checkpoint_history(
        &self,
        checkpoint_id: &str,
        max_depth: usize,
    ) -> StorageResult<Vec<Checkpoint>> {
        let mut history = Vec::new();
        let mut current_id = Some(checkpoint_id.to_string());
        let mut depth = 0;

        while let Some(id) = current_id {
            if depth >= max_depth {
                break;
            }

            if let Some(checkpoint) = self.load(&id).await? {
                current_id = checkpoint.parent_checkpoint_id.clone();
                history.push(checkpoint);
                depth += 1;
            } else {
                break;
            }
        }

        Ok(history)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_in_memory_storage() {
        let storage = InMemoryCheckpointStorage::new();

        let checkpoint = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            1,
            serde_json::json!({"key": "value"}),
            vec![],
        );

        // Save
        storage.save(&checkpoint).await.unwrap();

        // Load
        let loaded = storage.load(&checkpoint.checkpoint_id).await.unwrap();
        assert!(loaded.is_some());
        assert_eq!(loaded.unwrap().checkpoint_id, checkpoint.checkpoint_id);

        // List
        let list = storage.list_checkpoints("session-1", None).await.unwrap();
        assert_eq!(list.len(), 1);

        // Delete
        let deleted = storage.delete(&checkpoint.checkpoint_id).await.unwrap();
        assert!(deleted);

        let loaded_after = storage.load(&checkpoint.checkpoint_id).await.unwrap();
        assert!(loaded_after.is_none());
    }

    #[tokio::test]
    async fn test_checkpoint_history() {
        let storage = InMemoryCheckpointStorage::new();

        // Create chain: checkpoint1 -> checkpoint2 -> checkpoint3
        let checkpoint1 = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            1,
            serde_json::json!({}),
            vec![],
        );
        storage.save(&checkpoint1).await.unwrap();

        let checkpoint2 = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            2,
            serde_json::json!({}),
            vec![],
        )
        .with_parent(checkpoint1.checkpoint_id.clone());
        storage.save(&checkpoint2).await.unwrap();

        let checkpoint3 = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            3,
            serde_json::json!({}),
            vec![],
        )
        .with_parent(checkpoint2.checkpoint_id.clone());
        storage.save(&checkpoint3).await.unwrap();

        // Get history
        let history = storage
            .get_checkpoint_history(&checkpoint3.checkpoint_id, 10)
            .await
            .unwrap();

        assert_eq!(history.len(), 3);
        assert_eq!(history[0].step_number, 3);
        assert_eq!(history[1].step_number, 2);
        assert_eq!(history[2].step_number, 1);
    }

    #[tokio::test]
    async fn test_file_storage() {
        let temp_dir = std::env::temp_dir().join("test_checkpoints");
        let _ = std::fs::remove_dir_all(&temp_dir); // Clean up from previous tests

        let storage = FileCheckpointStorage::new(temp_dir.clone()).unwrap();

        let checkpoint = Checkpoint::new(
            "session-1".to_string(),
            "test-agent".to_string(),
            1,
            serde_json::json!({"key": "value"}),
            vec![],
        );

        // Save
        storage.save(&checkpoint).await.unwrap();

        // Load
        let loaded = storage.load(&checkpoint.checkpoint_id).await.unwrap();
        assert!(loaded.is_some());

        // Clean up
        let _ = std::fs::remove_dir_all(&temp_dir);
    }
}
