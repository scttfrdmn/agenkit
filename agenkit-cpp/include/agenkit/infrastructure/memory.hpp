#pragma once

/// C++ Memory System for Long-Running AI Agents
///
/// Three-tier hierarchy for managing conversation context beyond 200K token limits:
///
/// 1. **WorkingMemory**: Current context (5-20 messages, FIFO eviction)
/// 2. **ShortTermMemory**: Recent session (100-1000 messages, LRU + TTL eviction)
/// 3. **LongTermMemory**: Persistent facts (unbounded, importance-filtered)
///
/// **Example Usage:**
/// ```cpp
/// using namespace agenkit::infrastructure::memory;
///
/// // Create three-tier hierarchy
/// auto working = std::make_unique<WorkingMemory>(10);
/// auto short_term = std::make_unique<ShortTermMemory>(100, 3600);  // 1 hour TTL
/// auto long_term = std::make_unique<LongTermMemory>(0.7);  // importance >= 0.7
///
/// MemoryHierarchy hierarchy(
///     std::move(working),
///     std::move(short_term),
///     std::move(long_term)
/// );
///
/// // Store messages
/// hierarchy.store("User prefers Python", {}, 0.8, "session-1");
/// hierarchy.store("Current task: implement auth", {}, 0.6, "session-1");
///
/// // Retrieve relevant context
/// auto result = hierarchy.retrieve("Python", 5);
/// if (result.is_ok()) {
///     for (const auto& entry : result.unwrap()) {
///         std::cout << entry.content << " (importance: " << entry.importance << ")\n";
///     }
/// }
/// ```

#include "agenkit/infrastructure/memory/entry.hpp"
#include "agenkit/infrastructure/memory/working.hpp"
#include "agenkit/infrastructure/memory/short_term.hpp"
#include "agenkit/infrastructure/memory/long_term.hpp"
#include "agenkit/infrastructure/memory/hierarchy.hpp"
#include "agenkit/infrastructure/memory/redis_memory.hpp"
