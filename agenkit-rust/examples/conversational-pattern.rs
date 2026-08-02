//! Conversational Pattern Example
//!
//! Demonstrates the Conversational pattern for maintaining context across
//! multiple turns of conversation with automatic history management.
//!
//! Run with: cargo run --example conversational_pattern

use agenkit::core::{Agent, AgentError, Message};
use agenkit::patterns::{ConversationalAgent, ConversationalConfig};
use async_trait::async_trait;
use std::sync::Arc;

/// Mock LLM agent that responds contextually based on conversation history
struct MockLLMAgent {
    scenario: String,
}

#[async_trait]
impl Agent for MockLLMAgent {
    fn name(&self) -> &str {
        "MockLLM"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["chat".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        let content = message.content_as_str().unwrap_or("");

        // Parse conversation history from context
        let response = if content.contains("My name is Alice")
            && content.contains("What's my name?")
        {
            "Your name is Alice, as you mentioned earlier!"
        } else if content.contains("My name is Alice") {
            "Nice to meet you, Alice! How can I help you today?"
        } else if content.contains("What's my name?") {
            "I don't recall you mentioning your name. Could you tell me?"
        } else if content.contains("I like pizza") && content.contains("What's my favorite food?") {
            "Based on our conversation, your favorite food is pizza!"
        } else if content.contains("I like pizza") {
            "Pizza is delicious! Do you have a favorite type?"
        } else if content.contains("favorite color") && content.contains("blue") {
            "Blue is a great color! Is there anything else you'd like to talk about?"
        } else if content.contains("What did we talk about") {
            if content.contains("color") && content.contains("pizza") {
                "We talked about your favorite food (pizza) and your favorite color (blue)."
            } else if content.contains("pizza") {
                "We talked about your favorite food, which is pizza."
            } else {
                "We haven't talked about much yet. What would you like to discuss?"
            }
        } else if content.contains("capital of France") {
            "The capital of France is Paris."
        } else if content.contains("Who was the first president") {
            "The first President of the United States was George Washington."
        } else if content.contains("previous question") || content.contains("asked before") {
            if content.contains("France") {
                "You asked about the capital of France, which is Paris."
            } else if content.contains("president") {
                "You asked about the first President of the United States, which was George Washington."
            } else {
                "I remember your previous questions from our conversation."
            }
        } else if self.scenario == "customer_support" {
            if content.contains("order") && content.contains("123") {
                "I found your order #123. It's currently being processed and should ship tomorrow."
            } else if content.contains("shipping") {
                "Based on your order #123, shipping will take 3-5 business days."
            } else {
                "I'm here to help! What can I assist you with today?"
            }
        } else {
            "I understand. What else would you like to know?"
        };

        Ok(Message::with_text("assistant", response))
    }
}

/// Example 1: Basic conversation with name memory
async fn example_basic_conversation() -> Result<(), AgentError> {
    println!("\n=== Example 1: Basic Conversation with Memory ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "general".to_string(),
    });

    let agent = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 10,
        system_prompt: Some("You are a friendly assistant that remembers context.".to_string()),
        include_system: true,
    })?;

    println!("User: My name is Alice");
    let response1 = agent
        .process(Message::with_text("user", "My name is Alice"))
        .await?;
    println!("Assistant: {}\n", response1.content_as_str().unwrap());

    println!("User: What's my name?");
    let response2 = agent
        .process(Message::with_text("user", "What's my name?"))
        .await?;
    println!("Assistant: {}\n", response2.content_as_str().unwrap());

    println!("History length: {} messages", agent.history_length());

    Ok(())
}

/// Example 2: Multi-topic conversation tracking
async fn example_multi_topic() -> Result<(), AgentError> {
    println!("\n=== Example 2: Multi-Topic Conversation ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "general".to_string(),
    });

    let agent = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 20,
        system_prompt: Some("You are a helpful assistant.".to_string()),
        include_system: true,
    })?;

    let turns = [
        ("User", "I like pizza"),
        ("Assistant", ""),
        ("User", "My favorite color is blue"),
        ("Assistant", ""),
        ("User", "What's my favorite food?"),
        ("Assistant", ""),
        ("User", "What did we talk about so far?"),
        ("Assistant", ""),
    ];

    for (i, (role, input)) in turns.iter().enumerate() {
        if *role == "User" {
            println!("{}: {}", role, input);
            let response = agent.process(Message::with_text("user", *input)).await?;
            println!("Assistant: {}\n", response.content_as_str().unwrap());
        }

        if i == turns.len() - 2 {
            println!("Current history length: {}\n", agent.history_length());
        }
    }

    Ok(())
}

