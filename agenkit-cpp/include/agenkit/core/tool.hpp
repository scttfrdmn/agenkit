/**
 * @file tool.hpp
 * @brief Tool interface for executable tools
 */

#ifndef AGENKIT_CORE_TOOL_HPP
#define AGENKIT_CORE_TOOL_HPP

#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/core/errors.hpp"
#include <nlohmann/json.hpp>
#include <string>
#include <future>
#include <optional>

namespace agenkit {
namespace core {

/**
 * @brief Tool interface - minimal contract for executable tools
 *
 * Design decisions:
 * - Pure virtual interface (abstract base class)
 * - Async execution via std::future
 * - JSON parameters for flexibility
 * - Optional schema for validation
 *
 * Performance characteristics:
 * - Virtual dispatch overhead (minimal)
 * - Future-based async execution
 * - Type-safe Result wrapper
 *
 * @par Example
 * @code
 * class SearchTool : public Tool {
 * public:
 *     std::string name() const override {
 *         return "search";
 *     }
 *
 *     std::string description() const override {
 *         return "Search the web for information";
 *     }
 *
 *     std::optional<nlohmann::json> parameters_schema() const override {
 *         return nlohmann::json{
 *             {"type", "object"},
 *             {"properties", {
 *                 {"query", {
 *                     {"type", "string"},
 *                     {"description", "Search query"}
 *                 }}
 *             }},
 *             {"required", nlohmann::json::array({"query"})}
 *         };
 *     }
 *
 *     std::future<Result<ToolResult, AgentError>>
 *     execute(const nlohmann::json& params) override {
 *         std::string query = params.value("query", "");
 *
 *         // Simulate async search
 *         return std::async(std::launch::async, [query]() {
 *             nlohmann::json result{
 *                 {"results", "Search results for: " + query}
 *             };
 *             return Result<ToolResult, AgentError>::ok(
 *                 ToolResult("tool_use_id", result)
 *             );
 *         });
 *     }
 * };
 * @endcode
 */
class Tool {
public:
    /**
     * @brief Virtual destructor
     */
    virtual ~Tool() = default;

    /**
     * @brief Get tool identifier
     *
     * Must be unique within a tool set. Used by LLMs to identify which tool to call.
     *
     * @return Unique tool name (e.g., "search", "calculator")
     */
    virtual std::string name() const = 0;

    /**
     * @brief Get tool description
     *
     * What this tool does. Used by LLMs to decide when to call it.
     * Should be clear and concise, describing the tool's purpose and capabilities.
     *
     * @return Human-readable description of tool functionality
     */
    virtual std::string description() const = 0;

    /**
     * @brief Get JSON schema for tool parameters
     *
     * Optional schema describing the expected parameters. Used by LLMs to understand
     * how to call the tool with correct parameters. Should follow JSON Schema draft-07.
     *
     * @return Optional JSON schema object, or nullopt if no schema provided
     */
    virtual std::optional<nlohmann::json> parameters_schema() const {
        return std::nullopt;
    }

    /**
     * @brief Execute the tool with given parameters
     *
     * Executes the tool asynchronously with the provided parameters. Parameters are
     * passed as a JSON object for flexibility. The tool should validate parameters
     * against its schema if provided.
     *
     * @param params Tool parameters as JSON object
     * @return Future containing Result with ToolResult on success or AgentError on failure
     *
     * @par Example
     * @code
     * nlohmann::json params{
     *     {"query", "What is the weather?"}
     * };
     *
     * auto future = tool->execute(params);
     * auto result = future.get();
     *
     * if (result.is_ok()) {
     *     auto tool_result = result.unwrap();
     *     std::cout << "Result: " << tool_result.result() << std::endl;
     * } else {
     *     auto error = result.unwrap_err();
     *     std::cerr << "Error: " << error.message() << std::endl;
     * }
     * @endcode
     */
    virtual std::future<Result<ToolResult, AgentError>>
    execute(const nlohmann::json& params) = 0;
};

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_TOOL_HPP
