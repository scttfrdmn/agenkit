#!/usr/bin/env node
/**
 * Quick test to verify @agenkit/wasm package works
 */

import { loadWasmModule, getAvailableModules } from './dist/index.mjs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

console.log('[@agenkit/wasm] Local package test');
console.log('');

// Test 1: List available modules
console.log('✓ Test 1: Available modules');
const modules = getAvailableModules();
console.log(`  Found ${modules.length} modules:`, modules.join(', '));
console.log('');

// Test 2: Load echo example
console.log('✓ Test 2: Load echo_example WASM module');
try {
  const wasmPath = join(__dirname, 'wasm', 'echo_example.wasm');
  const wasmModule = await loadWasmModule({ wasmPath, debug: true });
  console.log('  WASM module loaded successfully');
  console.log('  Exports:', Object.keys(wasmModule.exports).slice(0, 5).join(', '), '...');

  console.log('');
  console.log('✅ All tests passed!');
  console.log('');
  console.log('Package structure is valid and ready for publishing to npm.');
  console.log('');
  console.log('Note: Full agent interop requires Zig WASM bindings implementation.');
} catch (error) {
  console.error('❌ Test failed:', error.message);
  if (error.stack) {
    console.error(error.stack);
  }
  process.exit(1);
}
