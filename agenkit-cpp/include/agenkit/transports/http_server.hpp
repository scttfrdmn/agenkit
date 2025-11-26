/**
 * @file http_server.hpp
 * @brief HTTP server for exposing agents via HTTP
 */

#ifndef AGENKIT_TRANSPORTS_HTTP_SERVER_HPP
#define AGENKIT_TRANSPORTS_HTTP_SERVER_HPP

#include "agenkit/core/agent.hpp"
#include <string>
#include <memory>
#include <atomic>

// Forward declare to avoid including httplib in header
namespace httplib {
class Server;
}

namespace agenkit {
namespace transports {

/**
 * @brief HTTP server for exposing agents via REST API
 *
 * Wraps a local agent and exposes it via HTTP endpoints:
 * - POST /process - Process a message
 * - GET /health - Health check
 *
 * @example
 * @code
 * auto agent = std::make_shared<EchoAgent>();
 * HttpServer server(agent, "127.0.0.1:8080");
 *
 * // Run in background thread
 * std::thread server_thread([&]() {
 *     server.serve();
 * });
 *
 * // Later: stop server
 * server.stop();
 * server_thread.join();
 * @endcode
 */
class HttpServer {
public:
    /**
     * @brief Construct HTTP server
     * @param agent Agent to expose via HTTP
     * @param address Address to bind (e.g., "127.0.0.1:8080" or "0.0.0.0:8080")
     */
    HttpServer(std::shared_ptr<core::Agent> agent, std::string address);

    /**
     * @brief Destructor (stops server if running)
     */
    ~HttpServer();

    /**
     * @brief Start serving (blocking)
     *
     * This method blocks until stop() is called from another thread.
     */
    void serve();

    /**
     * @brief Stop server (thread-safe)
     *
     * Can be called from any thread to stop a running server.
     */
    void stop();

    /**
     * @brief Check if server is running
     * @return true if serving, false otherwise
     */
    bool is_running() const;

private:
    std::shared_ptr<core::Agent> agent_;
    std::string host_;
    int port_;
    std::unique_ptr<httplib::Server> server_;
    std::atomic<bool> running_;

    // Parse address into host and port
    void parse_address(const std::string& address);

    // Route handlers (defined in .cpp to avoid httplib header dependency)
    void handle_process(void* req, void* res);
    void handle_health(void* req, void* res);
};

} // namespace transports
} // namespace agenkit

#endif // AGENKIT_TRANSPORTS_HTTP_SERVER_HPP
