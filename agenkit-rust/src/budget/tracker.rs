//! Cost tracking and storage.

use crate::budget::models::{CostRecord, UsageStats};
use crate::budget::pricing::ModelPricing;
use async_trait::async_trait;
use std::collections::HashMap;
use std::sync::Arc;
use thiserror::Error;
use tokio::sync::RwLock;

/// Cost storage errors.
#[derive(Error, Debug)]
pub enum StorageError {
    #[error("record not found: {0}")]
    NotFound(String),

    #[error("storage error: {0}")]
    Other(String),
}

pub type StorageResult<T> = Result<T, StorageError>;

/// Abstract cost storage interface.
#[async_trait]
pub trait CostStorage: Send + Sync {
    /// Save a cost record.
    async fn save(&self, record: &CostRecord) -> StorageResult<()>;

    /// Get all records for a session.
    async fn get_session_records(&self, session_id: &str) -> StorageResult<Vec<CostRecord>>;

    /// Get all records for an agent.
    async fn get_agent_records(&self, agent_name: &str) -> StorageResult<Vec<CostRecord>>;

    /// Get all records.
    async fn get_all_records(&self) -> StorageResult<Vec<CostRecord>>;

    /// Delete all records for a session.
    async fn delete_session(&self, session_id: &str) -> StorageResult<usize>;

    /// Delete all records.
    async fn clear(&self) -> StorageResult<usize>;
}

/// In-memory cost storage.
#[derive(Clone)]
pub struct InMemoryCostStorage {
    records: Arc<RwLock<Vec<CostRecord>>>,
}

impl InMemoryCostStorage {
    /// Create a new in-memory storage.
    pub fn new() -> Self {
        Self {
            records: Arc::new(RwLock::new(Vec::new())),
        }
    }
}

impl Default for InMemoryCostStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl CostStorage for InMemoryCostStorage {
    async fn save(&self, record: &CostRecord) -> StorageResult<()> {
        let mut records = self.records.write().await;
        records.push(record.clone());
        Ok(())
    }

    async fn get_session_records(&self, session_id: &str) -> StorageResult<Vec<CostRecord>> {
        let records = self.records.read().await;
        Ok(records
            .iter()
            .filter(|r| r.session_id == session_id)
            .cloned()
            .collect())
    }

    async fn get_agent_records(&self, agent_name: &str) -> StorageResult<Vec<CostRecord>> {
        let records = self.records.read().await;
        Ok(records
            .iter()
            .filter(|r| r.agent_name == agent_name)
            .cloned()
            .collect())
    }

    async fn get_all_records(&self) -> StorageResult<Vec<CostRecord>> {
        let records = self.records.read().await;
        Ok(records.clone())
    }

    async fn delete_session(&self, session_id: &str) -> StorageResult<usize> {
        let mut records = self.records.write().await;
        let before = records.len();
        records.retain(|r| r.session_id != session_id);
        Ok(before - records.len())
    }

    async fn clear(&self) -> StorageResult<usize> {
        let mut records = self.records.write().await;
        let count = records.len();
        records.clear();
        Ok(count)
    }
}

/// Cost tracker for recording and querying costs.
#[derive(Clone)]
pub struct CostTracker {
    storage: Arc<dyn CostStorage>,
    pricing: ModelPricing,
}

impl CostTracker {
    /// Create a new cost tracker with in-memory storage.
    pub fn new() -> Self {
        Self {
            storage: Arc::new(InMemoryCostStorage::new()),
            pricing: ModelPricing::new(),
        }
    }

    /// Create a new cost tracker with custom storage and pricing.
    pub fn with_storage_and_pricing(
        storage: Arc<dyn CostStorage>,
        pricing: ModelPricing,
    ) -> Self {
        Self { storage, pricing }
    }

