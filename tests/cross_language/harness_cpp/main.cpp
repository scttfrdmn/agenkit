/**
 * @file main.cpp
 * @brief C++ test harness for cross-language equivalence testing
 *
 * Implements the JSON protocol for executing pattern tests.
 * Protocol version: 1.0
 */

#include <iostream>
#include <string>
#include <memory>
#include <future>
#include <nlohmann/json.hpp>

// Agenkit includes
#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/patterns/reflection.hpp"
#include "agenkit/patterns/sequential.hpp"
#include "agenkit/patterns/parallel.hpp"
#include "agenkit/patterns/react.hpp"
#include "agenkit/patterns/conversational.hpp"
#include "agenkit/patterns/task.hpp"

using json = nlohmann::json;
using namespace agenkit::core;
using namespace agenkit::patterns;

const std::string PROTOCOL_VERSION = "1.0";
const std::string VERSION = "0.46.0";

/**
 * @brief Mock agent for deterministic testing
 *
 * Returns predictable responses based on input content to match
 * the Python reference harness behavior.
 */
class MockAgent : public Agent {
public:
    explicit MockAgent(const std::string& name = "mock_agent")
        : name_(name), call_count_(0) {}

    std::string name() const override {
        return name_;
    }

    std::vector<std::string> capabilities() const override {
        return {"mock", "test"};
    }

    std::future<Result<Message, AgentError>> process(Message message) override {
        std::promise<Result<Message, AgentError>> promise;

        try {
            std::string content = message.content_as_str();
            std::string content_lower = content;
            std::transform(content_lower.begin(), content_lower.end(),
                          content_lower.begin(), ::tolower);

            // Reflection pattern - poetry about technology
            if (content_lower.find("poem") != std::string::npos &&
                content_lower.find("technology") != std::string::npos) {
                auto response = Message::with_text("assistant",
                    "Here's a poem about technology:\n\n"
                    "Circuits hum with electric dreams,\n"
                    "Connecting worlds through digital streams.\n"
                    "Innovation's spark lights up the night,\n"
                    "Technology guides us to new height.");
                promise.set_value(Result<Message, AgentError>::ok(response));
                return promise.get_future();
            }

            // Reflection pattern - critique prompt
            if (content_lower.find("critique") != std::string::npos ||
                content_lower.find("improve") != std::string::npos) {
                auto response = Message::with_text("assistant",
                    "Quality Score: 7/10\n\n"
                    "Feedback: The poem captures technology well but could be more specific. "
                    "Consider adding more vivid imagery.\n\n"
                    "Suggestion: Add references to specific technologies or their impact on society.");
                promise.set_value(Result<Message, AgentError>::ok(response));
                return promise.get_future();
            }

            // ReAct pattern - calculation (15 * 24 = 360)
            bool is_calc_query = (content.find("15 * 24") != std::string::npos ||
                                 content.find("What is 15") != std::string::npos) &&
                                content_lower.find("color") == std::string::npos;
            bool is_calc_followup = content.find("What's your next thought/action?") != std::string::npos &&
                                   content.find("360") != std::string::npos;

            if (is_calc_query || is_calc_followup) {
                bool has_actual_observation = content.find("Observation: 360") != std::string::npos ||
                                             content.find("What's your next thought/action?") != std::string::npos;

                if (has_actual_observation) {
                    auto response = Message::with_text("assistant",
                        "Thought: I now have the calculation result\n"
                        "Action: Final Answer\n"
                        "Action Input: The result of 15 * 24 is 360.");
                    promise.set_value(Result<Message, AgentError>::ok(response));
                    return promise.get_future();
                } else {
                    auto response = Message::with_text("assistant",
                        "Thought: I need to use the calculator tool to compute 15 * 24\n"
                        "Action: calculator\n"
                        "Action Input: {\"a\": 15, \"b\": 24}");
                    promise.set_value(Result<Message, AgentError>::ok(response));
                    return promise.get_future();
                }
            }

            // ReAct pattern - simple factual questions (no tools needed)
            if (content_lower.find("color") != std::string::npos &&
                content_lower.find("sky") != std::string::npos) {
                auto response = Message::with_text("assistant",
                    "Thought: This is a simple factual question I can answer directly\n"
                    "Action: Final Answer\n"
                    "Action Input: The sky is blue during the day due to Rayleigh scattering of sunlight.");
                promise.set_value(Result<Message, AgentError>::ok(response));
                return promise.get_future();
            }

            // Task pattern - impossible task (should fail)
            if (content_lower.find("impossible") != std::string::npos) {
                promise.set_value(Result<Message, AgentError>::err(
                    AgentError(AgentErrorType::ProcessingError, "Task cannot be completed")));
                return promise.get_future();
            }

            // Sequential/Parallel - echo the input
            auto response = Message::with_text("assistant", content);
            promise.set_value(Result<Message, AgentError>::ok(response));

        } catch (const std::exception& e) {
            promise.set_value(Result<Message, AgentError>::err(
                AgentError(AgentErrorType::ProcessingError, e.what())));
        }

        return promise.get_future();
    }

private:
    std::string name_;
    int call_count_;  // Reserved for future use
};

