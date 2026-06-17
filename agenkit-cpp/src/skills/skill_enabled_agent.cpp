/**
 * @file skill_enabled_agent.cpp
 * @brief SkillEnabledAgent implementation.
 */

#include "agenkit/skills/skill_enabled_agent.hpp"

#include <algorithm>
#include <utility>

namespace agenkit {
namespace skills {

SkillEnabledAgent::SkillEnabledAgent(std::shared_ptr<core::Agent> agent,
                                     std::shared_ptr<SkillRegistry> registry,
                                     std::size_t max_active_skills,
                                     bool auto_discover)
    : agent_(std::move(agent)),
      registry_(std::move(registry)),
      max_active_skills_(max_active_skills) {
    if (auto_discover && registry_) {
        registry_->discover_skills();
    }
}

std::string SkillEnabledAgent::name() const {
    return agent_->name();
}

std::vector<std::string> SkillEnabledAgent::capabilities() const {
    std::vector<std::string> caps = agent_->capabilities();
    if (std::find(caps.begin(), caps.end(), "skill_injection") == caps.end()) {
        caps.push_back("skill_injection");
    }
    return caps;
}

std::future<core::Result<core::Message, core::AgentError>>
SkillEnabledAgent::process(core::Message message) {
    const std::string query = message.content_as_str();

    std::vector<AgentSkill> relevant;
    if (registry_) {
        relevant = registry_->find_relevant_skills(query, max_active_skills_);
    }

    if (relevant.empty()) {
        return agent_->process(std::move(message));
    }

    // Build the <available_skills> block from the relevant skills.
    std::string skill_blocks;
    for (std::size_t i = 0; i < relevant.size(); ++i) {
        if (i > 0) {
            skill_blocks += "\n\n";
        }
        skill_blocks += relevant[i].to_prompt();
    }

    const std::string augmented_content =
        "<available_skills>\n" + skill_blocks + "\n</available_skills>\n\n" + query;

    // Preserve existing metadata, then record the active skill names.
    nlohmann::json metadata = message.metadata();
    nlohmann::json active = nlohmann::json::array();
    for (const auto& skill : relevant) {
        active.push_back(skill.name);
    }

    core::Message enhanced(message.role(), nlohmann::json(augmented_content));
    if (metadata.is_object()) {
        for (auto it = metadata.begin(); it != metadata.end(); ++it) {
            enhanced.with_metadata(it.key(), it.value());
        }
    }
    enhanced.with_metadata("active_skills", active);

    return agent_->process(std::move(enhanced));
}

} // namespace skills
} // namespace agenkit
