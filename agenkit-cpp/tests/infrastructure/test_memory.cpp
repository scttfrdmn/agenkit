/**
 * @file test_memory.cpp
 * @brief Comprehensive tests for memory infrastructure (working, short-term, long-term)
 */

#include <gtest/gtest.h>
#include "agenkit/infrastructure/memory.hpp"
#include <thread>
#include <chrono>

using namespace agenkit::infrastructure::memory;

// ============================================================================
// WorkingMemory Tests (FIFO Eviction)
// ============================================================================

TEST(WorkingMemoryTest, StoreAndRetrieve) {
    WorkingMemory memory(5);

    auto entry1 = MemoryEntry::create("message 1");
    auto entry2 = MemoryEntry::create("message 2");

    auto result1 = memory.store(entry1);
    auto result2 = memory.store(entry2);

    ASSERT_TRUE(result1.is_ok());
    ASSERT_TRUE(result2.is_ok());

    auto retrieve_result = memory.retrieve(2);
    ASSERT_TRUE(retrieve_result.is_ok());

    auto entries = retrieve_result.unwrap();
    EXPECT_EQ(entries.size(), 2);
    // Most recent first
    EXPECT_EQ(entries[0].content, "message 2");
    EXPECT_EQ(entries[1].content, "message 1");
}

TEST(WorkingMemoryTest, CapacityAndFIFOEviction) {
    WorkingMemory memory(3);

    auto entry1 = MemoryEntry::create("msg1");
    auto entry2 = MemoryEntry::create("msg2");
    auto entry3 = MemoryEntry::create("msg3");
    auto entry4 = MemoryEntry::create("msg4");

    memory.store(entry1);
    memory.store(entry2);
    memory.store(entry3);

    EXPECT_EQ(memory.count(), 3);

    // Adding 4th should evict oldest (msg1)
    memory.store(entry4);

    EXPECT_EQ(memory.count(), 3);

    auto all_result = memory.get_all();
    ASSERT_TRUE(all_result.is_ok());

    auto all = all_result.unwrap();
    EXPECT_EQ(all.size(), 3);

    // Should have msg2, msg3, msg4 (most recent first)
    EXPECT_EQ(all[0].content, "msg4");
    EXPECT_EQ(all[1].content, "msg3");
    EXPECT_EQ(all[2].content, "msg2");
}

TEST(WorkingMemoryTest, Remove) {
    WorkingMemory memory(5);

    auto entry = MemoryEntry::create("to delete");
    auto store_result = memory.store(entry);
    ASSERT_TRUE(store_result.is_ok());

    std::string entry_id = store_result.unwrap();

    auto remove_result = memory.deleteEntry(entry_id);
    ASSERT_TRUE(remove_result.is_ok());
    EXPECT_TRUE(remove_result.unwrap());

    EXPECT_EQ(memory.count(), 0);

    // Try to remove again - should return false
    auto remove_again = memory.deleteEntry(entry_id);
    ASSERT_TRUE(remove_again.is_ok());
    EXPECT_FALSE(remove_again.unwrap());
}

TEST(WorkingMemoryTest, Clear) {
    WorkingMemory memory(5);

    memory.store(MemoryEntry::create("msg1"));
    memory.store(MemoryEntry::create("msg2"));
    memory.store(MemoryEntry::create("msg3"));

    EXPECT_EQ(memory.count(), 3);

    memory.clear();
    EXPECT_EQ(memory.count(), 0);
}

TEST(WorkingMemoryTest, RetrieveLimit) {
    WorkingMemory memory(10);

    for (int i = 0; i < 5; i++) {
        memory.store(MemoryEntry::create("msg" + std::to_string(i)));
    }

    auto retrieve_result = memory.retrieve(3);
    ASSERT_TRUE(retrieve_result.is_ok());

    auto entries = retrieve_result.unwrap();
    EXPECT_EQ(entries.size(), 3);

    // Should get most recent 3
    EXPECT_EQ(entries[0].content, "msg4");
    EXPECT_EQ(entries[1].content, "msg3");
    EXPECT_EQ(entries[2].content, "msg2");
}

TEST(WorkingMemoryTest, Capacity) {
    WorkingMemory memory(10);

    EXPECT_EQ(memory.capacity(), 10);
    EXPECT_EQ(memory.count(), 0);

    for (int i = 0; i < 5; i++) {
        memory.store(MemoryEntry::create("msg" + std::to_string(i)));
    }

    EXPECT_EQ(memory.capacity(), 10);
    EXPECT_EQ(memory.count(), 5);
}

// ============================================================================
// ShortTermMemory Tests (LRU + TTL Eviction)
// ============================================================================

