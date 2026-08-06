#!/usr/bin/env python3
"""
TensorRT-LLM Integration Example

This example demonstrates how to use Agenkit with TensorRT-LLM, NVIDIA's
high-performance inference engine optimized for enterprise GPU deployments.
TensorRT-LLM provides maximum throughput and minimum latency on NVIDIA
datacenter GPUs (A100, H100).

Setup:
    1. Prerequisites:
       - NVIDIA GPU (A100, H100, or compatible)
       - CUDA 12.0+
       - TensorRT 9.0+
       - Docker with NVIDIA Container Runtime

    2. Build TensorRT-LLM engine (one-time setup):
       # Clone TensorRT-LLM
       git clone https://github.com/NVIDIA/TensorRT-LLM.git
       cd TensorRT-LLM

       # Build engine from HuggingFace model
       python examples/llama/build.py \
           --model_dir meta-llama/Llama-3.3-70B-Instruct \
           --output_dir ./engines/llama-70b \
           --dtype float16 \
           --use_gpt_attention_plugin float16

    3. Start OpenAI-compatible server:
       python examples/server/launch_server.py \
           --engine_dir ./engines/llama-70b \
           --port 8001 \
           --host 0.0.0.0

    4. Run this example:
       uv run python examples/adapters/openai_compatible/tensorrt_example.py

Requirements:
    - NVIDIA A100 (80GB) or H100 (80GB) for 70B models
    - NVIDIA A100 (40GB) for 7-13B models
    - CUDA 12.0+, TensorRT 9.0+
    - ~140GB VRAM for Llama-70B FP16

Key Features:
    - Optimized CUDA kernels for maximum throughput
    - Low latency with tensor parallelism
    - INT8/FP8 quantization support
    - Multi-GPU deployment
    - Production-grade performance monitoring

Learn more:
    - TensorRT-LLM: https://github.com/NVIDIA/TensorRT-LLM
    - Optimization Guide: https://nvidia.github.io/TensorRT-LLM/
    - Performance Tuning: https://docs.nvidia.com/deeplearning/tensorrt/
"""

import asyncio
import time
from typing import Any

from agenkit.adapters.llm import OpenAICompatibleLLM
from agenkit.interfaces import Message


async def basic_completion() -> None:
    """Basic completion example with TensorRT-LLM."""
    print("=" * 60)
    print("Basic Completion Example - Enterprise GPU Inference")
    print("=" * 60)

    # Connect to TensorRT-LLM server
    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8001/v1",
        model="llama-70b-instruct",
        provider="tensorrt",
    )

    messages = [
        Message(
            role="user",
            content="Explain the benefits of TensorRT-LLM for production deployments.",
        )
    ]

    print("\n📤 Sending query about TensorRT-LLM benefits...")
    start_time = time.time()
    response = await llm.complete(messages, max_tokens=500)
    elapsed = time.time() - start_time

    print(f"\n📥 Response: {response.content}")
    print("\n📊 Performance Metrics:")
    print(f"  • Model: {response.metadata['model']}")
    print(f"  • Provider: {response.metadata['provider']}")
    print(f"  • Total Tokens: {response.metadata['usage']['total_tokens']}")
    print(f"  • Latency: {elapsed:.3f}s")
    print(
        f"  • Throughput: {response.metadata['usage']['completion_tokens'] / elapsed:.1f} tokens/sec"
    )


async def high_throughput_batch() -> None:
    """
    Demonstrate high-throughput batch processing.

    TensorRT-LLM excels at processing multiple requests concurrently
    with optimal GPU utilization.
    """
    print("\n\n" + "=" * 60)
    print("High-Throughput Batch Processing")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8001/v1",
        model="llama-70b-instruct",
        provider="tensorrt",
    )

    # Simulate concurrent requests
    test_prompts = [
        "What is artificial intelligence?",
        "Explain quantum computing.",
        "What are neural networks?",
        "Describe machine learning.",
        "What is deep learning?",
    ]

    print(f"\n🚀 Processing {len(test_prompts)} requests concurrently...")

    start_time = time.time()

    # Process all requests concurrently
    tasks = []
    for prompt in test_prompts:
        messages = [Message(role="user", content=prompt)]
        tasks.append(llm.complete(messages, max_tokens=100))

    responses = await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    total_tokens = sum(r.metadata["usage"]["total_tokens"] for r in responses)
    throughput = total_tokens / total_time

    print(f"\n📊 Batch Results:")
    print(f"  • Requests: {len(test_prompts)}")
    print(f"  • Total time: {total_time:.2f}s")
    print(f"  • Avg time/request: {total_time / len(test_prompts):.2f}s")
    print(f"  • Total tokens: {total_tokens}")
    print(f"  • Throughput: {throughput:.1f} tokens/sec")
    print(f"  • GPU utilization: High (concurrent processing)")


