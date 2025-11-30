/**
 * @file router.cpp
 * @brief Implementation of Router pattern
 */

#include "agenkit/patterns/router.hpp"
#include <sstream>
#include <unordered_set>
#include <algorithm>
#include <cctype>

namespace agenkit {
namespace patterns {

RouterAgent::RouterAgent(RouterConfig config)
    : classifier_(std::move(config.classifier))
    , agents_(std::move(config.agents))
    , default_key_(std::move(config.default_key))
{
    if (!classifier_) {
        throw std::invalid_argument("classifier is required");
    }
    if (agents_.empty()) {
        throw std::invalid_argument("at least one agent is required");
    }

    // Validate default key if provided
    if (default_key_.has_value()) {
        if (agents_.find(default_key_.value()) == agents_.end()) {
            std::ostringstream oss;
            oss << "default key '" << default_key_.value() << "' not found in agents map";
            throw std::invalid_argument(oss.str());
        }
    }
}

std::string RouterAgent::name() const {
    return "router";
}

std::vector<std::string> RouterAgent::capabilities() const {
    // Collect unique capabilities from all agents
    std::unordered_set<std::string> cap_set;

    // Add classifier capabilities
    auto classifier_caps = classifier_->capabilities();
    cap_set.insert(classifier_caps.begin(), classifier_caps.end());

    // Add agent capabilities
    for (const auto& [category, agent] : agents_) {
        auto agent_caps = agent->capabilities();
        cap_set.insert(agent_caps.begin(), agent_caps.end());
    }

    // Convert to vector
    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());

    // Add router-specific capabilities
    capabilities.push_back("router");
    capabilities.push_back("conditional");
    capabilities.push_back("classification");