/**
 * @brief Handle health_check command
 */
json handle_health_check() {
    return {
        {"status", "success"},
        {"result", {
            {"healthy", true},
            {"uptime_seconds", 0.0}
        }},
        {"error", nullptr}
    };
}

/**
 * @brief Handle get_info command
 */
json handle_get_info() {
    return {
        {"status", "success"},
        {"result", {
            {"language", "cpp"},
            {"version", VERSION},
            {"patterns_supported", json::array({
                "Reflection",
                "Sequential",
                "Parallel",
                "ReAct",
                "Conversational",
                "Task"
            })},
            {"capabilities", {
                {"streaming", false},
                {"async", true},
                {"llm_providers", json::array({"openai", "anthropic"})}
            }}
        }},
        {"error", nullptr}
    };
}

/**
 * @brief Parse message from JSON
 */
Message parse_message(const json& msg_json) {
    std::string role = msg_json.value("role", "user");
    std::string content_str = msg_json.value("content", "");
    json metadata = msg_json.value("metadata", json::object());

    auto message = Message::with_text(role, content_str);

    // Add metadata if present
    if (!metadata.empty() && metadata.is_object()) {
        for (auto& [key, value] : metadata.items()) {
            message.with_metadata(key, value);
        }
    }

    return message;
}

/**
 * @brief Convert Message to JSON
 */
json message_to_json(const Message& msg) {
    return {
        {"role", msg.role()},
        {"content", msg.content_as_str()},
        {"metadata", msg.metadata()}
    };
}

/**
 * @brief Execute Reflection pattern test
 */
json execute_reflection(const json& input_data) {
    auto config = input_data.value("config", json::object());
    int max_iterations = config.value("max_iterations", 3);

    auto message = parse_message(input_data["message"]);

    auto generator = std::make_shared<MockAgent>("generator");
    auto critic = std::make_shared<MockAgent>("critic");

    ReflectionAgent agent(generator, critic, max_iterations);

    auto start = std::chrono::high_resolution_clock::now();
    auto result = agent.process(std::move(message)).get();
    auto end = std::chrono::high_resolution_clock::now();

    double duration_ms = std::chrono::duration<double, std::milli>(end - start).count();

    if (!result.is_ok()) {
        return {
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "ExecutionError"},
                {"message", result.unwrap_err().message()},
                {"details", json::object()}
            }}
        };
    }

    auto output = result.unwrap();
    int iterations = output.metadata().value("reflection_iterations", 0);

    return {
        {"status", "success"},
        {"result", {
            {"output", {
                {"message", message_to_json(output)},
                {"behavior", {
                    {"turns", iterations * 2},  // Each iteration = generation + critique
                    {"tool_calls", json::array()},
                    {"sub_agents", json::array()}
                }}
            }},
            {"execution_info", {
                {"duration_ms", duration_ms},
                {"llm_calls", 0},
                {"tokens_used", 0}
            }}
        }},
        {"error", nullptr}
    };
}

/**
 * @brief Execute Sequential pattern test
 */
