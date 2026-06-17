/**
 * Agent Skill loader and registry.
 *
 * Implements the Agent Skills specification: each skill is a directory containing
 * a SKILL.md file with YAML frontmatter (name, description, optional license and
 * metadata) followed by Markdown instructions.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';

/**
 * Represents a single agent skill loaded from a directory.
 *
 * A skill directory must contain a SKILL.md file structured as:
 *   ---
 *   name: skill-name
 *   description: What this skill does.
 *   license: Apache-2.0  # optional
 *   metadata:            # optional
 *     key: value
 *   ---
 *   # Skill Title
 *   Markdown instructions here.
 */
export class AgentSkill {
  /** Skill identifier. */
  readonly name: string;

  /** Human-readable description of what the skill does. */
  readonly description: string;

  /** Markdown instructions (body of SKILL.md). */
  readonly instructions: string;

  /** Optional license identifier. */
  readonly license?: string;

  /** Optional structured metadata. */
  readonly metadata: Record<string, unknown>;

  /** Optional path to the directory the skill was loaded from. */
  readonly skillDir?: string;

  constructor(params: {
    name: string;
    description: string;
    instructions: string;
    license?: string;
    metadata?: Record<string, unknown>;
    skillDir?: string;
  }) {
    this.name = params.name;
    this.description = params.description;
    this.instructions = params.instructions;
    this.license = params.license;
    this.metadata = params.metadata ?? {};
    this.skillDir = params.skillDir;
  }

  /**
   * Load a skill from a directory containing a SKILL.md file.
   *
   * @param skillDir Path to the skill directory.
   * @returns AgentSkill instance.
   * @throws Error if the directory lacks SKILL.md, has invalid frontmatter,
   *         or is missing required fields (name, description).
   */
  static fromDirectory(skillDir: string): AgentSkill {
    const skillFile = path.join(skillDir, 'SKILL.md');
    if (!fs.existsSync(skillFile)) {
      throw new Error(`No SKILL.md found in ${skillDir}`);
    }

    const raw = fs.readFileSync(skillFile, 'utf-8');

    // Split on "---" delimiters. File must start with "---".
    // Mirror Python's str.split("---", 2): at most 3 parts.
    const parts = splitMax(raw, '---', 3);
    if (parts.length < 3) {
      throw new Error(`Invalid SKILL.md in ${skillDir}: missing frontmatter delimiters`);
    }

    const frontmatterText = parts[1].trim();
    const instructions = parts[2].trim();

    let fm: unknown;
    try {
      fm = yaml.load(frontmatterText);
    } catch (exc) {
      throw new Error(`Invalid YAML frontmatter in ${skillDir}/SKILL.md: ${String(exc)}`);
    }

    if (typeof fm !== 'object' || fm === null || Array.isArray(fm)) {
      throw new Error(`Invalid frontmatter in ${skillDir}/SKILL.md: expected YAML mapping`);
    }

    const fmMap = fm as Record<string, unknown>;

    const name = fmMap.name;
    if (!name) {
      throw new Error(`Missing required field 'name' in ${skillDir}/SKILL.md`);
    }

    const description = fmMap.description;
    if (!description) {
      throw new Error(`Missing required field 'description' in ${skillDir}/SKILL.md`);
    }

    const license = fmMap.license;
    const metadata = fmMap.metadata;

    return new AgentSkill({
      name: String(name),
      description: String(description),
      instructions,
      license: license != null ? String(license) : undefined,
      metadata:
        typeof metadata === 'object' && metadata !== null && !Array.isArray(metadata)
          ? (metadata as Record<string, unknown>)
          : {},
      skillDir,
    });
  }

  /**
   * Render the skill as a prompt block for injection into agent messages.
   *
   * @returns Formatted string with skill name, description, and instructions.
   */
  toPrompt(): string {
    return (
      `# Skill: ${this.name}\n\n` +
      `## Description\n${this.description}\n\n` +
      `## Instructions\n${this.instructions}\n`
    );
  }
}

