# Agenkit on Vercel Edge Functions

Deploy Agenkit agents at the edge with Next.js and Vercel's global network for sub-50ms cold starts and zero-config scalability.

## Overview

This deployment provides edge-native AI agents with:

- ✅ **Global Edge Network**: 35+ regions worldwide, near-zero latency
- ✅ **Fast Cold Starts**: Sub-50ms initialization
- ✅ **Vercel KV**: Redis-compatible edge storage for sessions
- ✅ **Next.js Integration**: Full-stack framework with React UI
- ✅ **Zero Configuration**: Deploy with one command
- ✅ **Auto-Scaling**: Handle any traffic level automatically
- ✅ **Built-in Analytics**: Real-time insights and monitoring
- ✅ **Cost-Effective**: Pay only for execution time

## Quick Start

### 1. Prerequisites

- Node.js 18+
- Vercel account (free tier available)
- Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login
```

### 2. Installation

```bash
# Clone or navigate to directory
cd examples/deployment/vercel-edge

# Install dependencies
npm install
```

### 3. Setup Vercel KV

```bash
# Create KV store (Redis-compatible)
vercel kv create agenkit-sessions

# This will automatically add environment variables:
# - KV_URL
# - KV_REST_API_URL
# - KV_REST_API_TOKEN
# - KV_REST_API_READ_ONLY_TOKEN
```

### 4. Configure Secrets

```bash
# Set OpenAI API key (optional)
vercel env add OPENAI_API_KEY

# Or Anthropic API key
vercel env add ANTHROPIC_API_KEY
```

### 5. Deploy

```bash
# Deploy to production
vercel --prod

# Or deploy to preview
vercel
```

### 6. Test

```bash
# Your deployment URL will be displayed
curl -X POST https://your-deployment.vercel.app/api/agent \
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
│   Client    │ (San Francisco)
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Vercel Edge Node │ (San Francisco datacenter)
│                  │ <10ms away from client
└────┬─────────────┘
     │
     ├──> Next.js Edge Runtime
     ├──> Vercel KV (Redis)
     └──> Analytics & Logs
