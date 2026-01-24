///! AG-UI (Agent-User Interaction) Protocol
///!
///! Provides streaming agent-to-frontend communication using the AG-UI protocol.
///!
///! Reference: https://docs.ag-ui.com

pub mod adapter;
pub mod events;
pub mod hitl;
pub mod transports;

// Re-export main types
pub use adapter::{AGUIAdapter, AGUIAdapterConfig};
pub use events::*;
pub use hitl::{AGUIHumanInLoopAdapter, AGUIHumanInLoopConfig};
