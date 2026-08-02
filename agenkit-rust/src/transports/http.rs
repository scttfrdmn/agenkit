//! HTTP transport for remote agent communication.
//!
//! This module provides HTTP client and server implementations for
//! communicating with remote agents over HTTP.
use crate::core::{Agent, AgentError, Message};
use async_trait::async_trait;
use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response},
    routing::post,
    Json, Router,
};
use reqwest::Client;
use std::sync::Arc;
use std::time::Duration;
use tokio::net::TcpListener;
use tower_http::trace::TraceLayer;
use tracing::{debug, error, info};

/// HTTP transport configuration.
#[derive(Debug, Clone)]
pub struct HttpTransportConfig {
    /// Request timeout in seconds
    pub timeout_secs: u64,
    /// Base URL for the remote agent
    pub base_url: String,
    /// Optional API key for authentication
    pub api_key: Option<String>,
}

impl Default for HttpTransportConfig {
    fn default() -> Self {
        Self {
            timeout_secs: 30,
            base_url: "http://localhost:8080".to_string(),
            api_key: None,
        }
    }
}

/// HTTP client for communicating with remote agents.
///
/// # Example
/// ```no_run
/// use agenkit::transports::{HttpAgent, HttpTransportConfig};
/// use agenkit::core::{Agent, Message};
///
/// #[tokio::main]
/// async fn main() {
///     let config = HttpTransportConfig {
///         base_url: "http://localhost:8080".to_string(),
///         timeout_secs: 30,
///         api_key: None,
///     };
///
///     let agent = HttpAgent::new("remote-agent", config);
///     let msg = Message::with_text("user", "Hello!");
///     let response = agent.process(msg).await.unwrap();
/// }
/// ```
pub struct HttpAgent {
    name: String,
    config: HttpTransportConfig,
    client: Client,
}

impl HttpAgent {
    /// Create a new HTTP agent client.
    ///
    /// # Arguments
    /// * `name` - Agent name
    /// * `config` - HTTP transport configuration
    pub fn new(name: impl Into<String>, config: HttpTransportConfig) -> Self {
        let client = Client::builder()
            .timeout(Duration::from_secs(config.timeout_secs))
            .build()
            .expect("failed to build HTTP client");

        Self {
            name: name.into(),
            config,
            client,
        }
    }
}

#[async_trait]
impl Agent for HttpAgent {
    fn name(&self) -> &str {
        &self.name
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        debug!("Sending message to {}/process", self.config.base_url);

        let url = format!("{}/process", self.config.base_url);
        let mut request = self.client.post(&url).json(&message);

        if let Some(api_key) = &self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", api_key));
        }

        let response = request.send().await?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "unknown error".to_string());
            error!("HTTP error {}: {}", status, error_text);
            return Err(AgentError::Transport(format!(
                "HTTP error {}: {}",
                status, error_text
            )));
        }

        let message: Message = response.json().await?;
        Ok(message)
    }
}

/// HTTP server for exposing an agent over HTTP.
///
/// # Example
/// ```no_run
/// use agenkit::transports::HttpServer;
/// use agenkit::core::{Agent, Message, AgentError};
/// use async_trait::async_trait;
///
/// struct EchoAgent;
///
/// #[async_trait]
/// impl Agent for EchoAgent {
///     fn name(&self) -> &str { "echo" }
///     async fn process(&self, message: Message) -> Result<Message, AgentError> {
///         Ok(Message::with_text("assistant", message.content_as_str().unwrap_or("")))
///     }
/// }
///
/// #[tokio::main]
/// async fn main() {
///     let agent = EchoAgent;
///     let server = HttpServer::new(agent, "127.0.0.1:8080");
///     server.serve().await.unwrap();
/// }
/// ```
pub struct HttpServer<A: Agent> {
    agent: Arc<A>,
    addr: String,
}

impl<A: Agent + 'static> HttpServer<A> {
    /// Create a new HTTP server for an agent.
    ///
    /// # Arguments
    /// * `agent` - Agent to expose over HTTP
    /// * `addr` - Address to bind to (e.g., "127.0.0.1:8080")
    pub fn new(agent: A, addr: impl Into<String>) -> Self {
        Self {
            agent: Arc::new(agent),
            addr: addr.into(),
        }
    }

    /// Start serving requests.
    ///
    /// This will block until the server is shut down.
    pub async fn serve(self) -> Result<(), std::io::Error> {
        let app = Router::new()
            .route("/process", post(process_handler::<A>))
            .route("/health", axum::routing::get(health_handler))
            .layer(TraceLayer::new_for_http())
            .with_state(self.agent);

        info!("Starting HTTP server on {}", self.addr);
        let listener = TcpListener::bind(&self.addr).await?;
        axum::serve(listener, app).await
    }
}

/// Handler for /process endpoint.
async fn process_handler<A: Agent>(
    State(agent): State<Arc<A>>,
    Json(message): Json<Message>,
) -> Result<Json<Message>, AppError> {
    debug!("Received process request for agent '{}'", agent.name());

    let response = agent.process(message).await?;
    Ok(Json(response))
}

/// Handler for /health endpoint.
async fn health_handler() -> impl IntoResponse {
    Json(serde_json::json!({"status": "ok"}))
}

/// Error wrapper for HTTP responses.
struct AppError(AgentError);

impl From<AgentError> for AppError {
    fn from(err: AgentError) -> Self {
        AppError(err)
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let status = match self.0 {
            AgentError::Timeout(_) => StatusCode::REQUEST_TIMEOUT,
            AgentError::NotFound(_) => StatusCode::NOT_FOUND,
            AgentError::ProcessingError(_) => StatusCode::BAD_REQUEST,
            _ => StatusCode::INTERNAL_SERVER_ERROR,
        };

        let body = Json(serde_json::json!({
            "error": self.0.to_string()
        }));

        (status, body).into_response()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct TestAgent {
        name: String,
    }

    #[async_trait]
    impl Agent for TestAgent {
        fn name(&self) -> &str {
            &self.name
        }

        async fn process(&self, message: Message) -> Result<Message, AgentError> {
            // Echo back with "processed: " prefix
            let content = message.content_as_str().unwrap_or("");
            Ok(Message::with_text(
                "assistant",
                format!("processed: {}", content),
            ))
        }
    }

    #[tokio::test]
    async fn test_http_server_creation() {
        let agent = TestAgent {
            name: "test".to_string(),
        };
        let server = HttpServer::new(agent, "127.0.0.1:0");
        assert_eq!(server.agent.name(), "test");
    }

    #[tokio::test]
    async fn test_http_agent_creation() {
        let config = HttpTransportConfig::default();
        let agent = HttpAgent::new("test", config);
        assert_eq!(agent.name(), "test");
    }

    #[test]
    fn test_http_transport_config_default() {
        let config = HttpTransportConfig::default();
        assert_eq!(config.timeout_secs, 30);
        assert_eq!(config.base_url, "http://localhost:8080");
        assert!(config.api_key.is_none());
    }
}
