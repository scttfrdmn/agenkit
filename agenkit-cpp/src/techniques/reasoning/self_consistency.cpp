/**
 * @file self_consistency.cpp
 * @brief Implementation of Self-Consistency Reasoning Technique
 */

#include "agenkit/techniques/reasoning/self_consistency.hpp"
#include "agenkit/infrastructure/thread_pool.hpp"
#include <regex>
#include <algorithm>
#include <cctype>
#include <map>

namespace agenkit {
namespace techniques {
namespace reasoning {

std::string default_answer_extractor(const std::string& text) {
    // Try explicit answer markers
    std::vector<std::regex> patterns = {
        std::regex("(?:therefore|thus|so),?\\s+(?:the answer is\\s+)?(.+?)(?:\\.|$)",
                   std::regex::icase),
        std::regex("(?:the answer is|answer:)\\s+(.+?)(?:\\.|$)",
                   std::regex::icase),
        std::regex("=\\s*(.+?)(?:\\n|$)"),
        std::regex("(?:conclusion|result):\\s*(.+?)(?:\\.|$)",
                   std::regex::icase),
    };

    for (const auto& pattern : patterns) {
        std::smatch match;
        if (std::regex_search(text, match, pattern)) {
            if (match.size() > 1) {
                std::string result = match[1].str();
                // Trim whitespace
                result.erase(0, result.find_first_not_of(" \t\n\r"));
                result.erase(result.find_last_not_of(" \t\n\r") + 1);
                return result;
            }
        }
    }

    // Fallback: use last non-empty line
    std::istringstream iss(text);
    std::string line, last_line;
    while (std::getline(iss, line)) {
        // Trim
        line.erase(0, line.find_first_not_of(" \t\n\r"));
        line.erase(line.find_last_not_of(" \t\n\r") + 1);
        if (!line.empty()) {
            last_line = line;
        }
    }

    if (!last_line.empty()) {
        return last_line;
    }

    // Final fallback
    std::string result = text;
    result.erase(0, result.find_first_not_of(" \t\n\r"));
    result.erase(result.find_last_not_of(" \t\n\r") + 1);
    return result;
}

SelfConsistencyAgent::SelfConsistencyAgent(
    std::shared_ptr<core::Agent> agent,
    const SelfConsistencyConfig& config
) : agent_(agent),
    num_samples_(config.num_samples),
    voting_strategy_(config.voting_strategy),
    temperature_(config.temperature),
    answer_extractor_(config.answer_extractor.value_or(default_answer_extractor))
{}

std::string SelfConsistencyAgent::name() const {
    return "self_consistency";
}

std::vector<std::string> SelfConsistencyAgent::capabilities() const {
    return {
        "reasoning",
        "self_consistency",
        "majority_voting",
        "reliability",
        "consensus"
    };
}

std::string SelfConsistencyAgent::normalize_string(const std::string& str) {
    std::string result = str;
    // Trim
    result.erase(0, result.find_first_not_of(" \t\n\r"));
    result.erase(result.find_last_not_of(" \t\n\r") + 1);
    // Lowercase
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c){ return std::tolower(c); });
    return result;
}

std::vector<SelfConsistencyAgent::Sample>
SelfConsistencyAgent::generate_samples(const core::Message& message) {
    // Generate samples in parallel
    std::vector<std::future<core::Result<core::Message, core::AgentError>>> futures;

    for (size_t i = 0; i < num_samples_; ++i) {
        futures.push_back(agent_->process(message));
    }

    // Collect results
    std::vector<Sample> samples;
    for (auto& future : futures) {
        auto result = future.get();
        if (result.is_ok()) {
            auto response = result.unwrap();
            std::string full_response = response.content_as_str();
            std::string extracted_answer = answer_extractor_(full_response);
            samples.push_back({full_response, extracted_answer});
        } else {
            // If any sample fails, throw error
            throw std::runtime_error("Sampling failed: " + result.unwrap_err().message());
        }
    }

    return samples;
}

std::pair<std::string, double>
SelfConsistencyAgent::vote_majority(const std::vector<std::string>& answers) {
    if (answers.empty()) {
        return {"", 0.0};
    }

    // Count answer occurrences (case-insensitive)
    std::map<std::string, size_t> counts;
    std::map<std::string, std::string> original_case;

    for (const auto& answer : answers) {
        std::string normalized = normalize_string(answer);
        counts[normalized]++;
        if (original_case.find(normalized) == original_case.end()) {
            original_case[normalized] = answer;
        }
    }

    // Find most common
    std::string winning_answer;
    size_t max_count = 0;

    for (const auto& [normalized, count] : counts) {
        if (count > max_count) {
            max_count = count;
            winning_answer = normalized;
        }
    }

    // Get original case version
    std::string winner = original_case[winning_answer];
    double consistency_score = static_cast<double>(max_count) / answers.size();

    return {winner, consistency_score};
}

std::pair<std::string, double>
SelfConsistencyAgent::vote_weighted(
    const std::vector<std::string>& answers,
    const std::vector<std::string>& responses
) {
    if (answers.empty()) {
        return {"", 0.0};
    }

    // Group answers by normalized form
    struct Group {
        std::string original;
        size_t weight;
        size_t count;
    };
    std::map<std::string, Group> groups;

    for (size_t i = 0; i < answers.size(); ++i) {
        std::string normalized = normalize_string(answers[i]);
        auto it = groups.find(normalized);
        if (it != groups.end()) {
            it->second.weight += responses[i].length();
            it->second.count++;
        } else {
            groups[normalized] = {answers[i], responses[i].length(), 1};
        }
    }

    // Find highest weighted answer
    std::string winning_answer;
    size_t max_weight = 0;
    size_t total_weight = 0;

    for (const auto& [normalized, group] : groups) {
        total_weight += group.weight;
        if (group.weight > max_weight) {
            max_weight = group.weight;
            winning_answer = group.original;
        }
    }

    double consistency_score = total_weight > 0
        ? static_cast<double>(max_weight) / total_weight
        : 0.0;

    return {winning_answer, consistency_score};
}

std::pair<std::string, double>
SelfConsistencyAgent::vote_first(const std::vector<std::string>& answers) {
    if (answers.empty()) {
        return {"", 0.0};
    }
    return {answers[0], 1.0};
}

std::map<std::string, size_t>
SelfConsistencyAgent::count_answers(const std::vector<std::string>& answers) {
    std::map<std::string, size_t> counts;

    for (const auto& answer : answers) {
        std::string normalized = normalize_string(answer);
        counts[normalized]++;
    }

    return counts;
}

std::future<core::Result<core::Message, core::AgentError>>
SelfConsistencyAgent::process(core::Message message) {
    return infrastructure::global_thread_pool().enqueue([this, message]() -> core::Result<core::Message, core::AgentError> {
        try {
            // Generate multiple samples
            auto samples = generate_samples(message);

            // Extract full responses and answers
            std::vector<std::string> full_responses;
            std::vector<std::string> extracted_answers;
            for (const auto& sample : samples) {
                full_responses.push_back(sample.full_response);
                extracted_answers.push_back(sample.extracted_answer);
            }

            // Vote for consensus answer
            std::string consensus_answer;
            double consistency_score;

            switch (voting_strategy_) {
                case VotingStrategy::Majority:
                    std::tie(consensus_answer, consistency_score) = vote_majority(extracted_answers);
                    break;
                case VotingStrategy::Weighted:
                    std::tie(consensus_answer, consistency_score) = vote_weighted(extracted_answers, full_responses);
                    break;
                case VotingStrategy::First:
                    std::tie(consensus_answer, consistency_score) = vote_first(extracted_answers);
                    break;
            }

            // Count answer occurrences
            auto answer_counts = count_answers(extracted_answers);

            // Build response with metadata
            auto response = core::Message::with_text("assistant", consensus_answer);
            response.with_metadata("technique", nlohmann::json("self_consistency"));
            response.with_metadata("num_samples", nlohmann::json(num_samples_));

            std::string strategy_str;
            switch (voting_strategy_) {
                case VotingStrategy::Majority: strategy_str = "majority"; break;
                case VotingStrategy::Weighted: strategy_str = "weighted"; break;
                case VotingStrategy::First: strategy_str = "first"; break;
            }
            response.with_metadata("voting_strategy", nlohmann::json(strategy_str));
            response.with_metadata("consistency_score", nlohmann::json(consistency_score));
            response.with_metadata("samples", nlohmann::json(full_responses));
            response.with_metadata("extracted_answers", nlohmann::json(extracted_answers));
            response.with_metadata("answer_counts", nlohmann::json(answer_counts));
            response.with_metadata("base_agent", nlohmann::json(agent_->name()));

            return core::Result<core::Message, core::AgentError>::ok(response);

        } catch (const std::exception& e) {
            return core::Result<core::Message, core::AgentError>::err(
                core::AgentError(core::AgentErrorType::ProcessingError, e.what())
            );
        }
    });
}

} // namespace reasoning
} // namespace techniques
} // namespace agenkit
