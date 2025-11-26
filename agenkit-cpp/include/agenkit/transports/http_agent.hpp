/**
 * @file http_agent.hpp
 * @brief HTTP client for remote agent communication
 */

#ifndef AGENKIT_TRANSPORTS_HTTP_AGENT_HPP
#define AGENKIT_TRANSPORTS_HTTP_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include <string>
#include <optional>
#include <memory>

// Forward declare to avoid including httplib in header
namespace httplib {
class Client;
}

namespace agenkit {
namespace transports {

/**
 * @brief Configuration for HTTP transport
 */
struct HttpTransportConfig {
    std::string base_url;           ///< Base URL (e.g., "http://localhost:8080")
    int timeout_secs = 30;          ///< Request timeout in seconds
    std::optional<std::string> api_key;  ///< Optional API key for authentication
};

/**
 * @brief HTTP client agent for communicating with remote agents
 *
 * Wraps a remote agent accessible via HTTP, providing the same Agent
 * interface as local agents.
 *
 * @example
 * @code
 * HttpTransportConfig config{
 *     "http://localhost:8080",
 *     30,
 *     std::nullopt
 * };
 * HttpAgent client("remote", config);
 * auto msg = Message::with_text("user", "Hello!");
 * auto result = client.process(std::move(msg)).get();
 * @endcode
 */
class HttpAgent : public core::Agent {
public:
    /**
     * @brief Construct HTTP client agent
     * @param name Agent name
     * @param config HTTP transport configuration
     */
    HttpAgent(std::string name, HttpTransportConfig config);

    /**
     * @brief Destructor
     */
    ~HttpAgent() override;

    /**
     * @brief Get agent name
     * @return Agent name
     */
    std::string name() const override;

    /**
     * @brief Process message via HTTP
     * @param message Input message
     * @return Future with result
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get capabilities (may query remote)
     * @return Capabilities list
     */
    std::vector<std::string> capabilities() const override;

private:
    std::string name_;
    HttpTransportConfig config_;
    std::unique_ptr<httplib::Client> client_;

    // Initialize HTTP client
    void init_client();
};

} // namespace transports
} // namespace agenkit

#endif // AGENKIT_TRANSPORTS_HTTP_AGENT_HPP
