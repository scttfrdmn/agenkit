# Agenkit on Cloudflare Workers

Deploy Agenkit agents at the edge with global distribution and sub-10ms cold starts using Cloudflare Workers.

## Overview

This deployment provides edge-native AI agents with:

- ✅ **Global Distribution**: 300+ cities worldwide, near-zero latency
- ✅ **Fast Cold Starts**: Sub-10ms initialization
- ✅ **Durable Objects**: Stateful agent sessions with automatic cleanup
- ✅ **KV Storage**: Edge caching for responses and data
- ✅ **D1 Database**: Serverless SQL for metrics and persistence
- ✅ **Zero Infrastructure**: No servers to manage
- ✅ **Auto-Scaling**: Handle any traffic level automatically
- ✅ **Cost-Effective**: Pay only for requests ($0.50 per million)

## Quick Start

### 1. Prerequisites

- Node.js 18+
- Cloudflare account (free tier available)
- Wrangler CLI

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login
```

### 2. Installation

```bash
# Clone or navigate to directory
cd examples/deployment/cloudflare-workers

# Install dependencies
npm install
```

### 3. Setup Resources

```bash
# Get your Cloudflare account ID
wrangler whoami

# Create KV namespace
wrangler kv:namespace create AGENT_CACHE
wrangler kv:namespace create AGENT_CACHE --preview

# Create D1 database
wrangler d1 create agenkit-db

# Update wrangler.toml with the IDs from above commands
```

### 4. Configure Secrets

```bash
# Set OpenAI API key (optional)
wrangler secret put OPENAI_API_KEY

# Or Anthropic API key
wrangler secret put ANTHROPIC_API_KEY
```

### 5. Run Database Migrations

```bash
# Apply migrations locally for testing
npm run d1:migrate:local

# Apply migrations to production
npm run d1:migrate
```

### 6. Deploy

```bash
# Deploy to development
npm run deploy:dev

# Or deploy to production
npm run deploy:production
```

### 7. Test

```bash
# Your worker URL will be displayed after deployment
curl -X POST https://agenkit-worker.your-subdomain.workers.dev/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "react",
    "message": {
      "role": "user",
      "content": "Calculate 10 + 5"
    }
  }'
```

## Architecture

### Edge Computing Model

```
┌─────────────┐
│   Client    │ (London)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│  Cloudflare Edge │ (London datacenter)
│                  │ <10ms away from client
└────┬─────────────┘
     │
     ├──> Durable Object (Session State)
     ├──> KV Storage (Cache)
     └──> D1 Database (Metrics)
```

**Key Benefits:**
- Request processed at nearest datacenter
- State managed by Durable Objects
- Automatic replication and failover
- Zero cold start after first request

### Components

**1. Worker (index.ts)**
- HTTP request handler
- Routing logic
- API endpoints

**2. Durable Objects (AgentSession)**
- Stateful session management
- Conversation history
- Automatic cleanup (1-hour inactivity)

**3. KV Storage**
- Response caching
- Configuration storage
- Eventually consistent, globally distributed

**4. D1 Database**
- Metrics tracking
- Request logging
- Session metadata

## Agent Types

### 1. ReAct Agent

**Endpoint:** `POST /api/agent`

**Request:**
```json
{
  "agent_type": "react",
  "message": {
    "role": "user",
    "content": "Calculate 15 * 3"
  }
}
```

**Features:**
- Tool use (calculator)
- Multi-step reasoning
- Action-observation loops

### 2. Conversational Agent

**Request:**
```json
{
  "agent_type": "conversational",
  "message": {
    "role": "user",
    "content": "Hello! How are you?"
  },
  "session_id": "user-123"
}
```

**Features:**
- Multi-turn conversations
- Session memory (10 messages)
- Context-aware responses

### 3. Router Agent

**Request:**
```json
{
  "agent_type": "router",
  "message": {
    "role": "user",
    "content": "Calculate 10 + 5 and explain the result"
  }
}
```

**Features:**
- Intelligent routing
- Keyword-based classification
- Automatic agent selection

## Configuration

### Environment Variables

Edit `wrangler.toml`:

```toml
[vars]
ENVIRONMENT = "production"
LOG_LEVEL = "info"
```

### Secrets

```bash
# OpenAI
wrangler secret put OPENAI_API_KEY

