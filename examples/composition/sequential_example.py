"""
Sequential Composition Example

This example demonstrates WHY and HOW to use sequential composition for building
data pipelines, multi-stage processing, and separation of concerns.

WHY USE SEQUENTIAL COMPOSITION?
-------------------------------
1. Separation of Concerns: Each agent does one thing well
2. Data Pipelines: Natural fit for ETL, data transformation workflows
3. Modularity: Easy to add/remove/reorder stages
4. Testability: Test each stage independently
5. Clarity: Pipeline structure makes data flow obvious
6. Incremental Processing: Transform data step-by-step

WHEN TO USE:
- Data transformation pipelines (ETL)
- Multi-stage content processing (translate → summarize → classify)
- Validation → processing → formatting workflows
- Request/response transformation chains
- Content moderation pipelines
- Document processing workflows

WHEN NOT TO USE:
- Independent operations that can run in parallel (use ParallelAgent)
- Conditional logic based on input (use ConditionalAgent)
- When any stage can satisfy the request (use FallbackAgent)
- Real-time systems where cumulative latency is critical

TRADE-OFFS:
- Simplicity & Clarity vs Parallelism
- Sequential latency (sum of all stages) vs Code clarity
- Easy debugging vs Total throughput
- Predictable behavior vs Maximum performance
"""

import asyncio
from typing import Any
from agenkit.interfaces import Agent, Message
from agenkit.composition import SequentialAgent


# Example 1: Content Processing Pipeline
class TranslationAgent(Agent):
    """Translates text to English."""

    def __init__(self, source_lang: str = "auto"):
        self.source_lang = source_lang

    @property
    def name(self) -> str:
        return "translator"

    @property
    def capabilities(self) -> list[str]:
        return ["translation"]

    async def process(self, message: Message) -> Message:
        """Simulate translation (in real system, call translation API)."""
        text = str(message.content)

        # Simulate translation latency
        await asyncio.sleep(0.1)

        # Detect language and translate
        if "bonjour" in text.lower():
            translated = text.replace("Bonjour", "Hello").replace("bonjour", "hello")
            lang = "French"
        elif "hola" in text.lower():
            translated = text.replace("Hola", "Hello").replace("hola", "hello")
            lang = "Spanish"
        else:
            translated = text
            lang = "English"

        return Message(
            role="agent",
            content=translated,
            metadata={
                **message.metadata,
                "source_language": lang,
                "translated": lang != "English"
            }
        )


class SummarizationAgent(Agent):
    """Summarizes text to key points."""

    @property
    def name(self) -> str:
        return "summarizer"

    @property
    def capabilities(self) -> list[str]:
        return ["summarization"]

    async def process(self, message: Message) -> Message:
        """Simulate summarization (in real system, call LLM)."""
        text = str(message.content)

        # Simulate LLM latency
        await asyncio.sleep(0.2)

        # Simple summarization logic
        sentences = text.split(".")
        summary = f"Summary: {len(sentences)} sentences. "
        if len(text) > 100:
            summary += f"First point: {sentences[0].strip()}..."
        else:
            summary += text.strip()

        return Message(
            role="agent",
            content=summary,
            metadata={
                **message.metadata,
                "original_length": len(text),
                "summary_length": len(summary),
                "compression_ratio": len(summary) / len(text) if len(text) > 0 else 0
            }
        )


