//! Session Recording Framework
//!
//! Records agent sessions for replay and analysis.
//!
//! Automatically records all interactions with an agent, storing inputs,
//! outputs, timing, and metadata for debugging and evaluation.
//!
//! # Example
//!
//! ```no_run
//! use agenkit::evaluation::recorder::{SessionRecorder, FileRecordingStorage};
//! use agenkit::core::Agent;
//! use std::sync::Arc;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! # let agent: Arc<dyn Agent> = todo!();
//! let storage = FileRecordingStorage::new("./recordings");
//! let recorder = SessionRecorder::new(Some(Box::new(storage)));
//! let wrapped_agent = recorder.wrap(agent);
//!
//! // Use agent normally (automatically recorded)
//! // response = wrapped_agent.process(message).await?;
//!
//! // Finalize and save recording
//! recorder.finalize_session("session-123").await?;
//! # Ok(())
//! # }
//! ```

use async_trait::async_trait;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use uuid::Uuid;

use crate::core::{Agent, AgentError, Message};

/// Single agent interaction record.
///
/// Contains input, output, timing, and metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InteractionRecord {
    /// Unique interaction identifier
    pub interaction_id: String,
    /// Session identifier
    pub session_id: String,
    /// Input message
    pub input_message: serde_json::Value,
    /// Output message
    pub output_message: serde_json::Value,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Latency in milliseconds
    pub latency_ms: f64,
    /// Additional metadata
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl InteractionRecord {
    /// Creates a new interaction record.
    pub fn new(
        session_id: impl Into<String>,
        input_message: &Message,
        output_message: &Message,
        latency_ms: f64,
    ) -> Self {
        Self {
            interaction_id: Uuid::new_v4().to_string(),
            session_id: session_id.into(),
            input_message: message_to_json(input_message),
            output_message: message_to_json(output_message),
            timestamp: Utc::now(),
            latency_ms,
            metadata: HashMap::new(),
        }
    }

    /// Converts record to dictionary.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert(
            "interaction_id".to_string(),
            serde_json::json!(self.interaction_id),
        );
        result.insert("session_id".to_string(), serde_json::json!(self.session_id));
        result.insert("input_message".to_string(), self.input_message.clone());
        result.insert("output_message".to_string(), self.output_message.clone());
        result.insert(
            "timestamp".to_string(),
            serde_json::json!(self.timestamp.to_rfc3339()),
        );
        result.insert("latency_ms".to_string(), serde_json::json!(self.latency_ms));
        result.insert("metadata".to_string(), serde_json::json!(self.metadata));
        result
    }
}

/// Recording of entire session.
///
/// Contains all interactions and session metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionRecording {
    /// Session identifier
    pub session_id: String,
    /// Agent name
    pub agent_name: String,
    /// Session start time
    pub start_time: DateTime<Utc>,
    /// Session end time
    pub end_time: Option<DateTime<Utc>>,
    /// All interactions
    pub interactions: Vec<InteractionRecord>,
    /// Session metadata
    #[serde(skip_serializing_if = "HashMap::is_empty")]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl SessionRecording {
    /// Creates a new session recording.
    pub fn new(session_id: impl Into<String>, agent_name: impl Into<String>) -> Self {
        Self {
            session_id: session_id.into(),
            agent_name: agent_name.into(),
            start_time: Utc::now(),
            end_time: None,
            interactions: Vec::new(),
            metadata: HashMap::new(),
        }
    }

    /// Calculates session duration in seconds.
    pub fn duration_seconds(&self) -> Option<f64> {
        self.end_time
            .map(|end| (end - self.start_time).num_milliseconds() as f64 / 1000.0)
    }

    /// Gets number of interactions.
    pub fn interaction_count(&self) -> usize {
        self.interactions.len()
    }

    /// Gets total latency across all interactions.
    pub fn total_latency_ms(&self) -> f64 {
        self.interactions.iter().map(|i| i.latency_ms).sum()
    }

    /// Converts recording to dictionary.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let interactions: Vec<_> = self.interactions.iter().map(|i| i.to_dict()).collect();

        let mut result = HashMap::new();
        result.insert("session_id".to_string(), serde_json::json!(self.session_id));
        result.insert("agent_name".to_string(), serde_json::json!(self.agent_name));
        result.insert(
            "start_time".to_string(),
            serde_json::json!(self.start_time.to_rfc3339()),
        );
        result.insert("interactions".to_string(), serde_json::json!(interactions));
        result.insert("metadata".to_string(), serde_json::json!(self.metadata));

        if let Some(end) = self.end_time {
            result.insert("end_time".to_string(), serde_json::json!(end.to_rfc3339()));
        } else {
            result.insert("end_time".to_string(), serde_json::Value::Null);
        }

        result
    }
}

