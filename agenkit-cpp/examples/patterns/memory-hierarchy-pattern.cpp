/**
 * @file memory_example.cpp
 * @brief Demonstrates the Memory hierarchy pattern
 *
 * This example shows how to use the three-tier memory system:
 * - Working Memory: Current conversation context
 * - Short-term Memory: Recent sessions with TTL
 * - Long-term Memory: Important persistent facts
 */

#include "agenkit/patterns/memory.hpp"
#include <iostream>
#include <iomanip>
#include <thread>
#include <chrono>

using namespace agenkit;
using namespace agenkit::patterns;

void print_separator() {
    std::cout << std::string(70, '=') << "\n";
}

void print_memories(const std::vector<MemoryEntry>& memories, const std::string& title) {
    std::cout << "\n" << title << " (" << memories.size() << " entries):\n";
    for (size_t i = 0; i < memories.size(); ++i) {
        std::cout << "  " << (i + 1) << ". " << memories[i].content;
        std::cout << " (importance: " << std::fixed << std::setprecision(1)
                  << memories[i].importance;
        std::cout << ", accessed: " << memories[i].access_count << "x)\n";
    }
}

/**
 * Example 1: Working Memory - Current Conversation
 * Demonstrates FIFO eviction and context management
 */
void example_working_memory() {
    print_separator();
    std::cout << "Example 1: Working Memory (Current Context)\n";
    print_separator();

    WorkingMemory memory(3);  // Keep only 3 most recent messages

    std::cout << "\nCharacteristics:\n";
    std::cout << "  • Small capacity (3 messages)\n";
    std::cout << "  • FIFO eviction (oldest removed first)\n";
    std::cout << "  • Fast O(1) storage\n";
    std::cout << "  • Use case: Current conversation context\n";

    std::cout << "\nAdding conversation messages:\n";

    memory.store(MemoryEntry("User: Hello, I'm Alice", 0.3));
    std::cout << "  Added: 'User: Hello, I'm Alice'\n";

    memory.store(MemoryEntry("Assistant: Hi Alice! How can I help?", 0.3));
    std::cout << "  Added: 'Assistant: Hi Alice! How can I help?'\n";

    memory.store(MemoryEntry("User: What's the weather like?", 0.5));
    std::cout << "  Added: 'User: What's the weather like?'\n";

    std::cout << "\nCurrent working memory (" << memory.size() << " messages):\n";
    auto all = memory.get_all();
    for (const auto& entry : all) {
        std::cout << "  • " << entry.content << "\n";
    }

    std::cout << "\nAdding 4th message (triggers FIFO eviction):\n";
    memory.store(MemoryEntry("Assistant: It's sunny and 72°F", 0.5));
    std::cout << "  Added: 'Assistant: It's sunny and 72°F'\n";
    std::cout << "  Evicted: 'User: Hello, I'm Alice' (oldest)\n";

    std::cout << "\nUpdated working memory (" << memory.size() << " messages):\n";
    all = memory.get_all();
    for (const auto& entry : all) {
        std::cout << "  • " << entry.content << "\n";
    }

    // Demonstrate retrieval
    std::cout << "\nSearching for 'weather':\n";
    auto results = memory.retrieve("weather", 10);
    for (const auto& entry : results) {
        std::cout << "  ✓ Found: " << entry.content << "\n";
    }
}

/**
 * Example 2: Short-term Memory - Recent Sessions
 * Demonstrates TTL-based expiry and recency
 */
