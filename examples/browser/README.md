# Agenkit WASM Browser Examples

Interactive examples demonstrating @agenkit/wasm integration with popular frontend frameworks.

## Examples

### 1. React Example
**Port:** 3000
**Stack:** React 18 + TypeScript + Vite
**Features:**
- useState/useEffect hooks
- Module selector with 5 patterns
- Real-time agent loading and processing
- Error handling and loading states

**Run:**
```bash
cd react-example
npm install
npm run dev
```

### 2. Vue Example
**Port:** 3001
**Stack:** Vue 3 (Composition API) + TypeScript + Vite
**Features:**
- ref/onMounted composables
- Reactive module switching
- Template-driven UI
- Scoped component styles

**Run:**
```bash
cd vue-example
npm install
npm run dev
```

### 3. Svelte Example
**Port:** 3002
**Stack:** Svelte 4 + TypeScript + Vite
**Features:**
- Svelte stores and reactivity
- Minimal bundle size
- Declarative UI updates
- Built-in animations

**Run:**
```bash
cd svelte-example
npm install
npm run dev
```

### 4. Astro Example
**Port:** 3003
**Stack:** Astro 4 + TypeScript
**Features:**
- **Server-side WASM** - Process during build/SSR
- **Client-side hydration** - Interactive islands
- **Zero JS default** - Ship minimal JavaScript
- **Hybrid rendering** - Best of both worlds

**Run:**
```bash
cd astro-example
npm install
npm run dev
```

## Features Comparison

| Framework | Bundle Size | Hydration | SSR | Build Time | Developer Experience |
|-----------|-------------|-----------|-----|------------|---------------------|
| **React** | Medium      | Full      | ✅  | Fast       | Excellent |
| **Vue**   | Small       | Full      | ✅  | Fast       | Excellent |
| **Svelte** | Smallest   | Full      | ✅  | Fastest    | Excellent |
| **Astro** | Zero-JS*    | Partial   | ✅  | Medium     | Unique |

*Astro ships zero JS by default, hydrating only interactive components

## Available Agents

All examples include these WASM agent modules:

1. **echo_example** (19KB) - Simple echo agent
2. **reflection_example** (66KB) - Self-reflection pattern
3. **sequential_example** (23KB) - Sequential processing
4. **parallel_example** (31KB) - Parallel processing
5. **react_example** (33KB) - Reasoning + acting pattern

## Quick Start

### Prerequisites

- Node.js ≥18.0.0
- npm or pnpm or yarn

### Run All Examples

```bash
# Install dependencies for all examples
for dir in react-example vue-example svelte-example astro-example; do
  cd $dir
  npm install
  cd ..
done

# Run React (terminal 1)
cd react-example && npm run dev

# Run Vue (terminal 2)
cd vue-example && npm run dev

# Run Svelte (terminal 3)
cd svelte-example && npm run dev

# Run Astro (terminal 4)
cd astro-example && npm run dev
```

### Using @agenkit/wasm

All examples use the same API:

```typescript
import { createZigAgent } from '@agenkit/wasm';

// Load agent
const agent = await createZigAgent('echo_example', 'my-agent');

// Process message
const result = await agent.process({
  role: 'user',
  content: 'Hello, WASM!'
});

if (result.ok) {
  console.log(result.message?.content);
}
```

## Architecture

### Client-Side Flow

```
User Input → JavaScript → Load WASM Module → Initialize with WASI
  ↓
Process Message → Call WASM Function → Get Response
  ↓
Update UI ← Return Result ← Parse Output
```

### Server-Side Flow (Astro)

```
Build Time → Load WASM on Server → Process Static Content
  ↓
Generate HTML → Include Results → Ship to Client
  ↓
Optional: Hydrate Interactive Parts → Load WASM in Browser
```

## Performance

### Load Times (Localhost)

| Module | Size | Parse | Compile | Total |
|--------|------|-------|---------|-------|
| echo | 19KB | <1ms | <2ms | ~3ms |
| reflection | 66KB | <2ms | <5ms | ~7ms |
| sequential | 23KB | <1ms | <3ms | ~4ms |
| parallel | 31KB | <1ms | <3ms | ~4ms |
| react | 33KB | <1ms | <3ms | ~4ms |