/// Example 3: History pruning demonstration
async fn example_history_pruning() -> Result<(), AgentError> {
    println!("\n=== Example 3: History Pruning ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "general".to_string(),
    });

    let agent = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 5, // Small history to demonstrate pruning
        system_prompt: Some("System prompt".to_string()),
        include_system: true,
    })?;

    println!("Max history: 5 messages");
    println!(
        "Initial history (with system): {}\n",
        agent.history_length()
    );

    // Add several messages
    for i in 1..=4 {
        println!("Turn {}: Sending message...", i);
        agent
            .process(Message::with_text("user", format!("Message {}", i)))
            .await?;
        println!("History length: {}\n", agent.history_length());
    }

    println!("Final history:");
    let history = agent.get_history();
    for (i, msg) in history.iter().enumerate() {
        println!(
            "  [{}] {}: {}",
            i,
            msg.role,
            msg.content_as_str().unwrap_or("[no content]")
        );
    }

    Ok(())
}

/// Example 4: Export and import history
async fn example_export_import() -> Result<(), AgentError> {
    println!("\n=== Example 4: Export and Import History ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "general".to_string(),
    });

    // First agent
    let agent1 = ConversationalAgent::new(ConversationalConfig {
        llm: llm.clone(),
        max_history: 10,
        system_prompt: None,
        include_system: true,
    })?;

    println!("Agent 1: Starting conversation...");
    agent1
        .process(Message::with_text("user", "What's the capital of France?"))
        .await?;
    agent1
        .process(Message::with_text(
            "user",
            "Who was the first president of the US?",
        ))
        .await?;

    println!("Agent 1: History length: {}", agent1.history_length());

    // Export history
    let exported = agent1.export_history();
    println!("Exported {} messages\n", exported.len());

    // Second agent - import history
    let agent2 = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 10,
        system_prompt: None,
        include_system: true,
    })?;

    agent2.import_history(exported)?;
    println!("Agent 2: Imported history");
    println!("Agent 2: History length: {}", agent2.history_length());

    // Continue conversation on agent2
    println!("\nAgent 2: Continuing conversation...");
    println!("User: What was my previous question about France?");
    let response = agent2
        .process(Message::with_text(
            "user",
            "What was my previous question about France?",
        ))
        .await?;
    println!("Assistant: {}\n", response.content_as_str().unwrap());

    Ok(())
}

/// Example 5: Customer support conversation
async fn example_customer_support() -> Result<(), AgentError> {
    println!("\n=== Example 5: Customer Support Scenario ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "customer_support".to_string(),
    });

    let agent = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 15,
        system_prompt: Some(
            "You are a customer support agent. Be helpful and remember order details.".to_string(),
        ),
        include_system: true,
    })?;

    let conversation = [
        "I need help with my order",
        "The order number is 123",
        "When will it ship?",
        "Thank you!",
    ];

    for (i, user_input) in conversation.iter().enumerate() {
        println!("User: {}", user_input);
        let response = agent
            .process(Message::with_text("user", *user_input))
            .await?;
        println!("Support: {}\n", response.content_as_str().unwrap());

        if i == 1 {
            println!("[Agent remembered order number from context]\n");
        }
    }

    Ok(())
}

/// Example 6: Clear history demonstration
async fn example_clear_history() -> Result<(), AgentError> {
    println!("\n=== Example 6: Clear History ===\n");

    let llm = Arc::new(MockLLMAgent {
        scenario: "general".to_string(),
    });

    let agent = ConversationalAgent::new(ConversationalConfig {
        llm,
        max_history: 10,
        system_prompt: Some("You are a helpful assistant.".to_string()),
        include_system: true,
    })?;

    // Build up some history
    agent
        .process(Message::with_text("user", "My name is Bob"))
        .await?;
    agent
        .process(Message::with_text("user", "I like coffee"))
        .await?;

    println!("After conversation:");
    println!("History length: {}\n", agent.history_length());

    // Clear history but keep system prompt
    agent.clear_history(true);
    println!("After clear_history(keep_system=true):");
    println!(
        "History length: {} (system prompt preserved)\n",
        agent.history_length()
    );

    // Try asking about previous context
    println!("User: What's my name?");
    let response = agent
        .process(Message::with_text("user", "What's my name?"))
        .await?;
    println!("Assistant: {}\n", response.content_as_str().unwrap());
    println!("[Agent doesn't remember because history was cleared]");

    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), AgentError> {
    println!("Conversational Pattern Examples");
    println!("===============================");

    // Run all examples
    example_basic_conversation().await?;
    example_multi_topic().await?;
    example_history_pruning().await?;
    example_export_import().await?;
    example_customer_support().await?;
    example_clear_history().await?;

    println!("\n✓ All examples completed successfully!");

    Ok(())
}