async def low_latency_inference() -> None:
    """Demonstrate low-latency inference for real-time applications."""
    print("\n\n" + "=" * 60)
    print("Low-Latency Inference Example")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8001/v1",
        model="llama-70b-instruct",
        provider="tensorrt",
        timeout=5.0,  # Strict timeout for latency-sensitive apps
    )

    print("\n⚡ Running latency test (10 requests)...")

    latencies = []
    for i in range(10):
        messages = [Message(role="user", content=f"Quick response test {i + 1}")]

        start = time.time()
        response = await llm.complete(messages, max_tokens=50)
        latency = time.time() - start
        latencies.append(latency)

        print(f"  Request {i + 1}: {latency * 1000:.0f}ms")

    avg_latency = sum(latencies) / len(latencies)
    p50 = sorted(latencies)[len(latencies) // 2]
    p95 = sorted(latencies)[int(len(latencies) * 0.95)]

    print(f"\n📊 Latency Statistics:")
    print(f"  • Average: {avg_latency * 1000:.0f}ms")
    print(f"  • P50: {p50 * 1000:.0f}ms")
    print(f"  • P95: {p95 * 1000:.0f}ms")
    print(f"  • Min: {min(latencies) * 1000:.0f}ms")
    print(f"  • Max: {max(latencies) * 1000:.0f}ms")


async def multi_gpu_deployment() -> None:
    """Example configuration for multi-GPU deployment."""
    print("\n\n" + "=" * 60)
    print("Multi-GPU Deployment Configuration")
    print("=" * 60)

    print("\n🔧 TensorRT-LLM Multi-GPU Setup:")
    print("-" * 60)
    print("  # Tensor Parallelism (split model across GPUs)")
    print("  python build.py \\")
    print("      --model_dir meta-llama/Llama-3.3-70B-Instruct \\")
    print("      --tp_size 4  # Use 4 GPUs")
    print()
    print("  # Pipeline Parallelism (layer distribution)")
    print("  python build.py \\")
    print("      --model_dir meta-llama/Llama-3.3-70B-Instruct \\")
    print("      --pp_size 2  # 2-stage pipeline")

    print("\n📊 GPU Configuration Recommendations:")
    print("-" * 60)
    print("  Model Size      | GPUs | Config")
    print("  ----------------|------|------------------")
    print("  Llama-7B-8B     | 1    | Single GPU")
    print("  Llama-13B       | 1-2  | TP=1 or TP=2")
    print("  Llama-70B       | 4-8  | TP=4 or TP=8")
    print("  Llama-405B      | 8+   | TP=8, PP=2+")

    print("\n🎯 When to Use Multi-GPU:")
    print("  ✓ Model doesn't fit in single GPU VRAM")
    print("  ✓ Need maximum throughput")
    print("  ✓ Production deployment with high load")
    print("  ✗ Development/testing (use single GPU)")


async def quantization_options() -> None:
    """Demonstrate quantization for better performance."""
    print("\n\n" + "=" * 60)
    print("Quantization Options")
    print("=" * 60)

    print("\n⚙️  TensorRT-LLM Quantization Support:")
    print("-" * 60)
    print("  FP16:  Standard precision, good quality")
    print("  INT8:  2x throughput, minimal quality loss")
    print("  FP8:   1.5x throughput (H100 GPUs only)")
    print("  INT4:  4x throughput, some quality loss")

    print("\n📝 Building Quantized Engine:")
    print("-" * 60)
    print("  # INT8 (recommended for production)")
    print("  python build.py \\")
    print("      --model_dir meta-llama/Llama-3.3-70B-Instruct \\")
    print("      --dtype float16 \\")
    print("      --use_weight_only \\")
    print("      --weight_only_precision int8")
    print()
    print("  # FP8 (H100 only - maximum performance)")
    print("  python build.py \\")
    print("      --model_dir meta-llama/Llama-3.3-70B-Instruct \\")
    print("      --dtype float16 \\")
    print("      --use_fp8")

    print("\n📊 Performance vs Quality Trade-offs:")
    print("-" * 60)
    print("  Format | Speed  | Quality | VRAM  | Use Case")
    print("  -------|--------|---------|-------|------------------")
    print("  FP16   | 1x     | ⭐⭐⭐⭐⭐ | 1x    | Development")
    print("  INT8   | 2x     | ⭐⭐⭐⭐   | 0.5x  | Production (rec)")
    print("  FP8    | 1.5x   | ⭐⭐⭐⭐⭐ | 0.7x  | H100 production")
    print("  INT4   | 4x     | ⭐⭐⭐    | 0.25x | High throughput")


async def production_monitoring() -> None:
    """Production monitoring and metrics example."""
    print("\n\n" + "=" * 60)
    print("Production Monitoring")
    print("=" * 60)

    llm = OpenAICompatibleLLM(
        base_url="http://localhost:8001/v1",
        model="llama-70b-instruct",
        provider="tensorrt",
    )

    print("\n📊 Key Metrics to Monitor:")
    print("-" * 60)
    print("  • Request latency (P50, P95, P99)")
    print("  • Throughput (requests/sec, tokens/sec)")
    print("  • GPU utilization (%)")
    print("  • GPU memory usage (GB)")
    print("  • Queue depth (pending requests)")
    print("  • Error rate (%)")

    print("\n🔍 Example Request with Metrics:")
    messages = [Message(role="user", content="Test request for monitoring")]

    start = time.time()
    response = await llm.complete(messages, max_tokens=100)
    latency = time.time() - start

    # Extract and display metrics
    metrics: dict[str, Any] = {
        "latency_ms": latency * 1000,
        "prompt_tokens": response.metadata["usage"]["prompt_tokens"],
        "completion_tokens": response.metadata["usage"]["completion_tokens"],
        "total_tokens": response.metadata["usage"]["total_tokens"],
        "throughput_tokens_sec": response.metadata["usage"]["completion_tokens"] / latency,
    }

    print("\n📈 Request Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  • {key}: {value:.2f}")
        else:
            print(f"  • {key}: {value}")

    print("\n⚠️  Alert Thresholds (example):")
    print("  • P95 latency > 500ms: Scale up")
    print("  • GPU utilization > 90%: Add capacity")
    print("  • Error rate > 1%: Investigate")


async def deployment_best_practices() -> None:
    """Best practices for TensorRT-LLM deployment."""
    print("\n\n" + "=" * 60)
    print("Deployment Best Practices")
    print("=" * 60)

    print("\n🏗️  Architecture Recommendations:")
    print("-" * 60)
    print("  1. Load Balancer")
    print("     ↓")
    print("  2. Multiple TensorRT-LLM Instances")
    print("     ├─ Instance 1 (GPU 0-3)")
    print("     ├─ Instance 2 (GPU 4-7)")
    print("     └─ Instance N")
    print("     ↓")
    print("  3. Metrics Collection (Prometheus)")
    print("     ↓")
    print("  4. Monitoring Dashboard (Grafana)")

    print("\n✅ Production Checklist:")
    print("-" * 60)
    print("  □ Build optimized engine with INT8/FP8 quantization")
    print("  □ Configure appropriate tensor parallelism")
    print("  □ Set up load balancing across instances")
    print("  □ Implement request queuing and batching")
    print("  □ Monitor GPU utilization and latency")
    print("  □ Set up alerting for degraded performance")
    print("  □ Plan for model updates and A/B testing")
    print("  □ Implement request logging for debugging")
    print("  □ Configure auto-scaling based on load")

    print("\n🔐 Security Considerations:")
    print("  • Use authentication for API access")
    print("  • Implement rate limiting per user/API key")
    print("  • Log all requests for audit trail")
    print("  • Use TLS/SSL for encrypted communication")
    print("  • Isolate inference workloads in containers")


async def main() -> None:
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 11 + "TensorRT-LLM Integration Examples" + " " * 14 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # Run examples
        await basic_completion()
        await high_throughput_batch()
        await low_latency_inference()
        await multi_gpu_deployment()
        await quantization_options()
        await production_monitoring()
        await deployment_best_practices()

        print("\n\n" + "=" * 60)
        print("✅ All examples completed successfully!")
        print("=" * 60)
        print("\n🎯 Key Takeaways:")
        print("  • TensorRT-LLM provides maximum GPU performance")
        print("  • INT8/FP8 quantization for 1.5-2x speedup")
        print("  • Multi-GPU support for large models")
        print("  • Production-ready with monitoring and metrics")
        print("  • Ideal for high-throughput, low-latency deployments")
        print("\n💡 When to Use TensorRT-LLM:")
        print("  ✓ Production deployments on NVIDIA GPUs")
        print("  ✓ High-throughput requirements (>100 req/sec)")
        print("  ✓ Low-latency requirements (<100ms P95)")
        print("  ✓ Large models (70B+) on multi-GPU systems")
        print("\nNext steps:")
        print("  • Build optimized engine for your model")
        print("  • Benchmark with your expected load")
        print("  • Set up monitoring and alerting")
        print("  • See production_setup.py for full deployment guide")

    except Exception as e:
        print(f"\n\n❌ Error running examples: {e}")
        print("\nTroubleshooting:")
        print("  1. Is TensorRT-LLM server running? Check: curl http://localhost:8001/health")
        print("  2. Build engine first:")
        print("     cd TensorRT-LLM")
        print("     python examples/llama/build.py --model_dir <model> \\")
        print("       --output_dir ./engines/llama --dtype float16")
        print("  3. Start server:")
        print("     python examples/server/launch_server.py \\")
        print("       --engine_dir ./engines/llama --port 8001")
        print("  4. Ensure NVIDIA drivers and CUDA are installed")
        print("  5. Check GPU availability: nvidia-smi")
        raise


if __name__ == "__main__":
    asyncio.run(main())
