"""
Experimental: Document QA with RLM Pattern

Demonstrates RLM for multi-hop question answering over large document collections
(similar to BrowseComp+ benchmark from the paper).

Use case: Answer complex questions requiring reasoning over 100s-1000s of documents
that don't fit in a single LLM context window.

Based on "Recursive Language Models" (Zhang et al., 2025)
https://arxiv.org/abs/2512.24601

Status: EXPERIMENTAL - High cost variance, models not optimized for this.
"""

import asyncio
from typing import Any

from agenkit.interfaces import Agent, Message


class DocumentQAAgent:
    """
    RLM-based document QA that handles arbitrarily large document collections.

    Strategy:
    1. Filter documents using keyword/regex search
    2. Recursively query sub-LLM on filtered docs
    3. Verify answer with additional targeted queries
    4. Aggregate findings into final answer

    WARNING: Cost scales with query complexity. Use BM25/RAG if possible.
    """

    def __init__(self, agent: Agent, sub_agent: Agent | None = None):
        self.agent = agent
        self.sub_agent = sub_agent or agent

    async def answer_question(self, question: str, documents: list[dict[str, Any]]) -> str:
        """
        Answer multi-hop question over document collection.

        Args:
            question: Question to answer
            documents: List of documents, each with 'content' and optional 'title'

        Returns:
            Answer string
        """
        # Serialize documents into context string
        context_parts = []
        for i, doc in enumerate(documents):
            title = doc.get("title", f"Document {i + 1}")
            content = doc["content"]
            context_parts.append(f"=== {title} ===\n{content}\n")

        context = "\n".join(context_parts)

        # Build system prompt
        system_prompt = self._build_system_prompt(question, len(documents))

        # Create message with context as variable reference
        message = Message(
            role="user",
            content=f"{system_prompt}\n\nCONTEXT:\n{context}\n\nQUESTION: {question}",
        )

        # Process with RLM strategy
        response = await self.agent.process(message)

        return response.content

    def _build_system_prompt(self, question: str, num_docs: int) -> str:
        """Build system prompt for document QA."""
        return f"""You are answering a complex question that requires reasoning over {num_docs} documents.

QUESTION: {question}

STRATEGY:
1. Use regex/keyword search to filter relevant documents
2. Examine filtered documents with llm_query()
3. Track evidence across multiple documents
4. Verify your answer before finalizing

EXAMPLE APPROACH:
```python
import re

# Step 1: Filter documents by keywords
query_terms = ["keyword1", "keyword2"]
relevant_docs = []

for line in context.split("==="):
    if any(term.lower() in line.lower() for term in query_terms):
        relevant_docs.append(line)

print(f"Found {{len(relevant_docs)}} relevant documents")

# Step 2: Extract information from each
findings = []
for i, doc in enumerate(relevant_docs):
    finding = llm_query(f"Given this document, what information helps answer: {{question}}?\\n\\nDocument: {{doc}}")
    findings.append(finding)
    print(f"Processed {{i+1}}/{{len(relevant_docs)}}")

# Step 3: Synthesize answer
answer = llm_query(f"Based on these findings, answer: {{question}}\\n\\nFindings: {{findings}}")

# Step 4: Verify (optional)
verification = llm_query(f"Is this answer correct and well-supported? Answer: {{answer}}")
print(f"Verification: {{verification}}")
```

FINAL_VAR(answer)

Remember: Use llm_query() for semantic understanding, but filter programmatically first to reduce cost.
"""


async def main():
    """Demo document QA with synthetic multi-hop question."""

    # Synthetic document collection (in production: 100s-1000s of docs)
    documents = [
        {
            "title": "Company History",
            "content": "Acme Corp was founded in 2010 by Dr. Sarah Chen in Boston.",
        },
        {
            "title": "Product Launch",
            "content": "The flagship product, Widget X, launched in March 2015.",
        },
        {
            "title": "CEO Biography",
            "content": "Dr. Sarah Chen holds a PhD from MIT in Computer Science.",
        },
        {
            "title": "Financial Report",
            "content": "Revenue grew 250% in fiscal year 2023 to $50M.",
        },
        {
            "title": "Office Locations",
            "content": "Headquarters moved to San Francisco in 2020.",
        },
        # Add many more documents here...
    ] * 50  # Simulate larger collection

    question = """
    What is the educational background of the person who founded the company,
    and in what year did they launch their flagship product?
    """

    # Mock agent for demo
    class MockDocQAAgent(Agent):
        def name(self) -> str:
            return "mock-doc-qa"

        async def process(self, message: Message) -> Message:
            # Simplified mock that demonstrates the pattern
            return Message(
                role="assistant",
                content="""Dr. Sarah Chen, who founded Acme Corp, holds a PhD from MIT in Computer Science.
The flagship product Widget X launched in March 2015.""",
            )

    agent = MockDocQAAgent()

    doc_qa = DocumentQAAgent(agent=agent)

    print(f"Answering multi-hop question over {len(documents)} documents...")
    answer = await doc_qa.answer_question(question, documents)

    print("\n=== Answer ===")
    print(answer)


if __name__ == "__main__":
    asyncio.run(main())
