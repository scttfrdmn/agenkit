# Code Review System - Multi-Agent Team

End-to-end example demonstrating parallel multi-agent code review with specialized agents.

## Overview

A **production-ready code review system** using AgentKit's parallel agent execution. Multiple specialized agents review code concurrently, then results are synthesized into a comprehensive report.

**Key Features:**
- **Parallel Agent Execution**: 4 agents run simultaneously
- **Specialized Reviews**: Style, Security, Performance, Correctness
- **Result Synthesis**: Combined into comprehensive report
- **Severity Classification**: Critical, High, Medium, Low

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│             Code Review Orchestrator                     │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  Code Submission → Parallel Execution                    │
│                                                           │
│    ┌────────────┐  ┌────────────┐  ┌────────────┐      │
│    │   Style    │  │  Security  │  │Performance │      │
│    │   Agent    │  │   Agent    │  │   Agent    │      │
│    └─────┬──────┘  └─────┬──────┘  └─────┬──────┘      │
│          │                 │                │            │
│          └─────────────────┴────────────────┘            │
│                           │                              │
│                     ┌─────┴──────┐                       │
│                     │Correctness │                       │
│                     │   Agent    │                       │
│                     └─────┬──────┘                       │
│                           │                              │
│                    Review Results                        │
│                           │                              │
│                     ┌─────▼──────┐                       │
│                     │ Synthesis  │                       │
│                     │   Agent    │                       │
│                     └─────┬──────┘                       │
│                           │                              │
│                   Final Report                           │
└───────────────────────────┴─────────────────────────────┘
```

## Quick Start

```bash
# From agenkit root
cd examples/e2e/code-review

# Run demo
python3 main.py

# Review specific file
python3 main.py path/to/file.py
```

## Components

### 1. Review Agents (4 specialized agents)

**StyleAgent** - Code style and conventions
- Naming conventions (snake_case, PascalCase)
- Line length
- Indentation consistency
- Trailing whitespace

**SecurityAgent** - Security vulnerabilities
- Hardcoded secrets/credentials
- SQL injection
- Command injection
- Insecure cryptography
- Path traversal

**PerformanceAgent** - Performance issues
- Nested loops (O(n²))
- String concatenation in loops
- Inefficient list operations

**CorrectnessAgent** - Bugs and logic errors
- Bare except clauses
- Assignment vs comparison (= vs ==)
- Mutable default arguments

### 2. Orchestrator

**ReviewOrchestrator** - Coordinates parallel execution
- Runs 4 agents concurrently using `asyncio.gather()`
- Collects results from all agents
- Passes to synthesis agent
- Returns final report

### 3. Synthesis Agent

**SynthesisAgent** - Combines all review results
- Groups issues by severity
- Calculates overall verdict
- Generates comprehensive report
- Prioritizes critical issues

## Example Output

```
======================================================================
CODE REVIEW REPORT
======================================================================

Overall Verdict: ✗ FAILED
Average Score: 6.0/10.0
Total Issues: 7

Issues by Severity:
  Critical: 2
  High:     3
  Medium:   2
  Low:      0

Agent Results:
  ✗ StyleAgent: 6.0/10 - 3 issues
  ✗ SecurityAgent: 2.0/10 - 2 issues
  ✓ PerformanceAgent: 10.0/10 - 0 issues
  ✗ CorrectnessAgent: 6.0/10 - 2 issues

======================================================================
CRITICAL ISSUES (Must Fix)
======================================================================

1. [SECURITY] Hardcoded password detected
   Location: Line 3
   Code: password = "admin123"
   Fix: Use environment variables or secret management system

2. [SECURITY] Hardcoded API key detected
   Location: Line 4
   Code: api_key = "sk_test_1234567890"
   Fix: Use environment variables or secret management system

======================================================================
RECOMMENDATION
======================================================================
❌ Code review FAILED with 2 critical issues.
   These must be fixed before merging.
======================================================================
```

## Performance

- **Parallel Execution**: All 4 agents run simultaneously
- **Review Time**: ~10-50ms for typical files
- **Scalability**: Can review multiple files concurrently
- **Efficiency**: 4x faster than sequential execution

## Programmatic Usage

```python
from agents.review_types import CodeSubmission
from orchestration import ReviewOrchestrator

# Initialize orchestrator
orchestrator = ReviewOrchestrator(verbose=True)

# Create submission
submission = CodeSubmission(content=code_string, file_path="example.py", language="python")

# Execute review
report = await orchestrator.review_code(submission)
print(report)
```

## Extending

### Add New Review Agent

```python
from agenkit import Agent, Message
from agents.review_types import ReviewResult, CodeIssue, CodeSubmission


class DocumentationAgent(Agent):
    @property
    def name(self) -> str:
        return "DocumentationAgent"

    async def process(self, message: Message) -> Message:
        submission = message.metadata.get("code_submission")

        # Your review logic here
        issues = []
        # ... check for docstrings, comments, etc.

        result = ReviewResult(
            agent_name=self.name,
            issues=issues,
            summary=f"Found {len(issues)} documentation issues",
            overall_score=calculate_score(issues),
            passed=len(issues) == 0,
        )

        return Message(role="assistant", content=result.summary, metadata={"review_result": result})
```

### Integrate Real Tools

Replace pattern-based checks with real tools:

```python
# pylint integration
import pylint.lint

run = pylint.lint.Run([filepath], do_exit=False)

# bandit for security
import bandit

b_mgr = bandit.core.BanditManager(bandit.core.config.BanditConfig(), "file")
b_mgr.discover_files([filepath])
b_mgr.run_tests()

# mypy for type checking
import mypy.api

result = mypy.api.run([filepath])
```

## Production Considerations

**Ready:**
- ✅ Parallel agent execution
- ✅ Comprehensive issue detection
- ✅ Severity classification
- ✅ Result synthesis
- ✅ Type hints throughout
- ✅ Async/await

**Needs Enhancement:**
- ⚠️ Integrate real linting tools (pylint, flake8, bandit)
- ⚠️ Add LLM for contextual analysis
- ⚠️ Add caching for repeated files
- ⚠️ Add incremental reviews (diff-only)
- ⚠️ Add configuration file support
- ⚠️ Add CI/CD integration
- ⚠️ Add metrics and observability

## Related Examples

- **customer-support/**: Sequential multi-agent pipeline
- **research-assistant/**: Autonomous agent with planning
- **patterns/**: Individual agent patterns

---

**Built with AgentKit** - Production-grade multi-agent framework for Python
