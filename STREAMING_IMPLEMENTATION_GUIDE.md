# Streaming Implementation Guide

This guide provides templates for completing streaming support across all remaining adapters.

## Current Status

**Completed:** 24/35 providers (69%)
**Remaining:** 11 implementations (~1,250 LOC)

---

## Rust Implementations (2 adapters)

### 1. Rust Ollama Streaming (~100 LOC)

**File:** `agenkit-rust/src/adapters/ollama.rs`

**Add to imports:**
```rust
use futures::Stream;
use std::pin::Pin;
```

**Add before `impl Agent for OllamaAgent` (around line 217):**
```rust
    /// Stream completion from Ollama API.
    #[cfg(feature = "native")]
    pub async fn stream(
        &self,
        message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        let ollama_message = self.message_to_ollama_message(&message);

        match self.stream_api_impl(vec![ollama_message]).await {
            Ok(chunks) => Box::pin(futures::stream::iter(chunks.into_iter().map(Ok))),
            Err(e) => Box::pin(futures::stream::once(async move { Err(e) })),
        }
    }

    #[cfg(not(feature = "native"))]
    pub async fn stream(
        &self,
        _message: Message,
    ) -> Pin<Box<dyn Stream<Item = Result<Message, AgentError>> + Send>> {
        Box::pin(futures::stream::once(async {
            Err(AgentError::Transport("Ollama adapter requires 'native' feature".to_string()))
        }))
    }

    #[cfg(feature = "native")]
    async fn stream_api_impl(&self, messages: Vec<OllamaMessage>) -> Result<Vec<Message>, AgentError> {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(self.config.timeout_seconds))
            .build()
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        let mut request_body = json!({
            "model": self.config.model,
            "messages": messages,
            "stream": true,
        });

        if let Some(temp) = self.config.temperature {
            request_body["temperature"] = json!(temp);
        }

        let response = client
            .post(format!("{}/api/chat", self.config.base_url))
            .json(&request_body)
            .send()
            .await
            .map_err(|e| AgentError::Transport(e.to_string()))?;

        if !response.status().is_success() {
            let status = response.status();
            let body = response.text().await.unwrap_or_default();
            return Err(AgentError::Http(format!("Ollama API error ({}): {}", status, body)));
        }

        let body = response.text().await.map_err(|e| AgentError::Transport(e.to_string()))?;

        // Parse newline-delimited JSON
        let mut chunks = Vec::new();
        for line in body.lines() {
            if line.is_empty() {
                continue;
            }

            let chunk_json: serde_json::Value = serde_json::from_str(line)
                .map_err(|e| AgentError::Serialization(e.to_string()))?;

            if let Some(message) = chunk_json["message"].as_object() {
                if let Some(content) = message.get("content") {
                    if let Some(text) = content.as_str() {
                        let mut msg = Message::with_text("assistant", text);
                        msg.with_metadata("streaming", json!(true));
                        chunks.push(msg);
                    }
                }
            }
        }

        Ok(chunks)
    }
```

**Example:** `agenkit-rust/examples/ollama_streaming.rs` (copy from openai_streaming.rs, change to OllamaAgent)

---

### 2. Rust LiteLLM Streaming (~150 LOC)

**File:** `agenkit-rust/src/adapters/litellm.rs`

Same pattern as Rust OpenAI (SSE parsing), but use LiteLLM base URL:
- Change endpoint to `{base_url}/chat/completions`
- Use OpenAI-compatible SSE format
- Parse `choices[0].delta.content`

---

## C++ Implementations (2 adapters)

### 3. C++ OpenAI Streaming (~250 LOC)

**File:** `agenkit-cpp/src/adapters/openai_agent.cpp`

**Pattern:** Follow claude_agent.cpp SSE parsing pattern

**Key changes:**
- Endpoint: `/v1/chat/completions`
- Header: `Authorization: Bearer {api_key}`
- Parse `choices[0].delta.content` instead of ContentBlockDelta

**Add to header (`openai_agent.hpp`):**
```cpp
core::Result<void, core::AgentError>
stream(core::Message message, std::function<bool(const std::string&)> callback);
```

**Implementation:** Copy from claude_agent.cpp streaming, modify JSON parsing for OpenAI format

---

### 4. C++ Ollama Streaming (~250 LOC)

**File:** Create `agenkit-cpp/src/adapters/ollama_agent.cpp`

**Pattern:** Similar to Gemini (newline-delimited JSON), but simpler

- No API key required
- Endpoint: `{base_url}/api/chat`
- Parse newline-JSON for `message.content`

---

## Zig Implementation (1 adapter)

### 5. Zig LiteLLM Streaming (~90 LOC)

**File:** `agenkit-zig/src/adapter/litellm.zig`

**Add before `pub const LiteLLMLLM`:**
```zig
const LiteLLMStream = struct {
    allocator: Allocator,
    self: *LiteLLMLLM,
    chunks: std.ArrayList([]const u8),
    current_index: usize,

    fn makeStreamRequest(self: *LiteLLMStream, body: []const u8) !void {
        // Same pattern as OpenAIStream in openai.zig
        // Endpoint: {base_url}/chat/completions
        // Parse SSE with "data: " prefix
    }

    fn parseSSEStream(self: *LiteLLMStream, data: []const u8) !void {
        // Copy from openai.zig parseSSEStream
    }

    fn deinit(self: *LiteLLMStream) void {
        for (self.chunks.items) |chunk| self.allocator.free(chunk);
        self.chunks.deinit();
        self.allocator.destroy(self);
    }
};

fn litellmStreamNext(ptr: *anyopaque, allocator: Allocator) !?*Message {
    // Same pattern as openaiStreamNext
}

fn litellmStreamDeinit(ptr: *anyopaque) void {
    // Same pattern as openaiStreamDeinit
}
```

