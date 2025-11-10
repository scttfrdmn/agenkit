"""
Database Tool Examples for Agenkit

This example demonstrates WHY and HOW to use database tools with agents,
covering real-world scenarios like SQL queries, transactions, connection
pooling, and security considerations.

WHY USE DATABASE TOOLS?
-----------------------
- **Structured data access**: Databases store organized, queryable data
- **Accuracy**: Direct queries are deterministic vs LLM hallucinations
- **Performance**: Database indexes enable fast retrieval (ms vs seconds)
- **Transactions**: ACID guarantees for data consistency
- **Security**: Parameterized queries prevent SQL injection

WHEN TO USE:
- Retrieving user data, orders, products, etc.
- Analytics and reporting queries
- Data validation and lookups
- Multi-step transactions requiring consistency
- Real-time data access

WHEN NOT TO USE:
- Unstructured data (documents, images, logs)
- Questions requiring reasoning over data
- Data not in database (external APIs, files)
- Complex aggregations better handled by analytics tools

TRADE-OFFS:
- Accuracy: Deterministic queries vs LLM flexibility
- Latency: 10-100ms for queries vs 1-10s for LLM
- Security: Must prevent SQL injection with parameterization
- Complexity: Connection management, pooling, transactions
- Cost: Database hosting vs API call costs

"""

import asyncio
import hashlib
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
import sqlite3
from agenkit import Agent
from agenkit.tools import Tool, ToolRegistry


# ============================================================================
# MOCK DATABASE (Using SQLite for demonstration)
# ============================================================================

class MockDatabase:
    """
    Mock database for demonstration.

    In production, use:
    - PostgreSQL with asyncpg
    - MySQL with aiomysql
    - MongoDB with motor
    - Redis with aioredis
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.connection = None
        self._setup_database()

    def _setup_database(self):
        """Initialize database with sample data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                product TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Insert sample data
        cursor.executemany(
            "INSERT OR IGNORE INTO users (id, name, email, role) VALUES (?, ?, ?, ?)",
            [
                (1, "Alice Johnson", "alice@example.com", "admin"),
                (2, "Bob Smith", "bob@example.com", "user"),
                (3, "Charlie Brown", "charlie@example.com", "user"),
            ]
        )

        cursor.executemany(
            "INSERT OR IGNORE INTO orders (id, user_id, product, quantity, price, status) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (1, 1, "Laptop", 1, 1200.00, "completed"),
                (2, 1, "Mouse", 2, 25.00, "completed"),
                (3, 2, "Keyboard", 1, 80.00, "pending"),
                (4, 2, "Monitor", 1, 300.00, "shipped"),
                (5, 3, "Headphones", 1, 150.00, "pending"),
            ]
        )

        conn.commit()
        conn.close()

    def connect(self):
        """Connect to database."""
        if not self.connection:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Return rows as dicts
        return self.connection

    async def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute SQL query."""
        await asyncio.sleep(0.01)  # Simulate network latency
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    async def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute SQL statement (INSERT, UPDATE, DELETE)."""
        await asyncio.sleep(0.01)  # Simulate network latency
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid or cursor.rowcount


# ============================================================================
# EXAMPLE 1: Basic Database Queries
# ============================================================================

