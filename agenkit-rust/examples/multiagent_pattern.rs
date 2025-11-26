//! Multi-Agent Collaboration Pattern Example
//!
//! Demonstrates the Multi-Agent pattern for coordinating multiple agents
//! working together on complex tasks.
//!
//! Run with: cargo run --example multiagent_pattern

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{
    ConsensusAgent, MultiAgentOrchestrator, OrchestrationStrategy, VotingStrategy,
};
use async_trait::async_trait;
use std::sync::Arc;

/// Mock research agent
struct ResearchAgent {
    specialty: String,
}

#[async_trait]
impl Agent for ResearchAgent {
    fn name(&self) -> &str {
        "Researcher"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["research".to_string(), "analysis".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Simulate research
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

        let research = format!(
            "[Research - {}] Key findings: AI agents show promise in {}. \
             Recent studies indicate significant advances in multi-agent collaboration.",
            self.specialty, content
        );

        Ok(Message::with_text("assistant", research))
    }
}

/// Mock writing agent
struct WritingAgent {
    style: String,
}

#[async_trait]
impl Agent for WritingAgent {
    fn name(&self) -> &str {
        "Writer"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["writing".to_string(), "editing".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Simulate writing
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

        let text = format!(
            "[Writer - {} style] This comprehensive report explores {}. \
             The analysis reveals important insights for the field.",
            self.style, content
        );

        Ok(Message::with_text("assistant", text))
    }
}

/// Mock editor agent
struct EditorAgent;

#[async_trait]
impl Agent for EditorAgent {
    fn name(&self) -> &str {
        "Editor"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["editing".to_string(), "proofreading".to_string()]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        // Simulate editing
        tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;

        let feedback = "[Editor] Reviewed document. Corrected grammar, \
                       improved clarity, and ensured consistent tone. \
                       Ready for publication.";

        Ok(Message::with_text("assistant", feedback))
    }
}

/// Mock critic agent
struct CriticAgent {
    perspective: String,
}

#[async_trait]
impl Agent for CriticAgent {
    fn name(&self) -> &str {
        "Critic"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["critique".to_string(), "analysis".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        let critique = format!(
            "[Critic - {} perspective] Regarding {}: \
             The approach has merit but should consider additional factors. \
             Recommend further validation.",
            self.perspective, content
        );

        Ok(Message::with_text("assistant", critique))
    }
}

/// Example 1: Basic orchestrator with sequential execution
async fn example_sequential_orchestration() -> Result<(), AgentError> {
    println!("\n=== Example 1: Sequential Orchestration ===\n");

    let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);

    orchestrator.register_agent(
        "researcher",
        Arc::new(ResearchAgent {
            specialty: "ML".to_string(),
        }),
    );

    orchestrator.register_agent(
        "writer",
        Arc::new(WritingAgent {
            style: "academic".to_string(),
        }),
    );

    orchestrator.register_agent("editor", Arc::new(EditorAgent));

    println!("Registered agents: {:?}", orchestrator.list_agents());
    println!("\nProcessing: Write a report on AI agents\n");

    let message = Message::with_text("user", "AI agent capabilities");
    let result = orchestrator.process(message).await?;

    println!("Combined result:\n{}\n", result.content_as_str().unwrap());

    // Check task history
    let tasks = orchestrator.get_tasks();
    println!("Tasks executed: {}", tasks.len());
    for task in tasks {
        println!("  - {}: {}", task.agent_name, task.status);
    }

    Ok(())
}

/// Example 2: Consensus with multiple perspectives
async fn example_consensus() -> Result<(), AgentError> {
    println!("\n=== Example 2: Consensus Building ===\n");

    let mut consensus = ConsensusAgent::new(VotingStrategy::Majority);

    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "conservative".to_string(),
    }));

    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "innovative".to_string(),
    }));

    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "pragmatic".to_string(),
    }));

    println!("Voting strategy: {:?}", consensus.voting_strategy());
    println!("Number of agents: {}\n", consensus.agents().len());

    let message = Message::with_text("user", "implementing multi-agent systems");
    let result = consensus.process(message).await?;

    println!("Consensus result:\n{}\n", result.content_as_str().unwrap());

    Ok(())
}

/// Example 3: Research team collaboration
async fn example_research_team() -> Result<(), AgentError> {
    println!("\n=== Example 3: Research Team Collaboration ===\n");

    let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);

    orchestrator.register_agent(
        "ml_researcher",
        Arc::new(ResearchAgent {
            specialty: "Machine Learning".to_string(),
        }),
    );

    orchestrator.register_agent(
        "nlp_researcher",
        Arc::new(ResearchAgent {
            specialty: "Natural Language Processing".to_string(),
        }),
    );

    orchestrator.register_agent(
        "systems_researcher",
        Arc::new(ResearchAgent {
            specialty: "Distributed Systems".to_string(),
        }),
    );

    let message = Message::with_text("user", "conversational AI architectures");
    let result = orchestrator.process(message).await?;

    println!("Research findings:\n{}\n", result.content_as_str().unwrap());

    Ok(())
}

