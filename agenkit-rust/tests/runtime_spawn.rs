//! Tests for `runtime::spawn`'s spawning contract (#778).
//!
//! `runtime::spawn` used to be implemented as
//!
//! ```ignore
//! Box::pin(async move { tokio::spawn(future).await.unwrap() })
//! ```
//!
//! with the `tokio::spawn` *inside* the returned future. Nothing was submitted to
//! the runtime until the caller awaited the handle, and because `JoinHandle` is a
//! bare `Pin<Box<dyn Future>>` with no `Drop`, discarding the handle discarded the
//! work — the exact opposite of the fire-and-forget contract the name implies.
//!
//! That silently broke the one call site in the crate
//! (`patterns::autonomous`'s manual-stop test), which passed anyway for unrelated
//! reasons. These tests exist so the laziness cannot come back unnoticed.

#![cfg(feature = "native")]

use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;

/// The load-bearing test: a spawned task must run even if the handle is dropped.
///
/// This is what fails against the old lazy implementation, with
/// "the spawned task never ran".
#[tokio::test]
async fn spawn_runs_task_when_handle_is_dropped() {
    let ran = Arc::new(AtomicBool::new(false));
    let flag = ran.clone();

    drop(agenkit::runtime::spawn(async move {
        flag.store(true, Ordering::SeqCst);
    }));

    // Give the runtime a chance to poll the task. Generous, because this asserts a
    // *positive* (the task ran) and a slow scheduler must not read as a failure.
    for _ in 0..100 {
        if ran.load(Ordering::SeqCst) {
            break;
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }

    assert!(
        ran.load(Ordering::SeqCst),
        "the spawned task never ran: runtime::spawn returned a lazy future rather \
         than submitting the task to the runtime"
    );
}

/// A spawned task must make progress *concurrently* with the spawner, not only
/// when the spawner blocks on the handle.
///
/// Distinct from the test above: an implementation that eagerly spawned but whose
/// task could not be observed until awaited would pass that one and fail this.
#[tokio::test]
async fn spawn_makes_progress_without_awaiting_the_handle() {
    let counter = Arc::new(AtomicUsize::new(0));
    let ticker = counter.clone();

    let handle = agenkit::runtime::spawn(async move {
        for _ in 0..5 {
            ticker.fetch_add(1, Ordering::SeqCst);
            tokio::time::sleep(Duration::from_millis(5)).await;
        }
    });

    // Wait on the *side effect*, never on the handle.
    for _ in 0..100 {
        if counter.load(Ordering::SeqCst) >= 5 {
            break;
        }
        tokio::time::sleep(Duration::from_millis(10)).await;
    }

    assert_eq!(
        counter.load(Ordering::SeqCst),
        5,
        "spawned task did not run to completion without the handle being awaited"
    );

    // And the handle must still be awaitable after the task has already finished.
    handle.await;
}

/// The handle must still yield the task's output, so the fix does not trade the
/// spawning contract away for it.
#[tokio::test]
async fn spawn_handle_yields_the_output() {
    let handle = agenkit::runtime::spawn(async { 6 * 7 });
    assert_eq!(handle.await, 42);
}

/// Two tasks spawned before either is awaited must both be resident on the
/// runtime, i.e. they interleave rather than running one-after-another at await
/// time. Against the lazy implementation `first` would not even start until its
/// handle was awaited, so the ordering below could not hold.
#[tokio::test]
async fn spawned_tasks_run_concurrently_with_each_other() {
    let order = Arc::new(std::sync::Mutex::new(Vec::new()));

    let slow_order = order.clone();
    let slow = agenkit::runtime::spawn(async move {
        tokio::time::sleep(Duration::from_millis(60)).await;
        slow_order.lock().unwrap().push("slow");
    });

    let fast_order = order.clone();
    let fast = agenkit::runtime::spawn(async move {
        tokio::time::sleep(Duration::from_millis(10)).await;
        fast_order.lock().unwrap().push("fast");
    });

    // Await the *slow* one first. If both are really on the runtime, "fast" has
    // already recorded itself by the time "slow" finishes.
    slow.await;
    fast.await;

    assert_eq!(
        *order.lock().unwrap(),
        vec!["fast", "slow"],
        "spawned tasks did not overlap; they appear to run only when awaited"
    );
}