/**
 * Split a string on a separator into at most `limit` parts, mirroring
 * Python's ``str.split(sep, maxsplit)`` where ``maxsplit = limit - 1``.
 * The final part retains any further occurrences of the separator.
 */
function splitMax(value: string, sep: string, limit: number): string[] {
  const result: string[] = [];
  let rest = value;
  while (result.length < limit - 1) {
    const idx = rest.indexOf(sep);
    if (idx === -1) {
      break;
    }
    result.push(rest.slice(0, idx));
    rest = rest.slice(idx + sep.length);
  }
  result.push(rest);
  return result;
}

/**
 * Discovers and searches agent skills across filesystem paths.
 *
 * Skills are discovered by walking search paths and loading any subdirectory
 * that contains a SKILL.md file. Invalid skill directories are skipped with
 * a warning.
 */
export class SkillRegistry {
  private readonly searchPaths: string[];
  private readonly _skills: Map<string, AgentSkill> = new Map();

  constructor(searchPaths: string[]) {
    this.searchPaths = searchPaths;
  }

  /**
   * Walk each search path and load all valid skill directories.
   *
   * Skill directories without a SKILL.md or with invalid format are
   * skipped and logged as warnings.
   */
  discoverSkills(): void {
    for (const searchPath of this.searchPaths) {
      let stat: fs.Stats;
      try {
        stat = fs.statSync(searchPath);
      } catch {
        continue;
      }
      if (!stat.isDirectory()) {
        continue;
      }

      let entries: string[];
      try {
        entries = fs.readdirSync(searchPath);
      } catch {
        continue;
      }

      for (const entry of entries) {
        const entryPath = path.join(searchPath, entry);
        let entryStat: fs.Stats;
        try {
          entryStat = fs.statSync(entryPath);
        } catch {
          continue;
        }
        if (!entryStat.isDirectory()) {
          continue;
        }
        if (!fs.existsSync(path.join(entryPath, 'SKILL.md'))) {
          continue;
        }
        try {
          const skill = AgentSkill.fromDirectory(entryPath);
          this._skills.set(skill.name, skill);
        } catch (exc) {
          // eslint-disable-next-line no-console
          console.warn(`skipping skill directory ${entryPath}: ${String(exc)}`);
        }
      }
    }
  }

  /**
   * Return skills most relevant to the given query string.
   *
   * Scoring:
   *   +10 if query (lowercased) appears in skill name (lowercased)
   *   +5  if query (lowercased) appears in skill description (lowercased)
   *   +N  for each word in query that also appears in description
   *
   * Only skills with score > 0 are returned, sorted descending.
   *
   * @param query Natural-language query to match against skills.
   * @param maxResults Maximum number of skills to return.
   * @returns Ordered list of matching AgentSkill instances (best match first).
   */
  findRelevantSkills(query: string, maxResults = 5): AgentSkill[] {
    const queryLower = query.toLowerCase();
    const queryWords = new Set(queryLower.split(/\s+/).filter((w) => w.length > 0));

    const scored: Array<{ score: number; skill: AgentSkill }> = [];
    for (const skill of this._skills.values()) {
      let score = 0;
      const nameLower = skill.name.toLowerCase();
      const descLower = skill.description.toLowerCase();

      if (nameLower.includes(queryLower)) {
        score += 10;
      }
      if (descLower.includes(queryLower)) {
        score += 5;
      }

      const descWords = new Set(descLower.split(/\s+/).filter((w) => w.length > 0));
      let wordOverlap = 0;
      for (const word of queryWords) {
        if (descWords.has(word)) {
          wordOverlap += 1;
        }
      }
      score += wordOverlap;

      if (score > 0) {
        scored.push({ score, skill });
      }
    }

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, maxResults).map((s) => s.skill);
  }

  /** Return the skill with the given name, or undefined if not found. */
  getSkill(name: string): AgentSkill | undefined {
    return this._skills.get(name);
  }

  /** Read-only copy of loaded skills keyed by name. */
  get skills(): Record<string, AgentSkill> {
    const copy: Record<string, AgentSkill> = {};
    for (const [name, skill] of this._skills.entries()) {
      copy[name] = skill;
    }
    return copy;
  }
}
