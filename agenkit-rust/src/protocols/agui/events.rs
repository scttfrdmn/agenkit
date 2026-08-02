//! AG-UI (Agent-User Interaction) Protocol Events
//!
//! Provides event types for streaming agent-to-frontend communication.
//!
//! Reference: https://docs.ag-ui.com
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Event type identifier for AG-UI protocol events.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EventType {
    TextMessageStart,
    TextMessageChunk,
    TextMessageComplete,
    ToolCallStart,
    ToolCallChunk,
    ToolCallComplete,
    StateDelta,
    Interrupt,
    InterruptResponse,
    Error,
    Attachment,
    Metadata,
    Heartbeat,
}

/// Interrupt reason indicating why human approval is needed.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterruptReason {
    ApprovalRequired,
    ClarificationNeeded,
    ToolConfirmation,
    Escalation,
    UserRequested,
}

/// Action that can be taken in response to an interrupt.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InterruptAction {
    Approve,
    Reject,
    Edit,
    Retry,
    Escalate,
    Cancel,
    Continue,
}

/// Attachment type for multimodal content.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AttachmentType {
    File,
    Image,
    Audio,
    Video,
    Document,
}

/// Base trait for all AG-UI events.
pub trait AGUIEvent: Send + Sync {
    /// Get the event type.
    fn event_type(&self) -> EventType;

    /// Convert event to JSON value for serialization.
    fn to_json(&self) -> serde_json::Value;
}

