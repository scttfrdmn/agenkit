/**
 * @file graph_of_thought.cpp
 * @brief Implementation of Graph-of-Thought Reasoning Technique
 */

#include "agenkit/techniques/reasoning/graph_of_thought.hpp"
#include <sstream>
#include <algorithm>
#include <cctype>

namespace agenkit {
namespace techniques {
namespace reasoning {

GraphOfThoughtAgent::GraphOfThoughtAgent(std::shared_ptr<core::Agent> agent, const GraphOfThoughtConfig& config)
    : agent_(agent),
      max_nodes_(config.max_nodes),
      max_edges_(config.max_edges),
      aggregator_(config.aggregator),
      allow_cycles_(config.allow_cycles) {}

std::string GraphOfThoughtAgent::name() const {
    return "graph_of_thought";
}

std::vector<std::string> GraphOfThoughtAgent::capabilities() const {
    return {
        "reasoning",
        "graph_reasoning",
        "multi_hop",
        "path_aggregation",
        "graph_of_thought"
    };
}

std::future<core::Result<std::string, core::AgentError>> GraphOfThoughtAgent::llm_call(const std::string& prompt) {
    return std::async(std::launch::async, [this, prompt]() -> core::Result<std::string, core::AgentError> {
        auto message = core::Message::with_text("user", prompt);

        auto result_future = agent_->process(message);
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<std::string, core::AgentError>::err(result.unwrap_err());
        }

        return core::Result<std::string, core::AgentError>::ok(result.unwrap().content_as_str());
    });
}

std::future<core::Result<std::vector<std::string>, core::AgentError>> GraphOfThoughtAgent::generate_premises(const std::string& problem) {
    return std::async(std::launch::async, [this, problem]() -> core::Result<std::vector<std::string>, core::AgentError> {
        std::stringstream prompt;
        prompt << "Identify the key facts and premises for this problem.\n"
               << "List 2-4 foundational facts or assumptions, one per line.\n\n"
               << "Problem: " << problem << "\n\n"
               << "Premises:";

        auto result_future = llm_call(prompt.str());
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<std::vector<std::string>, core::AgentError>::err(result.unwrap_err());
        }

        // Parse premises
        std::vector<std::string> premises;
        std::stringstream ss(result.unwrap());
        std::string line;

        while (std::getline(ss, line)) {
            // Trim whitespace
            line.erase(0, line.find_first_not_of(" \t\r\n"));
            line.erase(line.find_last_not_of(" \t\r\n") + 1);

            if (line.empty() || line[0] == '#') {
                continue;
            }

            // Remove numbering and bullets
            size_t start = 0;
            while (start < line.length() && (std::isdigit(line[start]) || line[start] == '.' ||
                                             line[start] == '-' || line[start] == '*')) {
                start++;
            }
            // Skip UTF-8 bullet if present
            if (start < line.length() && line.substr(start, 3) == "\xE2\x80\xA2") {  // • in UTF-8
                start += 3;
            }

            std::string cleaned = line.substr(start);
            cleaned.erase(0, cleaned.find_first_not_of(" \t"));

            if (!cleaned.empty() && premises.size() < 4) {
                premises.push_back(cleaned);
            }
        }

        return core::Result<std::vector<std::string>, core::AgentError>::ok(premises);
    });
}

std::future<core::Result<std::vector<std::string>, core::AgentError>> GraphOfThoughtAgent::generate_thoughts(
    const std::string& problem,
    const std::vector<std::string>& existing_thoughts,
    size_t max_new) {

    return std::async(std::launch::async, [this, problem, existing_thoughts, max_new]()
                      -> core::Result<std::vector<std::string>, core::AgentError> {
        std::stringstream prompt;

        if (!existing_thoughts.empty()) {
            prompt << "Given this problem and existing thoughts, generate " << max_new
                   << " new insights or conclusions.\n\n"
                   << "Problem: " << problem << "\n\n"
                   << "Existing thoughts:\n";

            for (const auto& thought : existing_thoughts) {
                prompt << "- " << thought << "\n";
            }

            prompt << "\nNew thoughts (one per line):";
        } else {
            prompt << "Generate " << max_new << " initial thoughts or insights about this problem.\n\n"
                   << "Problem: " << problem << "\n\n"
                   << "Thoughts (one per line):";
        }

        auto result_future = llm_call(prompt.str());
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<std::vector<std::string>, core::AgentError>::err(result.unwrap_err());
        }

        // Parse thoughts
        std::vector<std::string> thoughts;
        std::stringstream ss(result.unwrap());
        std::string line;

        while (std::getline(ss, line)) {
            line.erase(0, line.find_first_not_of(" \t\r\n"));
            line.erase(line.find_last_not_of(" \t\r\n") + 1);

            if (line.empty() || line[0] == '#') {
                continue;
            }

            size_t start = 0;
            while (start < line.length() && (std::isdigit(line[start]) || line[start] == '.' ||
                                             line[start] == '-' || line[start] == '*')) {
                start++;
            }
            // Skip UTF-8 bullet if present
            if (start < line.length() && line.substr(start, 3) == "\xE2\x80\xA2") {  // • in UTF-8
                start += 3;
            }

            std::string cleaned = line.substr(start);
            cleaned.erase(0, cleaned.find_first_not_of(" \t"));

            if (!cleaned.empty() && thoughts.size() < max_new) {
                thoughts.push_back(cleaned);
            }
        }

        return core::Result<std::vector<std::string>, core::AgentError>::ok(thoughts);
    });
}

