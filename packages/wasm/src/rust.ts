/**
 * Rust WASM Agent Wrapper
 *
 * Provides a JavaScript interface to Rust-compiled WASM agents using wasm-bindgen.
 */

import { loadWasmModule } from './loader';
import { Agent, Message, AgentResult, WasmModule } from './types';

export class RustAgent implements Agent {
  private module: WasmModule | null = null;
  public readonly name: string;
  public readonly capabilities: string[];

  constructor(name: string, capabilities: string[] = []) {
    this.name = name;
    this.capabilities = capabilities;
  }

  /**
   * Load the Rust WASM module
   *
   * @param debug - Enable debug logging
   *
   * @example
   * ```typescript
   * const agent = new RustAgent('rust-agent', ['reasoning', 'patterns']);
   * await agent.load();
   * ```
   */
  async load(debug = false): Promise<void> {
    // Rust WASM is a single unified library, not separate modules like Zig
    const wasmPath = 'wasm/agenkit_rust.wasm';
    this.module = await loadWasmModule({ wasmPath, debug });
  }

  /**
   * Process a message through the agent
   *
   * Note: This is a simplified implementation. Full Rust WASM interop
   * with wasm-bindgen requires loading the generated JS glue code.
   *
   * @param message - Input message
   * @returns Agent result
   */
  async process(message: Message): Promise<AgentResult> {
    if (!this.module) {
      return {
        ok: false,
        error: {
          type: 'NotInitialized',
          message: 'Agent not loaded. Call load() first.',
        },
      };
    }

    // For now, return a simple echo response
    // TODO: Implement proper wasm-bindgen function calls
    // wasm-bindgen generates JS glue code that we'll need to load
    return {
      ok: true,
      message: {
        role: 'assistant',
        content: `Echo from ${this.name}: ${message.content}`,
        metadata: {
          ...message.metadata,
          processed_by: this.name,
          wasm_runtime: 'rust',
          wasm_bindgen: true,
        },
      },
    };
  }

  /**
   * Check if the agent is loaded and ready
   */
  isReady(): boolean {
    return this.module !== null;
  }

  /**
   * Get information about the loaded module
   */
  getModuleInfo() {
    if (!this.module) {
      return null;
    }

    return {
      name: this.name,
      capabilities: this.capabilities,
      runtime: 'rust',
      bindgen: true,
      exports: Object.keys(this.module.exports),
      memoryPages: this.module.memory.buffer.byteLength / 65536,
      size: '334KB',
    };
  }
}

/**
 * Create and load a Rust agent in one step
 *
 * @param agentName - Name for the agent instance
 * @param capabilities - Agent capabilities
 * @param debug - Enable debug logging
 * @returns Initialized agent
 *
 * @example
 * ```typescript
 * import { createRustAgent } from '@agenkit/wasm';
 *
 * const agent = await createRustAgent('reasoning-agent', ['cot', 'tot', 'self-consistency']);
 * const result = await agent.process({
 *   role: 'user',
 *   content: 'What is 2 + 2?'
 * });
 * console.log(result.message?.content);
 * ```
 */
export async function createRustAgent(
  agentName: string,
  capabilities: string[] = [],
  debug = false
): Promise<RustAgent> {
  const agent = new RustAgent(agentName, capabilities);
  await agent.load(debug);
  return agent;
}
