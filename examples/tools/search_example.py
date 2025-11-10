"""
Search Tool Examples for Agenkit

This example demonstrates WHY and HOW to use search tools with agents,
covering real-world scenarios like web search, multi-source aggregation,
and search result processing.

WHY USE SEARCH TOOLS?
--------------------
- **Real-time information**: LLMs have knowledge cutoff; search provides current data
- **Factual grounding**: Search results reduce hallucination by providing sources
- **Broad coverage**: Access to web, documents, databases beyond training data
- **Source attribution**: Search provides URLs and citations for verification

WHEN TO USE:
- Current events and news
- Product information and reviews
- Research and fact-checking
- Document retrieval
- Q&A systems requiring sources

WHEN NOT TO USE:
- Questions within LLM's training knowledge
- Queries requiring reasoning over multiple sources
- Private/sensitive information not indexed
- When offline operation is required

TRADE-OFFS:
- Accuracy: Search provides sources but results may be outdated/irrelevant
- Latency: 100-1000ms per search vs instant LLM recall
- Cost: API fees for search services (e.g., $5-25/1000 queries)
- Reliability: Depends on external service availability
- Privacy: Queries sent to third-party services

"""

import asyncio
import hashlib
import time
from typing import List, Dict, Optional, Literal
from dataclasses import dataclass
import httpx
from agenkit import Agent
from agenkit.tools import Tool, ToolRegistry


# ============================================================================
# MOCK SEARCH SERVICE (Replace with real API in production)
# ============================================================================

@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str = "web"
    relevance_score: float = 0.0


class MockSearchService:
    """
    Mock search service for demonstration.

    In production, replace with:
    - Google Custom Search API
    - Bing Search API
    - Brave Search API
    - Elasticsearch
    - Algolia
    """

    def __init__(self, latency_ms: int = 200):
        self.latency_ms = latency_ms
        self.call_count = 0

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Simulate search API call."""
        await asyncio.sleep(self.latency_ms / 1000)
        self.call_count += 1

        # Mock results based on query
        return [
            SearchResult(
                title=f"Result {i+1} for '{query}'",
                url=f"https://example.com/{i+1}",
                snippet=f"This is a relevant snippet about {query}...",
                source="web",
                relevance_score=1.0 - (i * 0.1)
            )
            for i in range(min(max_results, 5))
        ]


# ============================================================================
# BASIC SEARCH TOOL
# ============================================================================

class WebSearchTool:
    """
    Basic web search tool.

    WHY: LLMs can't access real-time information or current events.
    Search tools bridge the knowledge gap between training cutoff and present.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.service = MockSearchService()

    async def search(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, str]]:
        """
        Search the web for query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of search results with title, url, and snippet
        """
        results = await self.service.search(query, max_results)

        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet
            }
            for r in results
        ]


# ============================================================================
# EXAMPLE 1: Basic Web Search
# ============================================================================