class SentimentAgent(Agent):
    """Analyzes sentiment of text."""

    @property
    def name(self) -> str:
        return "sentiment"

    @property
    def capabilities(self) -> list[str]:
        return ["sentiment_analysis"]

    async def process(self, message: Message) -> Message:
        """Simulate sentiment analysis."""
        text = str(message.content).lower()

        # Simulate analysis latency
        await asyncio.sleep(0.05)

        # Simple sentiment detection
        positive_words = ["good", "great", "excellent", "amazing", "wonderful"]
        negative_words = ["bad", "terrible", "awful", "horrible", "poor"]

        pos_count = sum(1 for word in positive_words if word in text)
        neg_count = sum(1 for word in negative_words if word in text)

        if pos_count > neg_count:
            sentiment = "positive"
            score = 0.8
        elif neg_count > pos_count:
            sentiment = "negative"
            score = 0.2
        else:
            sentiment = "neutral"
            score = 0.5

        return Message(
            role="agent",
            content=f"{message.content} [Sentiment: {sentiment}]",
            metadata={
                **message.metadata,
                "sentiment": sentiment,
                "sentiment_score": score
            }
        )


async def example_content_pipeline():
    """Example 1: Multi-language content processing pipeline."""
    print("\n=== Example 1: Content Processing Pipeline ===")
    print("Use case: Process multi-language customer feedback\n")
    print("Pipeline: Translation → Summarization → Sentiment Analysis")

    # Build pipeline
    pipeline = SequentialAgent(
        name="content-processor",
        agents=[
            TranslationAgent(),
            SummarizationAgent(),
            SentimentAgent()
        ]
    )

    # Test with French input
    french_input = Message(
        role="user",
        content="Bonjour. This product is amazing! The quality is excellent. "
                "Very happy with my purchase."
    )

    print("\nInput (French):")
    print(f"  {french_input.content}")

    result = await pipeline.process(french_input)

    print(f"\nOutput:")
    print(f"  {result.content}")
    print(f"\nMetadata:")
    print(f"  Source Language: {result.metadata.get('source_language')}")
    print(f"  Sentiment: {result.metadata.get('sentiment')}")
    print(f"  Sentiment Score: {result.metadata.get('sentiment_score'):.1f}")

    print("\n💡 Why Sequential?")
    print("   - Must translate BEFORE summarizing (order matters)")
    print("   - Each stage depends on previous stage's output")
    print("   - Clear data flow: raw → translated → summarized → analyzed")


# Example 2: Data Validation and Transformation
class ValidationAgent(Agent):
    """Validates input data meets requirements."""

    @property
    def name(self) -> str:
        return "validator"

    @property
    def capabilities(self) -> list[str]:
        return ["validation"]

    async def process(self, message: Message) -> Message:
        """Validate input meets requirements."""
        text = str(message.content)

        errors = []

        if len(text) < 10:
            errors.append("Text too short (min 10 chars)")

        if len(text) > 1000:
            errors.append("Text too long (max 1000 chars)")

        if not any(c.isalpha() for c in text):
            errors.append("Must contain letters")

        if errors:
            return Message(
                role="agent",
                content=f"VALIDATION FAILED: {'; '.join(errors)}",
                metadata={"valid": False, "errors": errors}
            )

        return Message(
            role="agent",
            content=text,
            metadata={"valid": True}
        )


class NormalizationAgent(Agent):
    """Normalizes text format."""

    @property
    def name(self) -> str:
        return "normalizer"

    @property
    def capabilities(self) -> list[str]:
        return ["normalization"]

    async def process(self, message: Message) -> Message:
        """Normalize text (only if valid)."""
        # Short-circuit if validation failed
        if not message.metadata.get("valid", True):
            return message

        text = str(message.content)

        # Normalize whitespace, trim, lowercase
        normalized = " ".join(text.split()).strip().lower()

        return Message(
            role="agent",
            content=normalized,
            metadata={**message.metadata, "normalized": True}
        )


class EnrichmentAgent(Agent):
    """Enriches data with additional information."""

    @property
    def name(self) -> str:
        return "enricher"

    @property
    def capabilities(self) -> list[str]:
        return ["enrichment"]

    async def process(self, message: Message) -> Message:
        """Add metadata (only if valid)."""
        # Short-circuit if validation failed
        if not message.metadata.get("valid", True):
            return message

        text = str(message.content)

        # Add statistics
        word_count = len(text.split())
        char_count = len(text)

        return Message(
            role="agent",
            content=text,
            metadata={
                **message.metadata,
                "word_count": word_count,
                "char_count": char_count,
                "enriched": True
            }
        )