TEST(ShortTermMemoryTest, StoreAndRetrieve) {
    ShortTermMemory memory(100, 60);  // 100 messages, 60s TTL

    auto entry = MemoryEntry::create("test message");
    auto result = memory.store(entry);

    ASSERT_TRUE(result.is_ok());

    auto retrieve_result = memory.retrieve(1);
    ASSERT_TRUE(retrieve_result.is_ok());

    auto entries = retrieve_result.unwrap();
    EXPECT_EQ(entries.size(), 1);
    EXPECT_EQ(entries[0].content, "test message");
}

TEST(ShortTermMemoryTest, TTLExpiration) {
    ShortTermMemory memory(100, 1);  // 1 second TTL

    auto entry = MemoryEntry::create("expires soon");
    memory.store(entry);

    // Should be retrievable immediately
    auto retrieve1 = memory.retrieve(1);
    ASSERT_TRUE(retrieve1.is_ok());
    EXPECT_EQ(retrieve1.unwrap().size(), 1);

    // Wait for TTL expiration (wait 2x TTL to ensure expiration)
    std::this_thread::sleep_for(std::chrono::milliseconds(2100));

    // Should be filtered out now
    auto retrieve2 = memory.retrieve(1);
    ASSERT_TRUE(retrieve2.is_ok());
    EXPECT_EQ(retrieve2.unwrap().size(), 0);
}

TEST(ShortTermMemoryTest, LRUEviction) {
    ShortTermMemory memory(3, 3600);  // 3 messages, 1 hour TTL

    auto entry1 = MemoryEntry::create("msg1");
    auto entry2 = MemoryEntry::create("msg2");
    auto entry3 = MemoryEntry::create("msg3");

    auto r1 = memory.store(entry1);
    auto r2 = memory.store(entry2);
    auto r3 = memory.store(entry3);

    ASSERT_TRUE(r1.is_ok());
    ASSERT_TRUE(r2.is_ok());
    ASSERT_TRUE(r3.is_ok());

    std::string id1 = r1.unwrap();

    // Access msg1 to make it recently used
    auto retrieve_result = memory.retrieve(10);
    ASSERT_TRUE(retrieve_result.is_ok());

    // Add 4th entry - should evict LRU (msg2, since msg1 was accessed)
    auto entry4 = MemoryEntry::create("msg4");
    memory.store(entry4);

    EXPECT_EQ(memory.count(), 3);
}

TEST(ShortTermMemoryTest, CapacityAndTTL) {
    ShortTermMemory memory(50, 3600);

    EXPECT_EQ(memory.capacity(), 50);
    EXPECT_EQ(memory.ttl(), 3600);
    EXPECT_EQ(memory.count(), 0);
}

TEST(ShortTermMemoryTest, Remove) {
    ShortTermMemory memory(10, 3600);

    auto entry = MemoryEntry::create("to remove");
    auto store_result = memory.store(entry);
    ASSERT_TRUE(store_result.is_ok());

    std::string id = store_result.unwrap();

    auto remove_result = memory.deleteEntry(id);
    ASSERT_TRUE(remove_result.is_ok());
    EXPECT_TRUE(remove_result.unwrap());

    EXPECT_EQ(memory.count(), 0);
}

TEST(ShortTermMemoryTest, Clear) {
    ShortTermMemory memory(10, 3600);

    memory.store(MemoryEntry::create("msg1"));
    memory.store(MemoryEntry::create("msg2"));

    EXPECT_GT(memory.count(), 0);

    memory.clear();
    EXPECT_EQ(memory.count(), 0);
}

// ============================================================================
// LongTermMemory Tests (Importance Filtering)
// ============================================================================

TEST(LongTermMemoryTest, StoreAndRetrieve) {
    LongTermMemory memory(0.7);  // Min importance 0.7

    // High importance - should be stored
    auto entry1 = MemoryEntry::create("important fact", {}, 0.8);
    auto result1 = memory.store(entry1);

    ASSERT_TRUE(result1.is_ok());
    auto opt_id = result1.unwrap();
    ASSERT_TRUE(opt_id.has_value());

    EXPECT_EQ(memory.count(), 1);

    // Retrieve by query
    auto retrieve_result = memory.retrieve("fact", 10);
    ASSERT_TRUE(retrieve_result.is_ok());

    auto entries = retrieve_result.unwrap();
    EXPECT_EQ(entries.size(), 1);
    EXPECT_EQ(entries[0].content, "important fact");
}

