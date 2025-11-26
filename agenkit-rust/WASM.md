# WebAssembly (WASM) Support

Agenkit Rust can compile to WebAssembly, enabling AI agents to run directly in web browsers.

## Prerequisites

### Install Rustup (Recommended)

Homebrew's Rust installation doesn't support WASM targets. Install rustup instead:

```bash
# Install rustup
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Add WASM target
rustup target add wasm32-unknown-unknown

# Install wasm-pack
cargo install wasm-pack
```

## Building for WASM

### Build WASM Module

```bash
cd agenkit-rust

# Build for web browsers
wasm-pack build --target web --features wasm --no-default-features

# Build for Node.js
wasm-pack build --target nodejs --features wasm --no-default-features

# Build for bundlers (webpack, rollup, etc.)
wasm-pack build --target bundler --features wasm --no-default-features
```

This creates a `pkg/` directory with:
- `agenkit.js` - JavaScript bindings
- `agenkit_bg.wasm` - Compiled WASM module
- `agenkit.d.ts` - TypeScript definitions
- `package.json` - NPM package metadata

### NPM Publishing

```bash
cd pkg
npm publish
```

## Browser Usage

### Example HTML

See `examples/wasm_browser_agent.html` for a complete example.

```html
<!DOCTYPE html>
<html>
<head>
    <title>Agenkit WASM Agent</title>
</head>
<body>
    <h1>AI Agent in Browser</h1>
    <button id="processBtn">Process Message</button>
    <div id="response"></div>

    <script type="module">
        import init, { WasmEchoAgent, JsMessage } from './pkg/agenkit.js';

        async function main() {
            // Initialize WASM module
            await init();

            // Create agent
            const agent = new WasmEchoAgent('my-agent');

            // Process message
            document.getElementById('processBtn').addEventListener('click', async () => {
                const message = new JsMessage('user', 'Hello from browser!');
                const response = await agent.process(message);
                document.getElementById('response').textContent = response.content;
            });
        }

        main();
    </script>
</body>
</html>
```

### Serving Locally

```bash
# Python 3
python3 -m http.server 8000

# Node.js
npx http-server -p 8000

# Navigate to http://localhost:8000/examples/wasm_browser_agent.html
```

## API Reference

### WasmEchoAgent

Simple echo agent for demonstration.

```javascript
const agent = new WasmEchoAgent('agent-name');
const response = await agent.process(message);
console.log(agent.name); // 'agent-name'
```

### JsMessage

JavaScript-compatible message type.

```javascript
const message = new JsMessage('user', 'Hello!');
console.log(message.role);    // 'user'
console.log(message.content); // 'Hello!'
```

### Utility Functions

```javascript
// Log to browser console
log('Debug message');

// Get current timestamp
const timestamp = now();
```

## Available Patterns in WASM

### ✅ WASM-Compatible Patterns

These patterns work in both native and WASM builds:

- **Reflection**: Iterative self-critique and refinement
- **Agents-as-Tools**: Hierarchical agent delegation
- **Orchestration**: Sequential and parallel composition (sequential only in WASM)
- **ReAct**: Reasoning and acting with tool use
- **Conversational**: Multi-turn dialogue management

### ⚠️ Native-Only Patterns

These patterns require tokio and are not available in WASM:

- **Task**: One-shot execution with lifecycle management
- **Planning**: Task decomposition and execution
- **Multiagent**: Multi-agent collaboration and consensus
- **Autonomous**: Goal-directed self-organizing agents
- **Memory Hierarchy**: Three-tier memory system
- **Reasoning with Tools**: Interleaved reasoning and tool usage

## Feature Flags

### Default Features

```toml
[dependencies]
agenkit = "0.1"
```

Includes all native features (tokio, HTTP transport, etc.)

### WASM Features

```toml
[dependencies]
agenkit = { version = "0.1", default-features = false, features = ["wasm"] }
```

Includes only WASM-compatible features.

## Architecture

### Native Build

- Uses **tokio** for async runtime
- Uses **reqwest** for HTTP client
- Uses **axum** for HTTP server
- Supports true parallel execution with `tokio::spawn`
- Full pattern support (11/11)

### WASM Build

- Uses **wasm-bindgen-futures** for async runtime
- No HTTP transport (browsers handle networking)
- Sequential execution (no tokio)
- Limited pattern support (5/11)
- Smaller bundle size

## Optimization

### Bundle Size

```bash
# Release build with optimizations
wasm-pack build --release --target web --features wasm --no-default-features

# Check bundle size
ls -lh pkg/*.wasm
```

### Cargo.toml Optimizations

Already configured in `Cargo.toml`:

```toml
[package.metadata.wasm-pack.profile.release]
wasm-opt = ["-O4", "--enable-mutable-globals"]

[profile.release]
opt-level = "z"        # Optimize for size
lto = true             # Link-time optimization
codegen-units = 1      # Better optimization
strip = true           # Strip debug symbols
```

### Expected Bundle Sizes

- Debug build: ~2-3 MB
- Release build: ~200-500 KB (with wasm-opt)
- gzipped: ~50-150 KB

## Limitations

### Browser Restrictions

- **No file system access**: Cannot use file-based storage
- **No native threading**: Sequential execution only
- **No HTTP server**: Agents cannot listen for connections
- **Same-origin policy**: Cross-origin requests require CORS

### Workarounds

1. **Storage**: Use browser APIs (localStorage, IndexedDB)
2. **Concurrency**: Use Web Workers for parallelism
3. **Networking**: Use browser fetch API through wasm-bindgen
4. **Communication**: Use postMessage for cross-origin

## Advanced Usage

### Custom Agent Wrapper

```rust
use agenkit::core::{Agent, Message};
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct MyWasmAgent {
    inner: Box<dyn Agent>,
}

#[wasm_bindgen]
impl MyWasmAgent {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Self {
        Self {
            inner: Box::new(MyCustomAgent::new()),
        }
    }

    pub async fn process(&self, message: JsMessage) -> Result<JsMessage, JsValue> {
        let msg: Message = message.into();
        let response = self.inner.process(msg).await
            .map_err(|e| JsValue::from_str(&e.to_string()))?;
        Ok(response.into())
    }
}
```

### Integration with JavaScript Frameworks

#### React

```jsx
import { useEffect, useState } from 'react';
import init, { WasmEchoAgent } from './pkg/agenkit';

function App() {
    const [agent, setAgent] = useState(null);

    useEffect(() => {
        init().then(() => {
            setAgent(new WasmEchoAgent('react-agent'));
        });
    }, []);

    const handleMessage = async () => {
        if (agent) {
            const response = await agent.process(
                new JsMessage('user', 'Hello!')
            );
            console.log(response);
        }
    };

    return <button onClick={handleMessage}>Send Message</button>;
}
```

#### Vue

```vue
<template>
    <button @click="handleMessage">Send Message</button>
</template>

<script>
import init, { WasmEchoAgent, JsMessage } from './pkg/agenkit';

export default {
    data() {
        return {
            agent: null
        };
    },
    async mounted() {
        await init();
        this.agent = new WasmEchoAgent('vue-agent');
    },
    methods: {
        async handleMessage() {
            const message = new JsMessage('user', 'Hello!');
            const response = await this.agent.process(message);
            console.log(response);
        }
    }
};
</script>
```

## Troubleshooting

### "Failed to fetch" Error

Ensure you're serving files over HTTP, not opening `file://` URLs:

```bash
python3 -m http.server 8000
```

### CORS Errors

When loading from a different origin, the server must send CORS headers:

```python
# Python 3 with CORS
python3 -m http.server 8000 --bind localhost
```

### Module Not Found

Ensure the path to `pkg/agenkit.js` is correct relative to your HTML file:

```javascript
// Correct relative path
import init from '../pkg/agenkit.js';

// Or absolute path
import init from '/pkg/agenkit.js';
```

### Memory Issues

For large agent workloads, increase WASM memory:

```javascript
const memory = new WebAssembly.Memory({
    initial: 256,  // 16 MB
    maximum: 512   // 32 MB
});

await init({ memory });
```

## Performance

### Benchmarks

| Operation | Native | WASM |
|-----------|--------|------|
| Message processing | ~1ms | ~2-3ms |
| Agent creation | ~10µs | ~50µs |
| Pattern execution | ~5ms | ~10-15ms |

### Optimization Tips

1. **Minimize object creation**: Reuse messages when possible
2. **Batch operations**: Process multiple messages in parallel
3. **Use Workers**: Offload computation to Web Workers
4. **Cache agents**: Create agents once, reuse many times

## CI/CD Integration

### GitHub Actions

```yaml
name: WASM Build

on: [push]

jobs:
  wasm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          target: wasm32-unknown-unknown
      - run: cargo install wasm-pack
      - run: wasm-pack build --target web --features wasm --no-default-features
      - run: wasm-pack test --node
```

## Resources

- [wasm-bindgen Guide](https://rustwasm.github.io/wasm-bindgen/)
- [wasm-pack Documentation](https://rustwasm.github.io/wasm-pack/)
- [Rust and WebAssembly Book](https://rustwasm.github.io/docs/book/)
- [web-sys Reference](https://rustwasm.github.io/wasm-bindgen/api/web_sys/)

## License

Apache-2.0
