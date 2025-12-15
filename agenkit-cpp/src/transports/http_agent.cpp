/**
 * @file http_agent.cpp
 * @brief Implementation of HTTP client agent
 */

#include "agenkit/transports/http_agent.hpp"
#include <httplib.h>
#include <stdexcept>

namespace agenkit {
namespace transports {

// ============================================================================
// HttpConnectionPool Implementation
// ============================================================================

HttpConnectionPool& HttpConnectionPool::instance() {
    static HttpConnectionPool pool;
    return pool;
}

std::shared_ptr<httplib::Client> HttpConnectionPool::acquire(
    const std::string& base_url,
    const HttpTransportConfig& config
) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Check if we have an available connection in the pool
    auto& pool = pools_[base_url];
    if (!pool.empty()) {
        auto client = pool.back();
        pool.pop_back();
        return client;
    }

    // No available connection - create a new one
    auto client = std::make_shared<httplib::Client>(base_url);

    // Configure timeouts
    client->set_read_timeout(config.timeout_secs, 0);
    client->set_write_timeout(config.timeout_secs, 0);

    // Enable keep-alive for connection reuse
    if (config.keep_alive) {
        client->set_keep_alive(true);
    }

    // Set API key header if provided
    if (config.api_key) {
        client->set_default_headers({
            {"Authorization", "Bearer " + *config.api_key}
        });
    }

    // Track pool size for this host
    if (pool_sizes_.find(base_url) == pool_sizes_.end()) {
        pool_sizes_[base_url] = config.pool_size;
    }

    return client;
}

void HttpConnectionPool::release(
    const std::string& base_url,
    std::shared_ptr<httplib::Client> client
) {
    if (!client) {
        return;
    }

    std::lock_guard<std::mutex> lock(mutex_);

    auto& pool = pools_[base_url];
    int max_size = pool_sizes_[base_url];

    // Only return to pool if we haven't exceeded max size
    if (static_cast<int>(pool.size()) < max_size) {
        pool.push_back(client);
    }
    // Otherwise let the shared_ptr delete the client
}

// ============================================================================
// HttpAgent Implementation
// ============================================================================


HttpAgent::HttpAgent(std::string name, HttpTransportConfig config)
    : name_(std::move(name))
    , config_(std::move(config))
    , client_(nullptr)
{
    init_client();
}

HttpAgent::~HttpAgent() {
    cleanup_client();
}

void HttpAgent::init_client() {
    // Validate URL format
    std::string url = config_.base_url;
    bool is_https = (url.find("https://") == 0);
    bool is_http = (url.find("http://") == 0);

    if (!is_https && !is_http) {
        throw std::invalid_argument("URL must start with http:// or https://");
    }

    // Remove trailing slash if present
    if (!url.empty() && url.back() == '/') {
        url.pop_back();
        config_.base_url = url;
    }

    // Acquire connection from pool
    client_ = HttpConnectionPool::instance().acquire(config_.base_url, config_);
}

void HttpAgent::cleanup_client() {
    if (client_) {
        // Return connection to pool for reuse
        HttpConnectionPool::instance().release(config_.base_url, client_);
        client_ = nullptr;
    }
}

std::string HttpAgent::name() const {
    return name_;
}

std::future<core::Result<core::Message, core::AgentError>>
HttpAgent::process(core::Message message) {
    // Serialize message to JSON
    nlohmann::json request_body = {
        {"message", message.to_json()}
    };

    // Make HTTP POST request
    auto res = client_->Post("/process",
                            request_body.dump(),
                            "application/json");

    // Check for HTTP errors
    if (!res) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Transport,
                    "HTTP request failed: connection error"
                )
            )
        );
    }

    if (res->status != 200) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Http,
                    "HTTP error: " + std::to_string(res->status)
                )
            )
        );
    }

    // Parse response
    try {
        nlohmann::json response_json = nlohmann::json::parse(res->body);

        if (!response_json.contains("message")) {
            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(
                        core::AgentErrorType::Serialization,
                        "Response missing 'message' field"
                    )
                )
            );
        }

        auto response_msg = core::Message::from_json(response_json["message"]);

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::ok(
                std::move(response_msg)
            )
        );

    } catch (const nlohmann::json::exception& e) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Serialization,
                    std::string("JSON parse error: ") + e.what()
                )
            )
        );
    } catch (const std::exception& e) {
        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(
                    core::AgentErrorType::Internal,
                    std::string("Internal error: ") + e.what()
                )
            )
        );
    }
}

std::vector<std::string> HttpAgent::capabilities() const {
    // Could query /capabilities endpoint in the future
    return {"http", "remote"};
}

} // namespace transports
} // namespace agenkit
