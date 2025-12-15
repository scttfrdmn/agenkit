/**
 * Core types for Agenkit WASM
 */

export type Role = 'user' | 'assistant' | 'system' | 'tool';

export interface Message {
  role: Role;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface AgentResult {
  ok: boolean;
  message?: Message;
  error?: {
    type: string;
    message: string;
  };
}

export interface Agent {
  name: string;
  capabilities: string[];
  process(message: Message): Promise<AgentResult>;
}

export interface WasmModule {
  memory: WebAssembly.Memory;
  exports: Record<string, WebAssembly.ExportValue>;
}

export interface LoaderOptions {
  /** Path to WASM file (URL or file path) */
  wasmPath: string;
  /** Optional WASI imports for standalone WASM */
  wasiImports?: Record<string, unknown>;
  /** Enable debug logging */
  debug?: boolean;
}
