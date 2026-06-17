package io.agenkit.skills;

import io.agenkit.core.Agent;
import io.agenkit.core.IntrospectionResult;
import io.agenkit.core.Message;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

/**
 * Agent wrapper that automatically injects relevant skill instructions.
 *
 * <p>Before delegating to the wrapped agent, this wrapper queries the registry
 * for skills relevant to the incoming message and prepends their instructions
 * inside an {@code <available_skills>} block. The response's metadata will
 * contain {@code active_skills} listing the skill names that were injected.
 */
public final class SkillEnabledAgent implements Agent {

    private static final String SKILL_INJECTION = "skill_injection";

    private final Agent agent;
    private final SkillRegistry registry;
    private final int maxActiveSkills;

    /**
     * @param agent base agent to delegate processing to
     * @param registry registry used to look up relevant skills
     * @param maxActiveSkills maximum number of skills to inject (default 3)
     * @param autoDiscover whether to call {@link SkillRegistry#discoverSkills()}
     *        at construction time (default true)
     */
    public SkillEnabledAgent(
            Agent agent,
            SkillRegistry registry,
            int maxActiveSkills,
            boolean autoDiscover) {
        this.agent = agent;
        this.registry = registry;
        this.maxActiveSkills = maxActiveSkills;
        if (autoDiscover) {
            this.registry.discoverSkills();
        }
    }

    /** Construct with the default maximum of 3 active skills and auto-discovery enabled. */
    public SkillEnabledAgent(Agent agent, SkillRegistry registry) {
        this(agent, registry, 3, true);
    }

    @Override
    public String getName() {
        return agent.getName();
    }

    @Override
    public List<String> getCapabilities() {
        List<String> base = new ArrayList<>(agent.getCapabilities());
        if (!base.contains(SKILL_INJECTION)) {
            base.add(SKILL_INJECTION);
        }
        return base;
    }

    @Override
    public IntrospectionResult introspect() {
        return agent.introspect();
    }

    @Override
    public CompletableFuture<Message> process(Message message) {
        String query = message.contentString();
        List<AgentSkill> relevant = registry.findRelevantSkills(query, maxActiveSkills);

        if (relevant.isEmpty()) {
            return agent.process(message);
        }

        String skillBlocks = relevant.stream()
                .map(AgentSkill::toPrompt)
                .collect(Collectors.joining("\n\n"));
        String prefix = "<available_skills>\n" + skillBlocks + "\n</available_skills>\n\n";
        String augmentedContent = prefix + query;

        Map<String, Object> newMetadata = new HashMap<>(message.getMetadata());
        newMetadata.put("active_skills",
                relevant.stream().map(AgentSkill::getName).collect(Collectors.toList()));

        Message enhanced = new Message(
                message.getRole(), augmentedContent, newMetadata, message.getTimestamp());

        return agent.process(enhanced);
    }
}
