/**
 * @file test_object_pool.cpp
 * @brief Tests for ObjectPool template class
 */

#include <gtest/gtest.h>
#include "agenkit/infrastructure/memory/object_pool.hpp"
#include <thread>
#include <vector>
#include <chrono>

using namespace agenkit::infrastructure::memory;

// Simple test class for pooling
struct TestObject {
    int value;
    std::string name;

    TestObject() : value(0), name("") {}
    TestObject(int v, std::string n) : value(v), name(std::move(n)) {}
};

TEST(ObjectPoolTest, AcquireAndRelease) {
    ObjectPool<TestObject> pool;

    // Acquire object
    auto* obj = pool.acquire(42, "test");
    ASSERT_NE(obj, nullptr);
    EXPECT_EQ(obj->value, 42);
    EXPECT_EQ(obj->name, "test");

    // Release object
    pool.release(obj);

    // Pool should have 1 available object now
    EXPECT_GE(pool.available(), 1);
}

TEST(ObjectPoolTest, ReuseObjects) {
    ObjectPool<TestObject> pool;

    // Acquire and release object
    auto* obj1 = pool.acquire(1, "first");
    void* addr1 = obj1;
    pool.release(obj1);

    // Acquire again - should reuse same memory
    auto* obj2 = pool.acquire(2, "second");
    void* addr2 = obj2;

    EXPECT_EQ(addr1, addr2);  // Same memory location
    EXPECT_EQ(obj2->value, 2);
    EXPECT_EQ(obj2->name, "second");

    pool.release(obj2);
}

TEST(ObjectPoolTest, MultipleObjects) {
    ObjectPool<TestObject> pool;

    // Acquire multiple objects
    std::vector<TestObject*> objects;
    for (int i = 0; i < 10; i++) {
        objects.push_back(pool.acquire(i, "obj" + std::to_string(i)));
    }

    // Check all objects
    for (int i = 0; i < 10; i++) {
        EXPECT_EQ(objects[i]->value, i);
        EXPECT_EQ(objects[i]->name, "obj" + std::to_string(i));
    }

    // Release all objects
    for (auto* obj : objects) {
        pool.release(obj);
    }

    // Pool should have all objects available
    EXPECT_GE(pool.available(), 10);
}

TEST(ObjectPoolTest, BlockAllocation) {
    ObjectPool<TestObject, 4> pool;  // Small block size for testing

    EXPECT_EQ(pool.capacity(), 0);  // No blocks allocated yet
    EXPECT_EQ(pool.available(), 0);

    // Acquire first object - should allocate first block
    auto* obj1 = pool.acquire(1, "one");
    EXPECT_EQ(pool.capacity(), 4);  // One block of 4
    EXPECT_EQ(pool.available(), 3);  // 3 remaining

    // Acquire 3 more - should use same block
    auto* obj2 = pool.acquire(2, "two");
    auto* obj3 = pool.acquire(3, "three");
    auto* obj4 = pool.acquire(4, "four");
    EXPECT_EQ(pool.capacity(), 4);
    EXPECT_EQ(pool.available(), 0);

    // Acquire one more - should allocate second block
    auto* obj5 = pool.acquire(5, "five");
    EXPECT_EQ(pool.capacity(), 8);  // Two blocks
    EXPECT_EQ(pool.available(), 3);

    // Release all
    pool.release(obj1);
    pool.release(obj2);
    pool.release(obj3);
    pool.release(obj4);
    pool.release(obj5);

    // All 5 objects should be available, plus 3 remaining from second block
    EXPECT_EQ(pool.available(), 8);
}

TEST(ObjectPoolTest, ReleaseNull) {
    ObjectPool<TestObject> pool;

    // Should not crash
    pool.release(nullptr);

    EXPECT_EQ(pool.available(), 0);
}

TEST(ObjectPoolTest, ThreadSafety) {
    ObjectPool<TestObject> pool;

    const int num_threads = 10;
    const int objects_per_thread = 100;

    std::vector<std::thread> threads;

    // Launch threads that acquire and release objects
    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&pool, t, objects_per_thread]() {
            std::vector<TestObject*> local_objects;

            // Acquire objects
            for (int i = 0; i < objects_per_thread; i++) {
                local_objects.push_back(pool.acquire(t * 1000 + i, "thread" + std::to_string(t)));
            }

            // Small delay to increase contention
            std::this_thread::sleep_for(std::chrono::microseconds(10));

            // Release objects
            for (auto* obj : local_objects) {
                pool.release(obj);
            }
        });
    }

    // Wait for all threads
    for (auto& thread : threads) {
        thread.join();
    }

    // All objects should be back in pool
    EXPECT_GE(pool.available(), num_threads * objects_per_thread);
}

TEST(PooledObjectTest, RAIIRelease) {
    ObjectPool<TestObject, 4> pool;  // Small block size for predictable test

    EXPECT_EQ(pool.available(), 0);

    {
        auto obj = make_pooled(pool, 42, "test");
        EXPECT_EQ(obj->value, 42);
        EXPECT_EQ(obj->name, "test");
        EXPECT_EQ(pool.available(), 3);  // 3 remaining from first block

        // Object is automatically released when it goes out of scope
    }

    // Pool should have object available again (all 4 from block)
    EXPECT_EQ(pool.available(), 4);
}

TEST(PooledObjectTest, MoveSemantics) {
    ObjectPool<TestObject> pool;

    auto obj1 = make_pooled(pool, 1, "first");
    auto* ptr = obj1.get();

    // Move to new object
    auto obj2 = std::move(obj1);

    EXPECT_EQ(obj2.get(), ptr);
    EXPECT_EQ(obj1.get(), nullptr);  // Moved from
    EXPECT_EQ(obj2->value, 1);

    // Only released once when obj2 goes out of scope
}

TEST(PooledObjectTest, BoolConversion) {
    ObjectPool<TestObject> pool;

    auto obj1 = make_pooled(pool, 1, "test");
    EXPECT_TRUE(obj1);

    auto obj2 = std::move(obj1);
    EXPECT_FALSE(obj1);  // Moved from
    EXPECT_TRUE(obj2);
}

// Performance comparison test (informational)
TEST(ObjectPoolTest, PerformanceComparison) {
    const int iterations = 10000;

    // Benchmark standard allocation
    auto start_malloc = std::chrono::steady_clock::now();
    for (int i = 0; i < iterations; i++) {
        auto* obj = new TestObject(i, "test");
        delete obj;
    }
    auto end_malloc = std::chrono::steady_clock::now();
    auto duration_malloc = std::chrono::duration_cast<std::chrono::microseconds>(
        end_malloc - start_malloc
    ).count();

    // Benchmark pool allocation
    ObjectPool<TestObject> pool;
    auto start_pool = std::chrono::steady_clock::now();
    for (int i = 0; i < iterations; i++) {
        auto* obj = pool.acquire(i, "test");
        pool.release(obj);
    }
    auto end_pool = std::chrono::steady_clock::now();
    auto duration_pool = std::chrono::duration_cast<std::chrono::microseconds>(
        end_pool - start_pool
    ).count();

    // Print results (for manual inspection)
    std::cout << "Malloc: " << duration_malloc << " μs\n";
    std::cout << "Pool:   " << duration_pool << " μs\n";
    std::cout << "Speedup: " << (static_cast<double>(duration_malloc) / duration_pool) << "x\n";

    // Pool should be faster (but this is not guaranteed on all systems)
    // Just verify it completes successfully
    EXPECT_GT(duration_malloc, 0);
    EXPECT_GT(duration_pool, 0);
}
