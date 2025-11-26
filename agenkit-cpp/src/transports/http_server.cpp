/**
 * @file http_server.cpp
 * @brief Implementation of HTTP server
 */

#include "agenkit/transports/http_server.hpp"
#include <httplib.h>
#include <sstream>
#include <stdexcept>

namespace agenkit {
namespace transports {

HttpServer::HttpServer(std::shared_ptr<core::Agent> agent, std::string address)
    : agent_(std::move(agent))
    , port_(8080)
    , server_(std::make_unique<httplib::Server>())
    , running_(false)
{
    if (!agent_) {
        throw std::invalid_argument("agent cannot be null");
    }

    parse_address(address);

    // Set up routes
    server_->Post("/process", [this](const httplib::Request& req, httplib::Response& res) {
        handle_process(req, res);
    });

    server_->Get("/health", [this](const httplib::Request& req, httplib::Response& res) {
        handle_health(req, res);
    });
}

HttpServer::~HttpServer() {
    if (running_) {
        stop();
    }
}

void HttpServer::parse_address(const std::string& address) {
    // Parse "host:port" format
    size_t colon_pos = address.find(':');

    if (colon_pos == std::string::npos) {
        throw std::invalid_argument("address must be in format 'host:port'");
    }

    host_ = address.substr(0, colon_pos);

    try {
        port_ = std::stoi(address.substr(colon_pos + 1));
    } catch (const std::exception&) {
        throw std::invalid_argument("invalid port number");
    }

    if (port_ < 1 || port_ > 65535) {
        throw std::invalid_argument("port must be between 1 and 65535");
    }
}

void HttpServer::serve() {
    running_ = true;

    // Listen and serve (blocking)
    if (!server_->listen(host_.c_str(), port_)) {
        running_ = false;
        throw std::runtime_error("failed to start HTTP server");
    }

    running_ = false;
}

void HttpServer::stop() {
    if (running_) {
        server_->stop();
        running_ = false;
    }
}

bool HttpServer::is_running() const {
    return running_;
}

void HttpServer::handle_process(const httplib::Request& req, httplib::Response& res) {
    try {
        // Parse request body
        nlohmann::json request_json = nlohmann::json::parse(req.body);

        if (!request_json.contains("message")) {
            res.status = 400;
            res.set_content("{\"error\":\"missing 'message' field\"}", "application/json");
            return;
        }

        // Deserialize message
        auto message = core::Message::from_json(request_json["message"]);

        // Process with agent
        auto future = agent_->process(std::move(message));
        auto result = future.get();

        if (result.is_ok()) {
            // Success - return message
            auto response_msg = result.unwrap();
            nlohmann::json response_json = {
                {"message", response_msg.to_json()}
            };

            res.status = 200;
            res.set_content(response_json.dump(), "application/json");
        } else {
            // Error - return error details
            auto error = result.unwrap_err();
            nlohmann::json error_json = {
                {"error", error.message()},
                {"type", core::to_string(error.type())}
            };

            res.status = 500;
            res.set_content(error_json.dump(), "application/json");
        }

    } catch (const nlohmann::json::exception& e) {
        res.status = 400;
        nlohmann::json error_json = {
            {"error", std::string("JSON parse error: ") + e.what()}
        };
        res.set_content(error_json.dump(), "application/json");
    } catch (const std::exception& e) {
        res.status = 500;
        nlohmann::json error_json = {
            {"error", std::string("Internal error: ") + e.what()}
        };
        res.set_content(error_json.dump(), "application/json");
    }
}

void HttpServer::handle_health(const httplib::Request& /* req */, httplib::Response& res) {
    nlohmann::json health_json = {
        {"status", "ok"},
        {"agent", agent_->name()}
    };

    res.status = 200;
    res.set_content(health_json.dump(), "application/json");
}

} // namespace transports
} // namespace agenkit