json execute_sequential(const json& input_data) {
    auto config = input_data.value("config", json::object());
    auto message = parse_message(input_data["message"]);

    // Create agents from config
    std::vector<std::shared_ptr<Agent>> agents;
    if (config.contains("agents")) {
        for (const auto& agent_config : config["agents"]) {
            std::string agent_name = agent_config.value("name", "agent");
            agents.push_back(std::make_shared<MockAgent>(agent_name));
        }
    } else {
        // Default: two mock agents
        agents.push_back(std::make_shared<MockAgent>("agent1"));
        agents.push_back(std::make_shared<MockAgent>("agent2"));
    }

    SequentialAgent agent(agents);

    auto start = std::chrono::high_resolution_clock::now();
    auto result = agent.process(std::move(message)).get();
    auto end = std::chrono::high_resolution_clock::now();

    double duration_ms = std::chrono::duration<double, std::milli>(end - start).count();

    if (!result.is_ok()) {
        return {
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "ExecutionError"},
                {"message", result.unwrap_err().message()},
                {"details", json::object()}
            }}
        };
    }

    auto output = result.unwrap();

    // Extract sub_agents from metadata
    json sub_agents = json::array();
    if (output.metadata().contains("pipeline_stages")) {
        for (const auto& stage : output.metadata()["pipeline_stages"]) {
            sub_agents.push_back(stage["agent"]);
        }
    }

    return {
        {"status", "success"},
        {"result", {
            {"output", {
                {"message", message_to_json(output)},
                {"behavior", {
                    {"turns", 1},
                    {"tool_calls", json::array()},
                    {"sub_agents", sub_agents}
                }}
            }},
            {"execution_info", {
                {"duration_ms", duration_ms},
                {"llm_calls", 0},
                {"tokens_used", 0}
            }}
        }},
        {"error", nullptr}
    };
}

/**
 * @brief Execute Parallel pattern test
 */
json execute_parallel(const json& input_data) {
    auto config = input_data.value("config", json::object());
    auto message = parse_message(input_data["message"]);

    // Create agents from config
    std::vector<std::shared_ptr<Agent>> agents;
    if (config.contains("agents")) {
        for (const auto& agent_config : config["agents"]) {
            std::string agent_name = agent_config.value("name", "agent");
            agents.push_back(std::make_shared<MockAgent>(agent_name));
        }
    } else {
        // Default: two mock agents
        agents.push_back(std::make_shared<MockAgent>("agent1"));
        agents.push_back(std::make_shared<MockAgent>("agent2"));
    }

    // Simple aggregator that combines results
    auto aggregator = [](const std::vector<Message>& messages) -> Message {
        if (messages.empty()) {
            return Message::with_text("assistant", "No results");
        }

        std::string combined;
        for (const auto& msg : messages) {
            if (!combined.empty()) combined += " ";
            combined += msg.content_as_str();
        }

        auto result = Message::with_text("assistant", combined);
        result.with_metadata("aggregated", true);
        return result;
    };

    ParallelAgent agent(agents, aggregator);

    auto start = std::chrono::high_resolution_clock::now();
    auto result = agent.process(std::move(message)).get();
    auto end = std::chrono::high_resolution_clock::now();

    double duration_ms = std::chrono::duration<double, std::milli>(end - start).count();

    if (!result.is_ok()) {
        return {
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "ExecutionError"},
                {"message", result.unwrap_err().message()},
                {"details", json::object()}
            }}
        };
    }

    auto output = result.unwrap();

    // Extract agent names
    json sub_agents = json::array();
    for (const auto& a : agents) {
        sub_agents.push_back(a->name());
    }

    return {
        {"status", "success"},
        {"result", {
            {"output", {
                {"message", message_to_json(output)},
                {"behavior", {
                    {"turns", 1},
                    {"tool_calls", json::array()},
                    {"sub_agents", sub_agents}
                }}
            }},
            {"execution_info", {
                {"duration_ms", duration_ms},
                {"llm_calls", 0},
                {"tokens_used", 0}
            }}
        }},
        {"error", nullptr}
    };
}

/**
 * @brief Execute ReAct pattern test (stub for now)
 */
json execute_react(const json& input_data) {
    // For initial implementation, return not_implemented
    return {
        {"status", "not_implemented"},
        {"result", nullptr},
        {"error", {
            {"type", "NotImplemented"},
            {"message", "ReAct pattern not yet implemented in C++ harness"},
            {"details", json::object()}
        }}
    };
}

/**
 * @brief Execute Conversational pattern test (stub for now)
 */
