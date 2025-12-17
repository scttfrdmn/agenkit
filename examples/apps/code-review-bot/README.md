# Code Review Bot - Multi-LLM Consensus Review

**Production-ready code review system with parallel multi-LLM analysis and consensus scoring.**

Demonstrates AgentKit's multi-agent orchestration, cross-language architecture (Python + Go), and production middleware stack.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Code Review Bot                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌────────────────────┐           │
│  │   HTTP API   │────────▶│   Orchestrator     │           │
│  │   (FastAPI)  │         │   Agent            │           │
│  └──────────────┘         └────────────────────┘           │
│                                    │                         │
│                         ┌──────────┼──────────┐            │
│                         │          │          │            │
│                   ┌─────▼────┐ ┌──▼─────┐ ┌─▼─────┐       │
│                   │  Claude  │ │  GPT-4 │ │Gemini │       │
│                   │ Security │ │ Arch   │ │ Style │       │
│                   │  Review  │ │ Review │ │Review │       │
│                   └─────┬────┘ └───┬────┘ └───┬───┘       │
│                         │          │          │            │
│                         └──────────┼──────────┘            │
│                                    │                         │
│                         ┌──────────▼────────────┐           │
│                         │  Consensus Algorithm  │           │
│                         │  + Synthesis          │           │
│                         └───────────────────────┘           │
│                                                               │
│  Python Orchestration + Go Static Analysis Workers          │
│                                                               │
│  ┌────────────┐       ┌──────────────┐       ┌──────────┐  │
│  │   Redis    │       │  Prometheus  │       │  Jaeger  │  │
│  │  (Cache)   │       │  (Metrics)   │       │ (Traces) │  │
│  └────────────┘       └──────────────┘       └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Features

### Multi-LLM Consensus Review
- **3 Specialized Reviewers**: Claude (security), GPT-4 (architecture), Gemini (style)
- **Parallel Execution**: Reviews run concurrently via `asyncio.gather()`
- **Consensus Scoring**: Aggregate confidence across reviewers
- **Failure Tolerance**: Continue if individual LLMs fail

### Cross-Language Architecture
- **Python**: Orchestration, API server, LLM coordination (LiteLLM)
- **Go**: Static analysis workers (fast AST parsing, security scanning)
- **gRPC**: High-performance Python ↔ Go communication

### Production Middleware Stack
- **Timeout**: 120s for full review, 60s for analysis
- **Rate Limiting**: 10 reviews/hour per repository (token bucket)
- **Caching**: Redis-backed review caching (avoid duplicate reviews)
- **Audit Logging**: Track all review requests and decisions

### Observability
- **OpenTelemetry**: Distributed tracing across Python and Go
- **Prometheus**: Metrics for review latency, consensus scores, LLM usage
- **Jaeger**: Visual trace inspection at http://localhost:16686
- **Health Checks**: `/health`, `/ready` endpoints

### GitHub Integration (Webhook)
- **PR Events**: Automatic review on `opened` and `synchronize`
- **Comment Posting**: Post consolidated review as PR comment
- **Status Checks**: Update PR status based on consensus threshold

## Quick Start

### Prerequisites

- Docker and Docker Compose
- API Keys: Anthropic (Claude), OpenAI (GPT-4), Google (Gemini)
- Optional: GitHub personal access token for webhook integration

### Setup

```bash
# 1. Clone and navigate
cd examples/apps/code-review-bot

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   ANTHROPIC_API_KEY=sk-ant-xxxxx
#   OPENAI_API_KEY=sk-xxxxx
#   GOOGLE_API_KEY=xxxxx
#   GITHUB_TOKEN=ghp_xxxxx  (optional)

# 3. Start services
docker-compose up --build

# 4. Verify health
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### Usage

**Review Code via API:**

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def authenticate(user, pwd):\n    query = \"SELECT * FROM users WHERE username=\047\" + user + \"\047\"",
    "language": "python",
    "review_type": "security"
  }'
```

**Response:**