/// Start of a text message from the agent.
///
/// Signals that the agent is beginning to generate a text response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextMessageStart {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub role: String,
    pub message_id: Option<String>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl TextMessageStart {
    pub fn new(role: impl Into<String>, message_id: Option<String>) -> Self {
        Self {
            event_type: EventType::TextMessageStart,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            role: role.into(),
            message_id,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

impl AGUIEvent for TextMessageStart {
    fn event_type(&self) -> EventType {
        EventType::TextMessageStart
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Chunk of text message content (streaming).
///
/// Contains incremental text content as the agent generates the response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextMessageChunk {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub content: String,
    pub message_id: Option<String>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl TextMessageChunk {
    pub fn new(content: impl Into<String>, message_id: Option<String>) -> Self {
        Self {
            event_type: EventType::TextMessageChunk,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            content: content.into(),
            message_id,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

impl AGUIEvent for TextMessageChunk {
    fn event_type(&self) -> EventType {
        EventType::TextMessageChunk
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Complete text message with full content.
///
/// Signals that the text message is complete and provides the full content.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextMessageComplete {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub content: String,
    pub finish_reason: String,
    pub message_id: Option<String>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl TextMessageComplete {
    pub fn new(
        content: impl Into<String>,
        finish_reason: impl Into<String>,
        message_id: Option<String>,
    ) -> Self {
        Self {
            event_type: EventType::TextMessageComplete,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            content: content.into(),
            finish_reason: finish_reason.into(),
            message_id,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

impl AGUIEvent for TextMessageComplete {
    fn event_type(&self) -> EventType {
        EventType::TextMessageComplete
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Start of a tool call execution.
///
/// Signals that the agent is beginning to execute a tool.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallStart {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub tool_name: String,
    pub tool_call_id: Option<String>,
    pub arguments: serde_json::Value,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ToolCallStart {
    pub fn new(
        tool_name: impl Into<String>,
        arguments: serde_json::Value,
        tool_call_id: Option<String>,
    ) -> Self {
        Self {
            event_type: EventType::ToolCallStart,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            tool_name: tool_name.into(),
            tool_call_id,
            arguments,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

impl AGUIEvent for ToolCallStart {
    fn event_type(&self) -> EventType {
        EventType::ToolCallStart
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Chunk of tool call execution progress (streaming).
///
/// Contains incremental updates about tool execution progress.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallChunk {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub progress: String,
    pub percentage: Option<f64>,
    pub tool_call_id: Option<String>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ToolCallChunk {
    pub fn new(
        progress: impl Into<String>,
        percentage: Option<f64>,
        tool_call_id: Option<String>,
    ) -> Self {
        Self {
            event_type: EventType::ToolCallChunk,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            progress: progress.into(),
            percentage,
            tool_call_id,
            metadata: HashMap::new(),
        }
    }
}

impl AGUIEvent for ToolCallChunk {
    fn event_type(&self) -> EventType {
        EventType::ToolCallChunk
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Complete tool call result.
///
/// Contains the final result of tool execution.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallComplete {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub tool_name: String,
    pub result: serde_json::Value,
    pub success: bool,
    pub error: Option<String>,
    pub tool_call_id: Option<String>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ToolCallComplete {
    pub fn new(
        tool_name: impl Into<String>,
        result: serde_json::Value,
        success: bool,
        error: Option<String>,
        tool_call_id: Option<String>,
    ) -> Self {
        Self {
            event_type: EventType::ToolCallComplete,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            tool_name: tool_name.into(),
            result,
            success,
            error,
            tool_call_id,
            metadata: HashMap::new(),
        }
    }
}

impl AGUIEvent for ToolCallComplete {
    fn event_type(&self) -> EventType {
        EventType::ToolCallComplete
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Incremental state update (event sourcing pattern).
///
/// Contains partial state changes to synchronize agent and frontend state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StateDelta {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub delta: serde_json::Value,
    pub path: Option<Vec<String>>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl StateDelta {
    pub fn new(delta: serde_json::Value, path: Option<Vec<String>>) -> Self {
        Self {
            event_type: EventType::StateDelta,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            delta,
            path,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

impl AGUIEvent for StateDelta {
    fn event_type(&self) -> EventType {
        EventType::StateDelta
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Interrupt requiring human attention.
///
/// Signals that the agent needs human input or approval to proceed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Interrupt {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub reason: InterruptReason,
    pub message: String,
    pub available_actions: Vec<InterruptAction>,
    pub context: HashMap<String, serde_json::Value>,
    pub interrupt_id: Option<String>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Interrupt {
    pub fn new(
        reason: InterruptReason,
        message: impl Into<String>,
        available_actions: Vec<InterruptAction>,
        context: HashMap<String, serde_json::Value>,
        interrupt_id: Option<String>,
    ) -> Self {
        Self {
            event_type: EventType::Interrupt,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            reason,
            message: message.into(),
            available_actions,
            context,
            interrupt_id,
            metadata: HashMap::new(),
        }
    }
}

impl AGUIEvent for Interrupt {
    fn event_type(&self) -> EventType {
        EventType::Interrupt
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Response to an interrupt event.
///
/// Contains the human's response to an interrupt request.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InterruptResponse {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub interrupt_id: String,
    pub action: InterruptAction,
    pub data: Option<serde_json::Value>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl InterruptResponse {
    pub fn new(
        interrupt_id: impl Into<String>,
        action: InterruptAction,
        data: Option<serde_json::Value>,
    ) -> Self {
        Self {
            event_type: EventType::InterruptResponse,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            interrupt_id: interrupt_id.into(),
            action,
            data,
            metadata: HashMap::new(),
        }
    }
}

impl AGUIEvent for InterruptResponse {
    fn event_type(&self) -> EventType {
        EventType::InterruptResponse
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Error event indicating an error occurred.
///
/// Contains error details and whether the error is recoverable.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorEvent {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub error_code: String,
    pub error_message: String,
    pub recoverable: bool,
    pub details: Option<serde_json::Value>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl ErrorEvent {
    pub fn new(
        error_code: impl Into<String>,
        error_message: impl Into<String>,
        recoverable: bool,
        details: Option<serde_json::Value>,
    ) -> Self {
        Self {
            event_type: EventType::Error,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            error_code: error_code.into(),
            error_message: error_message.into(),
            recoverable,
            details,
            metadata: HashMap::new(),
        }
    }
}

impl AGUIEvent for ErrorEvent {
    fn event_type(&self) -> EventType {
        EventType::Error
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Attachment containing multimodal content.
///
/// Contains file, image, audio, or video content.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Attachment {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub attachment_type: AttachmentType,
    pub content_type: String,
    pub url: Option<String>,
    pub data: Option<String>,
    pub filename: Option<String>,
    pub size: Option<u64>,
    #[serde(flatten)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Attachment {
    pub fn new(
        attachment_type: AttachmentType,
        content_type: impl Into<String>,
        url: Option<String>,
        data: Option<String>,
        filename: Option<String>,
        size: Option<u64>,
    ) -> Self {
        Self {
            event_type: EventType::Attachment,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            attachment_type,
            content_type: content_type.into(),
            url,
            data,
            filename,
            size,
            metadata: HashMap::new(),
        }
    }

    pub fn with_metadata(mut self, key: impl Into<String>, value: serde_json::Value) -> Self {
        self.metadata.insert(key.into(), value);
        self
    }
}

impl AGUIEvent for Attachment {
    fn event_type(&self) -> EventType {
        EventType::Attachment
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Metadata event containing agent/protocol metadata.
///
/// Contains information about agent capabilities, protocol version, etc.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetadataEvent {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    #[serde(flatten)]
    pub data: HashMap<String, serde_json::Value>,
}

impl MetadataEvent {
    pub fn new(data: HashMap<String, serde_json::Value>) -> Self {
        Self {
            event_type: EventType::Metadata,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            data,
        }
    }
}

impl AGUIEvent for MetadataEvent {
    fn event_type(&self) -> EventType {
        EventType::Metadata
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Heartbeat event for keeping connections alive.
///
/// Sent periodically to prevent connection timeouts.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HeartbeatEvent {
    pub event_type: EventType,
    pub timestamp: DateTime<Utc>,
    pub event_id: Option<String>,
    pub interval_ms: u64,
}

impl HeartbeatEvent {
    pub fn new(interval_ms: u64) -> Self {
        Self {
            event_type: EventType::Heartbeat,
            timestamp: Utc::now(),
            event_id: Some(format!("evt_{}", Uuid::new_v4())),
            interval_ms,
        }
    }
}

impl AGUIEvent for HeartbeatEvent {
    fn event_type(&self) -> EventType {
        EventType::Heartbeat
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::to_value(self).unwrap_or(serde_json::Value::Null)
    }
}

/// Parse an AG-UI event from JSON.
///
/// # Arguments
/// * `json` - JSON value to parse
///
/// # Returns
/// Parsed event as a boxed AGUIEvent trait object.
///
/// # Errors
/// Returns error if JSON doesn't match any known event type.
pub fn parse_event(json: serde_json::Value) -> Result<Box<dyn AGUIEvent>, String> {
    let event_type_str = json
        .get("event_type")
        .and_then(|v| v.as_str())
        .ok_or_else(|| "Missing event_type field".to_string())?;

    match event_type_str {
        "text_message_start" => Ok(Box::new(
            serde_json::from_value::<TextMessageStart>(json)
                .map_err(|e| format!("Failed to parse TextMessageStart: {}", e))?,
        )),
        "text_message_chunk" => Ok(Box::new(
            serde_json::from_value::<TextMessageChunk>(json)
                .map_err(|e| format!("Failed to parse TextMessageChunk: {}", e))?,
        )),
        "text_message_complete" => Ok(Box::new(
            serde_json::from_value::<TextMessageComplete>(json)
                .map_err(|e| format!("Failed to parse TextMessageComplete: {}", e))?,
        )),
        "tool_call_start" => Ok(Box::new(
            serde_json::from_value::<ToolCallStart>(json)
                .map_err(|e| format!("Failed to parse ToolCallStart: {}", e))?,
        )),
        "tool_call_chunk" => Ok(Box::new(
            serde_json::from_value::<ToolCallChunk>(json)
                .map_err(|e| format!("Failed to parse ToolCallChunk: {}", e))?,
        )),
        "tool_call_complete" => Ok(Box::new(
            serde_json::from_value::<ToolCallComplete>(json)
                .map_err(|e| format!("Failed to parse ToolCallComplete: {}", e))?,
        )),
        "state_delta" => Ok(Box::new(
            serde_json::from_value::<StateDelta>(json)
                .map_err(|e| format!("Failed to parse StateDelta: {}", e))?,
        )),
        "interrupt" => Ok(Box::new(
            serde_json::from_value::<Interrupt>(json)
                .map_err(|e| format!("Failed to parse Interrupt: {}", e))?,
        )),
        "interrupt_response" => Ok(Box::new(
            serde_json::from_value::<InterruptResponse>(json)
                .map_err(|e| format!("Failed to parse InterruptResponse: {}", e))?,
        )),
        "error" => Ok(Box::new(
            serde_json::from_value::<ErrorEvent>(json)
                .map_err(|e| format!("Failed to parse ErrorEvent: {}", e))?,
        )),
        "attachment" => Ok(Box::new(
            serde_json::from_value::<Attachment>(json)
                .map_err(|e| format!("Failed to parse Attachment: {}", e))?,
        )),
        "metadata" => Ok(Box::new(
            serde_json::from_value::<MetadataEvent>(json)
                .map_err(|e| format!("Failed to parse MetadataEvent: {}", e))?,
        )),
        "heartbeat" => Ok(Box::new(
            serde_json::from_value::<HeartbeatEvent>(json)
                .map_err(|e| format!("Failed to parse HeartbeatEvent: {}", e))?,
        )),
        _ => Err(format!("Unknown event type: {}", event_type_str)),
    }
}
