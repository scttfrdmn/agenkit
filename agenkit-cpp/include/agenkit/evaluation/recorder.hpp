/**
 * @file recorder.hpp
 * @brief Session recording for agent replay and analysis
 *
 * This module provides session recording capabilities for agents:
 * - Record all agent interactions (inputs, outputs, timing)
 * - Store recordings to file or memory
 * - Replay sessions through different agent versions (A/B testing)
 * - Compare replay results
 *
 * Key use cases:
 * - Production monitoring and debugging
 * - A/B testing new agent versions
 * - Regression testing
 * - Performance analysis
 *
 * @example
 * @code
 * auto storage = std::make_shared<FileRecordingStorage>("./recordings");
 * auto recorder = SessionRecorder(storage);
 *
 * // Wrap agent for automatic recording
 * auto wrapped_agent = recorder.wrap(agent);
 *
 * // Use agent normally (automatically recorded)
 * auto result = wrapped_agent->process(message).get();
 *
 * // Save recording
 * recorder.finalize_session("test-123");
 * @endcode
 */

#ifndef AGENKIT_EVALUATION_RECORDER_HPP
#define AGENKIT_EVALUATION_RECORDER_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include <string>
#include <vector>
#include <memory>
#include <unordered_map>
#include <optional>
#include <chrono>
#include <nlohmann/json.hpp>

namespace agenkit {
namespace evaluation {

/**
 * @brief Record of a single agent interaction
 *
 * Contains input, output, timing, and metadata for one interaction.
 */
class InteractionRecord {
public:
    /**
     * @brief Create an interaction record
     * @param interaction_id Unique interaction identifier
     * @param session_id Session identifier
     * @param input_message Input message as JSON
     * @param output_message Output message as JSON
     * @param timestamp Timestamp of interaction
     * @param latency_ms Processing latency in milliseconds
     * @param metadata Optional metadata
     */
    InteractionRecord(
        std::string interaction_id,
        std::string session_id,
        nlohmann::json input_message,
        nlohmann::json output_message,
        std::chrono::system_clock::time_point timestamp,
        double latency_ms,
        nlohmann::json metadata = nlohmann::json::object()
    );

    /// Get interaction ID
    const std::string& interaction_id() const { return interaction_id_; }

    /// Get session ID
    const std::string& session_id() const { return session_id_; }

    /// Get input message
    const nlohmann::json& input_message() const { return input_message_; }

    /// Get output message
    const nlohmann::json& output_message() const { return output_message_; }

    /// Get timestamp
    std::chrono::system_clock::time_point timestamp() const { return timestamp_; }

    /// Get latency in milliseconds
    double latency_ms() const { return latency_ms_; }

    /// Get metadata
    const nlohmann::json& metadata() const { return metadata_; }

    /**
     * @brief Convert to dictionary representation
     * @return JSON object
     */
    nlohmann::json to_dict() const;

    /**
     * @brief Create from dictionary representation
     * @param data JSON object
     * @return InteractionRecord instance
     */
    static InteractionRecord from_dict(const nlohmann::json& data);

private:
    std::string interaction_id_;
    std::string session_id_;
    nlohmann::json input_message_;
    nlohmann::json output_message_;
    std::chrono::system_clock::time_point timestamp_;
    double latency_ms_;
    nlohmann::json metadata_;
};

/**
 * @brief Recording of an entire session
 *
 * Contains all interactions and session metadata.
 */
class SessionRecording {
public:
    /**
     * @brief Default constructor (needed for std::unordered_map)
     */
    SessionRecording() = default;

    /**
     * @brief Create a session recording
     * @param session_id Session identifier
     * @param agent_name Name of agent being recorded
     * @param start_time Session start time
     * @param metadata Optional session metadata
     */
    SessionRecording(
        std::string session_id,
        std::string agent_name,
        std::chrono::system_clock::time_point start_time,
        nlohmann::json metadata = nlohmann::json::object()
    );

    /// Get session ID
    const std::string& session_id() const { return session_id_; }

    /// Get agent name
    const std::string& agent_name() const { return agent_name_; }

