/// Redis Memory Example - C++
///
/// Demonstrates Redis-backed persistent memory for production deployments.
///
/// Prerequisites:
///   docker run -d -p 6379:6379 redis:7-alpine
///   Build with: cmake .. -DAGENKIT_WITH_REDIS=ON
///   Requires: hiredis library (apt install libhiredis-dev or brew install hiredis)
///
/// Features:
/// - Persistent storage (survives restarts)
/// - TTL support (automatic expiry)
/// - Multi-instance agents (shared memory)
/// - Filtering (time, importance, tags)
/// - Utilities (session management, stats)

#include <agenkit/infrastructure/memory.hpp>
#include <iostream>
#include <thread>
#include <chrono>

using namespace agenkit::infrastructure::memory;

void print_divider(const std::string& title = "") {
    std::cout << std::string(60, '=') << "\n";
    if (!title.empty()) {
        std::cout << title << "\n";
        std::cout << std::string(60, '=') << "\n";
    }
}

void basic_usage() {
    print_divider("Basic Redis Memory Usage");

    try {
        // Create Redis memory with 24-hour TTL
        auto memory = std::make_unique<RedisMemory>(
            "localhost",
            6379,
            86400,  // 24 hours
            "agenkit:demo"
        );

        std::string session_id = "demo-session-1";

        // Store messages with metadata
        std::cout << "\n📝 Storing messages...\n";

        std::map<std::string, nlohmann::json> metadata1;
        metadata1["importance"] = 0.8;
        metadata1["tags"] = nlohmann::json::array({"question", "technical"});
        memory->store(session_id, "user", "What is Redis?", metadata1);

        std::map<std::string, nlohmann::json> metadata2;
        metadata2["importance"] = 0.9;
        metadata2["tags"] = nlohmann::json::array({"answer", "technical"});
        memory->store(
            session_id,
            "assistant",
            "Redis is an in-memory data structure store used as a database, cache, and message broker.",
            metadata2
        );

        std::map<std::string, nlohmann::json> metadata3;
        metadata3["importance"] = 0.5;
        metadata3["tags"] = nlohmann::json::array({"gratitude"});
        memory->store(session_id, "user", "Thanks!", metadata3);

        // Retrieve recent messages
        std::cout << "\n📤 Retrieving recent messages...\n";
        auto messages = memory->retrieve(session_id, 3);

        for (const auto& msg : messages) {
            std::cout << "[" << msg.role << "] " << msg.content << "\n";
        }

        // Get session count
        size_t count = memory->get_session_count(session_id);
        std::cout << "\n📊 Session has " << count << " messages\n";

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        std::cerr << "Make sure Redis is running: docker run -d -p 6379:6379 redis:7-alpine\n";
    }
}