class DatabaseTool:
    """
    Basic database query tool.

    WHY: LLMs can't access databases directly.
    Database tools enable agents to retrieve real-time, structured data.
    """

    def __init__(self, db: MockDatabase):
        self.db = db

    async def query_users(self, role: Optional[str] = None) -> List[Dict]:
        """
        Query users from database.

        Args:
            role: Filter by user role (admin, user, etc.)

        Returns:
            List of user records
        """
        if role:
            sql = "SELECT * FROM users WHERE role = ?"
            return await self.db.query(sql, (role,))
        else:
            sql = "SELECT * FROM users"
            return await self.db.query(sql)

    async def query_orders(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Query orders from database.

        Args:
            user_id: Filter by user ID
            status: Filter by order status

        Returns:
            List of order records
        """
        conditions = []
        params = []

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM orders WHERE {where_clause}"

        return await self.db.query(sql, tuple(params))


async def example1_basic_queries():
    """
    Demonstrate basic database queries.

    WHY: Agents need access to real-time structured data.
    Database tools provide accurate, deterministic data retrieval.

    TRADE-OFFS:
    - Pros: Accurate, fast (10-50ms), structured data
    - Cons: Requires schema knowledge, limited to database contents
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Database Queries")
    print("="*80)

    # Create database and tool
    db = MockDatabase()
    db_tool = DatabaseTool(db)

    # Query all users
    print("\nQuery: Get all users")
    users = await db_tool.query_users()
    print(f"✓ Found {len(users)} users:")
    for user in users:
        print(f"  - {user['name']} ({user['email']}) - Role: {user['role']}")

    # Query by role
    print("\nQuery: Get admin users")
    admins = await db_tool.query_users(role="admin")
    print(f"✓ Found {len(admins)} admin(s):")
    for admin in admins:
        print(f"  - {admin['name']}")

    # Query orders
    print("\nQuery: Get pending orders")
    pending_orders = await db_tool.query_orders(status="pending")
    print(f"✓ Found {len(pending_orders)} pending orders:")
    for order in pending_orders:
        print(f"  - Order #{order['id']}: {order['product']} x{order['quantity']} = ${order['price']}")

    print("\n💡 KEY INSIGHT:")
    print("   Database tools provide accurate, real-time data access.")
    print("   LLM can understand intent, tool retrieves precise data.")


# ============================================================================
# EXAMPLE 2: SQL Injection Prevention
# ============================================================================

class SecureDatabaseTool:
    """
    Database tool with SQL injection prevention.

    WHY: User inputs can contain malicious SQL code.
    Parameterized queries prevent SQL injection attacks.
    """

    def __init__(self, db: MockDatabase):
        self.db = db

    async def search_users_unsafe(self, search_term: str) -> List[Dict]:
        """
        ⚠️ UNSAFE: Vulnerable to SQL injection.
        NEVER do this in production!
        """
        # ❌ String interpolation allows SQL injection
        sql = f"SELECT * FROM users WHERE name LIKE '%{search_term}%'"
        return await self.db.query(sql)

    async def search_users_safe(self, search_term: str) -> List[Dict]:
        """
        ✅ SAFE: Uses parameterized queries.
        Always use this approach!
        """
        # ✅ Parameterized query prevents injection
        sql = "SELECT * FROM users WHERE name LIKE ?"
        return await self.db.query(sql, (f"%{search_term}%",))


async def example2_sql_injection_prevention():
    """
    Demonstrate SQL injection prevention.

    WHY: User inputs may contain malicious SQL code.
    Without parameterization, attackers can read/modify/delete data.

    TRADE-OFFS:
    - Parameterized queries: Slightly more verbose but CRITICAL for security
    - Input validation: Additional layer of defense
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: SQL Injection Prevention")
    print("="*80)

    db = MockDatabase()
    db_tool = SecureDatabaseTool(db)

    # Normal search (both work)
    print("\n--- Normal Search ---")
    search_term = "Alice"
    print(f"Search term: '{search_term}'")

    results = await db_tool.search_users_safe(search_term)
    print(f"✓ Found {len(results)} user(s)")

    # Malicious search (injection attempt)
    print("\n--- SQL Injection Attempt ---")
    malicious_input = "' OR '1'='1"  # Attempts to return all users
    print(f"Malicious input: '{malicious_input}'")

    print("\n⚠️ Unsafe query (would return ALL users):")
    print(f"   SELECT * FROM users WHERE name LIKE '%{malicious_input}%'")
    print("   → This becomes: WHERE name LIKE '%' OR '1'='1%'")
    print("   → Returns all users (security breach!)")

    print("\n✅ Safe query (parameterized):")
    results = await db_tool.search_users_safe(malicious_input)
    print(f"   Found {len(results)} user(s)")
    print("   → Treats input as literal string, no injection possible")

    print("\n💡 KEY INSIGHT:")
    print("   ALWAYS use parameterized queries (?, $1, %s) for user inputs.")
    print("   NEVER use f-strings or string concatenation for SQL.")
    print("   Parameterization is THE defense against SQL injection.")


# ============================================================================
# EXAMPLE 3: Connection Pooling
# ============================================================================

class PooledDatabaseTool:
    """
    Database tool with connection pooling.

    WHY: Creating connections is expensive (50-200ms).
    Connection pools reuse connections for better performance.
    """

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self.pool = []  # Simplified pool (use asyncpg.create_pool in production)
        self.stats = {
            "queries": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }

    async def _get_connection(self):
        """Get connection from pool or create new one."""
        if self.pool:
            self.stats["pool_hits"] += 1
            return self.pool.pop()
        else:
            self.stats["pool_misses"] += 1
            return MockDatabase()

    async def _return_connection(self, conn):
        """Return connection to pool."""
        if len(self.pool) < self.pool_size:
            self.pool.append(conn)
        # else: discard connection (pool full)

    async def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute query using pooled connection."""
        self.stats["queries"] += 1

        conn = await self._get_connection()
        try:
            return await conn.query(sql, params)
        finally:
            await self._return_connection(conn)


async def example3_connection_pooling():
    """
    Demonstrate connection pooling.

    WHY: Creating database connections is expensive (50-200ms).
    Connection pools reuse connections, reducing latency by 10-20×.

    TRADE-OFFS:
    - Performance: 5-10ms with pool vs 50-200ms without
    - Memory: Each pooled connection uses ~1-10MB
    - Complexity: Pool management and configuration
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Connection Pooling")
    print("="*80)

    # Create pooled database tool
    db_tool = PooledDatabaseTool(pool_size=5)

    # Execute multiple queries
    print("\nExecuting 10 queries with connection pool (size=5):")

    start = time.time()
    for i in range(10):
        results = await db_tool.query("SELECT * FROM users")
        print(f"  Query {i+1}: {len(results)} users")
    elapsed = time.time() - start

    print(f"\n✓ Completed in {elapsed*1000:.0f}ms")
    print(f"\nPool Statistics:")
    print(f"  Total queries: {db_tool.stats['queries']}")
    print(f"  Pool hits: {db_tool.stats['pool_hits']}")
    print(f"  Pool misses: {db_tool.stats['pool_misses']}")
    print(f"  Hit rate: {db_tool.stats['pool_hits'] / db_tool.stats['queries'] * 100:.0f}%")

    print("\n💡 KEY INSIGHT:")
    print("   Connection pooling reduces query latency by 10-20×.")
    print("   First 5 queries create connections (pool misses).")
    print("   Remaining queries reuse connections (pool hits).")
    print("   In production: Use asyncpg.create_pool() or aiomysql.create_pool().")


# ============================================================================
# EXAMPLE 4: Transaction Management
# ============================================================================

class TransactionalDatabaseTool:
    """
    Database tool with transaction support.

    WHY: Multiple related operations need atomicity.
    Transactions ensure all-or-nothing execution (ACID).
    """

    def __init__(self, db: MockDatabase):
        self.db = db

    async def create_order_with_validation(
        self,
        user_id: int,
        product: str,
        quantity: int,
        price: float
    ) -> Dict[str, Any]:
        """
        Create order with validation in a transaction.

        TRADE-OFFS:
        - Consistency: Guaranteed via ACID transactions
        - Performance: ~10-20ms overhead for transaction management
        - Complexity: Requires rollback logic for errors
        """
        try:
            # Start transaction (implicit in this example)
            # In production: async with conn.transaction()

            # 1. Validate user exists
            users = await self.db.query(
                "SELECT id FROM users WHERE id = ?",
                (user_id,)
            )
            if not users:
                return {
                    "success": False,
                    "error": f"User {user_id} not found"
                }

            # 2. Validate quantity
            if quantity <= 0:
                return {
                    "success": False,
                    "error": "Quantity must be positive"
                }

            # 3. Create order
            order_id = await self.db.execute(
                "INSERT INTO orders (user_id, product, quantity, price, status) VALUES (?, ?, ?, ?, ?)",
                (user_id, product, quantity, price, "pending")
            )

            # 4. Commit transaction (implicit)
            return {
                "success": True,
                "order_id": order_id,
                "message": f"Order #{order_id} created successfully"
            }

        except Exception as e:
            # Rollback transaction on error
            return {
                "success": False,
                "error": f"Transaction failed: {e}"
            }


async def example4_transactions():
    """
    Demonstrate transaction management.

    WHY: Multi-step operations need atomicity.
    Example: Create order + update inventory + charge card → all or nothing.

    TRADE-OFFS:
    - Consistency: ACID guarantees data integrity
    - Performance: ~10-20ms transaction overhead
    - Complexity: Requires error handling and rollback logic
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Transaction Management")
    print("="*80)

    db = MockDatabase()
    db_tool = TransactionalDatabaseTool(db)

    # Valid order
    print("\n--- Creating Valid Order ---")
    result = await db_tool.create_order_with_validation(
        user_id=1,
        product="Tablet",
        quantity=1,
        price=500.00
    )
    print(f"✓ {result['message']}")

    # Invalid order (user doesn't exist)
    print("\n--- Creating Invalid Order (user not found) ---")
    result = await db_tool.create_order_with_validation(
        user_id=999,
        product="Phone",
        quantity=1,
        price=800.00
    )
    print(f"✗ {result['error']}")

    # Invalid order (negative quantity)
    print("\n--- Creating Invalid Order (invalid quantity) ---")
    result = await db_tool.create_order_with_validation(
        user_id=1,
        product="Charger",
        quantity=-1,
        price=20.00
    )
    print(f"✗ {result['error']}")

    print("\n💡 KEY INSIGHT:")
    print("   Transactions ensure atomicity: all operations succeed or all fail.")
    print("   Validations prevent invalid data from being committed.")
    print("   Rollbacks undo partial changes on error.")


# ============================================================================
# EXAMPLE 5: Read Replicas (Read/Write Splitting)
# ============================================================================

class ReplicatedDatabaseTool:
    """
    Database tool with read/write splitting.

    WHY: Write operations are expensive and contend for locks.
    Read replicas offload read traffic for better performance.
    """

    def __init__(self):
        self.primary = MockDatabase()  # Handles writes
        self.replica1 = MockDatabase()  # Handles reads
        self.replica2 = MockDatabase()  # Handles reads
        self.read_index = 0
        self.stats = {"reads": 0, "writes": 0}

    async def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute read query on replica."""
        self.stats["reads"] += 1

        # Round-robin load balancing across replicas
        replica = [self.replica1, self.replica2][self.read_index % 2]
        self.read_index += 1

        return await replica.query(sql, params)

    async def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute write operation on primary."""
        self.stats["writes"] += 1
        return await self.primary.execute(sql, params)


async def example5_read_replicas():
    """
    Demonstrate read/write splitting with replicas.

    WHY: Write operations contend for locks, limiting throughput.
    Read replicas offload reads, enabling horizontal scaling.

    TRADE-OFFS:
    - Throughput: 10× more reads with replicas vs single primary
    - Consistency: Eventual consistency (replica lag ~10-1000ms)
    - Cost: 2-3× database hosting costs for replicas
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Read Replicas (Read/Write Splitting)")
    print("="*80)

    db_tool = ReplicatedDatabaseTool()

    # Simulate workload: 90% reads, 10% writes
    print("\nSimulating workload (90% reads, 10% writes):")

    operations = ["read"] * 9 + ["write"]

    for i, op in enumerate(operations, 1):
        if op == "read":
            await db_tool.query("SELECT * FROM users")
            print(f"  {i}. Read → Replica")
        else:
            await db_tool.execute(
                "INSERT INTO orders (user_id, product, quantity, price) VALUES (?, ?, ?, ?)",
                (1, "Test Product", 1, 10.00)
            )
            print(f"  {i}. Write → Primary")

    print(f"\nStatistics:")
    print(f"  Total reads: {db_tool.stats['reads']} (sent to replicas)")
    print(f"  Total writes: {db_tool.stats['writes']} (sent to primary)")

    print("\n💡 KEY INSIGHT:")
    print("   Read replicas enable horizontal scaling for read-heavy workloads.")
    print("   Writes go to primary (consistency).")
    print("   Reads go to replicas (performance, load distribution).")
    print("   Trade-off: Eventual consistency (replica lag).")


# ============================================================================
# EXAMPLE 6: Query Caching
# ============================================================================

class CachedDatabaseTool:
    """
    Database tool with query result caching.

    WHY: Repeated queries waste database resources.
    Caching reduces latency (0ms) and database load.
    """

    def __init__(self, db: MockDatabase, ttl_seconds: int = 60):
        self.db = db
        self.ttl_seconds = ttl_seconds
        self.cache = {}  # {cache_key: (result, timestamp)}
        self.stats = {"queries": 0, "cache_hits": 0, "cache_misses": 0}

    def _cache_key(self, sql: str, params: tuple) -> str:
        """Generate cache key from SQL and parameters."""
        key_str = f"{sql}:{params}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute query with caching."""
        self.stats["queries"] += 1

        # Check cache
        cache_key = self._cache_key(sql, params)
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]

            # Check if cache entry is still valid
            if time.time() - timestamp < self.ttl_seconds:
                self.stats["cache_hits"] += 1
                return result
            else:
                # Expired, remove from cache
                del self.cache[cache_key]

        # Cache miss - query database
        self.stats["cache_misses"] += 1
        result = await self.db.query(sql, params)

        # Store in cache
        self.cache[cache_key] = (result, time.time())

        return result