std::future<core::Result<std::optional<EdgeType>, core::AgentError>> GraphOfThoughtAgent::identify_connection(
    const std::string& thought1,
    const std::string& thought2) {

    return std::async(std::launch::async, [this, thought1, thought2]()
                      -> core::Result<std::optional<EdgeType>, core::AgentError> {
        std::stringstream prompt;
        prompt << "Analyze the logical relationship between these two statements.\n\n"
               << "Statement 1: " << thought1 << "\n\n"
               << "Statement 2: " << thought2 << "\n\n"
               << "Does statement 2:\n"
               << "- SUPPORT statement 1 (provides evidence or reasoning for it)\n"
               << "- DEPEND on statement 1 (requires it to be true)\n"
               << "- CONTRADICT statement 1 (conflicts with it)\n"
               << "- REFINE statement 1 (improves or clarifies it)\n"
               << "- NO_RELATION (no clear logical connection)\n\n"
               << "Answer with one word: SUPPORT, DEPEND, CONTRADICT, REFINE, or NO_RELATION";

        auto result_future = llm_call(prompt.str());
        auto result = result_future.get();

        if (!result.is_ok()) {
            return core::Result<std::optional<EdgeType>, core::AgentError>::err(result.unwrap_err());
        }

        std::string response = result.unwrap();
        std::transform(response.begin(), response.end(), response.begin(), ::toupper);

        if (response.find("SUPPORT") != std::string::npos) {
            return core::Result<std::optional<EdgeType>, core::AgentError>::ok(EdgeType::SUPPORTS);
        } else if (response.find("DEPEND") != std::string::npos) {
            return core::Result<std::optional<EdgeType>, core::AgentError>::ok(EdgeType::DEPENDS_ON);
        } else if (response.find("CONTRADICT") != std::string::npos) {
            return core::Result<std::optional<EdgeType>, core::AgentError>::ok(EdgeType::CONTRADICTS);
        } else if (response.find("REFINE") != std::string::npos) {
            return core::Result<std::optional<EdgeType>, core::AgentError>::ok(EdgeType::REFINES);
        }

        return core::Result<std::optional<EdgeType>, core::AgentError>::ok(std::nullopt);
    });
}