async def example1_basic_search():
    """
    Demonstrate basic web search with an agent.

    WHY: Agents need current information beyond their training data.
    HOW: Tool provides search capability; LLM synthesizes results.

    TRADE-OFFS:
    - Pros: Access to current information, source attribution
    - Cons: 200ms+ latency, depends on external service
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Web Search")
    print("="*80)

    # Create search tool
    search_tool = WebSearchTool()

    # Create tool definition
    tool = Tool(
        name="web_search",
        description="Search the web for current information",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "default": 10
                }
            },
            "required": ["query"]
        },
        function=search_tool.search
    )

    # Register tool
    registry = ToolRegistry()
    registry.register(tool)

    # Create agent with search capability
    agent = Agent(
        name="SearchAgent",
        instructions="You are a helpful assistant with web search capabilities. "
                    "When asked about current information, use the web_search tool.",
        tools=registry
    )

    # Query requiring current information
    query = "What are the latest developments in AI research?"
    print(f"\nUser Query: {query}")

    # Agent uses search tool
    results = await search_tool.search(query, max_results=5)

    print(f"\nSearch Results ({len(results)} found):")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   {result['snippet']}")

    print("\n💡 KEY INSIGHT:")
    print("   Search tools extend LLM knowledge with real-time information.")
    print("   Agent can now answer questions about current events.")


# ============================================================================
# EXAMPLE 2: Multi-Source Search (Parallel)
# ============================================================================

class MultiSourceSearchTool:
    """
    Search multiple sources in parallel.

    WHY: Different sources provide different perspectives and coverage.
    Parallel execution reduces latency.
    """

    def __init__(self):
        self.web_search = MockSearchService(latency_ms=200)
        self.news_search = MockSearchService(latency_ms=150)
        self.academic_search = MockSearchService(latency_ms=300)

    async def search_all(
        self,
        query: str,
        max_results_per_source: int = 5
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Search multiple sources in parallel.

        TRADE-OFFS:
        - Latency: max(sources) = 300ms vs sum(sources) = 650ms
        - Coverage: 3× results but 3× cost
        - Reliability: Partial results if one source fails
        """
        # Search all sources concurrently
        web_task = self.web_search.search(query, max_results_per_source)
        news_task = self.news_search.search(query, max_results_per_source)
        academic_task = self.academic_search.search(query, max_results_per_source)

        web_results, news_results, academic_results = await asyncio.gather(
            web_task,
            news_task,
            academic_task,
            return_exceptions=True  # Don't fail if one source fails
        )

        # Handle failures gracefully
        results = {}

        if not isinstance(web_results, Exception):
            results["web"] = [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in web_results
            ]

        if not isinstance(news_results, Exception):
            results["news"] = [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in news_results
            ]

        if not isinstance(academic_results, Exception):
            results["academic"] = [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in academic_results
            ]

        return results


async def example2_multi_source_search():
    """
    Demonstrate parallel search across multiple sources.

    WHY: Single source may miss relevant information.
    Multiple sources provide broader coverage and different perspectives.

    TRADE-OFFS:
    - Better coverage vs higher cost (3× API calls)
    - Latency = max(sources) when parallel (300ms vs 650ms sequential)
    - Graceful degradation if one source fails
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Multi-Source Search (Parallel)")
    print("="*80)

    search_tool = MultiSourceSearchTool()

    query = "climate change solutions 2025"
    print(f"\nQuery: {query}")

    # Measure parallel execution time
    start = time.time()
    results = await search_tool.search_all(query, max_results_per_source=3)
    elapsed = time.time() - start

    print(f"\n✓ Retrieved results from {len(results)} sources in {elapsed*1000:.0f}ms")

    for source, source_results in results.items():
        print(f"\n{source.upper()} ({len(source_results)} results):")
        for i, result in enumerate(source_results, 1):
            print(f"  {i}. {result['title']}")

    print("\n💡 KEY INSIGHT:")
    print(f"   Parallel execution: {elapsed*1000:.0f}ms total")
    print("   Sequential would take: ~650ms (200+150+300)")
    print("   Speedup: 2.2× faster with parallel execution")


# ============================================================================
# EXAMPLE 3: Search with Ranking and Filtering
# ============================================================================

class RankedSearchTool:
    """
    Search with result ranking and filtering.

    WHY: Raw search results often contain noise and irrelevant results.
    Ranking and filtering improve result quality.
    """

    def __init__(self):
        self.service = MockSearchService()

    async def search_ranked(
        self,
        query: str,
        max_results: int = 10,
        min_relevance: float = 0.5,
        preferred_domains: Optional[List[str]] = None
    ) -> List[Dict[str, any]]:
        """
        Search with relevance ranking and domain filtering.

        Args:
            query: Search query
            max_results: Maximum results
            min_relevance: Minimum relevance score (0.0-1.0)
            preferred_domains: Boost results from these domains

        Returns:
            Ranked and filtered search results
        """
        # Get raw results
        results = await self.service.search(query, max_results * 2)

        # Filter by relevance
        filtered = [r for r in results if r.relevance_score >= min_relevance]

        # Boost preferred domains
        if preferred_domains:
            for result in filtered:
                for domain in preferred_domains:
                    if domain in result.url:
                        result.relevance_score *= 1.5

        # Sort by relevance
        filtered.sort(key=lambda r: r.relevance_score, reverse=True)

        # Return top results
        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "relevance": r.relevance_score
            }
            for r in filtered[:max_results]
        ]


async def example3_ranked_search():
    """
    Demonstrate search with ranking and filtering.

    WHY: Raw search results often contain low-quality or irrelevant content.
    Ranking and filtering improve signal-to-noise ratio.

    TRADE-OFFS:
    - Quality: Higher relevance threshold means fewer but better results
    - Latency: Ranking adds ~10-50ms processing overhead
    - Complexity: More configuration options for users
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Search with Ranking and Filtering")
    print("="*80)

    search_tool = RankedSearchTool()

    query = "Python asyncio best practices"
    print(f"\nQuery: {query}")

    # Search with domain preferences
    results = await search_tool.search_ranked(
        query,
        max_results=5,
        min_relevance=0.6,
        preferred_domains=["stackoverflow.com", "python.org", "realpython.com"]
    )

    print(f"\n✓ Found {len(results)} high-quality results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']} (relevance: {result['relevance']:.2f})")
        print(f"   {result['url']}")
        print(f"   {result['snippet']}")

    print("\n💡 KEY INSIGHT:")
    print("   Ranking and filtering improve result quality.")
    print("   Preferred domains get relevance boost.")
    print("   Min relevance threshold filters low-quality results.")


