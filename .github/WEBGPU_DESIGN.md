# WebGPU Integration Technical Design

**Status**: 📋 Design Phase
**Target Release**: v0.40.0 - v0.43.0
**Author**: System Design
**Last Updated**: December 2025

---

## Executive Summary

This document describes the integration of WebGPU into Agenkit's Rust WASM implementation, enabling GPU-accelerated AI agent inference directly in web browsers. WebGPU provides 20-100x performance improvements for compute-intensive operations like LLM inference, embedding generation, and vision processing.

**Key Objectives:**
- Enable local LLM inference in browsers (1B-7B parameter models)
- GPU-accelerated embedding generation for RAG applications
- Unlock parallel pattern execution in WASM (6th → 7th pattern)
- Maintain backwards compatibility with existing WASM implementation

**Business Value:**
- Zero inference costs (no API calls)
- Complete privacy (data never leaves browser)
- Offline-capable AI agents
- First-mover advantage in WebGPU agent frameworks

---

## Table of Contents

1. [Background](#1-background)
2. [Architecture Overview](#2-architecture-overview)
3. [Component Design](#3-component-design)
4. [Implementation Phases](#4-implementation-phases)
5. [API Design](#5-api-design)
6. [Performance Targets](#6-performance-targets)
7. [Browser Compatibility](#7-browser-compatibility)
8. [Memory Management](#8-memory-management)
9. [Security Considerations](#9-security-considerations)
10. [Testing Strategy](#10-testing-strategy)
11. [Documentation Requirements](#11-documentation-requirements)
12. [Open Questions](#12-open-questions)

---

## 1. Background

### 1.1 WebGPU Capabilities

**WebGPU** is a modern GPU API available in browsers:
- Chrome/Chromium 113+ (May 2023)
- Edge 113+
- Safari 18+ (September 2024)
- Firefox Nightly (in development)

**Key Features:**
- Compute shaders (WGSL - WebGPU Shading Language)
- Direct buffer sharing with WASM (zero-copy)
- 10-100x faster than CPU for parallel operations
- Native browser support (no plugins)

### 1.2 Current WASM Limitations

Agenkit Rust WASM currently supports 5/11 patterns:
- ✅ Reflection, Agents-as-Tools, Orchestration (sequential), ReAct, Conversational
- ❌ Task, Planning, Multiagent, Autonomous, Memory Hierarchy, Reasoning with Tools

**Limitations:**
- No tokio runtime (no native threading)
- Sequential execution only (no parallel pattern)
- CPU-bound inference too slow for practical LLMs
- No GPU acceleration for embeddings/vision

### 1.3 Strategic Opportunity

**Market Gap:**
- Transformers.js: CPU-only WASM (too slow)
- ONNX Runtime Web: Limited model support
- WebLLM (MLC): Not an agent framework
- **Agenkit**: First agent framework with WebGPU support

**Use Cases Unlocked:**
- Browser-based chatbots with local LLMs (no API keys)
- Privacy-preserving RAG with local embeddings
- Offline-capable AI agents
- Real-time multimodal processing (vision + text)

---

## 2. Architecture Overview

### 2.1 Layer Structure

```
┌──────────────────────────────────────────────────────┐
│  Agenkit Application Layer                            │
│  (User code: React, Vue, vanilla JS)                 │
└──────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Agenkit Rust WASM + WebGPU                          │
├──────────────────────────────────────────────────────┤
│  Pattern Layer                                        │
│  ├─ Existing: 5 WASM-compatible patterns            │
│  ├─ NEW: Parallel (WebGPU batching)                 │
│  └─ NEW: Multimodal patterns                        │
├──────────────────────────────────────────────────────┤
│  Adapter Layer                                        │
│  ├─ Existing: HTTP-based (OpenAI, Anthropic, etc.)  │
│  ├─ NEW: WebGPULLMAdapter (local inference)         │
│  ├─ NEW: WebGPUEmbeddingAdapter (local embeddings)  │
│  └─ NEW: WebGPUVisionAdapter (image understanding)  │
├──────────────────────────────────────────────────────┤
│  WebGPU Compute Layer (NEW)                          │
│  ├─ GPU Context Management                          │
│  ├─ Buffer Management (staging, storage, uniform)   │
│  ├─ Shader Compilation & Caching                    │
│  ├─ Model Loading & Quantization                    │
│  ├─ Kernel Dispatch & Synchronization               │
│  └─ Memory Pool & Cleanup                           │
├──────────────────────────────────────────────────────┤
│  Browser WebGPU API (web-sys bindings)              │
│  └─ navigator.gpu                                    │
└──────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

#### Local LLM Inference Flow

```
User Input (JavaScript)
    ↓
WASM Agent.process(message)
    ↓
Tokenization (CPU, WASM)
    ↓
Upload tokens to GPU buffer
    ↓
GPU Compute (WebGPU shaders)
├─ Embedding layer
├─ Attention layers (multi-head self-attention)
├─ Feed-forward layers
└─ Output projection
    ↓
Download logits from GPU buffer
    ↓
Decoding & Sampling (CPU, WASM)
    ↓
Return Response (JavaScript)
```

### 2.3 Memory Layout

```
┌─────────────────────────────────────────┐
│  Browser Heap (JavaScript)              │
│  ├─ Application data                    │
│  └─ WASM module references              │
└─────────────────────────────────────────┘
            ↓ (wasm-bindgen)
┌─────────────────────────────────────────┐
│  WASM Linear Memory                     │
│  ├─ Rust data structures                │
│  ├─ Tokenizer data                      │
│  ├─ Staging buffers                     │
│  └─ Shared buffers with GPU (mapped)   │
└─────────────────────────────────────────┘
            ↓ (WebGPU buffer mapping)
┌─────────────────────────────────────────┐
│  GPU Memory (VRAM)                      │
│  ├─ Model weights (read-only)          │
│  ├─ Activations (read-write)           │
│  ├─ KV cache (read-write, persistent)  │
│  └─ Output buffers (write, mapped)     │
└─────────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 WebGPU Context Manager

**Responsibility**: Initialize and manage GPU device, queue, and feature detection

```rust
// agenkit-rust/src/webgpu/context.rs

use web_sys::{GpuDevice, GpuQueue, GpuAdapter};
use wasm_bindgen::prelude::*;

pub struct WebGPUContext {
    device: GpuDevice,
    queue: GpuQueue,
    adapter_info: AdapterInfo,
}

pub struct AdapterInfo {
    pub max_buffer_size: u64,
    pub max_compute_workgroup_size_x: u32,
    pub max_compute_workgroups_per_dimension: u32,
}

impl WebGPUContext {
    /// Initialize WebGPU context
    /// Returns None if WebGPU is not available
    pub async fn new() -> Result<Option<Self>, JsValue> {
        let window = web_sys::window().ok_or("No window")?;
        let navigator = window.navigator();

        // Check if WebGPU is available
        let gpu = match navigator.gpu() {
            Some(gpu) => gpu,
            None => return Ok(None), // Graceful fallback
        };

        // Request adapter
        let adapter = gpu.request_adapter().await?;

        // Get adapter limits
        let limits = adapter.limits();
        let adapter_info = AdapterInfo {
            max_buffer_size: limits.max_buffer_size(),
            max_compute_workgroup_size_x: limits.max_compute_workgroup_size_x(),
            max_compute_workgroups_per_dimension: limits.max_compute_workgroups_per_dimension(),
        };

        // Request device
        let device = adapter.request_device().await?;
        let queue = device.queue();

        Ok(Some(Self {
            device,
            queue,
            adapter_info,
        }))
    }

    pub fn device(&self) -> &GpuDevice {
        &self.device
    }

    pub fn queue(&self) -> &GpuQueue {
        &self.queue
    }

    pub fn max_buffer_size(&self) -> u64 {
        self.adapter_info.max_buffer_size
    }
}
```

### 3.2 Buffer Manager

**Responsibility**: Allocate, deallocate, and manage GPU buffers with lifecycle tracking

```rust
// agenkit-rust/src/webgpu/buffer.rs

use web_sys::{GpuBuffer, GpuBufferDescriptor, GpuBufferUsage};
use std::collections::HashMap;

pub struct BufferManager {
    context: WebGPUContext,
    buffers: HashMap<String, GpuBuffer>,
    buffer_sizes: HashMap<String, u64>,
}

impl BufferManager {
    pub fn new(context: WebGPUContext) -> Self {
        Self {
            context,
            buffers: HashMap::new(),
            buffer_sizes: HashMap::new(),
        }
    }

    /// Create a storage buffer (read/write from compute shaders)
    pub fn create_storage_buffer(&mut self, name: &str, size: u64) -> Result<(), JsValue> {
        let buffer = self.context.device().create_buffer(&GpuBufferDescriptor::new(
            size,
            GpuBufferUsage::STORAGE | GpuBufferUsage::COPY_DST | GpuBufferUsage::COPY_SRC,
        ));

        self.buffers.insert(name.to_string(), buffer);
        self.buffer_sizes.insert(name.to_string(), size);

        Ok(())
    }

    /// Create a uniform buffer (read-only constants)
    pub fn create_uniform_buffer(&mut self, name: &str, size: u64) -> Result<(), JsValue> {
        let buffer = self.context.device().create_buffer(&GpuBufferDescriptor::new(
            size,
            GpuBufferUsage::UNIFORM | GpuBufferUsage::COPY_DST,
        ));

        self.buffers.insert(name.to_string(), buffer);
        self.buffer_sizes.insert(name.to_string(), size);

        Ok(())
    }

    /// Create a mapped buffer (accessible from WASM)
    pub fn create_mapped_buffer(&mut self, name: &str, size: u64) -> Result<(), JsValue> {
        let buffer = self.context.device().create_buffer(&GpuBufferDescriptor::new(
            size,
            GpuBufferUsage::MAP_READ | GpuBufferUsage::COPY_DST,
        ));

        self.buffers.insert(name.to_string(), buffer);
        self.buffer_sizes.insert(name.to_string(), size);

        Ok(())
    }

    /// Write data to buffer
    pub fn write_buffer(&self, name: &str, data: &[u8]) -> Result<(), JsValue> {
        let buffer = self.buffers.get(name)
            .ok_or("Buffer not found")?;

        self.context.queue().write_buffer_with_u8_array(buffer, 0, data);

        Ok(())
    }

    /// Get buffer by name
    pub fn get_buffer(&self, name: &str) -> Option<&GpuBuffer> {
        self.buffers.get(name)
    }

    /// Clean up all buffers
    pub fn cleanup(&mut self) {
        for buffer in self.buffers.values() {
            buffer.destroy();
        }
        self.buffers.clear();
        self.buffer_sizes.clear();
    }
}

impl Drop for BufferManager {
    fn drop(&mut self) {
        self.cleanup();
    }
}
```

### 3.3 Shader Manager

**Responsibility**: Compile, cache, and manage compute shaders

```rust
// agenkit-rust/src/webgpu/shader.rs

use web_sys::{GpuShaderModule, GpuComputePipeline};
use std::collections::HashMap;

pub struct ShaderManager {
    context: WebGPUContext,
    modules: HashMap<String, GpuShaderModule>,
    pipelines: HashMap<String, GpuComputePipeline>,
}

impl ShaderManager {
    pub fn new(context: WebGPUContext) -> Self {
        Self {
            context,
            modules: HashMap::new(),
            pipelines: HashMap::new(),
        }
    }

    /// Compile WGSL shader source
    pub fn compile_shader(&mut self, name: &str, source: &str) -> Result<(), JsValue> {
        let module = self.context.device().create_shader_module(&web_sys::GpuShaderModuleDescriptor::new(source));

        self.modules.insert(name.to_string(), module);

        Ok(())
    }

    /// Create compute pipeline from shader
    pub fn create_pipeline(&mut self, name: &str, shader_name: &str, entry_point: &str) -> Result<(), JsValue> {
        let module = self.modules.get(shader_name)
            .ok_or("Shader module not found")?;

        let pipeline = self.context.device().create_compute_pipeline(&web_sys::GpuComputePipelineDescriptor::new(
            &web_sys::GpuProgrammableStage::new(entry_point, module),
        ));

        self.pipelines.insert(name.to_string(), pipeline);

        Ok(())
    }

    /// Get pipeline by name
    pub fn get_pipeline(&self, name: &str) -> Option<&GpuComputePipeline> {
        self.pipelines.get(name)
    }
}
```

### 3.4 Model Loader

**Responsibility**: Load and quantize model weights, manage model metadata

```rust
// agenkit-rust/src/webgpu/model_loader.rs

use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct ModelMetadata {
    pub name: String,
    pub architecture: String,  // "llama", "bert", "clip", etc.
    pub num_layers: u32,
    pub hidden_size: u32,
    pub num_heads: u32,
    pub vocab_size: u32,
    pub quantization: Quantization,
    pub total_size_bytes: u64,
}

#[derive(Serialize, Deserialize)]
pub enum Quantization {
    None,
    Int8,
    Int4,  // GPTQ, AWQ
}

pub struct ModelLoader {
    buffer_manager: BufferManager,
}

impl ModelLoader {
    pub fn new(buffer_manager: BufferManager) -> Self {
        Self { buffer_manager }
    }

    /// Load model from URL (IndexedDB cache-first)
    pub async fn load_model(&mut self, url: &str) -> Result<ModelMetadata, JsValue> {
        // 1. Check IndexedDB cache
        if let Some(cached) = self.load_from_cache(url).await? {
            return Ok(cached);
        }

        // 2. Fetch from URL (with progress callback)
        let model_data = self.fetch_with_progress(url).await?;

        // 3. Parse metadata
        let metadata: ModelMetadata = serde_json::from_slice(&model_data[0..4096])?;

        // 4. Load weights into GPU buffers
        self.load_weights(&model_data[4096..], &metadata).await?;

        // 5. Cache to IndexedDB
        self.save_to_cache(url, &model_data).await?;

        Ok(metadata)
    }

    async fn load_weights(&mut self, weights_data: &[u8], metadata: &ModelMetadata) -> Result<(), JsValue> {
        // Create buffer for model weights
        let buffer_size = weights_data.len() as u64;
        self.buffer_manager.create_storage_buffer("model_weights", buffer_size)?;

        // Upload weights to GPU
        self.buffer_manager.write_buffer("model_weights", weights_data)?;

        Ok(())
    }

    async fn load_from_cache(&self, url: &str) -> Result<Option<ModelMetadata>, JsValue> {
        // IndexedDB implementation
        todo!("Implement IndexedDB caching")
    }

    async fn fetch_with_progress(&self, url: &str) -> Result<Vec<u8>, JsValue> {
        // Fetch with progress events
        todo!("Implement fetch with progress")
    }

    async fn save_to_cache(&self, url: &str, data: &[u8]) -> Result<(), JsValue> {
        // IndexedDB implementation
        todo!("Implement IndexedDB caching")
    }
}
```

### 3.5 WebGPU LLM Adapter

**Responsibility**: Local LLM inference using GPU compute shaders

```rust
// agenkit-rust/src/adapters/webgpu_llm.rs

use crate::core::{Agent, Message, AgentError};
use crate::webgpu::{WebGPUContext, BufferManager, ShaderManager, ModelLoader};

pub struct WebGPULLMAdapter {
    context: WebGPUContext,
    buffer_manager: BufferManager,
    shader_manager: ShaderManager,
    model_metadata: ModelMetadata,
    kv_cache: Option<KVCache>,
}

impl WebGPULLMAdapter {
    /// Create new adapter and load model
    pub async fn new(model_name: &str) -> Result<Self, JsValue> {
        // Initialize WebGPU
        let context = WebGPUContext::new().await?
            .ok_or("WebGPU not available")?;

        // Create managers
        let buffer_manager = BufferManager::new(context.clone());
        let shader_manager = ShaderManager::new(context.clone());

        // Load model
        let mut model_loader = ModelLoader::new(buffer_manager.clone());
        let model_metadata = model_loader.load_model(&format!("https://cdn.example.com/models/{}", model_name)).await?;

        // Compile shaders
        let mut adapter = Self {
            context,
            buffer_manager,
            shader_manager,
            model_metadata,
            kv_cache: None,
        };

        adapter.compile_shaders().await?;

        Ok(adapter)
    }

    async fn compile_shaders(&mut self) -> Result<(), JsValue> {
        // Compile attention shader
        self.shader_manager.compile_shader("attention", include_str!("../shaders/attention.wgsl"))?;
        self.shader_manager.create_pipeline("attention", "attention", "main")?;

        // Compile feed-forward shader
        self.shader_manager.compile_shader("feedforward", include_str!("../shaders/feedforward.wgsl"))?;
        self.shader_manager.create_pipeline("feedforward", "feedforward", "main")?;

        // Compile layernorm shader
        self.shader_manager.compile_shader("layernorm", include_str!("../shaders/layernorm.wgsl"))?;
        self.shader_manager.create_pipeline("layernorm", "layernorm", "main")?;

        Ok(())
    }

    async fn forward_pass(&mut self, tokens: &[u32]) -> Result<Vec<f32>, JsValue> {
        // 1. Upload tokens to GPU
        let tokens_bytes = bytemuck::cast_slice(tokens);
        self.buffer_manager.write_buffer("input_tokens", tokens_bytes)?;

        // 2. Embedding layer
        self.dispatch_embedding(tokens.len()).await?;

        // 3. Transformer layers
        for layer_idx in 0..self.model_metadata.num_layers {
            self.dispatch_attention(layer_idx, tokens.len()).await?;
            self.dispatch_feedforward(layer_idx, tokens.len()).await?;
        }

        // 4. Output projection
        self.dispatch_output_projection(tokens.len()).await?;

        // 5. Download logits from GPU
        let logits = self.read_logits().await?;

        Ok(logits)
    }

    async fn dispatch_attention(&self, layer: u32, seq_len: usize) -> Result<(), JsValue> {
        let encoder = self.context.device().create_command_encoder();
        let compute_pass = encoder.begin_compute_pass();

        let pipeline = self.shader_manager.get_pipeline("attention")
            .ok_or("Attention pipeline not found")?;

        compute_pass.set_pipeline(pipeline);

        // Dispatch workgroups (seq_len / 256 workgroups)
        let workgroups = (seq_len as u32 + 255) / 256;
        compute_pass.dispatch_workgroups(workgroups, 1, 1);
        compute_pass.end();

        self.context.queue().submit(&[encoder.finish()]);

        Ok(())
    }

    async fn dispatch_feedforward(&self, layer: u32, seq_len: usize) -> Result<(), JsValue> {
        // Similar to dispatch_attention
        todo!("Implement feedforward dispatch")
    }

    async fn dispatch_embedding(&self, seq_len: usize) -> Result<(), JsValue> {
        // Embedding lookup
        todo!("Implement embedding dispatch")
    }

    async fn dispatch_output_projection(&self, seq_len: usize) -> Result<(), JsValue> {
        // Final linear projection to vocab
        todo!("Implement output projection")
    }

    async fn read_logits(&self) -> Result<Vec<f32>, JsValue> {
        // Map GPU buffer and read logits
        todo!("Implement logits reading")
    }
}

#[async_trait::async_trait(?Send)]
impl Agent for WebGPULLMAdapter {
    fn name(&self) -> String {
        format!("webgpu-{}", self.model_metadata.name)
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["text-generation".to_string(), "local-inference".to_string()]
    }

    async fn process(&self, message: Message) -> Result<Message, AgentError> {
        // 1. Tokenize input
        let tokens = self.tokenize(message.content_as_str())?;

        // 2. GPU forward pass
        let logits = self.forward_pass(&tokens).await
            .map_err(|e| AgentError::processing_error(format!("GPU forward pass failed: {:?}", e)))?;

        // 3. Sample next token
        let next_token = self.sample(&logits)?;

        // 4. Decode token to text
        let response_text = self.decode(&[next_token])?;

        // 5. Return response
        let mut response = Message::with_text("assistant", &response_text);
        response.with_metadata("model", self.model_metadata.name.clone());
        response.with_metadata("inference_type", "local_gpu");

        Ok(response)
    }
}
```

### 3.6 WebGPU Embedding Adapter

**Responsibility**: Fast embedding generation for RAG applications

```rust
// agenkit-rust/src/adapters/webgpu_embedding.rs

pub struct WebGPUEmbeddingAdapter {
    context: WebGPUContext,
    buffer_manager: BufferManager,
    shader_manager: ShaderManager,
    model_metadata: ModelMetadata,
    embedding_dim: usize,
}

impl WebGPUEmbeddingAdapter {
    pub async fn new(model_name: &str) -> Result<Self, JsValue> {
        // Similar initialization to WebGPULLMAdapter
        // Load smaller embedding model (e.g., MiniLM-L6-v2, ~80MB)
        todo!()
    }

    /// Generate embedding for text
    pub async fn embed(&self, text: &str) -> Result<Vec<f32>, JsValue> {
        // 1. Tokenize
        let tokens = self.tokenize(text)?;

        // 2. GPU forward pass (much faster than LLM)
        let embedding = self.forward_pass(&tokens).await?;

        Ok(embedding)
    }

    /// Batch embed multiple texts (parallel on GPU)
    pub async fn embed_batch(&self, texts: Vec<String>) -> Result<Vec<Vec<f32>>, JsValue> {
        // GPU batch processing for maximum throughput
        todo!()
    }
}
```

---

## 4. Implementation Phases

### Phase 1: Foundation (v0.40.0 - 2 weeks)

**Scope**: WebGPU infrastructure without models

**Tasks:**
1. Create `agenkit-rust/src/webgpu/` module structure
2. Implement `WebGPUContext` (device, queue, feature detection)
3. Implement `BufferManager` (allocation, deallocation, lifecycle)
4. Implement `ShaderManager` (compilation, caching, pipeline creation)
5. Write basic compute shader (matrix multiplication benchmark)
6. Add feature flags: `webgpu` feature in Cargo.toml
7. Browser detection and graceful fallback
8. Unit tests for buffer management
9. Example: Basic GPU matrix multiply in browser

**Deliverables:**
- Working WebGPU initialization
- Buffer management with proper cleanup
- Shader compilation pipeline
- Matrix multiply benchmark showing 10-100x speedup
- Documentation: `WEBGPU.md` (getting started guide)

**Success Criteria:**
- WebGPU context initializes in Chrome/Edge/Safari
- Buffers allocate/deallocate without leaks
- Compute shaders execute correctly
- Benchmark shows expected GPU speedup

### Phase 2: Embedding Adapter (v0.41.0 - 2 weeks)

**Scope**: GPU-accelerated embedding generation

**Tasks:**
1. Implement `ModelLoader` (fetch, cache, quantization)
2. Implement tokenizer (Byte-Pair Encoding in Rust)
3. Write transformer shaders (attention, feedforward, layernorm)
4. Implement `WebGPUEmbeddingAdapter`
5. Load MiniLM-L6-v2 model (80MB, 384-dim embeddings)
6. IndexedDB caching for model weights
7. Batch processing for multiple texts
8. Benchmarks: CPU vs GPU embedding generation
9. Example: Semantic search in browser

**Deliverables:**
- Working embedding adapter
- 20-100x speedup vs CPU WASM
- Browser example: semantic document search
- NPM package: `@agenkit/webgpu-embeddings`
- Performance documentation

**Success Criteria:**
- Generate embeddings in <10ms per text
- 100+ embeddings/sec throughput
- Model caches correctly (load once)
- Zero memory leaks after 1000+ embeddings

### Phase 3: Local LLM Inference (v0.42.0 - 4 weeks)

**Scope**: Full LLM inference on GPU

**Tasks:**
1. Extend shader library (all transformer operations)
2. Implement KV cache management (for generation)
3. Implement autoregressive generation loop
4. Implement sampling strategies (top-k, top-p, temperature)
5. Load quantized Llama 3.2 1B model (4-bit, ~1.5GB)
6. Streaming token generation
7. Progressive model loading (download while initializing)
8. Memory optimization (offload inactive layers)
9. Benchmarks: tokens/sec, memory usage
10. Example: Chatbot with local LLM (no API keys)

**Deliverables:**
- `WebGPULLMAdapter` with full generation
- 20-50 tokens/sec generation speed
- Browser chatbot example (self-contained)
- Model loading from CDN with progress bar
- Documentation: Local LLM guide

**Success Criteria:**
- Generate coherent text (perplexity check)
- Stable memory usage (no leaks during long sessions)
- Works on 8GB VRAM GPUs
- Acceptable latency (<2s first token)

### Phase 4: Parallel Pattern & Vision (v0.43.0 - 3 weeks)

**Scope**: Advanced features and multimodal

**Tasks:**
1. Implement GPU batch processing for parallel pattern
2. Unlock 7th WASM pattern (Parallel Orchestration)
3. Implement `WebGPUVisionAdapter` (CLIP ViT-B/32)
4. Image preprocessing shaders
5. Multimodal embedding generation (text + image)
6. Example: Multimodal RAG (search text and images)
7. Example: Parallel agent execution with GPU batching
8. Comprehensive benchmarks (all adapters)
9. Production optimization (memory, latency)
10. Security audit (shader injection, buffer overflows)

**Deliverables:**
- 7th WASM pattern enabled
- Vision adapter with image embeddings
- Multimodal RAG example
- Complete benchmark suite
- Security documentation

**Success Criteria:**
- 7/11 WASM patterns working
- Vision embeddings in <50ms per image
- Parallel pattern 3-5x faster than sequential
- Zero security vulnerabilities found in audit

---

## 5. API Design

### 5.1 JavaScript/TypeScript API

```typescript
// Usage in browser application
import init, { WebGPULLMAdapter, WebGPUEmbeddingAdapter, JsMessage } from '@agenkit/webgpu';

// Initialize WASM
await init();

// Check WebGPU support
if (await hasWebGPU()) {
    // Create local LLM adapter (no API keys!)
    const agent = await WebGPULLMAdapter.new("llama3.2-1b-q4");

    // Process message
    const response = await agent.process(
        new JsMessage("user", "Explain WebGPU in simple terms")
    );

    console.log(response.content); // GPU-generated response
} else {
    // Fall back to API-based adapter
    const agent = new OpenAIAdapter(apiKey);
    const response = await agent.process(message);
}

// Embedding generation for RAG
const embedder = await WebGPUEmbeddingAdapter.new("minilm-l6-v2");

const documents = [
    "WebGPU is a modern GPU API for browsers.",
    "Agenkit is a framework for AI agents.",
    "Rust compiles to WebAssembly for the web.",
];

// Batch embed (parallel on GPU)
const embeddings = await embedder.embedBatch(documents);

// Semantic search
const query = "What is WebGPU?";
const queryEmbedding = await embedder.embed(query);
const similarities = embeddings.map(e => cosineSimilarity(queryEmbedding, e));
const bestMatch = documents[argmax(similarities)];
```

### 5.2 Feature Detection API

```typescript
// Detect WebGPU support
async function hasWebGPU(): Promise<boolean> {
    if (!navigator.gpu) return false;

    try {
        const adapter = await navigator.gpu.requestAdapter();
        return adapter !== null;
    } catch {
        return false;
    }
}

// Get GPU capabilities
async function getGPUInfo(): Promise<GPUInfo> {
    const adapter = await navigator.gpu.requestAdapter();
    const limits = adapter.limits;

    return {
        maxBufferSize: limits.maxBufferSize,
        maxComputeWorkgroupSizeX: limits.maxComputeWorkgroupSizeX,
        // ... other limits
    };
}
```

### 5.3 Progressive Model Loading

```typescript
// Load model with progress callback
const agent = await WebGPULLMAdapter.newWithProgress(
    "llama3.2-1b-q4",
    (progress: LoadProgress) => {
        console.log(`Loading: ${progress.loaded}/${progress.total} bytes (${progress.percent}%)`);
        updateProgressBar(progress.percent);
    }
);
```

---

## 6. Performance Targets

### 6.1 Embedding Generation

| Operation | CPU WASM | WebGPU | Speedup |
|-----------|----------|--------|---------|
| Single embedding (384-dim) | 100ms | 5ms | 20x |
| Batch 10 embeddings | 1000ms | 15ms | 66x |
| Batch 100 embeddings | 10s | 80ms | 125x |

**Target**: 100+ embeddings/sec with WebGPU

### 6.2 LLM Inference (Llama 3.2 1B, 4-bit)

| Metric | Target |
|--------|--------|
| First token latency | <2s |
| Token generation speed | 20-50 tokens/sec |
| Memory usage (VRAM) | <2GB |
| Model loading time | <10s (cached: <1s) |

**Comparison**:
- CPU WASM: 1-5 tokens/sec (too slow)
- WebGPU: 20-50 tokens/sec (acceptable)
- Native GPU (Python): 50-100 tokens/sec (optimal)

### 6.3 Vision Encoding (CLIP ViT-B/32)

| Operation | CPU WASM | WebGPU | Speedup |
|-----------|----------|--------|---------|
| Single image (224x224) | 1000ms | 50ms | 20x |
| Batch 10 images | 10s | 200ms | 50x |

**Target**: 10-20 images/sec with WebGPU

---

## 7. Browser Compatibility

### 7.1 WebGPU Support Matrix

| Browser | Version | Status | Notes |
|---------|---------|--------|-------|
| Chrome | 113+ | ✅ Full support | Stable since May 2023 |
| Edge | 113+ | ✅ Full support | Chromium-based |
| Safari | 18+ | ✅ Full support | macOS, iOS |
| Firefox | Nightly | 🚧 Experimental | Behind flag |
| Firefox Stable | - | ❌ Not yet | Planned 2025 |

### 7.2 Fallback Strategy

```rust
// Automatic fallback if WebGPU unavailable
pub async fn create_agent(model: &str, api_key: Option<&str>) -> Result<Box<dyn Agent>, JsValue> {
    // Try WebGPU first
    if let Some(webgpu_agent) = WebGPULLMAdapter::new(model).await.ok() {
        return Ok(Box::new(webgpu_agent));
    }

    // Fall back to API-based adapter
    if let Some(key) = api_key {
        let api_agent = OpenAIAdapter::new(key)?;
        return Ok(Box::new(api_agent));
    }

    Err("Neither WebGPU nor API key available".into())
}
```

### 7.3 Feature Detection at Runtime

```javascript
// Detect and display capabilities to user
const gpuInfo = await detectGPUCapabilities();

if (gpuInfo.webgpu) {
    console.log("✅ WebGPU available - Local AI enabled");
    console.log(`   Max buffer: ${gpuInfo.maxBufferSize / 1e9}GB`);
} else if (gpuInfo.webgl2) {
    console.log("⚠️  WebGL2 available - Limited acceleration");
} else {
    console.log("❌ No GPU acceleration - CPU only");
}
```

---

## 8. Memory Management

### 8.1 GPU Memory Allocation Strategy

**Challenge**: Browsers limit GPU memory access (typically 2-4GB)

**Solution**:
1. **Streaming Layers**: Process transformer layers sequentially, not all at once
2. **Weight Offloading**: Keep inactive layer weights in CPU RAM, swap to GPU on-demand
3. **KV Cache Management**: Limit context window, prune old tokens
4. **Quantization**: Use 4-bit weights (75% size reduction)

```rust
pub struct LayeredModelExecutor {
    context: WebGPUContext,
    buffer_manager: BufferManager,
    layer_weights: Vec<Vec<u8>>,  // CPU storage
    active_layer: Option<usize>,
}

impl LayeredModelExecutor {
    /// Load layer weights to GPU on-demand
    async fn activate_layer(&mut self, layer_idx: usize) -> Result<(), JsValue> {
        // Unload previous layer
        if let Some(prev) = self.active_layer {
            self.buffer_manager.get_buffer("layer_weights")?.destroy();
        }

        // Load new layer
        let weights = &self.layer_weights[layer_idx];
        self.buffer_manager.create_storage_buffer("layer_weights", weights.len() as u64)?;
        self.buffer_manager.write_buffer("layer_weights", weights)?;

        self.active_layer = Some(layer_idx);
        Ok(())
    }
}
```

### 8.2 Memory Leak Prevention

**Strategies**:
1. **RAII**: Rust's Drop trait ensures cleanup
2. **Buffer tracking**: Track all allocations in BufferManager
3. **Automatic cleanup**: Call buffer.destroy() in Drop
4. **Leak detection**: Unit tests with memory profiling

```rust
impl Drop for BufferManager {
    fn drop(&mut self) {
        // Destroy all buffers automatically
        for buffer in self.buffers.values() {
            buffer.destroy();
        }
        log::info!("Cleaned up {} buffers", self.buffers.len());
    }
}
```

### 8.3 Memory Limits

**Recommended Model Sizes**:
- 8GB VRAM: Up to 7B params (4-bit)
- 4GB VRAM: Up to 3B params (4-bit)
- 2GB VRAM: Up to 1B params (4-bit) or embeddings only

**Runtime Checks**:
```rust
pub async fn check_memory_requirements(model: &ModelMetadata) -> Result<(), JsValue> {
    let adapter = navigator.gpu().request_adapter().await?;
    let max_buffer = adapter.limits().max_buffer_size();

    if model.total_size_bytes > max_buffer {
        return Err(format!(
            "Model too large: {}GB required, {}GB available",
            model.total_size_bytes / 1e9,
            max_buffer / 1e9
        ).into());
    }

    Ok(())
}
```

---

## 9. Security Considerations

### 9.1 Shader Injection Attacks

**Risk**: Malicious shader code could crash GPU or read memory

**Mitigation**:
1. **No user-provided shaders**: All shaders embedded in WASM at compile time
2. **Static shader library**: Pre-compiled, audited shaders only
3. **No eval()**: No dynamic shader compilation from user input
4. **Browser sandboxing**: WebGPU runs in browser sandbox

```rust
// All shaders embedded at compile time
const ATTENTION_SHADER: &str = include_str!("../shaders/attention.wgsl");
const FEEDFORWARD_SHADER: &str = include_str!("../shaders/feedforward.wgsl");

// No runtime shader compilation from user input
pub fn compile_shader(source: &str) -> Result<(), JsValue> {
    // ❌ NEVER do this with user input
    // let module = device.create_shader_module(source);

    // ✅ Only use pre-defined shaders
    match source {
        "attention" => device.create_shader_module(ATTENTION_SHADER),
        "feedforward" => device.create_shader_module(FEEDFORWARD_SHADER),
        _ => return Err("Unknown shader".into()),
    }
}
```

### 9.2 Buffer Overflow Prevention

**Risk**: Out-of-bounds buffer access could read other data

**Mitigation**:
1. **Bounds checking**: All buffer accesses bounds-checked in shaders
2. **WebGPU validation**: Browser validates all GPU operations
3. **Rust type safety**: No pointer arithmetic, bounds-checked indexing
4. **Buffer size limits**: Enforce maximum buffer sizes

```rust
// Bounds-checked buffer write
pub fn write_buffer_checked(&self, name: &str, data: &[u8], offset: u64) -> Result<(), JsValue> {
    let size = self.buffer_sizes.get(name)
        .ok_or("Buffer not found")?;

    if offset + data.len() as u64 > *size {
        return Err("Buffer overflow detected".into());
    }

    let buffer = self.buffers.get(name).ok_or("Buffer not found")?;
    self.context.queue().write_buffer_with_u8_array(buffer, offset, data);

    Ok(())
}
```

### 9.3 Model Tampering

**Risk**: Malicious model weights could produce harmful outputs

**Mitigation**:
1. **HTTPS only**: Models fetched over TLS
2. **Checksum verification**: Verify SHA-256 hash of model files
3. **Signed models**: Support GPG-signed model files (future)
4. **Trusted sources**: Only load models from known CDNs

```rust
pub async fn load_model_verified(url: &str, expected_sha256: &str) -> Result<Vec<u8>, JsValue> {
    // Fetch model
    let data = fetch(url).await?;

    // Compute SHA-256
    let hash = sha256(&data);

    // Verify
    if hash != expected_sha256 {
        return Err("Model checksum mismatch - possible tampering".into());
    }

    Ok(data)
}
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Scope**: Individual components in isolation

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[wasm_bindgen_test]
    async fn test_buffer_manager_allocation() {
        let context = WebGPUContext::new().await.unwrap().unwrap();
        let mut manager = BufferManager::new(context);

        // Create buffer
        manager.create_storage_buffer("test", 1024).unwrap();

        // Verify buffer exists
        assert!(manager.get_buffer("test").is_some());

        // Write data
        let data = vec![1u8; 1024];
        manager.write_buffer("test", &data).unwrap();

        // Cleanup
        manager.cleanup();
        assert!(manager.get_buffer("test").is_none());
    }

    #[wasm_bindgen_test]
    async fn test_shader_compilation() {
        let context = WebGPUContext::new().await.unwrap().unwrap();
        let mut manager = ShaderManager::new(context);

        // Compile simple shader
        let shader = r#"
            @compute @workgroup_size(64)
            fn main(@builtin(global_invocation_id) id: vec3<u32>) {
                // Simple compute shader
            }
        "#;

        manager.compile_shader("test", shader).unwrap();
        manager.create_pipeline("test_pipeline", "test", "main").unwrap();

        assert!(manager.get_pipeline("test_pipeline").is_some());
    }
}
```

### 10.2 Integration Tests

**Scope**: End-to-end workflows

```rust
#[wasm_bindgen_test]
async fn test_embedding_generation_e2e() {
    // Skip if WebGPU unavailable
    if WebGPUContext::new().await.unwrap().is_none() {
        return;
    }

    // Create adapter
    let adapter = WebGPUEmbeddingAdapter::new("minilm-l6-v2").await.unwrap();

    // Generate embedding
    let embedding = adapter.embed("Hello, world!").await.unwrap();

    // Verify dimensions
    assert_eq!(embedding.len(), 384);

    // Verify normalization (should be unit vector)
    let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
    assert!((norm - 1.0).abs() < 0.01);
}
```

### 10.3 Performance Benchmarks

**Scope**: Measure performance targets

```rust
#[wasm_bindgen_test]
async fn bench_embedding_throughput() {
    let adapter = WebGPUEmbeddingAdapter::new("minilm-l6-v2").await.unwrap();

    let texts: Vec<String> = (0..100).map(|i| format!("Test text {}", i)).collect();

    let start = now();
    let embeddings = adapter.embed_batch(texts).await.unwrap();
    let elapsed = now() - start;

    let throughput = 100.0 / elapsed;

    // Should achieve 100+ embeddings/sec
    assert!(throughput > 100.0, "Throughput: {} emb/sec", throughput);
}
```

### 10.4 Browser Testing Matrix

**Automation**: Playwright for cross-browser testing

```javascript
// playwright.config.js
module.exports = {
    projects: [
        { name: 'chrome', use: { browserName: 'chromium' } },
        { name: 'edge', use: { browserName: 'chromium', channel: 'msedge' } },
        { name: 'safari', use: { browserName: 'webkit' } },
    ],
};

// tests/webgpu.spec.js
test('WebGPU embedding generation', async ({ page }) => {
    await page.goto('http://localhost:8080/test.html');

    // Wait for WASM initialization
    await page.waitForFunction(() => window.agenkitReady === true);

    // Run embedding generation
    const result = await page.evaluate(async () => {
        const adapter = await WebGPUEmbeddingAdapter.new('minilm-l6-v2');
        const embedding = await adapter.embed('Test');
        return embedding.length;
    });

    expect(result).toBe(384);
});
```

---

## 11. Documentation Requirements

### 11.1 Getting Started Guide (`WEBGPU.md`)

**Content**:
- Introduction to WebGPU + Agenkit
- Browser compatibility check
- Installation instructions
- Basic example (embedding generation)
- API reference
- Troubleshooting guide

### 11.2 Model Guide (`MODELS.md`)

**Content**:
- Supported models (LLMs, embeddings, vision)
- Model formats (quantization, architecture)
- Where to download models
- How to verify model checksums
- Custom model loading

### 11.3 Performance Guide (`WEBGPU_PERFORMANCE.md`)

**Content**:
- Benchmarks (CPU vs GPU)
- Memory requirements by model size
- Optimization tips
- Profiling tools
- Common performance issues

### 11.4 API Documentation

**Generated from Rust doc comments**:
```rust
/// GPU-accelerated LLM adapter for browser inference
///
/// # Example
/// ```javascript
/// const agent = await WebGPULLMAdapter.new("llama3.2-1b-q4");
/// const response = await agent.process(new JsMessage("user", "Hello!"));
/// ```
///
/// # Performance
/// - First token: <2s
/// - Generation speed: 20-50 tokens/sec
/// - Memory: <2GB VRAM
#[wasm_bindgen]
pub struct WebGPULLMAdapter { /* ... */ }
```

---

## 12. Open Questions

### Q1: Should we support WebGL compute as fallback?

**Context**: WebGL2 has compute shaders via extensions, wider browser support than WebGPU

**Options**:
- A) WebGPU only (simpler, better performance)
- B) WebGL compute fallback (wider compatibility, 2x implementation cost)

**Recommendation**: Start WebGPU-only (Phase 1-4), add WebGL in v0.44.0 if demand exists

---

### Q2: How to handle model versioning and updates?

**Context**: Models improve over time, users should get updates

**Options**:
- A) Manual version pins (users specify exact model version)
- B) Automatic updates (fetch latest compatible version)
- C) Hybrid (auto-update minor versions, pin major versions)

**Recommendation**: Option C - Auto-update patches, user controls major versions

---

### Q3: Should we support streaming inference?

**Context**: LLMs can stream tokens as they're generated

**Options**:
- A) Batch only (simpler, lower latency overall)
- B) Streaming (better UX, more complex)

**Recommendation**: Phase 3 includes streaming (via async iterators)

```javascript
const agent = await WebGPULLMAdapter.new("llama3.2-1b-q4");

// Streaming generation
for await (const token of agent.processStream(message)) {
    console.log(token); // Display incrementally
}
```

---

### Q4: How to handle multi-GPU systems?

**Context**: Some systems have integrated + discrete GPUs

**Options**:
- A) Use default GPU (simple)
- B) Let user choose GPU (more control)
- C) Automatically select discrete GPU (best performance)

**Recommendation**: Option C with Option B as fallback

---

## Appendix A: WGSL Shader Examples

### A.1 Matrix Multiplication

```wgsl
// Simple matrix multiply kernel
@group(0) @binding(0) var<storage, read> a: array<f32>;
@group(0) @binding(1) var<storage, read> b: array<f32>;
@group(0) @binding(2) var<storage, read_write> result: array<f32>;

@compute @workgroup_size(16, 16)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let row = global_id.x;
    let col = global_id.y;

    var sum = 0.0;
    for (var k = 0u; k < 512u; k = k + 1u) {
        sum = sum + a[row * 512u + k] * b[k * 512u + col];
    }

    result[row * 512u + col] = sum;
}
```

### A.2 Self-Attention (Simplified)

```wgsl
// Simplified self-attention kernel
@group(0) @binding(0) var<storage, read> queries: array<f32>;
@group(0) @binding(1) var<storage, read> keys: array<f32>;
@group(0) @binding(2) var<storage, read> values: array<f32>;
@group(0) @binding(3) var<storage, read_write> output: array<f32>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) global_id: vec3<u32>) {
    let seq_idx = global_id.x;
    let dim = 512u;

    // Compute attention scores
    var max_score = -3.4028235e38; // -inf
    for (var i = 0u; i <= seq_idx; i = i + 1u) {
        var score = 0.0;
        for (var d = 0u; d < dim; d = d + 1u) {
            score = score + queries[seq_idx * dim + d] * keys[i * dim + d];
        }
        max_score = max(max_score, score);
    }

    // Softmax and weighted sum
    var sum_exp = 0.0;
    for (var i = 0u; i <= seq_idx; i = i + 1u) {
        var score = 0.0;
        for (var d = 0u; d < dim; d = d + 1u) {
            score = score + queries[seq_idx * dim + d] * keys[i * dim + d];
        }
        sum_exp = sum_exp + exp(score - max_score);
    }

    for (var d = 0u; d < dim; d = d + 1u) {
        var weighted_sum = 0.0;
        for (var i = 0u; i <= seq_idx; i = i + 1u) {
            var score = 0.0;
            for (var dd = 0u; dd < dim; dd = dd + 1u) {
                score = score + queries[seq_idx * dim + dd] * keys[i * dim + dd];
            }
            let attention_weight = exp(score - max_score) / sum_exp;
            weighted_sum = weighted_sum + attention_weight * values[i * dim + d];
        }
        output[seq_idx * dim + d] = weighted_sum;
    }
}
```

---

## Appendix B: Performance Estimation

### B.1 Llama 3.2 1B (4-bit Quantized)

**Model Size**: ~1.5GB (4-bit weights + metadata)

**Memory Breakdown**:
- Weights: 1.2GB (4-bit quantized)
- Activations: 200MB (per batch)
- KV Cache: 100MB (context window: 2048 tokens)
- Total: ~1.5GB VRAM

**Compute Estimation**:
- FLOPs per token: ~2 billion (1B params × 2 ops)
- GPU throughput: 5 TFLOPS (typical integrated GPU)
- Theoretical max: 2500 tokens/sec
- Actual (with overhead): 20-50 tokens/sec

**Bottlenecks**:
1. Memory bandwidth (reading weights)
2. Kernel launch overhead
3. KV cache management

---

## Appendix C: Related Work

### C.1 Existing Solutions

| Project | Tech Stack | Strengths | Weaknesses |
|---------|------------|-----------|------------|
| Transformers.js | ONNX Runtime Web (WebGL) | Easy to use | CPU-only, slow |
| WebLLM (MLC) | WebGPU | Fast inference | Not an agent framework |
| llama.cpp WASM | C++ → WASM | Portable | CPU-only, no GPU |
| ONNX Runtime Web | WebGL/WebGPU | Good model support | Limited to ONNX format |

### C.2 Agenkit Differentiation

**Unique Features**:
- First **agent framework** with WebGPU
- Pattern library (orchestration, reflection, ReAct, etc.)
- Multi-language (unified API across Python, Go, TypeScript, Rust, C++)
- Automatic fallback (WebGPU → API-based)
- Privacy-first (local inference by default)

---

**Document Status**: Draft for Review
**Next Steps**:
1. Review and refine design with stakeholders
2. Create GitHub issue (#225)
3. Begin Phase 1 implementation spike
4. Validate performance assumptions with prototype
