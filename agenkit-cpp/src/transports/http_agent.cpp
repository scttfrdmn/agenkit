/**
 * @file http_agent.cpp
 * @brief Implementation of HTTP client agent
 */

#include "agenkit/transports/http_agent.hpp"
#include <httplib.h>
#include <stdexcept>

namespace agenkit {
namespace transports {

HttpAgent::HttpAgent(std::string name, HttpTransportConfig config)
    : name_(std::move(name))
    , config_(std::move(config))
    , client_(nullptr)
{
    init_client();
}

HttpAgent::~HttpAgent() = default;

void HttpAgent::init_client() {
    // Parse URL to extract scheme, host, port
    std::string url = config_.base_url;

    // Simple URL parsing (assumes http:// or https://)
    bool is_https = (url.find("https://") == 0);
    std::string prefix = is_https ? "https://" : "http://";

    if (url.find(prefix) != 0) {
        throw std::invalid_argument("URL must start with http:// or https://");
    }

    std::string host_port = url.substr(prefix.length());

    // Remove trailing slash if present
    if (!host_port.empty() && host_port.back() == '/') {
        host_port.pop_back();
    }

    // Create client (httplib handles scheme internally)
    client_ = std::make_unique<httplib::Client>(url);

    // Set timeout
    client_->set_read_timeout(config_.timeout_secs, 0);
    client_->set_write_timeout(config_.timeout_secs, 0);

    // Set API key header if provided
    if (config_.api_key) {
        client_->set_default_headers({
            {"Authorization", "Bearer " + *config_.api_key}
        });
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
