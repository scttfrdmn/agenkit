# WASM v1.0 Implementation Plan - Complete Browser Story

**Target Date**: Early April 2026 (Conference)
**Duration**: 6-8 weeks (February 24 - March 31, 2026)
**Scope**: Option 3 - Comprehensive WASM with browser examples

---

## Executive Summary

Implement complete WebAssembly support across 3 languages (Rust, C++, Zig) with browser integration examples, enabling Agenkit agents to run natively in web browsers for the v1.0 release.

**Key Deliverables**:
- ✅ All 18 patterns working in Rust WASM (fix tokio incompatibility)
- ✅ C++ WASM via Emscripten
- ✅ Zig native WASM support
- ✅ Browser examples: React, Vue, Svelte
- ✅ NPM package: @agenkit/wasm
- ✅ Automated browser testing
- ✅ Performance benchmarks

---

## Phase 1: Rust WASM Completion (Weeks 1-2)

### Current Status
- **Working (5/18)**: Reflection, Agents-as-Tools, Orchestration (sequential), ReAct, Conversational
- **Broken (6/18)**: Task, Planning, Multiagent, Autonomous, Memory Hierarchy, Reasoning with Tools
- **Not Yet Implemented (7/18)**: Router, Fallback, Collaborative, HumanInLoop, Supervisor, OrchestrationPatterns, ReasoningWithTools

**Root Cause**: Patterns use tokio for async runtime, which doesn't work in WASM

### Solution Strategy: wasm-bindgen-futures

Replace tokio with browser-native Promise runtime:

```rust
// BEFORE (Native Rust - uses tokio)
use tokio::task;

pub async fn process(&self, message: Message) -> Result<Message> {
    let result = task::spawn(async move {
        // async work
    }).await?;
    Ok(result)
}

// AFTER (WASM - uses browser Promises)
use wasm_bindgen_futures::spawn_local;
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub async fn process(&self, message: Message) -> Result<JsValue> {
    let promise = js_sys::Promise::new(&mut |resolve, reject| {
        spawn_local(async move {
            // async work
            resolve.call1(&JsValue::NULL, &result)?;
        });
    });

    JsValue::from_promise(promise).await
}
```

### Implementation Plan

#### Week 1: Fix 6 Broken Patterns

**Day 1-2: Task + Planning**
- File: `agenkit-rust/src/patterns/task.rs`
- Changes:
  - Replace `tokio::spawn` with `spawn_local`
  - Replace `tokio::time::sleep` with `gloo_timers::future::TimeoutFuture`
  - Add `#[cfg(target_arch = "wasm32")]` conditional compilation
  - Add WASM-specific error types

- File: `agenkit-rust/src/patterns/planning.rs`
- Changes: Same pattern replacement as Task

**Day 3-4: Multiagent + Autonomous**
- File: `agenkit-rust/src/patterns/multiagent.rs`
- Changes:
  - Replace parallel execution with browser-native `Promise.all()`
  - Use `js_sys::Promise` for coordination

- File: `agenkit-rust/src/patterns/autonomous.rs`
- Changes:
  - Replace tokio channels with `web_sys::MessageChannel`
  - Use browser events for agent communication

**Day 5: Memory Hierarchy + Reasoning with Tools**
- File: `agenkit-rust/src/patterns/memory.rs`
- Changes:
  - Use `web_sys::Storage` API for persistence
  - IndexedDB for larger memory storage

- File: `agenkit-rust/src/patterns/reasoning_with_tools.rs`
- Changes: Tool execution via browser-safe APIs

#### Week 2: Implement 7 New Patterns (WASM-first)

**Day 1-2: Router + Fallback + Collaborative**
- Implement directly with wasm-bindgen-futures
- No tokio dependency from start
- Test in browser immediately

**Day 3-4: HumanInLoop + Supervisor + OrchestrationPatterns**
- Browser-native implementations
- Use DOM events for human-in-loop interactions

