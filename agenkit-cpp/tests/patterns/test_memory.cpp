/**
 * @file test_memory.cpp
 * @brief Tests for Memory hierarchy pattern
 */

#include <gtest/gtest.h>
#include "agenkit/patterns/memory.hpp"
#include <thread>
#include <chrono>

using namespace agenkit;
using namespace agenkit::patterns;

// ============================================================================
// MemoryEntry Tests
// ============================================================================

TEST(MemoryEntryTest, Construction) {
    MemoryEntry entry("Test content", 0.8);

    EXPECT_EQ(entry.content, "Test content");
    EXPECT_DOUBLE_EQ(entry.importance, 0.8);
    EXPECT_FALSE(entry.id.empty());
    EXPECT_EQ(entry.access_count, 0);
    EXPECT_FALSE(entry.last_accessed.has_value());
}

TEST(MemoryEntryTest, UniqueIds) {
    MemoryEntry entry1("Content 1");
    MemoryEntry entry2("Content 2");

    EXPECT_NE(entry1.id, entry2.id);
}

TEST(MemoryEntryTest, Metadata) {
    MemoryEntry entry("Test");
    entry.metadata["key1"] = "value1";
    entry.metadata["key2"] = "value2";

    EXPECT_EQ(entry.metadata.size(), 2);
    EXPECT_EQ(entry.metadata["key1"], "value1");
    EXPECT_EQ(entry.metadata["key2"], "value2");
}

// ============================================================================
// WorkingMemory Tests
// ============================================================================

TEST(WorkingMemoryTest, Construction) {
    WorkingMemory memory(10);

    EXPECT_EQ(memory.size(), 0);
}

TEST(WorkingMemoryTest, StoreAndRetrieve) {
    WorkingMemory memory(10);

    MemoryEntry entry("Hello world", 0.5);
    memory.store(entry);

    EXPECT_EQ(memory.size(), 1);

    auto results = memory.retrieve("world", 10);
    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].content, "Hello world");
}

TEST(WorkingMemoryTest, FIFOEviction) {
    WorkingMemory memory(3);

    memory.store(MemoryEntry("First", 0.5));
    memory.store(MemoryEntry("Second", 0.5));
    memory.store(MemoryEntry("Third", 0.5));
    memory.store(MemoryEntry("Fourth", 0.5));  // Should evict "First"

    EXPECT_EQ(memory.size(), 3);

    auto all = memory.get_all();
    EXPECT_EQ(all[0].content, "Second");
    EXPECT_EQ(all[1].content, "Third");
    EXPECT_EQ(all[2].content, "Fourth");
}

TEST(WorkingMemoryTest, RetrieveLimit) {
    WorkingMemory memory(10);

    for (int i = 0; i < 5; ++i) {
        memory.store(MemoryEntry("test message", 0.5));
    }

    auto results = memory.retrieve("test", 2);
    EXPECT_EQ(results.size(), 2);
}

TEST(WorkingMemoryTest, RetrieveMostRecentFirst) {
    WorkingMemory memory(10);

    memory.store(MemoryEntry("Old message", 0.5));
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    memory.store(MemoryEntry("New message", 0.5));

    auto results = memory.retrieve("message", 10);
    EXPECT_EQ(results.size(), 2);
    EXPECT_EQ(results[0].content, "New message");  // Most recent first
    EXPECT_EQ(results[1].content, "Old message");
}

TEST(WorkingMemoryTest, AccessTracking) {
    WorkingMemory memory(10);

    MemoryEntry entry("Track me", 0.5);
    memory.store(entry);

    auto results = memory.retrieve("Track", 10);
    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].access_count, 1);
    EXPECT_TRUE(results[0].last_accessed.has_value());
}

TEST(WorkingMemoryTest, Remove) {
    WorkingMemory memory(10);

    MemoryEntry entry("Remove me", 0.5);
    memory.store(entry);

    std::string id = memory.get_all()[0].id;
    memory.del(id);

    EXPECT_EQ(memory.size(), 0);
}

TEST(WorkingMemoryTest, Clear) {
    WorkingMemory memory(10);

    memory.store(MemoryEntry("Entry 1", 0.5));
    memory.store(MemoryEntry("Entry 2", 0.5));

    EXPECT_EQ(memory.size(), 2);

    memory.clear();

    EXPECT_EQ(memory.size(), 0);
}

// ============================================================================
// ShortTermMemory Tests
// ============================================================================

TEST(ShortTermMemoryTest, Construction) {
    ShortTermMemory memory(100, 3600);

    EXPECT_EQ(memory.size(), 0);
}

TEST(ShortTermMemoryTest, StoreAndRetrieve) {
    ShortTermMemory memory(100, 3600);

    MemoryEntry entry("Short term memory", 0.5);
    memory.store(entry);

    EXPECT_EQ(memory.size(), 1);

    auto results = memory.retrieve("term", 10);
    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].content, "Short term memory");
}

