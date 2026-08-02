//! Runtime abstraction layer for native (tokio) and WASM (wasm-bindgen-futures).
//!
//! This module provides a unified async runtime interface that works on both
//! native platforms (using tokio) and in the browser (using wasm-bindgen-futures).
//!
//! # Usage
//!
//! ```
//! use agenkit::runtime;
//!
//! async fn my_function() {
//!     // Sleep for 1 second (works on both native and WASM)
//!     runtime::sleep(std::time::Duration::from_secs(1)).await;
//!
//!     // Spawn a task. It starts running immediately; awaiting the handle waits
//!     // for the result, and dropping the handle leaves the task running.
//!     let handle = runtime::spawn(async { 6 * 7 });
//!     assert_eq!(handle.await, 42);
//! }
//! ```
//!
//! # Platform differences
//!
//! `spawn` is not perfectly symmetric across the two arms, and callers writing
//! cross-platform code need to know it:
//!
//! | | native | WASM |
//! |---|---|---|
//! | returns | [`JoinHandle<T>`] | `()` |
//! | task output | any `Send` type | must be `()` |
//! | `Send` bound | required | not required (single-threaded) |
//!
//! So `spawn(async { 42 })` compiles on native and not on WASM, and code that
//! awaits the handle has no WASM equivalent. Only `spawn(async { ... })` returning
//! `()`, with the handle discarded, means the same thing on both.
use std::future::Future;
use std::pin::Pin;
use std::time::Duration;

/// Task handle returned by spawn()
pub type JoinHandle<T> = Pin<Box<dyn Future<Output = T> + Send>>;

// ============================================================================
// Native (tokio) implementation
// ============================================================================

/// Spawn a task onto the runtime.
///
/// The task is submitted **immediately**, before this function returns. Dropping
/// the returned handle does not cancel it — like `tokio::spawn`, and unlike a bare
/// future, spawning is fire-and-forget.
///
/// # Panics
///
/// Awaiting the returned handle panics if the task panicked, propagating it to the
/// awaiting task. A task that panics while its handle has been dropped is
/// unobserved, again matching `tokio::spawn`.
///
/// # Examples
///
/// The handle yields the task's output:
///
/// ```
/// # #[tokio::main] async fn main() {
/// let handle = agenkit::runtime::spawn(async { 6 * 7 });
/// assert_eq!(handle.await, 42);
/// # }
/// ```
///
/// The task runs even if the handle is discarded:
///
/// ```
/// use std::sync::atomic::{AtomicBool, Ordering};
/// use std::sync::Arc;
///
/// # #[tokio::main] async fn main() {
/// let ran = Arc::new(AtomicBool::new(false));
/// let flag = ran.clone();
/// drop(agenkit::runtime::spawn(async move { flag.store(true, Ordering::SeqCst) }));
///
/// agenkit::runtime::sleep(std::time::Duration::from_millis(50)).await;
/// assert!(ran.load(Ordering::SeqCst));
/// # }
/// ```
#[cfg(feature = "native")]
pub fn spawn<F>(future: F) -> JoinHandle<F::Output>
where
    F: Future + Send + 'static,
    F::Output: Send + 'static,
{
    // `tokio::spawn` is called here, *outside* the returned future, so the task is
    // on the runtime before this function returns. It used to sit inside the async
    // block, which meant nothing was submitted until the caller awaited the handle
    // -- and since `JoinHandle` is a bare boxed future with no `Drop`, discarding
    // the handle silently discarded the work (#778). `tests/runtime_spawn.rs` pins
    // this; three of those tests fail if the call moves back inside.
    let task = tokio::spawn(future);
    Box::pin(async move {
        task.await
            .expect("spawned task panicked or was cancelled")
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
        })
        .await;

        assert!(result.is_err());
    }
}