**Day 5: ReasoningWithTools + Testing**
- Complete WASM test suite
- Verify all 18 patterns work in browser

### Testing Strategy

Create browser test harness:

```rust
// agenkit-rust/tests/wasm_patterns.rs
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen_test]
async fn test_all_patterns_in_browser() {
    // Test each pattern
    test_router().await;
    test_fallback().await;
    // ... all 18 patterns
}
```

Run with: `wasm-pack test --headless --firefox`

---

## Phase 2: Multi-Language WASM (Weeks 3-4)

### C++ WASM via Emscripten

**Goal**: Compile agenkit-cpp to WASM using Emscripten

#### Week 3: C++ WASM Setup

**Day 1: Emscripten Build System**

Create new CMake configuration:

```cmake
# agenkit-cpp/CMakeLists.txt (add WASM target)

if(EMSCRIPTEN)
    # WASM-specific settings
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s WASM=1 -s ASYNCIFY")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s MODULARIZE=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s EXPORT_NAME='createAgenkitModule'")

    # Disable features not needed in WASM
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s NO_EXIT_RUNTIME=1")
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -s ALLOW_MEMORY_GROWTH=1")
endif()
```

**Build script**:
```bash
#!/bin/bash
# agenkit-cpp/scripts/build_wasm.sh

emcmake cmake -B build-wasm -DEMSCRIPTEN=ON
emmake make -C build-wasm
```

**Day 2-3: Pattern Adaptation**

Async patterns need special handling:

```cpp
// agenkit-cpp/src/patterns/async_base.hpp

#ifdef __EMSCRIPTEN__
#include <emscripten/emscripten.h>
#include <emscripten/bind.h>

// Use Emscripten's async support
EM_ASYNC_JS(Message, process_async, (Message msg), {
    return await processMessage(msg);
});
#else
// Native async/await
std::future<Message> process_async(Message msg) {
    return std::async(std::launch::async, [msg]() {
        return processMessage(msg);
    });
}
#endif
```

**Day 4-5: Test All Patterns**

Create WASM test suite:
```bash
node agenkit-cpp/build-wasm/tests/test_patterns.js
```

### Zig WASM (Native Support)

**Goal**: Leverage Zig's excellent WASM support

#### Week 4: Zig WASM Implementation

**Day 1: Build Configuration**

Update build.zig:

```zig
// agenkit-zig/build.zig

const wasm = b.option(bool, "wasm", "Build for WebAssembly") orelse false;

if (wasm) {
    const target = b.resolveTargetQuery(.{
        .cpu_arch = .wasm32,
        .os_tag = .freestanding,
    });

    const lib = b.addSharedLibrary(.{
        .name = "agenkit",
        .root_source_file = b.path("src/wasm_entry.zig"),
        .target = target,
        .optimize = optimize,
    });

    // Export WASM functions
    lib.rdynamic = true;
    b.installArtifact(lib);
}
```

**Day 2: WASM Entry Point**

```zig
// agenkit-zig/src/wasm_entry.zig

const std = @import("std");
const patterns = @import("patterns.zig");

// Allocator for WASM (use GPA for leak detection in dev)
var gpa = std.heap.GeneralPurposeAllocator(.{}){};
const allocator = gpa.allocator();

// Export patterns to JavaScript
export fn createRouterAgent(classifier_ptr: [*]const u8, len: usize) [*]u8 {
    const config = parseConfig(classifier_ptr[0..len]);
    const agent = patterns.RouterAgent.init(allocator, config) catch return null;
    return @ptrCast(agent);
}

export fn processMessage(agent_ptr: [*]u8, msg_ptr: [*]const u8, msg_len: usize) [*]u8 {
    const agent = @ptrCast(*patterns.RouterAgent, @alignCast(@alignOf(*patterns.RouterAgent), agent_ptr));
    const msg_json = msg_ptr[0..msg_len];
    const message = parseMessage(msg_json);
    const result = agent.process(message) catch return null;
    return serializeResult(result);
}

export fn destroyAgent(agent_ptr: [*]u8) void {
    // Cleanup
}
```

