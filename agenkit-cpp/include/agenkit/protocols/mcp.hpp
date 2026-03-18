/**
 * @file mcp.hpp
 * @brief Model Context Protocol (MCP) client, server, and tool adapter types
 *
 * Implements the MCP 2024-11-05 specification:
 * - StdioClient: subprocess-based MCP client over stdin/stdout
 * - HttpClient: HTTP-based MCP client using JSON-RPC
 * - McpServer: expose agenkit Tools via MCP stdio protocol
 * - McpToolAdapter: wrap remote MCP tools as local agenkit::core::Tool
 */

#pragma once

#include "agenkit/core/tool.hpp"
#include "agenkit/core/result.hpp"
#include <nlohmann/json.hpp>
#include <string>
#include <vector>
#include <memory>
#include <functional>
#include <map>
#include <mutex>

namespace agenkit {
namespace protocols {
namespace mcp {

inline constexpr const char* PROTOCOL_VERSION = "2024-11-05";
inline constexpr const char* CLIENT_VERSION = "0.83.0";

// ── Wire types ───────────────────────────────────────────────────────────────

struct JsonRpcRequest {
    std::string jsonrpc;
    long long   id;
    std::string method;
    nlohmann::json params;  // null if no params

    nlohmann::json to_json() const;
    static JsonRpcRequest from_json(const nlohmann::json& j);
};

struct JsonRpcError {
    int code;
    std::string message;
};

struct JsonRpcResponse {
    std::string    jsonrpc;
    long long      id;
    nlohmann::json result;     // null if no result
    bool           has_error;
    JsonRpcError   error;

    static JsonRpcResponse from_json(const nlohmann::json& j);
};

// ── MCP domain types ─────────────────────────────────────────────────────────

struct McpTool {
    std::string name;
    std::string description;

    nlohmann::json to_json() const {
        return {{"name", name}, {"description", description}};
    }

    static McpTool from_json(const nlohmann::json& j) {
        return {j.value("name", ""), j.value("description", "")};
    }
};

struct McpContent {
    std::string type;
    std::string text;
};

struct McpToolResult {
    std::vector<McpContent> content;
    bool is_error;
};

struct McpServerInfo {
    std::string name;
    std::string version;
};

/// Concatenate text-type contents into a single string.
inline std::string text_content(const std::vector<McpContent>& contents) {
    std::string result;
    for (const auto& c : contents) {
        if (c.type == "text" && !c.text.empty()) {
            if (!result.empty()) result += " ";
            result += c.text;
        }
    }
    return result;
}

// ── McpClient abstract interface ─────────────────────────────────────────────

class McpClient {
public:
    virtual ~McpClient() = default;

    /// Initialize the client (handshake with server).
    virtual void initialize() = 0;

    /// List tools exposed by the MCP server.
    virtual std::vector<McpTool> list_tools() = 0;

    /// Call a named tool with JSON arguments.
    virtual McpToolResult call_tool(const std::string& name,
                                    const nlohmann::json& args) = 0;

    /// Return server identification info (filled after initialize()).
    virtual McpServerInfo server_info() const = 0;

    /// Close the connection / subprocess.
    virtual void close() = 0;
};

// ── StdioClient ──────────────────────────────────────────────────────────────

/**
 * @brief MCP client that communicates with a subprocess over stdin/stdout.
 *
 * Spawns the given command via fork/exec. Each JSON-RPC message is a
 * single line terminated with '\n'.
 */
class StdioClient : public McpClient {
public:
    explicit StdioClient(const std::string& command,
                         const std::vector<std::string>& args = {});
    ~StdioClient() override;

    void initialize() override;
    std::vector<McpTool> list_tools() override;
    McpToolResult call_tool(const std::string& name,
                            const nlohmann::json& args) override;
    McpServerInfo server_info() const override;
    void close() override;

private:
    std::string              command_;
    std::vector<std::string> args_;
    int                      pid_         = -1;
    int                      stdin_fd_    = -1;
    FILE*                    stdout_file_ = nullptr;
    long long                next_id_     = 0;
    std::mutex               mutex_;
    McpServerInfo            server_info_;

    JsonRpcResponse send_request(const std::string& method,
                                 const nlohmann::json& params);
    static nlohmann::json init_params();
};

// ── HttpClient ───────────────────────────────────────────────────────────────

/**
 * @brief MCP client that communicates with an HTTP server via JSON-RPC POST.
 *
 * Parses "http://host[:port][/path]" URLs and uses cpp-httplib for transport.
 */
class HttpClient : public McpClient {
public:
    explicit HttpClient(const std::string& base_url);
    ~HttpClient() override = default;

    void initialize() override;
    std::vector<McpTool> list_tools() override;
    McpToolResult call_tool(const std::string& name,
                            const nlohmann::json& args) override;
    McpServerInfo server_info() const override;
    void close() override {}

private:
    std::string   host_;
    int           port_    = 80;
    std::string   path_;
    long long     next_id_ = 0;
    std::mutex    mutex_;
    McpServerInfo server_info_;

    JsonRpcResponse send_request(const std::string& method,
                                 const nlohmann::json& params);
    static nlohmann::json init_params();
};

// ── McpServer ────────────────────────────────────────────────────────────────

/**
 * @brief Expose a set of agenkit Tools as an MCP server over stdio.
 *
 * Call serve_stdio() to enter the request-handling loop (reads from std::cin,
 * writes to std::cout).  handle_request() is public for unit testing.
 */
class McpServer {
public:
    McpServer(const std::string& name, const std::string& version,
              std::vector<std::shared_ptr<agenkit::core::Tool>> tools);

    /// Block and serve requests from stdin until EOF.
    void serve_stdio();

    /// Handle a single JSON-RPC request JSON object.  Public for testing.
    nlohmann::json handle_request(const nlohmann::json& req_json);

private:
    std::string name_;
    std::string version_;
    std::map<std::string, std::shared_ptr<agenkit::core::Tool>> tools_;

    nlohmann::json handle_initialize(const nlohmann::json& req);
    nlohmann::json handle_tools_list(const nlohmann::json& req);
    nlohmann::json handle_tools_call(const nlohmann::json& req);
    static nlohmann::json error_response(long long id, int code,
                                         const std::string& msg);
};

// ── Tool adapter ─────────────────────────────────────────────────────────────

/**
 * @brief Wrap a remote MCP tool as a local agenkit::core::Tool.
 *
 * Calls client->call_tool() asynchronously, mapping McpToolResult to
 * agenkit Result<ToolResult, AgentError>.
 */
class McpToolAdapter : public agenkit::core::Tool {
public:
    McpToolAdapter(std::shared_ptr<McpClient> client, McpTool tool);

    std::string name() const override;
    std::string description() const override;
    std::optional<nlohmann::json> parameters_schema() const override {
        return std::nullopt;
    }

    std::future<agenkit::core::Result<agenkit::core::ToolResult,
                                      agenkit::core::AgentError>>
    execute(const nlohmann::json& params) override;

private:
    std::shared_ptr<McpClient> client_;
    McpTool                    tool_;
};

/// Create one McpToolAdapter per tool returned by client->list_tools().
std::vector<std::shared_ptr<agenkit::core::Tool>>
tools_from_client(std::shared_ptr<McpClient> client);

} // namespace mcp
} // namespace protocols
} // namespace agenkit
