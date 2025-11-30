/**
 * @file recorder.cpp
 * @brief Implementation of session recording for agent replay and analysis
 */

#include "agenkit/evaluation/recorder.hpp"
#include <fstream>
#include <filesystem>
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <random>

namespace agenkit {
namespace evaluation {

// Helper functions (same as metrics.cpp)
static std::string time_point_to_rfc3339(std::chrono::system_clock::time_point tp) {
    auto time_t_value = std::chrono::system_clock::to_time_t(tp);
    std::tm tm_value = *std::gmtime(&time_t_value);

    std::ostringstream oss;
    oss << std::put_time(&tm_value, "%Y-%m-%dT%H:%M:%S");

    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        tp.time_since_epoch()
    ) % 1000;
    oss << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';

    return oss.str();
}

static std::chrono::system_clock::time_point rfc3339_to_time_point(const std::string& str) {
    std::tm tm_value = {};
    std::istringstream iss(str);
    iss >> std::get_time(&tm_value, "%Y-%m-%dT%H:%M:%S");

    auto tp = std::chrono::system_clock::from_time_t(std::mktime(&tm_value));

    size_t dot_pos = str.find('.');
    if (dot_pos != std::string::npos) {
        size_t end_pos = str.find('Z', dot_pos);
        if (end_pos != std::string::npos) {
            std::string ms_str = str.substr(dot_pos + 1, end_pos - dot_pos - 1);
            int ms = std::stoi(ms_str);
            tp += std::chrono::milliseconds(ms);
        }
    }

    return tp;
}

static std::string generate_uuid() {
    static std::random_device rd;
    static std::mt19937 gen(rd());
    static std::uniform_int_distribution<> dis(0, 15);
    static std::uniform_int_distribution<> dis2(8, 11);

    std::stringstream ss;
    ss << std::hex;
    for (int i = 0; i < 8; i++) {
        ss << dis(gen);
    }
    ss << "-";
    for (int i = 0; i < 4; i++) {
        ss << dis(gen);
    }
    ss << "-4";
    for (int i = 0; i < 3; i++) {
        ss << dis(gen);
    }
    ss << "-";
    ss << dis2(gen);
    for (int i = 0; i < 3; i++) {
        ss << dis(gen);
    }
    ss << "-";
    for (int i = 0; i < 12; i++) {
        ss << dis(gen);
    }
    return ss.str();
}

static nlohmann::json message_to_dict(const core::Message& msg) {
    return msg.to_json();
}

// InteractionRecord implementation

InteractionRecord::InteractionRecord(
    std::string interaction_id,
    std::string session_id,
    nlohmann::json input_message,
    nlohmann::json output_message,
    std::chrono::system_clock::time_point timestamp,
    double latency_ms,
    nlohmann::json metadata
)
    : interaction_id_(std::move(interaction_id))
    , session_id_(std::move(session_id))
    , input_message_(std::move(input_message))
    , output_message_(std::move(output_message))
    , timestamp_(timestamp)
    , latency_ms_(latency_ms)
    , metadata_(std::move(metadata))
{
}

nlohmann::json InteractionRecord::to_dict() const {
    nlohmann::json j;
    j["interaction_id"] = interaction_id_;
    j["session_id"] = session_id_;
    j["input_message"] = input_message_;
    j["output_message"] = output_message_;
    j["timestamp"] = time_point_to_rfc3339(timestamp_);
    j["latency_ms"] = latency_ms_;
    j["metadata"] = metadata_;
    return j;
}

InteractionRecord InteractionRecord::from_dict(const nlohmann::json& data) {
    return InteractionRecord(
        data["interaction_id"].get<std::string>(),
        data["session_id"].get<std::string>(),
        data["input_message"],
        data["output_message"],
        rfc3339_to_time_point(data["timestamp"].get<std::string>()),
        data["latency_ms"].get<double>(),
        data.value("metadata", nlohmann::json::object())
    );
}

// SessionRecording implementation

SessionRecording::SessionRecording(
    std::string session_id,
    std::string agent_name,
    std::chrono::system_clock::time_point start_time,
    nlohmann::json metadata
)
    : session_id_(std::move(session_id))
    , agent_name_(std::move(agent_name))
    , start_time_(start_time)
    , end_time_(std::nullopt)
    , metadata_(std::move(metadata))
{
}

void SessionRecording::add_interaction(const InteractionRecord& interaction) {
    interactions_.push_back(interaction);
}

double SessionRecording::duration_seconds() const {
    if (!end_time_.has_value()) {
        return 0.0;
    }

    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        *end_time_ - start_time_
    );
    return duration.count() / 1000000.0;
}