    /// Get start time
    std::chrono::system_clock::time_point start_time() const { return start_time_; }

    /// Get end time (if session has ended)
    std::optional<std::chrono::system_clock::time_point> end_time() const { return end_time_; }

    /// Set end time
    void set_end_time(std::chrono::system_clock::time_point end_time) { end_time_ = end_time; }

    /// Get interactions
    const std::vector<InteractionRecord>& interactions() const { return interactions_; }

    /// Add an interaction
    void add_interaction(const InteractionRecord& interaction);

    /// Get metadata
    const nlohmann::json& metadata() const { return metadata_; }

    /// Get mutable metadata
    nlohmann::json& metadata() { return metadata_; }

    /**
     * @brief Calculate session duration in seconds
     * @return Duration in seconds, or 0.0 if not ended
     */
    double duration_seconds() const;

    /**
     * @brief Get number of interactions
     * @return Interaction count
     */
    size_t interaction_count() const { return interactions_.size(); }

    /**
     * @brief Get total latency across all interactions
     * @return Total latency in milliseconds
     */
    double total_latency_ms() const;

    /**
     * @brief Convert to dictionary representation
     * @return JSON object
     */
    nlohmann::json to_dict() const;

    /**
     * @brief Create from dictionary representation
     * @param data JSON object
     * @return SessionRecording instance
     */
    static SessionRecording from_dict(const nlohmann::json& data);

private:
    std::string session_id_;
    std::string agent_name_;
    std::chrono::system_clock::time_point start_time_;
    std::optional<std::chrono::system_clock::time_point> end_time_;
    std::vector<InteractionRecord> interactions_;
    nlohmann::json metadata_;
};

/**
 * @brief Interface for recording storage backends
 *
 * Implement this to create custom storage (Redis, S3, Postgres, etc.).
 *
 * @details
 * All implementations should be thread-safe if they will be accessed
 * from multiple threads.
 */
class RecordingStorage {
public:
    virtual ~RecordingStorage() = default;

    /**
     * @brief Save a recording
     * @param recording Recording to save
     */
    virtual void save_recording(const SessionRecording& recording) = 0;

    /**
     * @brief Load a recording by session ID
     * @param session_id Session ID to load
     * @return Recording if found, nullopt otherwise
     */
    virtual std::optional<SessionRecording> load_recording(const std::string& session_id) = 0;

    /**
     * @brief List recordings with pagination
     * @param limit Maximum number to return
     * @param offset Number to skip
     * @return Vector of recordings
     */
    virtual std::vector<SessionRecording> list_recordings(size_t limit, size_t offset) = 0;

    /**
     * @brief Delete a recording
     * @param session_id Session ID to delete
     */
    virtual void delete_recording(const std::string& session_id) = 0;
};

/**
 * @brief File-based recording storage
 *
 * Stores recordings as JSON files on disk.
 */
class FileRecordingStorage : public RecordingStorage {
public:
    /**
     * @brief Create file storage
     * @param recordings_dir Directory to store recordings (default: "./recordings")
     */
    explicit FileRecordingStorage(std::string recordings_dir = "./recordings");

    void save_recording(const SessionRecording& recording) override;
    std::optional<SessionRecording> load_recording(const std::string& session_id) override;
    std::vector<SessionRecording> list_recordings(size_t limit, size_t offset) override;
    void delete_recording(const std::string& session_id) override;

private:
    std::string recordings_dir_;
};

/**
 * @brief In-memory recording storage for testing
 *
 * Does not persist recordings across restarts.
 */
class InMemoryRecordingStorage : public RecordingStorage {
public:
    InMemoryRecordingStorage() = default;

