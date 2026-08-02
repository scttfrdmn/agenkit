//! Transport layers for remote agent communication.
//!
//! This module provides HTTP, gRPC, and WebSocket transports for
//! communicating with agents over the network.
mod http;

#[cfg(feature = "native")]
mod grpc;

#[cfg(feature = "native")]
mod websocket;

pub use http::{HttpAgent, HttpServer, HttpTransportConfig};

#[cfg(feature = "native")]
pub use grpc::{GrpcAgent, GrpcConfig};

#[cfg(feature = "native")]
pub use websocket::{WebSocketAgent, WebSocketConfig};