```json
{
  "report": "# Code Review Report\n\n**Consensus Score**: 1.00\n\n## CLAUDE Review\n\n❌ **Critical**: SQL injection vulnerability...",
  "consensus_score": 1.0,
  "num_reviews": 3,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**GitHub Webhook:**

Configure webhook at `https://your-domain.com/webhook/github` with:
- Events: Pull requests
- Content type: `application/json`
- Secret: Value from `GITHUB_WEBHOOK_SECRET`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Basic health check |
| `/ready` | GET | Readiness check (verifies LLM API keys) |
| `/review` | POST | Conduct code review |
| `/webhook/github` | POST | GitHub PR webhook handler |

## Services

| Service | Port | Description |
|---------|------|-------------|
| **python-api** | 8000 | FastAPI server (orchestrator) |
| **go-analyzer** | 50051 | gRPC static analysis worker |
| **redis** | 6379 | Review caching |
| **prometheus** | 9090 | Metrics collection |
| **jaeger** | 16686 | Distributed tracing UI |

## Configuration

Environment variables in `.env`:

```bash
# LLM API Keys (all required)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=xxxxx

# GitHub Integration (optional)
GITHUB_TOKEN=ghp_xxxxx
GITHUB_WEBHOOK_SECRET=your-secret

# Timeouts
TIMEOUT_REVIEW=120.0        # Full review timeout (seconds)
TIMEOUT_ANALYSIS=60.0       # Static analysis timeout

# Rate Limiting
RATE_LIMIT_REPO_RATE=10.0   # Reviews per hour per repository

# Features
ENABLE_CACHING=true
ENABLE_AUDIT_LOGGING=true

# Application
CONSENSUS_THRESHOLD=0.7      # Minimum consensus for approval
MAX_FILES_PER_REVIEW=50      # Max files per PR
```

## Testing

```bash
# Unit tests (no services required)
pytest tests/unit/ -v

# Integration tests (requires services)
docker-compose up -d
pytest tests/integration/ -v -m integration

# All tests
pytest tests/ -v
```

## Development

**Local Python Development:**

```bash
cd python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run API server
python -m python.api.server
```

**Local Go Development:**

```bash
cd go
go mod download

# Run analyzer
go run cmd/worker/main.go -port 50051

# Run tests
go test ./...
```

## Key Implementation Details

### Multi-LLM Orchestration

The orchestrator uses LiteLLM to interface with multiple providers:

```python
class ReviewOrchestrator(Agent):
    def __init__(self, anthropic_key, openai_key, google_key):
        self._reviewers = {
            "claude": LiteLLMLLM(model="claude-3-5-sonnet-20241022", api_key=anthropic_key),
            "gpt4": LiteLLMLLM(model="gpt-4-turbo", api_key=openai_key),
            "gemini": LiteLLMLLM(model="gemini-pro", api_key=google_key),
        }

    async def process(self, message: Message) -> Message:
        # Create specialized prompts
        prompts = {
            "claude": self._create_security_prompt(code),
            "gpt4": self._create_architecture_prompt(code),
            "gemini": self._create_style_prompt(code),
        }

        # Run in parallel
        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

        # Calculate consensus
        consensus = self._calculate_consensus(successful_reviews)
        return Message(content=self._synthesize_reviews(reviews, consensus))
```

### Static Analysis Worker (Go)

Fast static analysis for common issues:

```go
type AnalyzerAgent struct {
    name string
}

func (a *AnalyzerAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
    code := message.Content

    // Detect security issues
    issues := a.analyzeCode(code, language)

    // Calculate metrics
    complexity := a.calculateComplexity(code)
    securityScore := a.calculateSecurityScore(issues)

    return &agenkit.Message{
        Role: "assistant",
        Content: a.buildReport(issues, complexity, securityScore),
        Metadata: map[string]interface{}{
            "issues_found": len(issues),
            "complexity": complexity,
            "security_score": securityScore,
        },
    }, nil
}
```

### Consensus Algorithm

Simple but effective consensus calculation:

```python
def _calculate_consensus(self, reviews: List[Dict]) -> float:
    """Calculate proportion of successful reviews."""
    if not reviews:
        return 0.0
    successful = sum(1 for r in reviews if r.get("success", False))
    return successful / len(reviews)
```

