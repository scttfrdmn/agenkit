/**
 * MCP server — serves tools over stdio using JSON-RPC 2.0.
 *
 * {@link McpServer} reads newline-delimited JSON-RPC requests from stdin,
 * dispatches them to the appropriate handler, and writes responses to stdout.
 * The server is intentionally minimal: it exposes exactly the MCP methods that
 * a conformant client needs to discover and invoke tools.
 *
 * @example
 * ```ts
 * import { McpServer } from './protocols/mcp/server.js';
 *
 * const server = new McpServer('my-server', '1.0.0', [myTool]);
 * server.serveStdio();
 * ```
 *
 * @packageDocumentation
 */

import * as readline from 'readline';
import type { Tool } from '../../core/interfaces.js';
import { PROTOCOL_VERSION, type JsonRpcRequest, type JsonRpcResponse } from './types.js';

/**
 * MCP server that exposes a set of {@link Tool} instances over stdio.
 *
 * The server handles the three MCP methods required for tool use:
 * - `initialize` — returns server capabilities and version info
 * - `tools/list`  — enumerates registered tools with their schemas
 * - `tools/call`  — invokes a named tool and returns the result
 */
export class McpServer {
  private readonly tools: Map<string, Tool>;

  /**
   * @param name    - Server name reported to clients during initialization
   * @param version - Server version string
   * @param tools   - Tools to expose; names must be unique
   */
  constructor(
    private readonly name: string,
    private readonly version: string,
    tools: Tool[],
  ) {
    this.tools = new Map(tools.map((t) => [t.name, t]));
  }

  /**
   * Start the server, reading from `process.stdin` and writing to `process.stdout`.
   *
   * This method does not return — call it from a standalone entry-point script.
   */
  serveStdio(): void {
    const rl = readline.createInterface({
      input: process.stdin,
      terminal: false,
    });

    rl.on('line', async (line: string) => {
      let resp: JsonRpcResponse;
      try {
        const req = JSON.parse(line) as JsonRpcRequest;
        resp = await this.handleRequest(req);
      } catch {
        resp = {
          jsonrpc: '2.0',
          id: 0,
          error: { code: -32700, message: 'parse error' },
        };
      }
      process.stdout.write(JSON.stringify(resp) + '\n');
    });
  }

  /**
   * Dispatch a single JSON-RPC request and return the response.
   *
   * Exposed as a public method to allow direct unit-testing without stdio.
   *
   * @param req - Parsed JSON-RPC request
   * @returns JSON-RPC response
   */
  async handleRequest(req: JsonRpcRequest): Promise<JsonRpcResponse> {
    switch (req.method) {
      case 'initialize':
        return this.handleInitialize(req);
      case 'tools/list':
        return this.handleToolsList(req);
      case 'tools/call':
        return this.handleToolsCall(req);
      default:
        return {
          jsonrpc: '2.0',
          id: req.id,
          error: { code: -32601, message: `method not found: ${req.method}` },
        };
    }
  }

  // ─── Handlers ─────────────────────────────────────────────────────────────

  private handleInitialize(req: JsonRpcRequest): JsonRpcResponse {
    // Read (and thus stop discarding) the client's requested version —
    // agenkit#781. Per the MCP spec's negotiation model the server always
    // replies with the revision it actually implements; a mismatch is
    // logged so version skew is visible instead of silent.
    const params = req.params as { protocolVersion?: string } | undefined;
    const clientProtocolVersion = params?.protocolVersion ?? '';
    if (clientProtocolVersion && clientProtocolVersion !== PROTOCOL_VERSION) {
      console.warn(
        `mcp: client requested protocol version "${clientProtocolVersion}", server speaks "${PROTOCOL_VERSION}"`,
      );
    }

    return {
      jsonrpc: '2.0',
      id: req.id,
      result: {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: { tools: {} },
        serverInfo: { name: this.name, version: this.version },
      },
    };
  }

  private handleToolsList(req: JsonRpcRequest): JsonRpcResponse {
    const tools = Array.from(this.tools.values()).map((t) => ({
      name: t.name,
      description: t.description,
      inputSchema: t.parametersSchema ?? { type: 'object', properties: {} },
    }));

    return {
      jsonrpc: '2.0',
      id: req.id,
      result: { tools },
    };
  }

  private async handleToolsCall(req: JsonRpcRequest): Promise<JsonRpcResponse> {
    const params = req.params as {
      name?: string;
      arguments?: Record<string, unknown>;
    };

    const toolName = params?.name;
    if (!toolName) {
      return {
        jsonrpc: '2.0',
        id: req.id,
        error: { code: -32602, message: 'missing tool name' },
      };
    }

    const tool = this.tools.get(toolName);
    if (!tool) {
      return {
        jsonrpc: '2.0',
        id: req.id,
        error: { code: -32602, message: `unknown tool: ${toolName}` },
      };
    }

    try {
      const result = await tool.execute(params?.arguments ?? {});
      const text =
        typeof result.output === 'string'
          ? result.output
          : JSON.stringify(result.output);

      return {
        jsonrpc: '2.0',
        id: req.id,
        result: {
          content: [{ type: 'text', text }],
          isError: !result.success,
        },
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      return {
        jsonrpc: '2.0',
        id: req.id,
        result: {
          content: [{ type: 'text', text: message }],
          isError: true,
        },
      };
    }
  }
}
