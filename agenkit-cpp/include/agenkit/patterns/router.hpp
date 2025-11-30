/**
 * @file router.hpp
 * @brief Router conditional agent selection pattern
 *
 * This module provides the Router pattern for conditional agent selection based on message
 * classification. A classifier determines the intent/category, then routes
 * the request to an appropriate specialist agent.
 */

#ifndef AGENKIT_PATTERNS_ROUTER_HPP
#define AGENKIT_PATTERNS_ROUTER_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include <memory>
#include <vector>
#include <string>
#include <unordered_map>
#include <optional>

namespace agenkit {
namespace patterns {

/**
 * @brief Classifier agent interface for determining routing decisions
 *
 * The classifier analyzes the input message and returns a category/intent
 * that determines which specialist agent should handle the request.
 */
class ClassifierAgent : public core::Agent {
public:
    /**
     * @brief Classify determines the category/intent for routing
     * @param message Input message to classify
     * @return Result containing category string or error
     */
    virtual core::Result<std::string, core::AgentError>
    classify(const core::Message& message) = 0;
};

/**
 * @brief Configuration for RouterAgent
 */
struct RouterConfig {
    /// Classifier determines which agent to route to
    std::shared_ptr<ClassifierAgent> classifier;
    /// Agents maps categories to specialist agents
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents;
    /// DefaultKey specifies fallback agent when classification doesn't match (optional)
    std::optional<std::string> default_key;
};

/**
 * @brief Router agent for conditional agent selection
 *
 * The RouterAgent routes messages to appropriate agents based on classification.
 * The router uses a classifier to determine message intent/category, then
 * delegates to the corresponding specialist agent. This enables efficient
 * conditional processing without executing all agents.
 *
 * Key concepts:
 * - Intent/category classification
 * - Conditional routing to specialists
 * - Single agent execution per request
 * - Dynamic agent selection based on input
 *
 * Performance characteristics:
 * - Time: O(classification + selected agent)
 * - Memory: O(1) - only one agent executes
 * - Efficient single-path execution
 *
 * Example use cases:
 * - Customer service: route to billing, technical, account agents
 * - Content moderation: route to spam, abuse, quality agents
 * - Language routing: route to language-specific agents
 * - Skill-based routing: route to domain expert agents
 * - Intent-based chatbots: route to booking, info, support agents
 *
 * The router pattern is ideal when requests have clear categories and
 * different agents handle different types of requests.
 *
 * @example
 * @code
 * auto classifier = std::make_shared<IntentClassifier>();
 * std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents = {
 *     {"billing", std::make_shared<BillingAgent>()},
 *     {"technical", std::make_shared<TechnicalAgent>()},
 *     {"account", std::make_shared<AccountAgent>()}
 * };
 *
 * RouterConfig config{classifier, agents, "technical"};
 * RouterAgent router(config);
 *
 * auto msg = core::Message::with_text("user", "How do I reset my password?");
 * auto result = router.process(std::move(msg)).get();
 * @endcode
 */
class RouterAgent : public core::Agent {
public:
    /**
     * @brief Construct a router agent
     * @param config Router configuration with classifier and agents
     * @throws std::invalid_argument if config is invalid
     */
    explicit RouterAgent(RouterConfig config);

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<ClassifierAgent> classifier_;
    std::unordered_map<std::string, std::shared_ptr<core::Agent>> agents_;
    std::optional<std::string> default_key_;
};

/**
 * @brief Simple classifier using keyword matching
 *
 * This classifier uses simple string matching to determine categories.
 * For production use, consider implementing a custom ClassifierAgent with
 * ML-based classification or more sophisticated logic.
 */
class SimpleClassifier : public ClassifierAgent {
public:
    /**
     * @brief Create a keyword-based classifier
     * @param agent Fallback agent for complex classifications
     * @param keywords Map of categories to keyword lists
     */
    SimpleClassifier(
        std::shared_ptr<core::Agent> agent,
        std::unordered_map<std::string, std::vector<std::string>> keywords
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    core::Result<std::string, core::AgentError>
    classify(const core::Message& message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    std::unordered_map<std::string, std::vector<std::string>> keywords_;
};

/**
 * @brief LLM-based classifier
 *
 * This classifier prompts an LLM to determine the category. The LLM is given
 * a list of valid categories and must respond with one of them.
 */
class LLMClassifier : public ClassifierAgent {
public:
    /**
     * @brief Create an LLM-based classifier
     * @param agent LLM agent for classification
     * @param categories List of valid category names
     */
    LLMClassifier(
        std::shared_ptr<core::Agent> agent,
        std::vector<std::string> categories
    );

    std::string name() const override;

    std::vector<std::string> capabilities() const override;

    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

    core::Result<std::string, core::AgentError>
    classify(const core::Message& message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    std::vector<std::string> categories_;
    std::string prompt_template_;
};

} // namespace patterns
} // namespace agenkit

#endif // AGENKIT_PATTERNS_ROUTER_HPP
