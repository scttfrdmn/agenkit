/**
 * C++ test harness for cross-language equivalence testing.
 *
 * Implements the JSON protocol for executing pattern tests.
 */

#include <nlohmann/json.hpp>
#include <chrono>
#include <iostream>
#include <map>
#include <string>
#include <vector>

using json = nlohmann::json;
using namespace std::chrono;

// Constants
constexpr const char* PROTOCOL_VERSION = "1.0";
constexpr const char* VERSION = "0.29.2";

// Exit codes
constexpr int HARNESS_EXIT_SUCCESS = 0;
constexpr int HARNESS_EXIT_ERROR = 1;
constexpr int HARNESS_EXIT_PROTOCOL_ERROR = 2;
constexpr int HARNESS_EXIT_TIMEOUT = 3;
constexpr int HARNESS_EXIT_INTERNAL_ERROR = 4;

// Pattern registry
const std::map<std::string, bool> SUPPORTED_PATTERNS = {
    {"reflection", true},
    {"sequential", true},
    {"parallel", true},
    {"router", true},
    {"react", true},
    {"conversational", true},
    {"agents_as_tools", true},
    {"fallback", true},
    {"supervisor", true},
    {"planning", true},
    {"task", true},
    {"collaborative", true},
    {"human_in_loop", true},
    {"autonomous", true},
    {"multiagent", true},
    {"orchestration", true},
    {"memory", true},
    {"reasoning_with_tools", true}
};

// Helper functions
std::string to_lower(const std::string& str) {
    std::string result = str;
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
    return result;
}

bool is_supported_pattern(const std::string& pattern) {
    return SUPPORTED_PATTERNS.find(to_lower(pattern)) != SUPPORTED_PATTERNS.end();
}

// Response builders
json create_error_response(const std::string& request_id,
                          const std::string& error_type,
                          const std::string& message) {
    return {
        {"protocol_version", PROTOCOL_VERSION},
        {"request_id", request_id},
        {"status", "error"},
        {"error", {
            {"type", error_type},
            {"message", message}
        }}
    };
}

json create_success_response(const std::string& request_id, const json& result) {
    return {
        {"protocol_version", PROTOCOL_VERSION},
        {"request_id", request_id},
        {"status", "success"},
        {"result", result}
    };
}

void write_response_and_exit(const json& response, int exit_code = HARNESS_EXIT_SUCCESS) {
    std::cout << response.dump() << std::endl;
    std::exit(exit_code);
}

// Pattern execution functions
json execute_reflection(const json& message, const json& config) {
    // TODO: Implement actual reflection pattern execution
    // For now, return a mock response

    int max_iterations = config.value("max_iterations", 3);

    return {
        {"role", "assistant"},
        {"content", "Reflected response to: " + message.value("content", std::string(""))},
        {"metadata", {
            {"iterations", 1},
            {"improved", true},
            {"max_iterations", max_iterations}
        }}
    };
}

json execute_sequential(const json& message, const json& config) {
    // TODO: Implement actual sequential pattern execution
    int agent_count = 0;
    if (config.contains("agents") && config["agents"].is_array()) {
        agent_count = config["agents"].size();
    }

    return {
        {"role", "assistant"},
        {"content", "Sequential result: " + message.value("content", std::string(""))},
        {"metadata", {
            {"agent_count", agent_count}
        }}
    };
}

json execute_parallel(const json& message, const json& config) {
    // TODO: Implement actual parallel pattern execution
    int agent_count = 0;
    if (config.contains("agents") && config["agents"].is_array()) {
        agent_count = config["agents"].size();
    }

    return {
        {"role", "assistant"},
        {"content", "Parallel result: " + message.value("content", std::string(""))},
        {"metadata", {
            {"agent_count", agent_count}
        }}
    };
}

json execute_pattern(const std::string& pattern_name,
                    const json& message,
                    const json& config) {
    // This is a simplified implementation that returns mock responses
    // TODO: Implement actual pattern execution based on pattern_name and config

    std::string pattern_lower = to_lower(pattern_name);

    if (pattern_lower == "reflection") {
        return execute_reflection(message, config);
    } else if (pattern_lower == "sequential") {
        return execute_sequential(message, config);
    } else if (pattern_lower == "parallel") {
        return execute_parallel(message, config);
    } else {
        // Mock response for other patterns
        return {
            {"role", "assistant"},
            {"content", "Mock response for " + pattern_name + " pattern"},
            {"metadata", {
                {"pattern", pattern_name},
                {"mock", true}
            }}
        };
    }
}

