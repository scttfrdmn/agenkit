# Migrating from CopilotKit to Agenkit

**Target Audience**: TypeScript/React developers using CopilotKit for AI-powered chat UI
**Difficulty**: Beginner to Intermediate
**Time to Read**: 10-12 minutes

---

## Overview

### Why Migrate to Agenkit?

**Backend Flexibility**:
- **Any LLM**: Not tied to OpenAI API; works with Anthropic, Gemini, local Ollama
- **6 languages**: Python, Go, TypeScript, Rust, C++, Zig (CopilotKit is TypeScript/React)
- **Composable patterns**: 11+ orchestration patterns beyond chat UI

**Protocol**:
- **AG-UI Standard**: Agenkit implements the AG-UI streaming protocol compatible with any frontend
- **OpenTelemetry**: Standard observability vs CopilotKit's proprietary analytics
- **WebSocket/SSE**: Standard streaming without CopilotKit's runtime dependency

**Production**:
- **Circuit breakers, retry, timeout**: Infrastructure-level resilience
- **HITL approval flows**: Built-in human-in-the-loop confirmation
- **State management**: AG-UI `StateManager` for bidirectional sync

### Key Conceptual Differences

| CopilotKit | Agenkit | Notes |
|------------|---------|-------|
| **`CopilotRuntime`** | **Agent + AG-UI adapter** | Explicit |
| **`CopilotAction`** | **Tool class** | Same concept |
| **`useCopilotChat()`** | **AG-UI streaming protocol** | Standard |
| **`useCopilotReadable()`** | **AG-UI StateManager** | Bidirectional |
| **`useCopilotAction()`** | **Tool with HITL approval** | Explicit |
| **`CopilotKitContext`** | **AG-UI `StateManager`** | Same concept |
| **`TextMessage`** | **`Message`** | Standard |
| **`CopilotTask`** | **`agent.process()`** | Direct |

### What You Gain

✅ **Any LLM**: Not restricted to OpenAI API
✅ **Backend language choice**: Python for ML, Go for performance
✅ **Standard protocol**: AG-UI works with any frontend framework
✅ **Production middleware**: Retry, circuit breaker, timeout
✅ **No React dependency**: Backend agents work without frontend context

### What You Lose

❌ **React hooks**: No `useCopilotChat()`, `useCopilotReadable()`, `useCopilotAction()` hooks
❌ **Pre-built UI components**: No `<CopilotChat>`, `<CopilotSidebar>` components
❌ **CopilotKit Cloud**: No managed hosting / analytics dashboard
❌ **PDF reader, spreadsheet tools**: No built-in CopilotKit tool integrations

---

## Pattern Mapping Table

| CopilotKit | Agenkit Equivalent | Notes |
|------------|-------------------|-------|
| `CopilotRuntime` | `Agent` + `AGUIAdapter` | Explicit |
| `OpenAIAdapter` | `OpenAILLM` / `OpenAICompatibleAgent` | Direct |
| `CopilotAction({ name, handler })` | `Tool` class | Class-based |
| `useCopilotReadable({ description, value })` | `StateManager.set(key, value)` | AG-UI |
| `useCopilotAction({ name, handler })` | `Tool` with approval hook | HITL |
| `useCopilotChat()` | AG-UI streaming endpoint | Protocol |
| `TextMessage({ role, content })` | `Message({ role, content })` | Same |
| `copilotContext.messages` | `ConversationalAgent` history | Built-in |

---

## Common Patterns

### Pattern 1: CopilotRuntime + Action

**CopilotKit Code:**
```typescript
import { CopilotRuntime, OpenAIAdapter, copilotRuntimeNextJSAppRouterEndpoint } from '@copilotkit/runtime';
import OpenAI from 'openai';

const runtime = new CopilotRuntime({
  actions: [
    {
      name: 'get_weather',
      description: 'Get current weather for a city',
      parameters: [{ name: 'city', type: 'string', description: 'City name', required: true }],
      handler: async ({ city }) => {
        return `Weather in ${city}: Sunny, 22°C`;
      },
    },
  ],
});

export const POST = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  serviceAdapter: new OpenAIAdapter({ openai: new OpenAI() }),
});
```

**Agenkit Equivalent:**
```typescript
import { OpenAICompatibleAgent } from 'agenkit/llm/openai-compatible';
import { AGUIAdapter } from 'agenkit/protocols/agui';
import { createMessage } from 'agenkit';

class GetWeatherTool {
  name = 'get_weather';
  description = 'Get current weather for a city';

  async run(city: string): Promise<string> {
    return `Weather in ${city}: Sunny, 22°C`;
  }
}

const agent = new OpenAICompatibleAgent({
  baseURL: 'https://api.openai.com/v1',
  model: 'gpt-4o-mini',
  tools: [new GetWeatherTool()],
});

const adapter = new AGUIAdapter(agent);

// Next.js App Router handler
export async function POST(req: Request): Promise<Response> {
  const { messages } = await req.json();
  return adapter.handleRequest(messages);
}
```

---

### Pattern 2: useCopilotReadable (Shared State)

**CopilotKit Code:**
```typescript
import { useCopilotReadable } from '@copilotkit/react-core';

function MyComponent() {
  const [cartItems, setCartItems] = useState([{ name: 'Widget', qty: 2 }]);

  // Make cart visible to the AI
  useCopilotReadable({
    description: 'Current shopping cart contents',
    value: cartItems,
  });

  return <div>...</div>;
}
```

**Agenkit Equivalent (AG-UI StateManager):**
```typescript
import { StateManager } from 'agenkit/protocols/agui';

// Backend: share state with the agent
const stateManager = new StateManager();
stateManager.set('cart_items', [{ name: 'Widget', qty: 2 }]);

// Agent reads shared state
const systemPrompt = `
You have access to the following shared state:
Cart: ${JSON.stringify(stateManager.get('cart_items'))}
`;
```