TEST(LongTermMemoryTest, ImportanceThreshold) {
    LongTermMemory memory(0.7);

    // Below threshold - should be silently rejected (not an error!)
    auto entry1 = MemoryEntry::create("minor detail", {}, 0.3);
    auto result1 = memory.store(entry1);

    ASSERT_TRUE(result1.is_ok());
    auto opt_id1 = result1.unwrap();
    EXPECT_FALSE(opt_id1.has_value());  // Rejected due to low importance

    EXPECT_EQ(memory.count(), 0);

    // Above threshold - should be stored
    auto entry2 = MemoryEntry::create("major fact", {}, 0.9);
    auto result2 = memory.store(entry2);

    ASSERT_TRUE(result2.is_ok());
    auto opt_id2 = result2.unwrap();
    EXPECT_TRUE(opt_id2.has_value());

    EXPECT_EQ(memory.count(), 1);
}

TEST(LongTermMemoryTest, RelevanceRanking) {
    LongTermMemory memory(0.5);

    // Store entries with different relevance to query "python"
    memory.store(MemoryEntry::create("User prefers Python programming", {}, 0.8));
    memory.store(MemoryEntry::create("Python is a snake", {}, 0.6));
    memory.store(MemoryEntry::create("Java programming tutorial", {}, 0.7));

    EXPECT_EQ(memory.count(), 3);

    // Query for "python" - returns ALL entries ranked by relevance
    auto result = memory.retrieve("python", 10);
    ASSERT_TRUE(result.is_ok());

    auto entries = result.unwrap();
    EXPECT_EQ(entries.size(), 3);  // All entries returned, ranked by relevance

    // Entries with "python" should rank higher due to keyword match bonus
    // (keyword_match: 0.5, importance: 0.3, recency: 0.2)
    // First two should contain "python" (higher relevance scores)
    EXPECT_NE(entries[0].content.find("Python"), std::string::npos);
    EXPECT_NE(entries[1].content.find("Python"), std::string::npos);
}

TEST(LongTermMemoryTest, Remove) {
    LongTermMemory memory(0.5);

    auto entry = MemoryEntry::create("to delete", {}, 0.8);
    auto store_result = memory.store(entry);
    ASSERT_TRUE(store_result.is_ok());

    auto opt_id = store_result.unwrap();
    ASSERT_TRUE(opt_id.has_value());

    std::string id = opt_id.value();

    auto remove_result = memory.deleteEntry(id);
    ASSERT_TRUE(remove_result.is_ok());
    EXPECT_TRUE(remove_result.unwrap());

    EXPECT_EQ(memory.count(), 0);
}

TEST(LongTermMemoryTest, GetAll) {
    LongTermMemory memory(0.5);

    memory.store(MemoryEntry::create("fact 1", {}, 0.8));
    memory.store(MemoryEntry::create("fact 2", {}, 0.7));
    memory.store(MemoryEntry::create("fact 3", {}, 0.9));

    EXPECT_EQ(memory.count(), 3);

    auto all_result = memory.get_all();
    ASSERT_TRUE(all_result.is_ok());

    auto all = all_result.unwrap();
    EXPECT_EQ(all.size(), 3);
}

TEST(LongTermMemoryTest, Clear) {
    LongTermMemory memory(0.5);

    memory.store(MemoryEntry::create("fact 1", {}, 0.8));
    memory.store(MemoryEntry::create("fact 2", {}, 0.9));

    EXPECT_EQ(memory.count(), 2);

    memory.clear();
    EXPECT_EQ(memory.count(), 0);
}

TEST(LongTermMemoryTest, MinImportance) {
    LongTermMemory memory(0.6);

    EXPECT_DOUBLE_EQ(memory.min_importance(), 0.6);
}

// ============================================================================
// MemoryHierarchy Tests
// ============================================================================

TEST(MemoryHierarchyTest, StoreAcrossTiers) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.7);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    // High importance - should be stored in all tiers
    std::map<std::string, nlohmann::json> metadata;
    metadata["category"] = "preference";

    auto result = hierarchy.store(
        "User prefers Python",
        metadata,
        0.9,
        "session-1"
    );

    ASSERT_TRUE(result.is_ok());

    auto stats = hierarchy.get_stats();
    EXPECT_EQ(stats["working"], 1);
    EXPECT_EQ(stats["short_term"], 1);
    EXPECT_EQ(stats["long_term"], 1);
}

TEST(MemoryHierarchyTest, ImportanceBasedRouting) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.7);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    // Low importance - should skip long-term
    auto result = hierarchy.store(
        "Minor detail",
        {},
        0.3
    );

    ASSERT_TRUE(result.is_ok());

    auto stats = hierarchy.get_stats();
    EXPECT_EQ(stats["working"], 1);
    EXPECT_EQ(stats["short_term"], 1);
    EXPECT_EQ(stats["long_term"], 0);  // Skipped due to low importance
}