# ============================================================================
# EXAMPLE 4: Semantic Search
# ============================================================================

class SemanticSearchTool:
    """
    Semantic search using embeddings.

    WHY: Keyword search misses semantically similar content.
    Embeddings capture meaning for better retrieval.
    """

    def __init__(self):
        self.service = MockSearchService()
        # In production, use real embeddings (OpenAI, Cohere, etc.)
        self.cache = {}

    def _compute_embedding(self, text: str) -> List[float]:
        """
        Compute text embedding.

        In production, use:
        - OpenAI embeddings (text-embedding-3-small)
        - Cohere embeddings
        - Sentence transformers
        """
        # Mock embedding (hash-based for demo)
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [float((hash_val >> i) & 0xFF) / 255.0 for i in range(0, 128, 8)]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between embeddings."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        return dot_product / (norm_a * norm_b) if norm_a and norm_b else 0.0

    async def search_semantic(
        self,
        query: str,
        max_results: int = 10,
        min_similarity: float = 0.7
    ) -> List[Dict[str, any]]:
        """
        Search using semantic similarity.

        TRADE-OFFS:
        - Better recall of semantically similar content
        - Higher latency (~100ms for embedding + search)
        - Higher cost (embedding API + storage)
        """
        # Compute query embedding
        query_embedding = self._compute_embedding(query)

        # Get candidate results
        results = await self.service.search(query, max_results * 2)

        # Compute similarity scores
        scored_results = []
        for result in results:
            # Compute embedding for result
            result_text = f"{result.title} {result.snippet}"
            result_embedding = self._compute_embedding(result_text)

            # Compute similarity
            similarity = self._cosine_similarity(query_embedding, result_embedding)

            if similarity >= min_similarity:
                scored_results.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "similarity": similarity
                })

        # Sort by similarity
        scored_results.sort(key=lambda r: r["similarity"], reverse=True)

        return scored_results[:max_results]