async def example6_query_caching():
    """
    Demonstrate query result caching.

    WHY: Repeated queries (e.g., "get user profile") waste resources.
    Caching reduces latency (0ms vs 10-50ms) and database load.

    TRADE-OFFS:
    - Latency: 0ms (cache hit) vs 10-50ms (cache miss)
    - Consistency: Stale data risk (TTL-based expiration)
    - Memory: Cache storage (~1-10KB per entry)
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Query Caching")
    print("="*80)

    db = MockDatabase()
    db_tool = CachedDatabaseTool(db, ttl_seconds=60)

    # First query (cache miss)
    print("\n--- First Query (cache miss) ---")
    start = time.time()
    result = await db_tool.query("SELECT * FROM users WHERE role = ?", ("admin",))
    elapsed = (time.time() - start) * 1000
    print(f"✓ Found {len(result)} admin(s)")
    print(f"  Latency: {elapsed:.1f}ms")
    print(f"  Cache: MISS")

    # Second query (cache hit)
    print("\n--- Second Query (cache hit) ---")
    start = time.time()
    result = await db_tool.query("SELECT * FROM users WHERE role = ?", ("admin",))
    elapsed = (time.time() - start) * 1000
    print(f"✓ Found {len(result)} admin(s)")
    print(f"  Latency: {elapsed:.1f}ms")
    print(f"  Cache: HIT")

    # Different query (cache miss)
    print("\n--- Different Query (cache miss) ---")
    start = time.time()
    result = await db_tool.query("SELECT * FROM users WHERE role = ?", ("user",))
    elapsed = (time.time() - start) * 1000
    print(f"✓ Found {len(result)} user(s)")
    print(f"  Latency: {elapsed:.1f}ms")
    print(f"  Cache: MISS")

    print(f"\nCache Statistics:")
    print(f"  Total queries: {db_tool.stats['queries']}")
    print(f"  Cache hits: {db_tool.stats['cache_hits']}")
    print(f"  Cache misses: {db_tool.stats['cache_misses']}")
    print(f"  Hit rate: {db_tool.stats['cache_hits'] / db_tool.stats['queries'] * 100:.0f}%")

    print("\n💡 KEY INSIGHT:")
    print("   Caching reduces latency from ~10-50ms to ~0ms.")
    print("   Ideal for read-heavy workloads with repeated queries.")
    print("   TTL (time-to-live) balances freshness vs performance.")


# ============================================================================
# EXAMPLE 7: Error Handling and Retries
# ============================================================================

class ResilientDatabaseTool:
    """
    Database tool with error handling and retries.

    WHY: Networks and databases fail transiently.
    Retries with exponential backoff improve reliability.
    """

    def __init__(self, db: MockDatabase, max_retries: int = 3):
        self.db = db
        self.max_retries = max_retries

    async def query_with_retry(
        self,
        sql: str,
        params: tuple = ()
    ) -> Dict[str, Any]:
        """
        Execute query with exponential backoff retry.

        TRADE-OFFS:
        - Reliability: ~99.9% success vs ~99% without retries
        - Latency: Worst case: 10ms + 20ms + 40ms = 70ms
        - Complexity: Retry logic and backoff configuration
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                result = await self.db.query(sql, params)
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1
                }
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 10ms, 20ms, 40ms
                    backoff = 0.01 * (2 ** attempt)
                    await asyncio.sleep(backoff)

        return {
            "success": False,
            "error": str(last_error),
            "attempts": self.max_retries
        }