std::future<core::Result<ReasoningGraph, core::AgentError>> GraphOfThoughtAgent::build_graph(const std::string& problem) {
    return std::async(std::launch::async, [this, problem]() -> core::Result<ReasoningGraph, core::AgentError> {
        ReasoningGraph graph;

        // Step 1: Generate premises
        auto premises_future = generate_premises(problem);
        auto premises_result = premises_future.get();

        if (!premises_result.is_ok()) {
            return core::Result<ReasoningGraph, core::AgentError>::err(premises_result.unwrap_err());
        }

        auto premises = premises_result.unwrap();
        std::vector<size_t> premise_ids;
        for (const auto& premise : premises) {
            size_t node_id = graph.add_node(premise, NodeType::PREMISE, 0.9);
            premise_ids.push_back(node_id);
        }

        // Step 2: Generate intermediate thoughts
        std::vector<std::string> all_thoughts = premises;
        std::vector<size_t> node_ids = premise_ids;

        while (graph.get_nodes().size() < max_nodes_) {
            size_t max_new = std::min(static_cast<size_t>(3), max_nodes_ - graph.get_nodes().size());
            if (max_new == 0) {
                break;
            }

            auto thoughts_future = generate_thoughts(problem, all_thoughts, max_new);
            auto thoughts_result = thoughts_future.get();

            if (!thoughts_result.is_ok()) {
                return core::Result<ReasoningGraph, core::AgentError>::err(thoughts_result.unwrap_err());
            }

            auto new_thoughts = thoughts_result.unwrap();
            if (new_thoughts.empty()) {
                break;
            }

            for (const auto& thought : new_thoughts) {
                if (graph.get_nodes().size() >= max_nodes_) {
                    break;
                }

                size_t node_id = graph.add_node(thought, NodeType::INTERMEDIATE, 0.7);
                all_thoughts.push_back(thought);
                node_ids.push_back(node_id);
            }
        }

        // Step 3: Identify connections between thoughts
        size_t edge_count = 0;
        for (size_t i = 0; i < node_ids.size() && edge_count < max_edges_; ++i) {
            for (size_t j = i + 1; j < node_ids.size() && edge_count < max_edges_; ++j) {
                size_t node1_id = node_ids[i];
                size_t node2_id = node_ids[j];

                const auto* node1 = graph.get_node(node1_id);
                const auto* node2 = graph.get_node(node2_id);

                if (node1 && node2) {
                    auto connection_future = identify_connection(node1->content, node2->content);
                    auto connection_result = connection_future.get();

                    if (connection_result.is_ok() && connection_result.unwrap().has_value()) {
                        graph.add_edge(node1_id, node2_id, connection_result.unwrap().value(), 0.8);
                        edge_count++;
                    }
                }
            }
        }

        // Step 4: Generate final conclusion
        if (graph.get_nodes().size() < max_nodes_) {
            std::stringstream conclusion_prompt;
            conclusion_prompt << "Based on all these thoughts, what is the final conclusion?\n\n"
                            << "Problem: " << problem << "\n\n"
                            << "Thoughts:\n";

            for (const auto& thought : all_thoughts) {
                conclusion_prompt << "- " << thought << "\n";
            }

            conclusion_prompt << "\nFinal conclusion:";

            auto conclusion_future = llm_call(conclusion_prompt.str());
            auto conclusion_result = conclusion_future.get();

            if (conclusion_result.is_ok()) {
                std::string conclusion = conclusion_result.unwrap();
                // Trim whitespace
                conclusion.erase(0, conclusion.find_first_not_of(" \t\r\n"));
                conclusion.erase(conclusion.find_last_not_of(" \t\r\n") + 1);

                size_t conclusion_id = graph.add_node(conclusion, NodeType::CONCLUSION, 0.8);

                // Connect conclusion to recent thoughts
                size_t connect_count = std::min(static_cast<size_t>(3), node_ids.size());
                for (size_t i = node_ids.size() - connect_count; i < node_ids.size() && edge_count < max_edges_; ++i) {
                    graph.add_edge(node_ids[i], conclusion_id, EdgeType::SUPPORTS, 0.9);
                    edge_count++;
                }
            }
        }

        return core::Result<ReasoningGraph, core::AgentError>::ok(std::move(graph));
    });
}

