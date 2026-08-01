/**
 * Basic example using @agenkit/wasm
 *
 * Run with: node --loader ts-node/esm examples/basic.ts
 */

import { fileURLToPath } from 'node:url';

import { createZigAgent, getAvailableModules } from '../src/index';

async function main() {
  console.log('=== @agenkit/wasm Basic Example ===\n');

  // Show available modules
  console.log('Available modules:', getAvailableModules());
  console.log('');

  // Create an echo agent.
  //
  // The explicit base is required because this example runs as an ES module,
  // where `__dirname` does not exist. CommonJS consumers can omit it and a
  // browser defaults to /wasm — see getModulePath in src/loader.ts.
  const wasmDir = fileURLToPath(new URL('../wasm', import.meta.url));

  console.log('Creating echo agent...');
  const agent = await createZigAgent('echo_example', 'demo-agent', ['echo', 'demo'], true, wasmDir);

  console.log(`\nAgent created: ${agent.name}`);
  console.log(`Capabilities: ${agent.capabilities.join(', ')}`);
  console.log(`Ready: ${agent.isReady()}`);

  // Get module info
  const info = agent.getModuleInfo();
  console.log('\nModule Info:', info);

  // Process a message
  console.log('\n--- Processing Message ---');
  const result = await agent.process({
    role: 'user',
    content: 'Hello from @agenkit/wasm!',
    metadata: {
      timestamp: new Date().toISOString(),
      example: 'basic',
    },
  });

  if (result.ok && result.message) {
    console.log('\n✓ Success!');
    console.log(`Role: ${result.message.role}`);
    console.log(`Content: ${result.message.content}`);
    console.log(`Metadata:`, result.message.metadata);
  } else if (result.error) {
    console.error('\n✗ Error!');
    console.error(`Type: ${result.error.type}`);
    console.error(`Message: ${result.error.message}`);
  }

  console.log('\n=== Example Complete ===');
}

main().catch(console.error);