void example_short_term_memory() {
    print_separator();
    std::cout << "\nExample 2: Short-term Memory (Recent Sessions)\n";
    print_separator();

    ShortTermMemory memory(100, 2);  // 100 max, 2 second TTL

    std::cout << "\nCharacteristics:\n";
    std::cout << "  • Medium capacity (100 messages)\n";
    std::cout << "  • Time-to-live: 2 seconds\n";
    std::cout << "  • Automatic expiry cleanup\n";
    std::cout << "  • Use case: Recent conversation history\n";

    std::cout << "\nAdding session memories:\n";
    memory.store(MemoryEntry("User prefers Python over Java", 0.6));
    std::cout << "  Added: 'User prefers Python over Java'\n";

    memory.store(MemoryEntry("User is working on ML project", 0.7));
    std::cout << "  Added: 'User is working on ML project'\n";

    memory.store(MemoryEntry("User asked about TensorFlow", 0.6));
    std::cout << "  Added: 'User asked about TensorFlow'\n";

    std::cout << "\nCurrent short-term memory: " << memory.size() << " entries\n";

    std::cout << "\nWaiting 2.5 seconds for TTL expiry...\n";
    std::this_thread::sleep_for(std::chrono::milliseconds(2500));

    int removed = memory.cleanup_expired();
    std::cout << "  Cleaned up " << removed << " expired entries\n";
    std::cout << "  Remaining: " << memory.size() << " entries\n";

    // Add fresh memory
    std::cout << "\nAdding new memory after expiry:\n";
    memory.store(MemoryEntry("User mentioned PyTorch interest", 0.7));
    std::cout << "  Added: 'User mentioned PyTorch interest'\n";
    std::cout << "  Current size: " << memory.size() << " entries\n";
}

/**
 * Example 3: Long-term Memory - Important Facts
 * Demonstrates importance-based storage and retrieval
 */
void example_long_term_memory() {
    print_separator();
    std::cout << "\nExample 3: Long-term Memory (Persistent Facts)\n";
    print_separator();

    LongTermMemory memory(0.6);  // Only store importance >= 0.6

    std::cout << "\nCharacteristics:\n";
    std::cout << "  • Large/unlimited capacity\n";
    std::cout << "  • Importance threshold: 0.6\n";
    std::cout << "  • Importance-based retrieval (highest first)\n";
    std::cout << "  • Use case: Important facts, preferences, knowledge\n";

    std::cout << "\nAttempting to store memories:\n";

    memory.store(MemoryEntry("User's name is Alice", 0.9));
    std::cout << "  ✓ Stored: 'User's name is Alice' (importance: 0.9)\n";

    memory.store(MemoryEntry("Weather was sunny yesterday", 0.4));
    std::cout << "  ✗ Rejected: 'Weather was sunny yesterday' (importance: 0.4 < 0.6)\n";

    memory.store(MemoryEntry("User works at TechCorp", 0.8));
    std::cout << "  ✓ Stored: 'User works at TechCorp' (importance: 0.8)\n";

    memory.store(MemoryEntry("User likes coffee", 0.7));
    std::cout << "  ✓ Stored: 'User likes coffee' (importance: 0.7)\n";

    memory.store(MemoryEntry("Casual small talk", 0.3));
    std::cout << "  ✗ Rejected: 'Casual small talk' (importance: 0.3 < 0.6)\n";

    memory.store(MemoryEntry("User is allergic to peanuts", 0.95));
    std::cout << "  ✓ Stored: 'User is allergic to peanuts' (importance: 0.95)\n";

    std::cout << "\nLong-term memory size: " << memory.size() << " entries\n";

    std::cout << "\nRetrieving all memories (sorted by importance):\n";
    auto all = memory.retrieve("", 10);  // Empty query returns all
    for (size_t i = 0; i < all.size(); ++i) {
        std::cout << "  " << (i + 1) << ". " << all[i].content;
        std::cout << " (importance: " << all[i].importance << ")\n";
    }

    std::cout << "\nSearching for 'User' facts:\n";
    auto user_facts = memory.retrieve("User", 10);
    for (const auto& fact : user_facts) {
        std::cout << "  • " << fact.content;
        std::cout << " (importance: " << fact.importance << ")\n";
    }
}

/**
 * Example 4: Memory Hierarchy - Unified System
 * Demonstrates automatic tier management and cross-tier retrieval
 */