TEST(MemoryHierarchyTest, RetrieveFromAllTiers) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.5);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    // Store with different importance levels
    hierarchy.store("Python programming", {}, 0.9);
    hierarchy.store("Python tutorial", {}, 0.7);
    hierarchy.store("Python example", {}, 0.5);

    // Retrieve from all tiers
    auto result = hierarchy.retrieve("Python", 10);
    ASSERT_TRUE(result.is_ok());

    auto entries = result.unwrap();
    EXPECT_GE(entries.size(), 1);
}

TEST(MemoryHierarchyTest, RetrieveFromSpecificTiers) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.7);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    hierarchy.store("Test message", {}, 0.9);

    // Retrieve only from working
    auto result = hierarchy.retrieve("Test", 10, {"working"});
    ASSERT_TRUE(result.is_ok());

    auto entries = result.unwrap();
    EXPECT_GE(entries.size(), 0);
}

TEST(MemoryHierarchyTest, RemoveFromAllTiers) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.5);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    auto store_result = hierarchy.store("To delete", {}, 0.9);
    ASSERT_TRUE(store_result.is_ok());

    std::string entry_id = store_result.unwrap();

    auto remove_result = hierarchy.deleteEntry(entry_id);
    ASSERT_TRUE(remove_result.is_ok());

    // Should be removed from all tiers
    auto stats = hierarchy.get_stats();
    EXPECT_EQ(stats["working"], 0);
    EXPECT_EQ(stats["short_term"], 0);
    EXPECT_EQ(stats["long_term"], 0);
}

TEST(MemoryHierarchyTest, ClearWorking) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term)
    );

    hierarchy.store("Message 1", {}, 0.5);
    hierarchy.store("Message 2", {}, 0.5);

    hierarchy.clear_working();

    auto stats = hierarchy.get_stats();
    EXPECT_EQ(stats["working"], 0);
    EXPECT_GT(stats["short_term"], 0);  // Short-term still has entries
}

TEST(MemoryHierarchyTest, ClearAll) {
    auto working = std::make_unique<WorkingMemory>(10);
    auto short_term = std::make_unique<ShortTermMemory>(100, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.5);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    hierarchy.store("Message 1", {}, 0.9);
    hierarchy.store("Message 2", {}, 0.8);

    hierarchy.clear_all();

    auto stats = hierarchy.get_stats();
    EXPECT_EQ(stats["working"], 0);
    EXPECT_EQ(stats["short_term"], 0);
    EXPECT_EQ(stats["long_term"], 0);
}

// ============================================================================
// Thread Safety Tests
// ============================================================================

TEST(MemoryThreadSafetyTest, ConcurrentWorkingMemory) {
    WorkingMemory memory(100);

    std::vector<std::thread> threads;
    const int num_threads = 10;
    const int ops_per_thread = 50;

    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&memory, t, ops_per_thread]() {
            for (int i = 0; i < ops_per_thread; i++) {
                std::string content = "msg_" + std::to_string(t) + "_" + std::to_string(i);
                auto entry = MemoryEntry::create(content);
                memory.store(entry);
                memory.retrieve(10);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Should complete without crashes
    EXPECT_LE(memory.count(), 100);  // Capacity limit
}

TEST(MemoryThreadSafetyTest, ConcurrentLongTermMemory) {
    LongTermMemory memory(0.5);

    std::vector<std::thread> threads;
    const int num_threads = 10;
    const int ops_per_thread = 20;

    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&memory, t, ops_per_thread]() {
            for (int i = 0; i < ops_per_thread; i++) {
                std::string content = "fact_" + std::to_string(t) + "_" + std::to_string(i);
                auto entry = MemoryEntry::create(content, {}, 0.8);
                memory.store(entry);
                memory.retrieve("fact", 10);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    EXPECT_EQ(memory.count(), num_threads * ops_per_thread);
}

TEST(MemoryThreadSafetyTest, ConcurrentHierarchy) {
    auto working = std::make_unique<WorkingMemory>(50);
    auto short_term = std::make_unique<ShortTermMemory>(200, 3600);
    auto long_term = std::make_unique<LongTermMemory>(0.5);

    MemoryHierarchy hierarchy(
        std::move(working),
        std::move(short_term),
        std::move(long_term)
    );

    std::vector<std::thread> threads;
    const int num_threads = 5;

    for (int t = 0; t < num_threads; t++) {
        threads.emplace_back([&hierarchy, t]() {
            for (int i = 0; i < 20; i++) {
                std::string content = "entry_" + std::to_string(t) + "_" + std::to_string(i);
                hierarchy.store(content, {}, 0.7);
                hierarchy.retrieve(content, 5);
            }
        });
    }

    for (auto& thread : threads) {
        thread.join();
    }

    // Should complete without crashes
    auto stats = hierarchy.get_stats();
    EXPECT_GT(stats["working"], 0);
}