TEST(ShortTermMemoryTest, CapacityLimit) {
    ShortTermMemory memory(3, 0);  // No TTL

    memory.store(MemoryEntry("First", 0.5));
    memory.store(MemoryEntry("Second", 0.5));
    memory.store(MemoryEntry("Third", 0.5));
    memory.store(MemoryEntry("Fourth", 0.5));  // Should evict "First"

    EXPECT_EQ(memory.size(), 3);

    auto all = memory.get_all();
    EXPECT_EQ(all[0].content, "Second");
}

TEST(ShortTermMemoryTest, TTLExpiry) {
    ShortTermMemory memory(100, 1);  // 1 second TTL

    memory.store(MemoryEntry("Will expire", 0.5));

    EXPECT_EQ(memory.size(), 1);

    // Wait for expiry (use significantly longer time to ensure cleanup)
    std::this_thread::sleep_for(std::chrono::seconds(2));

    int removed = memory.cleanup_expired();
    // TTL-based cleanup may have timing variations, so just check size decreased
    EXPECT_EQ(memory.size(), 0);
}

TEST(ShortTermMemoryTest, NoTTL) {
    ShortTermMemory memory(100, 0);  // No TTL

    memory.store(MemoryEntry("Never expires", 0.5));

    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    int removed = memory.cleanup_expired();
    EXPECT_EQ(removed, 0);
    EXPECT_EQ(memory.size(), 1);
}

TEST(ShortTermMemoryTest, CleanupOnRetrieve) {
    ShortTermMemory memory(100, 1);  // 1 second TTL

    memory.store(MemoryEntry("Will expire", 0.5));
    memory.store(MemoryEntry("Also expires", 0.5));

    EXPECT_EQ(memory.size(), 2);

    // Wait for expiry (use significantly longer time to ensure cleanup)
    std::this_thread::sleep_for(std::chrono::seconds(2));

    // retrieve() should cleanup expired entries
    auto results = memory.retrieve("expires", 10);

    // After TTL expiry, entries should be cleaned up
    EXPECT_EQ(results.size(), 0);
    EXPECT_EQ(memory.size(), 0);
}

TEST(ShortTermMemoryTest, Remove) {
    ShortTermMemory memory(100, 3600);

    MemoryEntry entry("Remove me", 0.5);
    memory.store(entry);

    std::string id = memory.get_all()[0].id;
    memory.del(id);

    EXPECT_EQ(memory.size(), 0);
}

// ============================================================================
// LongTermMemory Tests
// ============================================================================

TEST(LongTermMemoryTest, Construction) {
    LongTermMemory memory(0.5);

    EXPECT_EQ(memory.size(), 0);
}

TEST(LongTermMemoryTest, ImportanceThreshold) {
    LongTermMemory memory(0.7);  // Only store importance >= 0.7

    memory.store(MemoryEntry("Low importance", 0.5));
    memory.store(MemoryEntry("High importance", 0.9));

    EXPECT_EQ(memory.size(), 1);

    auto all = memory.get_all();
    EXPECT_EQ(all[0].content, "High importance");
}

TEST(LongTermMemoryTest, ImportanceBasedRetrieval) {
    LongTermMemory memory(0.0);  // Accept all

    memory.store(MemoryEntry("Low priority fact", 0.3));
    memory.store(MemoryEntry("High priority fact", 0.9));
    memory.store(MemoryEntry("Medium priority fact", 0.6));

    auto results = memory.retrieve("fact", 10);

    EXPECT_EQ(results.size(), 3);
    // Results should be sorted by importance (highest first)
    EXPECT_EQ(results[0].content, "High priority fact");
    EXPECT_EQ(results[1].content, "Medium priority fact");
    EXPECT_EQ(results[2].content, "Low priority fact");
}

TEST(LongTermMemoryTest, RetrieveLimit) {
    LongTermMemory memory(0.0);

    for (int i = 0; i < 5; ++i) {
        memory.store(MemoryEntry("test fact", 0.5 + i * 0.1));
    }

    auto results = memory.retrieve("fact", 2);
    EXPECT_EQ(results.size(), 2);
    // Should return highest importance
    EXPECT_DOUBLE_EQ(results[0].importance, 0.9);
    EXPECT_DOUBLE_EQ(results[1].importance, 0.8);
}

TEST(LongTermMemoryTest, AccessTracking) {
    LongTermMemory memory(0.5);

    memory.store(MemoryEntry("Important fact", 0.8));

    auto results = memory.retrieve("Important", 10);
    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].access_count, 1);
    EXPECT_TRUE(results[0].last_accessed.has_value());

    // Access again
    results = memory.retrieve("Important", 10);
    EXPECT_EQ(results[0].access_count, 2);
}

TEST(LongTermMemoryTest, Remove) {
    LongTermMemory memory(0.5);

    MemoryEntry entry("Remove me", 0.8);
    memory.store(entry);

    std::string id = memory.get_all()[0].id;
    memory.del(id);

    EXPECT_EQ(memory.size(), 0);
}

