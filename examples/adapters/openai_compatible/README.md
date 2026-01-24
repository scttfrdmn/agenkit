# OpenAI-Compatible LLM Adapter Examples

This directory contains examples for using Agenkit with OpenAI-compatible inference services.

## What is the OpenAI-Compatible Adapter?

The `OpenAICompatibleLLM` adapter allows you to use **any** inference service that implements the OpenAI Chat Completions API with Agenkit. This includes popular local and self-hosted engines:

- **vLLM** - High-throughput batch inference
- **llama.cpp** - Lightweight C++ implementation (CPU-friendly)
- **SGLang** - Optimized for complex prompts
- **TensorRT-LLM** - NVIDIA GPU optimized
- **OpenLLM** - Multi-model serving platform
- **MLC LLM** - Mobile and edge deployment
- **Text Generation Inference (TGI)** - HuggingFace inference server
- **Inferflow** - High-performance inference

## Quick Start

```python
from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message

# Connect to local vLLM server
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-2-7b-chat-hf",
    provider="vllm"
)

# Use like any other LLM
messages = [Message(role="user", content="Hello!")]
response = await llm.complete(messages)
print(response.content)
```

## Examples

### 1. vLLM Integration ([vllm_example.py](vllm_example.py))

Comprehensive example showing:
- Basic completions
- Streaming responses
- Multi-turn conversations
- Custom parameters (temperature, max_tokens)
- Error handling

**Setup:**
```bash
# Start vLLM with Docker
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-2-7b-chat-hf

# Run example
uv run python examples/adapters/openai_compatible/vllm_example.py
```

**Requirements:**
- GPU with CUDA support
- ~14GB VRAM for Llama-2-7b

### 2. Service Comparison ([service_comparison.py](service_comparison.py))

Compare performance across different inference engines:
- vLLM vs llama.cpp vs SGLang vs TensorRT-LLM
- Performance benchmarking
- Migration patterns from OpenAI to self-hosted
- Code portability demonstration

**Run:**
```bash
uv run python examples/adapters/openai_compatible/service_comparison.py
```

### 3. Production Deployment ([production_setup.py](production_setup.py))

Production-ready patterns:
- Health checks and connection validation
- Load balancing across multiple instances
- Automatic failover and retry logic
- Monitoring and observability
- Docker Compose configuration
- Kubernetes deployment guide

**Run:**
```bash
uv run python examples/adapters/openai_compatible/production_setup.py
```

## Service Setup Guides

### vLLM

**Docker (Recommended):**
```bash
docker run --gpus all -p 8000:8000 vllm/vllm-openai \
    --model meta-llama/Llama-2-7b-chat-hf \
    --dtype float16
```

**Python:**
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-2-7b-chat-hf
```

**Documentation:** https://docs.vllm.ai/

### llama.cpp

**Build & Run:**
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make
./server -m models/llama-2-7b-chat.gguf -c 2048 --port 8080
```

**Docker:**
```bash
docker run -p 8080:8080 -v /path/to/models:/models \
    ghcr.io/ggerganov/llama.cpp:server \
    --model /models/llama-2-7b-chat.gguf --port 8080
```

**Documentation:** https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md

### SGLang

**Install & Run:**
```bash
pip install sglang
python -m sglang.launch_server \
    --model-path meta-llama/Llama-2-7b-chat-hf \
    --port 30000
```

**Documentation:** https://sgl-project.github.io/

### TensorRT-LLM

**Docker (NVIDIA GPUs):**
```bash
docker run --gpus all -p 8001:8001 \
    nvcr.io/nvidia/tritonserver:23.10-trtllm-python-py3 \
    tritonserver --model-repository=/models
```

**Documentation:** https://github.com/NVIDIA/TensorRT-LLM

## Key Features

### 1. Same Code, Any Service

The same Agenkit code works with all OpenAI-compatible services:

```python
# Works with vLLM
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="llama-2-7b",
    provider="vllm"
)

# Works with llama.cpp (just change URL!)
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8080/v1",
    model="llama-2-7b",
    provider="llamacpp"
)

# Same usage for both
response = await llm.complete(messages)
```

