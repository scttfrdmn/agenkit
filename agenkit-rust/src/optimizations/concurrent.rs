//! Concurrent processing utilities
//!
//! Provides lock-free data structures and parallel processing helpers
//! using crossbeam and rayon for high-performance concurrent operations.

use crossbeam::channel::{bounded, unbounded, Receiver, Sender};
use crossbeam::queue::SegQueue;
use rayon::prelude::*;
use std::sync::Arc;

/// Lock-free concurrent queue for message passing
///
/// Uses crossbeam's SegQueue for lock-free multi-producer, multi-consumer
/// operations. Ideal for work distribution across threads.
///
/// # Example
/// ```
/// use agenkit::optimizations::concurrent::ConcurrentQueue;
///
/// let queue = ConcurrentQueue::new();
/// queue.push(42);
/// assert_eq!(queue.pop(), Some(42));
/// ```
pub struct ConcurrentQueue<T> {
    queue: Arc<SegQueue<T>>,
}

impl<T> ConcurrentQueue<T> {
    /// Create a new concurrent queue
    pub fn new() -> Self {
        Self {
            queue: Arc::new(SegQueue::new()),
        }
    }

    /// Push an item onto the queue
    pub fn push(&self, item: T) {
        self.queue.push(item);
    }

    /// Pop an item from the queue
    pub fn pop(&self) -> Option<T> {
        self.queue.pop()
    }

    /// Check if the queue is empty
    pub fn is_empty(&self) -> bool {
        self.queue.is_empty()
    }

    /// Get the approximate length (may be inaccurate under high concurrency)
    pub fn len(&self) -> usize {
        self.queue.len()
    }
}

impl<T> Clone for ConcurrentQueue<T> {
    fn clone(&self) -> Self {
        Self {
            queue: Arc::clone(&self.queue),
        }
    }
}

impl<T> Default for ConcurrentQueue<T> {
    fn default() -> Self {
        Self::new()
    }
}

/// Bounded channel for backpressure-aware message passing
///
/// Wrapper around crossbeam's bounded channel for controlled
/// concurrency with backpressure.
///
/// # Example
/// ```
/// use agenkit::optimizations::concurrent::BoundedChannel;
///
/// let (tx, rx) = BoundedChannel::new(10);
/// tx.send(42).unwrap();
/// assert_eq!(rx.recv().unwrap(), 42);
/// ```
pub struct BoundedChannel<T> {
    _phantom: std::marker::PhantomData<T>,
}

impl<T> BoundedChannel<T> {
    /// Create a new bounded channel with specified capacity
    pub fn new(capacity: usize) -> (Sender<T>, Receiver<T>) {
        bounded(capacity)
    }

    /// Create an unbounded channel (no backpressure)
    pub fn unbounded() -> (Sender<T>, Receiver<T>) {
        unbounded()
    }
}

/// Parallel processing utilities using rayon
pub mod parallel {
    use super::*;

    /// Execute a function in parallel over a collection
    ///
    /// Uses rayon's work-stealing thread pool for efficient parallel execution.
    ///
    /// # Example
    /// ```
    /// use agenkit::optimizations::concurrent::parallel;
    ///
    /// let items = vec![1, 2, 3, 4, 5];
    /// let results = parallel::map(items, |x| x * 2);
    /// assert_eq!(results, vec![2, 4, 6, 8, 10]);
    /// ```
    pub fn map<T, U, F>(items: Vec<T>, f: F) -> Vec<U>
    where
        T: Send + Sync,
        U: Send,
        F: Fn(T) -> U + Send + Sync,
    {
        items.into_par_iter().map(f).collect()
    }

    /// Execute a function in parallel over a slice
    pub fn map_slice<T, U, F>(items: &[T], f: F) -> Vec<U>
    where
        T: Sync,
        U: Send,
        F: Fn(&T) -> U + Send + Sync,
    {
        items.par_iter().map(f).collect()
    }

    /// Filter and map in parallel
    pub fn filter_map<T, U, F>(items: Vec<T>, f: F) -> Vec<U>
    where
        T: Send + Sync,
        U: Send,
        F: Fn(T) -> Option<U> + Send + Sync,
    {
        items.into_par_iter().filter_map(f).collect()
    }

    /// Parallel reduce operation
    pub fn reduce<T, F>(items: Vec<T>, identity: T, f: F) -> T
    where
        T: Send + Sync + Clone,
        F: Fn(T, T) -> T + Send + Sync,
    {
        items.into_par_iter().reduce(|| identity.clone(), f)
    }

    /// Parallel fold with combine
    pub fn fold<T, U, F, R>(items: Vec<T>, identity: U, fold_fn: F, reduce_fn: R) -> U
    where
        T: Send + Sync,
        U: Send + Sync + Clone,
        F: Fn(U, T) -> U + Send + Sync,
        R: Fn(U, U) -> U + Send + Sync,
    {
        items
            .into_par_iter()
            .fold(|| identity.clone(), fold_fn)
            .reduce(|| identity.clone(), reduce_fn)
    }

    /// Check if any element satisfies predicate (short-circuits)
    pub fn any<T, F>(items: &[T], predicate: F) -> bool
    where
        T: Sync,
        F: Fn(&T) -> bool + Send + Sync,
    {
        items.par_iter().any(predicate)
    }

    /// Check if all elements satisfy predicate (short-circuits)
    pub fn all<T, F>(items: &[T], predicate: F) -> bool
    where
        T: Sync,
        F: Fn(&T) -> bool + Send + Sync,
    {
        items.par_iter().all(predicate)
    }