std::vector<std::vector<size_t>> GraphOfThoughtAgent::find_reasoning_paths(const ReasoningGraph& graph) {
    auto premises = graph.get_premises();
    auto conclusions = graph.get_conclusions();

    std::vector<std::vector<size_t>> all_paths;

    for (const auto* premise : premises) {
        for (const auto* conclusion : conclusions) {
            auto paths = graph.find_paths(premise->id, conclusion->id, 6);
            all_paths.insert(all_paths.end(), paths.begin(), paths.end());
        }
    }

    return all_paths;
}

std::string GraphOfThoughtAgent::aggregate_paths(const ReasoningGraph& graph,
                                                 const std::vector<std::vector<size_t>>& paths) {
    if (paths.empty()) {
        // No paths found - use conclusion nodes directly
        auto conclusions = graph.get_conclusions();
        if (!conclusions.empty()) {
            return conclusions[0]->content;
        }
        // Fallback to any node
        auto nodes = graph.get_nodes();
        if (!nodes.empty()) {
            return nodes.back()->content;
        }
        return "Unable to reach conclusion";
    }

    if (aggregator_ == AggregatorType::PATH_BASED) {
        // Find highest scoring path
        const std::vector<size_t>* best_path = &paths[0];
        double best_score = graph.get_path_score(*best_path);

        for (const auto& path : paths) {
            double score = graph.get_path_score(path);
            if (score > best_score) {
                best_score = score;
                best_path = &path;
            }
        }

        // Get conclusion from best path
        const auto* conclusion_node = graph.get_node((*best_path)[best_path->size() - 1]);
        return conclusion_node ? conclusion_node->content : "Unable to reach conclusion";

    } else { // NODE_BASED
        // Count node appearances across paths
        std::unordered_map<size_t, size_t> node_counts;
        for (const auto& path : paths) {
            for (size_t node_id : path) {
                node_counts[node_id]++;
            }
        }

        // Weight by confidence
        size_t best_node_id = 0;
        double best_score = -1.0;

        for (const auto& pair : node_counts) {
            const auto* node = graph.get_node(pair.first);
            if (node) {
                double score = static_cast<double>(pair.second) * node->confidence;
                if (score > best_score) {
                    best_score = score;
                    best_node_id = pair.first;
                }
            }
        }

        const auto* best_node = graph.get_node(best_node_id);
        return best_node ? best_node->content : "Unable to reach conclusion";
    }
}

std::future<core::Result<core::Message, core::AgentError>> GraphOfThoughtAgent::process(core::Message message) {
    return std::async(std::launch::async, [this, message]() -> core::Result<core::Message, core::AgentError> {
        std::string problem = message.content_as_str();

        // Step 1: Build reasoning graph
        auto graph_future = build_graph(problem);
        auto graph_result = graph_future.get();

        if (!graph_result.is_ok()) {
            return core::Result<core::Message, core::AgentError>::err(graph_result.unwrap_err());
        }

        auto graph = std::move(graph_result.unwrap());

        // Step 2: Check for cycles (if not allowed)
        if (!allow_cycles_ && graph.has_cycle()) {
            // For now, just continue - cycles detected but not removed
            // Could implement cycle removal in future
        }

        // Step 3: Find reasoning paths
        auto reasoning_paths = find_reasoning_paths(graph);

        // Step 4: Aggregate paths to final answer
        std::string final_answer = aggregate_paths(graph, reasoning_paths);

        // Get statistics
        auto stats = graph.statistics();

        // Build response message
        auto response = core::Message::with_text("assistant", final_answer);

        // Add metadata
        response.with_metadata("technique", nlohmann::json("graph_of_thought"))
                .with_metadata("num_nodes", nlohmann::json(static_cast<int>(stats.num_nodes)))
                .with_metadata("num_edges", nlohmann::json(static_cast<int>(stats.num_edges)))
                .with_metadata("has_cycles", nlohmann::json(stats.has_cycles))
                .with_metadata("num_reasoning_paths", nlohmann::json(static_cast<int>(reasoning_paths.size())))
                .with_metadata("aggregator", nlohmann::json(aggregator_ == AggregatorType::PATH_BASED ? "path_based" : "node_based"))
                .with_metadata("allow_cycles", nlohmann::json(allow_cycles_));

        return core::Result<core::Message, core::AgentError>::ok(response);
    });
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