void example_memory_hierarchy() {
    print_separator();
    std::cout << "\nExample 4: Memory Hierarchy (Unified 3-Tier System)\n";
    print_separator();

    MemoryHierarchy hierarchy(
        3,      // Working memory: 3 messages
        10,     // Short-term: 10 messages
        3600,   // TTL: 1 hour
        0.7     // Long-term threshold: 0.7
    );

    std::cout << "\nConfiguration:\n";
    std::cout << "  Working Memory: 3 max, FIFO eviction\n";
    std::cout << "  Short-term Memory: 10 max, 1 hour TTL\n";
    std::cout << "  Long-term Memory: Unlimited, importance >= 0.7\n";

    std::cout << "\nStoring conversation with varying importance:\n";

    hierarchy.store("Hi, I'm Bob", 0.4);
    std::cout << "  'Hi, I'm Bob' (0.4) → Working + Short-term\n";

    hierarchy.store("I work as a data scientist", 0.8);
    std::cout << "  'I work as a data scientist' (0.8) → All three tiers\n";

    hierarchy.store("What's the weather?", 0.3);
    std::cout << "  'What's the weather?' (0.3) → Working + Short-term\n";

    hierarchy.store("I have a nut allergy", 0.95);
    std::cout << "  'I have a nut allergy' (0.95) → All three tiers\n";

    hierarchy.store("Tell me a joke", 0.2);
    std::cout << "  'Tell me a joke' (0.2) → Working + Short-term\n";

    std::cout << "\nMemory tier sizes:\n";
    std::cout << "  Working: " << hierarchy.get_working_memory().size() << " entries\n";
    std::cout << "  Short-term: " << hierarchy.get_short_term_memory().size() << " entries\n";
    std::cout << "  Long-term: " << hierarchy.get_long_term_memory().size() << " entries\n";
    std::cout << "  Total: " << hierarchy.total_size() << " entries (across all tiers)\n";

    std::cout << "\nRetrieving across all tiers (query: 'I'):\n";
    auto results = hierarchy.retrieve("I", 10);
    std::cout << "  Found " << results.size() << " unique entries:\n";
    for (const auto& entry : results) {
        std::cout << "    • " << entry.content;
        std::cout << " (importance: " << entry.importance << ")\n";
    }
}

/**
 * Example 5: Chatbot with Memory
 * Demonstrates practical usage in a conversational agent
 */
void example_chatbot_memory() {
    print_separator();
    std::cout << "\nExample 5: Chatbot with Memory System\n";
    print_separator();

    MemoryHierarchy memory(5, 50, 3600, 0.7);

    std::cout << "\nSimulating conversation with memory:\n";

    // Turn 1
    std::cout << "\n[Turn 1]\n";
    std::cout << "User: Hi, my name is Sarah\n";
    memory.store("User's name is Sarah", 0.9);

    std::cout << "Assistant: Hello Sarah! Nice to meet you.\n";
    memory.store("Greeted user Sarah", 0.3);

    // Turn 2
    std::cout << "\n[Turn 2]\n";
    std::cout << "User: I'm interested in learning machine learning\n";
    memory.store("User wants to learn ML", 0.8);

    std::cout << "Assistant: Great! ML is fascinating. Do you have programming experience?\n";
    memory.store("Asked about programming experience", 0.4);

    // Turn 3
    std::cout << "\n[Turn 3]\n";
    std::cout << "User: Yes, I know Python well\n";
    memory.store("User knows Python", 0.7);

    std::cout << "Assistant: Perfect! Python is ideal for ML.\n";
    memory.store("Confirmed Python for ML", 0.5);

    // Recall user information
    std::cout << "\n[Recalling User Information]\n";
    std::cout << "Searching memory for 'User':\n";
    auto user_info = memory.retrieve("User", 10);
    std::cout << "  Retrieved " << user_info.size() << " relevant memories:\n";
    for (const auto& info : user_info) {
        std::cout << "    • " << info.content;
        std::cout << " (tier: ";
        if (info.importance >= 0.7) {
            std::cout << "long-term";
        } else {
            std::cout << "short-term";
        }
        std::cout << ")\n";
    }

    // Demonstrate personalized response
    std::cout << "\n[Turn 4 - Using Memory]\n";
    std::cout << "User: Recommend a resource for me\n";

    auto name_results = memory.retrieve("name is", 1);
    auto ml_results = memory.retrieve("ML", 1);
    auto python_results = memory.retrieve("Python", 1);

    std::cout << "Assistant: Based on what I know about you:\n";
    if (!name_results.empty()) {
        std::cout << "  • Name: Sarah\n";
    }
    if (!ml_results.empty()) {
        std::cout << "  • Interest: Machine Learning\n";
    }
    if (!python_results.empty()) {
        std::cout << "  • Skills: Python\n";
    }
    std::cout << "  I recommend starting with scikit-learn tutorials!\n";

    std::cout << "\n Memory System Stats:\n";
    std::cout << "  Working memory: " << memory.get_working_memory().size() << " entries\n";
    std::cout << "  Short-term memory: " << memory.get_short_term_memory().size() << " entries\n";
    std::cout << "  Long-term memory: " << memory.get_long_term_memory().size() << " entries\n";
}