async def example4_semantic_search():
    """
    Demonstrate semantic search using embeddings.

    WHY: Keyword search misses semantically similar results.
    Example: "car" and "automobile" are semantically similar but different keywords.

    TRADE-OFFS:
    - Better recall: Finds semantically similar content
    - Higher latency: ~100ms for embedding generation
    - Higher cost: Embedding API fees (~$0.10/1M tokens)
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Semantic Search")
    print("="*80)

    search_tool = SemanticSearchTool()

    query = "How to write asynchronous code in Python?"
    print(f"\nQuery: {query}")

    results = await search_tool.search_semantic(
        query,
        max_results=5,
        min_similarity=0.5
    )

    print(f"\n✓ Found {len(results)} semantically similar results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['title']} (similarity: {result['similarity']:.2f})")
        print(f"   {result['url']}")

    print("\n💡 KEY INSIGHT:")
    print("   Semantic search finds results with similar *meaning*.")
    print("   Example: 'async code' matches 'asyncio', 'concurrent', 'parallel'")
    print("   Better than keyword matching for natural language queries.")


# ============================================================================
# EXAMPLE 5: Search with Fallback
# ============================================================================

class ResilientSearchTool:
    """
    Search with fallback sources for high availability.

    WHY: External search APIs may fail or be rate-limited.
    Fallbacks ensure reliable service.
    """

    def __init__(self):
        self.primary = MockSearchService(latency_ms=200)
        self.secondary = MockSearchService(latency_ms=300)
        self.cache = {}

    async def search_with_fallback(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, any]:
        """
        Search with fallback to secondary source.

        TRADE-OFFS:
        - Higher availability (99.9% vs 99%)
        - Slower on primary failure (200ms + 300ms)
        - More complex error handling
        """
        # Check cache first
        cache_key = hashlib.md5(f"{query}:{max_results}".encode()).hexdigest()
        if cache_key in self.cache:
            return {
                "results": self.cache[cache_key],
                "source": "cache",
                "latency_ms": 0
            }

        # Try primary search
        start = time.time()
        try:
            results = await asyncio.wait_for(
                self.primary.search(query, max_results),
                timeout=2.0
            )
            latency = (time.time() - start) * 1000

            # Cache results
            result_dicts = [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in results
            ]
            self.cache[cache_key] = result_dicts

            return {
                "results": result_dicts,
                "source": "primary",
                "latency_ms": latency
            }
        except Exception as e:
            print(f"   ⚠ Primary search failed: {e}")

            # Fallback to secondary
            try:
                results = await asyncio.wait_for(
                    self.secondary.search(query, max_results),
                    timeout=3.0
                )
                latency = (time.time() - start) * 1000

                result_dicts = [
                    {"title": r.title, "url": r.url, "snippet": r.snippet}
                    for r in results
                ]

                return {
                    "results": result_dicts,
                    "source": "secondary",
                    "latency_ms": latency
                }
            except Exception as e2:
                print(f"   ⚠ Secondary search failed: {e2}")

                # Return cached results if available
                if cache_key in self.cache:
                    return {
                        "results": self.cache[cache_key],
                        "source": "stale_cache",
                        "latency_ms": (time.time() - start) * 1000
                    }

                # No results available
                return {
                    "results": [],
                    "source": "none",
                    "latency_ms": (time.time() - start) * 1000,
                    "error": "All search sources failed"
                }


async def example5_search_with_fallback():
    """
    Demonstrate search with fallback for high availability.

    WHY: External APIs may fail, be rate-limited, or slow.
    Fallbacks ensure reliable service (99.9% vs 99% availability).

    TRADE-OFFS:
    - Higher availability: Primary fails → use secondary → use cache
    - Slower on failure: 200ms (primary) + 300ms (secondary) = 500ms
    - Stale data risk: Cache may be outdated
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Search with Fallback")
    print("="*80)

    search_tool = ResilientSearchTool()

    query = "machine learning tutorials"
    print(f"\nQuery: {query}")

    # First search (cache miss, use primary)
    print("\n--- First Search (cache miss) ---")
    result = await search_tool.search_with_fallback(query, max_results=3)

    print(f"✓ Source: {result['source']}")
    print(f"✓ Latency: {result['latency_ms']:.0f}ms")
    print(f"✓ Results: {len(result['results'])}")

    # Second search (cache hit)
    print("\n--- Second Search (cache hit) ---")
    result = await search_tool.search_with_fallback(query, max_results=3)

    print(f"✓ Source: {result['source']}")
    print(f"✓ Latency: {result['latency_ms']:.0f}ms")
    print(f"✓ Results: {len(result['results'])}")

    print("\n💡 KEY INSIGHT:")
    print("   Fallback chain: Primary → Secondary → Cache → Error")
    print("   Cache provides instant results (0ms) for repeated queries")
    print("   High availability: Service continues even if primary fails")


