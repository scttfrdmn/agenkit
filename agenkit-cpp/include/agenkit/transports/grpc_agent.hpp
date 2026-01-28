/**
 * @file grpc_agent.hpp
 * @brief gRPC client for remote agent communication
 *
 * Provides efficient binary protocol communication using Protocol Buffers
 * over HTTP/2 with built-in streaming support.
 *
 * Features:
 * - Binary protocol with Protocol Buffers
 * - Bidirectional streaming
 * - HTTP/2 multiplexing
 * - TLS support
 * - Automatic reconnection
 * - Load balancing support
 *
 * Example:
 * @code
 * GrpcConfig config{
 *     "localhost:50051",
 *     false,  // use_tls
 *     {},     // ca_cert
 *     30,     // timeout_secs
 * };
 * GrpcAgent client("remote", config);
 * auto msg = Message::with_text("user", "Hello!");
 * auto result = client.process(std::move(msg)).get();
 * @endcode
 *
 * Implementation Notes:
 *
 * This is a stub implementation showing the API design.
 *
 * Full implementation requires:
 * 1. Add gRPC C++ library dependency to CMakeLists.txt
 * 2. Generate C++ code from proto/agent.proto using protoc
 * 3. Implement AgentServiceClient integration
 * 4. Add connection pooling and retry logic
 * 5. Implement TLS configuration
 *
 * Dependencies needed in CMakeLists.txt:
 * ```cmake
 * find_package(gRPC CONFIG REQUIRED)
 * find_package(Protobuf REQUIRED)
 * target_link_libraries(agenkit PRIVATE
 *     gRPC::grpc++
 *     gRPC::grpc++_reflection
 *     protobuf::libprotobuf
 * )
 * ```
 *
 * Proto compilation:
 * ```cmake
 * protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS ${CMAKE_SOURCE_DIR}/../proto/agent.proto)
 * grpc_generate_cpp(GRPC_SRCS GRPC_HDRS ${CMAKE_SOURCE_DIR}/../proto/agent.proto)
 * ```
 */

#ifndef AGENKIT_TRANSPORTS_GRPC_AGENT_HPP
#define AGENKIT_TRANSPORTS_GRPC_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include <string>
#include <optional>
#include <memory>
#include <vector>

// Forward declarations for gRPC types
#ifdef AGENKIT_WITH_GRPC
namespace grpc {
class Channel;
class ChannelCredentials;
class ChannelArguments;
}
namespace agent {
class AgentService;
}
#endif

namespace agenkit {
namespace transports {

/**
 * @brief Configuration for gRPC transport
 */
struct GrpcConfig {
    std::string url;                        ///< gRPC server URL (e.g., "localhost:50051")
    bool use_tls = false;                   ///< Enable TLS (grpcs://)
    std::optional<std::string> ca_cert;     ///< Path to CA certificate for TLS
    std::optional<std::string> client_cert; ///< Client certificate for mTLS
    std::optional<std::string> client_key;  ///< Client key for mTLS
    int timeout_secs = 30;                  ///< Request timeout in seconds
    int connect_timeout_secs = 10;          ///< Connection timeout in seconds
    int keepalive_interval_secs = 30;       ///< Keep-alive interval in seconds
    size_t max_message_size = 4 * 1024 * 1024; ///< Max message size (4MB)
};

/**
 * @brief gRPC client agent for communicating with remote agents
 *
 * Wraps a remote agent accessible via gRPC, providing the same Agent
 * interface as local agents.
 *
 * Protocol:
 * Uses the agent.proto definition with:
 * - Process(Request) -> Response - Single request/response
 * - ProcessStream(Request) -> stream StreamChunk - Server streaming
 * - BidirectionalStream(stream Request) -> stream Response - Bidirectional
 *
 * @example
 * @code
 * GrpcConfig config{
 *     "localhost:50051",
 *     false,  // use_tls
 *     std::nullopt,  // ca_cert
 *     std::nullopt,  // client_cert
 *     std::nullopt,  // client_key
 *     30,     // timeout_secs
 * };
 * GrpcAgent client("remote", config);
 * auto msg = Message::with_text("user", "Hello!");
 * auto result = client.process(std::move(msg)).get();
 * @endcode
 *
 * TLS Configuration:
 * @code
 * GrpcConfig config{
 *     "api.example.com:443",
 *     true,  // use_tls
 *     "/path/to/ca.pem",
 *     "/path/to/client.pem",
 *     "/path/to/client.key",
 *     60,    // timeout_secs
 * };
 * GrpcAgent client("secure-remote", config);
 * @endcode
 */
class GrpcAgent : public core::Agent {
public:
    /**
     * @brief Construct gRPC client agent
     * @param name Agent name
     * @param config gRPC transport configuration
     * @throws std::runtime_error if gRPC support not compiled in
     */
    GrpcAgent(std::string name, GrpcConfig config);

    /**
     * @brief Destructor
     */
    ~GrpcAgent() override;

    /**
     * @brief Get agent name
     * @return Agent name
     */
    std::string name() const override;

    /**
     * @brief Process message via gRPC
     * @param message Input message
     * @return Future with result
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    /**
     * @brief Get capabilities
     * @return Capabilities list including "grpc", "streaming", "binary_protocol", "http2"
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Check if gRPC support is available
     * @return true if compiled with AGENKIT_WITH_GRPC, false otherwise
     */
    static bool is_available();

private:
    std::string name_;
    GrpcConfig config_;

#ifdef AGENKIT_WITH_GRPC
    // Full implementation would include:
    // std::shared_ptr<grpc::Channel> channel_;
    // std::unique_ptr<agent::AgentService::Stub> stub_;

    void init_channel();
    void init_tls();
#endif
};

} // namespace transports
} // namespace agenkit

#endif // AGENKIT_TRANSPORTS_GRPC_AGENT_HPP
