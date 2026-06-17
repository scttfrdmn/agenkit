/**
 * Agent Skills — directory-based, discoverable units of agent capability.
 *
 * Each skill is a directory containing a SKILL.md file with YAML frontmatter
 * (name, description, optional license and metadata) followed by Markdown
 * instructions.
 *
 * Classes:
 *   AgentSkill: A single skill loaded from a directory.
 *   SkillRegistry: Discovers and searches skills across filesystem paths.
 *   SkillEnabledAgent: Wraps an Agent and injects relevant skill instructions.
 *
 * Example:
 *   import { SkillRegistry, SkillEnabledAgent } from 'agenkit';
 *
 *   const registry = new SkillRegistry(['./skills']);
 *   const agent = new SkillEnabledAgent(baseAgent, registry);
 *   const response = await agent.process({ role: 'user', content: 'parse this pdf' });
 */

export { AgentSkill, SkillRegistry } from './loader';
export { SkillEnabledAgent } from './agent';
