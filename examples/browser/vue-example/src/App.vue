<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import type { ZigAgent } from '@agenkit/wasm';

// Import from local package during development
declare const createZigAgent: (moduleName: string, agentName: string, capabilities?: string[], debug?: boolean) => Promise<ZigAgent>;

const agent = ref<ZigAgent | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);
const message = ref('');
const response = ref('');
const processing = ref(false);
const selectedModule = ref('echo_example');

const modules = [
  { id: 'echo_example', name: 'Echo', description: 'Simple echo agent' },
  { id: 'reflection_example', name: 'Reflection', description: 'Self-reflection pattern' },
  { id: 'sequential_example', name: 'Sequential', description: 'Sequential processing' },
  { id: 'parallel_example', name: 'Parallel', description: 'Parallel processing' },
  { id: 'react_example', name: 'ReAct', description: 'Reasoning + acting' },
];

async function loadAgent() {
  try {
    loading.value = true;
    error.value = null;
    response.value = '';

    const newAgent = await createZigAgent(
      selectedModule.value,
      `vue-${selectedModule.value}`,
      ['browser', 'demo'],
      true
    );

    agent.value = newAgent;
    loading.value = false;
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to load agent';
    loading.value = false;
  }
}

async function handleSend() {
  if (!agent.value || !message.value.trim() || processing.value) return;

  try {
    processing.value = true;
    error.value = null;

    const result = await agent.value.process({
      role: 'user',
      content: message.value,
      metadata: {
        timestamp: new Date().toISOString(),
        source: 'vue-app',
      },
    });

    if (result.ok && result.message) {
      response.value = result.message.content;
    } else if (result.error) {
      error.value = `${result.error.type}: ${result.error.message}`;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Processing failed';
  } finally {
    processing.value = false;
  }
}

onMounted(() => {
  loadAgent();
});

watch(selectedModule, () => {
  loadAgent();
});
</script>

<template>
  <div class="container">
    <h1>🚀 Agenkit WASM + Vue</h1>
    <p class="subtitle">Run AI agents in the browser using WebAssembly</p>

    <!-- Module Selector -->
    <div class="module-selector">
      <label>Select Agent Pattern:</label>
      <select v-model="selectedModule" :disabled="loading || processing">
        <option v-for="mod in modules" :key="mod.id" :value="mod.id">
          {{ mod.name }} - {{ mod.description }}
        </option>
      </select>
    </div>

    <!-- Status -->
    <div v-if="loading" class="status loading">
      <strong>⏳ Loading agent...</strong>
      <p>Initializing {{ selectedModule }} WASM module</p>
    </div>

    <div v-if="error" class="status error">
      <strong>❌ Error:</strong>
      <p>{{ error }}</p>
    </div>

    <div v-if="agent && !loading">
      <!-- Agent Info -->
      <div class="status success">
        <strong>✅ Agent Loaded</strong>
        <p>Name: {{ agent.name }} | Capabilities: {{ agent.capabilities.join(', ') }}</p>
      </div>

      <!-- Input Area -->
      <div class="input-group">
        <label>Your Message:</label>
        <textarea
          v-model="message"
          placeholder="Type your message here..."
          :disabled="processing"
          rows="4"
          @keypress.enter.exact.prevent="handleSend"
        />
      </div>

      <button
        @click="handleSend"
        :disabled="!message.trim() || processing"
        class="send-button"
      >
        {{ processing ? '⏳ Processing...' : '🚀 Send to Agent' }}
      </button>

      <!-- Response Area -->
      <div v-if="response" class="response">
        <strong>🤖 Agent Response:</strong>
        <p>{{ response }}</p>
      </div>
    </div>

    <!-- Footer -->
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
</template>

<style scoped>
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
  background-color: #1976d2;
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
  color: #1976d2;
  text-decoration: none;
}

footer a:hover {
  text-decoration: underline;
}
</style>
