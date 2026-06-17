/**
 * Tests for Agent Skills: AgentSkill, SkillRegistry, and SkillEnabledAgent.
 *
 * Ported from the Python reference suites:
 *   tests/skills/test_skill_loader.py
 *   tests/skills/test_skill_agent.py
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

import { AgentSkill, SkillRegistry } from '../skills/loader';
import { SkillEnabledAgent } from '../skills/agent';
import { Agent, Message } from '../core/interfaces';

// ---------------------------------------------------------------------------
// Fixture helpers
// ---------------------------------------------------------------------------

let tmpRoot: string;

beforeEach(() => {
  tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'agenkit-skills-'));
});

afterEach(() => {
  fs.rmSync(tmpRoot, { recursive: true, force: true });
});

function makeSkillDir(
  root: string,
  name: string,
  description: string,
  body = 'Instructions here.',
): string {
  const skillDir = path.join(root, name);
  fs.mkdirSync(skillDir);
  const content = `---\nname: ${name}\ndescription: ${description}\n---\n${body}`;
  fs.writeFileSync(path.join(skillDir, 'SKILL.md'), content, 'utf-8');
  return skillDir;
}

// ---------------------------------------------------------------------------
// AgentSkill.fromDirectory
// ---------------------------------------------------------------------------

describe('AgentSkill.fromDirectory', () => {
  it('loads a valid skill', () => {
    const skillDir = makeSkillDir(
      tmpRoot,
      'pdf-processing',
      'Extract text from PDFs.',
      '# PDF\nDo stuff.',
    );
    const skill = AgentSkill.fromDirectory(skillDir);

    expect(skill.name).toBe('pdf-processing');
    expect(skill.description).toBe('Extract text from PDFs.');
    expect(skill.instructions).toContain('Do stuff.');
    expect(skill.skillDir).toBe(skillDir);
  });

  it('loads license and metadata', () => {
    const skillDir = path.join(tmpRoot, 'advanced');
    fs.mkdirSync(skillDir);
    const content =
      '---\n' +
      'name: advanced\n' +
      'description: Advanced skill.\n' +
      'license: Apache-2.0\n' +
      'metadata:\n' +
      "  version: '1.0'\n" +
      '---\n' +
      'Advanced instructions.';
    fs.writeFileSync(path.join(skillDir, 'SKILL.md'), content, 'utf-8');
    const skill = AgentSkill.fromDirectory(skillDir);

    expect(skill.license).toBe('Apache-2.0');
    expect(skill.metadata).toEqual({ version: '1.0' });
  });

  it('throws when SKILL.md is missing', () => {
    const emptyDir = path.join(tmpRoot, 'empty');
    fs.mkdirSync(emptyDir);
    expect(() => AgentSkill.fromDirectory(emptyDir)).toThrow(/No SKILL\.md found/);
  });

  it('throws on missing frontmatter delimiters', () => {
    const skillDir = path.join(tmpRoot, 'bad');
    fs.mkdirSync(skillDir);
    // Missing second "---" delimiter.
    fs.writeFileSync(
      path.join(skillDir, 'SKILL.md'),
      'name: foo\ndescription: bar\n',
      'utf-8',
    );
    expect(() => AgentSkill.fromDirectory(skillDir)).toThrow(
      /missing frontmatter delimiters/,
    );
  });

  it('throws on missing name', () => {
    const skillDir = path.join(tmpRoot, 'noname');
    fs.mkdirSync(skillDir);
    const content = '---\ndescription: A skill without a name.\n---\nInstructions.';
    fs.writeFileSync(path.join(skillDir, 'SKILL.md'), content, 'utf-8');
    expect(() => AgentSkill.fromDirectory(skillDir)).toThrow(
      /Missing required field 'name'/,
    );
  });

  it('throws on missing description', () => {
    const skillDir = path.join(tmpRoot, 'nodesc');
    fs.mkdirSync(skillDir);
    const content = '---\nname: nodesc\n---\nInstructions.';
    fs.writeFileSync(path.join(skillDir, 'SKILL.md'), content, 'utf-8');
    expect(() => AgentSkill.fromDirectory(skillDir)).toThrow(
      /Missing required field 'description'/,
    );
  });

  it('renders toPrompt', () => {
    const skillDir = makeSkillDir(
      tmpRoot,
      'csv-tools',
      'Handle CSV files.',
      'Parse and write CSV.',
    );
    const skill = AgentSkill.fromDirectory(skillDir);
    const prompt = skill.toPrompt();

    expect(prompt).toContain('# Skill: csv-tools');
    expect(prompt).toContain('## Description');
    expect(prompt).toContain('Handle CSV files.');
    expect(prompt).toContain('## Instructions');
    expect(prompt).toContain('Parse and write CSV.');
  });
});

// ---------------------------------------------------------------------------
// SkillRegistry
// ---------------------------------------------------------------------------

describe('SkillRegistry', () => {
  it('skips non-directory entries during discovery', () => {
    fs.writeFileSync(path.join(tmpRoot, 'not_a_dir.md'), 'ignored', 'utf-8');
    const registry = new SkillRegistry([tmpRoot]);
    registry.discoverSkills();
    expect(Object.keys(registry.skills)).toHaveLength(0);
  });

  it('discovers valid skills', () => {
    makeSkillDir(tmpRoot, 'skill-a', 'Skill A description.');
    makeSkillDir(tmpRoot, 'skill-b', 'Skill B description.');
    const registry = new SkillRegistry([tmpRoot]);
    registry.discoverSkills();

    expect(registry.skills).toHaveProperty('skill-a');
    expect(registry.skills).toHaveProperty('skill-b');
  });

  it('finds relevant skills by name match', () => {
    makeSkillDir(tmpRoot, 'pdf-processing', 'Work with PDF documents.');
    makeSkillDir(tmpRoot, 'csv-tools', 'Handle CSV spreadsheets.');
    const registry = new SkillRegistry([tmpRoot]);
    registry.discoverSkills();

    const results = registry.findRelevantSkills('pdf');
    expect(results.length).toBeGreaterThanOrEqual(1);
    expect(results[0].name).toBe('pdf-processing');
  });

  it('caps results at maxResults', () => {
    for (let i = 0; i < 6; i++) {
      makeSkillDir(
        tmpRoot,
        `skill-${i}`,
        `A skill about document processing number ${i}.`,
      );
    }
    const registry = new SkillRegistry([tmpRoot]);
    registry.discoverSkills();

    const results = registry.findRelevantSkills('document', 3);
    expect(results.length).toBeLessThanOrEqual(3);
  });

  it('getSkill returns the skill or undefined', () => {
    makeSkillDir(tmpRoot, 'email-compose', 'Compose professional emails.');
    const registry = new SkillRegistry([tmpRoot]);
    registry.discoverSkills();

    const skill = registry.getSkill('email-compose');
    expect(skill).toBeDefined();
    expect(skill?.name).toBe('email-compose');

    expect(registry.getSkill('nonexistent')).toBeUndefined();
  });

  it('skips invalid skill directories with a warning', () => {
    // Valid skill.
    makeSkillDir(tmpRoot, 'good', 'Good skill.');
    // Invalid skill: has SKILL.md but missing required fields.
    const badDir = path.join(tmpRoot, 'bad');
    fs.mkdirSync(badDir);
    fs.writeFileSync(path.join(badDir, 'SKILL.md'), '---\nfoo: bar\n---\nbody', 'utf-8');

    const registry = new SkillRegistry([tmpRoot]);
    registry.discoverSkills();

    expect(registry.skills).toHaveProperty('good');
    expect(Object.keys(registry.skills)).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// SkillEnabledAgent
// ---------------------------------------------------------------------------

class EchoAgent implements Agent {
  get name(): string {
    return 'echo';
  }

  async process(message: Message): Promise<Message> {
    return {
      role: 'agent',
      content: message.content,
      metadata: { ...(message.metadata ?? {}) },
    };
  }
}

describe('SkillEnabledAgent', () => {
  it('augments the message with an available_skills block', async () => {
    makeSkillDir(tmpRoot, 'pdf-processing', 'Extract text from PDF documents.');
    const registry = new SkillRegistry([tmpRoot]);
    const agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, true);

    const msg: Message = { role: 'user', content: 'How do I parse pdf files?' };
    const response = await agent.process(msg);

    expect(String(response.content)).toContain('<available_skills>');
    expect(String(response.content)).toContain('pdf-processing');
  });

  it('passes through when no skills are relevant', async () => {
    makeSkillDir(tmpRoot, 'email-compose', 'Compose professional emails.');
    const registry = new SkillRegistry([tmpRoot]);
    const agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, true);

    const msg: Message = { role: 'user', content: 'tell me a joke' };
    const response = await agent.process(msg);

    expect(String(response.content)).not.toContain('<available_skills>');
    expect(String(response.content)).toBe('tell me a joke');
  });

  it('records active_skills in metadata', async () => {
    makeSkillDir(tmpRoot, 'csv-tools', 'Handle and transform CSV spreadsheets.');
    const registry = new SkillRegistry([tmpRoot]);
    const agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, true);

    const msg: Message = { role: 'user', content: 'parse this csv spreadsheet data' };
    const response = await agent.process(msg);

    expect(response.metadata).toHaveProperty('active_skills');
    expect(response.metadata?.active_skills as string[]).toContain('csv-tools');
  });

  it('exposes skill_injection capability', () => {
    const registry = new SkillRegistry([tmpRoot]);
    const agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, false);

    expect(agent.capabilities).toContain('skill_injection');
  });

  it('delegates name to the wrapped agent', () => {
    const registry = new SkillRegistry([tmpRoot]);
    const agent = new SkillEnabledAgent(new EchoAgent(), registry, 3, false);
    expect(agent.name).toBe('echo');
  });
});