**Day 3-4: Pattern Exports**

Export all 18 patterns with JavaScript-friendly APIs:

```zig
// Generate TypeScript definitions
export fn getPatternMetadata() [*]const u8 {
    const metadata =
        \\{
        \\  "patterns": [
        \\    {"name": "RouterAgent", "create": "createRouterAgent"},
        \\    {"name": "FallbackAgent", "create": "createFallbackAgent"},
        \\    ...
        \\  ]
        \\}
    ;
    return metadata.ptr;
}
```

**Day 5: Testing**

```bash
zig build -Dwasm=true
node test_zig_wasm.js
```

---

## Phase 3: Browser Integration & Examples (Weeks 5-6)

### NPM Package Structure

```
@agenkit/wasm/
├── package.json
├── README.md
├── dist/
│   ├── rust/
│   │   ├── agenkit_bg.wasm
│   │   ├── agenkit.js
│   │   └── agenkit.d.ts
│   ├── cpp/
│   │   ├── agenkit.wasm
│   │   └── agenkit.js
│   └── zig/
│       ├── agenkit.wasm
│       └── agenkit.js
├── src/
│   ├── index.ts          # Main entry point
│   ├── rust-wrapper.ts   # Rust WASM wrapper
│   ├── cpp-wrapper.ts    # C++ WASM wrapper
│   └── zig-wrapper.ts    # Zig WASM wrapper
└── examples/
    ├── react/
    ├── vue/
    └── svelte/
```

#### Week 5: NPM Package Development

**Day 1: TypeScript Wrapper**

```typescript
// @agenkit/wasm/src/index.ts

export type Language = 'rust' | 'cpp' | 'zig';

export interface AgenkitWASM {
    loadPattern(name: string): Promise<Pattern>;
    createAgent(pattern: Pattern, config: any): Promise<Agent>;
}

export async function createAgenkit(lang: Language = 'rust'): Promise<AgenkitWASM> {
    switch (lang) {
        case 'rust':
            return await loadRustWASM();
        case 'cpp':
            return await loadCppWASM();
        case 'zig':
            return await loadZigWASM();
    }
}

// Unified API across all languages
export class Agent {
    constructor(private impl: any, private lang: Language) {}

    async process(message: Message): Promise<Message> {
        // Delegate to language-specific implementation
        return this.impl.process(message);
    }
}
```

**Day 2: Rust Wrapper**

```typescript
// @agenkit/wasm/src/rust-wrapper.ts

import init, * as wasm from '../dist/rust/agenkit.js';

export async function loadRustWASM(): Promise<AgenkitWASM> {
    await init();

    return {
        async loadPattern(name: string): Promise<Pattern> {
            return wasm[`create_${name}`];
        },

        async createAgent(pattern: Pattern, config: any): Promise<Agent> {
            const rustAgent = await pattern(config);
            return new Agent(rustAgent, 'rust');
        }
    };
}
```

**Day 3: Package Configuration**

```json
// @agenkit/wasm/package.json
{
  "name": "@agenkit/wasm",
  "version": "1.0.0",
  "description": "Agenkit WebAssembly bindings for browser-based AI agents",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": [
    "dist/**/*"
  ],
  "scripts": {
    "build": "tsc && npm run build:rust && npm run build:cpp && npm run build:zig",
    "build:rust": "cd ../agenkit-rust && wasm-pack build --target web --out-dir ../wasm-package/dist/rust",
    "build:cpp": "cd ../agenkit-cpp && ./scripts/build_wasm.sh",
    "build:zig": "cd ../agenkit-zig && zig build -Dwasm=true",
    "test": "vitest",
    "prepublish": "npm run build"
  },
  "keywords": [
    "ai",
    "agents",
    "wasm",
    "webassembly",
    "browser",
    "llm"
  ],
  "peerDependencies": {
    "react": ">=18.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",
    "@types/node": "^20.0.0"
  }
}
```

