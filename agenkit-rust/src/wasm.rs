//! WASM-specific bindings and utilities.
//!
//! This module provides browser-compatible functionality for running
//! Agenkit agents in WebAssembly environments.
//!
//! # Example
//!
//! ```javascript
//! import init, { WasmAgent } from './pkg/agenkit.js';
//!
//! async function main() {
//!     await init();
//!
//!     const agent = new WasmAgent("my-agent");
//!     const response = await agent.process({
//!         role: "user",
//!         content: "Hello from browser!"
//!     });
//!
//!     console.log(response);
//! }
//! ```

use crate::core::{Agent, Message};
use wasm_bindgen::prelude::*;
use serde::{Serialize, Deserialize};
use std::sync::Arc;

/// Initialize WASM module with panic hook and logging.
#[wasm_bindgen(start)]
pub fn init_wasm() {
    // Set panic hook for better error messages
    #[cfg(feature = "console_error_panic_hook")]
    console_error_panic_hook::set_once();

    // Initialize logging
    #[cfg(feature = "wasm-logger")]
    wasm_logger::init(wasm_logger::Config::default());
}

/// JavaScript-compatible message type.
#[wasm_bindgen]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsMessage {
    role: String,
    content: String,
}

#[wasm_bindgen]
impl JsMessage {
    #[wasm_bindgen(constructor)]
    pub fn new(role: String, content: String) -> Self {
        Self { role, content }
    }

    #[wasm_bindgen(getter)]
    pub fn role(&self) -> String {
        self.role.clone()
    }

    #[wasm_bindgen(getter)]
    pub fn content(&self) -> String {
        self.content.clone()
    }
}

impl From<JsMessage> for Message {
    fn from(js_msg: JsMessage) -> Self {
        Message::with_text(&js_msg.role, js_msg.content)
    }
}

impl From<Message> for JsMessage {
    fn from(msg: Message) -> Self {
        let content = msg.content_as_str().unwrap_or("").to_string();
        Self {
            role: msg.role,
            content,
        }
    }
}

/// Simple echo agent for WASM demonstration.
#[wasm_bindgen]
pub struct WasmEchoAgent {
    name: String,
}

#[wasm_bindgen]
impl WasmEchoAgent {
    #[wasm_bindgen(constructor)]
    pub fn new(name: String) -> Self {
        Self { name }
    }

    /// Process a message and return a response.
    pub async fn process(&self, message: JsMessage) -> Result<JsMessage, JsValue> {
        let msg: Message = message.into();
        let response = Message::with_text(
            "assistant",
            format!("Echo from {}: {}", self.name, msg.content_as_str().unwrap_or("")),
        );
        Ok(response.into())
    }

    #[wasm_bindgen(getter)]
    pub fn name(&self) -> String {
        self.name.clone()
    }
}

/// Agent wrapper for WASM compatibility.
///
/// Wraps any Rust agent to expose it to JavaScript.
#[wasm_bindgen]
pub struct WasmAgent {
    inner: Arc<dyn Agent>,
}

#[wasm_bindgen]
impl WasmAgent {
    /// Process a message through the wrapped agent.
    pub async fn process(&self, message: JsMessage) -> Result<JsMessage, JsValue> {
        let msg: Message = message.into();
        let response = self.inner
            .process(msg)
            .await
            .map_err(|e| JsValue::from_str(&format!("Agent error: {}", e)))?;
        Ok(response.into())
    }

    #[wasm_bindgen(getter)]
    pub fn name(&self) -> String {
        self.inner.name().to_string()
    }
}

/// Utility function to log to browser console.
#[wasm_bindgen]
pub fn log(message: &str) {
    web_sys::console::log_1(&JsValue::from_str(message));
}

/// Get current timestamp in milliseconds.
#[wasm_bindgen]
pub fn now() -> f64 {
    js_sys::Date::now()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_js_message_creation() {
        let msg = JsMessage::new("user".to_string(), "test".to_string());
        assert_eq!(msg.role(), "user");
        assert_eq!(msg.content(), "test");
    }

    #[test]
    fn test_js_message_to_message() {
        let js_msg = JsMessage::new("user".to_string(), "hello".to_string());
        let msg: Message = js_msg.into();
        assert_eq!(msg.role, "user");
        assert_eq!(msg.content_as_str().unwrap(), "hello");
    }

    #[test]
    fn test_message_to_js_message() {
        let msg = Message::with_text("assistant", "response");
        let js_msg: JsMessage = msg.into();
        assert_eq!(js_msg.role(), "assistant");
        assert_eq!(js_msg.content(), "response");
    }

    #[test]
    fn test_wasm_echo_agent_creation() {
        let agent = WasmEchoAgent::new("test-agent".to_string());
        assert_eq!(agent.name(), "test-agent");
    }
}
