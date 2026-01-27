"""
Code Assistant Agent

An AI agent that helps with coding tasks:
- Documentation search
- Code generation
- Best practices
- Debugging assistance
- Multi-language support
"""

import asyncio
from typing import Any

from agenkit import Agent, Message


class CodeAssistantAgent(Agent):
    """
    AI coding assistant with documentation and generation capabilities.

    Supports Python, JavaScript, Go, Rust, TypeScript, and more.
    """

    def __init__(self, name: str = "CodeAssistant"):
        self._name = name
        self._query_count = 0

        # Mock documentation database
        self._docs = {
            "python": {
                "async": "Use async/await for asynchronous operations. Example: async def main(): await task()",
                "list": "Lists are mutable sequences: my_list = [1, 2, 3]",
                "dict": "Dictionaries store key-value pairs: my_dict = {'key': 'value'}",
            },
            "javascript": {
                "promise": "Promises handle async operations: new Promise((resolve, reject) => {...})",
                "arrow": "Arrow functions: const add = (a, b) => a + b",
            },
            "go": {
                "goroutine": "Concurrent execution: go func() { ... }()",
                "channel": "Communication between goroutines: ch := make(chan int)",
            },
        }

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> list[str]:
        return [
            "documentation_search",
            "code_generation",
            "debugging",
            "best_practices",
            "multi_language",
        ]

    async def process(self, message: Message) -> Message:
        """Process coding assistance request."""
        self._query_count += 1
        content = str(message.content).lower().strip()
        metadata = message.metadata or {}

        # Determine request type
        if any(word in content for word in ["generate", "create", "write", "code for"]):
            result = await self._generate_code(content, metadata)
        elif any(word in content for word in ["document", "docs", "how to", "explain"]):
            result = await self._search_docs(content, metadata)
        elif any(word in content for word in ["debug", "error", "fix", "wrong"]):
            result = await self._debug_help(content, metadata)
        else:
            result = await self._general_help(content, metadata)

        return Message(
            role="assistant",
            content=result["content"],
            metadata={
                "query_count": self._query_count,
                "request_type": result["type"],
                "language": result.get("language"),
                "code_blocks": result.get("code_blocks", 0),
            },
        )

    async def _generate_code(self, query: str, metadata: dict) -> dict[str, Any]:
        """Generate code based on request."""
        await asyncio.sleep(0.4)

        language = self._detect_language(query)

        if "fibonacci" in query:
            code = self._get_fibonacci_code(language)
        elif "api" in query or "endpoint" in query:
            code = self._get_api_code(language)
        elif "database" in query or "sql" in query:
            code = self._get_database_code(language)
        else:
            code = self._get_hello_world_code(language)

        content = f"""
# Code Generation: {language.title()}

```{language}
{code}
```

**Explanation:**
This code demonstrates best practices for {language}:
- Clear variable naming
- Proper error handling
- Documented functions
- Type hints (where applicable)

**Usage:**
Run this code in your {language} environment. Make sure dependencies are installed.

**Next Steps:**
- Add unit tests
- Handle edge cases
- Add logging
- Optimize performance

Need help with something else?
"""

        return {
            "type": "code_generation",
            "language": language,
            "code_blocks": 1,
            "content": content,
        }

    async def _search_docs(self, query: str, metadata: dict) -> dict[str, Any]:
        """Search documentation."""
        await asyncio.sleep(0.3)

        language = self._detect_language(query)

        # Find relevant docs
        docs_found = []
        if language in self._docs:
            for topic, doc in self._docs[language].items():
                if topic in query:
                    docs_found.append({"topic": topic, "content": doc})

        content = f"""
# Documentation Search: {language.title()}

"""
        if docs_found:
            for doc in docs_found:
                content += f"## {doc['topic'].title()}\n\n{doc['content']}\n\n"
        else:
            content += f"""
No exact matches found for "{query}" in {language}.

**Suggested Topics:**
- Functions and methods
- Data structures
- Async programming
- Error handling
- Testing

**Resources:**
- Official docs: https://docs.{language}.org
- Tutorials: https://learn.{language}.org
- Community: https://community.{language}.org

Try rephrasing your question or asking about specific features!
"""

        return {
            "type": "documentation_search",
            "language": language,
            "results_found": len(docs_found),
            "content": content,
        }

    async def _debug_help(self, query: str, metadata: dict) -> dict[str, Any]:
        """Provide debugging assistance."""
        await asyncio.sleep(0.3)

        content = """
# Debugging Assistance

**Common Debugging Steps:**

1. **Check the Error Message**
   - Read the full stack trace
   - Identify the line number
   - Understand the error type

2. **Verify Inputs**
   - Print variable values
   - Check data types
   - Validate assumptions

3. **Isolate the Problem**
   - Comment out code sections
   - Test functions individually
   - Use minimal reproduction

4. **Common Issues:**
   - Null/undefined values
   - Type mismatches
   - Off-by-one errors
   - Race conditions

**Pro Tips:**
- Use debugger breakpoints
- Add strategic logging
- Write unit tests
- Check documentation

Share your error message for specific help!
"""

        return {
            "type": "debugging",
            "content": content,
        }

    async def _general_help(self, query: str, metadata: dict) -> dict[str, Any]:
        """General coding assistance."""
        await asyncio.sleep(0.2)

        content = """
# Code Assistant

I can help you with:

**1. Code Generation**
- "Generate Python code for X"
- "Create a REST API endpoint"
- "Write a function to Y"

**2. Documentation**
- "Explain async in Python"
- "How to use promises in JavaScript"
- "What are goroutines in Go"

**3. Debugging**
- "Help me debug this error"
- "Why isn't my code working"
- "Fix this bug"

**4. Best Practices**
- Code reviews
- Performance optimization
- Security recommendations

**Supported Languages:**
Python, JavaScript, TypeScript, Go, Rust, C++, Java

What would you like help with?
"""

        return {
            "type": "general",
            "content": content,
        }

    def _detect_language(self, query: str) -> str:
        """Detect programming language from query."""
        languages = ["python", "javascript", "typescript", "go", "rust", "cpp", "java"]

        for lang in languages:
            if lang in query:
                return lang

        # Default to Python
        return "python"

    def _get_fibonacci_code(self, language: str) -> str:
        """Generate Fibonacci code."""
        codes = {
            "python": """def fibonacci(n: int) -> int:
    \"\"\"Calculate nth Fibonacci number.\"\"\"
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

# Example usage
result = fibonacci(10)
print(f"Fibonacci(10) = {result}")""",
            "javascript": r"""function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// Example usage
const result = fibonacci(10);
console.log(\`Fibonacci(10) = \${result}\`);""",
            "go": """func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    return fibonacci(n-1) + fibonacci(n-2)
}

// Example usage
result := fibonacci(10)
fmt.Printf("Fibonacci(10) = %d\\n", result)""",
        }
        return codes.get(language, codes["python"])

    def _get_api_code(self, language: str) -> str:
        """Generate API endpoint code."""
        codes = {
            "python": """from fastapi import FastAPI

app = FastAPI()

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id, "name": "John Doe"}

# Run with: uvicorn main:app --reload""",
            "javascript": """const express = require('express');
const app = express();

app.get('/api/users/:userId', (req, res) => {
    res.json({ userId: req.params.userId, name: 'John Doe' });
});

app.listen(3000, () => console.log('Server running'));""",
        }
        return codes.get(language, codes["python"])

    def _get_database_code(self, language: str) -> str:
        """Generate database code."""
        codes = {
            "python": """import sqlite3

def get_users():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

# Example usage
users = get_users()
for user in users:
    print(user)""",
        }
        return codes.get(language, codes["python"])

    def _get_hello_world_code(self, language: str) -> str:
        """Generate hello world code."""
        codes = {
            "python": 'print("Hello, World!")',
            "javascript": 'console.log("Hello, World!");',
            "go": 'fmt.Println("Hello, World!")',
            "rust": 'println!("Hello, World!");',
        }
        return codes.get(language, codes["python"])