**Day 4-5: Testing Framework**

```typescript
// @agenkit/wasm/tests/browser.test.ts

import { describe, it, expect } from 'vitest';
import { createAgenkit } from '../src';

describe('Browser Integration', () => {
    it('should load Rust WASM', async () => {
        const agenkit = await createAgenkit('rust');
        expect(agenkit).toBeDefined();
    });

    it('should create and run RouterAgent', async () => {
        const agenkit = await createAgenkit('rust');
        const pattern = await agenkit.loadPattern('RouterAgent');
        const agent = await agenkit.createAgent(pattern, {
            routes: { greeting: 'GreetingAgent', help: 'HelpAgent' }
        });

        const result = await agent.process({ content: 'hello' });
        expect(result.content).toBeDefined();
    });

    it('should work across all 3 languages', async () => {
        for (const lang of ['rust', 'cpp', 'zig'] as const) {
            const agenkit = await createAgenkit(lang);
            const pattern = await agenkit.loadPattern('SequentialAgent');
            const agent = await agenkit.createAgent(pattern, { agents: [] });

            const result = await agent.process({ content: 'test' });
            expect(result).toBeDefined();
        }
    });
});
```

#### Week 6: Browser Examples

**Day 1-2: React Example**

```typescript
// examples/react-chat-agent/src/App.tsx

import React, { useState, useEffect } from 'react';
import { createAgenkit, Agent } from '@agenkit/wasm';

export default function App() {
    const [agent, setAgent] = useState<Agent | null>(null);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // Initialize WASM agent
        async function init() {
            const agenkit = await createAgenkit('rust');
            const pattern = await agenkit.loadPattern('ConversationalAgent');
            const chatAgent = await agenkit.createAgent(pattern, {
                model: 'gpt-4',
                systemPrompt: 'You are a helpful assistant running in the browser via WASM.'
            });
            setAgent(chatAgent);
        }
        init();
    }, []);

    const handleSend = async () => {
        if (!agent || !input.trim()) return;

        setLoading(true);
        const userMessage = { role: 'user', content: input };
        setMessages([...messages, userMessage]);

        try {
            const response = await agent.process(userMessage);
            setMessages([...messages, userMessage, response]);
        } catch (error) {
            console.error('Agent error:', error);
        } finally {
            setLoading(false);
            setInput('');
        }
    };

    return (
        <div className="chat-container">
            <h1>Agenkit WASM Chat</h1>
            <div className="messages">
                {messages.map((msg, i) => (
                    <div key={i} className={`message ${msg.role}`}>
                        {msg.content}
                    </div>
                ))}
            </div>
            <div className="input-area">
                <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    disabled={!agent || loading}
                    placeholder={agent ? "Type a message..." : "Loading WASM..."}
                />
                <button onClick={handleSend} disabled={!agent || loading}>
                    Send
                </button>
            </div>
        </div>
    );
}
```

**Day 3: Vue Example**

```vue
<!-- examples/vue-agent-demo/src/App.vue -->

<template>
  <div class="agent-demo">
    <h1>Agenkit WASM - Pattern Showcase</h1>

    <select v-model="selectedPattern" @change="loadPattern">
      <option value="router">Router Agent</option>
      <option value="fallback">Fallback Agent</option>
      <option value="collaborative">Collaborative Agent</option>
      <option value="sequential">Sequential Agent</option>
    </select>

    <div class="demo-area">
      <component :is="currentDemo" :agent="agent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { createAgenkit, Agent } from '@agenkit/wasm';
import RouterDemo from './components/RouterDemo.vue';
import FallbackDemo from './components/FallbackDemo.vue';

const selectedPattern = ref('router');
const agent = ref<Agent | null>(null);
const agenkit = ref(null);

onMounted(async () => {
  agenkit.value = await createAgenkit('rust');
  await loadPattern();
});

async function loadPattern() {
  if (!agenkit.value) return;

  const pattern = await agenkit.value.loadPattern(
    selectedPattern.value + 'Agent'
  );
  agent.value = await agenkit.value.createAgent(pattern, {
    // Pattern-specific config
  });
}
</script>
```

