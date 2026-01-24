# OpenAI-Compatible Inference Services Guide

**Complete setup and deployment guide for self-hosted LLM inference with Agenkit**

This guide covers setup, configuration, and deployment of OpenAI-compatible inference services with Agenkit's `OpenAICompatibleLLM` adapter.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Service Comparison](#service-comparison)
4. [Setup Guides](#setup-guides)
   - [vLLM](#vllm)
   - [llama.cpp](#llamacpp)
   - [SGLang](#sglang)
   - [TensorRT-LLM](#tensorrt-llm)
   - [OpenLLM](#openllm)
   - [MLC LLM](#mlc-llm)
   - [Text Generation Inference (TGI)](#text-generation-inference-tgi)
   - [Inferflow](#inferflow)
   - [LM Studio](#lm-studio)
5. [Model Selection](#model-selection)
6. [Performance Tuning](#performance-tuning)
7. [Migration Guide](#migration-guide)
8. [Troubleshooting](#troubleshooting)
9. [Production Deployment](#production-deployment)
10. [Monitoring & Observability](#monitoring--observability)

---

## Overview

### What is an OpenAI-Compatible Service?

An OpenAI-compatible service implements the OpenAI Chat Completions API, allowing you to:
- Use the same code across different inference engines
- Easily migrate from OpenAI to self-hosted
- Avoid vendor lock-in
- Run models locally for privacy and cost savings

### Supported Services

Agenkit's `OpenAICompatibleLLM` adapter works with **9+ inference services**:

| Service | Type | Best For | Deployment |
|---------|------|----------|------------|
| vLLM | Production | High throughput | GPU (NVIDIA) |
| llama.cpp | Edge/Local | CPU-friendly | CPU/GPU |
| SGLang | Conversational | Multi-turn chat | GPU (NVIDIA) |
| TensorRT-LLM | Enterprise | Lowest latency | GPU (NVIDIA A100/H100) |
| OpenLLM | Platform | Multi-model serving | CPU/GPU |
| MLC LLM | Mobile/Edge | Browser/mobile | CPU/GPU/WebGPU |
| TGI | Cloud | HuggingFace integration | CPU/GPU |
| Inferflow | Performance | High-throughput | GPU |
| LM Studio | Desktop | Local development | CPU/GPU (Mac/Windows/Linux) |

### Why Use Self-Hosted Inference?

**Benefits:**
- ✅ **Cost savings**: No per-token charges
- ✅ **Privacy**: Data never leaves your infrastructure
- ✅ **Customization**: Fine-tune models for your use case
- ✅ **Offline operation**: No internet dependency
- ✅ **Compliance**: Meet data residency requirements
- ✅ **Vendor independence**: Avoid lock-in

**Trade-offs:**
- ⚠️ **Infrastructure costs**: GPU/server expenses
- ⚠️ **Maintenance**: Managing deployments and updates
- ⚠️ **Expertise required**: Technical knowledge needed
- ⚠️ **Model quality**: May differ from GPT-4/Claude

---

## Quick Start

### Basic Usage

```python
from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message

# Connect to any OpenAI-compatible service
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",  # Service endpoint
    model="meta-llama/Llama-3.3-8B-Instruct",  # Model name
    provider="vllm"  # Optional: for metadata
)

# Use like any other LLM
messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
print(response.content)
```

### Decision Tree: Which Service to Use?

```
┌─────────────────────────────────────┐
│ What's your priority?               │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
   GPU available?   CPU only
       │                │
       ├─ Yes           └─→ llama.cpp (edge/local)
       │
       ├─ Production serving? ──→ vLLM (high throughput)
       │
       ├─ Chatbot/multi-turn? ──→ SGLang (RadixAttention)
       │
       ├─ Enterprise/A100/H100? ──→ TensorRT-LLM (lowest latency)
       │
       ├─ Desktop development? ──→ LM Studio (GUI)
       │
       └─ HuggingFace models? ──→ TGI (tight integration)
```

---

## Service Comparison

### Detailed Comparison Table

| Feature | vLLM | llama.cpp | SGLang | TensorRT-LLM | OpenLLM | MLC LLM | TGI | Inferflow |
|---------|------|-----------|--------|--------------|---------|---------|-----|-----------|
| **GPU Required** | Yes (NVIDIA) | No | Yes (NVIDIA) | Yes (A100/H100) | Optional | Optional | Optional | Yes |
| **CPU Support** | No | ✅ Excellent | No | No | ✅ Good | ✅ Good | ✅ Good | Limited |
| **Memory (8B)** | ~16GB VRAM | ~4-8GB RAM | ~16GB VRAM | ~16GB VRAM | ~16GB | ~8GB | ~16GB | ~16GB |
| **Setup Difficulty** | Easy | Easy | Medium | Hard | Medium | Medium | Easy | Medium |
| **Throughput** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Latency** | Very Low | Medium | Low | Lowest | Medium | Low | Low | Very Low |
| **Quantization** | FP16, INT8 | All formats | FP16, INT8 | FP16, INT8, FP8, INT4 | FP16, INT8 | INT4, INT8 | FP16, INT8 | FP16, INT8 |
| **Multi-GPU** | ✅ Yes | Limited | ✅ Yes | ✅ Yes | ✅ Yes | Limited | ✅ Yes | ✅ Yes |
| **Streaming** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Batching** | ✅ Auto | Limited | ✅ Auto | ✅ Auto | ✅ Auto | Limited | ✅ Auto | ✅ Auto |
| **Best Use Case** | Production API | Edge/CPU | Chatbots | Enterprise | Multi-model | Browser/Mobile | HuggingFace | Research |
| **License** | Apache 2.0 | MIT | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **Default Port** | 8000 | 8080 | 30000 | 8001 | 3000 | 8080 | 8080 | 8080 |

### When to Use Each Service

**vLLM** - Production serving with high concurrency
- ✅ Serving 100+ users simultaneously
- ✅ High request volume (>50 req/sec)
- ✅ Need PagedAttention efficiency
- ✅ Standard production deployment
- ❌ CPU-only environments
- ❌ Edge devices with limited resources

**llama.cpp** - Local, edge, and CPU inference
- ✅ CPU-only environments
- ✅ Edge devices (Raspberry Pi, IoT)
- ✅ Offline/air-gapped deployments
- ✅ Low resource environments
- ✅ Desktop development
- ❌ High-throughput production APIs
- ❌ Multiple concurrent users

**SGLang** - Conversational AI and chatbots
- ✅ Multi-turn conversations
- ✅ Chatbots with persistent system prompts
- ✅ RAG applications with repeated context
- ✅ Complex structured generation
- ❌ One-off queries
- ❌ CPU-only environments

**TensorRT-LLM** - Enterprise with A100/H100 GPUs
- ✅ Lowest possible latency required (<100ms)
- ✅ A100 or H100 datacenter GPUs available
- ✅ Maximum throughput needed
- ✅ Multi-GPU deployments
- ✅ Production at scale
- ❌ Consumer GPUs (3090, 4090)
- ❌ Development/testing
- ❌ CPU environments

**OpenLLM** - Multi-model platform
- ✅ Need to serve multiple models
- ✅ BentoML deployment pipeline
- ✅ Model versioning and A/B testing
- ✅ REST and gRPC APIs
- ❌ Single model deployments
- ❌ Simplicity preferred

**MLC LLM** - Browser and mobile deployment
- ✅ In-browser inference (WebGPU)
- ✅ Mobile apps (iOS/Android)
- ✅ Edge devices
- ✅ Offline mobile apps
- ❌ Server-side deployment
- ❌ High throughput needed

**TGI** - HuggingFace ecosystem
- ✅ Using HuggingFace models
- ✅ Need tight HF integration
- ✅ Cloud deployment (AWS/GCP/Azure)
- ✅ Standard production setup
- ❌ Non-HF model formats
- ❌ Highly specialized optimizations

**Inferflow** - Research and experimentation
- ✅ Research projects
- ✅ Performance benchmarking
- ✅ Custom optimizations
- ❌ Production deployments
- ❌ Limited documentation

**LM Studio** - Desktop development
- ✅ Local development and testing
- ✅ GUI for model management
- ✅ Mac, Windows, Linux support
- ✅ Quick experimentation
- ❌ Server deployments
- ❌ Programmatic control

---

## Setup Guides

### vLLM

**Best for:** Production serving with high throughput

#### Overview
vLLM is a high-throughput and memory-efficient inference engine featuring:
- PagedAttention for efficient memory management
- Continuous batching for high throughput
- Optimized CUDA kernels
- Easy deployment with Docker

#### Requirements
- NVIDIA GPU with CUDA support
- ~16GB VRAM for Llama-3.3-8B
- ~40GB VRAM for Llama-3.3-70B (or use tensor parallelism)
- Python 3.8+

#### Installation

**Option 1: Docker (Recommended)**

```bash
# Pull and run vLLM container
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-3.3-8B-Instruct \
    --dtype float16 \
    --max-model-len 8192

# With custom settings
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-3.3-8B-Instruct \
    --dtype float16 \
    --tensor-parallel-size 2 \
    --max-model-len 8192 \
    --max-num-seqs 256
```

**Option 2: Python Installation**

```bash
# Install vLLM
pip install vllm

# Start server
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.3-8B-Instruct \
    --dtype float16 \
    --port 8000
```

#### Configuration

**Key Parameters:**

```bash
--model MODEL               # HuggingFace model ID
--dtype {auto,float16,bfloat16}  # Data type
--tensor-parallel-size N    # Number of GPUs for model parallelism
--max-model-len N          # Maximum sequence length
--max-num-seqs N           # Maximum batch size
--gpu-memory-utilization F # GPU memory usage (0-1, default 0.9)
--trust-remote-code        # Allow custom model code
```

**Performance Tuning:**

```bash
# For maximum throughput
--max-num-seqs 256 \
--max-model-len 4096 \
--gpu-memory-utilization 0.95

# For lower latency
--max-num-seqs 64 \
--max-model-len 2048 \
--gpu-memory-utilization 0.85
```

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="vllm",
    timeout=60.0
)

# Use with Agenkit
messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages, temperature=0.7, max_tokens=1000)
```

#### Health Check

```bash
# Check server health
curl http://localhost:8000/health

# Check model info
curl http://localhost:8000/v1/models

# Test inference
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.3-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

#### Multi-GPU Setup

```bash
# Tensor parallelism (split model across GPUs)
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-3.3-70B-Instruct \
    --tensor-parallel-size 4  # Use 4 GPUs

# Pipeline parallelism (layer distribution)
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-3.3-70B-Instruct \
    --pipeline-parallel-size 2
```

#### Common Issues

**Out of Memory:**
```bash
# Reduce memory usage
--gpu-memory-utilization 0.8 \
--max-model-len 4096 \
--max-num-seqs 128
```

**Slow Startup:**
- Large models take 1-5 minutes to load
- Check logs: `docker logs <container-id>`

#### Resources
- Documentation: https://docs.vllm.ai/
- GitHub: https://github.com/vllm-project/vllm
- OpenAI API: https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html

---

### llama.cpp

**Best for:** Local, edge, and CPU inference

#### Overview
llama.cpp is a lightweight C++ implementation designed for:
- CPU-only inference
- Quantized models (2-bit to 16-bit)
- Low memory footprint
- Cross-platform support (Mac, Linux, Windows)
- Optional GPU acceleration

#### Requirements
- CPU with AVX2 support (most modern CPUs)
- 4-8GB RAM for Q4 quantized 8B models
- Optional: NVIDIA GPU for acceleration
- Optional: Apple Silicon for Metal acceleration

#### Installation

**Option 1: Build from Source (Recommended)**

```bash
# Clone repository
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Build with CPU support
make server

# Build with CUDA support (NVIDIA GPU)
make server LLAMA_CUDA=1

# Build with Metal support (Apple Silicon)
make server LLAMA_METAL=1

# Build with OpenCL support (AMD GPU)
make server LLAMA_CLBLAST=1
```

**Option 2: Docker**

```bash
# Pull and run
docker pull ghcr.io/ggerganov/llama.cpp:server

# Run with model
docker run -p 8080:8080 \
    -v /path/to/models:/models \
    ghcr.io/ggerganov/llama.cpp:server \
    --model /models/llama-3.3-8b-instruct.Q4_K_M.gguf \
    --port 8080 \
    --host 0.0.0.0
```

#### Model Download

Models must be in GGUF format. Download from HuggingFace:

```bash
# Create models directory
mkdir -p models

# Download quantized model
wget https://huggingface.co/TheBloke/Llama-3.3-8B-Instruct-GGUF/resolve/main/llama-3.3-8b-instruct.Q4_K_M.gguf \
    -P models/

# Or use huggingface-cli
pip install huggingface-hub
huggingface-cli download TheBloke/Llama-3.3-8B-Instruct-GGUF \
    llama-3.3-8b-instruct.Q4_K_M.gguf \
    --local-dir models/
```

**Quantization Options:**

| Quantization | Size (8B) | Quality | Speed | Use Case |
|--------------|-----------|---------|-------|----------|
| Q2_K | ~2.5GB | ⭐⭐ | Very Fast | Testing only |
| Q3_K_M | ~3.2GB | ⭐⭐⭐ | Fast | Resource-constrained |
| Q4_K_M | ~4.1GB | ⭐⭐⭐⭐ | Fast | **Recommended** |
| Q5_K_M | ~5.0GB | ⭐⭐⭐⭐ | Medium | Good quality |
| Q6_K | ~6.1GB | ⭐⭐⭐⭐⭐ | Medium | High quality |
| Q8_0 | ~7.2GB | ⭐⭐⭐⭐⭐ | Slower | Best quality |
| F16 | ~14GB | ⭐⭐⭐⭐⭐ | Slow | Reference quality |

#### Starting the Server

**Basic CPU-only:**

```bash
./server \
    --model models/llama-3.3-8b-instruct.Q4_K_M.gguf \
    --port 8080 \
    --host 0.0.0.0 \
    --ctx-size 4096 \
    --threads 8
```

**With GPU acceleration (NVIDIA):**

```bash
./server \
    --model models/llama-3.3-8b-instruct.Q4_K_M.gguf \
    --port 8080 \
    --n-gpu-layers 35 \  # Offload layers to GPU
    --ctx-size 4096
```

**With Apple Silicon (Metal):**

```bash
./server \
    --model models/llama-3.3-8b-instruct.Q4_K_M.gguf \
    --port 8080 \
    --n-gpu-layers 35 \
    --ctx-size 4096 \
    --metal
```

#### Configuration

**Key Parameters:**

```bash
--model PATH              # Model file path
--port N                  # Server port (default: 8080)
--host IP                 # Host IP (default: 127.0.0.1)
--threads N               # CPU threads (default: all)
--ctx-size N              # Context window size (default: 2048)
--n-gpu-layers N          # GPU offload layers (0 = CPU only)
--batch-size N            # Batch size (default: 512)
--mlock                   # Lock model in RAM (prevent swapping)
--no-mmap                 # Don't use memory mapping
```

**Performance Tuning:**

```bash
# Maximum performance (CPU)
./server \
    --model models/model.gguf \
    --threads $(nproc) \
    --ctx-size 4096 \
    --batch-size 512 \
    --mlock

# Balanced (CPU + GPU)
./server \
    --model models/model.gguf \
    --threads 8 \
    --n-gpu-layers 25 \  # Adjust based on VRAM
    --ctx-size 4096

# Low memory
./server \
    --model models/model.Q4_K_M.gguf \
    --threads 4 \
    --ctx-size 2048 \
    --batch-size 256
```

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:8080/v1",
    model="llama-3.3-8b-instruct",
    provider="llamacpp",
    timeout=60.0
)

# Use with Agenkit
messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
```

#### Health Check

```bash
# Check server
curl http://localhost:8080/health

# Test completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.3-8b-instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

#### Platform-Specific Tips

**macOS (Apple Silicon):**
```bash
# Build with Metal
make server LLAMA_METAL=1

# Run with GPU acceleration
./server --model model.gguf --n-gpu-layers 35 --metal
```

**Linux (CPU only):**
```bash
# Optimize for CPU
./server --model model.gguf --threads $(nproc) --mlock

# Run as systemd service
sudo cp llama-server.service /etc/systemd/system/
sudo systemctl enable llama-server
sudo systemctl start llama-server
```

**Windows:**
```powershell
# Build with CMake
cmake -B build -DLLAMA_CUDA=ON
cmake --build build --config Release

# Run server
.\build\bin\Release\server.exe --model model.gguf
```

#### Edge Deployment

**Raspberry Pi 4/5:**
```bash
# Use Q4_K_M quantization, smaller models
./server \
    --model models/llama-3.3-1b-instruct.Q4_K_M.gguf \
    --threads 4 \
    --ctx-size 2048 \
    --batch-size 256
```

**Offline/Air-Gapped:**
1. Download model files on internet-connected machine
2. Copy llama.cpp binary and model to target
3. Run server - no internet required!

#### Resources
- GitHub: https://github.com/ggerganov/llama.cpp
- Server Docs: https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md
- Model Hub: https://huggingface.co/models?library=gguf

---

### SGLang

**Best for:** Multi-turn conversations and chatbots

#### Overview
SGLang (Structured Generation Language) features:
- RadixAttention for automatic KV cache reuse
- 2-10x speedup for similar prompts
- Optimized for conversational AI
- Structured generation support

#### Requirements
- NVIDIA GPU with CUDA support
- ~16GB VRAM for Llama-3.3-8B
- ~140GB VRAM for Llama-3.3-70B (or tensor parallelism)
- Python 3.8+

#### Installation

**Option 1: Docker (Recommended)**

```bash
# Run SGLang with Docker
docker run --gpus all -p 30000:30000 \
    lmsysorg/sglang:latest \
    python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.3-70B-Instruct \
    --port 30000 \
    --host 0.0.0.0
```

**Option 2: Python Installation**

```bash
# Install SGLang
pip install "sglang[all]"

# Install FlashInfer for better performance (optional)
pip install flashinfer -i https://flashinfer.ai/whl/cu121/torch2.4/

# Start server
python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.3-70B-Instruct \
    --port 30000
```

#### Configuration

**Key Parameters:**

```bash
--model-path MODEL         # HuggingFace model ID or local path
--port N                   # Server port (default: 30000)
--host IP                  # Host IP
--tp-size N                # Tensor parallelism size
--mem-fraction-static F    # Static KV cache memory fraction
--max-total-tokens N       # Maximum context length
--trust-remote-code        # Allow custom model code
```

**For Chatbots (Optimized for RadixAttention):**

```bash
python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.3-70B-Instruct \
    --port 30000 \
    --tp-size 4 \
    --mem-fraction-static 0.85 \
    --max-total-tokens 8192
```

**For High Throughput:**

```bash
python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.3-8B-Instruct \
    --port 30000 \
    --tp-size 1 \
    --mem-fraction-static 0.9 \
    --max-total-tokens 4096 \
    --context-length 4096
```

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:30000/v1",
    model="meta-llama/Llama-3.3-70B-Instruct",
    provider="sglang",
    timeout=120.0
)

# Chatbot with RadixAttention benefits
system_prompt = "You are a helpful AI assistant..."
messages = [
    Message(role="system", content=system_prompt),
    Message(role="user", content="Hello!")
]

# First request builds cache
response1 = await llm.complete(messages)

# Subsequent requests reuse cached system prompt (faster!)
messages.append(response1)
messages.append(Message(role="user", content="Tell me more"))
response2 = await llm.complete(messages)  # 2-10x faster
```

#### RadixAttention Explained

RadixAttention automatically:
1. **Caches common prefixes**: System prompts cached once
2. **Reuses KV states**: Similar prompts share cached states
3. **Speeds up inference**: 2-10x faster for repeated content
4. **Works automatically**: Zero configuration needed

**Benefits for Chatbots:**
- Same system prompt → Cached after first use
- Multi-turn conversations → Previous turns cached
- RAG with fixed context → Context cached and reused

#### Health Check

```bash
# Check server
curl http://localhost:30000/health

# Get server info
curl http://localhost:30000/get_server_info

# Test completion
curl http://localhost:30000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.3-70B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

#### Multi-GPU Setup

```bash
# Tensor parallelism across 4 GPUs
python -m sglang.launch_server \
    --model-path meta-llama/Llama-3.3-70B-Instruct \
    --tp-size 4 \
    --port 30000
```

#### Monitoring Cache Performance

```bash
# Get cache statistics
curl http://localhost:30000/get_server_info | jq '.cache_info'
```

Look for:
- `cache_hit_rate`: Should be >50% for chatbots
- `cached_tokens`: Number of reused tokens
- `total_tokens`: Total processed tokens

#### Resources
- GitHub: https://github.com/sgl-project/sglang
- Documentation: https://sgl-project.github.io/
- RadixAttention Paper: https://arxiv.org/abs/2312.07104

---

### TensorRT-LLM

**Best for:** Enterprise GPU deployments (A100/H100)

#### Overview
TensorRT-LLM by NVIDIA provides:
- Lowest latency inference (<100ms P95)
- Maximum throughput on NVIDIA GPUs
- Advanced quantization (FP8, INT8, INT4)
- Multi-GPU tensor parallelism
- Production-grade performance

#### Requirements
- NVIDIA A100, A100, or H100 GPUs
- CUDA 12.0+
- TensorRT 9.0+
- Docker with NVIDIA Container Runtime
- ~140GB VRAM for Llama-70B FP16 (or less with quantization)

#### Installation

**Prerequisites:**

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

**Pull TensorRT-LLM Container:**

```bash
# Pull latest container
docker pull nvcr.io/nvidia/tritonserver:24.01-trtllm-python-py3
```

#### Building Optimized Engines

TensorRT-LLM requires a one-time engine build process:

**Step 1: Clone Repository**

```bash
git clone https://github.com/NVIDIA/TensorRT-LLM.git
cd TensorRT-LLM
```

**Step 2: Build Engine (FP16)**

```bash
# Build for single GPU
python examples/llama/build.py \
    --model_dir meta-llama/Llama-3.3-70B-Instruct \
    --output_dir ./engines/llama-70b-fp16 \
    --dtype float16 \
    --use_gpt_attention_plugin float16 \
    --use_gemm_plugin float16 \
    --max_batch_size 128 \
    --max_input_len 2048 \
    --max_output_len 1024

# Build for multi-GPU (4x GPUs)
python examples/llama/build.py \
    --model_dir meta-llama/Llama-3.3-70B-Instruct \
    --output_dir ./engines/llama-70b-tp4 \
    --dtype float16 \
    --tp_size 4 \
    --use_gpt_attention_plugin float16 \
    --use_gemm_plugin float16
```

**Step 3: Build Engine (INT8 - Recommended for Production)**

```bash
python examples/llama/build.py \
    --model_dir meta-llama/Llama-3.3-70B-Instruct \
    --output_dir ./engines/llama-70b-int8 \
    --dtype float16 \
    --use_weight_only \
    --weight_only_precision int8 \
    --use_gpt_attention_plugin float16
```

**Step 4: Build Engine (FP8 - H100 only)**

```bash
python examples/llama/build.py \
    --model_dir meta-llama/Llama-3.3-70B-Instruct \
    --output_dir ./engines/llama-70b-fp8 \
    --dtype float16 \
    --use_fp8 \
    --use_gpt_attention_plugin float16
```

#### Starting the Server

```bash
# Start OpenAI-compatible server
python examples/server/launch_server.py \
    --engine_dir ./engines/llama-70b-int8 \
    --port 8001 \
    --host 0.0.0.0 \
    --max_batch_size 128
```

#### Configuration

**Quantization Options:**

| Format | Speed | Quality | VRAM (70B) | Use Case |
|--------|-------|---------|------------|----------|
| FP16 | 1x | ⭐⭐⭐⭐⭐ | ~140GB | Development/Reference |
| INT8 | 2x | ⭐⭐⭐⭐ | ~70GB | **Production (Recommended)** |
| FP8 | 1.5x | ⭐⭐⭐⭐⭐ | ~90GB | H100 Production |
| INT4 | 4x | ⭐⭐⭐ | ~35GB | High Throughput |

**Multi-GPU Configuration:**

```bash
# GPU Layout Recommendations
# Llama-7B-8B:    1 GPU
# Llama-13B:      1-2 GPUs (TP=2 recommended)
# Llama-70B:      4-8 GPUs (TP=4 or TP=8)
# Llama-405B:     8+ GPUs (TP=8, PP=2+)

# Build with tensor parallelism
python examples/llama/build.py \
    --model_dir MODEL \
    --tp_size 4 \  # Split across 4 GPUs
    --output_dir ./engines/model-tp4
```

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:8001/v1",
    model="llama-70b-instruct",
    provider="tensorrt",
    timeout=30.0  # Can be very fast!
)

# Use with Agenkit
messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
```

#### Performance Optimization

**For Lowest Latency (<100ms P95):**

```bash
# Use INT8, single GPU, small batch
python examples/llama/build.py \
    --weight_only_precision int8 \
    --max_batch_size 32 \
    --max_input_len 1024 \
    --max_output_len 512
```

**For Maximum Throughput:**

```bash
# Use INT8, multi-GPU, large batch
python examples/llama/build.py \
    --weight_only_precision int8 \
    --tp_size 4 \
    --max_batch_size 256 \
    --max_input_len 2048 \
    --max_output_len 1024
```

#### Monitoring

```bash
# GPU utilization
nvidia-smi -l 1

# Server metrics (if exposed)
curl http://localhost:8001/metrics
```

**Key Metrics:**
- GPU utilization: Should be >80% under load
- P95 latency: Target <100ms for production
- Throughput: Measure tokens/second
- Memory usage: Monitor VRAM usage

#### Production Deployment

**Docker Compose Example:**

```yaml
version: '3.8'
services:
  tensorrt-llm:
    image: nvcr.io/nvidia/tritonserver:24.01-trtllm-python-py3
    ports:
      - "8001:8001"
    volumes:
      - ./engines:/engines
    command: >
      python examples/server/launch_server.py
      --engine_dir /engines/llama-70b-int8
      --port 8001
      --max_batch_size 128
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 4
              capabilities: [gpu]
```

#### Troubleshooting

**Engine Build Fails:**
- Check CUDA version compatibility
- Ensure enough disk space (~200GB for 70B builds)
- Verify model files downloaded correctly

**OOM During Inference:**
- Reduce `max_batch_size`
- Use INT8 instead of FP16
- Increase `tp_size` (more GPUs)

**Slow Inference:**
- Check GPU utilization (`nvidia-smi`)
- Verify using correct quantization
- Ensure NVLink enabled for multi-GPU

#### Resources
- GitHub: https://github.com/NVIDIA/TensorRT-LLM
- Documentation: https://nvidia.github.io/TensorRT-LLM/
- Performance Guide: https://docs.nvidia.com/deeplearning/tensorrt/

---

### OpenLLM

**Best for:** Multi-model serving platform

#### Overview
OpenLLM by BentoML provides:
- Serve multiple models simultaneously
- REST and gRPC APIs
- Model versioning and A/B testing
- BentoML deployment pipeline
- Production monitoring

#### Requirements
- Python 3.8+
- Optional: GPU for acceleration
- Docker (recommended)

#### Installation

```bash
# Install OpenLLM
pip install openllm

# Or with specific backend
pip install "openllm[vllm]"  # Use vLLM backend
pip install "openllm[pt]"    # PyTorch backend
```

#### Starting a Model

```bash
# Start with default settings
openllm start meta-llama/Llama-3.3-8B-Instruct

# With custom port
openllm start meta-llama/Llama-3.3-8B-Instruct \
    --port 3000

# With GPU
openllm start meta-llama/Llama-3.3-8B-Instruct \
    --device cuda

# With vLLM backend (faster)
openllm start meta-llama/Llama-3.3-8B-Instruct \
    --backend vllm \
    --device cuda
```

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:3000/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="openllm"
)

messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
```

#### Multi-Model Serving

```bash
# Start multiple models
openllm start meta-llama/Llama-3.3-8B-Instruct --port 3000 &
openllm start meta-llama/Llama-3.3-70B-Instruct --port 3001 &

# Use different models in Agenkit
llm_fast = OpenAICompatibleLLM(base_url="http://localhost:3000/v1", ...)
llm_quality = OpenAICompatibleLLM(base_url="http://localhost:3001/v1", ...)
```

#### BentoML Deployment

```python
# bentofile.yaml
service: "llm_service.py:svc"
python:
  packages:
    - openllm
models:
  - meta-llama/Llama-3.3-8B-Instruct
docker:
  python_version: "3.10"
```

```bash
# Build Bento
bentoml build

# Deploy to cloud
bentoml containerize llm_service:latest
docker push your-registry/llm_service:latest
```

#### Resources
- GitHub: https://github.com/bentoml/OpenLLM
- Documentation: https://github.com/bentoml/OpenLLM#readme
- BentoML: https://docs.bentoml.com/

---

### MLC LLM

**Best for:** Browser and mobile deployment

#### Overview
MLC LLM enables:
- In-browser inference with WebGPU
- Mobile apps (iOS/Android)
- Edge device deployment
- Universal deployment (CPU/GPU/WebGPU)

#### Requirements
- Modern browser with WebGPU support (Chrome/Edge)
- Or iOS/Android device
- Or standard CPU/GPU for native apps

#### Web Deployment

```bash
# Install MLC LLM
pip install mlc-llm mlc-ai-nightly

# Compile model for WebGPU
mlc_llm compile \
    meta-llama/Llama-3.3-8B-Instruct \
    --target webgpu \
    --quantization q4f16_1 \
    -o dist/

# Serve web app
python -m http.server 8080 --directory dist/
```

**HTML Integration:**

```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm"></script>
</head>
<body>
    <div id="output"></div>
    <script>
        const llm = new webllm.MLCEngine();
        await llm.reload("Llama-3.3-8B-Instruct-q4f16_1");

        const response = await llm.chat.completions.create({
            messages: [{ role: "user", content: "Hello!" }]
        });

        document.getElementById("output").textContent = response.choices[0].message.content;
    </script>
</body>
</html>
```

#### Native Deployment

```bash
# Start local server
mlc_llm serve \
    meta-llama/Llama-3.3-8B-Instruct \
    --port 8080
```

#### Agenkit Integration

```python
# Use like any other OpenAI-compatible service
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8080/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="mlc"
)
```

#### Resources
- GitHub: https://github.com/mlc-ai/mlc-llm
- WebLLM: https://github.com/mlc-ai/web-llm
- Documentation: https://llm.mlc.ai/

---

### Text Generation Inference (TGI)

**Best for:** HuggingFace model integration

#### Overview
TGI by HuggingFace provides:
- Native HuggingFace Hub integration
- Optimized inference for HF models
- Production-ready deployment
- Advanced features (guided generation, etc.)

#### Requirements
- Python 3.9+
- Optional: NVIDIA GPU
- Docker (recommended)

#### Installation

**Docker (Recommended):**

```bash
# Run TGI with Docker
docker run --gpus all -p 8080:80 \
    -v $PWD/data:/data \
    ghcr.io/huggingface/text-generation-inference:latest \
    --model-id meta-llama/Llama-3.3-8B-Instruct \
    --num-shard 1
```

**Python:**

```bash
# Install TGI
pip install text-generation

# Start server
text-generation-launcher \
    --model-id meta-llama/Llama-3.3-8B-Instruct \
    --port 8080
```

#### Configuration

```bash
# With quantization
docker run --gpus all -p 8080:80 \
    ghcr.io/huggingface/text-generation-inference:latest \
    --model-id meta-llama/Llama-3.3-8B-Instruct \
    --quantize bitsandbytes-nf4

# Multi-GPU
docker run --gpus all -p 8080:80 \
    ghcr.io/huggingface/text-generation-inference:latest \
    --model-id meta-llama/Llama-3.3-70B-Instruct \
    --num-shard 4
```

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:8080/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="tgi"
)

messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
```

#### Resources
- GitHub: https://github.com/huggingface/text-generation-inference
- Documentation: https://huggingface.co/docs/text-generation-inference

---

### Inferflow

**Best for:** Research and custom optimizations

#### Overview
Inferflow is a high-performance inference engine for research.

#### Installation

```bash
# Clone repository
git clone https://github.com/inferflow/inferflow
cd inferflow

# Build
mkdir build && cd build
cmake ..
make -j

# Start server
./inferflow_server --model path/to/model --port 8080
```

#### Agenkit Integration

```python
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8080/v1",
    model="model-name",
    provider="inferflow"
)
```

#### Resources
- GitHub: https://github.com/inferflow/inferflow

---

### LM Studio

**Best for:** Desktop development and testing

#### Overview
LM Studio provides:
- GUI for model management
- Cross-platform (Mac, Windows, Linux)
- Local OpenAI-compatible server
- Easy model downloads
- No command line required

#### Installation

1. Download from: https://lmstudio.ai/
2. Install application
3. Launch LM Studio

#### Usage

1. **Download Model:**
   - Click "Search" tab
   - Search for "Llama-3.3-8B"
   - Click download

2. **Start Server:**
   - Click "Local Server" tab
   - Select model
   - Click "Start Server"
   - Default port: 1234

#### Agenkit Integration

```python
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:1234/v1",
    model="llama-3.3-8b-instruct",
    provider="lmstudio"
)

messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
```

#### Resources
- Website: https://lmstudio.ai/
- Documentation: https://lmstudio.ai/docs

---

## Model Selection

### Choosing the Right Model Size

| Model Size | Parameters | VRAM (FP16) | VRAM (Q4) | Best For | Speed |
|------------|------------|-------------|-----------|----------|-------|
| 1B-3B | 1-3B | ~4GB | ~2GB | Edge devices, testing | Very Fast |
| 7B-8B | 7-8B | ~16GB | ~4GB | **General use, recommended** | Fast |
| 13B-14B | 13-14B | ~26GB | ~8GB | Better quality | Medium |
| 30B-34B | 30-34B | ~60GB | ~18GB | High quality | Slow |
| 65B-70B | 65-70B | ~140GB | ~40GB | Best quality | Very Slow |
| 175B+ | 175B+ | ~350GB+ | ~100GB+ | Research, enterprise | Extremely Slow |

### Popular Models (January 2026)

**Recommended for Production:**

| Model | Size | License | Best For |
|-------|------|---------|----------|
| Llama-3.3-8B-Instruct | 8B | Llama 3 | General purpose (recommended) |
| Llama-3.3-70B-Instruct | 70B | Llama 3 | High quality |
| Mistral-7B-Instruct-v0.3 | 7B | Apache 2.0 | Fast, commercial-friendly |
| Mixtral-8x7B-Instruct | 47B (8x7B MoE) | Apache 2.0 | Quality + efficiency |
| Qwen2.5-7B-Instruct | 7B | Apache 2.0 | Multilingual, code |
| Phi-3-Mini-4K-Instruct | 3.8B | MIT | Small, efficient |

**For Code:**
- DeepSeek-Coder-33B-Instruct
- CodeLlama-70B-Instruct
- Qwen2.5-Coder-7B-Instruct

**For Reasoning:**
- Llama-3.3-70B-Instruct
- Qwen2.5-72B-Instruct
- DeepSeek-V2

### Model Format Guide

**GGUF (llama.cpp):**
- Quantized formats (Q2_K to F16)
- Best for CPU inference
- Download from HuggingFace (TheBloke repos)

**SafeTensors (HuggingFace):**
- Standard format
- Used by vLLM, SGLang, TGI
- Direct from HuggingFace Hub

**TensorRT Engines:**
- Pre-compiled for TensorRT-LLM
- Must build from HF models
- Optimized for specific hardware

---

## Performance Tuning

### General Optimization Strategies

#### 1. Choose the Right Quantization

**Quality vs Speed Trade-off:**

| Quantization | Quality Loss | Speed Gain | Memory Savings | When to Use |
|--------------|--------------|------------|----------------|-------------|
| FP16 | 0% | 1x (baseline) | 0% | Development, reference |
| INT8 | <2% | 2x | 50% | **Production (recommended)** |
| INT4 | 5-10% | 4x | 75% | High throughput priority |

#### 2. Tune Context Window

```python
# Smaller context = faster inference
llm = OpenAICompatibleLLM(
    base_url="...",
    model="...",
    # Configure in server startup, not here
)

# Use only what you need
response = await llm.complete(
    messages,
    max_tokens=500  # Not 2000 if you only need 500
)
```

#### 3. Batch Requests

```python
# Process multiple requests in parallel
import asyncio

messages_batch = [messages1, messages2, messages3, ...]
tasks = [llm.complete(msgs) for msgs in messages_batch]
responses = await asyncio.gather(*tasks)
```

#### 4. Use Appropriate Hardware

**For Different Workloads:**

```
Low latency (<100ms):
  TensorRT-LLM on A100/H100 + INT8

High throughput (>100 req/sec):
  vLLM on multiple GPUs + INT8

Cost-effective:
  llama.cpp on CPU + Q4_K_M

Chatbots:
  SGLang on GPU + FP16 (RadixAttention benefits)
```

### Service-Specific Tuning

**vLLM:**
```bash
--gpu-memory-utilization 0.95  # Use more GPU memory
--max-num-seqs 256             # Larger batch size
--max-model-len 4096           # Match your needs
```

**llama.cpp:**
```bash
--threads $(nproc)    # Use all CPU cores
--n-gpu-layers 35     # Offload to GPU
--mlock               # Lock in RAM
--batch-size 512      # Larger batch
```

**SGLang:**
```bash
--mem-fraction-static 0.9  # More cache memory
--tp-size 4                # Multi-GPU
```

**TensorRT-LLM:**
```bash
# Build with INT8
--weight_only_precision int8
--max_batch_size 128
```

### Benchmarking

```python
import time
import asyncio

async def benchmark(llm, messages, n=10):
    """Benchmark inference performance."""
    times = []
    tokens = []

    for i in range(n):
        start = time.time()
        response = await llm.complete(messages, max_tokens=100)
        elapsed = time.time() - start

        times.append(elapsed)
        tokens.append(response.metadata['usage']['completion_tokens'])

    avg_time = sum(times) / len(times)
    avg_tokens = sum(tokens) / len(tokens)
    throughput = avg_tokens / avg_time

    print(f"Average latency: {avg_time:.3f}s")
    print(f"Average tokens: {avg_tokens:.1f}")
    print(f"Throughput: {throughput:.1f} tokens/sec")
    print(f"P50 latency: {sorted(times)[len(times)//2]:.3f}s")
    print(f"P95 latency: {sorted(times)[int(len(times)*0.95)]:.3f}s")

# Run benchmark
messages = [Message(role="user", content="What is AI?")]
await benchmark(llm, messages, n=50)
```

---

## Migration Guide

### From OpenAI to Self-Hosted

**Step 1: Choose Your Service**

Based on requirements:
- High throughput → vLLM
- CPU-only → llama.cpp
- Chatbots → SGLang
- Lowest latency → TensorRT-LLM

**Step 2: Update Code**

```python
# Before (OpenAI)
from agenkit.adapters.llm import OpenAILLM

llm = OpenAILLM(
    api_key="sk-...",
    model="gpt-4"
)

# After (vLLM)
from agenkit.adapters.llm import OpenAICompatibleLLM

llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="vllm"
)

# Everything else stays the same!
messages = [Message(role="user", content="Hello")]
response = await llm.complete(messages)
```

**Step 3: Test and Tune**

1. Compare outputs between GPT-4 and your model
2. Adjust temperature/max_tokens if needed
3. Benchmark performance
4. Deploy to production

### Between Self-Hosted Services

```python
# Easy to switch between services
# Just change base_url and provider!

# vLLM
llm_vllm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="vllm"
)

# SGLang (same code!)
llm_sglang = OpenAICompatibleLLM(
    base_url="http://localhost:30000/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="sglang"
)
```

### Configuration Mapping

| OpenAI Parameter | Self-Hosted Equivalent | Notes |
|------------------|------------------------|-------|
| `api_key` | Not needed (local) or custom | Optional for local services |
| `model` | Model path/ID | Service-specific format |
| `temperature` | Same | ✅ Compatible |
| `max_tokens` | Same | ✅ Compatible |
| `top_p` | Same | ✅ Compatible |
| `frequency_penalty` | May not be supported | Check service docs |
| `presence_penalty` | May not be supported | Check service docs |
| `functions` | Not supported | Use structured prompting instead |

---

## Troubleshooting

### Common Issues

#### Service Won't Start

**Symptom:** Server fails to start or crashes immediately

**Solutions:**
1. Check GPU availability: `nvidia-smi`
2. Verify CUDA version matches requirements
3. Check disk space for model downloads
4. Review server logs for specific errors

```bash
# Check CUDA
nvidia-smi

# Check Docker logs
docker logs <container-id>

# Check disk space
df -h
```

#### Out of Memory (OOM)

**Symptom:** Service crashes with CUDA OOM or system OOM

**Solutions:**

**For GPU OOM:**
```bash
# Use smaller model
--model meta-llama/Llama-3.3-8B-Instruct  # Instead of 70B

# Use quantization
--weight-only-precision int8

# Reduce batch size
--max-num-seqs 64  # vLLM
--max-batch-size 32  # TensorRT-LLM

# Reduce context
--max-model-len 2048
```

**For CPU/RAM OOM (llama.cpp):**
```bash
# Use smaller quantization
# Q4_K_M instead of Q8_0

# Reduce context
--ctx-size 2048

# Reduce batch
--batch-size 256
```

#### Slow Inference

**Symptom:** Responses take too long (>5s for simple queries)

**Diagnose:**
```python
import time

start = time.time()
response = await llm.complete(messages)
elapsed = time.time() - start

print(f"Latency: {elapsed:.2f}s")
print(f"Tokens: {response.metadata['usage']['completion_tokens']}")
print(f"Tokens/sec: {response.metadata['usage']['completion_tokens'] / elapsed:.1f}")
```

**Solutions:**
1. **Check GPU utilization:** `nvidia-smi -l 1`
   - Should be >80% during inference
   - If low, increase batch size or fix bottlenecks

2. **Use faster service:**
   - llama.cpp → vLLM (10-50x faster with GPU)
   - FP16 → INT8 (2x faster)

3. **Reduce generation:**
   ```python
   response = await llm.complete(
       messages,
       max_tokens=100  # Not 2000
   )
   ```

4. **Enable GPU offloading (llama.cpp):**
   ```bash
   --n-gpu-layers 35  # Offload layers to GPU
   ```

#### Connection Refused

**Symptom:** `Connection refused` or `Connection timeout`

**Solutions:**
1. Verify service is running:
   ```bash
   # Check port
   lsof -i :8000  # or 8080, 30000, etc.

   # Test connection
   curl http://localhost:8000/health
   ```

2. Check firewall:
   ```bash
   sudo ufw allow 8000  # Linux
   ```

3. Use correct host:
   ```python
   # If in Docker, use host.docker.internal
   base_url="http://host.docker.internal:8000/v1"

   # Or use container IP
   base_url="http://172.17.0.2:8000/v1"
   ```

#### Model Loading Fails

**Symptom:** "Model not found" or "Failed to load model"

**Solutions:**
1. **Verify model exists:**
   ```bash
   # For llama.cpp
   ls -lh models/*.gguf

   # For HuggingFace models
   huggingface-cli scan-cache
   ```

2. **Check model format:**
   - vLLM/SGLang/TGI: SafeTensors (HuggingFace format)
   - llama.cpp: GGUF format
   - TensorRT-LLM: Pre-built engines

3. **Download model manually:**
   ```bash
   # HuggingFace Hub
   huggingface-cli download \
       meta-llama/Llama-3.3-8B-Instruct \
       --local-dir ./models/llama-3.3-8b
   ```

#### Poor Output Quality

**Symptom:** Responses are nonsensical or low quality

**Solutions:**
1. **Check quantization:**
   - Q2_K is too aggressive for most uses
   - Use Q4_K_M or higher

2. **Adjust temperature:**
   ```python
   # Too creative (temperature too high)
   response = await llm.complete(messages, temperature=0.7)

   # More focused (lower temperature)
   response = await llm.complete(messages, temperature=0.3)
   ```

3. **Verify model:**
   - Ensure using an "Instruct" or "Chat" model
   - Base models need prompt formatting

4. **Check prompt formatting:**
   ```python
   # May need chat template
   messages = [
       Message(role="system", content="You are a helpful assistant."),
       Message(role="user", content="Hello!")
   ]
   ```

### Service-Specific Issues

#### vLLM

**"CUDA out of memory":**
```bash
--gpu-memory-utilization 0.8  # Reduce from 0.9
--max-num-seqs 64            # Reduce batch size
```

**"Deadlock detected":**
- Known issue with some models
- Try `--disable-log-requests`

#### llama.cpp

**Very slow on CPU:**
```bash
--threads $(nproc)  # Use all cores
--mlock            # Prevent swapping
```

**Model format error:**
- Ensure using GGUF format (not older GGML)
- Re-download model from TheBloke repos

#### SGLang

**Cache not working:**
- Ensure using same system prompt
- Check `get_server_info` for cache hits

**OOM with large context:**
```bash
--mem-fraction-static 0.85  # Reduce cache memory
--max-total-tokens 4096    # Reduce context
```

#### TensorRT-LLM

**Engine build fails:**
- Check CUDA version matches TensorRT
- Ensure enough disk space (~200GB)
- Try building with `--strongly_typed`

**Slow inference:**
- Verify using INT8 engines
- Check GPU utilization
- Ensure NVLink enabled (multi-GPU)

### Getting Help

**Before asking for help:**
1. Check server logs
2. Verify hardware meets requirements
3. Try with a smaller model first
4. Search GitHub issues

**Where to get help:**
- vLLM: https://github.com/vllm-project/vllm/issues
- llama.cpp: https://github.com/ggerganov/llama.cpp/discussions
- SGLang: https://github.com/sgl-project/sglang/issues
- TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM/issues
- Agenkit: https://github.com/scttfrdmn/agenkit/issues

---

## Production Deployment

### Architecture Patterns

#### Single Instance (Small Scale)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       v
┌─────────────────┐
│  Inference      │
│  Service        │
│  (vLLM/SGLang)  │
└─────────────────┘
```

**When to use:**
- <10 concurrent users
- Development/testing
- Low traffic applications

**Setup:**
```bash
# Start service
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-3.3-8B-Instruct
```

#### Load Balanced (Medium Scale)

```
         ┌─────────────┐
         │   Client    │
         └──────┬──────┘
                │
                v
         ┌──────────────┐
         │ Load Balancer│
         │   (nginx)    │
         └──────┬───────┘
                │
        ┌───────┼───────┐
        v       v       v
    ┌────┐  ┌────┐  ┌────┐
    │Inst│  │Inst│  │Inst│
    │ 1  │  │ 2  │  │ 3  │
    └────┘  └────┘  └────┘
```

**When to use:**
- 10-100 concurrent users
- Need high availability
- Geographic distribution

**Setup:**

`docker-compose.yml`:
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - vllm1
      - vllm2
      - vllm3

  vllm1:
    image: vllm/vllm-openai
    command: >
      --model meta-llama/Llama-3.3-8B-Instruct
      --port 8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  vllm2:
    image: vllm/vllm-openai
    command: >
      --model meta-llama/Llama-3.3-8B-Instruct
      --port 8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]

  vllm3:
    image: vllm/vllm-openai
    command: >
      --model meta-llama/Llama-3.3-8B-Instruct
      --port 8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['2']
              capabilities: [gpu]
```

`nginx.conf`:
```nginx
upstream vllm_backend {
    least_conn;
    server vllm1:8000;
    server vllm2:8000;
    server vllm3:8000;
}

server {
    listen 80;

    location / {
        proxy_pass http://vllm_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

#### Kubernetes (Large Scale)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        args:
          - "--model"
          - "meta-llama/Llama-3.3-8B-Instruct"
          - "--port"
          - "8000"
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1
---
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
spec:
  selector:
    app: vllm
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: LoadBalancer
```

### Health Checks

```python
import httpx
import asyncio

async def health_check(base_url: str) -> bool:
    """Check if inference service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url.rstrip('/v1')}/health")
            return response.status_code == 200
    except:
        return False

# Use in production
if not await health_check("http://localhost:8000/v1"):
    # Failover to backup instance
    llm = OpenAICompatibleLLM(base_url="http://backup:8000/v1", ...)
```

### Failover Strategy

```python
class ResilientLLM:
    """LLM with automatic failover."""

    def __init__(self, endpoints: list[str]):
        self.endpoints = endpoints
        self.current_idx = 0

    async def complete(self, messages, **kwargs):
        """Try each endpoint until one succeeds."""
        for i in range(len(self.endpoints)):
            idx = (self.current_idx + i) % len(self.endpoints)
            llm = OpenAICompatibleLLM(
                base_url=self.endpoints[idx],
                model="meta-llama/Llama-3.3-8B-Instruct"
            )

            try:
                response = await llm.complete(messages, **kwargs)
                self.current_idx = idx  # Remember working endpoint
                return response
            except Exception as e:
                print(f"Endpoint {idx} failed: {e}")
                continue

        raise Exception("All endpoints failed")

# Usage
llm = ResilientLLM([
    "http://vllm1:8000/v1",
    "http://vllm2:8000/v1",
    "http://vllm3:8000/v1"
])

response = await llm.complete(messages)
```

### Monitoring

**Key Metrics to Track:**

1. **Request Latency**
   - P50, P95, P99 latency
   - Target: <1s P95 for most use cases

2. **Throughput**
   - Requests/second
   - Tokens/second
   - Target: Varies by use case

3. **Error Rate**
   - Failed requests / total requests
   - Target: <1%

4. **GPU Utilization**
   - Should be >80% under load
   - Monitor with `nvidia-smi`

5. **Queue Depth**
   - Pending requests
   - Alert if growing unbounded

**Prometheus Example:**

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
request_count = Counter('llm_requests_total', 'Total requests')
request_duration = Histogram('llm_request_duration_seconds', 'Request duration')
active_requests = Gauge('llm_active_requests', 'Active requests')
error_count = Counter('llm_errors_total', 'Total errors')

async def monitored_complete(llm, messages, **kwargs):
    """Instrumented completion."""
    request_count.inc()
    active_requests.inc()

    start = time.time()
    try:
        response = await llm.complete(messages, **kwargs)
        request_duration.observe(time.time() - start)
        return response
    except Exception as e:
        error_count.inc()
        raise
    finally:
        active_requests.dec()
```

---

## Monitoring & Observability

### Agenkit Integration

Agenkit provides built-in observability:

```python
from agenkit.observability import init_tracing, init_metrics, TracingMiddleware
from agenkit.adapters.llm import OpenAICompatibleLLM

# Initialize observability
init_tracing("otlp", "http://localhost:4317")
init_metrics("prometheus", None)

# Create LLM with tracing
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-3.3-8B-Instruct",
    provider="vllm"
)

# Wrap with tracing middleware for automatic instrumentation
# (Note: This is conceptual - actual implementation may vary)
traced_llm = TracingMiddleware(llm, service_name="vllm-inference")

# All requests automatically traced
response = await traced_llm.complete(messages)
```

### Dashboard Example (Grafana)

```json
{
  "dashboard": {
    "title": "LLM Inference Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(llm_requests_total[5m])"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, llm_request_duration_seconds)"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(llm_errors_total[5m]) / rate(llm_requests_total[5m])"
          }
        ]
      }
    ]
  }
}
```

---

## Best Practices

### Development

1. **Start small**: Use Q4_K_M quantized 7-8B models for development
2. **Use LM Studio**: GUI makes testing easier
3. **Test locally**: llama.cpp on CPU before GPU deployment
4. **Benchmark early**: Measure performance before production

### Production

1. **Use INT8 quantization**: 2x speed, minimal quality loss
2. **Load balance**: Multiple instances for redundancy
3. **Monitor everything**: Latency, errors, GPU utilization
4. **Set timeouts**: Prevent hanging requests
5. **Implement retries**: With exponential backoff
6. **Health checks**: Automatic failover to healthy instances

### Security

1. **Network isolation**: Keep inference services on private network
2. **Authentication**: Use API keys or OAuth
3. **Rate limiting**: Prevent abuse
4. **Input validation**: Sanitize prompts
5. **Audit logging**: Track all requests

### Cost Optimization

1. **Right-size models**: Don't use 70B if 8B suffices
2. **Quantization**: INT8/INT4 reduces compute and memory
3. **Batch requests**: Better GPU utilization
4. **Auto-scaling**: Scale down during low traffic
5. **Spot instances**: For non-critical workloads

---

## Conclusion

This guide covered setup and deployment of 9 OpenAI-compatible inference services with Agenkit. Key takeaways:

- **Choose the right service** for your use case (throughput vs latency vs cost)
- **Start with recommended quantization** (Q4_K_M or INT8)
- **Monitor production deployments** (latency, errors, GPU utilization)
- **Use Agenkit's `OpenAICompatibleLLM`** for consistent API across services

### Quick Decision Guide

```
Need lowest cost? → llama.cpp (CPU only)
Need lowest latency? → TensorRT-LLM (A100/H100)
Need highest throughput? → vLLM (GPU clusters)
Building chatbot? → SGLang (RadixAttention)
Just getting started? → LM Studio (GUI)
```

### Next Steps

1. Review examples: `examples/adapters/openai_compatible/`
2. Try the service that fits your use case
3. Benchmark with your expected load
4. Deploy to production with monitoring
5. Iterate and optimize

### Resources

- **Agenkit Docs**: https://agenkit.dev
- **Examples**: `examples/adapters/openai_compatible/`
- **GitHub Issues**: https://github.com/scttfrdmn/agenkit/issues

---

**Document Version:** 1.0
**Last Updated:** January 23, 2026
**Agenkit Version:** 0.49.0+
