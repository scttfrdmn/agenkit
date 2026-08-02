/// Agent Skill loader and registry.
///
/// Implements the Agent Skills specification: each skill is a directory
/// containing a SKILL.md file with YAML frontmatter (name, description,
/// optional license and metadata) followed by Markdown instructions.
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fmt;
use std::path::{Path, PathBuf};

/// Error types for skill loading operations.
#[derive(Debug)]
pub enum SkillError {
    /// I/O error reading the skill directory or SKILL.md.
    Io(std::io::Error),
    /// The SKILL.md file has invalid structure (missing "---" delimiters, etc.).
    InvalidFormat(&'static str),
    /// A required YAML field is absent.
    MissingField(&'static str),
    /// YAML parsing failed.
    YamlParse(serde_yaml::Error),
}

impl fmt::Display for SkillError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SkillError::Io(e) => write!(f, "I/O error: {}", e),
            SkillError::InvalidFormat(msg) => write!(f, "invalid format: {}", msg),
            SkillError::MissingField(field) => write!(f, "missing required field: {}", field),
            SkillError::YamlParse(e) => write!(f, "YAML parse error: {}", e),
        }
    }
}

impl std::error::Error for SkillError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            SkillError::Io(e) => Some(e),
            SkillError::YamlParse(e) => Some(e),
            _ => None,
        }
    }
}

impl From<std::io::Error> for SkillError {
    fn from(e: std::io::Error) -> Self {
        SkillError::Io(e)
    }
}

impl From<serde_yaml::Error> for SkillError {
    fn from(e: serde_yaml::Error) -> Self {
        SkillError::YamlParse(e)
    }
}

