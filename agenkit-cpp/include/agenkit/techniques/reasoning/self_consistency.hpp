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
#include "agenkit/core/call_options.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <functional>
#include <future>
#include <memory>
#include <optional>
#include <string>
#include <vector>

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

    /**
     * Sampling temperature for diversity (optional)
     *
     * Forwarded to the wrapped agent on every sample, if that agent honours
     * per-call options. `std::nullopt` means unset — no temperature is sent,
     * rather than one being invented. See temperature_applied().
     *
     * Sample diversity is the mechanism this technique depends on: N samples
     * at temperature 0 would all be the same answer, and voting over identical
     * answers decides nothing.
     */
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
class SelfConsistencyAgent : public core::Agent, public core::OptionsAgent {
public:
    /**
     * @brief Create a new Self-Consistency agent
     * @param agent Base agent to wrap
     * @param config Configuration options
     *
     * @throws std::invalid_argument if config.temperature is set and outside
     *         0.0-2.0. Rejected here rather than on the first sample, so an
     *         unusable configuration fails where it was written.
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

    /**
     * @brief Process a message with Self-Consistency, honouring per-call options
     *
     * The configured temperature wins over one supplied by the caller — sample
     * diversity is what makes this technique correct, so it is not something a
     * caller can flatten by accident. Every other option passes through
     * untouched. process() is this method with an empty option set.
     *
     * @param message Input message
     * @param options Per-call options; merged under the configured temperature
     * @return Future containing Result<Message, AgentError>
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process_with(core::Message message, const core::CallOptions& options) override;

    /**
     * @brief Whether a configured temperature actually reaches the wrapped agent
     *
     * True when no temperature is configured (nothing to drop), and when one is
     * configured and the wrapped agent honours per-call options. False when a
     * temperature is set but the wrapped agent only implements process(), in
     * which case the value is silently discarded.
     *
     * Exposed because honouring options is optional: without this, a dropped
     * temperature would be invisible, which is the bug this method exists to
     * make impossible to reintroduce quietly.
     *
     * @return true if the configured temperature (if any) is applied
     */
    bool temperature_applied() const;

private:
    struct Sample {
        std::string full_response;
        std::string extracted_answer;
    };

    /**
     * @brief Generate multiple samples in parallel
     * @param message Input message
     * @param options Per-call options forwarded to every sample
     * @return Vector of samples
     */
    std::vector<Sample> generate_samples(
        const core::Message& message,
        const core::CallOptions& options
    );

    /**
     * @brief Overlay the configured temperature on the caller's options
     * @param caller Options supplied by the caller
     * @return Merged options
     */
    core::CallOptions call_options(const core::CallOptions& caller) const;

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
