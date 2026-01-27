# Custom Frontend Examples with AG-UI Standard

> **🎯 Direct Integration**: These examples demonstrate how to build custom frontends that consume the AG-UI Standard protocol directly via Server-Sent Events (SSE), without framework dependencies like CopilotKit.

## Overview

These minimal examples (~300 LOC each) show how to integrate AG-UI Standard with popular frontend frameworks using vanilla SSE consumption. Each example shares the same backend and demonstrates framework-specific patterns for handling real-time streaming.

**Frameworks Covered:**
- ⚛️ **React** (port 3001) - Hooks and functional components
- 🖖 **Vue** (port 3002) - Composition API with reactive state
- ⚡ **Svelte** (port 3003) - Reactive declarations and stores
- 🚀 **Astro** (port 3004) - Islands architecture with client-side interactivity

---

## Quick Start

### Prerequisites

- Python 3.11+ with `uv` installed
- Node.js 20+
- Running on ports 8000 (backend), 3001-3004 (frontends)

### Start the Shared Backend

```bash
cd shared-backend

# Install dependencies
uv pip install -r requirements.txt

# Run backend
uv run python main.py
```

Backend will start on http://localhost:8000

### Start a Frontend

**React:**
```bash
cd react
npm install
npm run dev
# Opens on http://localhost:3001
```

**Vue:**
```bash
cd vue
npm install
npm run dev
# Opens on http://localhost:3002
```

**Svelte:**
```bash
cd svelte
npm install
npm run dev
# Opens on http://localhost:3003
```

**Astro:**
```bash
cd astro
npm install
npm run dev
# Opens on http://localhost:3004
```

---

## Architecture

### Shared Backend

All four frontends consume the same AG-UI Standard backend:

```
┌─────────────────────────────────┐
│    FastAPI Backend (Port 8000)  │
│                                 │
│  • SimpleChatAgent              │
│  • AGUIAdapter                  │
│  • SSE Transport                │
│                                 │
│  Endpoint: POST /agui           │
└─────────────────────────────────┘
         │         │         │         │
         ▼         ▼         ▼         ▼
    React(3001) Vue(3002) Svelte(3003) Astro(3004)
```

**Key Components:**
- `agent.py` - Simple chat agent with greeting tool
- `main.py` - FastAPI server with AG-UI Standard endpoint
- CORS enabled for all frontend ports

### Frontend Architecture

Each frontend follows the same pattern:

1. **Send Message** - POST to `/agui` with thread_id and message
2. **Receive SSE Stream** - Parse Server-Sent Events
3. **Handle Events** - Process `text_message_content` events
4. **Update UI** - Accumulate deltas and render messages

---

## Implementation Comparison

### React (~300 LOC)

**Pattern**: Hooks with useRef for stream buffer

```javascript
const [messages, setMessages] = useState([]);
const streamBufferRef = useRef('');

async function sendMessage() {
  const response = await fetch('/agui', { method: 'POST', ... });
  const reader = response.body.getReader();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    // Parse SSE and update state
    streamBufferRef.current += event.delta;
    setMessages(prev => updateLastMessage(prev, streamBufferRef.current));
  }
}
```

**Key Features:**
- Functional components with hooks
- useRef for mutable stream buffer
- useEffect for auto-scroll
- Event-driven state updates

**File Structure:**
```
react/
├── src/
│   ├── App.jsx        # Main component (~150 LOC)
│   ├── App.css        # Styles
│   └── main.jsx       # Entry point
├── vite.config.js     # Proxy config
└── package.json
```

### Vue (~300 LOC)

**Pattern**: Composition API with reactive refs

```javascript
const messages = ref([]);
const streamBuffer = ref('');

async function sendMessage() {
  const response = await fetch('/agui', { method: 'POST', ... });
  const reader = response.body.getReader();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    streamBuffer.value += event.delta;
    messages.value = updateLastMessage(messages.value, streamBuffer.value);
  }
}
```

**Key Features:**
- Composition API (`<script setup>`)
- Reactive refs and computed
- Watchers for auto-scroll
- Scoped styles in SFC

**File Structure:**
```
vue/
├── src/
│   ├── App.vue        # Single File Component (~200 LOC)
│   ├── main.js        # Entry point
│   └── style.css      # Global styles
├── vite.config.js
└── package.json
```

### Svelte (~300 LOC)

