"""MiniPydantic example with dependency injection pattern."""

import asyncio
from dataclasses import dataclass

from minipydantic import TypeSafeAgent


# ============================================================================
# Define Dependencies
# ============================================================================


@dataclass
class DatabaseConnection:
    """Mock database connection."""

    host: str
    port: int
    connected: bool = False

    async def connect(self):
        """Connect to database."""
        self.connected = True
        print(f"✅ Connected to database at {self.host}:{self.port}")

    async def query(self, sql: str) -> list[dict]:
        """Execute query."""
        if not self.connected:
            raise ConnectionError("Not connected to database")

        # Mock query result
        return [
            {"id": 1, "name": "Alice", "score": 95},
            {"id": 2, "name": "Bob", "score": 87},
        ]


@dataclass
class CacheService:
    """Mock cache service."""

    data: dict = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    def get(self, key: str) -> any:
        """Get cached value."""
        return self.data.get(key)

    def set(self, key: str, value: any):
        """Set cached value."""
        self.data[key] = value
        print(f"📦 Cached: {key} = {value}")


# ============================================================================
# Agent with Dependency Injection
# ============================================================================


async def main():
    """Run dependency injection example."""
    # Create agent
    agent = TypeSafeAgent(name="DataAgent")

    # Create and inject dependencies
    db = DatabaseConnection(host="localhost", port=5432)
    cache = CacheService()

    await db.connect()

    agent.inject("db", db)
    agent.inject("cache", cache)

    # Register tools that use dependencies
    @agent.tool(description="Query database with caching")
    async def query_data(table: str, use_cache: bool = True) -> dict:
        """Query with dependency injection."""
        # Access injected dependencies
        db_conn = agent._dependencies["db"]
        cache_service = agent._dependencies["cache"]

        # Check cache first
        cache_key = f"query:{table}"
        if use_cache:
            cached = cache_service.get(cache_key)
            if cached:
                print("✨ Cache hit!")
                return {"source": "cache", "results": cached}

        # Query database
        results = await db_conn.query(f"SELECT * FROM {table}")

        # Cache results
        if use_cache:
            cache_service.set(cache_key, results)

        return {"source": "database", "results": results}

    # Test 1: Query without cache
    print("=" * 60)
    print("Test 1: Database Query (No Cache)")
    print("=" * 60)

    tool = agent.tools["query_data"]
    result = await tool.execute(table="users", use_cache=False)

    print(f"Result: {result.data}\n")

    # Test 2: Query with cache (first time - miss)
    print("=" * 60)
    print("Test 2: Query with Cache (Miss)")
    print("=" * 60)

    result = await tool.execute(table="scores", use_cache=True)
    print(f"Result: {result.data}\n")

    # Test 3: Query with cache (second time - hit)
    print("=" * 60)
    print("Test 3: Query with Cache (Hit)")
    print("=" * 60)

    result = await tool.execute(table="scores", use_cache=True)
    print(f"Result: {result.data}\n")

    # Test 4: Inspect injected dependencies
    print("=" * 60)
    print("Test 4: Dependency Inspection")
    print("=" * 60)

    print(f"Injected dependencies: {list(agent._dependencies.keys())}")
    print(f"Database connected: {agent._dependencies['db'].connected}")
    print(f"Cache size: {len(agent._dependencies['cache'].data)}")


if __name__ == "__main__":
    asyncio.run(main())