json execute_conversational(const json& input_data) {
    // For initial implementation, return not_implemented
    return {
        {"status", "not_implemented"},
        {"result", nullptr},
        {"error", {
            {"type", "NotImplemented"},
            {"message", "Conversational pattern not yet implemented in C++ harness"},
            {"details", json::object()}
        }}
    };
}

/**
 * @brief Execute Task pattern test (stub for now)
 */
json execute_task(const json& input_data) {
    // For initial implementation, return not_implemented
    return {
        {"status", "not_implemented"},
        {"result", nullptr},
        {"error", {
            {"type", "NotImplemented"},
            {"message", "Task pattern not yet implemented in C++ harness"},
            {"details", json::object()}
        }}
    };
}

/**
 * @brief Handle execute_test command
 */
json handle_execute_test(const json& payload) {
    std::string pattern = payload.value("pattern", "");
    json input_data = payload.value("input", json::object());

    if (pattern == "Reflection") {
        return execute_reflection(input_data);
    } else if (pattern == "Sequential") {
        return execute_sequential(input_data);
    } else if (pattern == "Parallel") {
        return execute_parallel(input_data);
    } else if (pattern == "ReAct") {
        return execute_react(input_data);
    } else if (pattern == "Conversational") {
        return execute_conversational(input_data);
    } else if (pattern == "Task") {
        return execute_task(input_data);
    } else {
        return {
            {"status", "not_implemented"},
            {"result", nullptr},
            {"error", {
                {"type", "PatternNotFound"},
                {"message", "Pattern '" + pattern + "' not implemented in C++ harness"},
                {"details", json::object()}
            }}
        };
    }
}

/**
 * @brief Handle incoming request
 */
json handle_request(const json& request) {
    // Validate protocol version
    std::string protocol_version = request.value("protocol_version", "");
    if (protocol_version != PROTOCOL_VERSION) {
        return {
            {"protocol_version", PROTOCOL_VERSION},
            {"request_id", request.value("request_id", "")},
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "ProtocolError"},
                {"message", "Protocol version mismatch: expected " + PROTOCOL_VERSION +
                           ", got " + protocol_version},
                {"details", json::object()}
            }}
        };
    }

    std::string command = request.value("command", "");
    json payload = request.value("payload", json::object());
    std::string request_id = request.value("request_id", "");

    json result;
    if (command == "health_check") {
        result = handle_health_check();
    } else if (command == "get_info") {
        result = handle_get_info();
    } else if (command == "execute_test") {
        result = handle_execute_test(payload);
    } else {
        result = {
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "CommandNotFound"},
                {"message", "Unknown command: " + command},
                {"details", json::object()}
            }}
        };
    }

    // Build response
    json response = {
        {"protocol_version", PROTOCOL_VERSION},
        {"request_id", request_id}
    };

    // Merge result into response
    for (auto& [key, value] : result.items()) {
        response[key] = value;
    }

    return response;
}

/**
 * @brief Main entry point
 */
int main() {
    try {
        // Read request from stdin
        std::string request_json;
        std::string line;
        while (std::getline(std::cin, line)) {
            request_json += line;
        }

        // Parse request
        json request = json::parse(request_json);

        // Handle request
        json response = handle_request(request);

        // Write response to stdout
        std::cout << response.dump() << std::endl;

        // Exit with appropriate code
        return response["status"] == "success" ? 0 : 1;

    } catch (const json::parse_error& e) {
        // Invalid JSON
        json error_response = {
            {"protocol_version", PROTOCOL_VERSION},
            {"request_id", nullptr},
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "ProtocolError"},
                {"message", std::string("Invalid JSON: ") + e.what()},
                {"details", json::object()}
            }}
        };
        std::cout << error_response.dump() << std::endl;
        return 2;

    } catch (const std::exception& e) {
        // Unexpected error
        json error_response = {
            {"protocol_version", PROTOCOL_VERSION},
            {"request_id", nullptr},
            {"status", "error"},
            {"result", nullptr},
            {"error", {
                {"type", "InternalError"},
                {"message", std::string("Internal error: ") + e.what()},
                {"details", json::object()}
            }}
        };
        std::cout << error_response.dump() << std::endl;
        return 4;
    }
}
