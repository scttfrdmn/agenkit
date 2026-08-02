//! Core data models for budget tracking.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Record of a single API call cost.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CostRecord {
    /// Unique record identifier
    pub record_id: String,

    /// Session identifier
    pub session_id: String,

    /// Agent identifier
    pub agent_name: String,

    /// Model name (e.g., "gpt-4", "claude-3-opus")
    pub model: String,

    /// Timestamp of the API call
    pub timestamp: DateTime<Utc>,

    /// Number of input tokens
    pub input_tokens: usize,

    /// Number of output tokens
    pub output_tokens: usize,

    /// Number of thinking/reasoning tokens (o3, Claude 4 extended)
    #[serde(default)]
    pub thinking_tokens: usize,

    /// Total cost in USD
    pub cost: f64,

    /// Cost for thinking tokens in USD
    #[serde(default)]
    pub thinking_cost: f64,

    /// Optional metadata (e.g., request_id, endpoint)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,
}

impl CostRecord {
    /// Create a new cost record.
    // Eight arguments, all of them required and none groupable: this is a flat record
    // constructor whose fields the caller must supply. A params struct would just be
    // `CostRecord` minus the generated id (#778).
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        session_id: String,
        agent_name: String,
        model: String,
        input_tokens: usize,
        output_tokens: usize,
        thinking_tokens: usize,
        cost: f64,
        thinking_cost: f64,
    ) -> Self {
        Self {
            record_id: uuid::Uuid::new_v4().to_string(),
            session_id,
            agent_name,
            model,
            timestamp: Utc::now(),
            input_tokens,
            output_tokens,
            thinking_tokens,
            cost,
            thinking_cost,
            metadata: None,
        }
    }

    /// Set metadata.
    pub fn with_metadata(mut self, metadata: serde_json::Value) -> Self {
        self.metadata = Some(metadata);
        self
    }

    /// Get total tokens.
    pub fn total_tokens(&self) -> usize {
        self.input_tokens + self.output_tokens + self.thinking_tokens
    }

    /// Convert to dictionary representation.
    pub fn to_dict(&self) -> HashMap<String, serde_json::Value> {
        let mut dict = HashMap::new();
        dict.insert("record_id".to_string(), serde_json::json!(self.record_id));
        dict.insert("session_id".to_string(), serde_json::json!(self.session_id));
        dict.insert("agent_name".to_string(), serde_json::json!(self.agent_name));
        dict.insert("model".to_string(), serde_json::json!(self.model));
        dict.insert(
            "timestamp".to_string(),
            serde_json::json!(self.timestamp.to_rfc3339()),
        );
        dict.insert(
            "input_tokens".to_string(),
            serde_json::json!(self.input_tokens),
        );
        dict.insert(
            "output_tokens".to_string(),
            serde_json::json!(self.output_tokens),
        );
        dict.insert(
            "thinking_tokens".to_string(),
            serde_json::json!(self.thinking_tokens),
        );
        dict.insert("cost".to_string(), serde_json::json!(self.cost));
        dict.insert(
            "thinking_cost".to_string(),
            serde_json::json!(self.thinking_cost),
        );

        if let Some(ref metadata) = self.metadata {
            dict.insert("metadata".to_string(), metadata.clone());
        }

        dict
    }
}

/// Usage statistics aggregation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageStats {
    /// Total cost in USD
    pub total_cost: f64,

    /// Total input tokens
    pub total_input_tokens: usize,

    /// Total output tokens
    pub total_output_tokens: usize,

    /// Number of API calls
    pub total_calls: usize,

    /// Per-model breakdown
    pub by_model: HashMap<String, ModelStats>,

    /// Per-agent breakdown (if applicable)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub by_agent: Option<HashMap<String, AgentStats>>,
}

impl UsageStats {
    /// Create new empty usage stats.
    pub fn new() -> Self {
        Self {
            total_cost: 0.0,
            total_input_tokens: 0,
            total_output_tokens: 0,
            total_calls: 0,
            by_model: HashMap::new(),
            by_agent: None,
        }
    }

    /// Add a cost record to stats.
    pub fn add_record(&mut self, record: &CostRecord) {
        self.total_cost += record.cost;
        self.total_input_tokens += record.input_tokens;
        self.total_output_tokens += record.output_tokens;
        self.total_calls += 1;

        // Update model stats
        let model_stats = self.by_model.entry(record.model.clone()).or_default();
        model_stats.add_record(record);

        // Update agent stats if tracking
        if let Some(ref mut by_agent) = self.by_agent {
            let agent_stats = by_agent
                .entry(record.agent_name.clone())
                .or_insert_with(AgentStats::new);
            agent_stats.add_record(record);
        }
    }