# ============================================================================
# EXAMPLE 6: Rate-Limited Search
# ============================================================================

class RateLimitedSearchTool:
    """
    Search tool with rate limiting.

    WHY: Search APIs have rate limits (e.g., 100 requests/day).
    Rate limiting prevents quota exhaustion and API bans.
    """

    def __init__(self, max_calls_per_minute: int = 10):
        self.service = MockSearchService()
        self.max_calls = max_calls_per_minute
        self.call_timestamps = []

    async def search_rate_limited(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, any]:
        """
        Search with rate limiting.

        TRADE-OFFS:
        - Prevents quota exhaustion and API bans
        - May reject requests during high traffic
        - Adds ~1ms overhead for rate limit check
        """
        now = time.time()

        # Remove old timestamps (outside window)
        self.call_timestamps = [
            ts for ts in self.call_timestamps
            if now - ts < 60  # Keep last minute
        ]

        # Check rate limit
        if len(self.call_timestamps) >= self.max_calls:
            oldest = self.call_timestamps[0]
            wait_time = 60 - (now - oldest)
            return {
                "results": [],
                "error": "Rate limit exceeded",
                "retry_after_seconds": wait_time
            }

        # Record call
        self.call_timestamps.append(now)

        # Execute search
        results = await self.service.search(query, max_results)

        return {
            "results": [
                {"title": r.title, "url": r.url, "snippet": r.snippet}
                for r in results
            ],
            "calls_remaining": self.max_calls - len(self.call_timestamps)
        }


async def example6_rate_limited_search():
    """
    Demonstrate rate-limited search.

    WHY: Search APIs have quotas (e.g., 100/day, 10/minute).
    Rate limiting prevents quota exhaustion and account suspension.

    TRADE-OFFS:
    - Prevents API bans and overage charges
    - May reject requests during traffic spikes
    - Minimal overhead (~1ms per request)
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Rate-Limited Search")
    print("="*80)

    search_tool = RateLimitedSearchTool(max_calls_per_minute=5)

    print("\nSimulating 7 searches (limit: 5/minute):")

    for i in range(7):
        result = await search_tool.search_rate_limited(
            f"query {i+1}",
            max_results=3
        )

        if "error" in result:
            print(f"\n  {i+1}. ⚠ Rate limit exceeded")
            print(f"     Retry after: {result['retry_after_seconds']:.1f}s")
        else:
            print(f"\n  {i+1}. ✓ Search successful")
            print(f"     Calls remaining: {result['calls_remaining']}")

    print("\n💡 KEY INSIGHT:")
    print("   Rate limiting protects against quota exhaustion.")
    print("   First 5 requests succeed, remaining are rejected.")
    print("   Alternative: Queue requests instead of rejecting.")


# ============================================================================
# EXAMPLE 7: Error Handling
# ============================================================================

async def example7_error_handling():
    """
    Demonstrate comprehensive error handling for search tools.

    WHY: External APIs fail in many ways:
    - Network errors (timeout, connection refused)
    - API errors (rate limit, invalid key, service down)
    - Data errors (invalid response format)

    TRADE-OFFS:
    - Robustness: Graceful error handling vs fail-fast
    - User experience: Detailed errors vs generic messages
    - Debugging: Logging vs privacy
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Error Handling")
    print("="*80)

    class ErrorHandlingSearchTool:
        """Search tool with comprehensive error handling."""

        async def search(self, query: str) -> Dict[str, any]:
            """Search with error handling."""
            try:
                # Validate input
                if not query or not query.strip():
                    return {
                        "success": False,
                        "error": "Query cannot be empty",
                        "error_type": "validation_error"
                    }

                # Simulate API call
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(
                            "https://api.example.com/search",
                            params={"q": query},
                            timeout=5.0
                        )
                        response.raise_for_status()

                        return {
                            "success": True,
                            "results": response.json()
                        }
                    except httpx.TimeoutException:
                        return {
                            "success": False,
                            "error": "Search request timed out",
                            "error_type": "timeout_error"
                        }
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 429:
                            return {
                                "success": False,
                                "error": "Rate limit exceeded",
                                "error_type": "rate_limit_error",
                                "retry_after": e.response.headers.get("Retry-After")
                            }
                        elif e.response.status_code == 401:
                            return {
                                "success": False,
                                "error": "Invalid API key",
                                "error_type": "auth_error"
                            }
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP error: {e.response.status_code}",
                                "error_type": "http_error"
                            }
            except Exception as e:
                # Catch-all for unexpected errors
                return {
                    "success": False,
                    "error": "Unexpected error occurred",
                    "error_type": "unknown_error"
                }

    search_tool = ErrorHandlingSearchTool()

    # Test various error scenarios
    test_cases = [
        ("valid query", "This would succeed in production"),
        ("", "Empty query should fail validation"),
        ("timeout query", "Would timeout in production"),
        ("rate limit query", "Would hit rate limit")
    ]

    print("\nTesting error handling:")
    for query, description in test_cases:
        result = await search_tool.search(query)
        status = "✓" if result.get("success") else "✗"
        error_type = result.get("error_type", "none")
        print(f"\n  {status} {description}")
        print(f"     Error type: {error_type}")

    print("\n💡 KEY INSIGHT:")
    print("   Comprehensive error handling improves reliability:")
    print("   - Validation errors: Catch before API call")
    print("   - Timeout errors: Set reasonable timeouts (5s)")
    print("   - Rate limit errors: Provide retry_after info")
    print("   - Auth errors: Check API key validity")
    print("   - Unknown errors: Catch-all for unexpected issues")