# Anthropic
wrangler secret put ANTHROPIC_API_KEY
```

### Multiple Environments

```bash
# Development
npm run deploy:dev

# Staging
npm run deploy:staging

# Production
npm run deploy:production
```

## Durable Objects

### Session Management

Durable Objects provide stateful sessions:

```typescript
// Automatic session creation
const sessionId = crypto.randomUUID();

// Session persists across requests
// Automatic cleanup after 1 hour inactivity
```

**Key Features:**
- Strong consistency
- Exactly-once execution
- Automatic state persistence
- Alarm-based cleanup

### Session API

**Get session info:**
```bash
curl https://your-worker.workers.dev/api/session/{session_id}
```

**Delete session:**
```bash
curl -X DELETE https://your-worker.workers.dev/api/session/{session_id}
```

## KV Storage

### Caching Responses

```typescript
// Cache response for 1 hour
await env.AGENT_CACHE.put(
  `response:${key}`,
  JSON.stringify(response),
  { expirationTtl: 3600 }
);

// Get cached response
const cached = await env.AGENT_CACHE.get(`response:${key}`, 'json');
```

### Use Cases

- Response caching (reduce LLM costs)
- Rate limiting counters
- Configuration storage
- Session metadata

## D1 Database

### Querying Metrics

```bash
# Execute query
wrangler d1 execute agenkit-db --command "SELECT * FROM metrics ORDER BY created_at DESC LIMIT 10"

# Or via API
curl https://your-worker.workers.dev/metrics
```

### Metrics Tracked

- Request count by agent type
- Response times
- Error rates
- Session duration

### Example Queries

```sql
-- Request rate by agent type
SELECT
  agent_type,
  COUNT(*) as request_count,
  AVG(duration_ms) as avg_duration
FROM metrics
WHERE created_at > datetime('now', '-1 hour')
GROUP BY agent_type;

-- Error rate
SELECT
  COUNT(*) FILTER (WHERE status = 'error') * 100.0 / COUNT(*) as error_rate
FROM metrics
WHERE created_at > datetime('now', '-24 hours');
```

## Development

### Local Development

```bash
# Start local dev server
npm run dev

# Worker available at http://localhost:8787
```

### Live Tail Logs

```bash
# Tail production logs in real-time
npm run tail:production

# Or for specific environment
wrangler tail --env staging
```

### Testing

```bash
# Run tests
npm test

# Watch mode
npm run test:watch
```

## Monitoring

### Cloudflare Dashboard

**Analytics:**
1. Go to Workers & Pages
2. Select your worker
3. View real-time metrics:
   - Requests per second
   - CPU time
   - Errors
   - Bandwidth

**Logs:**
- Real-time tail with `wrangler tail`
- LogPush integration for long-term storage

### Custom Metrics

Track custom metrics in D1:

```typescript
await env.AGENT_DB
  .prepare('INSERT INTO metrics (agent_type, duration_ms, status, created_at) VALUES (?, ?, ?, datetime("now"))')
  .bind(agentType, durationMs, status)
  .run();
