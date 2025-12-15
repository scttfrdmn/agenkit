# @agenkit/wasm

WebAssembly bindings for Agenkit - Run AI agents in browsers, edge environments, and serverless functions.

## Features

- 🚀 **Lightweight** - WASM modules range from 4.5KB to 66KB
- 🌐 **Universal** - Works in browsers, Node.js, Deno, and Bun
- ⚡ **Fast** - Compiled from Zig for optimal performance
- 🔒 **Secure** - Sandboxed execution with WASI
- 📦 **Zero Dependencies** - No runtime dependencies

## Installation

```bash
npm install @agenkit/wasm
```

## Quick Start

### Node.js

```typescript
import { createZigAgent } from '@agenkit/wasm';

const agent = await createZigAgent('echo_example', 'my-echo', ['echo']);

const result = await agent.process({
  role: 'user',
  content: 'Hello, WASM!'
});

console.log(result.message?.content);
// Output: Echo from my-echo: Hello, WASM!
```

### Browser

```html
<script type="module">
  import { createZigAgent } from 'https://unpkg.com/@agenkit/wasm';

  const agent = await createZigAgent('echo_example', 'browser-agent');

  const result = await agent.process({
    role: 'user',
    content: 'Running in the browser!'
  });

  console.log(result.message?.content);
</script>
```

## Available Modules

### Zig WASM Modules

The package includes 6 pre-compiled Zig WASM modules (ultra-lightweight):

| Module | Size | Description |
|--------|------|-------------|
| `agenkit` | 4.5KB | Core library |
| `echo_example` | 19KB | Simple echo agent |
| `reflection_example` | 66KB | Self-reflection pattern |
| `sequential_example` | 23KB | Sequential processing |
| `parallel_example` | 31KB | Parallel processing |
| `react_example` | 33KB | Reasoning + acting pattern |

### Rust WASM Module

The package also includes Rust WASM with advanced reasoning capabilities:

| Module | Size | Description |
|--------|------|-------------|
| `agenkit_rust` | 334KB | Full agenkit library with all 18 patterns, reasoning techniques (CoT, ToT, Self-Consistency), and wasm-bindgen interop |

**Note:** Rust WASM is larger but provides the complete agenkit feature set including:
- All 18 agent patterns
- Chain-of-Thought (CoT) reasoning
- Tree-of-Thought (ToT) reasoning
- Self-Consistency decoding
- Advanced middleware and evaluation
- Better JavaScript interop via wasm-bindgen

## API Reference

### createZigAgent()

Create and load a Zig WASM agent in one step.

```typescript
async function createZigAgent(
  moduleName: string,
  agentName: string,
  capabilities?: string[],
  debug?: boolean
): Promise<ZigAgent>
```

**Parameters:**
- `moduleName` - Name of the WASM module (e.g., 'echo_example')
- `agentName` - Custom name for the agent instance
- `capabilities` - Array of capability strings (optional)
- `debug` - Enable debug logging (optional, default: false)

**Returns:** Initialized `ZigAgent` instance

### ZigAgent

Main agent class for Zig WASM modules.

```typescript
class ZigAgent {
  name: string;
  capabilities: string[];

  async load(moduleName: string, debug?: boolean): Promise<void>;
  async process(message: Message): Promise<AgentResult>;
  isReady(): boolean;
  getModuleInfo(): object | null;
}
```

### createRustAgent()

Create and load the Rust WASM agent in one step.

```typescript
async function createRustAgent(
  agentName: string,
  capabilities?: string[],
  debug?: boolean
): Promise<RustAgent>
```

**Parameters:**
- `agentName` - Custom name for the agent instance
- `capabilities` - Array of capability strings (optional)
- `debug` - Enable debug logging (optional, default: false)

**Returns:** Initialized `RustAgent` instance

**Example:**
```typescript
import { createRustAgent } from '@agenkit/wasm';

const agent = await createRustAgent('reasoning-agent', ['cot', 'tot', 'self-consistency']);

const result = await agent.process({
  role: 'user',
  content: 'What is 2 + 2?'
});

console.log(result.message?.content);
```

### RustAgent

Main agent class for Rust WASM module (full feature set).

```typescript
class RustAgent {
  name: string;
  capabilities: string[];

  async load(debug?: boolean): Promise<void>;
  async process(message: Message): Promise<AgentResult>;
  isReady(): boolean;
  getModuleInfo(): object | null;
}
```

### loadWasmModule()

Low-level function to load any WASM module.

```typescript
async function loadWasmModule(options: LoaderOptions): Promise<WasmModule>
```

**Options:**
- `wasmPath` - Path to WASM file (URL or file path)
- `wasiImports` - Optional WASI imports (default: minimal WASI)
- `debug` - Enable debug logging (default: false)

### getAvailableModules()

Get list of bundled WASM modules.

```typescript
function getAvailableModules(): string[]
```

**Returns:** Array of module names

## Examples

### Pattern: Reflection

```typescript
import { createZigAgent } from '@agenkit/wasm';

// Create reflection agent
const agent = await createZigAgent(
  'reflection_example',
  'reflector',
  ['reflection', 'self-improvement']
);

// Process with reflection
const result = await agent.process({
  role: 'user',
  content: 'Analyze this code for improvements'
});

console.log(result.message?.content);
```

### Pattern: Sequential

