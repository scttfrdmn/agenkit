/// Agent Skills module.
///
/// Provides support for the Agent Skills specification — an open standard for
/// packaging reusable agent capabilities as discoverable, portable instruction
/// bundles.  Each skill is a directory containing a `SKILL.md` file with YAML
/// frontmatter (name, description, optional license and metadata) followed by
/// Markdown instructions.
///
/// # Types
/// - [`loader::AgentSkill`] — load and parse a SKILL.md directory
/// - [`loader::SkillRegistry`] — discover and search skills across paths
/// - [`agent::SkillEnabledAgent`] — agent wrapper that injects skill instructions
pub mod agent;
pub mod loader;

pub use agent::SkillEnabledAgent;
pub use loader::{AgentSkill, SkillError, SkillRegistry};