## Production Considerations

### Scaling
- **Horizontal**: Run multiple API instances behind load balancer
- **Vertical**: Increase Go worker instances for parallel analysis
- **Caching**: Redis TTL based on code change frequency

### Security
- **API Keys**: Store in secrets manager (AWS Secrets Manager, HashiCorp Vault)
- **Rate Limiting**: Prevent abuse with per-repo limits
- **Audit Logging**: Track all review requests for compliance
- **Webhook Secret**: Verify GitHub webhook signatures

### Cost Optimization
- **Caching**: Avoid duplicate reviews for unchanged code
- **Model Selection**: Use Haiku/GPT-3.5 for faster, cheaper reviews
- **Batching**: Group small files for single LLM call
- **Consensus Threshold**: Require only 2/3 reviewers for approval

### Monitoring
- **Prometheus Metrics**: `review_latency`, `consensus_score`, `llm_failures`
- **Jaeger Traces**: Inspect slow reviews
- **Alerts**: Consensus < 0.5, review failures > 10%

## Architecture Patterns

This example demonstrates:

1. **Multi-Agent Orchestration**: Coordinate 3 specialized LLM agents
2. **Cross-Language Integration**: Python orchestration + Go workers
3. **Consensus Algorithm**: Aggregate multiple LLM opinions
4. **Production Middleware**: Timeout, rate limiting, caching, audit logging
5. **OpenTelemetry Observability**: Traces, metrics, logs
6. **GitHub Integration**: Webhook handling for PR automation

## Comparison to Other Apps

| Feature | Customer Support | Research Assistant | **Code Review Bot** |
|---------|------------------|--------------------|--------------------|
| **LLM Provider** | Anthropic (Claude) | OpenAI (GPT-4) | **All 3 (consensus)** |
| **Go Component** | RAG specialist | Web scraper | **Static analyzer** |
| **Storage** | Redis | PostgreSQL | **Redis** |
| **Unique Feature** | Routing + escalation | WebSocket streaming | **Multi-LLM consensus** |
| **Timeout** | 5s default, 30s RAG | 60s research, 180s scraping | **120s review** |

## Extending

### Add More Reviewers

Add a 4th reviewer (e.g., Cohere):

```python
self._reviewers = {
    "claude": LiteLLMLLM(model="claude-3-5-sonnet-20241022", api_key=anthropic_key),
    "gpt4": LiteLLMLLM(model="gpt-4-turbo", api_key=openai_key),
    "gemini": LiteLLMLLM(model="gemini-pro", api_key=google_key),
    "cohere": LiteLLMLLM(model="command-r-plus", api_key=cohere_key),  # NEW
}

prompts = {
    "claude": self._create_security_prompt(code),
    "gpt4": self._create_architecture_prompt(code),
    "gemini": self._create_style_prompt(code),
    "cohere": self._create_performance_prompt(code),  # NEW
}
```

### Integrate Real Linters

Wrap real linters in Go analyzer:

```go
func (a *AnalyzerAgent) runLinters(code string, language string) []Issue {
    switch language {
    case "python":
        return a.runRuff(code)
    case "go":
        return a.runGolangciLint(code)
    case "javascript":
        return a.runESLint(code)
    }
}
```

### Post to GitHub

Integrate GitHub API to post reviews:

```python
from github import Github

gh = Github(settings.github_token)
repo = gh.get_repo(repo_full_name)
pr = repo.get_pull(pr_number)

# Post review as comment
pr.create_issue_comment(report)

# Update status
repo.create_status(
    sha=pr.head.sha,
    state="success" if consensus >= 0.7 else "failure",
    context="agenkit/code-review",
    description=f"Consensus: {consensus:.0%}"
)
```

## License

Built with AgentKit - see repository root for license.

## Learn More

- [Customer Support Example](../customer-support/) - Learn routing and RAG patterns
- [Research Assistant Example](../research-assistant/) - Learn WebSocket streaming
- [AgentKit Documentation](https://docs.agenkit.dev/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