double SessionRecording::total_latency_ms() const {
    double total = 0.0;
    for (const auto& interaction : interactions_) {
        total += interaction.latency_ms();
    }
    return total;
}

nlohmann::json SessionRecording::to_dict() const {
    nlohmann::json j;
    j["session_id"] = session_id_;
    j["agent_name"] = agent_name_;
    j["start_time"] = time_point_to_rfc3339(start_time_);

    if (end_time_.has_value()) {
        j["end_time"] = time_point_to_rfc3339(*end_time_);
    } else {
        j["end_time"] = nullptr;
    }

    nlohmann::json interactions_json = nlohmann::json::array();
    for (const auto& interaction : interactions_) {
        interactions_json.push_back(interaction.to_dict());
    }
    j["interactions"] = interactions_json;

    j["metadata"] = metadata_;

    return j;
}

SessionRecording SessionRecording::from_dict(const nlohmann::json& data) {
    SessionRecording recording(
        data["session_id"].get<std::string>(),
        data["agent_name"].get<std::string>(),
        rfc3339_to_time_point(data["start_time"].get<std::string>()),
        data.value("metadata", nlohmann::json::object())
    );

    if (!data["end_time"].is_null()) {
        recording.end_time_ = rfc3339_to_time_point(data["end_time"].get<std::string>());
    }

    for (const auto& interaction_json : data["interactions"]) {
        recording.interactions_.push_back(InteractionRecord::from_dict(interaction_json));
    }

    return recording;
}

// FileRecordingStorage implementation

FileRecordingStorage::FileRecordingStorage(std::string recordings_dir)
    : recordings_dir_(std::move(recordings_dir))
{
    // Create directory if it doesn't exist
    std::filesystem::create_directories(recordings_dir_);
}

void FileRecordingStorage::save_recording(const SessionRecording& recording) {
    std::filesystem::path file_path = std::filesystem::path(recordings_dir_) /
                                     (recording.session_id() + ".json");

    std::ofstream file(file_path);
    if (!file.is_open()) {
        throw std::runtime_error("Failed to open file for writing: " + file_path.string());
    }

    file << recording.to_dict().dump(2);
}

std::optional<SessionRecording> FileRecordingStorage::load_recording(const std::string& session_id) {
    std::filesystem::path file_path = std::filesystem::path(recordings_dir_) /
                                     (session_id + ".json");

    if (!std::filesystem::exists(file_path)) {
        return std::nullopt;
    }

    std::ifstream file(file_path);
    if (!file.is_open()) {
        return std::nullopt;
    }

    nlohmann::json data;
    file >> data;

    return SessionRecording::from_dict(data);
}

std::vector<SessionRecording> FileRecordingStorage::list_recordings(size_t limit, size_t offset) {
    std::vector<SessionRecording> recordings;

    // Collect all JSON files with their modification times
    std::vector<std::pair<std::filesystem::path, std::filesystem::file_time_type>> files;

    for (const auto& entry : std::filesystem::directory_iterator(recordings_dir_)) {
        if (entry.path().extension() == ".json") {
            files.emplace_back(entry.path(), std::filesystem::last_write_time(entry.path()));
        }
    }

    // Sort by modification time (most recent first)
    std::sort(files.begin(), files.end(),
              [](const auto& a, const auto& b) { return a.second > b.second; });

    // Apply pagination
    size_t start = offset;
    size_t end = std::min(offset + limit, files.size());

    if (start >= files.size()) {
        return recordings;
    }

    // Load recordings
    for (size_t i = start; i < end; ++i) {
        std::ifstream file(files[i].first);
        if (file.is_open()) {
            nlohmann::json data;
            file >> data;
            recordings.push_back(SessionRecording::from_dict(data));
        }
    }

    return recordings;
}