# ============================================================================
# MAIN RUNNER
# ============================================================================

async def main():
    """Run all search tool examples."""

    print("\n" + "="*80)
    print("SEARCH TOOL EXAMPLES FOR AGENKIT")
    print("="*80)
    print("\nThese examples demonstrate WHY and HOW to use search tools with agents.")
    print("Each example includes real-world scenarios, trade-offs, and key insights.")

    examples = [
        ("Basic Web Search", example1_basic_search),
        ("Multi-Source Search (Parallel)", example2_multi_source_search),
        ("Search with Ranking", example3_ranked_search),
        ("Semantic Search", example4_semantic_search),
        ("Search with Fallback", example5_search_with_fallback),
        ("Rate-Limited Search", example6_rate_limited_search),
        ("Error Handling", example7_error_handling),
    ]

    for i, (name, example_func) in enumerate(examples, 1):
        await example_func()

        if i < len(examples):
            input("\nPress Enter to continue to next example...")

    # Summary
    print("\n" + "="*80)
    print("KEY TAKEAWAYS")
    print("="*80)
    print("""
1. WHEN TO USE SEARCH TOOLS:
   - Current information beyond LLM training data
   - Fact-checking and source attribution
   - Multi-source information gathering
   - Document and knowledge base retrieval

2. SEARCH PATTERNS:
   - Basic: Single source, simple queries
   - Multi-source: Parallel search, broader coverage
   - Ranked: Filter and sort by relevance
   - Semantic: Embedding-based, meaning over keywords
   - Resilient: Fallbacks and caching for availability

3. PRODUCTION CONSIDERATIONS:
   - Rate limiting: Prevent quota exhaustion
   - Error handling: Graceful degradation
   - Caching: Reduce latency and cost
   - Monitoring: Track usage and failures

4. TRADE-OFFS:
   - Accuracy: Real-time data vs hallucination risk
   - Latency: 100-1000ms per search
   - Cost: $5-25/1000 queries
   - Reliability: Depends on external services

5. COMBINING WITH LLMs:
   - LLM: Understands intent, synthesizes results
   - Tool: Retrieves current, factual information
   - Hybrid: Best of both worlds

Next steps:
- Replace mock services with real APIs (Google, Bing, Brave)
- Add authentication and API key management
- Implement result caching and deduplication
- Add monitoring and usage analytics
    """)


if __name__ == "__main__":
    asyncio.run(main())
