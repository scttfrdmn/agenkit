/**
 * WASM Module Loader with WASI support
 */

import { readFileSync } from 'fs';
import { LoaderOptions, WasmModule } from './types';

/**
 * Load a WebAssembly module from a file or URL
 *
 * @param options - Loader configuration
 * @returns Initialized WASM module
 *
 * @example
 * ```typescript
 * import { loadWasmModule } from '@agenkit/wasm';
 *
 * const module = await loadWasmModule({
 *   wasmPath: './wasm/echo_example.wasm',
 *   debug: true
 * });
 * ```
 */
export async function loadWasmModule(options: LoaderOptions): Promise<WasmModule> {
  const { wasmPath, wasiImports = {}, debug = false } = options;

  if (debug) {
    console.log(`[@agenkit/wasm] Loading module from: ${wasmPath}`);
  }

  // Load WASM binary
  let wasmBinary: BufferSource;

  if (typeof process !== 'undefined' && process.versions && process.versions.node) {
    // Node.js environment
    try {
      wasmBinary = readFileSync(wasmPath);
    } catch (error) {
      throw new Error(`Failed to read WASM file: ${wasmPath}`, { cause: error });
    }
  } else {
    // Browser environment
    try {
      const response = await fetch(wasmPath);
      wasmBinary = await response.arrayBuffer();
    } catch (error) {
      throw new Error(`Failed to fetch WASM file: ${wasmPath}`, { cause: error });
    }
  }

  // Minimal WASI implementation
  const wasi = {
    args_sizes_get: () => 0,
    args_get: () => 0,
    environ_sizes_get: () => 0,
    environ_get: () => 0,
    clock_time_get: () => 0,
    fd_write: (fd: number, iovs: number, iovsLen: number, nwritten: number) => {
      if (debug && fd === 1) {
        console.log('[@agenkit/wasm] stdout write');
      }
      return 0;
    },
    fd_close: () => 0,
    fd_seek: () => 0,
    fd_read: () => 0,
    proc_exit: (code: number) => {
      if (debug) {
        console.log(`[@agenkit/wasm] Process exited with code: ${code}`);
      }
    },
    random_get: (buf: number, bufLen: number) => {
      // Fill buffer with random data (simplified)
      return 0;
    },
    ...wasiImports,
  };

  // Compile and instantiate
  const module = await WebAssembly.compile(wasmBinary);
  const instance = await WebAssembly.instantiate(module, {
    wasi_snapshot_preview1: wasi,
  });

  if (debug) {
    console.log('[@agenkit/wasm] Module loaded successfully');
    console.log('[@agenkit/wasm] Exports:', Object.keys(instance.exports));
  }

  return {
    memory: instance.exports.memory as WebAssembly.Memory,
    exports: instance.exports,
  };
}

/**
 * Get list of available WASM modules bundled with this package
 *
 * @returns Array of available module names
 */
export function getAvailableModules(): string[] {
  return [
    'agenkit',
    'echo_example',
    'reflection_example',
    'sequential_example',
    'parallel_example',
    'react_example',
  ];
}

/**
 * Get the path to a bundled WASM module
 *
 * @param moduleName - Name of the module (without .wasm extension)
 * @returns Path to the WASM file
 */
export function getModulePath(moduleName: string): string {
  return `${__dirname}/../wasm/${moduleName}.wasm`;
}