    /// Enable agent-level tracking.
    pub fn enable_agent_tracking(&mut self) {
        if self.by_agent.is_none() {
            self.by_agent = Some(HashMap::new());
        }
    }

    /// Get total tokens.
    pub fn total_tokens(&self) -> usize {
        self.total_input_tokens + self.total_output_tokens
    }

    /// Get average cost per call.
    pub fn avg_cost_per_call(&self) -> f64 {
        if self.total_calls == 0 {
            0.0
        } else {
            self.total_cost / self.total_calls as f64
        }
    }
}

impl Default for UsageStats {
    fn default() -> Self {
        Self::new()
    }
}

/// Per-model statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelStats {
    pub cost: f64,
    pub input_tokens: usize,
    pub output_tokens: usize,
    pub calls: usize,
}

impl ModelStats {
    pub fn new() -> Self {
        Self {
            cost: 0.0,
            input_tokens: 0,
            output_tokens: 0,
            calls: 0,
        }
    }

    pub fn add_record(&mut self, record: &CostRecord) {
        self.cost += record.cost;
        self.input_tokens += record.input_tokens;
        self.output_tokens += record.output_tokens;
        self.calls += 1;
    }
}

impl Default for ModelStats {
    fn default() -> Self {
        Self::new()
    }
}

/// Per-agent statistics.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentStats {
    pub cost: f64,
    pub input_tokens: usize,
    pub output_tokens: usize,
    pub calls: usize,
}

impl AgentStats {
    pub fn new() -> Self {
        Self {
            cost: 0.0,
            input_tokens: 0,
            output_tokens: 0,
            calls: 0,
        }
    }

    pub fn add_record(&mut self, record: &CostRecord) {
        self.cost += record.cost;
        self.input_tokens += record.input_tokens;
        self.output_tokens += record.output_tokens;
        self.calls += 1;
    }
}

impl Default for AgentStats {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cost_record_creation() {
        let record = CostRecord::new(
            "session-1".to_string(),
            "agent-1".to_string(),
            "gpt-4".to_string(),
            1000,
            500,
            0,
            0.05,
            0.0,
        );

        assert_eq!(record.session_id, "session-1");
        assert_eq!(record.agent_name, "agent-1");
        assert_eq!(record.model, "gpt-4");
        assert_eq!(record.input_tokens, 1000);
        assert_eq!(record.output_tokens, 500);
        assert_eq!(record.thinking_tokens, 0);
        assert_eq!(record.cost, 0.05);
        assert_eq!(record.thinking_cost, 0.0);
        assert_eq!(record.total_tokens(), 1500);
    }

    #[test]
    fn test_usage_stats_aggregation() {
        let mut stats = UsageStats::new();

        let record1 = CostRecord::new(
            "session-1".to_string(),
            "agent-1".to_string(),
            "gpt-4".to_string(),
            1000,
            500,
            0,
            0.05,
            0.0,
        );

        let record2 = CostRecord::new(
            "session-1".to_string(),
            "agent-2".to_string(),
            "gpt-3.5-turbo".to_string(),
            2000,
            1000,
            0,
            0.01,
            0.0,
        );

        stats.enable_agent_tracking();
        stats.add_record(&record1);
        stats.add_record(&record2);

        assert!((stats.total_cost - 0.06).abs() < 0.001);
        assert_eq!(stats.total_input_tokens, 3000);
        assert_eq!(stats.total_output_tokens, 1500);
        assert_eq!(stats.total_calls, 2);
        assert_eq!(stats.by_model.len(), 2);
        assert_eq!(stats.by_agent.as_ref().unwrap().len(), 2);
    }

    #[test]
    fn test_model_stats() {
        let mut model_stats = ModelStats::new();

        let record = CostRecord::new(
            "session-1".to_string(),
            "agent-1".to_string(),
            "gpt-4".to_string(),
            1000,
            500,
            0,
            0.05,
            0.0,
        );

        model_stats.add_record(&record);

        assert_eq!(model_stats.cost, 0.05);
        assert_eq!(model_stats.input_tokens, 1000);
        assert_eq!(model_stats.output_tokens, 500);
        assert_eq!(model_stats.calls, 1);
    }
}