/// Storage interface for recordings.
///
/// Implement this to create custom storage backends (Redis, S3, Postgres, etc.).
#[async_trait]
pub trait RecordingStorage: Send + Sync {
    /// Saves recording.
    async fn save_recording(&self, recording: &SessionRecording) -> Result<(), AgentError>;

    /// Loads recording by session ID.
    async fn load_recording(
        &self,
        session_id: &str,
    ) -> Result<Option<SessionRecording>, AgentError>;

    /// Lists recordings with pagination.
    async fn list_recordings(
        &self,
        limit: usize,
        offset: usize,
    ) -> Result<Vec<SessionRecording>, AgentError>;

    /// Deletes recording.
    async fn delete_recording(&self, session_id: &str) -> Result<(), AgentError>;
}

/// File-based recording storage.
///
/// Stores recordings as JSON files on disk.
pub struct FileRecordingStorage {
    recordings_dir: PathBuf,
}

impl FileRecordingStorage {
    /// Creates a new file storage.
    ///
    /// # Arguments
    ///
    /// * `recordings_dir` - Directory to store recordings
    pub fn new(recordings_dir: impl AsRef<Path>) -> Self {
        let dir = recordings_dir.as_ref();

        // Create directory if needed
        let _ = fs::create_dir_all(dir);

        Self {
            recordings_dir: dir.to_path_buf(),
        }
    }

    /// Gets file path for session ID.
    fn file_path(&self, session_id: &str) -> PathBuf {
        self.recordings_dir.join(format!("{}.json", session_id))
    }
}

#[async_trait]
impl RecordingStorage for FileRecordingStorage {
    async fn save_recording(&self, recording: &SessionRecording) -> Result<(), AgentError> {
        let path = self.file_path(&recording.session_id);
        let json = serde_json::to_string_pretty(&recording.to_dict()).map_err(|e| {
            AgentError::ProcessingError(format!("Failed to serialize recording: {}", e))
        })?;

        fs::write(&path, json).map_err(|e| {
            AgentError::ProcessingError(format!("Failed to write recording: {}", e))
        })?;

        Ok(())
    }

    async fn load_recording(
        &self,
        session_id: &str,
    ) -> Result<Option<SessionRecording>, AgentError> {
        let path = self.file_path(session_id);

        if !path.exists() {
            return Ok(None);
        }

        let json = fs::read_to_string(&path)
            .map_err(|e| AgentError::ProcessingError(format!("Failed to read recording: {}", e)))?;

        let recording: SessionRecording = serde_json::from_str(&json).map_err(|e| {
            AgentError::ProcessingError(format!("Failed to parse recording: {}", e))
        })?;

        Ok(Some(recording))
    }

    async fn list_recordings(
        &self,
        limit: usize,
        offset: usize,
    ) -> Result<Vec<SessionRecording>, AgentError> {
        let mut recordings = Vec::new();

        // Find all JSON files
        let entries = fs::read_dir(&self.recordings_dir).map_err(|e| {
            AgentError::ProcessingError(format!("Failed to list recordings: {}", e))
        })?;

        // Collect and sort by modification time
        let mut files: Vec<_> = entries
            .filter_map(|entry| entry.ok())
            .filter(|entry| entry.path().extension().and_then(|s| s.to_str()) == Some("json"))
            .filter_map(|entry| {
                let path = entry.path();
                let metadata = fs::metadata(&path).ok()?;
                Some((path, metadata.modified().ok()?))
            })
            .collect();

        // Sort by modification time (most recent first)
        files.sort_by_key(|f| std::cmp::Reverse(f.1));

        // Apply pagination
        let start = offset;
        let end = (offset + limit).min(files.len());

        if start >= files.len() {
            return Ok(recordings);
        }

        // Load recordings
        for (path, _) in &files[start..end] {
            if let Ok(json) = fs::read_to_string(path) {
                if let Ok(recording) = serde_json::from_str::<SessionRecording>(&json) {
                    recordings.push(recording);
                }
            }
        }

        Ok(recordings)
    }

    async fn delete_recording(&self, session_id: &str) -> Result<(), AgentError> {
        let path = self.file_path(session_id);

        if path.exists() {
            fs::remove_file(&path).map_err(|e| {
                AgentError::ProcessingError(format!("Failed to delete recording: {}", e))
            })?;
        }

        Ok(())
    }
}

/// In-memory recording storage for testing.
///
/// Does not persist recordings across restarts.
pub struct InMemoryRecordingStorage {
    recordings: Arc<Mutex<HashMap<String, SessionRecording>>>,
}

