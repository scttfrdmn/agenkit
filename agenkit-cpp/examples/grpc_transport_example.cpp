/**
 * @file grpc_transport_example.cpp
 * @brief Example of using gRPC transport for remote agent communication
 *
 * This example demonstrates how to use the GrpcAgent to communicate with
 * a remote agent server over gRPC protocol.
 *
 * Prerequisites:
 * 1. Build agenkit with gRPC support:
 *    cmake -DAGENKIT_WITH_GRPC=ON ..
 * 2. Start a gRPC agent server (see server examples in other languages)
 * 3. Run this example
 *
 * Features demonstrated:
 * - Basic gRPC connection
 * - TLS configuration
 * - Request/response pattern
 * - Error handling
 * - Timeout configuration
 */

#include <iostream>
#include <agenkit/transports/grpc_agent.hpp>
#include <agenkit/core/message.hpp>

using namespace agenkit;
using namespace agenkit::transports;

void basic_grpc_example() {
    std::cout << "\n=== Basic gRPC Example ===" << std::endl;

    // Check if gRPC support is available
    if (!GrpcAgent::is_available()) {
        std::cout << "gRPC transport not available." << std::endl;
        std::cout << "Rebuild with: cmake -DAGENKIT_WITH_GRPC=ON .." << std::endl;
        return;
    }

    try {
        // Configure gRPC transport
        GrpcConfig config{
            "localhost:50051",     // url
            false,                 // use_tls
            std::nullopt,         // ca_cert
            std::nullopt,         // client_cert
            std::nullopt,         // client_key
            30,                   // timeout_secs
            10,                   // connect_timeout_secs
            30,                   // keepalive_interval_secs
            4 * 1024 * 1024       // max_message_size (4MB)
        };

        // Create gRPC agent
        GrpcAgent agent("grpc-remote", config);

        std::cout << "Connected to gRPC server at " << config.url << std::endl;

        // Create a message
        auto message = core::Message::with_text("user", "Hello via gRPC!");

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

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

void secure_grpc_example() {
    std::cout << "\n=== Secure gRPC (TLS) Example ===" << std::endl;

    if (!GrpcAgent::is_available()) {
        std::cout << "gRPC transport not available." << std::endl;
        return;
    }

    try {
        // Configure secure gRPC with TLS
        GrpcConfig config{
            "api.example.com:443",           // url
            true,                            // use_tls
            "/path/to/ca.pem",              // ca_cert
            "/path/to/client.pem",          // client_cert (for mTLS)
            "/path/to/client.key",          // client_key (for mTLS)
            60,                             // timeout_secs (longer for production)
            15,                             // connect_timeout_secs
            60,                             // keepalive_interval_secs
            8 * 1024 * 1024                 // max_message_size (8MB)
        };

        // Create secure gRPC agent
        GrpcAgent agent("secure-grpc-remote", config);

        std::cout << "Connected to secure gRPC server at " << config.url << std::endl;

        // Use the agent (same as basic example)
        auto message = core::Message::with_text("user", "Secure message via gRPC");
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

void conversation_example() {
    std::cout << "\n=== Multi-turn Conversation via gRPC ===" << std::endl;

    if (!GrpcAgent::is_available()) {
        std::cout << "gRPC transport not available." << std::endl;
        return;
    }

    try {
        GrpcConfig config{
            "localhost:50051",
            false,
            std::nullopt,
            std::nullopt,
            std::nullopt,
            30
        };

        GrpcAgent agent("grpc-remote", config);

        // Multi-turn conversation
        std::vector<std::string> questions = {
            "What is 2 + 2?",
            "What about 10 + 5?",
            "Can you explain the previous answer?"
        };

        for (const auto& question : questions) {
            std::cout << "\nUser: " << question << std::endl;

            auto message = core::Message::with_text("user", question);
            auto future = agent.process(std::move(message));
            auto result = future.get();

            if (result.is_ok()) {
                std::cout << "Agent: " << result.unwrap().content() << std::endl;
            } else {
                std::cout << "Error: " << result.unwrap_err().message() << std::endl;
                break;
            }
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

void timeout_example() {
    std::cout << "\n=== Timeout Configuration Example ===" << std::endl;

    if (!GrpcAgent::is_available()) {
        std::cout << "gRPC transport not available." << std::endl;
        return;
    }

    try {
        // Short timeout for testing
        GrpcConfig config{
            "localhost:50051",
            false,
            std::nullopt,
            std::nullopt,
            std::nullopt,
            5,  // 5 second timeout
            3   // 3 second connect timeout
        };

        GrpcAgent agent("grpc-remote", config);

        auto message = core::Message::with_text("user", "This might timeout");
        auto future = agent.process(std::move(message));
        auto result = future.get();

        if (result.is_ok()) {
            std::cout << "Response: " << result.unwrap().content() << std::endl;
        } else {
            auto error = result.unwrap_err();
            std::cout << "Error (expected for timeout test): " << error.message() << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

int main() {
    std::cout << "Agenkit C++ - gRPC Transport Examples" << std::endl;
    std::cout << "======================================" << std::endl;

    // Run examples
    basic_grpc_example();
    secure_grpc_example();
    conversation_example();
    timeout_example();

    std::cout << "\n=== Setup Instructions ===" << std::endl;
    std::cout << "1. Install gRPC C++ library:" << std::endl;
    std::cout << "   vcpkg install grpc" << std::endl;
    std::cout << "   # or on macOS: brew install grpc" << std::endl;
    std::cout << "\n2. Rebuild agenkit with gRPC support:" << std::endl;
    std::cout << "   cmake -DAGENKIT_WITH_GRPC=ON .." << std::endl;
    std::cout << "   make" << std::endl;
    std::cout << "\n3. Start a gRPC server (Python example):" << std::endl;
    std::cout << "   cd ../agenkit" << std::endl;
    std::cout << "   python examples/grpc_server_example.py" << std::endl;
    std::cout << "\n4. Run this example:" << std::endl;
    std::cout << "   ./grpc_transport_example" << std::endl;

    return 0;
}
