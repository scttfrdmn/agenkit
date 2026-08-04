<script lang="ts">
  import { onMount } from 'svelte';
  import type { ZigAgent } from '@agenkit/wasm';

  declare const createZigAgent: (moduleName: string, agentName: string, capabilities?: string[], debug?: boolean) => Promise<ZigAgent>;

  let agent: ZigAgent | null = null;
  let loading = true;
  let error: string | null = null;
  let message = '';
  let response = '';
  let processing = false;
  let selectedModule = 'echo_example';

  const modules = [
    { id: 'echo_example', name: 'Echo', description: 'Simple echo agent' },
    { id: 'reflection_example', name: 'Reflection', description: 'Self-reflection pattern' },
    { id: 'sequential_example', name: 'Sequential', description: 'Sequential processing' },
    { id: 'parallel_example', name: 'Parallel', description: 'Parallel processing' },
    { id: 'react_example', name: 'ReAct', description: 'Reasoning + acting' },
  ];

  async function loadAgent() {
    try {
      loading = true;
      error = null;
      response = '';

      agent = await createZigAgent(
        selectedModule,
        `svelte-${selectedModule}`,
        ['browser', 'demo'],
        true
      );

      loading = false;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load agent';
      loading = false;
    }
  }

  async function handleSend() {
    if (!agent || !message.trim() || processing) return;

    try {
      processing = true;
      error = null;

      const result = await agent.process({
        role: 'user',
        content: message,
        metadata: {
          timestamp: new Date().toISOString(),
          source: 'svelte-app',
        },
      });

      if (result.ok && result.message) {
        response = result.message.content;
      } else if (result.error) {
        error = `${result.error.type}: ${result.error.message}`;
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Processing failed';
    } finally {
      processing = false;
    }
  }

  onMount(() => {
    loadAgent();
  });

  $: if (selectedModule) {
    loadAgent();
  }
</script>

<div class="container">
  <h1>🚀 Agenkit WASM + Svelte</h1>
  <p class="subtitle">Run AI agents in the browser using WebAssembly</p>

  <div class="module-selector">
    <label for="module">Select Agent Pattern:</label>
    <select id="module" bind:value={selectedModule} disabled={loading || processing}>
      {#each modules as mod}
        <option value={mod.id}>{mod.name} - {mod.description}</option>
      {/each}
    </select>
  </div>

  {#if loading}
    <div class="status loading">
      <strong>⏳ Loading agent...</strong>
      <p>Initializing {selectedModule} WASM module</p>
    </div>
  {/if}

  {#if error}
    <div class="status error">
      <strong>❌ Error:</strong>
      <p>{error}</p>
    </div>
  {/if}

  {#if agent && !loading}
    <div class="status success">
      <strong>✅ Agent Loaded</strong>
      <p>Name: {agent.name} | Capabilities: {agent.capabilities.join(', ')}</p>
    </div>

    <div class="input-group">
      <label for="message">Your Message:</label>
      <textarea
        id="message"
        bind:value={message}
        placeholder="Type your message here..."
        disabled={processing}
        rows="4"
      ></textarea>
    </div>

    <button
      on:click={handleSend}
      disabled={!message.trim() || processing}
      class="send-button"
    >
      {processing ? '⏳ Processing...' : '🚀 Send to Agent'}
    </button>

    {#if response}
      <div class="response">
        <strong>🤖 Agent Response:</strong>
        <p>{response}</p>
      </div>
    {/if}
  {/if}

  <footer>
    <p>
      <strong>How it works:</strong> This app loads a WebAssembly module compiled from Zig,
      instantiates it with WASI support, and provides a JavaScript interface for processing messages.
    </p>
    <p>
      <strong>Module size:</strong> 4.5KB-66KB per agent | <strong>Load time:</strong> &lt;10ms
    </p>
    <p>
      Learn more: <a href="https://github.com/scttfrdmn/agenkit" target="_blank" rel="noopener">
        github.com/scttfrdmn/agenkit
      </a>
    </p>
  </footer>
</div>

<style>
  .container {
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    font-family: system-ui, sans-serif;
  }

  h1 {
    margin: 0 0 0.5rem;
  }

  .subtitle {
    color: #666;
    margin: 0 0 2rem;
  }

  .module-selector {
    margin-bottom: 1.5rem;
  }

  .module-selector label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }

  select, textarea {
    width: 100%;
    padding: 0.75rem;
    font-size: 1rem;
    border: 2px solid #ddd;
    border-radius: 8px;
    font-family: inherit;
  }

  textarea {
    resize: vertical;
  }

  .status {
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
  }

  .status.loading {
    background-color: #e3f2fd;
  }

  .status.error {
    background-color: #ffebee;
    color: #c62828;
  }

  .status.success {
    background-color: #f5f5f5;
  }

  .status p {
    margin: 0.5rem 0 0;
    color: #666;
  }

  .input-group {
    margin-bottom: 1rem;
  }

  .input-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }

  .send-button {
    width: 100%;
    padding: 1rem;
    font-size: 1rem;
    font-weight: bold;
    color: white;
    background-color: #ff3e00;
    border: none;
    border-radius: 8px;
    cursor: pointer;
  }

  .send-button:disabled {
    background-color: #999;
    cursor: not-allowed;
  }

  .response {
    margin-top: 1.5rem;
    padding: 1rem;
    background-color: #e8f5e9;
    border-radius: 8px;
    border: 2px solid #4caf50;
  }

  .response strong {
    color: #2e7d32;
  }

  .response p {
    margin: 0.75rem 0 0;
    white-space: pre-wrap;
  }

  footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid #ddd;
    color: #666;
    font-size: 0.875rem;
  }

  footer p {
    margin: 0.5rem 0;
  }

  footer a {
    color: #ff3e00;
    text-decoration: none;
  }

  footer a:hover {
    text-decoration: underline;
  }
</style>
