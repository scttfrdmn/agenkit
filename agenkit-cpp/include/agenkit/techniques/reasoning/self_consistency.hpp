/**
 * @file self_consistency.hpp
 * @brief Self-Consistency Reasoning Technique
 *
 * Self-Consistency improves reliability by generating multiple independent reasoning
 * paths and using voting to select the most consistent answer.
 *
 * Reference: "Self-Consistency Improves Chain of Thought Reasoning in Language Models"
 * Wang et al., 2022 - https://arxiv.org/abs/2203.11171
 */

#ifndef AGENKIT_TECHNIQUES_REASONING_SELF_CONSISTENCY_HPP
#define AGENKIT_TECHNIQUES_REASONING_SELF_CONSISTENCY_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <future>

namespace agenkit {
namespace techniques {
namespace reasoning {

/**
 * @brief Voting strategy for answer aggregation
 */
enum class VotingStrategy {
    /** Most common answer wins */
    Majority,
    /** Weight answers by response length */
    Weighted,
    /** Use first answer (no voting, for debugging) */
    First
};

/**
 * @brief Answer extractor function type
 */
using AnswerExtractor = std::function<std::string(const std::string&)>;

/**
 * @brief Default answer extractor that looks for common answer patterns
 *
 * Patterns recognized:
 * - "Therefore, X" / "Thus, X" / "So, X"
 * - "The answer is X"
 * - "= X" (for math)
 * - "Conclusion: X" / "Result: X"
 * - Last non-empty line (fallback)
 *
 * @param text Input text to extract answer from
 * @return Extracted answer
 */
std::string default_answer_extractor(const std::string& text);

/**
 * @brief Configuration for Self-Consistency
 */
struct SelfConsistencyConfig {
    /** Number of independent samples to generate (default: 5) */
    size_t num_samples = 5;

    /** Voting strategy for answer aggregation (default: Majority) */
    VotingStrategy voting_strategy = VotingStrategy::Majority;

    /** Sampling temperature for diversity (optional, not used yet) */
    std::optional<double> temperature;

    /** Custom answer extraction function (optional) */
    std::optional<AnswerExtractor> answer_extractor;
};

/**
 * @brief Self-Consistency agent that wraps a base agent
 *
 * @example
 * @code
 * auto base_agent = std::make_shared<MyAgent>();
 * SelfConsistencyConfig config;
 * config.num_samples = 5;
 * config.voting_strategy = VotingStrategy::Majority;
 *
 * auto sc = std::make_shared<SelfConsistencyAgent>(base_agent, config);
 * auto future = sc->process(Message::with_text("user", "What is 6 * 7?"));
 * auto result = future.get();
 * if (result.is_ok()) {
 *     auto response = result.unwrap();
 *     std::cout << "Consensus: " << response.content_as_str() << std::endl;
 *     std::cout << "Confidence: "
 *               << response.metadata()["consistency_score"] << std::endl;
 * }
 * @endcode
 */
class SelfConsistencyAgent : public core::Agent {
public:
    /**
     * @brief Create a new Self-Consistency agent
     * @param agent Base agent to wrap
     * @param config Configuration options
     */
    SelfConsistencyAgent(
        std::shared_ptr<core::Agent> agent,
        const SelfConsistencyConfig& config = SelfConsistencyConfig{}
    );

    /**
     * @brief Agent identifier
     * @return "self_consistency"
     */
    std::string name() const override;

    /**
     * @brief Agent capabilities
     * @return List of capabilities
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Process a message with Self-Consistency
     *
     * Generates multiple independent samples, extracts answers, and uses
     * voting to determine the most consistent answer.
     *
     * @param message Input message
     * @return Future containing Result<Message, AgentError>
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    struct Sample {
        std::string full_response;
        std::string extracted_answer;
    };

    /**
     * @brief Generate multiple samples in parallel
     * @param message Input message
     * @return Vector of samples
     */
    std::vector<Sample> generate_samples(const core::Message& message);

    /**
     * @brief Vote using majority (most common answer wins)
     * @param answers List of extracted answers
     * @return Pair of (winning answer, consistency score)
     */
    std::pair<std::string, double> vote_majority(const std::vector<std::string>& answers);

    /**
     * @brief Vote using weighted strategy (longer responses get more weight)
     * @param answers List of extracted answers
     * @param responses List of full responses
     * @return Pair of (winning answer, consistency score)
     */
    std::pair<std::string, double> vote_weighted(
        const std::vector<std::string>& answers,
        const std::vector<std::string>& responses
    );

    /**
     * @brief Use first answer (no voting)
     * @param answers List of extracted answers
     * @return Pair of (first answer, 1.0)
     */
    std::pair<std::string, double> vote_first(const std::vector<std::string>& answers);

    /**
     * @brief Count answer occurrences (case-insensitive)
     * @param answers List of extracted answers
     * @return Map of normalized answers to counts
     */
    std::map<std::string, size_t> count_answers(const std::vector<std::string>& answers);

    /**
     * @brief Normalize string for comparison (lowercase, trim)
     * @param str String to normalize
     * @return Normalized string
     */
    std::string normalize_string(const std::string& str);

    std::shared_ptr<core::Agent> agent_;
    size_t num_samples_;
    VotingStrategy voting_strategy_;
    std::optional<double> temperature_;
    AnswerExtractor answer_extractor_;
};

} // namespace reasoning
} // namespace techniques
} // namespace agenkit

#endif // AGENKIT_TECHNIQUES_REASONING_SELF_CONSISTENCY_HPP