**Pattern**: Reactive declarations and stores

```javascript
let messages = [];
let streamBuffer = '';

$: messages && scrollToBottom();  // Reactive statement

async function sendMessage() {
  const response = await fetch('/agui', { method: 'POST', ... });
  const reader = response.body.getReader();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    streamBuffer += event.delta;
    messages = updateLastMessage(messages, streamBuffer);  // Triggers reactivity
  }
}
```

**Key Features:**
- Reactive declarations (`$:`)
- Simple, minimal syntax
- Built-in state management
- Component-scoped styles

**File Structure:**
```
svelte/
├── src/
│   ├── App.svelte     # Component (~180 LOC)
│   ├── main.js        # Entry point
│   └── app.css        # Global styles
├── vite.config.js
└── package.json
```

### Astro (~300 LOC)

**Pattern**: Static page with vanilla JavaScript

```html
<script>
  let isStreaming = false;
  let streamBuffer = '';

  async function sendMessage() {
    const response = await fetch('/agui', { method: 'POST', ... });
    const reader = response.body.getReader();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      streamBuffer += event.delta;
      updateLastMessage(streamBuffer);  // Direct DOM manipulation
    }
  }

  document.getElementById('send').addEventListener('click', sendMessage);
</script>
```

**Key Features:**
- Islands architecture
- Client-side JavaScript only where needed
- Direct DOM manipulation
- Zero runtime overhead for static parts

**File Structure:**
```
astro/
├── src/
│   └── pages/
│       └── index.astro  # Full page (~250 LOC)
├── astro.config.mjs
└── package.json
```

---

## SSE Event Handling

All examples handle the same AG-UI Standard events:

### Event Flow

```
User sends message
    │
    ▼
POST /agui {thread_id, message}
    │
    ▼
SSE Stream Begins
    │
    ├─► event: run_started
    │   data: {"type":"run_started","thread_id":"...","run_id":"..."}
    │
    ├─► event: text_message_start
    │   data: {"type":"text_message_start","message_id":"msg-1","role":"assistant"}
    │
    ├─► event: text_message_content (multiple)
    │   data: {"type":"text_message_content","message_id":"msg-1","delta":"Hello"}
    │   data: {"type":"text_message_content","message_id":"msg-1","delta":" there!"}
    │
    ├─► event: text_message_end
    │   data: {"type":"text_message_end","message_id":"msg-1"}
    │
    └─► event: run_finished
        data: {"type":"run_finished","thread_id":"...","run_id":"..."}
```

### Parsing Logic

Each frontend uses this common pattern:

```javascript
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '';

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value, { stream: true });
  const lines = buffer.split('\n');
  buffer = lines.pop();  // Keep incomplete line

  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));

      if (event.type === 'text_message_content') {
        // Accumulate delta and update UI
        streamBuffer += event.delta;
        updateMessages(streamBuffer);
      }
    }
  }
}
```

---

## Feature Comparison

| Feature | React | Vue | Svelte | Astro |
|---------|-------|-----|--------|-------|
| **Lines of Code** | ~300 | ~300 | ~280 | ~250 |
| **Bundle Size** | ~140 KB | ~120 KB | ~45 KB | ~5 KB* |
| **Reactivity** | Hooks | Composition API | Built-in | Manual |
| **Dev Experience** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **State Management** | useState | ref() | let | Variables |
| **Auto-scroll** | useEffect | watch | $: | Manual |
| **Style Scoping** | CSS Modules | Scoped | Scoped | Global |
| **HMR** | ✅ | ✅ | ✅ | ✅ |

*Astro ships minimal JS - most of the page is static HTML

---

## Customization Guide

### Add New Events

To handle additional AG-UI events (e.g., tool calls):

```javascript
// In all frameworks, extend the event handler:

if (event.type === 'tool_call_start') {
  console.log('Tool call started:', event.tool_call_name);
  showToolIndicator(event.tool_call_name);
}

if (event.type === 'tool_call_result') {
  console.log('Tool result:', event.content);
  hideToolIndicator();
}
```

### Customize Styles

Each framework has its own styling approach:

**React/Vue**: Modify `App.css` or component styles
**Svelte**: Edit `<style>` section in `App.svelte`
**Astro**: Edit `<style>` section in `index.astro`

All use the same design tokens for consistency.

### Add Features

Common enhancements:

1. **Message History**: Store messages in localStorage
2. **Typing Indicators**: Detect streaming state
3. **Error Boundaries**: Handle connection failures
4. **Reconnection**: Auto-retry on disconnect
5. **Markdown Rendering**: Use marked.js or similar
6. **Code Highlighting**: Add syntax highlighting

---

## Production Considerations

### Security

- **CORS**: Configure specific origins (not `*`)
- **Auth**: Add authentication headers
- **Rate Limiting**: Implement on backend
- **Input Validation**: Sanitize user input

### Performance

- **Debounce Input**: Prevent rapid requests
- **Virtual Scrolling**: For long message lists
- **Connection Pooling**: Reuse connections
- **Lazy Loading**: Load old messages on demand

### Reliability

- **Error Handling**: Graceful degradation
- **Timeouts**: Set reasonable limits
- **Retry Logic**: Exponential backoff
- **Health Checks**: Monitor backend availability

---

## Deployment

### Backend

```bash
# Docker
cd shared-backend
docker build -t agui-backend .
docker run -p 8000:8000 agui-backend

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontends

**React/Vue/Svelte (Vite):**
```bash
npm run build
# Serve dist/ folder with nginx, vercel, netlify, etc.
```

**Astro:**
```bash
npm run build
# Serve dist/ folder (fully static, works anywhere)
```

---

## Testing

### Manual Testing

1. Start backend: `cd shared-backend && uv run python main.py`
2. Start frontend: `cd react && npm run dev`
3. Open browser: http://localhost:3001
4. Test messages:
   - "Hello" → Should get greeting response
   - "Help" → Should list capabilities
   - Any text → Should echo with streaming

### Automated Testing

Add E2E tests with Playwright:

```javascript
// tests/react.spec.js
import { test, expect } from '@playwright/test';

test('sends message and receives response', async ({ page }) => {
  await page.goto('http://localhost:3001');
  await page.fill('input', 'Hello');
  await page.click('button');

  await expect(page.locator('.message.assistant')).toBeVisible();
});
```

---

## Troubleshooting

**Issue**: CORS errors
**Solution**: Ensure backend CORS includes frontend port

**Issue**: SSE connection drops
**Solution**: Check network, increase timeout, add reconnection logic

**Issue**: Messages not updating
**Solution**: Verify `text_message_content` event handling

**Issue**: Frontend not connecting to backend
**Solution**: Check Vite proxy config and backend URL

---

## Next Steps

### Enhance Examples

1. **Add Message History**: Persist conversations
2. **Markdown Support**: Render formatted responses
3. **Tool Visualization**: Show tool call indicators
4. **Dark Mode**: Add theme switching
5. **Mobile Optimization**: Responsive design

### Production Features

1. **Authentication**: Add user login
2. **Multi-user**: Support multiple conversations
3. **File Upload**: Handle documents
4. **Voice Input**: Add speech-to-text
5. **Analytics**: Track usage metrics

---

## Resources

### AG-UI Standard
- **Specification**: https://docs.ag-ui.com/
- **Events Reference**: See `agenkit/protocols/agui/events.py`
- **Comparison Doc**: `docs/agui_comparison.md`

### Framework Docs
- **React**: https://react.dev/
- **Vue**: https://vuejs.org/
- **Svelte**: https://svelte.dev/
- **Astro**: https://astro.build/

### Related Examples
- **CopilotKit Integration**: `examples/integrations/copilotkit/`
- **AG-UI Simple**: `examples/agui_simple/`

---

## FAQ

**Q: Why not use CopilotKit?**
A: These examples show how to build custom UIs with full control. Use CopilotKit when you want a pre-built solution.

**Q: Which framework should I choose?**
A:
- React: Most popular, large ecosystem
- Vue: Great DX, easy to learn
- Svelte: Minimal bundle, excellent performance
- Astro: Best for content-heavy sites with islands

**Q: Can I mix AG-UI Simple and Standard?**
A: Yes, but not in the same app. Choose one based on use case (see `docs/agui_comparison.md`).

**Q: How do I add authentication?**
A: Add auth tokens to fetch headers and validate on backend.

**Q: Can I use WebSocket instead of SSE?**
A: Yes, but AG-UI Standard uses SSE. For bidirectional needs, use AG-UI Simple with WebSocket.

---

**Built with ❤️ using Agenkit AG-UI Standard**