    /// Record a cost with automatic calculation.
    pub async fn record_cost(
        &self,
        session_id: &str,
        agent_name: &str,
        model: &str,
        input_tokens: usize,
        output_tokens: usize,
        thinking_tokens: usize,
        metadata: Option<serde_json::Value>,
    ) -> Result<String, String> {
        // Calculate base cost
        let cost = self
            .pricing
            .calculate(model, input_tokens, output_tokens)
            .await?;

        // Calculate thinking cost (typically uses output token pricing)
        let thinking_cost = if thinking_tokens > 0 {
            self.pricing
                .calculate(model, 0, thinking_tokens)
                .await?
        } else {
            0.0
        };

        // Create record
        let mut record = CostRecord::new(
            session_id.to_string(),
            agent_name.to_string(),
            model.to_string(),
            input_tokens,
            output_tokens,
            thinking_tokens,
            cost + thinking_cost,
            thinking_cost,
        );

        if let Some(metadata) = metadata {
            record = record.with_metadata(metadata);
        }

        // Save record
        self.storage
            .save(&record)
            .await
            .map_err(|e| e.to_string())?;

        Ok(record.record_id)
    }

    /// Record a cost with explicit cost value.
    pub async fn record_cost_explicit(
        &self,
        session_id: &str,
        agent_name: &str,
        model: &str,
        input_tokens: usize,
        output_tokens: usize,
        thinking_tokens: usize,
        cost: f64,
        thinking_cost: f64,
        metadata: Option<serde_json::Value>,
    ) -> Result<String, String> {
        let mut record = CostRecord::new(
            session_id.to_string(),
            agent_name.to_string(),
            model.to_string(),
            input_tokens,
            output_tokens,
            thinking_tokens,
            cost,
            thinking_cost,
        );

        if let Some(metadata) = metadata {
            record = record.with_metadata(metadata);
        }

        self.storage
            .save(&record)
            .await
            .map_err(|e| e.to_string())?;

        Ok(record.record_id)
    }

    /// Get total cost for a session.
    pub async fn get_session_cost(&self, session_id: &str) -> Result<f64, String> {
        let records = self
            .storage
            .get_session_records(session_id)
            .await
            .map_err(|e| e.to_string())?;

        Ok(records.iter().map(|r| r.cost).sum())
    }

    /// Get total cost for an agent.
    pub async fn get_agent_cost(&self, agent_name: &str) -> Result<f64, String> {
        let records = self
            .storage
            .get_agent_records(agent_name)
            .await
            .map_err(|e| e.to_string())?;

        Ok(records.iter().map(|r| r.cost).sum())
    }

    /// Get global total cost.
    pub async fn get_global_cost(&self) -> Result<f64, String> {
        let records = self
            .storage
            .get_all_records()
            .await
            .map_err(|e| e.to_string())?;

        Ok(records.iter().map(|r| r.cost).sum())
    }

    /// Get usage stats for a session.
    pub async fn get_session_stats(&self, session_id: &str) -> Result<UsageStats, String> {
        let records = self
            .storage
            .get_session_records(session_id)
            .await
            .map_err(|e| e.to_string())?;

        let mut stats = UsageStats::new();
        for record in records {
            stats.add_record(&record);
        }

        Ok(stats)
    }

    /// Get usage stats for an agent.
    pub async fn get_agent_stats(&self, agent_name: &str) -> Result<UsageStats, String> {
        let records = self
            .storage
            .get_agent_records(agent_name)
            .await
            .map_err(|e| e.to_string())?;

        let mut stats = UsageStats::new();
        for record in records {
            stats.add_record(&record);
        }

        Ok(stats)
    }

    /// Get global usage stats.
    pub async fn get_global_stats(&self) -> Result<UsageStats, String> {
        let records = self
            .storage
            .get_all_records()
            .await
            .map_err(|e| e.to_string())?;

        let mut stats = UsageStats::new();
        stats.enable_agent_tracking();

        for record in records {
            stats.add_record(&record);
        }

        Ok(stats)
    }

