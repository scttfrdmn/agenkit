/**
 * @file test_mcp.cpp
 * @brief Tests for MCP (Model Context Protocol) support
 *
 * Tests cover wire types, domain types, client subtype polymorphism,
 * tool adapter behaviour, McpServer request handling, and tools_from_client.
 */

#include <gtest/gtest.h>
#include "agenkit/protocols/mcp.hpp"

#include <future>
#include <string>
#include <vector>

using namespace agenkit::protocols::mcp;

// ─────────────────────────────────────────────────────────────────────────────
// MockMcpClient
// ─────────────────────────────────────────────────────────────────────────────

class MockMcpClient : public McpClient {
public:
    explicit MockMcpClient(std::vector<McpTool> tools = {},
                           bool next_call_is_error = false,
                           std::string next_call_text = "mock result")
        : tools_(std::move(tools))
        , next_call_is_error_(next_call_is_error)
        , next_call_text_(std::move(next_call_text)) {}

    void initialize() override { initialized_ = true; }

    std::vector<McpTool> list_tools() override { return tools_; }

    McpToolResult call_tool(const std::string& /*name*/,
                            const nlohmann::json& /*args*/) override {
        McpContent c{"text", next_call_text_};
        return McpToolResult{{c}, next_call_is_error_};
    }

    McpServerInfo server_info() const override {
        return McpServerInfo{"mock-server", "1.0.0"};
    }

    void close() override {}

    bool initialized_ = false;

private:
    std::vector<McpTool> tools_;
    bool                 next_call_is_error_;
    std::string          next_call_text_;
};

// ─────────────────────────────────────────────────────────────────────────────
// MockTool (for McpServer tests)
// ─────────────────────────────────────────────────────────────────────────────

class MockTool : public agenkit::core::Tool {
public:
    explicit MockTool(std::string name, std::string description = "a mock tool",
                      bool fail = false)
        : name_(std::move(name))
        , description_(std::move(description))
        , fail_(fail) {}

    std::string name() const override { return name_; }
    std::string description() const override { return description_; }

    std::future<agenkit::core::Result<agenkit::core::ToolResult,
                                      agenkit::core::AgentError>>
    execute(const nlohmann::json& params) override {
        bool f = fail_;
        std::string n = name_;
        return std::async(std::launch::async,
            [f, n, params]()
                -> agenkit::core::Result<agenkit::core::ToolResult,
                                         agenkit::core::AgentError>
            {
                if (f) {
                    return agenkit::core::Result<
                        agenkit::core::ToolResult,
                        agenkit::core::AgentError>::err(
                            agenkit::core::AgentError(
                                agenkit::core::AgentErrorType::ProcessingError,
                                "mock error"));
                }
                nlohmann::json result = {{"echo", params}};
                return agenkit::core::Result<
                    agenkit::core::ToolResult,
                    agenkit::core::AgentError>::ok(
                        agenkit::core::ToolResult(n, result));
            });
    }

private:
    std::string name_;
    std::string description_;
    bool        fail_;
};

// ─────────────────────────────────────────────────────────────────────────────
// 1. Wire type: request serializes to JSON
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpWireTypes, RequestSerializes) {
    JsonRpcRequest req;
    req.jsonrpc = "2.0";
    req.id      = 1;
    req.method  = "tools/list";
    req.params  = nlohmann::json(nullptr);

    auto j = req.to_json();
    EXPECT_EQ(j["jsonrpc"].get<std::string>(), "2.0");
    EXPECT_EQ(j["id"].get<long long>(), 1LL);
    EXPECT_EQ(j["method"].get<std::string>(), "tools/list");
    // params should be absent when null
    EXPECT_FALSE(j.contains("params"));
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. Wire type: response deserializes from JSON
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpWireTypes, ResponseDeserializes) {
    nlohmann::json j = {
        {"jsonrpc", "2.0"},
        {"id",      42},
        {"result",  {{"serverInfo", {{"name", "test"}, {"version", "1.0"}}}}}
    };
    auto resp = JsonRpcResponse::from_json(j);
    EXPECT_EQ(resp.jsonrpc, "2.0");
    EXPECT_EQ(resp.id, 42LL);
    EXPECT_FALSE(resp.has_error);
    EXPECT_EQ(resp.result["serverInfo"]["name"].get<std::string>(), "test");
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. McpTool round-trips through JSON
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpWireTypes, ToolRoundTrip) {
    McpTool original{"my_tool", "does something useful"};
    auto j    = original.to_json();
    auto copy = McpTool::from_json(j);
    EXPECT_EQ(copy.name, "my_tool");
    EXPECT_EQ(copy.description, "does something useful");
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. text_content: single text item
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpContent, SingleTextContent) {
    std::vector<McpContent> contents{{"text", "hello world"}};
    EXPECT_EQ(text_content(contents), "hello world");
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. text_content: multiple text items joined by space
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpContent, MultiTextContent) {
    std::vector<McpContent> contents{
        {"text", "foo"},
        {"image", "ignored"},
        {"text", "bar"}
    };
    EXPECT_EQ(text_content(contents), "foo bar");
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. StdioClient is a subtype of McpClient (no subprocess launched here)
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpClient, StdioClientIsSubtype) {
    // Construct but do NOT call initialize() — that would fork a real process.
    auto* c = new StdioClient("echo");
    McpClient* mc = c;
    EXPECT_NE(mc, nullptr);
    delete c;
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. HttpClient is a subtype of McpClient (no HTTP connection made here)
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpClient, HttpClientIsSubtype) {
    auto* c = new HttpClient("http://localhost:8080/mcp");
    McpClient* mc = c;
    EXPECT_NE(mc, nullptr);
    delete c;
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. McpToolAdapter: name() returns tool name
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpAdapter, Name) {
    auto mock   = std::make_shared<MockMcpClient>();
    McpTool tool{"calculator", "performs arithmetic"};
    McpToolAdapter adapter(mock, tool);
    EXPECT_EQ(adapter.name(), "calculator");
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. McpToolAdapter: description() returns tool description
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpAdapter, Description) {
    auto mock   = std::make_shared<MockMcpClient>();
    McpTool tool{"calculator", "performs arithmetic"};
    McpToolAdapter adapter(mock, tool);
    EXPECT_EQ(adapter.description(), "performs arithmetic");
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. McpToolAdapter: execute() succeeds and returns ok Result
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpAdapter, ExecuteSuccess) {
    auto mock = std::make_shared<MockMcpClient>(
        std::vector<McpTool>{},
        /*next_call_is_error=*/false,
        "42");
    McpTool tool{"add", "adds numbers"};
    McpToolAdapter adapter(mock, tool);

    auto future = adapter.execute({{"a", 1}, {"b", 2}});
    auto result = future.get();

    EXPECT_TRUE(result.is_ok());
    EXPECT_FALSE(result.is_err());
}