**Update stream() function:** Replace `error.StreamingNotSupported` with actual implementation (copy from openai.zig)

---

## TypeScript Implementations (5 adapters)

### 6. TypeScript OpenAI Streaming (~150 LOC)

**File:** `agenkit-ts/src/adapters/openai.ts`

**Leverage official SDK:**
```typescript
import OpenAI from 'openai';

export class OpenAIAdapter implements LLMAdapter {
    private client: OpenAI;

    async *stream(messages: Message[]): AsyncIterableIterator<string> {
        const stream = await this.client.chat.completions.create({
            model: this.config.model,
            messages: messages.map(m => ({
                role: m.role,
                content: m.content,
            })),
            stream: true,
        });

        for await (const chunk of stream) {
            const content = chunk.choices[0]?.delta?.content;
            if (content) {
                yield content;
            }
        }
    }
}
```

**Example:** `examples/adapters/openai-streaming.ts`

---

### 7. TypeScript Anthropic Streaming (~150 LOC)

**File:** `agenkit-ts/src/adapters/anthropic.ts`

**Leverage Anthropic SDK:**
```typescript
import Anthropic from '@anthropic-ai/sdk';

export class AnthropicAdapter implements LLMAdapter {
    private client: Anthropic;

    async *stream(messages: Message[]): AsyncIterableIterator<string> {
        const stream = await this.client.messages.stream({
            model: this.config.model,
            max_tokens: this.config.maxTokens,
            messages: messages.map(m => ({
                role: m.role === 'user' ? 'user' : 'assistant',
                content: m.content,
            })),
        });

        for await (const event of stream) {
            if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
                yield event.delta.text;
            }
        }
    }
}
```

---

### 8. TypeScript Gemini Streaming (~150 LOC)

**File:** `agenkit-ts/src/adapters/gemini.ts`

Use Google AI SDK streaming:
```typescript
import { GoogleGenerativeAI } from '@google/generative-ai';

async *stream(messages: Message[]): AsyncIterableIterator<string> {
    const result = await model.generateContentStream({
        contents: messages.map(m => ({
            role: m.role === 'user' ? 'user' : 'model',
            parts: [{ text: m.content }],
        })),
    });

    for await (const chunk of result.stream) {
        const text = chunk.text();
        if (text) yield text;
    }
}
```

---

### 9. TypeScript Bedrock Streaming (~200 LOC)

**File:** `agenkit-ts/src/adapters/bedrock.ts`

Use AWS SDK:
```typescript
import { BedrockRuntimeClient, ConverseStreamCommand } from '@aws-sdk/client-bedrock-runtime';

async *stream(messages: Message[]): AsyncIterableIterator<string> {
    const command = new ConverseStreamCommand({
        modelId: this.config.model,
        messages: messages.map(m => ({
            role: m.role === 'user' ? 'user' : 'assistant',
            content: [{ text: m.content }],
        })),
    });

    const response = await this.client.send(command);

    for await (const event of response.stream!) {
        if (event.contentBlockDelta?.delta?.text) {
            yield event.contentBlockDelta.delta.text;
        }
    }
}
```

---

### 10. TypeScript LiteLLM Streaming (~150 LOC)

**File:** `agenkit-ts/src/adapters/litellm.ts`

Use fetch with SSE parsing:
```typescript
async *stream(messages: Message[]): AsyncIterableIterator<string> {
    const response = await fetch(`${this.config.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.config.apiKey}`,
        },
        body: JSON.stringify({
            model: this.config.model,
            messages: messages.map(m => ({ role: m.role, content: m.content })),
            stream: true,
        }),
    });

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
            if (line.startsWith('data: ') && line !== 'data: [DONE]') {
                const json = JSON.parse(line.slice(6));
                const content = json.choices?.[0]?.delta?.content;
                if (content) yield content;
            }
        }
    }
}
```

---

## Testing Each Implementation

### Quick Test Script

```bash
# Rust
cd agenkit-rust
cargo run --example {adapter}_streaming --features native

# C++
cd agenkit-cpp/build
cmake .. && make {adapter}-streaming
./{adapter}-streaming

# Zig
cd agenkit-zig
zig build run-{adapter}-streaming

# TypeScript
cd agenkit-ts
npm run example:adapters/{adapter}-streaming
```

---

## Completion Checklist

- [ ] Rust Ollama streaming (~100 LOC)
- [ ] Rust LiteLLM streaming (~150 LOC)
- [ ] C++ OpenAI streaming (~250 LOC)
- [ ] C++ Ollama streaming (~250 LOC)
- [ ] Zig LiteLLM streaming (~90 LOC)
- [ ] TypeScript OpenAI streaming (~150 LOC)
- [ ] TypeScript Anthropic streaming (~150 LOC)
- [ ] TypeScript Gemini streaming (~150 LOC)
- [ ] TypeScript Bedrock streaming (~200 LOC)
- [ ] TypeScript LiteLLM streaming (~150 LOC)

**Total:** ~1,640 LOC remaining

---

## After Completion

Run full audit:
```bash
./scripts/test-streaming-parity.sh
```

Expected result: **34/35 providers (97%)** with streaming support

Only deferred: Zig Bedrock (requires AWS SigV4 implementation without SDK)