```

**Key Benefits:**
- Request processed at nearest edge location
- State managed by Vercel KV (globally replicated)
- Automatic HTTPS and DDoS protection
- Built-in CDN for static assets

### Components

**1. Next.js App (`app/`)**
- React UI for agent interaction
- Server-side rendering
- Client-side routing

**2. Edge API Routes (`api/`)**
- `agent.ts` - Main agent endpoint
- `health.ts` - Health check endpoint
- Edge Runtime configuration

**3. Agent Implementations (`lib/agents/`)**
- `react.ts` - ReAct agent (reasoning + tools)
- `conversational.ts` - Multi-turn conversations
- `router.ts` - Intelligent routing

**4. Vercel KV**
- Session state storage
- 1-hour expiration (configurable)
- Globally replicated for low latency

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

**Response:**
```json
{
  "role": "assistant",
  "content": "The answer is 45",
  "metadata": {
    "agent_type": "react",
    "steps": 4,
    "reasoning_steps": [
      "Thought: I need to solve \"Calculate 15 * 3\"",
      "Action: calculator(\"15 * 3\")",
      "Observation: 45",
      "Thought: I have the answer"
    ],
    "tools_used": ["calculator"],
    "session_id": "..."
  },
  "session_id": "..."
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

**Response:**
```json
{
  "role": "assistant",
  "content": "Hello! I'm a conversational agent...",
  "metadata": {
    "agent_type": "conversational",
    "history_length": 0,
    "max_history": 10,
    "provider": "mock",
    "session_id": "user-123"
  },
  "session_id": "user-123"
}
```

**Features:**
- Multi-turn conversations
- Session memory (10 messages)
- Context-aware responses
- OpenAI API integration (with mock fallback)

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

**Response:**
```json
{
  "role": "assistant",
  "content": "The answer is 15",
  "metadata": {
    "agent_type": "react",
    "router_decision": "react",
    "routing_confidence": 0.85,
    "session_id": "..."
  },
  "session_id": "..."
}
```

**Features:**
- Intelligent routing based on content
- Keyword-based classification
- Automatic agent selection
- Confidence scoring

## Configuration

### Environment Variables

Create `.env.local` for local development:

```bash
# Copy example
cp .env.example .env.local

# Add your keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# KV variables (auto-added by Vercel)
KV_URL=redis://...
KV_REST_API_URL=https://...
KV_REST_API_TOKEN=...
KV_REST_API_READ_ONLY_TOKEN=...
```

### Vercel Configuration

Edit `vercel.json` for deployment settings:

```json
{
  "regions": ["iad1", "sfo1", "lhr1", "fra1"],
  "functions": {
    "api/**/*.ts": {
      "runtime": "edge",
      "memory": 128,
      "maxDuration": 10
    }
  }
}
```

**Available Regions:**
- `iad1` - Washington, D.C., USA
- `sfo1` - San Francisco, USA
- `lhr1` - London, UK
- `fra1` - Frankfurt, Germany
- `syd1` - Sydney, Australia
- `sin1` - Singapore
- `nrt1` - Tokyo, Japan

### Next.js Configuration

Edit `next.config.js`:

```javascript
const nextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
        ],
      },
    ];
  },
};
```

## Deployment

### Production Deployment

```bash
# Deploy to production
vercel --prod

# Your app will be available at:
# https://your-project.vercel.app
```

### Preview Deployments

```bash
# Deploy preview (for testing)
vercel

# Preview URL provided:
# https://your-project-git-branch-user.vercel.app
```

### Automatic Git Deployments

1. Connect your Git repository in Vercel dashboard
2. Every push to `main` → Production deployment
3. Every PR → Preview deployment
4. Comments on PR with preview URL

### Custom Domains

```bash
# Add custom domain
vercel domains add yourdomain.com

# Configure DNS records as shown in Vercel dashboard
```

## Development

### Local Development

```bash
# Start development server
npm run dev

# App available at http://localhost:3000
# API available at http://localhost:3000/api/agent
```

### Testing API Locally

```bash
# Test health endpoint
curl http://localhost:3000/api/health

# Test agent endpoint
curl -X POST http://localhost:3000/api/agent \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "react",
    "message": {
      "role": "user",
      "content": "Calculate 5 + 3"
    }
  }'
```

### Type Checking

```bash
# Run TypeScript type checker
npm run type-check

# Fix linting issues
npm run lint
```

## Vercel KV (Redis)

### Session Management

Sessions are stored in Vercel KV with automatic expiration:

```typescript
// Save session (1 hour expiration)
await kv.set(`session:${sessionId}`, session, { ex: 3600 });

// Get session
const session = await kv.get<SessionState>(`session:${sessionId}`);

// Delete session
await kv.del(`session:${sessionId}`);
```

### KV Operations

```bash
# View KV store in dashboard
vercel kv list

# Get specific key
vercel kv get session:abc123

# Delete key
vercel kv del session:abc123
```

### Use Cases

- **Session Storage**: Conversation history (1 hour TTL)
- **Rate Limiting**: Request counters per IP
- **Caching**: LLM response caching
- **Metrics**: Simple counters and gauges

### Limits

**Free Tier:**
- 256 MB storage
- 30 requests/second
- 100 concurrent connections

**Pro Tier:**
- 512 MB storage
- 100 requests/second
- 1000 concurrent connections

## Monitoring

### Vercel Analytics

View real-time metrics in Vercel dashboard:
- Request volume
- Response times
- Error rates
- Geographic distribution
- Edge function invocations

### Function Logs

```bash
# Tail production logs
vercel logs --follow

# Filter by function
vercel logs --follow api/agent

# View recent errors
vercel logs --output json | jq 'select(.level == "error")'
```

### Custom Metrics

Track metrics via Vercel KV:

```typescript
// Increment counter
await kv.incr(`metrics:requests:${agentType}`);

// Track duration
await kv.set(`metrics:duration:${timestamp}`, durationMs);

// Query metrics
const reactCount = await kv.get('metrics:requests:react');
```

### Alerts

Configure alerts in Vercel dashboard:
- High error rate (>5%)
- Slow responses (>1s)
- High usage (approaching limits)
- Failed deployments

## Performance

### Benchmarks

| Metric | Value |
|--------|-------|
| Cold Start | <50ms |
| Warm Request | 1-10ms |
| Time to First Byte | 10-30ms |
| Global Latency | <100ms (95th percentile) |

### Optimization Tips

**1. Minimize Bundle Size**

```bash
# Analyze bundle
npm run build
# Check .next/server/pages/api for size
```

**2. Cache Aggressively**

```typescript
// Cache LLM responses in KV
const cacheKey = `llm:${hash(prompt)}`;
const cached = await kv.get(cacheKey);
if (cached) return cached;

const response = await callLLM(prompt);
await kv.set(cacheKey, response, { ex: 3600 }); // 1 hour
```

**3. Use Edge Runtime**

```typescript
// Ensure all API routes use edge runtime
export const config = {
  runtime: 'edge',
};
```

**4. Optimize React Rendering**

```typescript
// Use React.memo for expensive components
const AgentCard = React.memo(({ agent }) => {
  // ... component code
});
```

**5. Stream Responses**

```typescript
// For long responses, use streaming
const stream = new ReadableStream({
  async start(controller) {
    const response = await agent.process(message);
    controller.enqueue(response);
    controller.close();
  },
});

return new Response(stream);
```

## Cost Analysis

### Pricing

**Hobby (Free):**
- 100 GB-hours/month
- 100 requests/day (edge functions)
- 256 MB KV storage
- Community support

**Pro ($20/month):**
- 1000 GB-hours/month
- Unlimited edge function requests
- 512 MB KV storage
- Email support
- Custom domains

**Enterprise (Custom):**
- Unlimited everything
- SLA guarantees
- Dedicated support
- Advanced security

### Cost Examples

**Low Traffic (10K requests/month):**
- Vercel Pro: $20/month (all-inclusive)
- **Total: $20/month**

**Medium Traffic (1M requests/month):**
- Vercel Pro: $20/month (base)
- Additional GB-hours: ~$5
- **Total: ~$25/month**

**High Traffic (10M requests/month):**
- Vercel Enterprise: Custom pricing
- Estimate: $100-500/month depending on features
- **Total: $100-500/month**

### Cost Optimization

1. **Cache aggressively** - Use KV to cache responses
2. **Optimize bundle size** - Reduce cold start costs
3. **Use preview deployments** - Test before production
4. **Monitor usage** - Set up alerts for unusual patterns
5. **Consider enterprise** - Better pricing at scale

## Limitations

### Edge Runtime Limits

- **CPU Time**: 30 seconds per request
- **Memory**: 128 MB
- **Request Body**: 4 MB
- **Response Body**: 4 MB
- **No Node.js APIs**: Use edge-compatible packages only

### Workarounds

**Long-running tasks:**
```typescript
// Split into multiple requests or use background functions
// Note: Background functions are not available in edge runtime
```

**Large payloads:**
```typescript
// Stream large responses
return new Response(stream, {
  headers: { 'Content-Type': 'text/event-stream' }
});
```

**Node.js APIs:**
```typescript
// Use edge-compatible alternatives
// Instead of: fs.readFile()
// Use: fetch() or KV storage
```

## Troubleshooting

### Issue: Edge function timing out

**Solution:**
- Check if operation takes >30 seconds
- Split into smaller operations
- Use caching to reduce computation

### Issue: KV connection failing

**Solution:**
```bash
# Verify KV environment variables
vercel env ls

# Test KV connectivity
vercel kv get test-key

# Recreate KV store if needed
vercel kv create agenkit-sessions-new
```

### Issue: Build failing

**Solution:**
```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Try build locally
npm run build
```

### Issue: 404 on API routes

**Solution:**
- Verify file is in `api/` directory
- Check `vercel.json` configuration
- Ensure `export const config = { runtime: 'edge' }`

### Issue: Environment variables not working

**Solution:**
```bash
# Add to all environments (production, preview, development)
vercel env add OPENAI_API_KEY

# Pull latest environment variables
vercel env pull .env.local
```

## Security

### Best Practices

**1. Use Secrets for API Keys**
```bash
vercel env add OPENAI_API_KEY
# Never commit secrets to git
```

**2. Implement Rate Limiting**
```typescript
// Use KV for rate limiting
const key = `ratelimit:${clientIP}`;
const count = await kv.incr(key);
if (count === 1) {
  await kv.expire(key, 60); // 60 second window
}
if (count > 100) {
  return new Response('Rate limit exceeded', { status: 429 });
}
```

**3. Validate Input**
```typescript
if (!body.agent_type || !body.message) {
  return NextResponse.json(
    { error: 'Invalid request' },
    { status: 400 }
  );
}
```

**4. Use HTTPS Only**
- Vercel automatically provisions SSL certificates
- All traffic encrypted by default

**5. Enable Edge Protection**
- Vercel provides DDoS protection
- Automatic bot detection
- WAF rules available on Enterprise

## Next Steps

- [ ] Add real OpenAI/Anthropic integration
- [ ] Implement response streaming
- [ ] Add rate limiting with KV
- [ ] Set up custom domain
- [ ] Configure advanced analytics
- [ ] Add error tracking (Sentry integration)
- [ ] Implement caching strategy
- [ ] Add comprehensive tests
- [ ] Set up CI/CD pipeline
- [ ] Add database integration (Vercel Postgres)

## Support

For issues and questions:
- GitHub Issues: https://github.com/agenkit/agenkit/issues
- Vercel Docs: https://vercel.com/docs
- Next.js Docs: https://nextjs.org/docs
- Community Discord: https://discord.gg/agenkit

## Resources

- [Vercel Edge Functions](https://vercel.com/docs/functions/edge-functions)
- [Vercel KV](https://vercel.com/docs/storage/vercel-kv)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Edge Runtime](https://edge-runtime.vercel.app/)
- [Agenkit Documentation](https://github.com/agenkit/agenkit)