**Day 4: Svelte Example**

```svelte
<!-- examples/svelte-agent-workflow/src/App.svelte -->

<script lang="ts">
import { onMount } from 'svelte';
import { createAgenkit, type Agent } from '@agenkit/wasm';

let agent: Agent | null = null;
let steps: string[] = [];
let currentStep = 0;

onMount(async () => {
    const agenkit = await createAgenkit('rust');
    const pattern = await agenkit.loadPattern('PlanningAgent');
    agent = await agenkit.createAgent(pattern, {
        planner: 'gpt-4',
        maxSteps: 10
    });
});

async function executeWorkflow(task: string) {
    if (!agent) return;

    steps = [];
    currentStep = 0;

    const result = await agent.process({ content: task });
    steps = result.metadata.steps;

    // Animate through steps
    for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        currentStep = i;
    }
}
</script>

<div class="workflow">
    <h1>WASM Planning Agent Workflow</h1>

    <button on:click={() => executeWorkflow('Plan a birthday party')}>
        Start Workflow
    </button>

    {#each steps as step, i}
        <div class="step" class:active={i === currentStep}>
            {i + 1}. {step}
        </div>
    {/each}
</div>
```

**Day 5: Documentation & Publishing**

Create comprehensive README:

```markdown
# @agenkit/wasm - Browser-Native AI Agents

Run Agenkit agents directly in the browser using WebAssembly. Zero server required.

## Quick Start

```bash
npm install @agenkit/wasm
```

```typescript
import { createAgenkit } from '@agenkit/wasm';

const agenkit = await createAgenkit('rust');
const pattern = await agenkit.loadPattern('ConversationalAgent');
const agent = await agenkit.createAgent(pattern, { model: 'gpt-4' });

const response = await agent.process({
    role: 'user',
    content: 'Hello!'
});
```

## Choose Your Language

```typescript
// Rust (fast compilation, great debugging)
const rustKit = await createAgenkit('rust');

// C++ (maximum performance)
const cppKit = await createAgenkit('cpp');

// Zig (smallest bundle size)
const zigKit = await createAgenkit('zig');
```

All three provide identical APIs and behavior!
```

---

## Phase 4: Testing & CI/CD (Week 7)

### Automated Browser Testing

**Day 1-2: Playwright Setup**

```typescript
// tests/browser/playwright.config.ts

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests/browser',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,

    use: {
        baseURL: 'http://localhost:5173',
        trace: 'on-first-retry',
    },

    projects: [
        { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
        { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
        { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    ],

    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
    },
});
```

**Browser Tests**:

```typescript
// tests/browser/patterns.spec.ts

import { test, expect } from '@playwright/test';

test.describe('WASM Pattern Tests', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForSelector('#wasm-ready');
    });

    test('RouterAgent classifies and routes correctly', async ({ page }) => {
        await page.click('#load-router');
        await page.fill('#message-input', 'Help with billing');
        await page.click('#send');

        const result = await page.textContent('#agent-output');
        expect(result).toContain('Billing specialist');
    });

    test('FallbackAgent retries on failure', async ({ page }) => {
        await page.click('#load-fallback');
        await page.fill('#message-input', 'test message');
        await page.click('#send');

        const attempts = await page.locator('.attempt').count();
        expect(attempts).toBeGreaterThan(1);
    });

    test('All 18 patterns load successfully', async ({ page }) => {
        const patterns = [
            'SequentialAgent', 'ParallelAgent', 'RouterAgent',
            'FallbackAgent', 'Task', 'ReflectionAgent',
            // ... all 18
        ];

        for (const pattern of patterns) {
            await page.selectOption('#pattern-select', pattern);
            await expect(page.locator('#status')).toHaveText('Ready');
        }
    });
});

test.describe('Cross-Language Parity', () => {
    for (const lang of ['rust', 'cpp', 'zig']) {
        test(`${lang}: all patterns work identically`, async ({ page }) => {
            await page.selectOption('#language', lang);

            // Test RouterAgent
            await page.click('#load-router');
            const routerResult = await page.textContent('#output');

            // Switch language
            await page.selectOption('#language', 'rust');
            await page.click('#load-router');
            const rustResult = await page.textContent('#output');

            expect(routerResult).toEqual(rustResult);
        });
    }
});
```

