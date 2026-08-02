/// SkillEnabledAgent — wraps an Agent and injects relevant skill instructions.
use std::sync::Arc;

use async_trait::async_trait;
use serde_json::json;

use crate::core::{Agent, AgentError, IntrospectionResult, Message};
use crate::skills::loader::SkillRegistry;

/// Agent wrapper that automatically injects relevant skill instructions.
///
/// Before delegating to the wrapped agent, this wrapper queries the registry
/// for skills relevant to the incoming message and prepends their instructions
/// inside an `<available_skills>` block.  The response's metadata will contain
/// `active_skills` listing the skill names that were injected.
pub struct SkillEnabledAgent<A: Agent> {
    inner: A,
    registry: Arc<SkillRegistry>,
    max_active_skills: usize,
}

impl<A: Agent> SkillEnabledAgent<A> {
    /// Create a new SkillEnabledAgent with default max_active_skills of 3.
    pub fn new(agent: A, registry: Arc<SkillRegistry>) -> Self {
        SkillEnabledAgent {
            inner: agent,
            registry,
            max_active_skills: 3,
        }
    }

    /// Create a new SkillEnabledAgent with a custom max_active_skills limit.
    pub fn with_max_active_skills(agent: A, registry: Arc<SkillRegistry>, max: usize) -> Self {
        SkillEnabledAgent {
            inner: agent,
            registry,
            max_active_skills: max,
        }
    }
}

#[async_trait]
impl<A: Agent> Agent for SkillEnabledAgent<A> {
    fn name(&self) -> &str {
        self.inner.name()
    }

    fn capabilities(&self) -> Vec<String> {
        let mut caps = self.inner.capabilities();
        if !caps.iter().any(|c| c == "skill_injection") {
            caps.push("skill_injection".to_string());
        }
        caps
    }

    fn introspect(&self) -> IntrospectionResult {
        self.inner.introspect()
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let query = message.content.as_str().unwrap_or("").to_string();

        let relevant = self
            .registry
            .find_relevant_skills(&query, self.max_active_skills);

        if relevant.is_empty() {
            return self.inner.process(message).await;
        }

        // Build <available_skills> block.
        let mut prefix = String::from("<available_skills>\n");
        let mut active_names: Vec<String> = Vec::new();
        for skill in &relevant {
            prefix.push_str(&skill.to_prompt());
            prefix.push('\n');
            active_names.push(skill.name.clone());
        }
        prefix.push_str("</available_skills>\n\n");
        prefix.push_str(&query);

        // Build enhanced message.
        let mut new_metadata = message.metadata.clone();
        new_metadata.insert("active_skills".to_string(), json!(active_names));

        let enhanced = Message {
            role: message.role.clone(),
            content: serde_json::Value::String(prefix),
            metadata: new_metadata,
            timestamp: message.timestamp,
        };

        self.inner.process(enhanced).await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::skills::loader::SkillRegistry;
    use async_trait::async_trait;
    use std::fs;
    use std::path::PathBuf;
    use std::sync::Arc;
    use tempfile::TempDir;

    fn make_skill_dir(parent: &std::path::Path, name: &str, description: &str) -> PathBuf {
        let skill_dir = parent.join(name);
        fs::create_dir_all(&skill_dir).unwrap();
        let content = format!("---\nname: {name}\ndescription: {description}\n---\nInstructions.");
        fs::write(skill_dir.join("SKILL.md"), content).unwrap();
        skill_dir
    }

    struct EchoAgent;

    #[async_trait]
    impl Agent for EchoAgent {
        fn name(&self) -> &str {
            "echo"
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            let mut out = Message::with_text("agent", message.content.as_str().unwrap_or(""));
            out.metadata = message.metadata.clone();
            Ok(out)
        }
    }

    #[tokio::test]
    async fn test_skill_agent_augments_message() {
        let tmp = TempDir::new().unwrap();
        make_skill_dir(
            tmp.path(),
            "pdf-processing",
            "Extract text from PDF documents.",
        );

        let mut registry = SkillRegistry::new(vec![tmp.path().to_path_buf()]);
        registry.discover_skills();
        let registry = Arc::new(registry);

        let agent = SkillEnabledAgent::new(EchoAgent, registry);
        let msg = Message::with_text("user", "How do I parse pdf files?");
        let resp = agent.process(msg).await.unwrap();

        let content = resp.content.as_str().unwrap_or("");
        assert!(content.contains("<available_skills>"));
        assert!(content.contains("pdf-processing"));
    }

    #[tokio::test]
    async fn test_skill_agent_passthrough() {
        let tmp = TempDir::new().unwrap();
        make_skill_dir(tmp.path(), "email-compose", "Compose professional emails.");

        let mut registry = SkillRegistry::new(vec![tmp.path().to_path_buf()]);
        registry.discover_skills();
        let registry = Arc::new(registry);

        let agent = SkillEnabledAgent::new(EchoAgent, registry);
        let msg = Message::with_text("user", "tell me a joke");
        let resp = agent.process(msg).await.unwrap();

        let content = resp.content.as_str().unwrap_or("");
        assert!(!content.contains("<available_skills>"));
        assert_eq!(content, "tell me a joke");
    }
}