impl InMemoryRecordingStorage {
    /// Creates a new in-memory storage.
    pub fn new() -> Self {
        Self {
            recordings: Arc::new(Mutex::new(HashMap::new())),
        }
    }
}

impl Default for InMemoryRecordingStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl RecordingStorage for InMemoryRecordingStorage {
    async fn save_recording(&self, recording: &SessionRecording) -> Result<(), AgentError> {
        let mut recordings = self.recordings.lock().unwrap();
        recordings.insert(recording.session_id.clone(), recording.clone());
        Ok(())
    }

    async fn load_recording(
        &self,
        session_id: &str,
    ) -> Result<Option<SessionRecording>, AgentError> {
        let recordings = self.recordings.lock().unwrap();
        Ok(recordings.get(session_id).cloned())
    }

    async fn list_recordings(
        &self,
        limit: usize,
        offset: usize,
    ) -> Result<Vec<SessionRecording>, AgentError> {
        let recordings = self.recordings.lock().unwrap();
        let mut list: Vec<_> = recordings.values().cloned().collect();

        // Sort by start time (most recent first)
        list.sort_by_key(|r| std::cmp::Reverse(r.start_time));

        // Apply pagination
        let start = offset;
        let end = (offset + limit).min(list.len());

        if start >= list.len() {
            return Ok(Vec::new());
        }

        Ok(list[start..end].to_vec())
    }

    async fn delete_recording(&self, session_id: &str) -> Result<(), AgentError> {
        let mut recordings = self.recordings.lock().unwrap();
        recordings.remove(session_id);
        Ok(())
    }
}

/// Records agent sessions for replay and analysis.
///
/// Automatically records all interactions with an agent.
pub struct SessionRecorder {
    storage: Arc<Box<dyn RecordingStorage>>,
    active_sessions: Arc<Mutex<HashMap<String, SessionRecording>>>,
}