**Day 3-4: Performance Benchmarks**

```typescript
// benchmarks/wasm_performance.ts

import { benchmark } from './utils';
import { createAgenkit } from '@agenkit/wasm';

async function benchmarkPattern(lang: string, pattern: string, iterations: number) {
    const agenkit = await createAgenkit(lang as any);
    const patternObj = await agenkit.loadPattern(pattern);
    const agent = await agenkit.createAgent(patternObj, {});

    const start = performance.now();
    for (let i = 0; i < iterations; i++) {
        await agent.process({ content: 'benchmark message' });
    }
    const end = performance.now();

    return {
        language: lang,
        pattern,
        totalTime: end - start,
        avgTime: (end - start) / iterations,
        opsPerSecond: iterations / ((end - start) / 1000)
    };
}

async function runAllBenchmarks() {
    const results = [];
    const patterns = ['SequentialAgent', 'ParallelAgent', 'RouterAgent', 'FallbackAgent'];
    const languages = ['rust', 'cpp', 'zig'];

    for (const lang of languages) {
        for (const pattern of patterns) {
            const result = await benchmarkPattern(lang, pattern, 1000);
            results.push(result);
            console.log(`${lang} ${pattern}: ${result.avgTime.toFixed(2)}ms avg`);
        }
    }

    // Generate comparison matrix
    generateComparisonMatrix(results);
}
```

**Day 5: CI/CD Integration**

```yaml
# .github/workflows/wasm-tests.yml

name: WASM Tests

on:
  push:
    branches: [main]
  pull_request:
    paths:
      - 'agenkit-rust/**'
      - 'agenkit-cpp/**'
      - 'agenkit-zig/**'
      - '@agenkit/wasm/**'

jobs:
  build-wasm:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        language: [rust, cpp, zig]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Rust + wasm-pack
        if: matrix.language == 'rust'
        run: |
          curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

      - name: Setup Emscripten
        if: matrix.language == 'cpp'
        run: |
          git clone https://github.com/emscripten-core/emsdk.git
          cd emsdk && ./emsdk install latest && ./emsdk activate latest

      - name: Setup Zig
        if: matrix.language == 'zig'
        uses: goto-bus-stop/setup-zig@v2
        with:
          version: 0.12.0

      - name: Build WASM
        run: |
          cd agenkit-${{ matrix.language }}
          ./scripts/build_wasm.sh

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: wasm-${{ matrix.language }}
          path: agenkit-${{ matrix.language }}/dist/*.wasm

  browser-tests:
    needs: build-wasm
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Download WASM artifacts
        uses: actions/download-artifact@v3

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20

      - name: Install dependencies
        run: |
          cd @agenkit/wasm
          npm install

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run browser tests
        run: |
          cd @agenkit/wasm
          npm run test:browser

      - name: Run benchmarks
        run: |
          npm run benchmark

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-results
          path: playwright-report/

  publish-npm:
    needs: browser-tests
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          registry-url: 'https://registry.npmjs.org'

      - name: Publish to NPM
        run: |
          cd @agenkit/wasm
          npm publish --access public
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
```

---

## Phase 5: Performance Optimization & Polish (Week 8)

### Day 1-2: Bundle Size Optimization

**Goal**: Minimize WASM bundle size for faster loading

