/**
 * @file call_options.cpp
 * @brief Implementation of CallOptions and the OptionsAgent capability
 */

#include "agenkit/core/call_options.hpp"
#include "agenkit/adapters/validation.hpp"
#include <utility>

namespace agenkit {
namespace core {

void CallOptions::validate() const {
    // Validated through the shared adapter validator so the bounds cannot drift
    // apart from the ones the adapters themselves enforce.
    if (temperature.has_value()) {
        adapters::LLMParameterValidator::validate_temperature(temperature.value());
    }
    if (max_tokens.has_value()) {
        adapters::LLMParameterValidator::validate_max_tokens(max_tokens.value());
    }
    if (top_p.has_value()) {
        adapters::LLMParameterValidator::validate_top_p(top_p.value());
    }
}

bool CallOptions::empty() const {
    return !temperature.has_value()
        && !max_tokens.has_value()
        && !top_p.has_value()
        && !seed.has_value()
        && !stop.has_value()
        && extra.empty();
}

nlohmann::json CallOptions::to_params() const {
    nlohmann::json params = nlohmann::json::object();

    // has_value(), not truthiness: temperature 0.0 is greedy decoding, a real
    // request, and must reach the provider.
    if (temperature.has_value()) {
        params["temperature"] = temperature.value();
    }
    if (max_tokens.has_value()) {
        params["max_tokens"] = max_tokens.value();
    }
    if (top_p.has_value()) {
        params["top_p"] = top_p.value();
    }
    if (seed.has_value()) {
        params["seed"] = seed.value();
    }
    if (stop.has_value()) {
        params["stop"] = stop.value();
    }
    for (const auto& [key, value] : extra.items()) {
        params[key] = value;
    }

    return params;
}

CallOptions CallOptions::merge(const CallOptions& overrides) const {
    CallOptions merged = *this;

    // Field by field: an unset field in `overrides` means "did not ask", not
    // "clear it". Assigning unconditionally would let a caller forwarding an
    // unset optional erase the base value.
    if (overrides.temperature.has_value()) {
        merged.temperature = overrides.temperature;
    }
    if (overrides.max_tokens.has_value()) {
        merged.max_tokens = overrides.max_tokens;
    }
    if (overrides.top_p.has_value()) {
        merged.top_p = overrides.top_p;
    }
    if (overrides.seed.has_value()) {
        merged.seed = overrides.seed;
    }
    if (overrides.stop.has_value()) {
        merged.stop = overrides.stop;
    }
    for (const auto& [key, value] : overrides.extra.items()) {
        merged.extra[key] = value;
    }

    return merged;
}

CallOptions CallOptions::with_temperature(double value) const {
    adapters::LLMParameterValidator::validate_temperature(value);
    CallOptions copy = *this;
    copy.temperature = value;
    return copy;
}

CallOptions CallOptions::with_max_tokens(int value) const {
    adapters::LLMParameterValidator::validate_max_tokens(value);
    CallOptions copy = *this;
    copy.max_tokens = value;
    return copy;
}

CallOptions CallOptions::with_top_p(double value) const {
    adapters::LLMParameterValidator::validate_top_p(value);
    CallOptions copy = *this;
    copy.top_p = value;
    return copy;
}

CallOptions CallOptions::with_seed(uint64_t value) const {
    CallOptions copy = *this;
    copy.seed = value;
    return copy;
}

CallOptions CallOptions::with_stop(std::vector<std::string> value) const {
    CallOptions copy = *this;
    copy.stop = std::move(value);
    return copy;
}

CallOptions CallOptions::with_extra(const std::string& key, nlohmann::json value) const {
    CallOptions copy = *this;
    copy.extra[key] = std::move(value);
    return copy;
}

bool supports_options(Agent* agent) {
    return dynamic_cast<OptionsAgent*>(agent) != nullptr;
}

std::future<Result<Message, AgentError>>
process_with_options(Agent* agent, Message message, const CallOptions& options) {
    if (agent == nullptr) {
        return make_ready_future(Result<Message, AgentError>::err(
            AgentError(AgentErrorType::ProcessingError, "agent is null")
        ));
    }

    // No options to honour: take the plain path rather than handing an
    // OptionsAgent an empty set just because this helper was used.
    if (options.empty()) {
        return agent->process(std::move(message));
    }

    if (auto* options_agent = dynamic_cast<OptionsAgent*>(agent)) {
        return options_agent->process_with(std::move(message), options);
    }

    return agent->process(std::move(message));
}

std::future<Result<Message, AgentError>>
process_with_options(
    const std::shared_ptr<Agent>& agent,
    Message message,
    const CallOptions& options
) {
    return process_with_options(agent.get(), std::move(message), options);
}

} // namespace core
} // namespace agenkit
