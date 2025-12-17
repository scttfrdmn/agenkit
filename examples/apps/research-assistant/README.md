# Research Assistant - Production Example

**AI-powered research assistant with Python orchestration + Go web scraping workers.**

Apply the Customer Support pattern to build this application.

## Architecture

```
HTTP + WebSocket API (Python)
  ↓
Planner Agent (GPT-4) → Break down research question
  ↓
Scraper Workers (Go) → Fast HTML/PDF extraction
  ↓
Writer Agent (GPT-4) → Synthesize report
  ↓
PostgreSQL → Store results
```

## Quick Start

```bash
cp .env.example .env
# Add OPENAI_API_KEY
docker-compose up --build
```

## API Endpoints

- `POST /research` - Synchronous research
- `WS /ws/research` - Streaming research with progress updates
- `GET /health` - Health check

## Key Differences from Customer Support

1. **LLM**: OpenAI GPT-4 (better for research synthesis)
2. **Go Workers**: Web scraping (10x faster than Python)
3. **Storage**: PostgreSQL for research results
4. **Streaming**: WebSocket for real-time progress
5. **Timeouts**: Longer (60s default, 180s research)

## Extending

See Customer Support README for full implementation patterns.
Apply same middleware stack, observability, and testing patterns.

**Built with AgentKit**