```bash
# Rust optimization
wasm-pack build --target web --release -- -Z build-std=std,panic_abort -Z build-std-features=panic_immediate_abort
wasm-opt -Oz -o output.wasm input.wasm

# Expected sizes:
# Rust: ~300KB (gzipped)
# C++: ~250KB (gzipped)
# Zig: ~180KB (gzipped) ← Smallest!
```

**Code splitting**:

```typescript
// Load patterns on-demand
export async function loadPattern(name: string) {
    // Lazy load pattern-specific WASM
    const module = await import(`./patterns/${name}.wasm`);
    return module;
}
```

### Day 3-4: Performance Profiling

**Browser DevTools profiling**:
- Memory usage: Target <50MB for all 18 patterns
- Startup time: Target <500ms to first interaction
- Message latency: Target <10ms overhead vs native

**Optimization areas**:
1. Reduce serialization overhead (use binary encoding)
2. Cache WASM module instantiation
3. Use SharedArrayBuffer for zero-copy message passing
4. Optimize hot paths identified in profiling

### Day 5: Documentation & Examples Polish

**Final checklist**:
- [ ] All examples have live demos
- [ ] README has GIFs/videos of examples
- [ ] API documentation complete
- [ ] Migration guide from Node.js to browser
- [ ] Performance comparison table
- [ ] Bundle size comparison
- [ ] Browser compatibility table

---

## Success Criteria

### Technical Requirements

**All 18 Patterns Working**:
- [ ] SequentialAgent ✅
- [ ] ParallelAgent ✅
- [ ] RouterAgent ✅
- [ ] FallbackAgent ✅
- [ ] Task ✅
- [ ] ReflectionAgent ✅
- [ ] ReActAgent ✅
- [ ] PlanningAgent ✅
- [ ] ConversationalAgent ✅
- [ ] AgentAsTool ✅
- [ ] AutonomousAgent ✅
- [ ] MultiagentOrchestration ✅
- [ ] MemoryHierarchy ✅
- [ ] CollaborativeAgent ✅
- [ ] HumanInLoopAgent ✅
- [ ] OrchestrationPatterns ✅
- [ ] ReasoningWithTools ✅
- [ ] SupervisorAgent ✅

**Multi-Language Support**:
- [ ] Rust WASM (all 18 patterns)
- [ ] C++ WASM via Emscripten (all 18 patterns)
- [ ] Zig native WASM (all 18 patterns)
- [ ] Identical APIs across languages
- [ ] Behavioral equivalence verified

**Browser Integration**:
- [ ] React example working
- [ ] Vue example working
- [ ] Svelte example working
- [ ] Vanilla JS example
- [ ] NPM package published (@agenkit/wasm)

**Testing**:
- [ ] Playwright tests passing (Chrome, Firefox, Safari)
- [ ] All 18 patterns tested in browser
- [ ] Cross-language parity tests passing
- [ ] Performance benchmarks collected

**CI/CD**:
- [ ] Automated WASM builds
- [ ] Automated browser testing
- [ ] Automated NPM publishing
- [ ] Performance regression detection

### Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| **Bundle Size** (gzipped) | <500KB total | TBD |
| **Startup Time** | <500ms to first interaction | TBD |
| **Message Latency** | <10ms overhead | TBD |
| **Memory Usage** | <50MB for all patterns | TBD |
| **Browser Support** | Chrome 90+, Firefox 88+, Safari 14+ | TBD |

### Conference Deliverable

**Live Demo** (5-minute presentation):

1. **Opening** (30s): "Agenkit v1.0 - AI agents in any language, including your browser"

2. **Quick Start** (1min):
   ```bash
   npm install @agenkit/wasm
   ```
   Show 10 lines of code creating a conversational agent in React

3. **Pattern Showcase** (2min):
   - Live browser demo switching between patterns
   - RouterAgent routing messages
   - FallbackAgent recovering from failures
   - CollaborativeAgent showing multi-agent coordination
   - Show identical behavior in Rust/C++/Zig

