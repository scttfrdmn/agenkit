/**
 * @file http_transport.cpp
 * @brief Example demonstrating HTTP client/server communication
 *
 * This example shows how to:
 * - Start an HTTP server exposing an agent
 * - Create an HTTP client to communicate with the server
 * - Send messages and receive responses
 */

#include <iostream>
#include <thread>
#include <chrono>
#include "agenkit/adapters/echo_agent.hpp"
#include "agenkit/transports/http_server.hpp"
#include "agenkit/transports/http_agent.hpp"

using namespace agenkit;

void run_server() {
    std::cout << "[Server] Starting server..." << std::endl;

    // Create echo agent
    auto agent = std::make_shared<adapters::EchoAgent>();

    // Create HTTP server
    transports::HttpServer server(agent, "127.0.0.1:8080");

    std::cout << "[Server] Listening on http://127.0.0.1:8080" << std::endl;
    std::cout << "[Server] Endpoints:" << std::endl;
    std::cout << "[Server]   POST /process - Process messages" << std::endl;
    std::cout << "[Server]   GET  /health  - Health check" << std::endl;
    std::cout << std::endl;

    // Serve (blocking)
    server.serve();

    std::cout << "[Server] Stopped" << std::endl;
}

void run_client() {
    std::cout << "[Client] Waiting for server to start..." << std::endl;

    // Wait for server to start
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    std::cout << "[Client] Connecting to server..." << std::endl;

    // Create HTTP client
    transports::HttpTransportConfig config{
        "http://127.0.0.1:8080",
        30,
        std::nullopt
    };

    transports::HttpAgent client("remote-agent", config);

    std::cout << "[Client] Connected to: " << client.name() << std::endl;
    std::cout << "[Client] Capabilities: ";
    for (const auto& cap : client.capabilities()) {
        std::cout << cap << " ";
    }
    std::cout << std::endl << std::endl;

    // Send multiple messages
    std::vector<std::string> messages = {
        "Hello, server!",
        "How are you?",
        "This is message 3",
        "Testing HTTP transport",
        "Final message"
    };

    for (size_t i = 0; i < messages.size(); i++) {
        std::cout << "[Client] Sending message " << (i + 1) << ": \""
                  << messages[i] << "\"" << std::endl;

        auto msg = core::Message::with_text("user", messages[i]);
        msg.with_metadata("example", "http_transport")
           .with_metadata("message_id", static_cast<int>(i + 1));

        auto future = client.process(std::move(msg));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "[Client] Response: \"" << response.content_as_str() << "\""
                      << std::endl;
        } else {
            auto error = result.unwrap_err();
            std::cerr << "[Client] Error: " << error.message() << std::endl;
        }

        std::cout << std::endl;

        // Small delay between messages
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    std::cout << "[Client] All messages sent successfully!" << std::endl;
    std::cout << "[Client] Press Ctrl+C to stop server..." << std::endl;
}

int main() {
    std::cout << "=== Agenkit C++ HTTP Transport Example ===" << std::endl;
    std::cout << std::endl;

    // Start server in background thread
    std::thread server_thread(run_server);

    // Run client in main thread
    run_client();

    // In a real application, you'd have a proper shutdown mechanism
    // For this example, server will be terminated with Ctrl+C

    server_thread.detach();  // Detach server thread

    return 0;
}
