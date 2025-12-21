# Bidirectional LangChain + Agenkit Integration

Complete guide for using Agenkit with LangChain and LangGraph in both directions.

## Overview

This guide shows **bidirectional** integration between LangChain and Agenkit:

1. **Agenkit → LangChain**: Use Agenkit agents as LangChain tools
2. **LangChain → Agenkit**: Use LangChain components within Agenkit agents
3. **Hybrid Architecture**: Combine both frameworks for maximum flexibility

> **Note**: For migrating entirely from LangChain to Agenkit, see [Migration Guide](../migrations/langchain-to-agenkit.md).

---

## 1. Agenkit Agent as LangChain Tool

Use your Agenkit agents as tools within LangChain chains and agents.

### Basic Integration

```python
from langchain.tools import BaseTool
from langchain.agents import AgentType, initialize_agent
from langchain.llms import OpenAI
from agenkit import Agent, Message
import asyncio

class AgenkitTool(BaseTool):
    """Wrap Agenkit agent as LangChain tool."""

    name = "agenkit_agent"
    description = "An Agenkit agent that processes queries"

    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent

    def _run(self, query: str) -> str:
        """Synchronous execution."""
        return asyncio.run(self._arun(query))

    async def _arun(self, query: str) -> str:
        """Asynchronous execution."""
        message = Message(role="user", content=query)
        response = await self.agent.process(message)
        return response.content

# Create Agenkit agent
from agenkit.patterns import ReActAgent
from agenkit.adapters import OpenAIAdapter

llm_adapter = OpenAIAdapter(api_key="your-key", model="gpt-4")
agenkit_agent = ReActAgent(llm=llm_adapter)

# Wrap as LangChain tool
tool = AgenkitTool(agent=agenkit_agent)

# Use in LangChain agent
llm = OpenAI(temperature=0)
agent = initialize_agent(
    tools=[tool],
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)

# Run
result = agent.run("Analyze this data using the Agenkit agent")
print(result)
```

### Multiple Agenkit Agents as Tools

```python
from typing import List

class AgenkitToolkit:
    """Collection of Agenkit agents as LangChain tools."""

    @staticmethod
    def create_tools(agents: dict[str, Agent]) -> List[BaseTool]:
        """Create LangChain tools from multiple Agenkit agents."""
        tools = []

        for name, agent in agents.items():
            tool = type(
                f"AgenkitTool_{name}",
                (BaseTool,),
                {
                    "name": name,
                    "description": f"Agenkit {name} agent",
                    "agent": agent,
                    "_run": lambda self, query: asyncio.run(self._arun(query)),
                    "_arun": lambda self, query: self._execute(query),
                }
            )()

            # Bind agent to tool instance
            tool.agent = agent

            # Add async execution method
            async def execute(query: str, ag=agent):
                msg = Message(role="user", content=query)
                resp = await ag.process(msg)
                return resp.content

            tool._execute = execute
            tools.append(tool)

        return tools

# Example: Multiple specialized agents
from agenkit.patterns import ReActAgent, PlanningAgent, AnalysisAgent

agents = {
    "react_agent": ReActAgent(llm=llm_adapter),
    "planning_agent": PlanningAgent(llm=llm_adapter),
    "analysis_agent": AnalysisAgent(llm=llm_adapter),
}

# Create toolkit
tools = AgenkitToolkit.create_tools(agents)

# Use in LangChain
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)
```

### With LangGraph State Machines

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    next_agent: str

def create_langgraph_with_agenkit(agenkit_agents: dict[str, Agent]):
    """Create LangGraph that uses Agenkit agents."""

    workflow = StateGraph(AgentState)

    # Add Agenkit agents as nodes
    for name, agent in agenkit_agents.items():
        async def node_func(state: AgentState, ag=agent):
            last_message = state["messages"][-1]
            msg = Message(role="user", content=last_message)
            response = await ag.process(msg)
            return {
                "messages": [response.content],
                "next_agent": "end"
            }

        workflow.add_node(name, node_func)

    # Define edges
    workflow.set_entry_point("react_agent")
    workflow.add_edge("react_agent", "planning_agent")
    workflow.add_edge("planning_agent", END)

    return workflow.compile()

# Use hybrid workflow
graph = create_langgraph_with_agenkit({
    "react_agent": ReActAgent(llm=llm_adapter),
    "planning_agent": PlanningAgent(llm=llm_adapter),
})

