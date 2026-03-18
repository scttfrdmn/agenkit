/**
 * Adapts MCP tools so they satisfy the Agenkit {@link Tool} interface.
 *
 * This allows any MCP server's tools to be used transparently with every
 * Agenkit agent — ReAct, planning, conversational, and others — without any
 * changes to the agent implementation.
 *
 * @example
 * ```ts
 * import { StdioClient } from './client.js';
 * import { toolsFromClient } from './tool_adapter.js';
 *
 * const client = new StdioClient('npx', ['-y', '@modelcontextprotocol/server-filesystem', '/tmp']);
 * await client.initialize();
 *
 * const tools = await toolsFromClient(client);
 * // `tools` implements Tool[] — pass directly to any Agenkit agent
 * ```
 *
 * @packageDocumentation
 */

import type { Tool, ToolResult } from '../../core/interfaces.js';
import { textContent } from './types.js';
import type { McpClient, McpTool } from './types.js';

// ─── McpToolAdapter ────────────────────────────────────────────────────────

/**
 * Wraps a single MCP tool so it satisfies the Agenkit {@link Tool} interface.
 *
 * The adapter delegates execution to the underlying {@link McpClient}, converts
 * the MCP content blocks to a plain string, and maps `isError` onto the
 * `success` field expected by {@link ToolResult}.
 */
export class McpToolAdapter implements Tool {
  /**
   * @param client  - MCP client used to invoke the tool
   * @param mcpTool - Tool descriptor as returned by `tools/list`
   */
  constructor(
    private readonly client: McpClient,
    private readonly mcpTool: McpTool,
  ) {}

  get name(): string {
    return this.mcpTool.name;
  }

  get description(): string {
    return this.mcpTool.description;
  }

  get parametersSchema(): Record<string, unknown> | undefined {
    return this.mcpTool.inputSchema;
  }

  /**
   * Execute the tool via the MCP client.
   *
   * @param params - Key/value map of tool parameters
   * @returns Agenkit {@link ToolResult} populated from the MCP response
   */
  async execute(params: Record<string, unknown>): Promise<ToolResult> {
    const result = await this.client.callTool(this.name, params);
    const text = textContent(result.content);

    return {
      output: text,
      success: !result.isError,
      error: result.isError ? text : undefined,
    };
  }
}

// ─── Factory ───────────────────────────────────────────────────────────────

/**
 * Discover all tools exposed by an MCP server and return them as Agenkit
 * {@link Tool} instances.
 *
 * The client must have been initialized (via `initialize()`) before calling
 * this function.
 *
 * @param client - An already-initialized {@link McpClient}
 * @returns Array of {@link Tool} instances wrapping every tool on the server
 */
export async function toolsFromClient(client: McpClient): Promise<Tool[]> {
  const mcpTools = await client.listTools();
  return mcpTools.map((t) => new McpToolAdapter(client, t));
}
