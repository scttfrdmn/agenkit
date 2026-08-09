/**
 * MCP (Model Context Protocol) support for Agenkit.
 *
 * Provides client implementations ({@link StdioClient}, {@link HttpClient}),
 * a server ({@link McpServer}), and a tool adapter ({@link toolsFromClient})
 * for integrating MCP servers into Agenkit agent pipelines.
 *
 * Reference: https://spec.modelcontextprotocol.io/specification/2025-11-25/
 *
 * @example
 * ```ts
 * import { StdioClient, toolsFromClient } from 'agenkit-ts';
 *
 * const client = new McpStdioClient('npx', ['-y', '@modelcontextprotocol/server-filesystem', '/tmp']);
 * await client.initialize();
 * const tools = await toolsFromClient(client);
 * ```
 *
 * @packageDocumentation
 */

// Domain types and helpers
export type { McpTool, McpContent, McpToolResult, McpServerInfo, McpClient } from './types.js';
export { PROTOCOL_VERSION, textContent } from './types.js';

// Client implementations
export { StdioClient, HttpClient } from './client.js';

// Server
export { McpServer } from './server.js';

// Tool adapter
export { McpToolAdapter, toolsFromClient } from './tool_adapter.js';