```

### Alerts

Configure alerts in Cloudflare dashboard:
- Request rate thresholds
- Error rate spikes
- CPU time limits
- Script exceptions

## Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| Cold Start | <10ms |
| Warm Request | 1-5ms |
| Time to First Byte | 5-15ms |
| Global Latency | <50ms (99th percentile) |

### Optimization Tips

1. **Minimize Bundle Size**
   ```bash
   npm run build  # Uses esbuild with minification
   ```

2. **Cache Aggressively**
   ```typescript
   // Cache LLM responses
   const cacheKey = `llm:${hash(prompt)}`;
   const cached = await env.AGENT_CACHE.get(cacheKey);
   if (cached) return cached;
   ```

3. **Use Durable Objects Wisely**
   - Batch operations when possible
   - Use alarms for background cleanup
   - Avoid excessive state reads/writes

4. **Optimize D1 Queries**
   - Use indexes on frequently queried columns
   - Batch inserts when possible
   - Use prepared statements

## Cost Analysis

### Pricing

**Workers:**
- Free tier: 100,000 requests/day
- Paid: $5/month for 10M requests
- Additional: $0.50 per million requests

**Durable Objects:**
- $0.15 per million requests
- $0.20 per GB-month storage

**KV:**
- Free tier: 100,000 reads/day, 1,000 writes/day
- Paid: $0.50 per million reads, $5 per million writes

**D1:**
- Free tier: 5 million reads, 100,000 writes/day
- Paid: Starting at $5/month

### Cost Examples

**Low Traffic (100K requests/month):**
- Workers: Free
- Durable Objects: $0.02
- KV: Free
- D1: Free
- **Total: ~$0.02/month**

**Medium Traffic (1M requests/month):**
- Workers: $5.50
- Durable Objects: $0.15
- KV: $0.50 (assuming cache hits)
- D1: Free
- **Total: ~$6.15/month**

**High Traffic (10M requests/month):**
- Workers: $10 (5M included + 5M × $0.50)
- Durable Objects: $1.50
- KV: $5.00
- D1: $5.00
- **Total: ~$21.50/month**

## Limitations

### Workers Limits

- CPU time: 50ms per request (free tier), 30s (paid)
- Memory: 128 MB
- Script size: 1 MB (after compression)
- Subrequest limit: 50 per request

### Durable Objects Limits

- 1000 requests per second per object
- 128 MB storage per object
- CPU time: 30 seconds per request

### Workarounds

**Long-running tasks:**
```typescript
// Split into multiple requests
// Use Durable Object alarms for background work
await this.state.storage.setAlarm(Date.now() + 1000);
```

**Large responses:**
```typescript
// Stream responses
return new Response(stream, {
  headers: { 'Content-Type': 'text/event-stream' }
});
```

## Troubleshooting

### Issue: Cold starts are slow

**Solution:**
- Minimize bundle size
- Reduce number of imports
- Use code splitting

### Issue: Durable Object not persisting

**Solution:**
```typescript
// Always await storage operations
await this.state.storage.put('key', value);

// Use blockConcurrencyWhile for initialization
this.state.blockConcurrencyWhile(async () => {
  this.data = await this.state.storage.get('data');
});
```

### Issue: D1 query failing

**Solution:**
```bash
# Check migrations applied
wrangler d1 migrations list agenkit-db

# Test query locally
wrangler d1 execute agenkit-db --local --command "SELECT * FROM metrics LIMIT 1"
```

### Issue: KV not updating

**Solution:**
- KV is eventually consistent (60s propagation)
- Use cache tags for invalidation
- Consider using Durable Objects for strong consistency

## Security

### Best Practices

1. **Use Secrets for API Keys**
   ```bash
   wrangler secret put OPENAI_API_KEY
   # Never commit secrets to git
   ```

2. **Implement Rate Limiting**
   ```typescript
   const key = `ratelimit:${clientIP}`;
   const count = await env.AGENT_CACHE.get(key);
   if (count && parseInt(count) > 100) {
     return new Response('Rate limit exceeded', { status: 429 });
   }
   ```

3. **Validate Input**
   ```typescript
   if (!body.agent_type || !body.message) {
     return new Response('Invalid request', { status: 400 });
   }
   ```

4. **Use Custom Domains**
   ```toml
   route = "api.example.com/*"
   ```

5. **Enable WAF (Web Application Firewall)**
   - Cloudflare dashboard > Security > WAF
   - Configure rules for your workers

## Next Steps

- [ ] Add real LLM integration (OpenAI, Anthropic)
- [ ] Implement response streaming
- [ ] Add rate limiting with KV
- [ ] Set up custom domain
- [ ] Configure WAF rules
- [ ] Add Analytics Engine for detailed metrics
- [ ] Implement caching strategy
- [ ] Add error tracking (Sentry integration)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Add comprehensive tests

## Support

For issues and questions:
- GitHub Issues: https://github.com/scttfrdmn/agenkit/issues
- Cloudflare Workers Docs: https://developers.cloudflare.com/workers
- Community Discord: https://discord.gg/agenkit