impl SessionRecorder {
    /// Creates a new session recorder.
    ///
    /// # Arguments
    ///
    /// * `storage` - Storage backend (None = in-memory)
    pub fn new(storage: Option<Box<dyn RecordingStorage>>) -> Self {
        let storage = storage.unwrap_or_else(|| Box::new(InMemoryRecordingStorage::new()));

        Self {
            storage: Arc::new(storage),
            active_sessions: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    /// Wraps agent to record interactions.
    pub fn wrap(&self, agent: Arc<dyn Agent>) -> Arc<dyn Agent> {
        Arc::new(RecordingWrapper {
            agent,
            recorder: Arc::new(self.clone()),
        })
    }

    /// Starts recording session.
    pub fn start_session(&self, session_id: impl Into<String>, agent_name: impl Into<String>) {
        let mut sessions = self.active_sessions.lock().unwrap();
        let session_id = session_id.into();

        if !sessions.contains_key(&session_id) {
            sessions.insert(
                session_id.clone(),
                SessionRecording::new(session_id, agent_name),
            );
        }
    }

    /// Records single interaction.
    pub fn record_interaction(
        &self,
        session_id: &str,
        input_message: &Message,
        output_message: &Message,
        latency_ms: f64,
    ) {
        let mut sessions = self.active_sessions.lock().unwrap();

        // Get or create session
        if !sessions.contains_key(session_id) {
            sessions.insert(
                session_id.to_string(),
                SessionRecording::new(session_id, "unknown"),
            );
        }

        if let Some(session) = sessions.get_mut(session_id) {
            let record =
                InteractionRecord::new(session_id, input_message, output_message, latency_ms);
            session.interactions.push(record);
        }
    }

    /// Finalizes and saves session recording.
    pub async fn finalize_session(&self, session_id: &str) -> Result<(), AgentError> {
        let recording = {
            let mut sessions = self.active_sessions.lock().unwrap();
            sessions.remove(session_id)
        };

        if let Some(mut recording) = recording {
            recording.end_time = Some(Utc::now());
            self.storage.save_recording(&recording).await?;
        }

        Ok(())
    }

    /// Gets active session recording.
    pub fn get_session(&self, session_id: &str) -> Option<SessionRecording> {
        let sessions = self.active_sessions.lock().unwrap();
        sessions.get(session_id).cloned()
    }
}

impl Clone for SessionRecorder {
    fn clone(&self) -> Self {
        Self {
            storage: Arc::clone(&self.storage),
            active_sessions: Arc::clone(&self.active_sessions),
        }
    }
}

/// Wrapper agent that records interactions.
struct RecordingWrapper {
    agent: Arc<dyn Agent>,
    recorder: Arc<SessionRecorder>,
}

#[async_trait]
impl Agent for RecordingWrapper {
    fn name(&self) -> &str {
        self.agent.name()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Extract session ID from metadata
        let session_id = message
            .metadata
            .get("session_id")
            .and_then(|v| v.as_str())
            .unwrap_or("default")
            .to_string();

        // Start session if not already started
        {
            let sessions = self.recorder.active_sessions.lock().unwrap();
            if !sessions.contains_key(&session_id) {
                drop(sessions);
                self.recorder.start_session(&session_id, self.agent.name());
            }
        }

        // Process with timing
        let start = std::time::Instant::now();
        let output = self.agent.process(message.clone()).await;
        let latency_ms = start.elapsed().as_millis() as f64;

        // Record interaction (even if error)
        let output_msg = output
            .as_ref()
            .ok()
            .cloned()
            .unwrap_or_else(|| Message::with_text("assistant", "error"));
        self.recorder
            .record_interaction(&session_id, &message, &output_msg, latency_ms);

        output
    }
}

/// Converts message to JSON.
fn message_to_json(message: &Message) -> serde_json::Value {
    serde_json::json!({
        "role": message.role,
        "content": message.content,
        "metadata": message.metadata,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    struct MockAgent;

    #[async_trait]
    impl Agent for MockAgent {
        fn name(&self) -> &str {
            "mock"
        }

        async fn process(&self, _message: Message) -> Result<Message, AgentError> {
            Ok(Message::with_text("assistant", "response"))
        }
    }

    #[tokio::test]
    async fn test_interaction_record() {
        let input = Message::with_text("user", "hello");
        let output = Message::with_text("assistant", "hi");

        let record = InteractionRecord::new("session-1", &input, &output, 100.0);

        assert_eq!(record.session_id, "session-1");
        assert_eq!(record.latency_ms, 100.0);
        assert!(!record.interaction_id.is_empty());
    }

    #[tokio::test]
    async fn test_session_recording() {
        let mut recording = SessionRecording::new("session-1", "test-agent");

        assert_eq!(recording.session_id, "session-1");
        assert_eq!(recording.agent_name, "test-agent");
        assert_eq!(recording.interaction_count(), 0);

        let input = Message::with_text("user", "hello");
        let output = Message::with_text("assistant", "hi");
        let record = InteractionRecord::new("session-1", &input, &output, 100.0);

        recording.interactions.push(record);
        assert_eq!(recording.interaction_count(), 1);
        assert_eq!(recording.total_latency_ms(), 100.0);
    }

    #[tokio::test]
    async fn test_in_memory_storage() {
        let storage = InMemoryRecordingStorage::new();
        let recording = SessionRecording::new("session-1", "test-agent");

        storage.save_recording(&recording).await.unwrap();

        let loaded = storage.load_recording("session-1").await.unwrap();
        assert!(loaded.is_some());
        assert_eq!(loaded.unwrap().session_id, "session-1");

        let list = storage.list_recordings(10, 0).await.unwrap();
        assert_eq!(list.len(), 1);

        storage.delete_recording("session-1").await.unwrap();

        let loaded = storage.load_recording("session-1").await.unwrap();
        assert!(loaded.is_none());
    }

    #[tokio::test]
    async fn test_file_storage() {
        // Use a temporary test directory
        let test_dir = "./test_recordings_temp";
        let _ = fs::create_dir_all(test_dir);

        let storage = FileRecordingStorage::new(test_dir);
        let recording = SessionRecording::new("session-1", "test-agent");

        storage.save_recording(&recording).await.unwrap();

        let loaded = storage.load_recording("session-1").await.unwrap();
        assert!(loaded.is_some());
        assert_eq!(loaded.unwrap().session_id, "session-1");

        let list = storage.list_recordings(10, 0).await.unwrap();
        assert_eq!(list.len(), 1);

        storage.delete_recording("session-1").await.unwrap();

        let loaded = storage.load_recording("session-1").await.unwrap();
        assert!(loaded.is_none());

        // Cleanup
        let _ = fs::remove_dir_all(test_dir);
    }

    #[tokio::test]
    async fn test_session_recorder() {
        let recorder = SessionRecorder::new(None);
        let agent = Arc::new(MockAgent);
        let wrapped = recorder.wrap(agent);

        let mut message = Message::with_text("user", "hello");
        message
            .metadata
            .insert("session_id".to_string(), serde_json::json!("test-123"));

        let _response = wrapped.process(message).await.unwrap();

        let session = recorder.get_session("test-123");
        assert!(session.is_some());
        let session = session.unwrap();
        assert_eq!(session.session_id, "test-123");
        assert_eq!(session.interaction_count(), 1);

        recorder.finalize_session("test-123").await.unwrap();

        // Should be removed from active sessions
        let session = recorder.get_session("test-123");
        assert!(session.is_none());
    }
}
