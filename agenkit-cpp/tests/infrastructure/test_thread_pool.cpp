/**
 * @file test_thread_pool.cpp
 * @brief Tests for ThreadPool
 */

#include <gtest/gtest.h>
#include "agenkit/infrastructure/thread_pool.hpp"
#include <chrono>
#include <atomic>
#include <vector>

using namespace agenkit::infrastructure;

TEST(ThreadPoolTest, Construction) {
    // Default constructor (uses hardware_concurrency)
    ThreadPool pool1;
    EXPECT_GT(pool1.size(), 0);
    EXPECT_EQ(pool1.size(), std::thread::hardware_concurrency());

    // Custom size
    ThreadPool pool2(4);
    EXPECT_EQ(pool2.size(), 4);
}

TEST(ThreadPoolTest, ConstructionZeroThreads) {
    // Should throw for zero threads
    EXPECT_THROW(ThreadPool(0), std::invalid_argument);
}

TEST(ThreadPoolTest, SimpleTask) {
    ThreadPool pool(2);

    auto future = pool.enqueue([]() { return 42; });
    int result = future.get();

    EXPECT_EQ(result, 42);
}

TEST(ThreadPoolTest, TaskWithArguments) {
    ThreadPool pool(2);

    auto future = pool.enqueue([](int a, int b) { return a + b; }, 10, 32);
    int result = future.get();

    EXPECT_EQ(result, 42);
}

TEST(ThreadPoolTest, MultipleTasks) {
    ThreadPool pool(4);

    std::vector<std::future<int>> futures;

    // Enqueue 10 tasks
    for (int i = 0; i < 10; i++) {
        futures.push_back(pool.enqueue([](int x) { return x * 2; }, i));
    }

    // Check results
    for (int i = 0; i < 10; i++) {
        EXPECT_EQ(futures[i].get(), i * 2);
    }
}

TEST(ThreadPoolTest, VoidTask) {
    ThreadPool pool(2);

    std::atomic<int> counter{0};

    auto future = pool.enqueue([&counter]() { counter++; });
    future.get();  // Wait for completion

    EXPECT_EQ(counter.load(), 1);
}

TEST(ThreadPoolTest, ConcurrentExecution) {
    ThreadPool pool(4);

    std::atomic<int> counter{0};
    std::vector<std::future<void>> futures;

    // Submit 100 tasks that increment counter
    for (int i = 0; i < 100; i++) {
        futures.push_back(pool.enqueue([&counter]() {
            counter++;
        }));
    }

    // Wait for all tasks
    for (auto& future : futures) {
        future.get();
    }

    EXPECT_EQ(counter.load(), 100);
}

TEST(ThreadPoolTest, TaskOrdering) {
    ThreadPool pool(1);  // Single thread to guarantee ordering

    std::vector<int> results;
    std::mutex results_mutex;
    std::vector<std::future<void>> futures;

    // Submit tasks in order
    for (int i = 0; i < 10; i++) {
        futures.push_back(pool.enqueue([i, &results, &results_mutex]() {
            std::lock_guard<std::mutex> lock(results_mutex);
            results.push_back(i);
        }));
    }

    // Wait for completion
    for (auto& future : futures) {
        future.get();
    }

    // Verify order (single thread should execute in FIFO order)
    EXPECT_EQ(results.size(), 10);
    for (int i = 0; i < 10; i++) {
        EXPECT_EQ(results[i], i);
    }
}

TEST(ThreadPoolTest, ExceptionHandling) {
    ThreadPool pool(2);

    auto future = pool.enqueue([]() -> int {
        throw std::runtime_error("Test exception");
        return 0;
    });

    // Should propagate exception through future
    EXPECT_THROW(future.get(), std::runtime_error);
}

TEST(ThreadPoolTest, LongRunningTask) {
    ThreadPool pool(2);

    auto start = std::chrono::steady_clock::now();

    auto future = pool.enqueue([]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 42;
    });

    int result = future.get();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start
    ).count();

    EXPECT_EQ(result, 42);
    EXPECT_GE(elapsed, 100);
}

