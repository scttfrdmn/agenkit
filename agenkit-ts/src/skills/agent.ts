/**
 * SkillEnabledAgent — wraps an Agent and injects relevant skill instructions.
 */

import { Agent, Message } from '../core/interfaces';
import { IntrospectionResult } from '../core/introspection';
import { SkillRegistry } from './loader';

/**
 * Agent wrapper that automatically injects relevant skill instructions.
 *
 * Before delegating to the wrapped agent, this wrapper queries the registry
 * for skills relevant to the incoming message and prepends their instructions
 * inside an `<available_skills>` block. The response's metadata will contain
 * `active_skills` listing the skill names that were injected.
 */
export class SkillEnabledAgent implements Agent {
  private readonly agent: Agent;
  private readonly registry: SkillRegistry;
  private readonly maxActiveSkills: number;

  /**
   * @param agent Base agent to delegate processing to.
   * @param registry SkillRegistry used to look up relevant skills.
   * @param maxActiveSkills Maximum number of skills to inject (default 3).
   * @param autoDiscover Whether to call `registry.discoverSkills()` at
   *   construction time (default true).
   */
  constructor(
    agent: Agent,
    registry: SkillRegistry,
    maxActiveSkills = 3,
    autoDiscover = true,
  ) {
    this.agent = agent;
    this.registry = registry;
    this.maxActiveSkills = maxActiveSkills;
    if (autoDiscover) {
      this.registry.discoverSkills();
    }
  }

  get name(): string {
    return this.agent.name;
  }

  get capabilities(): string[] {
    const base = [...(this.agent.capabilities ?? [])];
    if (!base.includes('skill_injection')) {
      base.push('skill_injection');
    }
    return base;
  }

  introspect(): IntrospectionResult {
    if (this.agent.introspect) {
      return this.agent.introspect();
    }
    return {
      timestamp: new Date().toISOString(),
      agentName: this.name,
      capabilities: this.capabilities,
      internalState: {},
      metadata: {},
    };
  }

  /**
   * Process a message, injecting relevant skill instructions first.
   *
   * Finds skills relevant to the message content, builds an
   * `<available_skills>` block, and prepends it to the message content before
   * passing to the wrapped agent. The returned message's metadata will include
   * `active_skills`.
   */
  async process(message: Message): Promise<Message> {
    const query = message.content != null ? String(message.content) : '';
    const relevant = this.registry.findRelevantSkills(query, this.maxActiveSkills);

    if (relevant.length > 0) {
      const skillBlocks = relevant.map((skill) => skill.toPrompt()).join('\n\n');
      const prefix = `<available_skills>\n${skillBlocks}\n</available_skills>\n\n`;
      const augmentedContent = prefix + query;

      const newMetadata: Record<string, unknown> = { ...(message.metadata ?? {}) };
      newMetadata.active_skills = relevant.map((skill) => skill.name);

      const enhanced: Message = {
        ...message,
        content: augmentedContent,
        metadata: newMetadata,
      };
      return this.agent.process(enhanced);
    }

    return this.agent.process(message);
  }
}
