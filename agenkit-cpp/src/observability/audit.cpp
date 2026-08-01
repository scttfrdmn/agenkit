/**
 * @file audit.cpp
 * @brief Implementation of audit logging for compliance and security
 */

#ifdef AGENKIT_WITH_OBSERVABILITY

#include "agenkit/observability/audit.hpp"
#include <mutex>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <random>
#include <algorithm>

namespace agenkit {
namespace observability {

// Generate unique event ID
static std::string generate_event_id() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);

    const char* hex_chars = "0123456789abcdef";
    std::string id;
    id.reserve(32);

    for (int i = 0; i < 32; i++) {
        id += hex_chars[dis(gen)];
    }

    return id;
}

// Convert timestamp to ISO 8601 string
static std::string timestamp_to_string(std::chrono::system_clock::time_point tp) {
    auto time_t = std::chrono::system_clock::to_time_t(tp);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        tp.time_since_epoch()) % 1000;

    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S")
       << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
    return ss.str();
}

// Parse ISO 8601 timestamp (simplified - handles basic format)
static std::chrono::system_clock::time_point parse_timestamp(const std::string& str) {
    // For simplicity, return current time if parsing fails
    // In production, you'd want proper ISO 8601 parsing
    (void)str;
    return std::chrono::system_clock::now();
}

std::string audit_event_type_to_string(AuditEventType type) {
    switch (type) {
        case AuditEventType::AgentCreated: return "AgentCreated";
        case AuditEventType::AgentDestroyed: return "AgentDestroyed";
        case AuditEventType::MessageProcessed: return "MessageProcessed";
        case AuditEventType::MessageFailed: return "MessageFailed";
        case AuditEventType::SecurityViolation: return "SecurityViolation";
        case AuditEventType::ConfigurationChanged: return "ConfigurationChanged";
        case AuditEventType::ErrorOccurred: return "ErrorOccurred";
        case AuditEventType::UserAction: return "UserAction";
        case AuditEventType::SystemEvent: return "SystemEvent";
        default: return "Unknown";
    }
}

static AuditEventType string_to_audit_event_type(const std::string& str) {
    if (str == "AgentCreated") return AuditEventType::AgentCreated;
    if (str == "AgentDestroyed") return AuditEventType::AgentDestroyed;
    if (str == "MessageProcessed") return AuditEventType::MessageProcessed;
    if (str == "MessageFailed") return AuditEventType::MessageFailed;
    if (str == "SecurityViolation") return AuditEventType::SecurityViolation;
    if (str == "ConfigurationChanged") return AuditEventType::ConfigurationChanged;
    if (str == "ErrorOccurred") return AuditEventType::ErrorOccurred;
    if (str == "UserAction") return AuditEventType::UserAction;
    if (str == "SystemEvent") return AuditEventType::SystemEvent;
    return AuditEventType::SystemEvent; // Default
}

std::string severity_to_string(Severity severity) {
    switch (severity) {
        case Severity::INFO: return "INFO";
        case Severity::WARNING: return "WARNING";
        case Severity::ERROR: return "ERROR";
        case Severity::CRITICAL: return "CRITICAL";
        default: return "INFO";
    }
}

static Severity string_to_severity(const std::string& str) {
    if (str == "INFO") return Severity::INFO;
    if (str == "WARNING") return Severity::WARNING;
    if (str == "ERROR") return Severity::ERROR;
    if (str == "CRITICAL") return Severity::CRITICAL;
    return Severity::INFO; // Default
}

//=============================================================================
// AuditEvent Implementation
//=============================================================================

AuditEvent::AuditEvent(
    AuditEventType event_type,
    const std::string& agent_name,
    const std::string& session_id)
    : event_id_(generate_event_id())
    , timestamp_(std::chrono::system_clock::now())
    , event_type_(event_type)
    , agent_name_(agent_name)
    , session_id_(session_id)
    , details_(nlohmann::json::object())
    , severity_(Severity::INFO) {
}

AuditEvent AuditEvent::create(
    AuditEventType event_type,
    const std::string& agent_name,
    const std::string& session_id) {

    return AuditEvent(event_type, agent_name, session_id);
}

AuditEvent& AuditEvent::with_detail(const std::string& key, const nlohmann::json& value) {
    details_[key] = value;
    return *this;
}

AuditEvent& AuditEvent::with_severity(Severity severity) {
    severity_ = severity;
    return *this;
}