result = await graph.ainvoke({
    "messages": ["Plan and execute a web scraping task"],
    "next_agent": "react_agent"
})
```

---

## 2. LangChain Components in Agenkit

Use LangChain's rich ecosystem within Agenkit agents.

### LangChain Tools in Agenkit Agent

```python
from langchain.agents import load_tools
from agenkit import Agent, Message

class LangChainToolAgent(Agent):
    """Agenkit agent that uses LangChain tools."""

    def __init__(self, langchain_tools: list):
        self.tools = langchain_tools
        self.tool_map = {tool.name: tool for tool in tools}

    @property
    def name(self) -> str:
        return "langchain-tool-agent"

    async def process(self, message: Message) -> Message:
        # Parse which tool to use (simplified)
        content = message.content.lower()

        result = None
        for tool_name, tool in self.tool_map.items():
            if tool_name in content:
                # Execute LangChain tool
                query = content.replace(tool_name, "").strip()
                result = tool.run(query)
                break

        if result is None:
            result = "No matching tool found"

        return Message(
            role="assistant",
            content=result,
            metadata={"tools_used": list(self.tool_map.keys())}
        )

# Load LangChain tools
langchain_tools = load_tools(
    ["serpapi", "llm-math", "wikipedia"],
    llm=OpenAI(temperature=0)
)

# Create Agenkit agent with LangChain tools
agent = LangChainToolAgent(langchain_tools)

# Use Agenkit patterns on top
from agenkit.middleware import RetryMiddleware, CachingMiddleware

agent = CachingMiddleware(agent)
agent = RetryMiddleware(agent, max_retries=3)

# Now you have Agenkit patterns + LangChain tools!
response = await agent.process(
    Message(role="user", content="wikipedia what is quantum computing")
)
```

### LangChain Memory in Agenkit

```python
from langchain.memory import ConversationBufferMemory
from agenkit import Agent, Message

class AgenkitAgentWithLangChainMemory(Agent):
    """Agenkit agent using LangChain memory."""

    def __init__(self, base_agent: Agent, memory: ConversationBufferMemory):
        self.base_agent = base_agent
        self.memory = memory

    @property
    def name(self) -> str:
        return f"{self.base_agent.name}-with-memory"

    async def process(self, message: Message) -> Message:
        # Get conversation history from LangChain memory
        history = self.memory.load_memory_variables({})

        # Augment message with history
        augmented_content = f"{history.get('history', '')}\n\nUser: {message.content}"
        augmented_message = Message(
            role="user",
            content=augmented_content,
            metadata=message.metadata
        )

        # Process with base agent
        response = await self.base_agent.process(augmented_message)

        # Save to LangChain memory
        self.memory.save_context(
            {"input": message.content},
            {"output": response.content}
        )

        return response

# Example usage
memory = ConversationBufferMemory(memory_key="history")
base_agent = ReActAgent(llm=llm_adapter)
agent = AgenkitAgentWithLangChainMemory(base_agent, memory)

# Conversation with memory
response1 = await agent.process(Message(role="user", content="My name is Alice"))
response2 = await agent.process(Message(role="user", content="What's my name?"))
# LangChain memory provides context!
```

### LangChain Document Loaders + Agenkit

```python
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from agenkit import Agent, Message

class DocumentAnalysisAgent(Agent):
    """Agenkit agent that uses LangChain document processing."""

    def __init__(self, llm_adapter):
        self.llm_adapter = llm_adapter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

    @property
    def name(self) -> str:
        return "document-analysis-agent"

    async def process(self, message: Message) -> Message:
        # Extract URL from message
        url = message.metadata.get("url")

        if url:
            # Use LangChain loader
            loader = WebBaseLoader(url)
            documents = loader.load()

            # Split documents
            splits = self.text_splitter.split_documents(documents)

            # Analyze with Agenkit LLM
            summaries = []
            for doc in splits[:3]:  # First 3 chunks
                analysis_msg = Message(
                    role="user",
                    content=f"Summarize: {doc.page_content}"
                )
                # Use Agenkit adapter
                summary = await self.llm_adapter.complete(analysis_msg.content)
                summaries.append(summary)

            result = "\n\n".join(summaries)
        else:
            result = "No URL provided"

        return Message(role="assistant", content=result)

