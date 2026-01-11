#include "agenkit/infrastructure/memory/entry.hpp"
#include <algorithm>
#include <cctype>
#include <random>
#include <sstream>
#include <iomanip>

namespace agenkit {
namespace infrastructure {
namespace memory {

std::string MemoryEntry::generate_uuid() {
    // Simple UUID v4 generation
    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<uint64_t> dis;

    uint64_t a = dis(gen);
    uint64_t b = dis(gen);

    // Set version to 4
    b = (b & 0xFFFFFFFFFFFF0FFFULL) | 0x0000000000004000ULL;
    // Set variant to RFC4122
    b = (b & 0x3FFFFFFFFFFFFFFFULL) | 0x8000000000000000ULL;

    std::ostringstream oss;
    oss << std::hex << std::setfill('0')
        << std::setw(8) << (a >> 32)
        << "-"
        << std::setw(4) << ((a >> 16) & 0xFFFF)
        << "-"
        << std::setw(4) << (a & 0xFFFF)
        << "-"
        << std::setw(4) << (b >> 48)
        << "-"
        << std::setw(12) << (b & 0xFFFFFFFFFFFFULL);

    return oss.str();
}

std::string MemoryEntry::to_lowercase(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

MemoryEntry MemoryEntry::create(
    const std::string& content,
    const std::map<std::string, nlohmann::json>& metadata,
    double importance,
    const std::optional<std::string>& session_id
) {
    MemoryEntry entry;
    entry.id = generate_uuid();
    entry.content = content;
    entry.metadata = metadata;
    entry.timestamp = std::chrono::system_clock::now();
    entry.access_count = 0;
    entry.last_accessed = std::nullopt;
    entry.importance = std::clamp(importance, 0.0, 1.0);
    entry.session_id = session_id;
    return entry;
}

void MemoryEntry::record_access() {
    access_count++;
    last_accessed = std::chrono::system_clock::now();
}

bool MemoryEntry::is_expired(int64_t ttl_seconds) const {
    auto age = age_seconds();
    return age > ttl_seconds;
}

int64_t MemoryEntry::age_seconds() const {
    auto now = std::chrono::system_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::seconds>(now - timestamp);
    return duration.count();
}

double MemoryEntry::age_days() const {
    return static_cast<double>(age_seconds()) / 86400.0;
}

double MemoryEntry::calculate_relevance(const std::string& query) const {
    double score = 0.0;

    // Keyword matching (0.5 if found)
    std::string lower_content = to_lowercase(content);
    std::string lower_query = to_lowercase(query);
    if (lower_content.find(lower_query) != std::string::npos) {
        score += 0.5;
    }

    // Importance weight (0.0-0.3)
    score += importance * 0.3;

    // Recency weight (0.0-0.2)
    double days = age_days();
    double recency_factor = std::max(0.0, 1.0 - (days / 365.0));
    score += recency_factor * 0.2;

    return std::clamp(score, 0.0, 1.0);
}

nlohmann::json MemoryEntry::to_json() const {
    nlohmann::json j;
    j["id"] = id;
    j["content"] = content;
    j["metadata"] = nlohmann::json(metadata);
    j["timestamp"] = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()).count();
    j["access_count"] = access_count;

    if (last_accessed.has_value()) {
        j["last_accessed"] = std::chrono::duration_cast<std::chrono::milliseconds>(
            last_accessed.value().time_since_epoch()).count();
    } else {
        j["last_accessed"] = nullptr;
    }

    j["importance"] = importance;

    if (session_id.has_value()) {
        j["session_id"] = session_id.value();
    } else {
        j["session_id"] = nullptr;
    }

    return j;
}

MemoryEntry MemoryEntry::from_json(const nlohmann::json& j) {
    MemoryEntry entry;
    entry.id = j["id"].get<std::string>();
    entry.content = j["content"].get<std::string>();
    entry.metadata = j["metadata"].get<std::map<std::string, nlohmann::json>>();

    int64_t timestamp_ms = j["timestamp"].get<int64_t>();
    entry.timestamp = std::chrono::system_clock::time_point(
        std::chrono::milliseconds(timestamp_ms));

    entry.access_count = j["access_count"].get<size_t>();

    if (!j["last_accessed"].is_null()) {
        int64_t last_accessed_ms = j["last_accessed"].get<int64_t>();
        entry.last_accessed = std::chrono::system_clock::time_point(
            std::chrono::milliseconds(last_accessed_ms));
    } else {
        entry.last_accessed = std::nullopt;
    }

    entry.importance = j["importance"].get<double>();

    if (!j["session_id"].is_null()) {
        entry.session_id = j["session_id"].get<std::string>();
    } else {
        entry.session_id = std::nullopt;
    }

    return entry;
}

} // namespace memory
} // namespace infrastructure
} // namespace agenkit