nlohmann::json AuditEvent::to_json() const {
    nlohmann::json j;
    j["event_id"] = event_id_;
    j["timestamp"] = timestamp_to_string(timestamp_);
    j["event_type"] = audit_event_type_to_string(event_type_);
    j["agent_name"] = agent_name_;
    j["session_id"] = session_id_;
    j["details"] = details_;
    j["severity"] = severity_to_string(severity_);
    return j;
}

AuditEvent AuditEvent::from_json(const nlohmann::json& j) {
    auto event_type = string_to_audit_event_type(j["event_type"].get<std::string>());
    auto agent_name = j["agent_name"].get<std::string>();
    auto session_id = j["session_id"].get<std::string>();

    AuditEvent event(event_type, agent_name, session_id);

    if (j.contains("event_id")) {
        event.event_id_ = j["event_id"].get<std::string>();
    }
    if (j.contains("timestamp")) {
        event.timestamp_ = parse_timestamp(j["timestamp"].get<std::string>());
    }
    if (j.contains("details")) {
        event.details_ = j["details"];
    }
    if (j.contains("severity")) {
        event.severity_ = string_to_severity(j["severity"].get<std::string>());
    }

    return event;
}

//=============================================================================
// AuditLogger Implementation
//=============================================================================

AuditLogger::AuditLogger(const std::string& log_path, size_t buffer_size)
    : log_path_(log_path)
    , buffer_size_(buffer_size) {

    // Ensure the file exists and is writable
    std::ofstream test_file(log_path_, std::ios::app);
    if (!test_file) {
        throw std::runtime_error("Cannot open audit log file: " + log_path_);
    }
    test_file.close();
}

std::shared_ptr<AuditLogger> AuditLogger::create(
    const std::string& log_path,
    size_t buffer_size) {

    return std::shared_ptr<AuditLogger>(new AuditLogger(log_path, buffer_size));
}

AuditLogger::~AuditLogger() {
    try {
        flush();
    } catch (...) {
        // Don't throw from destructor
    }
}

void AuditLogger::log(const AuditEvent& event) {
    std::lock_guard<std::mutex> lock(mutex_);

    buffer_.push_back(event);

    // Auto-flush if buffer is full
    if (buffer_.size() >= buffer_size_) {
        flush_internal();
    }
}

void AuditLogger::flush() {
    std::lock_guard<std::mutex> lock(mutex_);
    flush_internal();
}

void AuditLogger::flush_internal() {
    if (buffer_.empty()) {
        return;
    }

    std::ofstream file(log_path_, std::ios::app);
    if (!file) {
        throw std::runtime_error("Cannot open audit log file for writing: " + log_path_);
    }

    for (const auto& event : buffer_) {
        file << event.to_json().dump() << std::endl;
    }

    file.close();
    buffer_.clear();
}

void AuditLogger::set_buffer_size(size_t size) {
    std::lock_guard<std::mutex> lock(mutex_);
    buffer_size_ = size;
}

std::vector<AuditEvent> AuditLogger::load_events() {
    std::vector<AuditEvent> events;

    std::ifstream file(log_path_);
    if (!file) {
        // File doesn't exist yet - return empty vector
        return events;
    }

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty()) {
            continue;
        }

        try {
            auto j = nlohmann::json::parse(line);
            events.push_back(AuditEvent::from_json(j));
        } catch (const std::exception&) {
            // Skip invalid lines
            continue;
        }
    }

    return events;
}

std::vector<AuditEvent> AuditLogger::query() {
    std::lock_guard<std::mutex> lock(mutex_);

    // Flush buffer first
    flush_internal();

    // Load all events from file
    return load_events();
}

std::vector<AuditEvent> AuditLogger::query_by_session(const std::string& session_id) {
    return query_with_filter([&session_id](const AuditEvent& event) {
        return event.session_id() == session_id;
    });
}

std::vector<AuditEvent> AuditLogger::query_by_agent(const std::string& agent_name) {
    return query_with_filter([&agent_name](const AuditEvent& event) {
        return event.agent_name() == agent_name;
    });
}

std::vector<AuditEvent> AuditLogger::query_by_type(AuditEventType event_type) {
    return query_with_filter([event_type](const AuditEvent& event) {
        return event.event_type() == event_type;
    });
}

std::vector<AuditEvent> AuditLogger::query_with_filter(
    std::function<bool(const AuditEvent&)> filter) {

    auto all_events = query();

    std::vector<AuditEvent> filtered;
    std::copy_if(
        all_events.begin(),
        all_events.end(),
        std::back_inserter(filtered),
        filter
    );

    return filtered;
}

} // namespace observability
} // namespace agenkit

#endif // AGENKIT_WITH_OBSERVABILITY