    /// Get all session costs.
    pub async fn get_all_session_costs(&self) -> Result<HashMap<String, f64>, String> {
        let records = self
            .storage
            .get_all_records()
            .await
            .map_err(|e| e.to_string())?;

        let mut session_costs = HashMap::new();
        for record in records {
            *session_costs.entry(record.session_id.clone()).or_insert(0.0) += record.cost;
        }

        Ok(session_costs)
    }

    /// Get all agent costs.
    pub async fn get_all_agent_costs(&self) -> Result<HashMap<String, f64>, String> {
        let records = self
            .storage
            .get_all_records()
            .await
            .map_err(|e| e.to_string())?;

        let mut agent_costs = HashMap::new();
        for record in records {
            *agent_costs.entry(record.agent_name.clone()).or_insert(0.0) += record.cost;
        }

        Ok(agent_costs)
    }

    /// Clear all costs for a session.
    pub async fn clear_session(&self, session_id: &str) -> Result<usize, String> {
        self.storage
            .delete_session(session_id)
            .await
            .map_err(|e| e.to_string())
    }

    /// Clear all costs.
    pub async fn clear_all(&self) -> Result<usize, String> {
        self.storage.clear().await.map_err(|e| e.to_string())
    }
}

impl Default for CostTracker {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cost_tracker_basic() {
        let tracker = CostTracker::new();

        let record_id = tracker
            .record_cost("session-1", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        assert!(!record_id.is_empty());

        let session_cost = tracker.get_session_cost("session-1").await.unwrap();
        assert!(session_cost > 0.0);
    }

    #[tokio::test]
    async fn test_multiple_sessions() {
        let tracker = CostTracker::new();

        tracker
            .record_cost("session-1", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        tracker
            .record_cost("session-2", "agent-1", "gpt-3.5-turbo", 2000, 1000, 0, None)
            .await
            .unwrap();

        let session1_cost = tracker.get_session_cost("session-1").await.unwrap();
        let session2_cost = tracker.get_session_cost("session-2").await.unwrap();
        let global_cost = tracker.get_global_cost().await.unwrap();

        assert!(session1_cost > session2_cost); // GPT-4 is more expensive
        assert!((global_cost - (session1_cost + session2_cost)).abs() < 0.001);
    }

    #[tokio::test]
    async fn test_agent_costs() {
        let tracker = CostTracker::new();

        tracker
            .record_cost("session-1", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        tracker
            .record_cost("session-2", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        tracker
            .record_cost("session-1", "agent-2", "gpt-3.5-turbo", 1000, 500, 0, None)
            .await
            .unwrap();

        let agent1_cost = tracker.get_agent_cost("agent-1").await.unwrap();
        let agent2_cost = tracker.get_agent_cost("agent-2").await.unwrap();

        assert!(agent1_cost > agent2_cost);
    }

    #[tokio::test]
    async fn test_usage_stats() {
        let tracker = CostTracker::new();

        tracker
            .record_cost("session-1", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        tracker
            .record_cost("session-1", "agent-1", "gpt-3.5-turbo", 2000, 1000, 0, None)
            .await
            .unwrap();

        let stats = tracker.get_session_stats("session-1").await.unwrap();

        assert_eq!(stats.total_calls, 2);
        assert_eq!(stats.total_input_tokens, 3000);
        assert_eq!(stats.total_output_tokens, 1500);
        assert_eq!(stats.by_model.len(), 2);
    }

    #[tokio::test]
    async fn test_clear_session() {
        let tracker = CostTracker::new();

        tracker
            .record_cost("session-1", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        tracker
            .record_cost("session-2", "agent-1", "gpt-4", 1000, 500, 0, None)
            .await
            .unwrap();

        let deleted = tracker.clear_session("session-1").await.unwrap();
        assert_eq!(deleted, 1);

        let session1_cost = tracker.get_session_cost("session-1").await.unwrap();
        assert_eq!(session1_cost, 0.0);

        let session2_cost = tracker.get_session_cost("session-2").await.unwrap();
        assert!(session2_cost > 0.0);
    }
}
