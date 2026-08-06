/**
 * MCP client implementations.
 *
 * Two transports are provided:
 *
 * - {@link StdioClient} — spawns a subprocess and communicates over its stdin/stdout.
 *   Suitable for local MCP servers.
 * - {@link HttpClient} — sends JSON-RPC requests over HTTP POST.
 *   Suitable for remote MCP servers that expose an HTTP endpoint.
 *
 * Both implement the {@link McpClient} interface so callers are transport-agnostic.
 *
 * @packageDocumentation
 */

import { spawn, ChildProcess } from 'child_process';
import * as readline from 'readline';
import type {
  JsonRpcRequest,
  JsonRpcResponse,
  McpClient,
  McpContent,
  McpServerInfo,
  McpTool,
  McpToolResult,
} from './types.js';

const PROTOCOL_VERSION = '2024-11-05';
const CLIENT_VERSION = '0.89.0';

// ─── StdioClient ─────────────────────────────────────────────────────────────

/**
 * MCP client that communicates with a subprocess over stdin/stdout.
 *
 * Requests and responses are newline-delimited JSON-RPC 2.0 messages.
 * A serial promise queue guarantees that at most one in-flight request exists
 * at any time, so the simple readline-line approach is safe.
 *
 * @example
 * ```ts
 * const client = new StdioClient('npx', ['-y', '@modelcontextprotocol/server-filesystem', '/tmp']);
 * await client.initialize();
 * const tools = await client.listTools();
 * await client.close();
 * ```
 */
export class StdioClient implements McpClient {
  private proc: ChildProcess | null = null;
  private rl: readline.Interface | null = null;

  /** Lines received from the subprocess that have not yet been consumed. */
  private lines: string[] = [];
  /** Callbacks waiting for the next line from the subprocess. */
  private lineResolvers: Array<(line: string) => void> = [];

  private nextId = 0;
  /** Serial queue — ensures only one `sendOnce` call runs at a time. */
  private queue: Promise<void> = Promise.resolve();
  private _serverInfo: McpServerInfo = { name: '', version: '' };

  /**
   * @param command - Executable to spawn (e.g. `"npx"`)
   * @param args    - Arguments passed to the executable
   * @param env     - Optional environment variable overrides merged into `process.env`
   */
  constructor(
    private readonly command: string,
    private readonly args: string[] = [],
    private readonly env?: Record<string, string>,
  ) {}

  get serverInfo(): McpServerInfo {
    return this._serverInfo;
  }

  async initialize(): Promise<void> {
    const mergedEnv = this.env
      ? { ...process.env, ...this.env }
      : process.env;

    this.proc = spawn(this.command, this.args, {
      stdio: ['pipe', 'pipe', 'inherit'],
      env: mergedEnv as NodeJS.ProcessEnv,
    });

    this.rl = readline.createInterface({
      input: this.proc.stdout!,
      terminal: false,
    });

    // Fan incoming lines to any pending resolver, or buffer them.
    this.rl.on('line', (line: string) => {
      const resolver = this.lineResolvers.shift();
      if (resolver) {
        resolver(line);
      } else {
        this.lines.push(line);
      }
    });

    const resp = await this.send('initialize', {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: 'agenkit', version: CLIENT_VERSION },
    });

    const result = resp.result as {
      serverInfo?: { name?: string; version?: string };
    };
    if (result?.serverInfo) {
      this._serverInfo = {
        name: result.serverInfo.name ?? '',
        version: result.serverInfo.version ?? '',
      };
    }
  }

  async listTools(): Promise<McpTool[]> {
    const resp = await this.send('tools/list');
    const result = resp.result as { tools?: McpTool[] };
    return result?.tools ?? [];
  }

  async callTool(
    name: string,
    args: Record<string, unknown>,
  ): Promise<McpToolResult> {
    const resp = await this.send('tools/call', { name, arguments: args });
    const result = resp.result as {
      content?: McpContent[];
      isError?: boolean;
    };
    return {
      content: result?.content ?? [],
      isError: result?.isError ?? false,
    };
  }

  async close(): Promise<void> {
    this.rl?.close();
    this.proc?.kill();
    this.proc = null;
    this.rl = null;
  }

  // ─── Internal helpers ──────────────────────────────────────────────────────

  /**
   * Return a promise that resolves with the next line emitted by the subprocess.
   */
  private readLine(): Promise<string> {
    const buffered = this.lines.shift();
    if (buffered !== undefined) {
      return Promise.resolve(buffered);
    }
    return new Promise<string>((resolve) => {
      this.lineResolvers.push(resolve);
    });
  }

  /**
   * Enqueue a request so that at most one `sendOnce` call runs at a time.
   */
  private send(method: string, params?: unknown): Promise<JsonRpcResponse> {
    return new Promise<JsonRpcResponse>((resolve, reject) => {
      this.queue = this.queue.then(async () => {
        try {
          resolve(await this.sendOnce(method, params));
        } catch (err) {
          reject(err);
        }
      });
    });
  }

  /**
   * Write a single JSON-RPC request and wait for exactly one response line.
   */
  private async sendOnce(
    method: string,
    params?: unknown,
  ): Promise<JsonRpcResponse> {
    const id = ++this.nextId;
    const req: JsonRpcRequest = { jsonrpc: '2.0', id, method, params };
    this.proc!.stdin!.write(JSON.stringify(req) + '\n');
    const raw = await this.readLine();
    return JSON.parse(raw) as JsonRpcResponse;
  }
}

// ─── HttpClient ───────────────────────────────────────────────────────────────

/**
 * MCP client that communicates with a remote server over HTTP POST.
 *
 * Each JSON-RPC call maps to a single HTTP request, so no session state or
 * connection management is required.
 *
 * @example
 * ```ts
 * const client = new HttpClient('http://localhost:3000/mcp');
 * await client.initialize();
 * const tools = await client.listTools();
 * ```
 */
export class HttpClient implements McpClient {
  private nextId = 0;
  private _serverInfo: McpServerInfo = { name: '', version: '' };

  /**
   * @param baseUrl - Full URL of the MCP JSON-RPC endpoint
   */
  constructor(private readonly baseUrl: string) {}

  get serverInfo(): McpServerInfo {
    return this._serverInfo;
  }

  async initialize(): Promise<void> {
    const resp = await this.send('initialize', {
      protocolVersion: PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: { name: 'agenkit', version: CLIENT_VERSION },
    });

    const result = resp.result as {
      serverInfo?: { name?: string; version?: string };
    };
    if (result?.serverInfo) {
      this._serverInfo = {
        name: result.serverInfo.name ?? '',
        version: result.serverInfo.version ?? '',
      };
    }
  }

  async listTools(): Promise<McpTool[]> {
    const resp = await this.send('tools/list');
    const result = resp.result as { tools?: McpTool[] };
    return result?.tools ?? [];
  }

  async callTool(
    name: string,
    args: Record<string, unknown>,
  ): Promise<McpToolResult> {
    const resp = await this.send('tools/call', { name, arguments: args });
    const result = resp.result as {
      content?: McpContent[];
      isError?: boolean;
    };
    return {
      content: result?.content ?? [],
      isError: result?.isError ?? false,
    };
  }

  async close(): Promise<void> {
    // HTTP is stateless — nothing to tear down.
  }

  // ─── Internal helpers ──────────────────────────────────────────────────────

  private async send(method: string, params?: unknown): Promise<JsonRpcResponse> {
    const id = ++this.nextId;
    const req: JsonRpcRequest = { jsonrpc: '2.0', id, method, params };

    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });

    return response.json() as Promise<JsonRpcResponse>;
  }
}