```typescript
import { createZigAgent } from '@agenkit/wasm';

// Create sequential processing agent
const agent = await createZigAgent(
  'sequential_example',
  'pipeline',
  ['sequential', 'pipeline']
);

// Process sequentially
const result = await agent.process({
  role: 'user',
  content: 'Step 1 → Step 2 → Step 3'
});
```

### Pattern: Parallel

```typescript
import { createZigAgent } from '@agenkit/wasm';

// Create parallel processing agent
const agent = await createZigAgent(
  'parallel_example',
  'concurrent',
  ['parallel', 'concurrent']
);

// Process in parallel
const result = await agent.process({
  role: 'user',
  content: 'Task A + Task B + Task C'
});
```

### Custom WASM Module

```typescript
import { loadWasmModule } from '@agenkit/wasm';

// Load custom WASM file
const module = await loadWasmModule({
  wasmPath: './my-custom-agent.wasm',
  debug: true
});

console.log('Exports:', Object.keys(module.exports));
```

## Framework Integration

### React

```typescript
import { useState, useEffect } from 'react';
import { createZigAgent, ZigAgent } from '@agenkit/wasm';

function AgentComponent() {
  const [agent, setAgent] = useState<ZigAgent | null>(null);
  const [response, setResponse] = useState('');

  useEffect(() => {
    createZigAgent('echo_example', 'react-agent').then(setAgent);
  }, []);

  const handleSend = async (message: string) => {
    if (!agent) return;
    const result = await agent.process({
      role: 'user',
      content: message
    });
    setResponse(result.message?.content || '');
  };

  return (
    <div>
      <button onClick={() => handleSend('Hello!')}>
        Send Message
      </button>
      <p>{response}</p>
    </div>
  );
}
```

### Vue

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { createZigAgent } from '@agenkit/wasm';

const agent = ref(null);
const response = ref('');

onMounted(async () => {
  agent.value = await createZigAgent('echo_example', 'vue-agent');
});

const sendMessage = async (message: string) => {
  if (!agent.value) return;
  const result = await agent.value.process({
    role: 'user',
    content: message
  });
  response.value = result.message?.content || '';
};
</script>

<template>
  <div>
    <button @click="sendMessage('Hello!')">Send Message</button>
    <p>{{ response }}</p>
  </div>
</template>
```

### Svelte

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { createZigAgent } from '@agenkit/wasm';

  let agent = null;
  let response = '';

  onMount(async () => {
    agent = await createZigAgent('echo_example', 'svelte-agent');
  });

  async function sendMessage(message: string) {
    if (!agent) return;
    const result = await agent.process({
      role: 'user',
      content: message
    });
    response = result.message?.content || '';
  }
</script>

<div>
  <button on:click={() => sendMessage('Hello!')}>Send Message</button>
  <p>{response}</p>
</div>
```

### Astro

```astro
---
import { createZigAgent } from '@agenkit/wasm';

const agent = await createZigAgent('echo_example', 'astro-agent');
const result = await agent.process({
  role: 'user',
  content: 'Server-side WASM in Astro!'
});
---

<div>
  <h2>Agent Response:</h2>
  <p>{result.message?.content}</p>
</div>
```

## Language Support

This package currently includes **Zig** WASM modules. Support for additional languages:

### ✅ Zig (Included)
- Native WASM compilation
- 18/18 patterns available
- WASI support via wasm32-wasi target
- Ultra-small binary sizes (4.5K-89K)

### 🚧 Rust (Coming Soon)
- wasm-bindgen integration
- 18/18 patterns (fixes in progress)
- Compilation issues being resolved

### 🚧 C++ (Coming Soon)
- Emscripten compilation
- 46MB static library available
- Need to compile to .wasm executables

## Development

### Building from Source

```bash
# Install dependencies
npm install

# Build the package
npm run build

# Run in development mode
npm run dev

# Run tests
npm test
```

### Project Structure

```
@agenkit/wasm/
├── src/
│   ├── index.ts      # Main entry point
│   ├── types.ts      # TypeScript types
│   ├── loader.ts     # WASM loader
│   └── zig.ts        # Zig agent wrapper
├── wasm/             # WASM binaries
│   ├── agenkit.wasm
│   ├── echo_example.wasm
│   └── ...
├── dist/             # Built output
└── examples/         # Usage examples
```

## WASM Runtime Requirements

- **Node.js**: ≥18.0.0 (native WASM support)
- **Browsers**: Modern browsers with WebAssembly support
  - Chrome 57+
  - Firefox 52+
  - Safari 11+
  - Edge 16+

## Performance

WASM modules in this package are highly optimized:

- **Load Time**: <10ms for smallest modules
- **Memory**: Minimal footprint (starts at ~1MB)
- **Execution**: Near-native performance
- **Bundle Size**: 4.5KB-66KB per module

## Security

All WASM modules run in a sandboxed environment:

- ✅ No access to file system (without explicit WASI permissions)
- ✅ No access to network (without explicit imports)
- ✅ Memory isolated from host
- ✅ Deterministic execution

## License

MIT

## Links

- [Agenkit Documentation](https://github.com/agenkit/agenkit)
- [WASM Language Choices](../../docs/WASM_LANGUAGE_CHOICES.md)
- [Zig WASM Guide](../../agenkit-zig/README.md#webassembly-wasm-build)
- [Issue Tracker](https://github.com/agenkit/agenkit/issues)

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.