    /// Find first element matching predicate
    pub fn find<T, F>(items: &[T], predicate: F) -> Option<&T>
    where
        T: Sync,
        F: Fn(&&T) -> bool + Send + Sync,
    {
        items.par_iter().find_any(predicate)
    }

    /// Partition into two collections based on predicate
    pub fn partition<T, F>(items: Vec<T>, predicate: F) -> (Vec<T>, Vec<T>)
    where
        T: Send,
        F: Fn(&T) -> bool + Send + Sync,
    {
        items.into_par_iter().partition(predicate)
    }
}

/// Work-stealing executor for async tasks
///
/// Provides a high-performance work-stealing scheduler for concurrent
/// task execution.
pub struct WorkStealingExecutor {
    thread_count: usize,
}

impl WorkStealingExecutor {
    /// Create a new work-stealing executor with specified thread count
    pub fn new(thread_count: usize) -> Self {
        Self { thread_count }
    }

    /// Create an executor using all available CPU cores
    pub fn with_max_parallelism() -> Self {
        Self {
            thread_count: rayon::current_num_threads(),
        }
    }

    /// Execute tasks in parallel using work-stealing
    pub fn execute<T, F>(&self, tasks: Vec<F>) -> Vec<T>
    where
        T: Send,
        F: Fn() -> T + Send + Sync,
    {
        tasks.into_par_iter().map(|task| task()).collect()
    }

    /// Get the number of threads
    pub fn thread_count(&self) -> usize {
        self.thread_count
    }
}

impl Default for WorkStealingExecutor {
    fn default() -> Self {
        Self::with_max_parallelism()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[test]
    fn test_concurrent_queue_basic() {
        let queue = ConcurrentQueue::new();
        queue.push(1);
        queue.push(2);
        queue.push(3);

        assert_eq!(queue.pop(), Some(1));
        assert_eq!(queue.pop(), Some(2));
        assert_eq!(queue.pop(), Some(3));
        assert_eq!(queue.pop(), None);
    }

    #[test]
    fn test_concurrent_queue_multi_thread() {
        let queue = ConcurrentQueue::new();
        let queue_clone = queue.clone();

        let producer = thread::spawn(move || {
            for i in 0..100 {
                queue_clone.push(i);
            }
        });

        let consumer = thread::spawn(move || {
            let mut count = 0;
            loop {
                if queue.pop().is_some() {
                    count += 1;
                    if count == 100 {
                        break;
                    }
                }
                thread::sleep(Duration::from_micros(1));
            }
            count
        });

        producer.join().unwrap();
        let count = consumer.join().unwrap();
        assert_eq!(count, 100);
    }

    #[test]
    fn test_bounded_channel() {
        let (tx, rx) = BoundedChannel::new(5);

        tx.send(1).unwrap();
        tx.send(2).unwrap();
        tx.send(3).unwrap();

        assert_eq!(rx.recv().unwrap(), 1);
        assert_eq!(rx.recv().unwrap(), 2);
        assert_eq!(rx.recv().unwrap(), 3);
    }

    #[test]
    fn test_parallel_map() {
        let items = vec![1, 2, 3, 4, 5];
        let results = parallel::map(items, |x| x * 2);
        assert_eq!(results, vec![2, 4, 6, 8, 10]);
    }

    #[test]
    fn test_parallel_filter_map() {
        let items = vec![1, 2, 3, 4, 5];
        let results = parallel::filter_map(items, |x| if x % 2 == 0 { Some(x * 2) } else { None });
        assert_eq!(results, vec![4, 8]);
    }

    #[test]
    fn test_parallel_reduce() {
        let items = vec![1, 2, 3, 4, 5];
        let sum = parallel::reduce(items, 0, |a, b| a + b);
        assert_eq!(sum, 15);
    }

    #[test]
    fn test_parallel_any() {
        let items = vec![1, 2, 3, 4, 5];
        assert!(parallel::any(&items, |&x| x > 3));
        assert!(!parallel::any(&items, |&x| x > 10));
    }

    #[test]
    fn test_parallel_all() {
        let items = vec![1, 2, 3, 4, 5];
        assert!(parallel::all(&items, |&x| x > 0));
        assert!(!parallel::all(&items, |&x| x > 3));
    }

    #[test]
    fn test_parallel_find() {
        let items = vec![1, 2, 3, 4, 5];
        let found = parallel::find(&items, |&&x| x == 3);
        assert_eq!(found, Some(&3));

        let not_found = parallel::find(&items, |&&x| x == 10);
        assert_eq!(not_found, None);
    }

    #[test]
    fn test_parallel_partition() {
        let items = vec![1, 2, 3, 4, 5, 6];
        let (evens, odds) = parallel::partition(items, |&x| x % 2 == 0);
        assert_eq!(evens, vec![2, 4, 6]);
        assert_eq!(odds, vec![1, 3, 5]);
    }

    #[test]
    fn test_work_stealing_executor() {
        let executor = WorkStealingExecutor::with_max_parallelism();
        assert!(executor.thread_count() > 0);

        let tasks: Vec<_> = (0..10).map(|i| move || i * 2).collect();
        let results = executor.execute(tasks);

        assert_eq!(results.len(), 10);
        for (i, &result) in results.iter().enumerate() {
            assert_eq!(result, i * 2);
        }
    }
}
