"""
Sequential + Parallel Pattern Composition.

Demonstrates composing Sequential and Parallel patterns to create sophisticated
workflows with both pipeline stages and concurrent execution.

Use case: Document analysis pipeline with parallel processing stages.

This example shows:
- Pipeline with parallel stages
- Multi-perspective analysis at each stage
- Metadata flow through composition
- Error handling in composed patterns
"""

import asyncio

from agenkit.core import Agent, Message
from agenkit.patterns import (ParallelAgent, SequentialAgent,
                              default_aggregators)


# Stage 1: Parallel Pre-processing
class TextExtractor(Agent):
    """Extracts text content."""

    def name(self) -> str:
        return "TextExtractor"

    def capabilities(self) -> list[str]:
        return ["extraction"]

    async def process(self, message: Message) -> Message:
        print("     📄 Extracting text...")
        await asyncio.sleep(0.05)
        result = Message(role="agent", content="Extracted text: [content]")
        result.metadata["word_count"] = 150
        return result


class MetadataExtractor(Agent):
    """Extracts metadata."""

    def name(self) -> str:
        return "MetadataExtractor"

    def capabilities(self) -> list[str]:
        return ["metadata"]

    async def process(self, message: Message) -> Message:
        print("     📋 Extracting metadata...")
        await asyncio.sleep(0.05)
        result = Message(role="agent", content="Metadata: author, date, tags")
        result.metadata["has_metadata"] = True
        return result


class StructureExtractor(Agent):
    """Extracts document structure."""

    def name(self) -> str:
        return "StructureExtractor"

    def capabilities(self) -> list[str]:
        return ["structure"]

    async def process(self, message: Message) -> Message:
        print("     🏗️  Extracting structure...")
        await asyncio.sleep(0.05)
        result = Message(role="agent", content="Structure: 3 sections, 12 paragraphs")
        result.metadata["sections"] = 3
        return result


# Stage 2: Single processing agent
class ContentNormalizer(Agent):
    """Normalizes extracted content."""

    def name(self) -> str:
        return "ContentNormalizer"

    def capabilities(self) -> list[str]:
        return ["normalization"]

    async def process(self, message: Message) -> Message:
        print("   🔄 Stage 2: Normalizing content...")
        await asyncio.sleep(0.08)
        result = Message(
            role="agent",
            content="Normalized content ready for analysis",
        )
        result.metadata["normalized"] = True
        result.metadata["previous"] = message.metadata
        return result


# Stage 3: Parallel Analysis
class SentimentAnalyzer(Agent):
    """Analyzes sentiment."""

    def name(self) -> str:
        return "SentimentAnalyzer"

    def capabilities(self) -> list[str]:
        return ["sentiment"]

    async def process(self, message: Message) -> Message:
        print("     💭 Analyzing sentiment...")
        await asyncio.sleep(0.06)
        result = Message(role="agent", content="Sentiment: positive")
        result.metadata["sentiment"] = "positive"
        return result


class TopicModeler(Agent):
    """Models topics."""

    def name(self) -> str:
        return "TopicModeler"

    def capabilities(self) -> list[str]:
        return ["topics"]

    async def process(self, message: Message) -> Message:
        print("     📚 Modeling topics...")
        await asyncio.sleep(0.07)
        result = Message(role="agent", content="Topics: AI, Machine Learning")
        result.metadata["topics"] = ["AI", "Machine Learning"]
        return result


class QualityScorer(Agent):
    """Scores content quality."""

    def name(self) -> str:
        return "QualityScorer"

    def capabilities(self) -> list[str]:
        return ["quality"]

    async def process(self, message: Message) -> Message:
        print("     ⭐ Scoring quality...")
        await asyncio.sleep(0.05)
        result = Message(role="agent", content="Quality score: 8.5/10")
        result.metadata["quality_score"] = 8.5
        return result


# Stage 4: Final synthesis
class ReportGenerator(Agent):
    """Generates final report."""

    def name(self) -> str:
        return "ReportGenerator"

    def capabilities(self) -> list[str]:
        return ["reporting"]

    async def process(self, message: Message) -> Message:
        print("   📊 Stage 4: Generating report...")
        await asyncio.sleep(0.1)

        report = "Document Analysis Report\n"
        report += "=" * 40 + "\n\n"

        # Extract info from previous stages
        if "previous" in message.metadata:
            prev = message.metadata["previous"]
            if "word_count" in prev:
                report += f"Word count: {prev['word_count']}\n"
            if "sections" in prev:
                report += f"Sections: {prev['sections']}\n"

        report += "\nAnalysis Results:\n"
        report += "- Sentiment: positive\n"
        report += "- Topics: AI, Machine Learning\n"
        report += "- Quality: 8.5/10\n"

        result = Message(role="agent", content=report)
        result.metadata["report_generated"] = True
        return result


