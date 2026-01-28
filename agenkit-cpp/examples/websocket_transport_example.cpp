/**
 * @file websocket_transport_example.cpp
 * @brief Example of using WebSocket transport for real-time agent communication
 *
 * This example demonstrates how to use the WebSocketAgent to communicate with
 * a remote agent server over WebSocket protocol for real-time bidirectional
 * communication.
 *
 * Prerequisites:
 * 1. Build agenkit with WebSocket support:
 *    cmake -DAGENKIT_WITH_WEBSOCKET=ON ..
 * 2. Start a WebSocket agent server (see server examples in other languages)
 * 3. Run this example
 *
 * Features demonstrated:
 * - Basic WebSocket connection
 * - Secure WebSocket (wss://)
 * - Automatic reconnection
 * - Keep-alive ping/pong
 * - Real-time messaging
 * - Custom headers
 */

#include <iostream>
#include <thread>
#include <chrono>
#include <agenkit/transports/websocket_agent.hpp>
#include <agenkit/core/message.hpp>

using namespace agenkit;
using namespace agenkit::transports;

void basic_websocket_example() {
    std::cout << "\n=== Basic WebSocket Example ===" << std::endl;

    // Check if WebSocket support is available
    if (!WebSocketAgent::is_available()) {
        std::cout << "WebSocket transport not available." << std::endl;
        std::cout << "Rebuild with: cmake -DAGENKIT_WITH_WEBSOCKET=ON .." << std::endl;
        return;
    }

    try {
        // Configure WebSocket transport
        WebSocketConfig config{
            "ws://localhost:8080",  // url
            5,                      // max_retries
            1000,                   // initial_retry_delay_ms
            30000,                  // max_retry_delay_ms
            30,                     // ping_interval_secs
            10,                     // ping_timeout_secs
            10,                     // connect_timeout_secs
            30                      // request_timeout_secs
        };

        // Create WebSocket agent
        WebSocketAgent agent("ws-remote", config);

        std::cout << "Connected to WebSocket server at " << config.url << std::endl;
        std::cout << "Connected: " << (agent.is_connected() ? "Yes" : "No") << std::endl;

        // Create a message
        auto message = core::Message::with_text("user", "Hello via WebSocket!");

        // Send message and get response
        std::cout << "Sending message: " << message.content() << std::endl;

        auto future = agent.process(std::move(message));
        auto result = future.get();

        if (result.is_ok()) {
            auto response = result.unwrap();
            std::cout << "Response from agent: " << response.content() << std::endl;
        } else {
            auto error = result.unwrap_err();
            std::cout << "Error: " << error.message() << std::endl;
        }

        // Show capabilities
        std::cout << "\nAgent capabilities:" << std::endl;
        for (const auto& cap : agent.capabilities()) {
            std::cout << "  - " << cap << std::endl;
        }

        // Test ping
        std::cout << "\nTesting keep-alive ping..." << std::endl;
        bool ping_ok = agent.ping();
        std::cout << "Ping successful: " << (ping_ok ? "Yes" : "No") << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

void secure_websocket_example() {
    std::cout << "\n=== Secure WebSocket (wss://) Example ===" << std::endl;

    if (!WebSocketAgent::is_available()) {
        std::cout << "WebSocket transport not available." << std::endl;
        return;
    }

    try {
        // Configure secure WebSocket with TLS
        WebSocketConfig config{
            "wss://api.example.com",  // url with wss:// scheme
            10,                       // max_retries (more for production)
            1000,                     // initial_retry_delay_ms
            30000,                    // max_retry_delay_ms
            60,                       // ping_interval_secs (longer for production)
            15,                       // ping_timeout_secs
            15,                       // connect_timeout_secs
            60                        // request_timeout_secs (longer for complex requests)
        };

        // Create secure WebSocket agent
        WebSocketAgent agent("secure-ws-remote", config);

        std::cout << "Connected to secure WebSocket server at " << config.url << std::endl;

        // Use the agent (same as basic example)
        auto message = core::Message::with_text("user", "Secure message via WebSocket");
        auto future = agent.process(std::move(message));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Response: " << result.unwrap().content() << std::endl;
        } else {
            std::cout << "Error: " << result.unwrap_err().message() << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

void custom_headers_example() {
    std::cout << "\n=== WebSocket with Custom Headers Example ===" << std::endl;

    if (!WebSocketAgent::is_available()) {
        std::cout << "WebSocket transport not available." << std::endl;
        return;
    }

    try {
        // Configure WebSocket with custom headers
        WebSocketConfig config;
        config.url = "ws://localhost:8080";
        config.max_retries = 5;
        config.initial_retry_delay_ms = 1000;
        config.ping_interval_secs = 30;

        // Add custom headers for authentication or other purposes
        config.headers["Authorization"] = "Bearer your-token-here";
        config.headers["X-Client-Version"] = "1.0.0";
        config.headers["X-Custom-Header"] = "custom-value";

        WebSocketAgent agent("ws-with-auth", config);

        std::cout << "Connected with custom headers" << std::endl;

        auto message = core::Message::with_text("user", "Authenticated request");
        auto future = agent.process(std::move(message));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Response: " << result.unwrap().content() << std::endl;
        } else {
            std::cout << "Error: " << result.unwrap_err().message() << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

void reconnection_example() {
    std::cout << "\n=== Automatic Reconnection Example ===" << std::endl;

    if (!WebSocketAgent::is_available()) {
        std::cout << "WebSocket transport not available." << std::endl;
        return;
    }

    try {
        WebSocketConfig config{
            "ws://localhost:8080",
            5,      // max_retries
            1000,   // initial_retry_delay_ms (1 second)
            30000,  // max_retry_delay_ms (30 seconds)
            30,     // ping_interval_secs
            10,     // ping_timeout_secs
            10,     // connect_timeout_secs
            30      // request_timeout_secs
        };

        WebSocketAgent agent("ws-remote", config);

        std::cout << "Initial connection status: "
                  << (agent.is_connected() ? "Connected" : "Disconnected")
                  << std::endl;

        // Simulate connection loss and reconnection
        std::cout << "\nSimulating connection loss..." << std::endl;
        std::cout << "Attempting manual reconnection..." << std::endl;

        bool reconnected = agent.reconnect();
        std::cout << "Reconnection " << (reconnected ? "successful" : "failed") << std::endl;

        if (reconnected) {
            // Try sending a message after reconnection
            auto message = core::Message::with_text("user", "Message after reconnection");
            auto future = agent.process(std::move(message));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Response: " << result.unwrap().content() << std::endl;
            }
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

void realtime_conversation_example() {
    std::cout << "\n=== Real-time Conversation Example ===" << std::endl;

    if (!WebSocketAgent::is_available()) {
        std::cout << "WebSocket transport not available." << std::endl;
        return;
    }

    try {
        WebSocketConfig config{
            "ws://localhost:8080",
            5,
            1000,
            30000,
            30
        };

        WebSocketAgent agent("ws-remote", config);

        // Real-time multi-turn conversation
        std::vector<std::string> messages = {
            "Hello!",
            "How are you?",
            "Tell me a joke",
            "Thanks, that was funny!",
            "Goodbye!"
        };

        for (const auto& msg : messages) {
            std::cout << "\nUser: " << msg << std::endl;

            auto message = core::Message::with_text("user", msg);
            auto future = agent.process(std::move(message));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Agent: " << result.unwrap().content() << std::endl;
            } else {
                std::cout << "Error: " << result.unwrap_err().message() << std::endl;
                break;
            }

            // Small delay between messages for more natural conversation
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

int main() {
    std::cout << "Agenkit C++ - WebSocket Transport Examples" << std::endl;
    std::cout << "===========================================" << std::endl;

    // Run examples
    basic_websocket_example();
    secure_websocket_example();
    custom_headers_example();
    reconnection_example();
    realtime_conversation_example();

    std::cout << "\n=== Setup Instructions ===" << std::endl;
    std::cout << "1. Install a WebSocket library:" << std::endl;
    std::cout << "   Option A (websocketpp): vcpkg install websocketpp boost-asio" << std::endl;
    std::cout << "   Option B (ixwebsocket): vcpkg install ixwebsocket" << std::endl;
    std::cout << "   Option C: Use cpp-httplib (already included)" << std::endl;
    std::cout << "\n2. Rebuild agenkit with WebSocket support:" << std::endl;
    std::cout << "   cmake -DAGENKIT_WITH_WEBSOCKET=ON .." << std::endl;
    std::cout << "   make" << std::endl;
    std::cout << "\n3. Start a WebSocket server (Python example):" << std::endl;
    std::cout << "   cd ../agenkit" << std::endl;
    std::cout << "   python examples/websocket_server_example.py" << std::endl;
    std::cout << "\n4. Run this example:" << std::endl;
    std::cout << "   ./websocket_transport_example" << std::endl;

    return 0;
}
