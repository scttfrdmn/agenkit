/**
 * @file parallel.cpp
 * @brief Implementation of ParallelAgent
 */

#include "agenkit/composition/parallel.hpp"
#include <stdexcept>
#include <set>
#include <sstream>

namespace agenkit {
namespace composition {

using namespace core;

ParallelAgent::ParallelAgent(
    std::string name,
    std::vector<std::shared_ptr<Agent>> agents
) : name_(std::move(name)), agents_(std::move(agents)) {
    if (agents_.empty()) {
        throw std::invalid_argument("Parallel agent requires at least one agent");
    }
}

std::vector<std::string> ParallelAgent::capabilities() const {
    std::set<std::string> cap_set;

    for (const auto& agent : agents_) {
        for (const auto& cap : agent->capabilities()) {
            cap_set.insert(cap);
        }
    }

    std::vector<std::string> capabilities(cap_set.begin(), cap_set.end());
    capabilities.push_back("parallel");

    return capabilities;
}

std::future<Result<Message, AgentError>>
ParallelAgent::process(Message message) {
    return std::async(std::launch::async, [this, message]() {
        // Launch all agents concurrently
        std::vector<std::future<Result<Message, AgentError>>> futures;
        futures.reserve(agents_.size());

        for (const auto& agent : agents_) {
            futures.push_back(agent->process(message));
        }

        // Collect results
        std::vector<std::string> content_parts;
        std::vector<std::string> errors;

        for (size_t i = 0; i < futures.size(); ++i) {
            try {
                auto result = futures[i].get();

                if (result.is_err()) {
                    errors.push_back(agents_[i]->name() + ": " + result.unwrap_err().message());
                } else {
                    content_parts.push_back(
                        "[" + agents_[i]->name() + "]: " + result.unwrap().content_as_str()
                    );
                }
            } catch (const std::exception& e) {
                errors.push_back(agents_[i]->name() + ": " + std::string(e.what()));
            }
        }

        if (!errors.empty()) {
            std::ostringstream oss;
            oss << "Parallel execution had errors: ";
            for (size_t i = 0; i < errors.size(); ++i) {
                if (i > 0) oss << "; ";
                oss << errors[i];
            }
            return Result<Message, AgentError>::err(AgentError(
                AgentErrorType::ProcessingError,
                oss.str()
            ));
        }

        // Combine content
        std::ostringstream combined;
        for (size_t i = 0; i < content_parts.size(); ++i) {
            if (i > 0) combined << "\n";
            combined << content_parts[i];
        }

        return Result<Message, AgentError>::ok(Message::with_text("agent", combined.str()));
    });
}

} // namespace composition
} // namespace agenkit