async def basic_composition():
    """Demonstrate basic sequential-parallel composition."""
    print("=" * 60)
    print("Document Analysis Pipeline")
    print("=" * 60)

    # Stage 1: Parallel extraction
    extraction_stage = ParallelAgent(
        agents=[
            TextExtractor(),
            MetadataExtractor(),
            StructureExtractor(),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    # Stage 2: Normalization (single agent)
    normalization_stage = ContentNormalizer()

    # Stage 3: Parallel analysis
    analysis_stage = ParallelAgent(
        agents=[
            SentimentAnalyzer(),
            TopicModeler(),
            QualityScorer(),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    # Stage 4: Report generation
    reporting_stage = ReportGenerator()

    # Compose into sequential pipeline
    pipeline = SequentialAgent(
        [
            extraction_stage,
            normalization_stage,
            analysis_stage,
            reporting_stage,
        ]
    )

    # Process document
    message = Message(
        role="user",
        content="Analyze this important document about AI and machine learning.",
    )

    print(f"\n📥 Input: {message.content}\n")
    print("Pipeline Execution:")
    print("  Stage 1: Parallel Extraction")

    import time

    start = time.time()
    result = await pipeline.process(message)
    elapsed = time.time() - start

    print(f"\n{'=' * 60}")
    print("\n📤 Final Report:\n")
    print(result.content)
    print(f"\n⏱️  Total time: {elapsed:.2f}s")
    print(f"   Pipeline stages: {result.metadata.get('pipeline_length', 0)}")


async def error_handling():
    """Demonstrate error handling in composed patterns."""
    print("\n\n" + "=" * 60)
    print("Error Handling in Composition")
    print("=" * 60)

    class FailingAnalyzer(Agent):
        """An analyzer that fails."""

        def name(self) -> str:
            return "FailingAnalyzer"

        def capabilities(self) -> list[str]:
            return ["analysis"]

        async def process(self, message: Message) -> Message:
            raise RuntimeError("Analysis failed")

    # Stage 1: Extraction (some will fail)
    extraction_stage = ParallelAgent(
        agents=[
            TextExtractor(),
            FailingAnalyzer(),  # This will fail
            StructureExtractor(),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    # Stage 2: Continue processing
    analysis_stage = ParallelAgent(
        agents=[
            SentimentAnalyzer(),
            TopicModeler(),
        ],
        aggregator=default_aggregators["concatenate"],
    )

    pipeline = SequentialAgent(
        [
            extraction_stage,
            analysis_stage,
        ]
    )

    message = Message(role="user", content="Test error handling")

    print(f"\n📥 Input: {message.content}\n")
    print("Processing with partial failures...")

    result = await pipeline.process(message)

    print("\n📤 Result: Partial success")
    print("   Pipeline continued despite failures")
    print(f"   Result content preview: {result.content[:100]}...")


async def metadata_flow():
    """Demonstrate metadata flow through composition."""
    print("\n\n" + "=" * 60)
    print("Metadata Flow Through Composition")
    print("=" * 60)

    # Simple pipeline to track metadata
    stage1 = ParallelAgent(
        agents=[TextExtractor(), MetadataExtractor()],
        aggregator=default_aggregators["concatenate"],
    )

    stage2 = ContentNormalizer()

    pipeline = SequentialAgent([stage1, stage2])

    message = Message(role="user", content="Track metadata flow")
    message.metadata["doc_id"] = "12345"
    message.metadata["source"] = "upload"

    print("\n📥 Input metadata:")
    print(f"   doc_id: {message.metadata['doc_id']}")
    print(f"   source: {message.metadata['source']}\n")

    result = await pipeline.process(message)

    print("\n📤 Output metadata:")
    print(f"   normalized: {result.metadata.get('normalized')}")
    if "previous" in result.metadata:
        prev = result.metadata["previous"]
        print(f"   word_count: {prev.get('word_count')}")
        print(f"   has_metadata: {prev.get('has_metadata')}")


async def main():
    """Run all examples."""
    print("\n🔀 Sequential + Parallel Pattern Composition\n")

    await basic_composition()
    await error_handling()
    await metadata_flow()

    print("\n✅ All examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