/// YAML frontmatter fields parsed from SKILL.md.
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SkillFrontmatter {
    pub name: Option<String>,
    pub description: Option<String>,
    #[serde(default)]
    pub license: Option<String>,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

/// Represents a single agent skill loaded from a directory.
///
/// A skill directory must contain a SKILL.md file structured as:
/// ```text
/// ---
/// name: skill-name
/// description: What this skill does.
/// license: Apache-2.0  # optional
/// metadata:            # optional
///   key: value
/// ---
/// # Skill Title
/// Markdown instructions here.
/// ```
#[derive(Debug, Clone)]
pub struct AgentSkill {
    pub name: String,
    pub description: String,
    pub instructions: String,
    pub license: Option<String>,
    pub metadata: HashMap<String, serde_json::Value>,
    pub skill_dir: Option<PathBuf>,
}

impl AgentSkill {
    /// Load a skill from a directory containing a SKILL.md file.
    ///
    /// # Errors
    /// Returns [`SkillError`] if the directory lacks a SKILL.md, the file has
    /// invalid frontmatter, or required fields (name, description) are missing.
    pub fn from_directory(skill_dir: &Path) -> Result<Self, SkillError> {
        let skill_file = skill_dir.join("SKILL.md");
        let raw = std::fs::read_to_string(&skill_file)?;

        // File must begin with "---"; split into at most 3 parts on "---".
        let parts: Vec<&str> = raw.splitn(3, "---").collect();
        if parts.len() < 3 {
            return Err(SkillError::InvalidFormat("missing frontmatter delimiters"));
        }

        let frontmatter_text = parts[1].trim();
        let instructions = parts[2].trim().to_string();

        let fm: SkillFrontmatter = serde_yaml::from_str(frontmatter_text)?;

        let name = fm
            .name
            .filter(|s| !s.is_empty())
            .ok_or(SkillError::MissingField("name"))?;

        let description = fm
            .description
            .filter(|s| !s.is_empty())
            .ok_or(SkillError::MissingField("description"))?;

        Ok(AgentSkill {
            name,
            description,
            instructions,
            license: fm.license,
            metadata: fm.metadata,
            skill_dir: Some(skill_dir.to_path_buf()),
        })
    }

    /// Render the skill as a prompt block for injection into agent messages.
    pub fn to_prompt(&self) -> String {
        format!(
            "# Skill: {}\n\n## Description\n{}\n\n## Instructions\n{}\n",
            self.name, self.description, self.instructions
        )
    }
}

/// Discovers and searches agent skills across filesystem paths.
///
/// Skills are discovered by walking search paths and loading any subdirectory
/// that contains a SKILL.md file. Invalid skill directories are skipped.
pub struct SkillRegistry {
    search_paths: Vec<PathBuf>,
    skills: HashMap<String, AgentSkill>,
}

impl SkillRegistry {
    /// Create a new registry with the given search paths.
    pub fn new(search_paths: Vec<PathBuf>) -> Self {
        SkillRegistry {
            search_paths,
            skills: HashMap::new(),
        }
    }

    /// Walk each search path and load all valid skill directories.
    ///
    /// Invalid or unreadable skill directories are silently skipped.
    pub fn discover_skills(&mut self) {
        for search_path in &self.search_paths.clone() {
            let entries = match std::fs::read_dir(search_path) {
                Ok(e) => e,
                Err(_) => continue,
            };
            for entry in entries.flatten() {
                let path = entry.path();
                if !path.is_dir() {
                    continue;
                }
                if !path.join("SKILL.md").exists() {
                    continue;
                }
                match AgentSkill::from_directory(&path) {
                    Ok(skill) => {
                        self.skills.insert(skill.name.clone(), skill);
                    }
                    Err(_) => {
                        // Skip invalid skill directories.
                    }
                }
            }
        }
    }

    /// Return up to `max_results` skills most relevant to `query`.
    ///
    /// Scoring:
    /// - +10 if query (lowercased) is contained in the skill name
    /// - +5  if query (lowercased) is contained in the skill description
    /// - +N  for each word in query that also appears in the description
    ///
    /// Only skills with score > 0 are returned, ordered best-first.
    pub fn find_relevant_skills(&self, query: &str, max_results: usize) -> Vec<&AgentSkill> {
        let query_lower = query.to_lowercase();
        let query_words: std::collections::HashSet<&str> = query_lower.split_whitespace().collect();

        let mut scored: Vec<(i32, &AgentSkill)> = self
            .skills
            .values()
            .filter_map(|skill| {
                let mut score: i32 = 0;
                let name_lower = skill.name.to_lowercase();
                let desc_lower = skill.description.to_lowercase();

                if name_lower.contains(&query_lower) {
                    score += 10;
                }
                if desc_lower.contains(&query_lower) {
                    score += 5;
                }

                let desc_words: std::collections::HashSet<&str> =
                    desc_lower.split_whitespace().collect();
                let overlap = query_words.intersection(&desc_words).count() as i32;
                score += overlap;

                if score > 0 {
                    Some((score, skill))
                } else {
                    None
                }
            })
            .collect();

        scored.sort_by_key(|s| std::cmp::Reverse(s.0));

        let limit = if max_results == 0 {
            scored.len()
        } else {
            max_results.min(scored.len())
        };

        scored[..limit].iter().map(|(_, s)| *s).collect()
    }

    /// Return the skill with the given name, or `None` if not found.
    pub fn get_skill(&self, name: &str) -> Option<&AgentSkill> {
        self.skills.get(name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn make_skill_dir(parent: &Path, name: &str, description: &str, body: &str) -> PathBuf {
        let skill_dir = parent.join(name);
        fs::create_dir_all(&skill_dir).unwrap();
        let content = format!("---\nname: {name}\ndescription: {description}\n---\n{body}");
        fs::write(skill_dir.join("SKILL.md"), content).unwrap();
        skill_dir
    }

    #[test]
    fn test_load_skill_valid() {
        let tmp = TempDir::new().unwrap();
        let skill_dir = make_skill_dir(
            tmp.path(),
            "pdf-processing",
            "Extract text from PDFs.",
            "# PDF\nDo stuff.",
        );

        let skill = AgentSkill::from_directory(&skill_dir).unwrap();
        assert_eq!(skill.name, "pdf-processing");
        assert_eq!(skill.description, "Extract text from PDFs.");
        assert!(skill.instructions.contains("Do stuff."));
        assert_eq!(skill.skill_dir.as_deref(), Some(skill_dir.as_path()));
    }

    #[test]
    fn test_invalid_format_missing_delimiters() {
        let tmp = TempDir::new().unwrap();
        let skill_dir = tmp.path().join("bad");
        fs::create_dir_all(&skill_dir).unwrap();
        fs::write(skill_dir.join("SKILL.md"), "name: foo\ndescription: bar\n").unwrap();

        let err = AgentSkill::from_directory(&skill_dir).unwrap_err();
        assert!(matches!(err, SkillError::InvalidFormat(_)));
    }

    #[test]
    fn test_missing_field_name() {
        let tmp = TempDir::new().unwrap();
        let skill_dir = tmp.path().join("noname");
        fs::create_dir_all(&skill_dir).unwrap();
        fs::write(
            skill_dir.join("SKILL.md"),
            "---\ndescription: A skill.\n---\nInstructions.",
        )
        .unwrap();

        let err = AgentSkill::from_directory(&skill_dir).unwrap_err();
        assert!(matches!(err, SkillError::MissingField("name")));
    }

    #[test]
    fn test_missing_field_description() {
        let tmp = TempDir::new().unwrap();
        let skill_dir = tmp.path().join("nodesc");
        fs::create_dir_all(&skill_dir).unwrap();
        fs::write(
            skill_dir.join("SKILL.md"),
            "---\nname: nodesc\n---\nInstructions.",
        )
        .unwrap();

        let err = AgentSkill::from_directory(&skill_dir).unwrap_err();
        assert!(matches!(err, SkillError::MissingField("description")));
    }

    #[test]
    fn test_to_prompt_format() {
        let tmp = TempDir::new().unwrap();
        let skill_dir = make_skill_dir(
            tmp.path(),
            "csv-tools",
            "Handle CSV files.",
            "Parse and write CSV.",
        );
        let skill = AgentSkill::from_directory(&skill_dir).unwrap();
        let prompt = skill.to_prompt();

        assert!(prompt.contains("# Skill: csv-tools"));
        assert!(prompt.contains("## Description"));
        assert!(prompt.contains("Handle CSV files."));
        assert!(prompt.contains("## Instructions"));
        assert!(prompt.contains("Parse and write CSV."));
    }

    #[test]
    fn test_registry_discover() {
        let tmp = TempDir::new().unwrap();
        make_skill_dir(tmp.path(), "skill-a", "Skill A description.", "");
        make_skill_dir(tmp.path(), "skill-b", "Skill B description.", "");

        let mut registry = SkillRegistry::new(vec![tmp.path().to_path_buf()]);
        registry.discover_skills();

        assert!(registry.get_skill("skill-a").is_some());
        assert!(registry.get_skill("skill-b").is_some());
    }

    #[test]
    fn test_find_relevant_skills() {
        let tmp = TempDir::new().unwrap();
        make_skill_dir(tmp.path(), "pdf-processing", "Work with PDF documents.", "");
        make_skill_dir(tmp.path(), "csv-tools", "Handle CSV spreadsheets.", "");

        let mut registry = SkillRegistry::new(vec![tmp.path().to_path_buf()]);
        registry.discover_skills();

        let results = registry.find_relevant_skills("pdf", 5);
        assert!(!results.is_empty());
        assert_eq!(results[0].name, "pdf-processing");
    }

    #[test]
    fn test_find_no_match() {
        let tmp = TempDir::new().unwrap();
        make_skill_dir(
            tmp.path(),
            "email-compose",
            "Compose professional emails.",
            "",
        );

        let mut registry = SkillRegistry::new(vec![tmp.path().to_path_buf()]);
        registry.discover_skills();

        let results = registry.find_relevant_skills("xyzzy-not-a-skill", 5);
        assert!(results.is_empty());
    }
}
