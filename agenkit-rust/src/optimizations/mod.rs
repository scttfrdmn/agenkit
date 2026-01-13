//! Performance optimizations for Agenkit
//!
//! This module provides various performance optimization utilities including:
//! - Caching (LRU and async memoization)
//! - Memory optimizations (string interning, allocation reduction)
//! - Optimized message construction
//! - Concurrency primitives (lock-free queues, parallel processing)

pub mod cache;

#[cfg(feature = "native")]
pub mod string_pool;

#[cfg(feature = "native")]
pub mod message_builder;

#[cfg(feature = "native")]
pub mod concurrent;

#[cfg(feature = "native")]
pub use cache::{CachedAgent, MemoizedAgent};

#[cfg(feature = "native")]
pub use string_pool::{intern, global_pool, roles, metadata_keys};

#[cfg(feature = "native")]
pub use message_builder::{MessageBuilder, MessageBatch, fast};

#[cfg(feature = "native")]
pub use concurrent::{ConcurrentQueue, BoundedChannel, WorkStealingExecutor, parallel};