/// Example 4: Content creation pipeline
async fn example_content_pipeline() -> Result<(), AgentError> {
    println!("\n=== Example 4: Content Creation Pipeline ===\n");

    let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);

    println!("Stage 1: Research");
    orchestrator.register_agent(
        "researcher",
        Arc::new(ResearchAgent {
            specialty: "Technical".to_string(),
        }),
    );

    println!("Stage 2: Writing");
    orchestrator.register_agent(
        "writer",
        Arc::new(WritingAgent {
            style: "technical".to_string(),
        }),
    );

    println!("Stage 3: Editing");
    orchestrator.register_agent("editor", Arc::new(EditorAgent));

    println!("\nProcessing content pipeline...\n");

    let message = Message::with_text("user", "agent design patterns");
    let result = orchestrator.process(message).await?;

    println!("Pipeline output:\n{}\n", result.content_as_str().unwrap());

    // Show pipeline stages
    let tasks = orchestrator.get_tasks();
    println!("Pipeline stages completed:");
    for (i, task) in tasks.iter().enumerate() {
        println!("  {}. {} - {}", i + 1, task.agent_name, task.status);
    }

    Ok(())
}

/// Example 5: Dynamic agent registration
async fn example_dynamic_registration() -> Result<(), AgentError> {
    println!("\n=== Example 5: Dynamic Agent Registration ===\n");

    let mut orchestrator = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);

    println!("Initial agents: {:?}", orchestrator.list_agents());

    // Add agents dynamically
    println!("\nAdding researcher...");
    orchestrator.register_agent(
        "researcher",
        Arc::new(ResearchAgent {
            specialty: "AI".to_string(),
        }),
    );
    println!("Agents: {:?}", orchestrator.list_agents());

    println!("\nAdding writer...");
    orchestrator.register_agent(
        "writer",
        Arc::new(WritingAgent {
            style: "concise".to_string(),
        }),
    );
    println!("Agents: {:?}", orchestrator.list_agents());

    // Process with current agents
    let message = Message::with_text("user", "test topic");
    let result = orchestrator.process(message).await?;
    println!("\nResult with 2 agents:\n{}\n", result.content_as_str().unwrap());

    // Remove an agent
    println!("Removing researcher...");
    orchestrator.unregister_agent("researcher");
    println!("Agents: {:?}", orchestrator.list_agents());

    Ok(())
}

/// Example 6: Consensus voting strategies
async fn example_voting_strategies() -> Result<(), AgentError> {
    println!("\n=== Example 6: Voting Strategies ===\n");

    // Majority voting
    println!("Testing MAJORITY voting:");
    let mut consensus = ConsensusAgent::new(VotingStrategy::Majority);
    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "optimistic".to_string(),
    }));
    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "realistic".to_string(),
    }));

    let message = Message::with_text("user", "new feature proposal");
    let result = consensus.process(message).await?;
    println!("{}\n", result.content_as_str().unwrap());

    // Unanimous voting
    println!("Testing UNANIMOUS voting:");
    let mut consensus = ConsensusAgent::new(VotingStrategy::Unanimous);
    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "security".to_string(),
    }));
    consensus.add_agent(Arc::new(CriticAgent {
        perspective: "performance".to_string(),
    }));

    let message = Message::with_text("user", "architecture decision");
    let result = consensus.process(message).await?;
    println!("{}\n", result.content_as_str().unwrap());

    Ok(())
}

/// Example 7: Orchestration strategies comparison
async fn example_orchestration_strategies() -> Result<(), AgentError> {
    println!("\n=== Example 7: Orchestration Strategies ===\n");

    // Sequential strategy
    println!("Sequential Strategy:");
    let mut orch1 = MultiAgentOrchestrator::new(OrchestrationStrategy::Sequential);
    orch1.register_agent(
        "agent1",
        Arc::new(ResearchAgent {
            specialty: "A".to_string(),
        }),
    );
    orch1.register_agent(
        "agent2",
        Arc::new(ResearchAgent {
            specialty: "B".to_string(),
        }),
    );
    println!("  Strategy: {:?}", orch1.strategy());
    println!("  Agents execute one after another\n");

    // Parallel strategy (placeholder - currently same as sequential)
    println!("Parallel Strategy:");
    let orch2 = MultiAgentOrchestrator::new(OrchestrationStrategy::Parallel);
    println!("  Strategy: {:?}", orch2.strategy());
    println!("  Agents execute simultaneously\n");

    // Delegate strategy (placeholder)
    println!("Delegate Strategy:");
    let orch3 = MultiAgentOrchestrator::new(OrchestrationStrategy::Delegate);
    println!("  Strategy: {:?}", orch3.strategy());
    println!("  Main agent delegates to specialists\n");

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    println!("Multi-Agent Collaboration Pattern Examples");
    println!("=========================================");

    // Run all examples
    example_sequential_orchestration().await?;
    example_consensus().await?;
    example_research_team().await?;
    example_content_pipeline().await?;
    example_dynamic_registration().await?;
    example_voting_strategies().await?;
    example_orchestration_strategies().await?;

    println!("✓ All examples completed successfully!");

    Ok(())
}