// Command handlers
json execute_test(const json& payload) {
    // Parse test payload
    if (!payload.contains("pattern") || !payload["pattern"].is_string()) {
        throw std::runtime_error("Pattern name is required");
    }
    std::string pattern = payload["pattern"];

    // Normalize pattern name to lowercase for case-insensitive matching
    std::string pattern_lower = to_lower(pattern);

    if (!payload.contains("scenario_id") || !payload["scenario_id"].is_string()) {
        throw std::runtime_error("Scenario ID is required");
    }

    if (!payload.contains("input") || !payload["input"].is_object()) {
        throw std::runtime_error("Input is required");
    }
    const json& input = payload["input"];

    // Check if pattern is supported
    if (!is_supported_pattern(pattern_lower)) {
        throw std::runtime_error("Pattern '" + pattern + "' not implemented in C++ harness");
    }

    // Parse input message
    if (!input.contains("message") || !input["message"].is_object()) {
        throw std::runtime_error("Input message is required");
    }
    const json& message_data = input["message"];

    json message = {
        {"role", message_data.value("role", "user")},
        {"content", message_data.value("content", "")},
        {"metadata", message_data.value("metadata", json::object())}
    };

    // Get configuration
    json config = input.value("config", json::object());

    // Execute pattern
    auto start_time = high_resolution_clock::now();
    json output_message = execute_pattern(pattern_lower, message, config);
    auto end_time = high_resolution_clock::now();
    auto duration = duration_cast<milliseconds>(end_time - start_time).count();

    // Build test output
    return {
        {"output", {
            {"message", output_message},
            {"behavior", {
                {"turns", 1},  // TODO: Track actual turns
                {"tool_calls", json::array()},
                {"sub_agents", json::array()}
            }}
        }},
        {"execution_info", {
            {"duration_ms", duration},
            {"llm_calls", 0},  // TODO: Track actual LLM calls
            {"tokens_used", 0}  // TODO: Track actual token usage
        }}
    };
}

json get_info() {
    std::vector<std::string> patterns;
    for (const auto& pair : SUPPORTED_PATTERNS) {
        patterns.push_back(pair.first);
    }

    return {
        {"language", "cpp"},
        {"version", VERSION},
        {"patterns_supported", patterns},
        {"capabilities", {
            {"streaming", true},
            {"async", true},
            {"llm_providers", {"openai", "anthropic"}}
        }}
    };
}

json health_check() {
    return {
        {"healthy", true},
        {"uptime_seconds", 0.0}  // Stateless harness
    };
}

// Request handler
json handle_request(const json& request) {
    // Validate protocol version
    if (!request.contains("protocol_version") ||
        request["protocol_version"] != PROTOCOL_VERSION) {
        return create_error_response(
            request.value("request_id", ""),
            "ProtocolError",
            "Protocol version mismatch: expected " + std::string(PROTOCOL_VERSION) +
                ", got " + request.value("protocol_version", std::string("unknown"))
        );
    }

    std::string request_id = request.value("request_id", "");
    std::string command = request.value("command", "");
    json payload = request.value("payload", json::object());

    try {
        json result;

        if (command == "execute_test") {
            result = execute_test(payload);
        } else if (command == "get_info") {
            result = get_info();
        } else if (command == "health_check") {
            result = health_check();
        } else {
            return create_error_response(
                request_id,
                "CommandNotFound",
                "Unknown command: " + command
            );
        }

        return create_success_response(request_id, result);
    } catch (const std::exception& e) {
        return create_error_response(
            request_id,
            "ExecutionError",
            std::string(e.what())
        );
    }
}

int main() {
    try {
        // Read request from stdin
        std::string request_str;
        std::string line;
        while (std::getline(std::cin, line)) {
            request_str += line;
        }

        // Parse request
        json request;
        try {
            request = json::parse(request_str);
        } catch (const json::parse_error& e) {
            write_response_and_exit(
                create_error_response(
                    "",
                    "ProtocolError",
                    std::string("Invalid JSON: ") + e.what()
                ),
                HARNESS_EXIT_PROTOCOL_ERROR
            );
        }

        // Handle request
        json response = handle_request(request);

        // Write response
        int exit_code = (response["status"] == "success") ? HARNESS_EXIT_SUCCESS : HARNESS_EXIT_ERROR;
        write_response_and_exit(response, exit_code);

    } catch (const std::exception& e) {
        write_response_and_exit(
            create_error_response(
                "",
                "InternalError",
                std::string("Internal error: ") + e.what()
            ),
            HARNESS_EXIT_INTERNAL_ERROR
        );
    }

    return HARNESS_EXIT_SUCCESS;
}