async def example_validation_pipeline():
    """Example 2: Data validation and transformation pipeline."""
    print("\n=== Example 2: Validation Pipeline ===")
    print("Use case: ETL pipeline with validation and normalization\n")
    print("Pipeline: Validate → Normalize → Enrich")

    pipeline = SequentialAgent(
        name="etl-pipeline",
        agents=[
            ValidationAgent(),
            NormalizationAgent(),
            EnrichmentAgent()
        ]
    )

    # Test valid input
    print("\nTest 1: Valid input")
    valid_input = Message(
        role="user",
        content="  This is   VALID input   with  extra   spaces.  "
    )
    result = await pipeline.process(valid_input)
    print(f"  Input:  '{valid_input.content}'")
    print(f"  Output: '{result.content}'")
    print(f"  Valid:  {result.metadata.get('valid')}")
    print(f"  Words:  {result.metadata.get('word_count')}")

    # Test invalid input
    print("\nTest 2: Invalid input (too short)")
    invalid_input = Message(role="user", content="Hi")
    result = await pipeline.process(invalid_input)
    print(f"  Input:  '{invalid_input.content}'")
    print(f"  Output: '{result.content}'")
    print(f"  Valid:  {result.metadata.get('valid')}")

    print("\n💡 Why Sequential?")
    print("   - Validation must happen FIRST (fail fast)")
    print("   - Don't waste resources on invalid data")
    print("   - Each stage checks metadata to short-circuit")
    print("   - Clear separation: validate → normalize → enrich")


# Example 3: Multi-stage LLM Pipeline
class RouterAgent(Agent):
    """Routes requests to appropriate handler."""

    @property
    def name(self) -> str:
        return "router"

    @property
    def capabilities(self) -> list[str]:
        return ["routing"]

    async def process(self, message: Message) -> Message:
        """Classify request type."""
        text = str(message.content).lower()

        if "code" in text or "function" in text:
            request_type = "code"
        elif "translate" in text:
            request_type = "translation"
        elif "summarize" in text:
            request_type = "summarization"
        else:
            request_type = "general"

        return Message(
            role="agent",
            content=message.content,
            metadata={**message.metadata, "request_type": request_type}
        )


class ProcessorAgent(Agent):
    """Processes request based on type."""

    @property
    def name(self) -> str:
        return "processor"

    @property
    def capabilities(self) -> list[str]:
        return ["processing"]

    async def process(self, message: Message) -> Message:
        """Process based on request type."""
        request_type = message.metadata.get("request_type", "general")

        await asyncio.sleep(0.1)  # Simulate processing

        responses = {
            "code": "Here's the code implementation: ...",
            "translation": "Translation: ...",
            "summarization": "Summary: ...",
            "general": "General response: ..."
        }

        response = responses.get(request_type, "Response: ...")

        return Message(
            role="agent",
            content=response,
            metadata={**message.metadata, "processed": True}
        )


class FormatterAgent(Agent):
    """Formats output for user."""

    @property
    def name(self) -> str:
        return "formatter"

    @property
    def capabilities(self) -> list[str]:
        return ["formatting"]

    async def process(self, message: Message) -> Message:
        """Format output nicely."""
        request_type = message.metadata.get("request_type", "general")
        content = str(message.content)

        formatted = f"[{request_type.upper()}]\n{content}"

        return Message(
            role="agent",
            content=formatted,
            metadata={**message.metadata, "formatted": True}
        )


