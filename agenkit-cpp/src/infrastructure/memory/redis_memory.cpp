#include "agenkit/infrastructure/memory/redis_memory.hpp"
#include <algorithm>
#include <ctime>
#include <sstream>
#include <stdexcept>

#ifdef AGENKIT_WITH_REDIS
#include <hiredis/hiredis.h>
#endif

namespace agenkit {
namespace infrastructure {
namespace memory {

#ifdef AGENKIT_WITH_REDIS

// Redis implementation using hiredis
class RedisMemory::Impl {
public:
    Impl(const std::string& host, int port) {
        context_ = redisConnect(host.c_str(), port);
        if (context_ == nullptr || context_->err) {
            if (context_) {
                std::string err_msg = context_->errstr;
                redisFree(context_);
                throw std::runtime_error("Redis connection error: " + err_msg);
            }
            throw std::runtime_error("Redis connection error: Can't allocate redis context");
        }
    }

    ~Impl() {
        if (context_) {
            redisFree(context_);
        }
    }

    redisContext* context() { return context_; }

private:
    redisContext* context_;
};

#else

// Stub implementation when Redis is not available
class RedisMemory::Impl {
public:
    Impl(const std::string&, int) {
        throw std::runtime_error(
            "Redis support not enabled. Build with -DAGENKIT_WITH_REDIS=ON"
        );
    }
    ~Impl() = default;
};

#endif

RedisMemory::RedisMemory(
    const std::string& host,
    int port,
    int64_t ttl,
    const std::string& key_prefix
)
    : host_(host)
    , port_(port)
    , ttl_(ttl)
    , key_prefix_(key_prefix)
    , impl_(std::make_unique<Impl>(host, port))
{
}

RedisMemory::~RedisMemory() = default;

std::string RedisMemory::session_key(const std::string& session_id) const {
    return key_prefix_ + ":" + session_id + ":messages";
}

std::string RedisMemory::serialize_message(
    const std::string& role,
    const std::string& content,
    const std::map<std::string, nlohmann::json>& metadata
) const {
    nlohmann::json j;
    j["role"] = role;
    j["content"] = content;
    j["metadata"] = metadata;
    return j.dump();
}

std::pair<RedisMessage, std::map<std::string, nlohmann::json>>
RedisMemory::deserialize_message(const std::string& data) const {
    nlohmann::json j = nlohmann::json::parse(data);

    RedisMessage msg;
    msg.role = j["role"].get<std::string>();
    msg.content = j["content"].get<std::string>();

    std::map<std::string, nlohmann::json> metadata;
    if (j.contains("metadata")) {
        metadata = j["metadata"].get<std::map<std::string, nlohmann::json>>();
    }

    return {msg, metadata};
}

double RedisMemory::get_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    return std::chrono::duration_cast<std::chrono::microseconds>(duration).count() / 1000000.0;
}

void RedisMemory::store(
    const std::string& session_id,
    const std::string& role,
    const std::string& content,
    const std::map<std::string, nlohmann::json>& metadata
) {
#ifdef AGENKIT_WITH_REDIS
    double timestamp = get_timestamp();
    std::string value = serialize_message(role, content, metadata);
    std::string key = session_key(session_id);

    // ZADD key score member
    redisReply* reply = (redisReply*)redisCommand(
        impl_->context(),
        "ZADD %s %f %s",
        key.c_str(),
        timestamp,
        value.c_str()
    );

    if (!reply) {
        throw std::runtime_error("Redis ZADD failed");
    }
    freeReplyObject(reply);

    // Set TTL if configured
    if (ttl_ > 0) {
        reply = (redisReply*)redisCommand(
            impl_->context(),
            "EXPIRE %s %lld",
            key.c_str(),
            static_cast<long long>(ttl_)
        );

        if (reply) {
            freeReplyObject(reply);
        }
    }
#else
    (void)session_id;
    (void)role;
    (void)content;
    (void)metadata;
    throw std::runtime_error("Redis support not enabled");
#endif
}

std::vector<RedisMessage> RedisMemory::retrieve(
    const std::string& session_id,
    size_t limit,
    const std::optional<std::pair<double, double>>& time_range,
    const std::optional<double>& importance_threshold,
    const std::optional<std::vector<std::string>>& tags
) {
#ifdef AGENKIT_WITH_REDIS
    std::string key = session_key(session_id);

    // ZREVRANGE key 0 -1 WITHSCORES (most recent first)
    redisReply* reply = (redisReply*)redisCommand(
        impl_->context(),
        "ZREVRANGE %s 0 -1 WITHSCORES",
        key.c_str()
    );

    if (!reply) {
        throw std::runtime_error("Redis ZREVRANGE failed");
    }

    if (reply->type != REDIS_REPLY_ARRAY) {
        freeReplyObject(reply);
        return {};
    }

    std::vector<RedisMessage> filtered;

    // Process pairs of (value, score)
    for (size_t i = 0; i + 1 < reply->elements; i += 2) {
        try {
            std::string data = reply->element[i]->str;
            double timestamp = std::stod(reply->element[i + 1]->str);

            auto [message, metadata] = deserialize_message(data);

            // Time range filter
            if (time_range) {
                if (timestamp < time_range->first || timestamp > time_range->second) {
                    continue;
                }
            }

            // Importance threshold filter
            if (importance_threshold) {
                double importance = 0.0;
                auto it = metadata.find("importance");
                if (it != metadata.end() && it->second.is_number()) {
                    importance = it->second.get<double>();
                }
                if (importance < *importance_threshold) {
                    continue;
                }
            }

            // Tags filter (any match)
            if (tags && !tags->empty()) {
                bool has_tag = false;
                auto it = metadata.find("tags");
                if (it != metadata.end() && it->second.is_array()) {
                    for (const auto& tag : *tags) {
                        for (const auto& msg_tag : it->second) {
                            if (msg_tag.is_string() && msg_tag.get<std::string>() == tag) {
                                has_tag = true;
                                break;
                            }
                        }
                        if (has_tag) break;
                    }
                }
                if (!has_tag) {
                    continue;
                }
            }

            filtered.push_back(message);

            if (filtered.size() >= limit) {
                break;
            }
        } catch (...) {
            // Skip malformed messages
            continue;
        }
    }

    freeReplyObject(reply);
    return filtered;
#else
    (void)session_id;
    (void)limit;
    (void)time_range;
    (void)importance_threshold;
    (void)tags;
    throw std::runtime_error("Redis support not enabled");
#endif
}

RedisMessage RedisMemory::summarize(const std::string& session_id) {
    auto messages = retrieve(session_id, 100);

    if (messages.empty()) {
        return RedisMessage{"system", "No messages in session."};
    }

    std::ostringstream summary;
    summary << "Session summary (" << messages.size() << " messages):\n";

    size_t max_messages = std::min(messages.size(), size_t(10));
    for (size_t i = 0; i < max_messages; ++i) {
        const auto& msg = messages[i];
        std::string preview = msg.content;
        if (preview.length() > 100) {
            preview = preview.substr(0, 100) + "...";
        }
        summary << (i + 1) << ". [" << msg.role << "] " << preview << "\n";
    }

    return RedisMessage{"system", summary.str()};
}

void RedisMemory::clear(const std::string& session_id) {
#ifdef AGENKIT_WITH_REDIS
    std::string key = session_key(session_id);

    redisReply* reply = (redisReply*)redisCommand(
        impl_->context(),
        "DEL %s",
        key.c_str()
    );

    if (reply) {
        freeReplyObject(reply);
    }
#else
    (void)session_id;
    throw std::runtime_error("Redis support not enabled");
#endif
}

size_t RedisMemory::get_session_count(const std::string& session_id) {
#ifdef AGENKIT_WITH_REDIS
    std::string key = session_key(session_id);

    redisReply* reply = (redisReply*)redisCommand(
        impl_->context(),
        "ZCARD %s",
        key.c_str()
    );

    if (!reply || reply->type != REDIS_REPLY_INTEGER) {
        if (reply) freeReplyObject(reply);
        return 0;
    }

    size_t count = reply->integer;
    freeReplyObject(reply);
    return count;
#else
    (void)session_id;
    throw std::runtime_error("Redis support not enabled");
#endif
}

std::vector<std::string> RedisMemory::get_all_sessions() {
#ifdef AGENKIT_WITH_REDIS
    std::string pattern = key_prefix_ + ":*:messages";

    redisReply* reply = (redisReply*)redisCommand(
        impl_->context(),
        "KEYS %s",
        pattern.c_str()
    );

    if (!reply || reply->type != REDIS_REPLY_ARRAY) {
        if (reply) freeReplyObject(reply);
        return {};
    }

    std::vector<std::string> sessions;
    for (size_t i = 0; i < reply->elements; ++i) {
        std::string key = reply->element[i]->str;
        // Extract session_id from key
        // Format: "agenkit:memory:{session_id}:messages"
        size_t last_colon = key.rfind(':');
        if (last_colon != std::string::npos) {
            size_t second_last_colon = key.rfind(':', last_colon - 1);
            if (second_last_colon != std::string::npos) {
                std::string session_id = key.substr(
                    second_last_colon + 1,
                    last_colon - second_last_colon - 1
                );
                sessions.push_back(session_id);
            }
        }
    }

    freeReplyObject(reply);
    return sessions;
#else
    throw std::runtime_error("Redis support not enabled");
#endif
}

std::tuple<size_t, size_t, int64_t> RedisMemory::get_memory_usage() {
    auto sessions = get_all_sessions();
    size_t total_messages = 0;

    for (const auto& session_id : sessions) {
        total_messages += get_session_count(session_id);
    }

    return {sessions.size(), total_messages, ttl_};
}

std::vector<std::string> RedisMemory::capabilities() {
    return {
        "basic_retrieval",
        "persistence",
        "ttl",
        "time_filtering",
        "importance_filtering",
        "tag_filtering"
    };
}

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
