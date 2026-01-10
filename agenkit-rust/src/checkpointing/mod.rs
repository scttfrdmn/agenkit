//! Checkpointing for durable execution and state persistence.
//!
//! This module provides checkpointing capabilities for agents, enabling:
//! - State persistence across restarts
//! - Crash recovery with automatic rollback
//! - Time-travel debugging via history traversal
//! - Multi-session support
//! - Durable execution for long-running agents
//!
//! # Architecture
//!
//! - **Checkpoint**: Core data structure with state, messages, and metadata
//! - **CheckpointStorage**: Abstract storage interface with implementations:
//!   - InMemoryCheckpointStorage: Fast, ephemeral storage for testing
//!   - FileCheckpointStorage: Persistent file-based storage
//! - **CheckpointManager**: High-level API for checkpoint lifecycle
//! - **DurableAgent**: Agent wrapper with automatic checkpointing
//!
//! # Example
//!
//! ```rust
//! use agenkit::checkpointing::{CheckpointManager, FileCheckpointStorage};
//! use std::path::PathBuf;
//!
//! # async fn example() -> Result<(), Box<dyn std::error::Error>> {
//! // Create checkpoint manager with file storage
//! let storage = FileCheckpointStorage::new(PathBuf::from("./checkpoints"))?;
//! let mut manager = CheckpointManager::new(Box::new(storage));
//!
//! // Create checkpoint
//! let checkpoint_id = manager.create_checkpoint(
//!     "session-1".to_string(),
//!     "my-agent".to_string(),
//!     1,
//!     serde_json::json!({"counter": 42}),
//!     vec![],
//!     None,
//!     None,
//! ).await?;
//!
//! // Load checkpoint later
//! let checkpoint = manager.load_checkpoint(&checkpoint_id).await?;
//! # Ok(())
//! # }
//! ```

pub mod checkpoint;
pub mod storage;
pub mod manager;
pub mod durable_agent;

pub use checkpoint::Checkpoint;
pub use storage::{CheckpointStorage, FileCheckpointStorage, InMemoryCheckpointStorage};
pub use manager::CheckpointManager;
pub use durable_agent::{DurableAgent, DurableAgentConfig};
