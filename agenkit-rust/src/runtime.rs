///! Runtime abstraction layer for native (tokio) and WASM (wasm-bindgen-futures).
///!
///! This module provides a unified async runtime interface that works on both
///! native platforms (using tokio) and in the browser (using wasm-bindgen-futures).
///!
///! # Usage
///!
///! ```
///! use agenkit::runtime;
///!
///! async fn my_function() {
///!     // Sleep for 1 second (works on both native and WASM)
///!     runtime::sleep(std::time::Duration::from_secs(1)).await;
///!
///!     // Spawn a task (works on both native and WASM)
///!     runtime::spawn(async {
///!         // ...
///!     });
///! }
///! ```

use std::future::Future;
use std::pin::Pin;
use std::time::Duration;

/// Task handle returned by spawn()
pub type JoinHandle<T> = Pin<Box<dyn Future<Output = T> + Send>>;

// ============================================================================
// Native (tokio) implementation
// ============================================================================

#[cfg(feature = "native")]
pub fn spawn<F>(future: F) -> JoinHandle<F::Output>
where
    F: Future + Send + 'static,
    F::Output: Send + 'static,
{
    Box::pin(async move {
        tokio::spawn(future).await.unwrap()
    })
}

#[cfg(feature = "native")]
pub async fn sleep(duration: Duration) {
    tokio::time::sleep(duration).await;
}

#[cfg(feature = "native")]
pub async fn timeout<F, T>(duration: Duration, future: F) -> Result<T, TimeoutError>
where
    F: Future<Output = T>,
{
    tokio::time::timeout(duration, future)
        .await
        .map_err(|_| TimeoutError)
}

#[cfg(feature = "native")]
pub async fn yield_now() {
    tokio::task::yield_now().await;
}

// ============================================================================
// WASM (wasm-bindgen-futures) implementation
// ============================================================================

#[cfg(feature = "wasm")]
pub fn spawn<F>(future: F)
where
    F: Future<Output = ()> + 'static,
{
    wasm_bindgen_futures::spawn_local(future);
}

#[cfg(feature = "wasm")]
pub fn spawn_local<F>(future: F)
where
    F: Future<Output = ()> + 'static,
{
    wasm_bindgen_futures::spawn_local(future);
}

#[cfg(feature = "wasm")]
pub async fn sleep(duration: Duration) {
    use wasm_bindgen::prelude::*;
    use wasm_bindgen::JsCast;
    use web_sys::window;

    let millis = duration.as_millis() as i32;

    let promise = js_sys::Promise::new(&mut |resolve, _reject| {
        let window = window().expect("no window");
        window
            .set_timeout_with_callback_and_timeout_and_arguments_0(&resolve, millis)
            .expect("set_timeout failed");
    });

    wasm_bindgen_futures::JsFuture::from(promise).await.ok();
}

#[cfg(feature = "wasm")]
pub async fn timeout<F, T>(duration: Duration, future: F) -> Result<T, TimeoutError>
where
    F: Future<Output = T>,
{
    use futures::future::{select, Either};
    use futures::pin_mut;

    let sleep_future = sleep(duration);
    pin_mut!(future);
    pin_mut!(sleep_future);

    match select(future, sleep_future).await {
        Either::Left((result, _)) => Ok(result),
        Either::Right(_) => Err(TimeoutError),
    }
}

#[cfg(feature = "wasm")]
pub async fn yield_now() {
    // In WASM, we can yield by sleeping for 0ms
    sleep(Duration::from_millis(0)).await;
}

// ============================================================================
// Common types
// ============================================================================

/// Error returned when a timeout occurs
#[derive(Debug, Clone, Copy)]
pub struct TimeoutError;

impl std::fmt::Display for TimeoutError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "operation timed out")
    }
}

impl std::error::Error for TimeoutError {}

// ============================================================================
// Synchronization primitives
// ============================================================================

#[cfg(feature = "native")]
pub use tokio::sync::Mutex;

#[cfg(feature = "wasm")]
pub use futures::lock::Mutex;

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(feature = "native")]
    #[tokio::test]
    async fn test_sleep() {
        use std::time::Instant;

        let start = Instant::now();
        sleep(Duration::from_millis(100)).await;
        let elapsed = start.elapsed();

        assert!(elapsed >= Duration::from_millis(100));
        assert!(elapsed < Duration::from_millis(200));
    }

    #[cfg(feature = "native")]
    #[tokio::test]
    async fn test_timeout_success() {
        let result = timeout(Duration::from_secs(1), async { 42 }).await;
        assert_eq!(result.unwrap(), 42);
    }

    #[cfg(feature = "native")]
    #[tokio::test]
    async fn test_timeout_failure() {
        let result = timeout(Duration::from_millis(10), async {
            sleep(Duration::from_secs(1)).await;
            42
        }).await;

        assert!(result.is_err());
    }
}