# Usage
agent = DocumentAnalysisAgent(llm_adapter)
response = await agent.process(
    Message(
        role="user",
        content="Analyze this webpage",
        metadata={"url": "https://example.com/article"}
    )
)
```

---

## 3. Hybrid Architectures

Combine both frameworks strategically for their strengths.

### Pattern: LangChain for RAG, Agenkit for Orchestration

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from agenkit.patterns import OrchestrationAgent

class HybridRAGAgent(Agent):
    """Use LangChain RAG + Agenkit orchestration."""

    def __init__(self, vectorstore: Chroma, orchestrator: OrchestrationAgent):
        self.vectorstore = vectorstore
        self.orchestrator = orchestrator

    @property
    def name(self) -> str:
        return "hybrid-rag-agent"

    async def process(self, message: Message) -> Message:
        # 1. Use LangChain for retrieval
        docs = self.vectorstore.similarity_search(
            message.content,
            k=3
        )

        # 2. Format context
        context = "\n\n".join([doc.page_content for doc in docs])

        # 3. Use Agenkit orchestration for reasoning
        augmented_message = Message(
            role="user",
            content=f"Context:\n{context}\n\nQuestion: {message.content}",
            metadata={"retrieved_docs": len(docs)}
        )

        return await self.orchestrator.process(augmented_message)

# Setup
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embeddings)
orchestrator = OrchestrationAgent(llm=llm_adapter)

agent = HybridRAGAgent(vectorstore, orchestrator)
```

### Pattern: Agenkit for Tool Execution, LangChain for Chains

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

class HybridToolChainAgent(Agent):
    """Agenkit tools + LangChain chains."""

    def __init__(self, agenkit_tools: dict[str, Agent], langchain_chain: LLMChain):
        self.tools = agenkit_tools
        self.chain = langchain_chain

    @property
    def name(self) -> str:
        return "hybrid-tool-chain"

    async def process(self, message: Message) -> Message:
        # 1. Use LangChain chain to decide which tool
        tool_decision = self.chain.run(query=message.content)

        # 2. Execute with Agenkit tool
        tool_name = tool_decision.strip().lower()
        if tool_name in self.tools:
            tool_agent = self.tools[tool_name]
            return await tool_agent.process(message)

        return Message(
            role="assistant",
            content=f"Unknown tool: {tool_name}"
        )

# Setup
prompt = PromptTemplate(
    input_variables=["query"],
    template="Which tool should handle this: {query}? Options: search, calculate, analyze"
)
chain = LLMChain(llm=OpenAI(), prompt=prompt)

tools = {
    "search": SearchAgent(llm_adapter),
    "calculate": CalculatorAgent(),
    "analyze": AnalysisAgent(llm_adapter),
}

agent = HybridToolChainAgent(tools, chain)
```

### Pattern: Best of Both Worlds

```python
from agenkit.middleware import RetryMiddleware, CachingMiddleware, TracingMiddleware
from langchain.memory import ConversationSummaryMemory
from langchain.vectorstores import FAISS

class BestOfBothAgent(Agent):
    """
    Combines strengths of both frameworks:
    - LangChain: Memory, vectorstores, document loaders
    - Agenkit: Middleware, patterns, cross-language support
    """

    def __init__(
        self,
        llm_adapter,
        memory: ConversationSummaryMemory,
        vectorstore: FAISS,
        langchain_tools: list
    ):
        self.llm_adapter = llm_adapter
        self.memory = memory
        self.vectorstore = vectorstore
        self.tools = {tool.name: tool for tool in langchain_tools}

    @property
    def name(self) -> str:
        return "best-of-both"

    async def process(self, message: Message) -> Message:
        # 1. Retrieve context (LangChain vectorstore)
        docs = self.vectorstore.similarity_search(message.content, k=2)
        context = "\n".join([doc.page_content for doc in docs])

        # 2. Get conversation history (LangChain memory)
        history = self.memory.load_memory_variables({})

        # 3. Build augmented prompt
        full_prompt = f"""
Context from knowledge base:
{context}

Conversation history:
{history.get('history', '')}

User query: {message.content}
"""

        # 4. Process with Agenkit LLM
        response_text = await self.llm_adapter.complete(full_prompt)

        # 5. Save to LangChain memory
        self.memory.save_context(
            {"input": message.content},
            {"output": response_text}
        )

        return Message(
            role="assistant",
            content=response_text,
            metadata={
                "docs_retrieved": len(docs),
                "memory_entries": len(history.get('history', ''))
            }
        )

# Create base agent
base = BestOfBothAgent(
    llm_adapter=llm_adapter,
    memory=ConversationSummaryMemory(llm=OpenAI()),
    vectorstore=vectorstore,
    langchain_tools=load_tools(["serpapi", "llm-math"])
)

