# Tools Pattern Guide

**Last Updated:** November 2025

Tools (also called "function calling") extend agent capabilities with deterministic operations. This guide explains when and how to use tools effectively, covering design patterns, security considerations, and real-world use cases.

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [When to Use Tools](#when-to-use-tools)
3. [Tool Design Patterns](#tool-design-patterns)
4. [Security Considerations](#security-considerations)
5. [Tool Composition](#tool-composition)
6. [Error Handling](#error-handling)
7. [Performance Considerations](#performance-considerations)
8. [Best Practices](#best-practices)
9. [Quick Reference](#quick-reference)

---

## Philosophy

### The LLM-Tool Spectrum

Tools and LLMs represent different points on a capability spectrum:

```
Deterministic ←──────────────────────→ Flexible
Accurate       ←──────────────────────→ Creative
Fast           ←──────────────────────→ Slow
Narrow         ←──────────────────────→ Broad
```

**Tools excel at:**
- **Accuracy**: Calculations, data retrieval, API calls
- **Determinism**: Same input → same output
- **Speed**: Milliseconds vs seconds for LLM calls
- **Reliability**: No hallucinations or inconsistencies

**LLMs excel at:**
- **Flexibility**: Understanding natural language intent
- **Reasoning**: Complex decision-making and synthesis
- **Creativity**: Novel solutions and content generation
- **Adaptation**: Handling unexpected inputs gracefully

### The Hybrid Approach

The most powerful agents use both:
1. **LLM** understands user intent and plans approach
2. **Tools** execute deterministic operations accurately
3. **LLM** synthesizes tool results into coherent response

```
User: "What's the average temperature in my dataset?"
  ↓
LLM: Recognizes need for statistical calculation
  ↓
Tool: calculate_statistics(data) → {"mean": 72.4, "median": 71.0}
  ↓
LLM: "The average temperature is 72.4°F (median: 71.0°F)"
```

---

## When to Use Tools

### Decision Framework

```
┌─────────────────────────────────────┐
│ Does the task require accuracy?     │
│ (calculations, data retrieval)      │
└────────────┬────────────────────────┘
             │ YES
             ↓
┌─────────────────────────────────────┐
│ Is the operation deterministic?     │
│ (same input → same output)          │
└────────────┬────────────────────────┘
             │ YES
             ↓
┌─────────────────────────────────────┐
│ Can you define clear parameters?    │
│ (structured input/output)           │
└────────────┬────────────────────────┘
             │ YES
             ↓
        USE A TOOL
```

### Use Tools For

#### 1. Mathematical Operations
**Why**: LLMs struggle with arithmetic, especially multi-step calculations.

```python
# ❌ LLM alone (unreliable)
"Calculate 847 * 293 + sqrt(12849)"

# ✅ With tool (accurate)
calculator.calculate("847 * 293 + sqrt(12849)")  # → 248,184.3
```

**Trade-offs**: Tools are fast and accurate but inflexible (can't handle ambiguous expressions).

#### 2. Data Retrieval
**Why**: LLMs can't access real-time data or databases.

```python
# ❌ LLM alone (hallucination risk)
"What's the current stock price of AAPL?"

# ✅ With tool (accurate)
stock_api.get_price("AAPL")  # → {"price": 178.23, "timestamp": "2025-11-10"}
```

**Trade-offs**: Tools require API keys, rate limits, and error handling.

#### 3. External APIs
**Why**: LLMs can't make HTTP requests or interact with services.

```python
# ✅ Search tool
search_tool.search("latest AI research papers")

# ✅ Database tool
db_tool.query("SELECT * FROM users WHERE role='admin'")

# ✅ Email tool
email_tool.send(to="user@example.com", subject="Report", body="...")
```

**Trade-offs**: Each API has its own auth, rate limits, and failure modes.

#### 4. Structured Data Processing
**Why**: LLMs are slow and error-prone for data transformations.

```python
# ❌ LLM alone (slow, expensive)
"Convert this CSV to JSON and calculate statistics..."

# ✅ With tools (fast, reliable)
data = csv_tool.parse(file)
stats = statistics_tool.calculate(data)
json_tool.serialize(stats)
```

**Trade-offs**: Tools require predefined schemas; LLMs handle unstructured data better.

### Use LLMs For

#### 1. Natural Language Understanding
**Why**: Tools can't interpret ambiguous intent.

```python
# LLM interprets intent
"Find flights to SF next week, but not on Monday"
# → LLM extracts: destination="SFO", dates=[Tue-Sun], exclude=[Mon]
```

#### 2. Reasoning and Planning
**Why**: LLMs excel at breaking down complex problems.

```python
# LLM creates plan
"Help me plan a 3-day trip to Paris"
# → LLM generates: day 1 (museums), day 2 (landmarks), day 3 (food tour)
```

#### 3. Creative Content
**Why**: Tools can't generate novel, contextually appropriate content.

```python
# LLM creates content
"Write a product description that emphasizes sustainability"
# → LLM generates marketing copy with appropriate tone
```

#### 4. Synthesis and Summarization
**Why**: LLMs combine information from multiple sources coherently.

```python
# LLM synthesizes
tool_result_1 = weather.get_forecast("Paris")
tool_result_2 = events.get_events("Paris")
# → LLM combines: "The weather will be sunny, perfect for the jazz festival!"
```

---

## Tool Design Patterns

### 1. Simple Function Tool

**When to use**: Single, focused operation.

```python
from agenkit.tools import Tool

calculator = Tool(
    name="calculator",
    description="Perform arithmetic calculations",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Mathematical expression to evaluate"
            }
        },
        "required": ["expression"]
    },
    function=lambda expression: eval(expression)  # Use safe_eval in production
)
```

**Trade-offs**: Simple but limited error handling.

### 2. Class-Based Tool

**When to use**: Stateful tools with configuration and multiple methods.

```python
class DatabaseTool:
    """Tool for database queries with connection management."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None

    async def query(self, sql: str, params: dict = None) -> list:
        """Execute SQL query with parameter validation."""
        # Validate SQL (prevent injection)
        if not self._is_safe_query(sql):
            raise ValueError("Unsafe query detected")

        # Connect if needed
        if not self.connection:
            await self._connect()

        # Execute query
        return await self.connection.execute(sql, params)

    def _is_safe_query(self, sql: str) -> bool:
        """Validate SQL query for security."""
        # Implement SQL injection prevention
        pass
```

**Trade-offs**: More complex but safer and more maintainable.

### 3. Async Tool

**When to use**: I/O-bound operations (API calls, file I/O, database queries).

```python
import asyncio
import httpx

class SearchTool:
    """Async tool for web searches."""

    async def search(self, query: str, max_results: int = 10) -> list:
        """Search the web and return results."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.example.com/search",
                params={"q": query, "limit": max_results}
            )
            return response.json()
```

**Trade-offs**: Better performance but requires async/await support.

### 4. Tool with Validation

**When to use**: User-provided inputs that need validation.

```python
from pydantic import BaseModel, validator

class EmailInput(BaseModel):
    """Validated email input."""
    to: str
    subject: str
    body: str

    @validator("to")
    def validate_email(cls, v):
        """Ensure valid email format."""
        import re
        if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            raise ValueError("Invalid email address")
        return v

    @validator("body")
    def validate_body(cls, v):
        """Ensure body is not empty."""
        if not v.strip():
            raise ValueError("Email body cannot be empty")
        return v

class EmailTool:
    """Tool for sending emails with validation."""

    async def send(self, to: str, subject: str, body: str) -> dict:
        """Send email with validation."""
        # Validate inputs
        email = EmailInput(to=to, subject=subject, body=body)

        # Send email (implementation details)
        # ...

        return {"status": "sent", "message_id": "..."}
```

**Trade-offs**: Safer but more verbose.

### 5. Tool with Retries

**When to use**: Unreliable external APIs with transient failures.

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class APITool:
    """Tool with automatic retries for API calls."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def call_api(self, endpoint: str, **kwargs) -> dict:
        """Call external API with automatic retries."""
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=kwargs)
            response.raise_for_status()
            return response.json()
```

**Trade-offs**: More resilient but slower on failures.

---

## Security Considerations

### 1. Input Validation

**Always validate user inputs** to prevent injection attacks and errors.

```python
class SafeDatabaseTool:
    """Database tool with SQL injection prevention."""

    ALLOWED_OPERATIONS = ["SELECT"]  # Whitelist safe operations

    async def query(self, sql: str) -> list:
        """Execute query with strict validation."""
        # 1. Check operation type
        operation = sql.strip().upper().split()[0]
        if operation not in self.ALLOWED_OPERATIONS:
            raise ValueError(f"Operation {operation} not allowed")

        # 2. Use parameterized queries
        # Instead of: f"SELECT * FROM users WHERE id={user_id}"
        # Use: "SELECT * FROM users WHERE id=?" with params=(user_id,)

        # 3. Validate table names
        if not self._is_valid_table(sql):
            raise ValueError("Invalid table name")

        return await self._execute_safe(sql)
```

### 2. Rate Limiting

**Prevent abuse** by limiting tool execution frequency.

```python
import time
from collections import defaultdict

class RateLimitedTool:
    """Tool with rate limiting to prevent abuse."""

    def __init__(self, max_calls_per_minute: int = 60):
        self.max_calls = max_calls_per_minute
        self.calls = defaultdict(list)  # user_id → [timestamps]

    async def execute(self, user_id: str, **kwargs):
        """Execute tool with rate limit check."""
        # Clean old timestamps
        now = time.time()
        self.calls[user_id] = [
            ts for ts in self.calls[user_id]
            if now - ts < 60  # Keep last minute
        ]

        # Check limit
        if len(self.calls[user_id]) >= self.max_calls:
            raise ValueError("Rate limit exceeded. Try again later.")

        # Record call
        self.calls[user_id].append(now)

        # Execute tool
        return await self._execute(**kwargs)
```

### 3. Permission Checking

**Enforce access control** for sensitive operations.

```python
class AdminTool:
    """Tool with role-based access control."""

    REQUIRED_ROLE = "admin"

    async def execute(self, user_id: str, action: str, **kwargs):
        """Execute tool with permission check."""
        # Check user role
        user_role = await self._get_user_role(user_id)
        if user_role != self.REQUIRED_ROLE:
            raise PermissionError(
                f"Action '{action}' requires {self.REQUIRED_ROLE} role"
            )

        # Execute action
        return await self._perform_action(action, **kwargs)
```

### 4. Sanitize Outputs

**Prevent information leakage** in error messages and logs.

```python
class SecureTool:
    """Tool with sanitized error handling."""

    async def execute(self, **kwargs):
        """Execute with sanitized error messages."""
        try:
            return await self._execute(**kwargs)
        except Exception as e:
            # ❌ DON'T expose internal details
            # raise Exception(f"Database error: {connection_string}")

            # ✅ DO provide generic error
            self._log_error(e)  # Log full error internally
            raise Exception("Operation failed. Please try again.")
```

### 5. Audit Logging

**Track tool usage** for security and debugging.

```python
import logging

class AuditedTool:
    """Tool with comprehensive audit logging."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def execute(self, user_id: str, action: str, **kwargs):
        """Execute with audit trail."""
        # Log request
        self.logger.info(
            "Tool execution",
            extra={
                "user_id": user_id,
                "action": action,
                "timestamp": time.time(),
                "params": self._sanitize_params(kwargs)
            }
        )

        try:
            result = await self._execute(action, **kwargs)

            # Log success
            self.logger.info("Tool execution succeeded", extra={
                "user_id": user_id,
                "action": action
            })

            return result
        except Exception as e:
            # Log failure
            self.logger.error("Tool execution failed", extra={
                "user_id": user_id,
                "action": action,
                "error": str(e)
            })
            raise
```

---

## Tool Composition

### 1. Sequential Tool Execution

**When to use**: Tools depend on each other's outputs.

```python
async def analyze_document(document_url: str) -> dict:
    """Analyze document using multiple tools in sequence."""
    # Step 1: Download
    content = await download_tool.fetch(document_url)

    # Step 2: Extract text
    text = await ocr_tool.extract_text(content)

    # Step 3: Analyze sentiment
    sentiment = await sentiment_tool.analyze(text)

    # Step 4: Extract entities
    entities = await ner_tool.extract_entities(text)

    return {
        "sentiment": sentiment,
        "entities": entities,
        "text_length": len(text)
    }
```

**Trade-offs**: Latency = sum of all tools, but simple and deterministic.

### 2. Parallel Tool Execution

**When to use**: Independent tools that can run concurrently.

```python
async def gather_context(query: str) -> dict:
    """Gather information from multiple sources in parallel."""
    # Run all tools concurrently
    results = await asyncio.gather(
        web_search_tool.search(query),
        database_tool.query(f"SELECT * FROM docs WHERE title LIKE '%{query}%'"),
        api_tool.call("external_service", query=query)
    )

    return {
        "web_results": results[0],
        "database_results": results[1],
        "api_results": results[2]
    }
```

**Trade-offs**: Latency = max(tools), but N× cost and complexity.

### 3. Conditional Tool Execution

**When to use**: Tool selection depends on context.

```python
async def route_to_tool(query: str, query_type: str) -> dict:
    """Route to appropriate tool based on query type."""
    if query_type == "calculation":
        return await calculator_tool.calculate(query)
    elif query_type == "search":
        return await search_tool.search(query)
    elif query_type == "database":
        return await database_tool.query(query)
    else:
        raise ValueError(f"Unknown query type: {query_type}")
```

**Trade-offs**: Flexible but requires classification logic.

### 4. Tool Chaining with Error Recovery

**When to use**: Complex workflows with fallback options.

```python
async def resilient_search(query: str) -> list:
    """Search with fallback to alternative sources."""
    try:
        # Try primary search
        return await primary_search_tool.search(query)
    except Exception as e:
        logger.warning(f"Primary search failed: {e}")

        try:
            # Fallback to secondary search
            return await secondary_search_tool.search(query)
        except Exception as e2:
            logger.error(f"Secondary search failed: {e2}")

            # Final fallback: cached results
            return await cache_tool.get_cached_results(query)
```

**Trade-offs**: More resilient but increased complexity.

---

## Error Handling

### 1. Graceful Degradation

**Provide partial results** when some tools fail.

```python
async def multi_source_search(query: str) -> dict:
    """Search multiple sources with graceful degradation."""
    results = {
        "web": None,
        "database": None,
        "api": None,
        "errors": []
    }

    # Try each source independently
    try:
        results["web"] = await web_search_tool.search(query)
    except Exception as e:
        results["errors"].append(f"Web search failed: {e}")

    try:
        results["database"] = await database_tool.query(query)
    except Exception as e:
        results["errors"].append(f"Database query failed: {e}")

    try:
        results["api"] = await api_tool.call(query)
    except Exception as e:
        results["errors"].append(f"API call failed: {e}")

    # Return partial results
    return results
```

### 2. Retry with Backoff

**Handle transient failures** with automatic retries.

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
async def reliable_api_call(endpoint: str) -> dict:
    """API call with automatic retries for transient failures."""
    async with httpx.AsyncClient() as client:
        response = await client.post(endpoint, timeout=10.0)
        response.raise_for_status()
        return response.json()
```

### 3. Circuit Breaker

**Prevent cascading failures** by failing fast when a tool is unhealthy.

```python
class CircuitBreakerTool:
    """Tool with circuit breaker to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open

    async def execute(self, **kwargs):
        """Execute with circuit breaker protection."""
        # Check circuit state
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open. Service unavailable.")

        try:
            result = await self._execute(**kwargs)

            # Reset on success
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0

            return result
        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = time.time()

            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise
```

### 4. Validation Errors

**Provide clear error messages** for invalid inputs.

```python
class ValidatedTool:
    """Tool with comprehensive input validation."""

    async def execute(self, **kwargs):
        """Execute with validation."""
        try:
            # Validate inputs
            self._validate_inputs(kwargs)

            # Execute
            return await self._execute(**kwargs)
        except ValidationError as e:
            # Provide clear error message
            raise ValueError(
                f"Invalid input: {e}. "
                f"Please check the parameters and try again."
            )

    def _validate_inputs(self, kwargs: dict):
        """Validate tool inputs."""
        # Check required parameters
        required = ["param1", "param2"]
        missing = [p for p in required if p not in kwargs]
        if missing:
            raise ValidationError(f"Missing required parameters: {missing}")

        # Validate types
        if not isinstance(kwargs["param1"], str):
            raise ValidationError("param1 must be a string")

        # Validate values
        if kwargs["param2"] < 0:
            raise ValidationError("param2 must be non-negative")
```

---

## Performance Considerations

### 1. Tool Execution Overhead

**Typical overhead**:
- Local tool (calculation): <1ms
- Database query: 10-100ms
- API call: 100-1000ms
- LLM call: 1-10s

**Optimization strategies**:

```python
# ❌ Sequential (slow)
result1 = await tool1()  # 100ms
result2 = await tool2()  # 100ms
result3 = await tool3()  # 100ms
# Total: 300ms

# ✅ Parallel (fast)
results = await asyncio.gather(
    tool1(),
    tool2(),
    tool3()
)
# Total: 100ms (max of all)
```

### 2. Caching

**Cache expensive operations** to reduce latency and cost.

```python
from functools import lru_cache
import hashlib

class CachedTool:
    """Tool with result caching."""

    def __init__(self):
        self.cache = {}

    async def execute(self, query: str) -> dict:
        """Execute with caching."""
        # Create cache key
        cache_key = hashlib.md5(query.encode()).hexdigest()

        # Check cache
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Execute and cache
        result = await self._execute(query)
        self.cache[cache_key] = result

        return result
```

**Trade-offs**: Faster but uses memory; stale data risk.

### 3. Connection Pooling

**Reuse connections** for database and API tools.

```python
class PooledDatabaseTool:
    """Database tool with connection pooling."""

    def __init__(self, connection_string: str, pool_size: int = 10):
        self.pool = create_pool(connection_string, pool_size)

    async def query(self, sql: str) -> list:
        """Execute query using connection pool."""
        async with self.pool.acquire() as connection:
            return await connection.execute(sql)
```

**Trade-offs**: Better performance but more complex setup.

### 4. Batch Processing

**Combine multiple requests** to reduce overhead.

```python
class BatchedTool:
    """Tool with request batching."""

    def __init__(self, batch_size: int = 10, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []

    async def execute(self, query: str) -> dict:
        """Execute with batching."""
        # Add to batch
        future = asyncio.Future()
        self.pending_requests.append((query, future))

        # Process batch if full or timeout
        if len(self.pending_requests) >= self.batch_size:
            await self._process_batch()
        else:
            asyncio.create_task(self._process_after_timeout())

        # Wait for result
        return await future

    async def _process_batch(self):
        """Process all pending requests in one API call."""
        if not self.pending_requests:
            return

        # Extract queries
        queries = [q for q, _ in self.pending_requests]
        futures = [f for _, f in self.pending_requests]

        # Batch API call
        results = await self._batch_execute(queries)

        # Distribute results
        for future, result in zip(futures, results):
            future.set_result(result)

        # Clear batch
        self.pending_requests.clear()
```

**Trade-offs**: Higher throughput but increased latency per request.

---

## Best Practices

### 1. Design Principles

#### Single Responsibility
**Each tool should do one thing well.**

```python
# ❌ Too broad
class GenericTool:
    def execute(self, operation, **kwargs):
        if operation == "calculate":
            return self._calculate(**kwargs)
        elif operation == "search":
            return self._search(**kwargs)
        # ...

# ✅ Focused tools
class CalculatorTool:
    def calculate(self, expression: str) -> float:
        """Calculate mathematical expression."""
        pass

class SearchTool:
    def search(self, query: str) -> list:
        """Search the web."""
        pass
```

#### Clear Interfaces
**Tool parameters should be explicit and well-documented.**

```python
# ❌ Unclear
def search(q, n=10, t="web"):
    pass

# ✅ Clear
def search(
    query: str,
    max_results: int = 10,
    search_type: Literal["web", "images", "news"] = "web"
) -> list[dict]:
    """
    Search the web for query.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 10)
        search_type: Type of search to perform (default: "web")

    Returns:
        List of search results with title, url, and snippet

    Raises:
        ValueError: If query is empty or max_results is negative
        APIError: If search service is unavailable
    """
    pass
```

#### Idempotency
**Tools should be idempotent when possible** (same input → same output).

```python
# ✅ Idempotent (safe to retry)
def get_user(user_id: str) -> dict:
    """Retrieve user by ID."""
    return database.query("SELECT * FROM users WHERE id=?", user_id)

# ⚠️ Not idempotent (creates new resource each time)
def create_user(name: str) -> dict:
    """Create new user."""
    return database.insert("INSERT INTO users (name) VALUES (?)", name)
```

### 2. Documentation

**Provide comprehensive documentation** for each tool:

```python
class WeatherTool:
    """
    Tool for retrieving weather information.

    This tool queries a weather API to get current conditions and forecasts.
    It requires an API key and has a rate limit of 1000 requests/day.

    Examples:
        >>> weather = WeatherTool(api_key="...")
        >>> await weather.get_current("San Francisco, CA")
        {'temp': 72, 'condition': 'sunny', 'humidity': 65}

        >>> await weather.get_forecast("London, UK", days=3)
        [
            {'date': '2025-11-10', 'high': 58, 'low': 48, 'condition': 'rainy'},
            {'date': '2025-11-11', 'high': 62, 'low': 50, 'condition': 'cloudy'},
            {'date': '2025-11-12', 'high': 65, 'low': 52, 'condition': 'sunny'}
        ]

    Attributes:
        api_key: API key for weather service
        base_url: Base URL for API requests
        timeout: Request timeout in seconds (default: 10)

    Raises:
        APIError: If the weather service is unavailable
        RateLimitError: If rate limit is exceeded
        ValueError: If location is invalid
    """
    pass
```

### 3. Testing

**Test tools thoroughly**:

```python
import pytest

class TestCalculatorTool:
    """Tests for calculator tool."""

    @pytest.fixture
    def calculator(self):
        """Create calculator tool instance."""
        return CalculatorTool()

    def test_basic_arithmetic(self, calculator):
        """Test basic arithmetic operations."""
        assert calculator.calculate("2 + 2") == 4
        assert calculator.calculate("10 - 3") == 7
        assert calculator.calculate("4 * 5") == 20
        assert calculator.calculate("15 / 3") == 5

    def test_complex_expressions(self, calculator):
        """Test complex mathematical expressions."""
        assert calculator.calculate("(2 + 3) * 4") == 20
        assert calculator.calculate("sqrt(16) + 2^3") == 12

    def test_error_handling(self, calculator):
        """Test error handling for invalid inputs."""
        with pytest.raises(ValueError):
            calculator.calculate("invalid")

        with pytest.raises(ZeroDivisionError):
            calculator.calculate("1 / 0")

    def test_edge_cases(self, calculator):
        """Test edge cases."""
        assert calculator.calculate("0") == 0
        assert calculator.calculate("-5 + 5") == 0
        assert calculator.calculate("1e6 * 1e-6") == 1
```

### 4. Monitoring

**Track tool usage and performance**:

```python
import time
from prometheus_client import Counter, Histogram

class MonitoredTool:
    """Tool with metrics collection."""

    # Metrics
    execution_count = Counter(
        "tool_executions_total",
        "Total number of tool executions",
        ["tool_name", "status"]
    )
    execution_duration = Histogram(
        "tool_execution_duration_seconds",
        "Tool execution duration in seconds",
        ["tool_name"]
    )

    async def execute(self, **kwargs):
        """Execute with metrics collection."""
        start_time = time.time()

        try:
            result = await self._execute(**kwargs)

            # Record success
            self.execution_count.labels(
                tool_name=self.__class__.__name__,
                status="success"
            ).inc()

            return result
        except Exception as e:
            # Record failure
            self.execution_count.labels(
                tool_name=self.__class__.__name__,
                status="error"
            ).inc()
            raise
        finally:
            # Record duration
            duration = time.time() - start_time
            self.execution_duration.labels(
                tool_name=self.__class__.__name__
            ).observe(duration)
```

---

## Quick Reference

### Tool Selection Checklist

- [ ] **Accuracy required?** → Use tool for deterministic operations
- [ ] **Real-time data?** → Use tool to fetch current information
- [ ] **External API?** → Use tool to make requests
- [ ] **Complex calculation?** → Use tool for math operations
- [ ] **Natural language understanding?** → Use LLM
- [ ] **Creative content?** → Use LLM
- [ ] **Reasoning required?** → Use LLM

### Security Checklist

- [ ] Input validation implemented
- [ ] Output sanitization in place
- [ ] Rate limiting configured
- [ ] Permission checking enforced
- [ ] Audit logging enabled
- [ ] Error messages don't leak sensitive data
- [ ] Connection strings/API keys secured

### Performance Checklist

- [ ] Async implementation for I/O operations
- [ ] Connection pooling for databases/APIs
- [ ] Caching for expensive operations
- [ ] Parallel execution where possible
- [ ] Timeouts configured
- [ ] Metrics collection enabled

### Common Tool Patterns

```python
# Calculator tool (deterministic)
result = await calculator_tool.calculate("2 + 2")

# Search tool (external API)
results = await search_tool.search("query")

# Database tool (data retrieval)
rows = await db_tool.query("SELECT * FROM users")

# Composition (sequential)
data = await fetch_tool.get(url)
processed = await process_tool.transform(data)
result = await analyze_tool.analyze(processed)

# Composition (parallel)
results = await asyncio.gather(
    tool1.execute(input),
    tool2.execute(input),
    tool3.execute(input)
)

# Error handling with fallback
try:
    result = await primary_tool.execute(input)
except Exception:
    result = await fallback_tool.execute(input)
```

---

## Key Takeaways

1. **Use tools for accuracy** - Calculations, data retrieval, deterministic operations
2. **Use LLMs for flexibility** - Understanding intent, reasoning, creative content
3. **Hybrid approach is best** - LLM plans, tools execute, LLM synthesizes
4. **Security is critical** - Validate inputs, rate limit, audit, sanitize outputs
5. **Design for composition** - Single responsibility, clear interfaces, idempotency
6. **Handle errors gracefully** - Fallbacks, retries, partial results
7. **Monitor and test** - Metrics, comprehensive tests, edge cases
8. **Document thoroughly** - Clear parameters, examples, error conditions

---

## Related Patterns

- [Middleware Pattern](MIDDLEWARE.md) - Add retry, metrics, and auth to tool calls
- [Composition Pattern](COMPOSITION.md) - Combine multiple tools in workflows
- [Agent Pattern](AGENTS.md) - Build agents that use tools effectively

---

**Next Steps:**
1. Review the [calculator example](../../examples/tools/calculator_example.py)
2. Review the [search example](../../examples/tools/search_example.py)
3. Review the [database example](../../examples/tools/database_example.py)
4. Explore tool composition patterns
5. Implement custom tools for your use case

For questions or contributions, see [CONTRIBUTING.md](../../CONTRIBUTING.md).