void filtering_example() {
    print_divider("\nFiltering Example");

    try {
        auto memory = std::make_unique<RedisMemory>(
            "localhost",
            6379,
            86400,
            "agenkit:filter"
        );

        std::string session_id = "filter-demo";

        // Store messages with different importance and tags
        std::cout << "\n📝 Storing messages with metadata...\n";

        std::vector<std::tuple<std::string, double, std::vector<std::string>>> messages = {
            {"Hello", 0.3, {"greeting"}},
            {"Can you help with Redis?", 0.8, {"question", "redis"}},
            {"How do I scale it?", 0.9, {"question", "scaling"}},
            {"Thanks!", 0.2, {"gratitude"}}
        };

        for (const auto& [content, importance, tags] : messages) {
            std::map<std::string, nlohmann::json> metadata;
            metadata["importance"] = importance;
            metadata["tags"] = tags;
            memory->store(session_id, "user", content, metadata);
        }

        // Filter by importance
        std::cout << "\n🔍 High-importance messages (>0.5):\n";
        auto important = memory->retrieve(session_id, 10, std::nullopt, 0.5, std::nullopt);
        for (const auto& msg : important) {
            std::cout << "  " << msg.content << "\n";
        }

        // Filter by tags
        std::cout << "\n🔍 Question messages:\n";
        auto questions = memory->retrieve(
            session_id,
            10,
            std::nullopt,
            std::nullopt,
            std::vector<std::string>{"question"}
        );
        for (const auto& msg : questions) {
            std::cout << "  " << msg.content << "\n";
        }

        // Combined filtering
        std::cout << "\n🔍 Important questions:\n";
        auto important_questions = memory->retrieve(
            session_id,
            10,
            std::nullopt,
            0.8,
            std::vector<std::string>{"question"}
        );
        for (const auto& msg : important_questions) {
            std::cout << "  " << msg.content << "\n";
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
    }
}

void multi_session_example() {
    print_divider("\nMulti-Session Example");

    try {
        auto memory = std::make_unique<RedisMemory>(
            "localhost",
            6379,
            86400,
            "agenkit:multi"
        );

        // Simulate multiple user sessions
        std::cout << "\n👥 Creating multiple sessions...\n";
        memory->store("user-alice", "user", "Hello from Alice");
        memory->store("user-bob", "user", "Hello from Bob");
        memory->store("user-charlie", "user", "Hello from Charlie");

        // List all sessions
        std::cout << "\n📋 All sessions:\n";
        auto sessions = memory->get_all_sessions();
        for (const auto& session : sessions) {
            size_t count = memory->get_session_count(session);
            std::cout << "  " << session << ": " << count << " messages\n";
        }

        // Get usage statistics
        std::cout << "\n📊 Memory usage:\n";
        auto [total_sessions, total_messages, ttl] = memory->get_memory_usage();
        std::cout << "  Total sessions: " << total_sessions << "\n";
        std::cout << "  Total messages: " << total_messages << "\n";
        std::cout << "  TTL: " << ttl << " seconds (" << ttl / 3600 << " hours)\n";

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
    }
}

void summarization_example() {
    print_divider("\nSummarization Example");

    try {
        auto memory = std::make_unique<RedisMemory>(
            "localhost",
            6379,
            86400,
            "agenkit:summary"
        );

        std::string session_id = "conversation";

        // Simulate a long conversation
        std::cout << "\n💬 Simulating conversation...\n";
        std::vector<std::pair<std::string, std::string>> conversation = {
            {"user", "What is Redis?"},
            {"assistant", "Redis is an in-memory database..."},
            {"user", "How fast is it?"},
            {"assistant", "Redis can handle millions of ops/sec..."},
            {"user", "Is it persistent?"},
            {"assistant", "Yes, Redis supports persistence..."}
        };

        for (const auto& [role, content] : conversation) {
            memory->store(session_id, role, content);
        }

        // Get summary
        std::cout << "\n📝 Conversation summary:\n";
        auto summary = memory->summarize(session_id);
        std::cout << summary.content << "\n";

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
    }
}

void production_example() {
    print_divider("\nProduction Deployment Example");

    try {
        // Production configuration
        const char* redis_url = std::getenv("REDIS_HOST");
        std::string host = redis_url ? redis_url : "localhost";

        auto memory = std::make_unique<RedisMemory>(
            host,
            6379,
            7 * 24 * 3600,  // 7 days
            "prod:agenkit:memory"
        );

        std::cout << "\n✅ Production features:\n";
        std::cout << "  • Persistent storage (survives restarts)\n";
        std::cout << "  • 7-day TTL (automatic cleanup)\n";
        std::cout << "  • Multi-instance support (shared memory)\n";
        std::cout << "  • Filtering (time, importance, tags)\n";
        std::cout << "  • Session management utilities\n";

        auto capabilities = RedisMemory::capabilities();
        std::cout << "\n🎯 Capabilities:\n";
        for (const auto& capability : capabilities) {
            std::cout << "  • " << capability << "\n";
        }

        std::cout << "\n💡 Use cases:\n";
        std::cout << "  • Long-running agents (persist across restarts)\n";
        std::cout << "  • Multi-instance deployments (shared state)\n";
        std::cout << "  • Session recovery (restore after failure)\n";
        std::cout << "  • Conversation history (queryable archive)\n";

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
    }
}

int main() {
    try {
        basic_usage();
        filtering_example();
        multi_session_example();
        summarization_example();
        production_example();

        print_divider("\n✅ All examples completed!");

    } catch (const std::exception& e) {
        std::cerr << "\n❌ Error: " << e.what() << "\n";
        if (std::string(e.what()).find("connection") != std::string::npos ||
            std::string(e.what()).find("support not enabled") != std::string::npos) {
            std::cerr << "\nPlease ensure:\n";
            std::cerr << "1. Redis is running: docker run -d -p 6379:6379 redis:7-alpine\n";
            std::cerr << "2. Built with Redis support: cmake .. -DAGENKIT_WITH_REDIS=ON\n";
            std::cerr << "3. hiredis library is installed\n";
        }
        return 1;
    }

    return 0;
}
