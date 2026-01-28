/**
 * @file websocket_agent.hpp
 * @brief WebSocket client for remote agent communication
 *
 * Provides real-time bidirectional communication with automatic reconnection
 * and keep-alive mechanisms.
 *
 * Features:
 * - Real-time bidirectional communication
 * - Automatic reconnection with exponential backoff
 * - Ping/pong keep-alive
 * - Request/response correlation
 * - Binary and text frames
 * - TLS support (wss://)
 *
 * Example:
 * @code
 * WebSocketConfig config{
 *     "ws://localhost:8080",
 *     5,      // max_retries
 *     1000,   // initial_retry_delay_ms
 *     30,     // ping_interval_secs
 * };
 * WebSocketAgent client("remote", config);
 * auto msg = Message::with_text("user", "Hello!");
 * auto result = client.process(std::move(msg)).get();
 * @endcode
 *
 * TLS Configuration:
 * @code
 * WebSocketConfig config{
 *     "wss://api.example.com",
 *     5,
 *     1000,
 *     30,
 * };
 * WebSocketAgent client("secure-remote", config);
 * @endcode
 *
 * Implementation Notes:
 *
 * This is a stub implementation showing the API design.
 *
 * Full implementation requires:
 * 1. Add WebSocket library dependency to CMakeLists.txt
 *    Options: websocketpp, ixwebsocket, or cpp-httplib WebSocket support
 * 2. Implement WebSocket client with reconnection logic
 * 3. Add message framing with request IDs for correlation
 * 4. Implement ping/pong keep-alive mechanism
 * 5. Handle concurrent requests with futures
 * 6. Implement TLS support for wss://
 *
 * Dependencies needed in CMakeLists.txt:
 * ```cmake
 * # Option 1: websocketpp (header-only, boost-based)
 * find_package(websocketpp CONFIG)
 * find_package(Boost REQUIRED COMPONENTS system)
 *
 * # Option 2: ixwebsocket (standalone, no boost)
 * find_package(ixwebsocket CONFIG)
 *
 * # Option 3: cpp-httplib already has WebSocket support
 * # (already included for HTTP transport)
 * ```
 */

#ifndef AGENKIT_TRANSPORTS_WEBSOCKET_AGENT_HPP
#define AGENKIT_TRANSPORTS_WEBSOCKET_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include <string>
#include <optional>
#include <memory>
#include <vector>
#include <map>
#include <mutex>
#include <atomic>

namespace agenkit {
namespace transports {

/**
 * @brief Configuration for WebSocket transport
 */
struct WebSocketConfig {
    std::string url;                        ///< WebSocket URL (ws:// or wss://)
    size_t max_retries = 5;                 ///< Maximum reconnection attempts
    uint64_t initial_retry_delay_ms = 1000; ///< Initial retry delay in milliseconds
    uint64_t max_retry_delay_ms = 30000;    ///< Maximum retry delay in milliseconds
    int ping_interval_secs = 30;            ///< Ping interval in seconds
    int ping_timeout_secs = 10;             ///< Ping timeout in seconds
    int connect_timeout_secs = 10;          ///< Connection timeout in seconds
    int request_timeout_secs = 30;          ///< Request timeout in seconds
    std::map<std::string, std::string> headers; ///< Custom headers for connection
};

/**
 * @brief WebSocket client agent for communicating with remote agents
 *
 * Wraps a remote agent accessible via WebSocket, providing the same Agent
 * interface as local agents with real-time bidirectional communication.
 *
 * Connection Management:
 * - Automatic reconnection with exponential backoff
 * - Keep-alive ping/pong mechanism
 * - Request/response correlation using request IDs
 *
 * @example
 * @code
 * WebSocketConfig config{
 *     "ws://localhost:8080",
 *     5,      // max_retries
 *     1000,   // initial_retry_delay_ms
 *     30,     // ping_interval_secs
 * };
 * WebSocketAgent client("remote", config);
 * auto msg = Message::with_text("user", "Hello!");
 * auto result = client.process(std::move(msg)).get();
 * @endcode
 *
 * Secure WebSocket:
 * @code
 * WebSocketConfig config{
 *     "wss://api.example.com",
 *     10,     // max_retries for production
 *     1000,
 *     60,     // longer ping interval
 * };
 * WebSocketAgent client("secure-remote", config);
 * @endcode
 *
 * Custom Headers:
 * @code
 * WebSocketConfig config;
 * config.url = "ws://localhost:8080";
 * config.headers["Authorization"] = "Bearer token123";
 * config.headers["X-Custom-Header"] = "value";
 * WebSocketAgent client("remote", config);
 * @endcode
 */
class WebSocketAgent : public core::Agent {
public:
    /**
     * @brief Construct WebSocket client agent
     * @param name Agent name
     * @param config WebSocket transport configuration
     * @throws std::runtime_error if WebSocket support not compiled in
     */
    WebSocketAgent(std::string name, WebSocketConfig config);

    /**
     * @brief Destructor
     */
    ~WebSocketAgent() override;

    /**
     * @brief Get agent name
     * @return Agent name
     */
    std::string name() const override;

    /**
     * @brief Process message via WebSocket
     * @param message Input message
     * @return Future with result
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get capabilities
     * @return Capabilities list including "websocket", "bidirectional", "realtime", "streaming"
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Check if WebSocket is connected
     * @return true if connected, false otherwise
     */
    bool is_connected() const;

    /**
     * @brief Manually reconnect to WebSocket server
     *
     * Automatically called on connection failure with exponential backoff.
     * @return true if reconnection successful, false otherwise
     */
    bool reconnect();

    /**
     * @brief Send a ping frame to keep connection alive
     *
     * Automatically called by ping task every ping_interval seconds.
     * @return true if ping successful, false otherwise
     */
    bool ping();

    /**
     * @brief Check if WebSocket support is available
     * @return true if compiled with AGENKIT_WITH_WEBSOCKET, false otherwise
     */
    static bool is_available();

private:
    std::string name_;
    WebSocketConfig config_;
    std::atomic<bool> connected_;

#ifdef AGENKIT_WITH_WEBSOCKET
    // Full implementation would include:
    // std::unique_ptr<WebSocketClient> client_;
    // std::map<std::string, std::promise<core::Message>> pending_requests_;
    // std::mutex pending_mutex_;
    // std::thread ping_thread_;
    // std::thread receive_thread_;
    // std::atomic<bool> should_stop_;

    void init_connection();
    void start_ping_task();
    void start_receive_loop();
    void handle_message(const std::string& data);
    void handle_disconnect();
    std::string generate_request_id();
#endif
};

} // namespace transports
} // namespace agenkit

#endif // AGENKIT_TRANSPORTS_WEBSOCKET_AGENT_HPP