---

### Pattern 3: useCopilotAction with UI (HITL)

**CopilotKit Code:**
```typescript
import { useCopilotAction } from '@copilotkit/react-core';

function App() {
  useCopilotAction({
    name: 'send_email',
    description: 'Send an email to a recipient',
    parameters: [
      { name: 'recipient', type: 'string', required: true },
      { name: 'subject', type: 'string', required: true },
    ],
    renderAndWait: ({ args, handler }) => (
      <ConfirmDialog
        message={`Send email to ${args.recipient}?`}
        onConfirm={() => handler.resolve('confirmed')}
        onCancel={() => handler.reject('cancelled')}
      />
    ),
    handler: async ({ recipient, subject }) => {
      await sendEmail(recipient, subject);
      return 'Email sent!';
    },
  });
}
```

**Agenkit Equivalent:**
```python
# Python backend with HITL approval
from agenkit.protocols.agui import AGUIAdapter, ToolCallTracker

class SendEmailTool:
    name = "send_email"
    description = "Send an email (requires approval)"

    def __init__(self, tracker: ToolCallTracker) -> None:
        self.tracker = tracker

    async def run(self, recipient: str, subject: str) -> str:
        # Request approval via HITL mechanism
        approved = await self.tracker.request_approval(
            tool=self.name,
            args={"recipient": recipient, "subject": subject},
            message=f"Approve sending email to {recipient}?",
        )
        if not approved:
            return "Email cancelled by user."
        await send_email(recipient, subject)
        return "Email sent successfully!"
```

---

### Pattern 4: Streaming Chat

**CopilotKit Code:**
```typescript
import { useCopilotChat, TextMessage } from '@copilotkit/react-core';

function ChatComponent() {
  const { visibleMessages, appendMessage, isLoading } = useCopilotChat();

  const sendMessage = async (text: string) => {
    await appendMessage(new TextMessage({ role: 'user', content: text }));
  };

  return (
    <div>
      {visibleMessages.map(m => <p key={m.id}>{m.content}</p>)}
      {isLoading && <p>Thinking...</p>}
    </div>
  );
}
```

**Agenkit Equivalent (AG-UI protocol):**
```typescript
// Agenkit AG-UI streaming with SSE
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ messages: conversationHistory }),
});

const reader = response.body!.getReader();
const decoder = new TextDecoder();
let buffer = '';

// Parse AG-UI SSE stream
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const events = buffer.split('\n\n');
  for (const event of events.slice(0, -1)) {
    const data = event.replace(/^data: /, '');
    const chunk = JSON.parse(data);
    appendToUI(chunk.content);
  }
  buffer = events[events.length - 1];
}
```

---

## Step-by-Step Migration

### Step 1: Replace CopilotRuntime with Agent + AGUIAdapter

```typescript
// Before
const runtime = new CopilotRuntime({ actions: [...] });
export const POST = copilotRuntimeNextJSAppRouterEndpoint({ runtime, serviceAdapter });

// After
const agent = new OpenAICompatibleAgent({ model: 'gpt-4o-mini', tools: [...] });
const adapter = new AGUIAdapter(agent);
export async function POST(req: Request) {
  return adapter.handleRequest(await req.json());
}
```

### Step 2: Replace CopilotAction with Tool class

```typescript
// Before
{ name: 'my_action', description: '...', handler: async (args) => result }

// After
class MyActionTool {
  name = 'my_action';
  description = '...';
  async run(args: MyArgs): Promise<string> { return result; }
}
```

### Step 3: Replace useCopilotReadable with StateManager

```typescript
// Before (React hook)
useCopilotReadable({ description: 'Cart', value: cartItems });

// After (AG-UI StateManager)
stateManager.set('cart', cartItems);
// Pass in agent system prompt:
// `Cart: ${JSON.stringify(stateManager.get('cart'))}`
```

### Step 4: Move to standard SSE streaming

```typescript
// Before
const { appendMessage } = useCopilotChat();
await appendMessage(new TextMessage({ role: 'user', content: text }));

// After
const stream = await fetch('/api/chat', { method: 'POST', body: JSON.stringify({ text }) });
// Read AG-UI SSE stream
```

---

## Common Pitfalls

1. **React hooks**: CopilotKit's `useCopilot*` hooks are React-specific; Agenkit backend patterns work independently of the frontend framework
2. **CopilotKit components**: `<CopilotChat>` and `<CopilotSidebar>` have no Agenkit equivalent — build your own chat UI consuming the AG-UI stream
3. **Approval UIs**: CopilotKit `renderAndWait` renders React components; Agenkit's HITL sends approval requests via AG-UI events to the frontend
4. **`copilotContext`**: No global context in Agenkit — pass state explicitly or use `StateManager`

---

## FAQ

**Q: Can I keep using CopilotKit's React components with an Agenkit backend?**
A: Yes, if you implement the CopilotKit runtime protocol in an Agenkit adapter. The `AGUIAdapter` uses a different wire format.

**Q: Does Agenkit have pre-built chat UI components?**
A: No. Agenkit provides the agent backend and AG-UI streaming protocol — build the frontend with any React/Vue/Svelte library.

**Q: How do I handle file uploads (PDF reader) that CopilotKit supports?**
A: Process files server-side before passing content as message text to the agent.

---

## Reference

- Python example: `examples/frameworks/minicopilotkit/minicopilotkit.py`
- AG-UI protocol: `docs/protocols/agui.md`
- Framework comparison: `docs/FRAMEWORK_COMPARISON.md`