# Add Agenkit middleware (LangChain doesn't have these!)
agent = TracingMiddleware(base, service_name="hybrid-agent")
agent = CachingMiddleware(agent, ttl=3600)
agent = RetryMiddleware(agent, max_retries=3)

# Now you have:
# ✅ LangChain's memory and vectorstore
# ✅ Agenkit's middleware and observability
# ✅ Best of both ecosystems!
```

---

## 4. When to Use Each Approach

### Use Agenkit → LangChain When:
- You have existing Agenkit agents you want to leverage
- You need LangChain's specific chains (e.g., ConversationalRetrievalChain)
- Your team is primarily LangChain but wants Agenkit benefits
- You want to gradually introduce Agenkit patterns

### Use LangChain → Agenkit When:
- You want Agenkit's middleware (retry, circuit breaker, timeout)
- You need cross-language support (Go, TypeScript, Rust, etc.)
- You want better observability (tracing, metrics)
- You prefer Agenkit's pattern library

### Use Hybrid Architecture When:
- You want best of both frameworks
- LangChain's ecosystem (document loaders, vectorstores)
- Agenkit's middleware and cross-language support
- Complex applications requiring multiple capabilities

---

## 5. Migration Strategy

### Gradual Migration Path

```python
# Phase 1: Keep LangChain, add Agenkit as tools
langchain_agent_with_agenkit_tools = initialize_agent(
    tools=[AgenkitTool(my_agent)],
    llm=llm
)

# Phase 2: Use LangChain components in Agenkit
agenkit_agent_with_langchain = AgenkitAgentWithLangChainMemory(
    base_agent,
    langchain_memory
)

# Phase 3: Hybrid architecture
hybrid = BestOfBothAgent(...)

# Phase 4: Full Agenkit (if desired)
pure_agenkit = OrchestrationAgent(...)
```

---

## 6. Performance Comparison

| Feature | LangChain Only | Agenkit Only | Hybrid |
|---------|----------------|--------------|--------|
| **Middleware** | ❌ | ✅ | ✅ |
| **Vectorstores** | ✅ | ⚠️ (DIY) | ✅ |
| **Cross-language** | ❌ | ✅ | ✅ |
| **Observability** | ⚠️ (basic) | ✅ | ✅ |
| **Memory** | ✅ | ⚠️ (DIY) | ✅ |
| **Learning Curve** | Medium | Low | High |
| **Flexibility** | Medium | High | Highest |

---

## 7. Complete Example

```python
"""
Complete hybrid system:
- LangChain for RAG (vectorstore, document loaders)
- Agenkit for orchestration (patterns, middleware)
- Both working together seamlessly
"""

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import CharacterTextSplitter
from agenkit.patterns import OrchestrationAgent
from agenkit.middleware import CachingMiddleware, TracingMiddleware

class ProductionHybridSystem:
    """Production-ready hybrid LangChain + Agenkit system."""

    def __init__(self):
        # LangChain: Document processing
        self.loader = DirectoryLoader('./docs')
        self.text_splitter = CharacterTextSplitter()
        self.embeddings = OpenAIEmbeddings()

        # LangChain: Vectorstore
        docs = self.loader.load()
        splits = self.text_splitter.split_documents(docs)
        self.vectorstore = Chroma.from_documents(splits, self.embeddings)

        # Agenkit: Core orchestration
        llm_adapter = OpenAIAdapter(api_key="key", model="gpt-4")
        orchestrator = OrchestrationAgent(llm=llm_adapter)

        # Agenkit: Middleware stack
        orchestrator = CachingMiddleware(orchestrator, ttl=3600)
        orchestrator = TracingMiddleware(orchestrator, service_name="hybrid")

        self.orchestrator = orchestrator

    async def query(self, question: str) -> str:
        """Process query using hybrid system."""
        # 1. Retrieve with LangChain
        docs = self.vectorstore.similarity_search(question, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])

        # 2. Orchestrate with Agenkit
        message = Message(
            role="user",
            content=f"Context:\n{context}\n\nQuestion: {question}"
        )

        response = await self.orchestrator.process(message)
        return response.content

# Usage
system = ProductionHybridSystem()
answer = await system.query("How do I deploy to production?")
```

---

## Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Agenkit Documentation](https://agenkit.dev)
- [Migration Guide](../migrations/langchain-to-agenkit.md)

---

**Best Practice**: Start with hybrid architecture, then optimize based on your specific needs. You don't have to choose one framework - use both strategically! 🚀
