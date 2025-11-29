/**
 * @file search_tool.hpp
 * @brief Simulated web search tool
 */

#ifndef AGENKIT_EXAMPLES_SEARCH_TOOL_HPP
#define AGENKIT_EXAMPLES_SEARCH_TOOL_HPP

#include "agenkit/patterns/react.hpp"
#include <string>
#include <unordered_map>
#include <algorithm>
#include <cctype>

namespace agenkit {
namespace examples {

/**
 * @brief Simulated web search tool
 *
 * Provides fake search results for demonstration purposes.
 * In production, this would call a real search API (Google, Bing, etc.)
 *
 * Has pre-defined answers for common queries about:
 * - AgentKit
 * - Programming languages
 * - Famous landmarks
 * - General knowledge
 */
class SearchTool : public patterns::Tool {
public:
    SearchTool() {
        // Simulated search database
        search_data_ = {
            {"agenkit", "AgentKit is a minimal, composable framework for building AI agents "
                       "in multiple languages (Python, Go, TypeScript, C++). It provides "
                       "core patterns like ReAct, Reflection, and Multiagent orchestration."},

            {"python", "Python is a high-level, interpreted programming language known for "
                      "its simplicity and readability. Created by Guido van Rossum in 1991."},

            {"c++", "C++ is a powerful, compiled programming language created by Bjarne Stroustrup "
                   "in 1983. It supports object-oriented, procedural, and generic programming."},

            {"eiffel tower", "The Eiffel Tower is a wrought-iron lattice tower in Paris, France. "
                            "Built in 1889, it stands 330 meters tall and is one of the most "
                            "recognizable structures in the world."},

            {"mount everest", "Mount Everest is Earth's highest mountain at 8,849 meters (29,032 ft) "
                             "above sea level. It's located in the Himalayas on the border between "
                             "Nepal and Tibet."},

            {"artificial intelligence", "Artificial Intelligence (AI) is the simulation of human "
                                       "intelligence by machines. Modern AI includes machine learning, "
                                       "deep learning, and large language models (LLMs)."},

            {"llm", "Large Language Models (LLMs) are AI models trained on vast amounts of text "
                   "data. Examples include GPT-4, Claude, and Llama. They can generate human-like "
                   "text and perform various language tasks."},

            {"react pattern", "ReAct (Reasoning + Acting) is an AI agent pattern that combines "
                             "reasoning with action-taking. The agent thinks, acts using tools, "
                             "observes results, and repeats until solving the task."}
        };
    }

    std::string name() const override {
        return "search";
    }

    std::string description() const override {
        return "Searches for information on the web. Useful for finding facts, definitions, "
               "or general knowledge. Example: 'What is the Eiffel Tower?' or 'Python programming language'";
    }

    patterns::ToolResult execute(const std::string& input) override {
        // Normalize input for search
        std::string query = input;
        std::transform(query.begin(), query.end(), query.begin(), ::tolower);

        // Remove common question words
        const std::vector<std::string> remove_words = {
            "what is ", "what's ", "who is ", "who's ", "where is ",
            "when is ", "how does ", "the ", "?"
        };

        for (const auto& word : remove_words) {
            size_t pos = query.find(word);
            if (pos != std::string::npos) {
                query.erase(pos, word.length());
            }
        }

        // Trim whitespace
        query.erase(0, query.find_first_not_of(" \t\r\n"));
        query.erase(query.find_last_not_of(" \t\r\n") + 1);

        // Search database
        for (const auto& [key, value] : search_data_) {
            if (query.find(key) != std::string::npos || key.find(query) != std::string::npos) {
                return patterns::ToolResult::ok(value);
            }
        }

        // No match found
        return patterns::ToolResult::error(
            "No search results found for '" + input + "'. "
            "Try searching for: AgentKit, Python, C++, Eiffel Tower, AI, LLM, ReAct pattern"
        );
    }

private:
    std::unordered_map<std::string, std::string> search_data_;
};

} // namespace examples
} // namespace agenkit

#endif // AGENKIT_EXAMPLES_SEARCH_TOOL_HPP