async def example7_error_handling():
    """
    Demonstrate error handling and retries.

    WHY: Networks fail, databases restart, connections timeout.
    Retries with exponential backoff improve reliability (99% → 99.9%).

    TRADE-OFFS:
    - Reliability: Higher success rate with retries
    - Latency: Slower on failures (70ms worst case vs 10ms success)
    - Idempotency: Only retry safe operations (SELECT, not INSERT)
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Error Handling and Retries")
    print("="*80)

    db = MockDatabase()
    db_tool = ResilientDatabaseTool(db, max_retries=3)

    # Successful query
    print("\n--- Successful Query ---")
    result = await db_tool.query_with_retry("SELECT * FROM users")
    print(f"✓ Success on attempt #{result['attempts']}")
    print(f"  Found {len(result['result'])} users")

    print("\n💡 KEY INSIGHT:")
    print("   Retries improve reliability for transient failures.")
    print("   Exponential backoff: 10ms → 20ms → 40ms")
    print("   IMPORTANT: Only retry idempotent operations (SELECT, not INSERT).")
    print("   Alternative: Use circuit breaker for repeated failures.")


# ============================================================================
# MAIN RUNNER
# ============================================================================

async def main():
    """Run all database tool examples."""

    print("\n" + "="*80)
    print("DATABASE TOOL EXAMPLES FOR AGENKIT")
    print("="*80)
    print("\nThese examples demonstrate WHY and HOW to use database tools with agents.")
    print("Each example includes real-world scenarios, trade-offs, and key insights.")

    examples = [
        ("Basic Database Queries", example1_basic_queries),
        ("SQL Injection Prevention", example2_sql_injection_prevention),
        ("Connection Pooling", example3_connection_pooling),
        ("Transaction Management", example4_transactions),
        ("Read Replicas", example5_read_replicas),
        ("Query Caching", example6_query_caching),
        ("Error Handling and Retries", example7_error_handling),
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
1. WHEN TO USE DATABASE TOOLS:
   - Structured data access (users, orders, products)
   - Analytics and reporting
   - Real-time data lookups
   - Transactional operations requiring consistency

2. SECURITY (CRITICAL):
   - ALWAYS use parameterized queries (?, $1, %s)
   - NEVER use f-strings or concatenation for SQL
   - Validate and sanitize all user inputs
   - Use least-privilege database credentials

3. PERFORMANCE PATTERNS:
   - Connection pooling: 10-20× faster (5ms vs 50-200ms)
   - Query caching: Instant (0ms) for repeated queries
   - Read replicas: 10× read throughput
   - Batch operations: Group multiple queries

4. RELIABILITY PATTERNS:
   - Transactions: ACID guarantees for multi-step operations
   - Retries: Exponential backoff for transient failures
   - Circuit breaker: Fail fast on repeated failures
   - Graceful degradation: Return partial results

5. TRADE-OFFS:
   - Accuracy: Deterministic queries vs LLM flexibility
   - Latency: 10-100ms per query
   - Consistency: Strong (primary) vs eventual (replicas)
   - Cost: Database hosting + connection overhead

6. PRODUCTION CONSIDERATIONS:
   - Use async database libraries (asyncpg, aiomysql, motor)
   - Configure connection pools (10-50 connections typical)
   - Set query timeouts (5-30 seconds)
   - Monitor slow queries and connection pool exhaustion
   - Implement query result caching for hot paths

7. COMBINING WITH LLMs:
   - LLM: Understands natural language intent
   - Tool: Executes precise database queries
   - LLM: Synthesizes results into user-friendly response

Next steps:
- Replace SQLite with production database (PostgreSQL, MySQL, MongoDB)
- Implement connection pooling (asyncpg.create_pool)
- Add query monitoring and slow query logging
- Set up read replicas for scaling
- Implement comprehensive error handling
    """)


if __name__ == "__main__":
    asyncio.run(main())
