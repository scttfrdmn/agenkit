"""
Cross-Language Image Processing Orchestrator (Python Side)

Demonstrates AgentKit's cross-language capabilities with a production-ready
distributed image processing system.

Architecture:
- Python: Orchestration, API gateway, ML integration
- Go: High-performance image processing workers (via gRPC)

This showcases the optimal use of each language's strengths.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from agenkit.adapters.python.remote_agent import RemoteAgent
from agenkit.interfaces import Message

# ============================================================================
# Data Models
# ============================================================================


class ProcessingTask(Enum):
    """Types of image processing tasks."""

    METADATA_EXTRACT = "metadata_extract"  # Extract EXIF, dimensions, etc.
    THUMBNAIL = "thumbnail"  # Generate thumbnail
    OPTIMIZE = "optimize"  # Optimize file size
    WATERMARK = "watermark"  # Add watermark
    ANALYZE = "analyze"  # ML-based analysis


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ImageJob:
    """Represents an image processing job."""

    job_id: str
    image_path: str
    tasks: list[ProcessingTask]
    priority: TaskPriority = TaskPriority.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ProcessingResult:
    """Result of image processing."""

    job_id: str
    task: ProcessingTask
    success: bool
    data: dict[str, Any]
    processing_time_ms: float
    worker_language: str
    error: str | None = None


# ============================================================================
# Distributed Processing Orchestrator
# ============================================================================


class ImageProcessingOrchestrator:
    """
    Orchestrates distributed image processing across Python and Go workers.

    Uses gRPC for high-performance cross-language communication.
    """

    def __init__(self, go_workers: list[str]):
        """
        Initialize orchestrator.

        Args:
            go_workers: List of gRPC endpoints for Go workers
                       (e.g., ["grpc://localhost:50051", "grpc://localhost:50052"])
        """
        self.go_workers = go_workers
        self.workers: list[RemoteAgent] = []
        self.next_worker_idx = 0
        self.job_stats: dict[str, Any] = {
            "total_jobs": 0,
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_time_ms": 0,
            "by_task": {},
            "by_language": {"python": 0, "go": 0},
        }

    async def start(self):
        """Initialize connections to all Go workers."""
        print(f"Starting orchestrator with {len(self.go_workers)} Go workers...")

        for i, endpoint in enumerate(self.go_workers):
            worker = RemoteAgent(name=f"go-worker-{i}", endpoint=endpoint)
            self.workers.append(worker)
            print(f"  ✓ Connected to Go worker at {endpoint}")

        print()

    async def stop(self):
        """Clean up connections."""
        for worker in self.workers:
            await worker.close()
        print("Orchestrator stopped")

    def _get_next_worker(self) -> RemoteAgent:
        """Round-robin load balancing across workers."""
        worker = self.workers[self.next_worker_idx]
        self.next_worker_idx = (self.next_worker_idx + 1) % len(self.workers)
        return worker

    async def process_job(self, job: ImageJob, verbose: bool = True) -> list[ProcessingResult]:
        """
        Process a complete image job.

        Distributes tasks across Go workers using gRPC for performance.

        Args:
            job: Image processing job with multiple tasks
            verbose: Print progress

        Returns:
            List of processing results
        """
        self.job_stats["total_jobs"] += 1
        self.job_stats["total_tasks"] += len(job.tasks)

        if verbose:
            print("=" * 70)
            print(f"Processing Job: {job.job_id}")
            print("=" * 70)
            print(f"Image: {job.image_path}")
            print(f"Tasks: {len(job.tasks)}")
            print(f"Priority: {job.priority.value}")
            print()

        # Process tasks in parallel across workers
        start_time = time.time()
        tasks_coroutines = [self._process_task(job, task, verbose) for task in job.tasks]
        results = await asyncio.gather(*tasks_coroutines)
        total_time = (time.time() - start_time) * 1000

        # Update stats
        for result in results:
            if result.success:
                self.job_stats["successful_tasks"] += 1
            else:
                self.job_stats["failed_tasks"] += 1

            self.job_stats["by_language"][result.worker_language] += 1

            task_name = result.task.value
            if task_name not in self.job_stats["by_task"]:
                self.job_stats["by_task"][task_name] = {"count": 0, "time_ms": 0}
            self.job_stats["by_task"][task_name]["count"] += 1
            self.job_stats["by_task"][task_name]["time_ms"] += result.processing_time_ms

        self.job_stats["total_time_ms"] += total_time

        if verbose:
            print(f"\nJob completed in {total_time:.1f}ms")
            print(f"  Success: {sum(1 for r in results if r.success)}/{len(results)}")
            print()

        return results

    async def _process_task(
        self, job: ImageJob, task: ProcessingTask, verbose: bool
    ) -> ProcessingResult:
        """Process a single task using appropriate worker."""

        # Route task to appropriate worker
        # For now, all image processing goes to Go workers (performance)
        # In production, ML tasks might go to Python workers
        worker = self._get_next_worker()

        # Build request message
        request = {
            "job_id": job.job_id,
            "task": task.value,
            "image_path": job.image_path,
            "priority": job.priority.value,
            "metadata": job.metadata,
        }

        message = Message(role="user", content=f"process:{task.value}", metadata=request)

        if verbose:
            print(f"  → Task: {task.value} (via {worker.name})")

        start_time = time.time()

        try:
            # Send to Go worker via gRPC
            response = await worker.process(message)
            processing_time = (time.time() - start_time) * 1000

            result = ProcessingResult(
                job_id=job.job_id,
                task=task,
                success=True,
                data=response.metadata,
                processing_time_ms=processing_time,
                worker_language=response.metadata.get("worker_language", "go"),
            )

            if verbose:
                print(f"    ✓ {task.value}: {processing_time:.1f}ms")

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000

            result = ProcessingResult(
                job_id=job.job_id,
                task=task,
                success=False,
                data={},
                processing_time_ms=processing_time,
                worker_language="unknown",
                error=str(e),
            )

            if verbose:
                print(f"    ✗ {task.value}: {e}")

            return result

    async def process_batch(
        self, jobs: list[ImageJob], verbose: bool = True
    ) -> dict[str, list[ProcessingResult]]:
        """
        Process multiple jobs in parallel.

        Demonstrates high-throughput distributed processing.
        """
        if verbose:
            print(f"\n{'=' * 70}")
            print(f"Batch Processing: {len(jobs)} jobs")
            print(f"{'=' * 70}\n")

        start_time = time.time()

        # Process all jobs in parallel
        results = await asyncio.gather(*[self.process_job(job, verbose=False) for job in jobs])

        total_time = (time.time() - start_time) * 1000

        # Group results by job_id
        results_by_job = {}
        for job, job_results in zip(jobs, results, strict=False):
            results_by_job[job.job_id] = job_results

        if verbose:
            total_tasks = sum(len(r) for r in results)
            successful = sum(sum(1 for task in r if task.success) for r in results)

            print(f"\nBatch completed in {total_time:.1f}ms")
            print(f"  Jobs: {len(jobs)}")
            print(f"  Tasks: {total_tasks}")
            print(
                f"  Success Rate: {successful}/{total_tasks} ({successful / total_tasks * 100:.1f}%)"
            )
            print(f"  Throughput: {total_tasks / (total_time / 1000):.1f} tasks/sec")
            print()

        return results_by_job

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        avg_time = (
            self.job_stats["total_time_ms"] / self.job_stats["total_jobs"]
            if self.job_stats["total_jobs"] > 0
            else 0
        )

        success_rate = (
            self.job_stats["successful_tasks"] / self.job_stats["total_tasks"]
            if self.job_stats["total_tasks"] > 0
            else 0
        )

        return {
            **self.job_stats,
            "avg_time_per_job_ms": avg_time,
            "success_rate": success_rate,
            "throughput_tasks_per_sec": (
                self.job_stats["total_tasks"] / (self.job_stats["total_time_ms"] / 1000)
                if self.job_stats["total_time_ms"] > 0
                else 0
            ),
        }