### Bundle Size Impact

| Framework | Base | + @agenkit/wasm | Total | Increase |
|-----------|------|-----------------|-------|----------|
| React | 143KB | 177KB | 320KB | +177KB |
| Vue | 118KB | 177KB | 295KB | +177KB |
| Svelte | 28KB | 177KB | 205KB | +177KB |
| Astro* | 0KB | 177KB | 177KB | +177KB |

*Astro ships zero JS by default (WASM only loaded on interaction)

## Development

### Project Structure

```
browser/
├── react-example/
│   ├── src/
│   │   ├── App.tsx         # React component
│   │   ├── main.tsx        # Entry point
│   │   └── index.css       # Styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── vue-example/
│   ├── src/
│   │   ├── App.vue         # Vue component
│   │   ├── main.ts         # Entry point
│   │   └── style.css       # Styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── svelte-example/
│   ├── src/
│   │   ├── App.svelte      # Svelte component
│   │   ├── main.ts         # Entry point
│   │   └── app.css         # Styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── astro-example/
│   ├── src/
│   │   └── pages/
│   │       └── index.astro # Astro page
│   ├── package.json
│   └── astro.config.mjs
└── README.md               # This file
```

### Common Issues

**WASM Module Not Found:**
```
Error: Failed to fetch WASM file
```
**Solution:** Ensure @agenkit/wasm is built (`npm run build` in packages/wasm)

**Memory Errors:**
```
Error: Out of memory
```
**Solution:** WASM memory automatically grows, but check browser console for limits

**CORS Errors:**
```
Access-Control-Allow-Origin error
```
**Solution:** Run dev servers (Vite/Astro handle CORS automatically)

## Deployment

### React/Vue/Svelte (Vite)

```bash
npm run build
```

Output: `dist/` directory ready for static hosting

**Deploy to:**
- Vercel: `vercel --prod`
- Netlify: `netlify deploy --prod`
- Cloudflare Pages: `wrangler pages publish dist`

### Astro

```bash
npm run build
```

Output: `dist/` directory with pre-rendered pages

**Deploy to:**
- Vercel: `vercel --prod` (SSR enabled)
- Netlify: `netlify deploy --prod`
- Cloudflare Pages: `wrangler pages publish dist`

## Browser Support

| Browser | Version | WASM Support | Notes |
|---------|---------|--------------|-------|
| Chrome | 57+ | ✅ | Full support |
| Firefox | 52+ | ✅ | Full support |
| Safari | 11+ | ✅ | Full support |
| Edge | 16+ | ✅ | Full support |
| Opera | 44+ | ✅ | Full support |

**Mobile:**
- iOS Safari 11+ ✅
- Chrome Android 57+ ✅
- Samsung Internet 7+ ✅

## Security

All WASM modules run in a sandboxed environment:

✅ **No file system access** (unless explicitly granted via WASI)
✅ **No network access** (unless explicitly granted)
✅ **Memory isolated** from host JavaScript
✅ **Deterministic execution**

## Contributing

Contributions welcome! To add a new framework example:

1. Create `{framework}-example/` directory
2. Follow existing structure
3. Use @agenkit/wasm API consistently
4. Add to this README
5. Test locally
6. Submit PR

## Resources

- [@agenkit/wasm Documentation](../../packages/wasm/README.md)
- [WebAssembly MDN](https://developer.mozilla.org/en-US/docs/WebAssembly)
- [WASI](https://wasi.dev/)
- [React](https://react.dev/)
- [Vue](https://vuejs.org/)
- [Svelte](https://svelte.dev/)
- [Astro](https://astro.build/)

## License

MIT

## Links

- [Agenkit Repository](https://github.com/agenkit/agenkit)
- [Issue #288](https://github.com/agenkit/agenkit/issues/288)
- [WASM Language Choices](../../docs/WASM_LANGUAGE_CHOICES.md)
