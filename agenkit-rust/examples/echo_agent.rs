///! Echo agent example.
///!
///! This example demonstrates a simple echo agent that returns
///! the input message back to the sender.
use agenkit::core::{Agent, AgentError, Message};
use async_trait::async_trait;

/// Simple echo agent that returns input unchanged.
struct EchoAgent {
    name: String,
}

impl EchoAgent {
    fn new(name: impl Into<String>) -> Self {
        Self { name: name.into() }
    }
}

#[async_trait]
impl Agent for EchoAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // Simply return the message content as assistant response
        Ok(Message::new("assistant", message.content.clone()))
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["echo".to_string()]
    }
}

#[tokio::main]
async fn main() {
    // Create an echo agent
    let agent = EchoAgent::new("echo");

    // Create a test message
    let msg = Message::with_text("user", "Hello, agent!");

    println!("Sending message: {}", msg.content_as_str().unwrap());

    // Process the message
    match agent.process(msg).await {
        Ok(response) => {
            println!("Agent response: {}", response.content_as_str().unwrap());
        }
        Err(e) => {
            eprintln!("Error: {}", e);
        }
    }
}