void FileRecordingStorage::delete_recording(const std::string& session_id) {
    std::filesystem::path file_path = std::filesystem::path(recordings_dir_) /
                                     (session_id + ".json");

    if (std::filesystem::exists(file_path)) {
        std::filesystem::remove(file_path);
    }
}

// InMemoryRecordingStorage implementation

void InMemoryRecordingStorage::save_recording(const SessionRecording& recording) {
    recordings_[recording.session_id()] = recording;
}

std::optional<SessionRecording> InMemoryRecordingStorage::load_recording(const std::string& session_id) {
    auto it = recordings_.find(session_id);
    if (it != recordings_.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::vector<SessionRecording> InMemoryRecordingStorage::list_recordings(size_t limit, size_t offset) {
    std::vector<SessionRecording> recordings;
    for (const auto& pair : recordings_) {
        recordings.push_back(pair.second);
    }

    // Sort by start time (most recent first)
    std::sort(recordings.begin(), recordings.end(),
              [](const auto& a, const auto& b) {
                  return a.start_time() > b.start_time();
              });

    // Apply pagination
    size_t start = offset;
    size_t end = std::min(offset + limit, recordings.size());

    if (start >= recordings.size()) {
        return {};
    }

    return std::vector<SessionRecording>(recordings.begin() + start,
                                        recordings.begin() + end);
}

void InMemoryRecordingStorage::delete_recording(const std::string& session_id) {
    recordings_.erase(session_id);
}

// SessionRecorder::RecordingWrapper implementation

class SessionRecorder::RecordingWrapper : public core::Agent {
public:
    RecordingWrapper(std::shared_ptr<core::Agent> agent, SessionRecorder* recorder)
        : agent_(std::move(agent))
        , recorder_(recorder)
    {
    }

    std::string name() const override {
        return agent_->name();
    }

    std::vector<std::string> capabilities() const override {
        return agent_->capabilities();
    }

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override {
        // Extract session ID from metadata
        std::string session_id = "default";
        auto& metadata = message.metadata();
        if (metadata.contains("session_id") && metadata["session_id"].is_string()) {
            session_id = metadata["session_id"].get<std::string>();
        }

        // Start session if not already started
        if (recorder_->active_sessions_.find(session_id) == recorder_->active_sessions_.end()) {
            recorder_->start_session(session_id, agent_->name(), nlohmann::json::object());
        }

        // Process with timing
        auto start = std::chrono::high_resolution_clock::now();
        auto future = agent_->process(message);
        auto result = future.get();
        auto end = std::chrono::high_resolution_clock::now();

        auto latency = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

        // Record interaction (even if error)
        if (result.is_ok()) {
            recorder_->record_interaction(session_id, message, result.unwrap(),
                                         latency.count(), nlohmann::json::object());
        } else {
            // Record error case with empty output
            core::Message empty_output = core::Message::with_text("assistant", "");
            recorder_->record_interaction(session_id, message, empty_output,
                                         latency.count(), nlohmann::json::object());
        }

        return core::make_ready_future(std::move(result));
    }

private:
    std::shared_ptr<core::Agent> agent_;
    SessionRecorder* recorder_;
};

// SessionRecorder implementation

SessionRecorder::SessionRecorder(std::shared_ptr<RecordingStorage> storage)
    : storage_(storage ? storage : std::make_shared<InMemoryRecordingStorage>())
{
}

std::shared_ptr<core::Agent> SessionRecorder::wrap(std::shared_ptr<core::Agent> agent) {
    return std::make_shared<RecordingWrapper>(agent, this);
}

void SessionRecorder::start_session(const std::string& session_id, const std::string& agent_name,
                                   const nlohmann::json& metadata) {
    SessionRecording recording(session_id, agent_name, std::chrono::system_clock::now(), metadata);
    active_sessions_[session_id] = std::move(recording);
}

void SessionRecorder::record_interaction(const std::string& session_id,
                                        const core::Message& input_message,
                                        const core::Message& output_message,
                                        double latency_ms,
                                        const nlohmann::json& metadata) {
    auto it = active_sessions_.find(session_id);
    if (it == active_sessions_.end()) {
        start_session(session_id, "unknown", nlohmann::json::object());
        it = active_sessions_.find(session_id);
    }

    InteractionRecord record(
        generate_uuid(),
        session_id,
        message_to_dict(input_message),
        message_to_dict(output_message),
        std::chrono::system_clock::now(),
        latency_ms,
        metadata
    );

    it->second.add_interaction(record);
}

SessionRecording SessionRecorder::finalize_session(const std::string& session_id) {
    auto it = active_sessions_.find(session_id);
    if (it == active_sessions_.end()) {
        throw std::runtime_error("No active session: " + session_id);
    }

    SessionRecording recording = std::move(it->second);
    active_sessions_.erase(it);

    recording.set_end_time(std::chrono::system_clock::now());

    // Save to storage
    storage_->save_recording(recording);

    return recording;
}

std::optional<SessionRecording> SessionRecorder::load_recording(const std::string& session_id) {
    return storage_->load_recording(session_id);
}

std::vector<SessionRecording> SessionRecorder::list_recordings(size_t limit, size_t offset) {
    return storage_->list_recordings(limit, offset);
}

void SessionRecorder::delete_recording(const std::string& session_id) {
    storage_->delete_recording(session_id);
}

// SessionReplay implementation

nlohmann::json SessionReplay::replay(const SessionRecording& recording,
                                     std::shared_ptr<core::Agent> agent,
                                     const std::string& session_id) {
    std::string replay_session_id = session_id.empty() ? recording.session_id() : session_id;

    nlohmann::json results;
    results["session_id"] = replay_session_id;
    results["original_session_id"] = recording.session_id();
    results["interactions"] = nlohmann::json::array();
    results["total_latency_ms"] = 0.0;
    results["error_count"] = 0;

    for (const auto& interaction : recording.interactions()) {
        // Reconstruct input message
        auto input_msg = core::Message::from_json(interaction.input_message());

        // Replay through agent
        auto start = std::chrono::high_resolution_clock::now();
        auto future = agent->process(input_msg);
        auto result = future.get();
        auto end = std::chrono::high_resolution_clock::now();

        auto latency = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

        nlohmann::json interaction_result;
        interaction_result["input"] = interaction.input_message();
        interaction_result["original_output"] = interaction.output_message();

        if (result.is_err()) {
            results["error_count"] = results["error_count"].get<int>() + 1;
            interaction_result["error"] = result.unwrap_err().message();
        } else {
            interaction_result["replay_output"] = message_to_dict(result.unwrap());
            interaction_result["original_latency_ms"] = interaction.latency_ms();
            interaction_result["replay_latency_ms"] = static_cast<double>(latency.count());

            results["total_latency_ms"] = results["total_latency_ms"].get<double>() + latency.count();
        }

        results["interactions"].push_back(interaction_result);
    }

    return results;
}

nlohmann::json SessionReplay::compare(const nlohmann::json& results_a,
                                     const nlohmann::json& results_b) {
    const auto& interactions_a = results_a["interactions"];
    const auto& interactions_b = results_b["interactions"];

    double latency_a = results_a["total_latency_ms"].get<double>();
    double latency_b = results_b["total_latency_ms"].get<double>();

    double latency_diff_percent = 0.0;
    if (latency_a > 0) {
        latency_diff_percent = (latency_b - latency_a) / latency_a * 100.0;
    }

    nlohmann::json comparison;
    comparison["interaction_count"] = interactions_a.size();
    comparison["latency_diff_ms"] = latency_b - latency_a;
    comparison["latency_diff_percent"] = latency_diff_percent;
    comparison["error_diff"] = results_b["error_count"].get<int>() - results_a["error_count"].get<int>();
    comparison["output_differences"] = nlohmann::json::array();

    // Compare outputs
    for (size_t i = 0; i < std::min(interactions_a.size(), interactions_b.size()); ++i) {
        const auto& ia = interactions_a[i];
        const auto& ib = interactions_b[i];

        if (ia.contains("error") || ib.contains("error")) {
            continue;
        }

        std::string output_a = ia["replay_output"]["content"].get<std::string>();
        std::string output_b = ib["replay_output"]["content"].get<std::string>();

        if (output_a != output_b) {
            nlohmann::json diff;
            diff["interaction_index"] = i;
            diff["output_a"] = output_a;
            diff["output_b"] = output_b;
            comparison["output_differences"].push_back(diff);
        }
    }

    return comparison;
}

} // namespace evaluation
} // namespace agenkit