// ─────────────────────────────────────────────────────────────────────────────
// 11. McpToolAdapter: execute() on is_error returns err Result
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpAdapter, ExecuteIsError) {
    auto mock = std::make_shared<MockMcpClient>(
        std::vector<McpTool>{},
        /*next_call_is_error=*/true,
        "tool failed");
    McpTool tool{"broken", "always fails"};
    McpToolAdapter adapter(mock, tool);

    auto future = adapter.execute(nlohmann::json::object());
    auto result = future.get();

    EXPECT_TRUE(result.is_err());
    EXPECT_FALSE(result.is_ok());
}

// ─────────────────────────────────────────────────────────────────────────────
// 12. tools_from_client returns one adapter per tool
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpToolsFromClient, Count) {
    std::vector<McpTool> exposed{
        {"search",   "searches the web"},
        {"weather",  "returns weather data"},
        {"calendar", "lists calendar events"}
    };
    auto mock  = std::make_shared<MockMcpClient>(exposed);
    auto tools = tools_from_client(mock);

    ASSERT_EQ(tools.size(), 3u);
    EXPECT_EQ(tools[0]->name(), "search");
    EXPECT_EQ(tools[1]->name(), "weather");
    EXPECT_EQ(tools[2]->name(), "calendar");
}

// ─────────────────────────────────────────────────────────────────────────────
// 13. McpServer: handle_request covers initialize + tools/list + tools/call
// ─────────────────────────────────────────────────────────────────────────────

TEST(McpServer, HandleRequest) {
    std::vector<std::shared_ptr<agenkit::core::Tool>> tools;
    tools.push_back(std::make_shared<MockTool>("echo_tool", "echoes its input"));

    McpServer server("test-server", "1.2.3", tools);

    // initialize
    {
        nlohmann::json req = {
            {"jsonrpc", "2.0"},
            {"id",      1},
            {"method",  "initialize"},
            {"params",  nlohmann::json::object()}
        };
        auto resp = server.handle_request(req);
        EXPECT_EQ(resp["jsonrpc"].get<std::string>(), "2.0");
        EXPECT_EQ(resp["id"].get<int>(), 1);
        EXPECT_FALSE(resp.contains("error"));
        EXPECT_EQ(
            resp["result"]["serverInfo"]["name"].get<std::string>(),
            "test-server");
        EXPECT_EQ(
            resp["result"]["protocolVersion"].get<std::string>(),
            std::string(PROTOCOL_VERSION));
    }

    // tools/list
    {
        nlohmann::json req = {
            {"jsonrpc", "2.0"},
            {"id",      2},
            {"method",  "tools/list"}
        };
        auto resp = server.handle_request(req);
        EXPECT_FALSE(resp.contains("error"));
        auto& tool_arr = resp["result"]["tools"];
        ASSERT_TRUE(tool_arr.is_array());
        ASSERT_EQ(tool_arr.size(), 1u);
        EXPECT_EQ(tool_arr[0]["name"].get<std::string>(), "echo_tool");
    }

    // tools/call — success
    {
        nlohmann::json req = {
            {"jsonrpc", "2.0"},
            {"id",      3},
            {"method",  "tools/call"},
            {"params",  {{"name", "echo_tool"}, {"arguments", {{"x", 99}}}}}
        };
        auto resp = server.handle_request(req);
        EXPECT_FALSE(resp.contains("error"));
        EXPECT_FALSE(resp["result"].value("isError", true));
    }

    // tools/call — unknown tool
    {
        nlohmann::json req = {
            {"jsonrpc", "2.0"},
            {"id",      4},
            {"method",  "tools/call"},
            {"params",  {{"name", "nonexistent"}, {"arguments", nlohmann::json::object()}}}
        };
        auto resp = server.handle_request(req);
        EXPECT_TRUE(resp.contains("error"));
        EXPECT_EQ(resp["error"]["code"].get<int>(), -32601);
    }

    // unknown method
    {
        nlohmann::json req = {
            {"jsonrpc", "2.0"},
            {"id",      5},
            {"method",  "unknown/method"}
        };
        auto resp = server.handle_request(req);
        EXPECT_TRUE(resp.contains("error"));
        EXPECT_EQ(resp["error"]["code"].get<int>(), -32601);
    }
}
