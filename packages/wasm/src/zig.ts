/**
 * Zig WASM Agent Wrapper
 *
 * Provides a JavaScript interface to Zig-compiled WASM agents.
 */

import { loadWasmModule, getModulePath } from './loader';
import { Agent, Message, AgentResult, WasmModule } from './types';

export class ZigAgent implements Agent {
  private module: WasmModule | null = null;
  public readonly name: string;
  public readonly capabilities: string[];

  constructor(name: string, capabilities: string[] = []) {
    this.name = name;
    this.capabilities = capabilities;
  }

  /**
   * Load a Zig WASM module
   *
   * @param moduleName - Name of the module (e.g., 'echo_example')
   * @param debug - Enable debug logging
   * @param baseUrl - Directory containing the .wasm files. See
   *   {@link getModulePath} for the per-environment defaults; a browser needs
   *   this to point at wherever the host app serves the files.
   *
   * @example
   * ```typescript
   * const agent = new ZigAgent('echo', ['echo', 'demo']);
   * await agent.load('echo_example');
   *
   * // Browser, assets served from /assets/wasm/
   * await agent.load('echo_example', false, '/assets/wasm');
   * ```
   */
  async load(moduleName: string, debug = false, baseUrl?: string): Promise<void> {
    const wasmPath = getModulePath(moduleName, baseUrl);
    this.module = await loadWasmModule({ wasmPath, debug });
  }

  /**
   * Process a message through the agent
   *
   * Note: This is a simplified implementation. Full Zig WASM interop
   * requires additional bindings for memory management and function exports.
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
    // TODO: Implement proper Zig WASM function calls
    return {
      ok: true,
      message: {
        role: 'assistant',
        content: `Echo from ${this.name}: ${message.content}`,
        metadata: {
          ...message.metadata,
          processed_by: this.name,
          wasm_runtime: 'zig',
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
      exports: Object.keys(this.module.exports),
      memoryPages: this.module.memory.buffer.byteLength / 65536,
    };
  }
}

/**
 * Create and load a Zig agent in one step
 *
 * @param moduleName - Name of the WASM module
 * @param agentName - Name for the agent instance
 * @param capabilities - Agent capabilities
 * @param debug - Enable debug logging
 * @param baseUrl - Directory containing the .wasm files. See
 *   {@link getModulePath} for the per-environment defaults.
 * @returns Initialized agent
 *
 * @example
 * ```typescript
 * import { createZigAgent } from '@agenkit/wasm';
 *
 * const agent = await createZigAgent('echo_example', 'my-echo', ['echo']);
 * const result = await agent.process({
 *   role: 'user',
 *   content: 'Hello, WASM!'
 * });
 * console.log(result.message?.content);
 * ```
 */
export async function createZigAgent(
  moduleName: string,
  agentName: string,
  capabilities: string[] = [],
  debug = false,
  baseUrl?: string
): Promise<ZigAgent> {
  const agent = new ZigAgent(agentName, capabilities);
  await agent.load(moduleName, debug, baseUrl);
  return agent;
}