TEST(LongTermMemoryTest, UnlimitedCapacity) {
    LongTermMemory memory(0.0);

    // Store many entries
    for (int i = 0; i < 1000; ++i) {
        memory.store(MemoryEntry("Fact " + std::to_string(i), 0.5));
    }

    EXPECT_EQ(memory.size(), 1000);
}

// ============================================================================
// MemoryHierarchy Tests
// ============================================================================

TEST(MemoryHierarchyTest, Construction) {
    MemoryHierarchy hierarchy;

    EXPECT_EQ(hierarchy.total_size(), 0);
}

TEST(MemoryHierarchyTest, StoreInAllTiers) {
    MemoryHierarchy hierarchy(10, 100, 3600, 0.5);

    hierarchy.store("Important message", 0.9);

    // Should be in all three tiers
    EXPECT_GT(hierarchy.get_working_memory().size(), 0);
    EXPECT_GT(hierarchy.get_short_term_memory().size(), 0);
    EXPECT_GT(hierarchy.get_long_term_memory().size(), 0);
}

TEST(MemoryHierarchyTest, StoreWithLowImportance) {
    MemoryHierarchy hierarchy(10, 100, 3600, 0.8);

    hierarchy.store("Low importance", 0.3);

    // Should be in working and short-term, but not long-term
    EXPECT_GT(hierarchy.get_working_memory().size(), 0);
    EXPECT_GT(hierarchy.get_short_term_memory().size(), 0);
    EXPECT_EQ(hierarchy.get_long_term_memory().size(), 0);
}

TEST(MemoryHierarchyTest, RetrieveAcrossTiers) {
    MemoryHierarchy hierarchy(10, 100, 3600, 0.5);

    hierarchy.store("In all tiers", 0.9);
    hierarchy.store("Also in all tiers", 0.9);

    auto results = hierarchy.retrieve("tiers", 10);

    EXPECT_EQ(results.size(), 2);
}

TEST(MemoryHierarchyTest, RetrieveDeduplication) {
    MemoryHierarchy hierarchy(10, 100, 3600, 0.5);

    hierarchy.store("Shared message", 0.9);

    // Should deduplicate across tiers
    auto results = hierarchy.retrieve("Shared", 10);

    EXPECT_EQ(results.size(), 1);
}

TEST(MemoryHierarchyTest, RetrieveLimit) {
    MemoryHierarchy hierarchy(10, 100, 3600, 0.0);

    for (int i = 0; i < 10; ++i) {
        hierarchy.store("Message " + std::to_string(i), 0.5);
    }

    auto results = hierarchy.retrieve("Message", 3);

    EXPECT_EQ(results.size(), 3);
}

TEST(MemoryHierarchyTest, StoreWithMetadata) {
    MemoryHierarchy hierarchy;

    std::map<std::string, std::string> metadata;
    metadata["source"] = "user";
    metadata["topic"] = "test";

    hierarchy.store("Content with metadata", 0.7, metadata);

    auto results = hierarchy.retrieve("Content", 10);

    EXPECT_EQ(results.size(), 1);
    EXPECT_EQ(results[0].metadata["source"], "user");
    EXPECT_EQ(results[0].metadata["topic"], "test");
}

TEST(MemoryHierarchyTest, TotalSize) {
    MemoryHierarchy hierarchy(10, 100, 3600, 0.5);

    hierarchy.store("Message 1", 0.3);  // Working + Short-term
    hierarchy.store("Message 2", 0.9);  // All three tiers

    // Note: Each store creates entries in multiple tiers
    EXPECT_GT(hierarchy.total_size(), 0);
}

TEST(MemoryHierarchyTest, AccessIndividualTiers) {
    MemoryHierarchy hierarchy;

    auto& working = hierarchy.get_working_memory();
    auto& short_term = hierarchy.get_short_term_memory();
    auto& long_term = hierarchy.get_long_term_memory();

    working.store(MemoryEntry("Working only", 0.0));
    short_term.store(MemoryEntry("Short-term only", 0.0));
    long_term.store(MemoryEntry("Long-term only", 0.9));

    EXPECT_EQ(working.size(), 1);
    EXPECT_EQ(short_term.size(), 1);
    EXPECT_EQ(long_term.size(), 1);
}

TEST(MemoryHierarchyTest, WorkingMemoryOverflow) {
    MemoryHierarchy hierarchy(2, 100, 3600, 0.5);  // Working memory max = 2

    hierarchy.store("Message 1", 0.5);
    hierarchy.store("Message 2", 0.5);
    hierarchy.store("Message 3", 0.5);  // Should evict oldest from working

    // Working memory should have only 2 most recent
    EXPECT_EQ(hierarchy.get_working_memory().size(), 2);

    // But short-term should have all 3
    EXPECT_EQ(hierarchy.get_short_term_memory().size(), 3);
}