async def example_llm_pipeline():
    """Example 3: Multi-stage LLM request pipeline."""
    print("\n=== Example 3: LLM Request Pipeline ===")
    print("Use case: Intelligent request routing and formatting\n")
    print("Pipeline: Route → Process → Format")

    pipeline = SequentialAgent(
        name="llm-pipeline",
        agents=[
            RouterAgent(),
            ProcessorAgent(),
            FormatterAgent()
        ]
    )

    test_queries = [
        "Write a function to calculate factorial",
        "Summarize this article",
        "How are you today?"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        result = await pipeline.process(Message(role="user", content=query))
        print(f"Type: {result.metadata.get('request_type')}")
        print(f"Response:\n{result.content}")

    print("\n💡 Why Sequential?")
    print("   - Routing determines processing strategy")
    print("   - Processing creates content")
    print("   - Formatting presents it to user")
    print("   - Natural flow: classify → execute → present")


async def example_error_handling():
    """Example 4: Error handling in pipelines."""
    print("\n=== Example 4: Error Handling in Pipelines ===")
    print("Use case: Graceful degradation with error handling\n")

    class FailingAgent(Agent):
        """Agent that sometimes fails."""

        def __init__(self, name: str, fail_on: str):
            self._name = name
            self.fail_on = fail_on

        @property
        def name(self) -> str:
            return self._name

        @property
        def capabilities(self) -> list[str]:
            return []

        async def process(self, message: Message) -> Message:
            if self.fail_on in str(message.content).lower():
                raise Exception(f"{self._name} failed on '{self.fail_on}'")
            return Message(
                role="agent",
                content=f"{message.content} -> {self._name}",
                metadata={**message.metadata, self._name: True}
            )

    pipeline = SequentialAgent(
        name="error-test",
        agents=[
            FailingAgent("stage1", "error1"),
            FailingAgent("stage2", "error2"),
            FailingAgent("stage3", "error3")
        ]
    )

    # Test successful case
    print("Test 1: Success path")
    try:
        result = await pipeline.process(Message(role="user", content="good"))
        print(f"  ✅ Success: {result.content}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")

    # Test failure at stage 2
    print("\nTest 2: Failure at stage 2")
    try:
        result = await pipeline.process(Message(role="user", content="error2"))
        print(f"  ✅ Success: {result.content}")
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print(f"     Pipeline stopped at failing stage")

    print("\n💡 Error Handling Strategy:")
    print("   - Sequential pipelines stop at first error (fail-fast)")
    print("   - Use try/except around pipeline for recovery")
    print("   - Consider FallbackAgent for automatic retries")
    print("   - Add validation early to catch errors before processing")


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("SEQUENTIAL COMPOSITION EXAMPLES")
    print("="*70)
    print("\nSequential composition is the foundation of data pipelines.")
    print("Use it when stages depend on each other's output.\n")

    await example_content_pipeline()
    await example_validation_pipeline()
    await example_llm_pipeline()
    await example_error_handling()

    print("\n" + "="*70)
    print("KEY TAKEAWAYS")
    print("="*70)
    print("""
1. Use sequential composition when:
   - Stages depend on previous stage's output
   - Order of operations matters
   - Building data transformation pipelines
   - Need clear, linear data flow

2. Design principles:
   - Each agent does ONE thing well
   - Validate early (fail fast on bad input)
   - Use metadata to pass context between stages
   - Short-circuit on errors to avoid wasted work

3. Performance considerations:
   - Total latency = sum of all stages
   - Optimize the slowest stage first
   - Consider caching for repeated inputs
   - Move validation/filtering earlier

4. When NOT to use:
   - Independent operations → Use ParallelAgent
   - Conditional routing → Use ConditionalAgent
   - Need fallback options → Use FallbackAgent

5. Real-world patterns:
   - ETL: Extract → Transform → Load
   - Content: Moderate → Process → Format
   - API: Authenticate → Authorize → Execute → Format
   - ML: Preprocess → Predict → Postprocess

TRADE-OFF SUMMARY:
✅ Pros: Simple, clear, testable, composable
❌ Cons: Sequential latency, no parallelism
🎯 Choose when: Clarity and correctness > maximum throughput
    """)


if __name__ == "__main__":
    asyncio.run(main())