    return capabilities;
}

std::future<core::Result<core::Message, core::AgentError>>
RouterAgent::process(core::Message message) {
    // Step 1: Classify the message
    auto classify_result = classifier_->classify(message);

    if (classify_result.is_err()) {
        auto error = classify_result.unwrap_err();
        std::ostringstream oss;
        oss << "classification failed: " << error.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    std::string category = classify_result.unwrap();

    // Step 2: Select agent based on category
    auto agent_it = agents_.find(category);
    std::shared_ptr<core::Agent> agent;

    if (agent_it == agents_.end()) {
        // Try default agent if configured
        if (default_key_.has_value()) {
            agent = agents_[default_key_.value()];
            category = default_key_.value(); // Update category to reflect actual routing
        } else {
            std::vector<std::string> available_categories;
            available_categories.reserve(agents_.size());
            for (const auto& [cat, _] : agents_) {
                available_categories.push_back(cat);
            }

            std::ostringstream oss;
            oss << "no agent found for category '" << category << "' (available: ";
            for (size_t i = 0; i < available_categories.size(); ++i) {
                if (i > 0) oss << ", ";
                oss << available_categories[i];
            }
            oss << ")";

            return core::make_ready_future(
                core::Result<core::Message, core::AgentError>::err(
                    core::AgentError(core::AgentErrorType::NotFound, oss.str())
                )
            );
        }
    } else {
        agent = agent_it->second;
    }

    // Step 3: Execute selected agent
    auto future = agent->process(std::move(message));
    auto result = future.get();

    if (result.is_err()) {
        auto error = result.unwrap_err();
        std::ostringstream oss;
        oss << "agent '" << agent->name() << "' (category: " << category
            << ") failed: " << error.message();

        return core::make_ready_future(
            core::Result<core::Message, core::AgentError>::err(
                core::AgentError(error.type(), oss.str())
            )
        );
    }

    auto response = result.unwrap();

    // Add routing metadata
    response.with_metadata("routed_category", category);
    response.with_metadata("routed_agent", agent->name());
    response.with_metadata("available_routes", static_cast<int>(agents_.size()));

    return core::make_ready_future(
        core::Result<core::Message, core::AgentError>::ok(response)
    );
}

// SimpleClassifier implementation

SimpleClassifier::SimpleClassifier(
    std::shared_ptr<core::Agent> agent,
    std::unordered_map<std::string, std::vector<std::string>> keywords
)
    : agent_(std::move(agent))
    , keywords_(std::move(keywords))
{
    if (!agent_) {
        throw std::invalid_argument("agent is required");
    }
}

std::string SimpleClassifier::name() const {
    return "simple_classifier";
}

std::vector<std::string> SimpleClassifier::capabilities() const {
    auto caps = agent_->capabilities();
    caps.push_back("classification");
    caps.push_back("keyword-matching");
    return caps;
}

std::future<core::Result<core::Message, core::AgentError>>
SimpleClassifier::process(core::Message message) {
    return agent_->process(std::move(message));
}

core::Result<std::string, core::AgentError>
SimpleClassifier::classify(const core::Message& message) {
    std::string content = message.content_as_str();

    // Convert to lowercase for case-insensitive matching
    std::transform(content.begin(), content.end(), content.begin(),
                   [](unsigned char c) { return std::tolower(c); });

    // Check each category's keywords
    int max_matches = 0;
    std::string best_category;

    for (const auto& [category, keywords] : keywords_) {
        int matches = 0;
        for (const auto& keyword : keywords) {
            std::string lower_keyword = keyword;
            std::transform(lower_keyword.begin(), lower_keyword.end(),
                          lower_keyword.begin(),
                          [](unsigned char c) { return std::tolower(c); });

            if (content.find(lower_keyword) != std::string::npos) {
                matches++;
            }
        }

        if (matches > max_matches) {
            max_matches = matches;
            best_category = category;
        }
    }

    if (best_category.empty()) {
        return core::Result<std::string, core::AgentError>::err(
            core::AgentError(
                core::AgentErrorType::ProcessingError,
                "unable to classify message - no keyword matches found"
            )
        );
    }

    return core::Result<std::string, core::AgentError>::ok(best_category);
}

// LLMClassifier implementation

LLMClassifier::LLMClassifier(
    std::shared_ptr<core::Agent> agent,
    std::vector<std::string> categories
)
    : agent_(std::move(agent))
    , categories_(std::move(categories))
{
    if (!agent_) {
        throw std::invalid_argument("agent is required");
    }

    if (categories_.empty()) {
        categories_.push_back("general");
    }

    // Build prompt template
    std::ostringstream prompt;
    prompt << "Classify the following message into one of these categories: ";
    for (size_t i = 0; i < categories_.size(); ++i) {
        if (i > 0) prompt << ", ";
        prompt << categories_[i];
    }
    prompt << "\n\nReply with ONLY the category name, nothing else.\n\nMessage: ";

    prompt_template_ = prompt.str();
}

std::string LLMClassifier::name() const {
    return "llm_classifier";
}

std::vector<std::string> LLMClassifier::capabilities() const {
    auto caps = agent_->capabilities();
    caps.push_back("classification");
    caps.push_back("llm-classification");
    return caps;
}

std::future<core::Result<core::Message, core::AgentError>>
LLMClassifier::process(core::Message message) {
    return agent_->process(std::move(message));
}

core::Result<std::string, core::AgentError>
LLMClassifier::classify(const core::Message& message) {
    // Build classification prompt
    std::string classification_content = prompt_template_ + message.content_as_str();
    auto classification_msg = core::Message::with_text("user", classification_content);

    // Get LLM classification
    auto future = agent_->process(std::move(classification_msg));
    auto result = future.get();

    if (result.is_err()) {
        auto error = result.unwrap_err();
        std::ostringstream oss;
        oss << "llm classification failed: " << error.message();

        return core::Result<std::string, core::AgentError>::err(
            core::AgentError(error.type(), oss.str())
        );
    }

    auto response = result.unwrap();
    std::string category = response.content_as_str();

    // Trim whitespace
    category.erase(0, category.find_first_not_of(" \t\n\r"));
    category.erase(category.find_last_not_of(" \t\n\r") + 1);

    // Validate category is in allowed list (case-insensitive)
    std::string lower_category = category;
    std::transform(lower_category.begin(), lower_category.end(),
                   lower_category.begin(),
                   [](unsigned char c) { return std::tolower(c); });

    for (const auto& valid_cat : categories_) {
        std::string lower_valid = valid_cat;
        std::transform(lower_valid.begin(), lower_valid.end(),
                      lower_valid.begin(),
                      [](unsigned char c) { return std::tolower(c); });

        if (lower_category == lower_valid) {
            return core::Result<std::string, core::AgentError>::ok(valid_cat);
        }
    }

    // Category not found
    std::ostringstream oss;
    oss << "llm returned invalid category '" << category << "' (valid: ";
    for (size_t i = 0; i < categories_.size(); ++i) {
        if (i > 0) oss << ", ";
        oss << categories_[i];
    }
    oss << ")";

    return core::Result<std::string, core::AgentError>::err(
        core::AgentError(core::AgentErrorType::ProcessingError, oss.str())
    );
}

} // namespace patterns
} // namespace agenkit