    void save_recording(const SessionRecording& recording) override;
    std::optional<SessionRecording> load_recording(const std::string& session_id) override;
    std::vector<SessionRecording> list_recordings(size_t limit, size_t offset) override;
    void delete_recording(const std::string& session_id) override;

private:
    std::unordered_map<std::string, SessionRecording> recordings_;
};

/**
 * @brief Records agent sessions for replay and analysis
 *
 * Automatically records all interactions with an agent,
 * storing inputs, outputs, timing, and metadata.
 *
 * @example
 * @code
 * auto storage = std::make_shared<FileRecordingStorage>("./recordings");
 * auto recorder = SessionRecorder(storage);
 *
 * // Wrap agent
 * auto wrapped = recorder.wrap(agent);
 *
 * // Use normally (automatically recorded)
 * auto response = wrapped->process(message).get();
 *
 * // Finalize session
 * recorder.finalize_session("test-123");
 * @endcode
 */
class SessionRecorder {
public:
    /**
     * @brief Create a session recorder
     * @param storage Storage backend (nullptr = in-memory)
     */
    explicit SessionRecorder(std::shared_ptr<RecordingStorage> storage = nullptr);

    /**
     * @brief Wrap an agent to record interactions
     * @param agent Agent to wrap
     * @return Wrapped agent that records all interactions
     */
    std::shared_ptr<core::Agent> wrap(std::shared_ptr<core::Agent> agent);

    /**
     * @brief Start recording a session
     * @param session_id Session identifier
     * @param agent_name Name of agent being recorded
     * @param metadata Optional session metadata
     */
    void start_session(const std::string& session_id, const std::string& agent_name,
                      const nlohmann::json& metadata = nlohmann::json::object());

    /**
     * @brief Record a single interaction
     * @param session_id Session identifier
     * @param input_message Input to agent
     * @param output_message Agent response
     * @param latency_ms Processing time in milliseconds
     * @param metadata Optional interaction metadata
     */
    void record_interaction(const std::string& session_id,
                           const core::Message& input_message,
                           const core::Message& output_message,
                           double latency_ms,
                           const nlohmann::json& metadata = nlohmann::json::object());

    /**
     * @brief Finalize and save a session recording
     * @param session_id Session to finalize
     * @return Session recording
     */
    SessionRecording finalize_session(const std::string& session_id);

    /**
     * @brief Load a recording from storage
     * @param session_id Session ID to load
     * @return Recording if found, nullopt otherwise
     */
    std::optional<SessionRecording> load_recording(const std::string& session_id);

    /**
     * @brief List all recordings
     * @param limit Maximum number to return
     * @param offset Number to skip
     * @return Vector of recordings
     */
    std::vector<SessionRecording> list_recordings(size_t limit, size_t offset);

    /**
     * @brief Delete a recording
     * @param session_id Session ID to delete
     */
    void delete_recording(const std::string& session_id);

private:
    std::shared_ptr<RecordingStorage> storage_;
    std::unordered_map<std::string, SessionRecording> active_sessions_;

    // Forward declaration for wrapper
    class RecordingWrapper;
};

/**
 * @brief Replays recorded sessions for analysis and A/B testing
 *
 * Takes a recorded session and replays it through a (possibly different)
 * agent to compare behavior.
 *
 * @example
 * @code
 * auto replay = SessionReplay();
 * auto recording = recorder.load_recording("test-123");
 *
 * // Replay with original agent
 * auto results_a = replay.replay(*recording, agent_v1);
 *
 * // Replay with new agent (A/B test)
 * auto results_b = replay.replay(*recording, agent_v2);
 *
 * // Compare
 * auto comparison = replay.compare(results_a, results_b);
 * @endcode
 */
class SessionReplay {
public:
    SessionReplay() = default;

    /**
     * @brief Replay a session through an agent
     * @param recording Session recording to replay
     * @param agent Agent to replay through
     * @param session_id Optional session ID (defaults to original)
     * @return Replay results with outputs and metrics
     */
    nlohmann::json replay(const SessionRecording& recording,
                         std::shared_ptr<core::Agent> agent,
                         const std::string& session_id = "");

    /**
     * @brief Compare two replay results
     * @param results_a First replay results
     * @param results_b Second replay results
     * @return Comparison metrics
     *
     * Useful for A/B testing different agent versions.
     */
    nlohmann::json compare(const nlohmann::json& results_a,
                          const nlohmann::json& results_b);
};

} // namespace evaluation
} // namespace agenkit

#endif // AGENKIT_EVALUATION_RECORDER_HPP
