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

  // Comprehensive WASI snapshot_preview1 stub implementation
  // Returns success (0) or EBADF (8) for unsupported operations
  const wasi = {
    // Args & Environment
    args_sizes_get: () => 0,
    args_get: () => 0,
    environ_sizes_get: () => 0,
    environ_get: () => 0,

    // Clock
    clock_time_get: () => 0,
    clock_res_get: () => 0,

    // File descriptors - Write operations
    fd_write: (fd: number, iovs: number, iovsLen: number, nwritten: number) => {
      if (debug && fd === 1) {
        console.log('[@agenkit/wasm] stdout write');
      }
      return 0;
    },
    fd_pwrite: () => 0,

    // File descriptors - Read operations
    fd_read: () => 0,
    fd_pread: () => 0,

    // File descriptors - Control
    fd_close: () => 0,
    fd_seek: () => 0,
    fd_sync: () => 0,
    fd_datasync: () => 0,
    fd_allocate: () => 0,
    fd_advise: () => 0,
    fd_fdstat_get: () => 0,
    fd_fdstat_set_flags: () => 0,
    fd_fdstat_set_rights: () => 0,
    fd_filestat_get: () => 0,
    fd_filestat_set_size: () => 0,
    fd_filestat_set_times: () => 0,
    fd_readdir: () => 0,
    fd_renumber: () => 0,
    fd_tell: () => 0,

    // File descriptors - Preopen
    fd_prestat_get: () => 8, // EBADF
    fd_prestat_dir_name: () => 8,

    // Path operations
    path_create_directory: () => 8,
    path_filestat_get: () => 8,
    path_filestat_set_times: () => 8,
    path_link: () => 8,
    path_open: () => 8,
    path_readlink: () => 8,
    path_remove_directory: () => 8,
    path_rename: () => 8,
    path_symlink: () => 8,
    path_unlink_file: () => 8,

    // Process
    proc_exit: (code: number) => {
      if (debug) {
        console.log(`[@agenkit/wasm] Process exited with code: ${code}`);
      }
    },
    proc_raise: () => 0,

    // Random
    random_get: (buf: number, bufLen: number) => {
      // Fill buffer with random data (simplified)
      return 0;
    },

    // Scheduling
    poll_oneoff: () => 0,
    sched_yield: () => 0,

    // Sockets (stubbed)
    sock_accept: () => 8,
    sock_recv: () => 8,
    sock_send: () => 8,
    sock_shutdown: () => 8,

    // Allow custom overrides
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