TEST(ThreadPoolTest, ParallelExecution) {
    ThreadPool pool(4);

    // Submit 4 tasks that each sleep for 100ms
    // With 4 threads, should complete in ~100ms (parallel)
    // With 1 thread, would take ~400ms (sequential)

    auto start = std::chrono::steady_clock::now();

    std::vector<std::future<int>> futures;
    for (int i = 0; i < 4; i++) {
        futures.push_back(pool.enqueue([]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            return 1;
        }));
    }

    // Wait for all
    int sum = 0;
    for (auto& future : futures) {
        sum += future.get();
    }

    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::steady_clock::now() - start
    ).count();

    EXPECT_EQ(sum, 4);
    // Should complete in roughly parallel time (allow 50ms overhead)
    EXPECT_LT(elapsed, 200);  // Much less than 400ms sequential
}

TEST(ThreadPoolTest, IsStopped) {
    auto pool = std::make_unique<ThreadPool>(2);

    EXPECT_FALSE(pool->is_stopped());

    // Destroy pool
    pool.reset();

    // Can't check after destruction, but verified no crashes
}

TEST(ThreadPoolTest, PendingTasks) {
    ThreadPool pool(1);  // Single thread to control execution

    // Submit a long-running task to block the thread
    auto blocker = pool.enqueue([]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    });

    // Submit more tasks while first is running
    std::vector<std::future<int>> futures;
    for (int i = 0; i < 5; i++) {
        futures.push_back(pool.enqueue([i]() { return i; }));
    }

    // Should have some pending tasks
    size_t pending = pool.pending_tasks();
    EXPECT_GT(pending, 0);

    // Wait for all to complete
    blocker.get();
    for (auto& future : futures) {
        future.get();
    }
}

TEST(ThreadPoolTest, DestructorWaitsForTasks) {
    std::atomic<int> completed{0};

    {
        ThreadPool pool(2);

        // Submit tasks
        for (int i = 0; i < 10; i++) {
            pool.enqueue([&completed]() {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                completed++;
            });
        }

        // Pool destructor will wait for all tasks
    }

    // All tasks should have completed
    EXPECT_EQ(completed.load(), 10);
}

TEST(ThreadPoolTest, StressTest) {
    ThreadPool pool(std::thread::hardware_concurrency());

    std::atomic<int> counter{0};
    std::vector<std::future<void>> futures;

    // Submit 1000 tasks
    for (int i = 0; i < 1000; i++) {
        futures.push_back(pool.enqueue([&counter]() {
            counter++;
        }));
    }

    // Wait for all
    for (auto& future : futures) {
        future.get();
    }

    EXPECT_EQ(counter.load(), 1000);
}

// Performance comparison test (informational)
TEST(ThreadPoolTest, PerformanceVsAsync) {
    const int num_tasks = 100;

    // Benchmark ThreadPool
    auto start_pool = std::chrono::steady_clock::now();
    {
        ThreadPool pool(4);
        std::vector<std::future<int>> futures;

        for (int i = 0; i < num_tasks; i++) {
            futures.push_back(pool.enqueue([i]() { return i * 2; }));
        }

        for (auto& future : futures) {
            future.get();
        }
    }
    auto end_pool = std::chrono::steady_clock::now();
    auto duration_pool = std::chrono::duration_cast<std::chrono::microseconds>(
        end_pool - start_pool
    ).count();

    // Benchmark std::async
    auto start_async = std::chrono::steady_clock::now();
    {
        std::vector<std::future<int>> futures;

        for (int i = 0; i < num_tasks; i++) {
            futures.push_back(std::async(std::launch::async, [i]() { return i * 2; }));
        }

        for (auto& future : futures) {
            future.get();
        }
    }
    auto end_async = std::chrono::steady_clock::now();
    auto duration_async = std::chrono::duration_cast<std::chrono::microseconds>(
        end_async - start_async
    ).count();

    std::cout << "ThreadPool: " << duration_pool << " μs\n";
    std::cout << "std::async: " << duration_async << " μs\n";
    if (duration_async > 0) {
        std::cout << "Speedup:    " << (static_cast<double>(duration_async) / duration_pool) << "x\n";
    }

    // ThreadPool should be faster or comparable
    // (Not enforcing this as a hard requirement since it's system-dependent)
    EXPECT_GT(duration_pool, 0);
    EXPECT_GT(duration_async, 0);
}
