/**
 * @file mcp.cpp
 * @brief Model Context Protocol (MCP) implementation
 *
 * Implements StdioClient, HttpClient, McpServer, McpToolAdapter, and
 * tools_from_client.  Uses POSIX fork/exec for subprocess management and
 * cpp-httplib for HTTP transport.
 */

#include "agenkit/protocols/mcp.hpp"

#include <httplib.h>

#include <unistd.h>
#include <sys/wait.h>

#include <stdexcept>
#include <sstream>
#include <iostream>

namespace agenkit {
namespace protocols {
namespace mcp {

// ============================================================================
// Protocol version negotiation (agenkit#781)
// ============================================================================

/// Build an McpServerInfo from an initialize result, capturing the server's
/// reported protocolVersion (previously discarded) and warning to stderr
/// when it differs from ours, so version skew is visible instead of
/// surfacing later as an unrelated decode error or wrong result.
static McpServerInfo parse_server_info(const nlohmann::json& result) {
    McpServerInfo info;
    if (result.contains("serverInfo") && result["serverInfo"].is_object()) {
        const auto& si = result["serverInfo"];
        info.name = si.value("name", "");
        info.version = si.value("version", "");
    }
    info.protocol_version = result.value("protocolVersion", "");
    if (!info.protocol_version.empty() && info.protocol_version != PROTOCOL_VERSION) {
        std::cerr << "mcp: server protocol version \"" << info.protocol_version
                  << "\" does not match client version \"" << PROTOCOL_VERSION << "\"\n";
    }
    return info;
}

// ============================================================================
// Wire type helpers
// ============================================================================

nlohmann::json JsonRpcRequest::to_json() const {
    nlohmann::json j = {
        {"jsonrpc", jsonrpc},
        {"id",      id},
        {"method",  method}
    };
    if (!params.is_null()) {
        j["params"] = params;
    }
    return j;
}

JsonRpcRequest JsonRpcRequest::from_json(const nlohmann::json& j) {
    JsonRpcRequest req;
    req.jsonrpc = j.value("jsonrpc", "2.0");
    req.id      = j.value("id", 0LL);
    req.method  = j.value("method", "");
    req.params  = j.contains("params") ? j["params"] : nlohmann::json(nullptr);
    return req;
}

JsonRpcResponse JsonRpcResponse::from_json(const nlohmann::json& j) {
    JsonRpcResponse resp;
    resp.jsonrpc   = j.value("jsonrpc", "2.0");
    resp.id        = j.value("id", 0LL);
    resp.has_error = j.contains("error") && !j["error"].is_null();
    if (resp.has_error) {
        auto& e        = j["error"];
        resp.error.code    = e.value("code", -1);
        resp.error.message = e.value("message", "unknown error");
    }
    resp.result = j.contains("result") ? j["result"] : nlohmann::json(nullptr);
    return resp;
}

// ============================================================================
// StdioClient
// ============================================================================

StdioClient::StdioClient(const std::string& command,
                         const std::vector<std::string>& args)
    : command_(command), args_(args) {}

StdioClient::~StdioClient() {
    try {
        close();
    } catch (...) {
        // suppress exceptions in destructor
    }
}

/*static*/ nlohmann::json StdioClient::init_params() {
    return {
        {"protocolVersion", PROTOCOL_VERSION},
        {"clientInfo", {
            {"name",    "agenkit-cpp"},
            {"version", CLIENT_VERSION}
        }},
        {"capabilities", nlohmann::json::object()}
    };
}

void StdioClient::initialize() {
    int stdin_pipe[2];
    int stdout_pipe[2];

    if (pipe(stdin_pipe) == -1) {
        throw std::runtime_error("mcp: stdin pipe failed");
    }
    if (pipe(stdout_pipe) == -1) {
        if (::close(stdin_pipe[0]) == -1) {}
        if (::close(stdin_pipe[1]) == -1) {}
        throw std::runtime_error("mcp: stdout pipe failed");
    }

    pid_ = fork();
    if (pid_ < 0) {
        if (::close(stdin_pipe[0]) == -1) {}
        if (::close(stdin_pipe[1]) == -1) {}
        if (::close(stdout_pipe[0]) == -1) {}
        if (::close(stdout_pipe[1]) == -1) {}
        throw std::runtime_error("mcp: fork failed");
    }

    if (pid_ == 0) {
        // child process
        if (dup2(stdin_pipe[0], STDIN_FILENO) == -1)   { _exit(1); }
        if (dup2(stdout_pipe[1], STDOUT_FILENO) == -1) { _exit(1); }
        if (::close(stdin_pipe[0]) == -1)  {}
        if (::close(stdin_pipe[1]) == -1)  {}
        if (::close(stdout_pipe[0]) == -1) {}
        if (::close(stdout_pipe[1]) == -1) {}

        std::vector<char*> argv;
        argv.push_back(const_cast<char*>(command_.c_str()));
        for (auto& a : args_) {
            argv.push_back(const_cast<char*>(a.c_str()));
        }
        argv.push_back(nullptr);
        execvp(command_.c_str(), argv.data());
        _exit(1);
    }

    // parent: close unused ends
    if (::close(stdin_pipe[0]) == -1)  {}
    if (::close(stdout_pipe[1]) == -1) {}

    stdin_fd_    = stdin_pipe[1];
    stdout_file_ = fdopen(stdout_pipe[0], "r");
    if (stdout_file_ == nullptr) {
        throw std::runtime_error("mcp: fdopen failed");
    }

    auto resp = send_request("initialize", init_params());
    if (resp.has_error) {
        throw std::runtime_error("mcp initialize error: " + resp.error.message);
    }
    server_info_ = parse_server_info(resp.result);
}

JsonRpcResponse StdioClient::send_request(const std::string& method,
                                           const nlohmann::json& params) {
    std::lock_guard<std::mutex> lock(mutex_);
    ++next_id_;
    nlohmann::json req = {
        {"jsonrpc", "2.0"},
        {"id",      next_id_},
        {"method",  method}
    };
    if (!params.is_null()) {
        req["params"] = params;
    }

    std::string line = req.dump() + "\n";
    if (write(stdin_fd_, line.c_str(), line.size()) == -1) {
        throw std::runtime_error("mcp: write to subprocess failed");
    }

    char buf[65536];
    if (fgets(buf, static_cast<int>(sizeof(buf)), stdout_file_) == nullptr) {
        throw std::runtime_error("mcp: server closed stdout");
    }

    return JsonRpcResponse::from_json(nlohmann::json::parse(buf));
}

std::vector<McpTool> StdioClient::list_tools() {
    auto resp = send_request("tools/list", nlohmann::json::object());
    if (resp.has_error) {
        throw std::runtime_error("mcp tools/list error: " + resp.error.message);
    }
    std::vector<McpTool> tools;
    if (resp.result.contains("tools") && resp.result["tools"].is_array()) {
        for (const auto& t : resp.result["tools"]) {
            tools.push_back(McpTool::from_json(t));
        }
    }
    return tools;
}

McpToolResult StdioClient::call_tool(const std::string& name,
                                      const nlohmann::json& args) {
    nlohmann::json params = {
        {"name",      name},
        {"arguments", args}
    };
    auto resp = send_request("tools/call", params);
    if (resp.has_error) {
        return McpToolResult{
            {{"error", resp.error.message}},
            true
        };
    }
    McpToolResult result;
    result.is_error = resp.result.value("isError", false);
    if (resp.result.contains("content") && resp.result["content"].is_array()) {
        for (const auto& c : resp.result["content"]) {
            McpContent mc;
            mc.type = c.value("type", "text");
            mc.text = c.value("text", "");
            result.content.push_back(std::move(mc));
        }
    }
    return result;
}

McpServerInfo StdioClient::server_info() const {
    return server_info_;
}

void StdioClient::close() {
    if (stdin_fd_ != -1) {
        if (::close(stdin_fd_) == -1) {}
        stdin_fd_ = -1;
    }
    if (stdout_file_ != nullptr) {
        if (fclose(stdout_file_) != 0) {}
        stdout_file_ = nullptr;
    }
    if (pid_ > 0) {
        waitpid(pid_, nullptr, 0);
        pid_ = -1;
    }
}

// ============================================================================
// HttpClient
// ============================================================================

namespace {

/// Minimal URL parser: "http://host[:port][/path]"
void parse_url(const std::string& url, std::string& host, int& port,
               std::string& path) {
    // Strip scheme
    std::string rest = url;
    const std::string http_scheme  = "http://";
    const std::string https_scheme = "https://";
    bool use_https = false;

    if (rest.rfind(https_scheme, 0) == 0) {
        rest      = rest.substr(https_scheme.size());
        use_https = true;
    } else if (rest.rfind(http_scheme, 0) == 0) {
        rest = rest.substr(http_scheme.size());
    }

    // Split at first '/'
    auto slash_pos = rest.find('/');
    std::string authority;
    if (slash_pos == std::string::npos) {
        authority = rest;
        path      = "/";
    } else {
        authority = rest.substr(0, slash_pos);
        path      = rest.substr(slash_pos);
    }

    // Split authority at ':'
    auto colon_pos = authority.find(':');
    if (colon_pos == std::string::npos) {
        host = authority;
        port = use_https ? 443 : 80;
    } else {
        host = authority.substr(0, colon_pos);
        port = std::stoi(authority.substr(colon_pos + 1));
    }
}

} // anonymous namespace

HttpClient::HttpClient(const std::string& base_url) {
    parse_url(base_url, host_, port_, path_);
}

/*static*/ nlohmann::json HttpClient::init_params() {
    return {
        {"protocolVersion", PROTOCOL_VERSION},
        {"clientInfo", {
            {"name",    "agenkit-cpp"},
            {"version", CLIENT_VERSION}
        }},
        {"capabilities", nlohmann::json::object()}
    };
}

JsonRpcResponse HttpClient::send_request(const std::string& method,
                                          const nlohmann::json& params) {
    std::lock_guard<std::mutex> lock(mutex_);
    ++next_id_;

    nlohmann::json req = {
        {"jsonrpc", "2.0"},
        {"id",      next_id_},
        {"method",  method}
    };
    if (!params.is_null()) {
        req["params"] = params;
    }

    httplib::Client cli(host_, port_);
    cli.set_connection_timeout(30, 0);
    cli.set_read_timeout(30, 0);
    cli.set_write_timeout(30, 0);

    auto res = cli.Post(path_, req.dump(), "application/json");
    if (!res) {
        throw std::runtime_error("mcp: HTTP request failed (no response)");
    }
    if (res->status != 200) {
        throw std::runtime_error(
            "mcp: HTTP error status " + std::to_string(res->status));
    }

    return JsonRpcResponse::from_json(nlohmann::json::parse(res->body));
}

void HttpClient::initialize() {
    auto resp = send_request("initialize", init_params());
    if (resp.has_error) {
        throw std::runtime_error("mcp initialize error: " + resp.error.message);
    }
    server_info_ = parse_server_info(resp.result);
}

std::vector<McpTool> HttpClient::list_tools() {
    auto resp = send_request("tools/list", nlohmann::json::object());
    if (resp.has_error) {
        throw std::runtime_error("mcp tools/list error: " + resp.error.message);
    }
    std::vector<McpTool> tools;
    if (resp.result.contains("tools") && resp.result["tools"].is_array()) {
        for (const auto& t : resp.result["tools"]) {
            tools.push_back(McpTool::from_json(t));
        }
    }
    return tools;
}

McpToolResult HttpClient::call_tool(const std::string& name,
                                     const nlohmann::json& args) {
    nlohmann::json params = {
        {"name",      name},
        {"arguments", args}
    };
    auto resp = send_request("tools/call", params);
    if (resp.has_error) {
        return McpToolResult{
            {{"error", resp.error.message}},
            true
        };
    }
    McpToolResult result;
    result.is_error = resp.result.value("isError", false);
    if (resp.result.contains("content") && resp.result["content"].is_array()) {
        for (const auto& c : resp.result["content"]) {
            McpContent mc;
            mc.type = c.value("type", "text");
            mc.text = c.value("text", "");
            result.content.push_back(std::move(mc));
        }
    }
    return result;
}

McpServerInfo HttpClient::server_info() const {
    return server_info_;
}

// ============================================================================
// McpServer
// ============================================================================

McpServer::McpServer(const std::string& name, const std::string& version,
                     std::vector<std::shared_ptr<agenkit::core::Tool>> tools)
    : name_(name), version_(version) {
    for (auto& t : tools) {
        tools_[t->name()] = t;
    }
}

/*static*/ nlohmann::json McpServer::error_response(long long id, int code,
                                                      const std::string& msg) {
    return {
        {"jsonrpc", "2.0"},
        {"id",      id},
        {"error",   {{"code", code}, {"message", msg}}}
    };
}

nlohmann::json McpServer::handle_initialize(const nlohmann::json& req) {
    long long id = req.value("id", 0LL);

    // Read (and thus stop discarding) the client's requested version —
    // agenkit#781. Per the MCP spec's negotiation model the server always
    // replies with the revision it actually implements; a mismatch is
    // logged so version skew is visible instead of silent.
    if (req.contains("params") && req["params"].is_object()) {
        std::string client_protocol_version = req["params"].value("protocolVersion", "");
        if (!client_protocol_version.empty() && client_protocol_version != PROTOCOL_VERSION) {
            std::cerr << "mcp: client requested protocol version \"" << client_protocol_version
                      << "\", server speaks \"" << PROTOCOL_VERSION << "\"\n";
        }
    }

    return {
        {"jsonrpc", "2.0"},
        {"id",      id},
        {"result",  {
            {"protocolVersion", PROTOCOL_VERSION},
            {"serverInfo",      {{"name", name_}, {"version", version_}}},
            {"capabilities",    {{"tools", nlohmann::json::object()}}}
        }}
    };
}

nlohmann::json McpServer::handle_tools_list(const nlohmann::json& req) {
    long long id = req.value("id", 0LL);
    nlohmann::json tool_array = nlohmann::json::array();
    for (const auto& kv : tools_) {
        tool_array.push_back({
            {"name",        kv.second->name()},
            {"description", kv.second->description()}
        });
    }
    return {
        {"jsonrpc", "2.0"},
        {"id",      id},
        {"result",  {{"tools", tool_array}}}
    };
}

nlohmann::json McpServer::handle_tools_call(const nlohmann::json& req) {
    long long id = req.value("id", 0LL);
    if (!req.contains("params")) {
        return error_response(id, -32602, "missing params");
    }
    const auto& params = req["params"];
    std::string tool_name = params.value("name", "");
    auto it = tools_.find(tool_name);
    if (it == tools_.end()) {
        return error_response(id, -32601, "tool not found: " + tool_name);
    }

    nlohmann::json args = params.contains("arguments")
        ? params["arguments"]
        : nlohmann::json::object();

    try {
        auto future = it->second->execute(args);
        auto result = future.get();
        if (result.is_err()) {
            const auto& err = result.unwrap_err();
            nlohmann::json content = nlohmann::json::array();
            content.push_back({{"type", "text"}, {"text", err.message()}});
            return {
                {"jsonrpc", "2.0"},
                {"id",      id},
                {"result",  {{"content", content}, {"isError", true}}}
            };
        }
        const auto& tr = result.unwrap();
        nlohmann::json content = nlohmann::json::array();
        content.push_back({{"type", "text"}, {"text", tr.result().dump()}});
        return {
            {"jsonrpc", "2.0"},
            {"id",      id},
            {"result",  {{"content", content}, {"isError", tr.is_error()}}}
        };
    } catch (const std::exception& ex) {
        return error_response(id, -32603, std::string("tool execution error: ") + ex.what());
    }
}

nlohmann::json McpServer::handle_request(const nlohmann::json& req_json) {
    if (!req_json.contains("method")) {
        long long id = req_json.value("id", 0LL);
        return error_response(id, -32600, "invalid request: missing method");
    }
    std::string method = req_json["method"];
    if (method == "initialize") {
        return handle_initialize(req_json);
    }
    if (method == "tools/list") {
        return handle_tools_list(req_json);
    }
    if (method == "tools/call") {
        return handle_tools_call(req_json);
    }
    long long id = req_json.value("id", 0LL);
    return error_response(id, -32601, "method not found: " + method);
}

void McpServer::serve_stdio() {
    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        nlohmann::json resp;
        try {
            auto req = nlohmann::json::parse(line);
            resp = handle_request(req);
        } catch (...) {
            resp = error_response(0, -32700, "parse error");
        }
        std::cout << resp.dump() << "\n" << std::flush;
    }
}

// ============================================================================
// McpToolAdapter
// ============================================================================

McpToolAdapter::McpToolAdapter(std::shared_ptr<McpClient> client, McpTool tool)
    : client_(std::move(client)), tool_(std::move(tool)) {}

std::string McpToolAdapter::name() const {
    return tool_.name;
}

std::string McpToolAdapter::description() const {
    return tool_.description;
}

std::future<agenkit::core::Result<agenkit::core::ToolResult,
                                   agenkit::core::AgentError>>
McpToolAdapter::execute(const nlohmann::json& params) {
    // Capture by value so the lambda owns the data.
    auto client   = client_;
    auto toolname = tool_.name;

    return std::async(std::launch::async,
        [client, toolname, params]()
            -> agenkit::core::Result<agenkit::core::ToolResult,
                                     agenkit::core::AgentError>
        {
            try {
                McpToolResult mcp_result = client->call_tool(toolname, params);
                bool is_err = mcp_result.is_error;
                std::string text = text_content(mcp_result.content);
                nlohmann::json result_json = {{"text", text}};
                agenkit::core::ToolResult tr(toolname, result_json, is_err);
                if (is_err) {
                    return agenkit::core::Result<
                        agenkit::core::ToolResult,
                        agenkit::core::AgentError>::err(
                            agenkit::core::AgentError(
                                agenkit::core::AgentErrorType::ProcessingError,
                                text));
                }
                return agenkit::core::Result<
                    agenkit::core::ToolResult,
                    agenkit::core::AgentError>::ok(std::move(tr));
            } catch (const std::exception& ex) {
                return agenkit::core::Result<
                    agenkit::core::ToolResult,
                    agenkit::core::AgentError>::err(
                        agenkit::core::AgentError(
                            agenkit::core::AgentErrorType::Transport,
                            ex.what()));
            }
        });
}

// ============================================================================
// tools_from_client
// ============================================================================

std::vector<std::shared_ptr<agenkit::core::Tool>>
tools_from_client(std::shared_ptr<McpClient> client) {
    auto mcp_tools = client->list_tools();
    std::vector<std::shared_ptr<agenkit::core::Tool>> tools;
    tools.reserve(mcp_tools.size());
    for (auto& t : mcp_tools) {
        tools.push_back(std::make_shared<McpToolAdapter>(client, std::move(t)));
    }
    return tools;
}

} // namespace mcp
} // namespace protocols
} // namespace agenkit
