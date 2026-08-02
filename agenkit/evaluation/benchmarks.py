"""
Benchmark suites for agent evaluation.

Provides standard benchmarks and extreme-scale tests (1M-25M tokens).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestCase:
    """
    Single test case for evaluation.

    Contains input, expected output, and metadata.
    """

    input: str
    expected: Any  # String, callable, or validation function
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "input": self.input,
            "expected": self.expected if not callable(self.expected) else "<function>",
            "metadata": self.metadata,
            "tags": self.tags,
        }


class Benchmark(ABC):
    """
    Base class for benchmarks.

    Benchmarks define test suites for evaluating specific capabilities.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Benchmark name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Benchmark description."""
        pass

    @abstractmethod
    async def generate_test_cases(self) -> list[TestCase]:
        """
        Generate test cases for this benchmark.

        Returns:
            List of test cases
        """
        pass


class SimpleQABenchmark(Benchmark):
    """
    Simple question-answering benchmark.

    Tests basic knowledge and reasoning.
    """

    @property
    def name(self) -> str:
        return "simple_qa"

    @property
    def description(self) -> str:
        return "Basic question-answering tasks"

    async def generate_test_cases(self) -> list[TestCase]:
        """Generate simple Q&A test cases."""
        return [
            TestCase(input="What is 2+2?", expected="4", tags=["math", "easy"]),
            TestCase(
                input="What is the capital of France?", expected="Paris", tags=["knowledge", "easy"]
            ),
            TestCase(
                input="What is the largest planet in our solar system?",
                expected="Jupiter",
                tags=["knowledge", "easy"],
            ),
            TestCase(
                input="If a train leaves at 2pm and travels for 3 hours, when does it arrive?",
                expected="5",  # "5pm" or "5:00pm" both match
                tags=["reasoning", "easy"],
            ),
            TestCase(
                input="What comes next in the sequence: 2, 4, 6, 8, ?",
                expected="10",
                tags=["reasoning", "easy"],
            ),
        ]


class NeedleInHaystackBenchmark(Benchmark):
    """
    Needle-in-haystack benchmark for context retrieval.

    Tests ability to retrieve specific information from large contexts.
    Essential for extreme-scale systems like endless.
    """

    def __init__(self, context_length: int = 10_000, needle_count: int = 5):
        """
        Initialize needle-in-haystack benchmark.

        Args:
            context_length: Target context length in tokens
            needle_count: Number of needles to hide
        """
        self.context_length = context_length
        self.needle_count = needle_count

    @property
    def name(self) -> str:
        return f"needle_in_haystack_{self.context_length}"

    @property
    def description(self) -> str:
        return f"Retrieve {self.needle_count} facts from {self.context_length} token context"

    async def generate_test_cases(self) -> list[TestCase]:
        """Generate needle-in-haystack test cases."""
        test_cases = []

        # Generate needles (specific facts to retrieve)
        needles = [
            f"The secret code for vault {i} is ALPHA-{i:04d}-OMEGA."
            for i in range(self.needle_count)
        ]

        # Generate haystack (filler content)
        haystack = self._generate_haystack(self.context_length)

        # Embed needles at random positions
        context = self._embed_needles(haystack, needles)

        # Create test cases asking for each needle
        for i, _needle in enumerate(needles):
            test_cases.append(
                TestCase(
                    input=f"Context: {context}\n\nQuestion: What is the secret code for vault {i}?",
                    expected=f"ALPHA-{i:04d}-OMEGA",
                    metadata={
                        "context_length": len(context.split()) // 4,  # Rough token estimate
                        "needle_position": i,
                        "total_needles": self.needle_count,
                    },
                    tags=["retrieval", "context", f"length_{self.context_length}"],
                )
            )

        return test_cases

    def _generate_haystack(self, target_tokens: int) -> str:
        """Generate filler content for haystack."""
        # Simple filler paragraphs
        paragraphs = [
            "This is a paragraph of filler content. It contains general information that is not relevant to the specific queries we will ask. "
            "The purpose of this content is to create a large context that the agent must search through. ",
            "Here is another paragraph with different content. It discusses various topics without providing the specific information we're looking for. "
            "This helps test the agent's ability to find needles in haystacks. ",
            "Additional filler text to expand the context. This paragraph talks about unrelated subjects and serves to increase the total context length. "
            "The agent must be able to filter through this content efficiently. ",
        ]

        # Repeat paragraphs to reach target length
        haystack = ""
        tokens_per_paragraph = sum(len(p.split()) for p in paragraphs)
        repetitions = (target_tokens // tokens_per_paragraph) + 1

        for _ in range(repetitions):
            for paragraph in paragraphs:
                haystack += paragraph

        return haystack

    def _embed_needles(self, haystack: str, needles: list[str]) -> str:
        """Embed needles at regular intervals in haystack."""
        words = haystack.split()
        interval = len(words) // (len(needles) + 1)

        embedded = []
        needle_idx = 0

        for i, word in enumerate(words):
            # Insert needle at intervals
            if needle_idx < len(needles) and i == interval * (needle_idx + 1):
                embedded.append(needles[needle_idx])
                needle_idx += 1
            embedded.append(word)

        return " ".join(embedded)


class ExtremeScaleBenchmark(Benchmark):
    """
    Extreme-scale benchmark for testing at 1M-25M+ tokens.

    Designed specifically for endless and similar systems that
    operate at unprecedented context lengths.
    """

    def __init__(self, test_lengths: list[int] | None = None, needles_per_length: int = 10):
        """
        Initialize extreme-scale benchmark.

        Args:
            test_lengths: Context lengths to test (defaults to 1M, 10M, 25M)
            needles_per_length: Number of needles per context length
        """
        self.test_lengths = test_lengths or [
            1_000_000,  # 1M tokens
            10_000_000,  # 10M tokens
            25_000_000,  # 25M tokens (endless scale)
        ]
        self.needles_per_length = needles_per_length

    @property
    def name(self) -> str:
        return "extreme_scale"

    @property
    def description(self) -> str:
        max_length = max(self.test_lengths) // 1_000_000
        return f"Test retrieval and quality at 1M-{max_length}M tokens"

    async def generate_test_cases(self) -> list[TestCase]:
        """Generate extreme-scale test cases."""
        test_cases = []

        for length in self.test_lengths:
            # Create needle-in-haystack tests at this scale
            benchmark = NeedleInHaystackBenchmark(
                context_length=length, needle_count=self.needles_per_length
            )

            cases = await benchmark.generate_test_cases()

            # Tag with scale
            for case in cases:
                case.tags.append("extreme_scale")
                case.tags.append(f"scale_{length // 1_000_000}M")
                case.metadata["benchmark"] = "extreme_scale"

            test_cases.extend(cases)

        return test_cases


class InformationRetentionBenchmark(Benchmark):
    """
    Test information retention across long conversations.

    Verifies that agents remember and can recall information
    from earlier in the conversation, even after compression.
    """

    def __init__(self, conversation_length: int = 100, recall_points: list[int] | None = None):
        """
        Initialize information retention benchmark.

        Args:
            conversation_length: Number of conversation turns
            recall_points: Turns at which to test recall (defaults to checkpoints)
        """
        self.conversation_length = conversation_length
        self.recall_points = recall_points or [10, 25, 50, 75, 100]

    @property
    def name(self) -> str:
        return "information_retention"

    @property
    def description(self) -> str:
        return f"Test recall of facts across {self.conversation_length} turns"

    async def generate_test_cases(self) -> list[TestCase]:
        """Generate information retention test cases."""
        test_cases = []

        # Plant facts at regular intervals
        facts = [
            ("favorite_color", "blue", "My favorite color is blue."),
            ("birth_city", "Paris", "I was born in Paris."),
            ("occupation", "engineer", "I work as an engineer."),
            ("pet_name", "Max", "My dog's name is Max."),
            ("hobby", "painting", "I enjoy painting in my free time."),
        ]

        # Create conversation with embedded facts
        for turn in range(self.conversation_length):
            # Plant fact every 20 turns
            if turn > 0 and turn % 20 == 0 and len(facts) > 0:
                fact_key, fact_value, fact_statement = facts.pop(0)

                test_cases.append(
                    TestCase(
                        input=fact_statement,
                        expected="I'll remember that",  # Acknowledgment
                        metadata={
                            "turn": turn,
                            "type": "fact_plant",
                            "fact_key": fact_key,
                            "fact_value": fact_value,
                        },
                        tags=["retention", "plant"],
                    )
                )

            # Test recall at checkpoints
            if turn in self.recall_points:
                # Ask about a previously planted fact
                # For now, just add filler
                test_cases.append(
                    TestCase(
                        input="What's the weather like?",
                        expected=lambda msg: len(str(msg.content)) > 0,  # Any response
                        metadata={"turn": turn, "type": "filler"},
                        tags=["retention", "filler"],
                    )
                )

        # Final recall tests
        # Ask about all planted facts
        fact_questions = [
            ("favorite_color", "blue", "What did I say my favorite color was?"),
            ("birth_city", "Paris", "Where did I tell you I was born?"),
            ("occupation", "engineer", "What is my occupation?"),
            ("pet_name", "Max", "What is my dog's name?"),
            ("hobby", "painting", "What hobby did I mention?"),
        ]

        for fact_key, expected_value, question in fact_questions:
            test_cases.append(
                TestCase(
                    input=question,
                    expected=expected_value,
                    metadata={
                        "turn": self.conversation_length,
                        "type": "recall_test",
                        "fact_key": fact_key,
                    },
                    tags=["retention", "recall"],
                )
            )

        return test_cases


class BenchmarkSuite:
    """
    Collection of benchmarks for comprehensive evaluation.

    Provides standard and extreme-scale benchmark suites.
    """

    def __init__(self, benchmarks: list[Benchmark] | None = None, name: str = "custom"):
        """
        Initialize benchmark suite.

        Args:
            benchmarks: List of benchmarks to include
            name: Suite name
        """
        self.benchmarks = benchmarks or []
        self.suite_name = name

    @classmethod
    def standard(cls) -> "BenchmarkSuite":
        """
        Standard benchmark suite.

        Includes basic Q&A and small-scale retrieval tests.
        """
        return cls(
            benchmarks=[
                SimpleQABenchmark(),
                NeedleInHaystackBenchmark(context_length=10_000),
                InformationRetentionBenchmark(conversation_length=50),
            ],
            name="standard",
        )

    @classmethod
    def extreme_scale(cls) -> "BenchmarkSuite":
        """
        Extreme-scale benchmark suite for endless.

        Tests at 1M-25M+ tokens with compression and retrieval.
        """
        return cls(
            benchmarks=[
                ExtremeScaleBenchmark(
                    test_lengths=[1_000_000, 10_000_000, 25_000_000], needles_per_length=10
                ),
                InformationRetentionBenchmark(conversation_length=1000),
            ],
            name="extreme_scale",
        )

    @classmethod
    def quick(cls) -> "BenchmarkSuite":
        """
        Quick benchmark suite for fast iteration.

        Small test set for rapid feedback during development.
        """
        return cls(
            benchmarks=[
                SimpleQABenchmark(),
                NeedleInHaystackBenchmark(context_length=1_000, needle_count=3),
            ],
            name="quick",
        )

    async def generate_all_test_cases(self) -> list[TestCase]:
        """
        Generate all test cases from all benchmarks.

        Returns:
            Combined list of test cases from all benchmarks
        """
        all_cases = []

        for benchmark in self.benchmarks:
            cases = await benchmark.generate_test_cases()
            # Tag with benchmark name
            for case in cases:
                case.metadata["benchmark_name"] = benchmark.name
                case.metadata["suite_name"] = self.suite_name
            all_cases.extend(cases)

        return all_cases

    def get_benchmark(self, name: str) -> Benchmark | None:
        """Get benchmark by name."""
        for benchmark in self.benchmarks:
            if benchmark.name == name:
                return benchmark
        return None

    def add_benchmark(self, benchmark: Benchmark) -> None:
        """Add benchmark to suite."""
        self.benchmarks.append(benchmark)

    def remove_benchmark(self, name: str) -> None:
        """Remove benchmark from suite."""
        self.benchmarks = [b for b in self.benchmarks if b.name != name]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "suite_name": self.suite_name,
            "benchmarks": [{"name": b.name, "description": b.description} for b in self.benchmarks],
        }