### 2. Easy Migration from OpenAI

Switching from OpenAI to self-hosted is a one-line change:

```python
# Before (OpenAI)
from agenkit.adapters.llm import OpenAILLM
llm = OpenAILLM(api_key="sk-...", model="gpt-4")

# After (Self-hosted vLLM)
from agenkit.adapters.llm import OpenAICompatibleLLM
llm = OpenAICompatibleLLM(
    base_url="http://localhost:8000/v1",
    model="meta-llama/Llama-2-7b-chat-hf",
    provider="vllm"
)

# Rest of code stays the same!
```

### 3. Provider Metadata

Responses include provider information for debugging:

```python
response = await llm.complete(messages)
print(response.metadata["provider"])    # "vllm"
print(response.metadata["base_url"])    # "http://localhost:8000/v1"
print(response.metadata["model"])       # "meta-llama/Llama-2-7b-chat-hf"
```

### 4. Consistent Interface

All standard LLM methods work:
- `complete()` - Standard completion
- `stream()` - Streaming response
- `unwrap()` - Access underlying AsyncOpenAI client

## Common Issues

### Service Not Starting

**Problem:** Model loading takes a long time

**Solution:** Wait for the service to fully load. Check health:
```bash
curl http://localhost:8000/health  # vLLM
curl http://localhost:8080/health  # llama.cpp
```

### Out of Memory (OOM)

**Problem:** GPU runs out of memory

**Solutions:**
- Use a smaller model (e.g., 7B instead of 13B)
- Use quantized models (4-bit, 8-bit)
- Reduce batch size
- Use CPU inference (slower but works)

### Connection Refused

**Problem:** Can't connect to service

**Solutions:**
- Verify service is running: `docker ps` or check process
- Check port is correct (8000 for vLLM, 8080 for llama.cpp)
- Use `127.0.0.1` instead of `localhost` if DNS issues

### Slow Inference

**Problem:** Responses take too long

**Solutions:**
- Use GPU instead of CPU
- Reduce `max_tokens` parameter
- Try a faster inference engine (vLLM for throughput, TensorRT-LLM for latency)
- Use model quantization

## Performance Tips

### 1. Choose the Right Engine

- **vLLM**: Best for high-throughput batch inference (serving many users)
- **llama.cpp**: Best for CPU inference and low resource usage
- **SGLang**: Best for complex prompts and structured generation
- **TensorRT-LLM**: Best for lowest latency on NVIDIA GPUs

### 2. Optimize Model Selection

- **7B models**: Fast, good for most tasks, ~14GB VRAM
- **13B models**: Better quality, slower, ~26GB VRAM
- **70B models**: Best quality, very slow, requires multiple GPUs

### 3. Use Quantization

Quantized models are smaller and faster with minimal quality loss:
- **FP16**: Half precision, 2x faster, same quality
- **INT8**: 8-bit, 4x faster, slight quality loss
- **INT4**: 4-bit, 8x faster, noticeable quality loss

### 4. Batch Requests

For high throughput, batch multiple requests together:
```python
# Process multiple requests in parallel
tasks = [llm.complete(msgs) for msgs in message_batches]
responses = await asyncio.gather(*tasks)
```

## Next Steps

1. **Try the examples** in order: vLLM → Service Comparison → Production Setup
2. **Experiment with different services** to find the best fit for your use case
3. **Read the documentation** for your chosen inference engine
4. **Deploy to production** using the patterns in production_setup.py

## Resources

- **Agenkit Documentation:** https://agenkit.dev
- **Issue Tracker:** https://github.com/scttfrdmn/agenkit/issues
- **vLLM Docs:** https://docs.vllm.ai/
- **llama.cpp Docs:** https://github.com/ggerganov/llama.cpp
- **SGLang Docs:** https://sgl-project.github.io/
- **TensorRT-LLM Docs:** https://github.com/NVIDIA/TensorRT-LLM

## Contributing

Found a bug or have a suggestion? Please [open an issue](https://github.com/scttfrdmn/agenkit/issues)!