4. **Performance** (1min):
   - Show benchmark comparison
   - Highlight <500ms startup, <10ms latency
   - Show bundle sizes

5. **Closing** (30s):
   - "100% pattern parity across 6 languages"
   - "All 18 patterns work in the browser"
   - "Production-ready with 2,101+ tests"
   - "Try it now: npm install @agenkit/wasm"

---

## Risk Mitigation

### Technical Risks

**Risk 1**: Tokio incompatibility harder to resolve than expected
- **Mitigation**: Rust implementation is highest priority (Week 1)
- **Fallback**: Can ship with 5 working patterns if needed
- **Contingency**: Focus on C++/Zig which don't have this issue

**Risk 2**: Emscripten compilation issues
- **Mitigation**: Start C++ WASM early (Week 3)
- **Fallback**: Can ship Rust + Zig only
- **Contingency**: Extensive Emscripten documentation and community

**Risk 3**: Browser API limitations
- **Mitigation**: Test in actual browsers early (Week 2)
- **Fallback**: Document limitations, provide polyfills
- **Contingency**: Some patterns may be "browser-limited"

### Schedule Risks

**Risk 1**: WASM work takes longer than 6-8 weeks
- **Mitigation**: Parallel work on Rust/C++/Zig (Weeks 1-4)
- **Mitigation**: Can cut scope (e.g., fewer examples)
- **Priority**: Rust WASM completion is MVP

**Risk 2**: Conference date moves earlier
- **Mitigation**: Weekly progress reviews
- **Mitigation**: Parallel work streams
- **Minimum Viable Demo**: Rust WASM + React example

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|--------------|
| **1** | Rust WASM fixes | 6 broken patterns working |
| **2** | Rust WASM new patterns | 7 new patterns implemented |
| **3** | C++ WASM setup | Emscripten build + pattern adaptation |
| **4** | Zig WASM | Native WASM build + exports |
| **5** | NPM package | @agenkit/wasm published |
| **6** | Browser examples | React, Vue, Svelte demos |
| **7** | Testing & CI | Playwright tests, benchmarks |
| **8** | Optimization & polish | Bundle size, performance, docs |

**Start Date**: February 24, 2026
**Conference Date**: Early April 2026
**Buffer**: ~1 week for unexpected issues

---

## Post-Conference (April+)

**Additional enhancements** (not blocking v1.0):

1. **WASM Streaming Compilation**:
   - Use `WebAssembly.instantiateStreaming()` for faster loading
   - Implement progressive pattern loading

2. **Service Worker Integration**:
   - Cache WASM modules for offline operation
   - Background agent execution

3. **WebGPU Acceleration**:
   - Use WebGPU for LLM inference in browser
   - Parallel pattern execution with GPU

4. **React Native**:
   - Extend WASM support to React Native
   - Mobile agent deployment

---

## Getting Started

### Immediate Next Steps (Week 1, Day 1)

1. **Setup Development Environment**:
   ```bash
   # Install wasm-pack
   curl https://rustwasm.github.io/wasm-pack/installer/init.sh -sSf | sh

   # Install wasm-bindgen
   cargo install wasm-bindgen-cli

   # Verify installation
   wasm-pack --version
   ```

2. **Create WASM Branch**:
   ```bash
   git checkout -b wasm-v1-implementation
   ```

3. **Start with Task Pattern**:
   ```bash
   cd agenkit-rust
   # Edit src/patterns/task.rs
   # Replace tokio with wasm-bindgen-futures
   ```

4. **Test in Browser**:
   ```bash
   wasm-pack build --target web
   python -m http.server 8000
   # Open localhost:8000/test.html
   ```

**Let's build the future of browser-based AI agents! 🚀**

---

**Document Version**: 1.0
**Created**: December 2025
**Target**: v1.0.0 Release (Early April 2026)
**Conference**: Early April 2026
