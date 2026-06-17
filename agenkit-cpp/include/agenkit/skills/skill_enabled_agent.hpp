/**
 * @file skill_enabled_agent.hpp
 * @brief SkillEnabledAgent — wraps an Agent and injects relevant skill instructions.
 *
 * Mirrors the Python reference implementation (agenkit/skills/agent.py).
 */

#ifndef AGENKIT_SKILLS_SKILL_ENABLED_AGENT_HPP
#define AGENKIT_SKILLS_SKILL_ENABLED_AGENT_HPP

#include "agenkit/core/agent.hpp"
#include "agenkit/core/message.hpp"
#include "agenkit/core/result.hpp"
#include "agenkit/skills/skill.hpp"

#include <cstddef>
#include <future>
#include <memory>
#include <string>
#include <vector>

namespace agenkit {
namespace skills {

/**
 * @brief Agent wrapper that automatically injects relevant skill instructions.
 *
 * Before delegating to the wrapped agent, this wrapper queries the registry for
 * skills relevant to the incoming message and prepends their instructions
 * inside an `<available_skills>` block. The response's metadata will contain
 * `active_skills` listing the skill names that were injected.
 */
class SkillEnabledAgent : public core::Agent {
public:
    /**
     * @brief Construct a skill-enabled agent.
     *
     * @param agent Base agent to delegate processing to.
     * @param registry SkillRegistry used to look up relevant skills.
     * @param max_active_skills Maximum number of skills to inject (default 3).
     * @param auto_discover Whether to call registry.discover_skills() at
     *        construction time (default true).
     */
    SkillEnabledAgent(std::shared_ptr<core::Agent> agent,
                      std::shared_ptr<SkillRegistry> registry,
                      std::size_t max_active_skills = 3,
                      bool auto_discover = true);

    /**
     * @brief Delegate to the wrapped agent's name.
     */
    std::string name() const override;

    /**
     * @brief Wrapped agent capabilities plus "skill_injection".
     */
    std::vector<std::string> capabilities() const override;

    /**
     * @brief Process a message, injecting relevant skill instructions first.
     *
     * Finds skills relevant to the message content, builds an
     * `<available_skills>` block, prepends it to the message content, and sets
     * `active_skills` metadata before delegating to the wrapped agent.
     *
     * @param message Input message.
     * @return Future with the wrapped agent's response.
     */
    std::future<core::Result<core::Message, core::AgentError>>
    process(core::Message message) override;

private:
    std::shared_ptr<core::Agent> agent_;
    std::shared_ptr<SkillRegistry> registry_;
    std::size_t max_active_skills_;
};

} // namespace skills
} // namespace agenkit

#endif // AGENKIT_SKILLS_SKILL_ENABLED_AGENT_HPP