/**
 * Example 6: Memory Metadata
 * Shows using metadata for richer memory entries
 */
void example_memory_metadata() {
    print_separator();
    std::cout << "\nExample 6: Memory with Metadata\n";
    print_separator();

    MemoryHierarchy memory;

    std::cout << "\nStoring memories with metadata:\n";

    std::map<std::string, std::string> metadata1;
    metadata1["source"] = "user";
    metadata1["topic"] = "preferences";
    metadata1["session"] = "2024-01-15";
    memory.store("Prefers dark mode UI", 0.7, metadata1);
    std::cout << "  Stored: 'Prefers dark mode UI'\n";
    std::cout << "    Metadata: source=user, topic=preferences\n";

    std::map<std::string, std::string> metadata2;
    metadata2["source"] = "system";
    metadata2["topic"] = "behavior";
    metadata2["session"] = "2024-01-15";
    memory.store("Frequently uses shortcuts", 0.6, metadata2);
    std::cout << "  Stored: 'Frequently uses shortcuts'\n";
    std::cout << "    Metadata: source=system, topic=behavior\n";

    std::map<std::string, std::string> metadata3;
    metadata3["source"] = "user";
    metadata3["topic"] = "personal";
    metadata3["session"] = "2024-01-16";
    memory.store("Birthday is in March", 0.9, metadata3);
    std::cout << "  Stored: 'Birthday is in March'\n";
    std::cout << "    Metadata: source=user, topic=personal\n";

    std::cout << "\nRetrieving memories:\n";
    auto results = memory.retrieve("", 10);
    for (const auto& entry : results) {
        std::cout << "  • " << entry.content << "\n";
        std::cout << "    Source: " << entry.metadata.at("source");
        std::cout << ", Topic: " << entry.metadata.at("topic");
        std::cout << ", Session: " << entry.metadata.at("session") << "\n";
    }
}

int main() {
    std::cout << "\n";
    std::cout << "╔═══════════════════════════════════════════════════════════════════╗\n";
    std::cout << "║         Memory Hierarchy Pattern - Comprehensive Examples        ║\n";
    std::cout << "╚═══════════════════════════════════════════════════════════════════╝\n";

    example_working_memory();
    example_short_term_memory();
    example_long_term_memory();
    example_memory_hierarchy();
    example_chatbot_memory();
    example_memory_metadata();

    print_separator();
    std::cout << "\nKey Takeaways:\n";
    std::cout << "  • Working Memory: Small, fast, FIFO eviction for current context\n";
    std::cout << "  • Short-term Memory: Medium capacity, TTL-based for recent history\n";
    std::cout << "  • Long-term Memory: Unlimited, importance-based for key facts\n";
    std::cout << "  • Hierarchy: Unified system with automatic tier management\n";
    std::cout << "  • Use metadata for richer memory organization\n";
    std::cout << "  • Perfect for chatbots, assistants, and stateful agents\n";
    print_separator();

    return 0;
}
