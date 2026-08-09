/**
 * MCP (Model Context Protocol) wire types and domain types.
 *
 * Implements JSON-RPC 2.0 wire format and MCP domain types.
 *
 * Reference: https://spec.modelcontextprotocol.io/specification/2025-11-25/
 *
 * @packageDocumentation
 */

/**
 * The MCP protocol revision this implementation speaks. A single named
 * constant (agenkit#781) imported by both client.ts and server.ts, rather
 * than each repeating the literal, so a version bump is a one-line change
 * and the two halves of the protocol can't drift from each other.
 *
 * 2025-11-25 is the latest *ratified* revision whose initialize/tools/list/
 * tools/call surface is additive over 2024-11-05 (agenkit#733: the
 * 2026-07-28 revision removes the initialize handshake in favor of a
 * stateless core this package does not implement, so advertising that
 * literal would claim a handshake the wire no longer has).
 */
export const PROTOCOL_VERSION = '2025-11-25';

// ─── Internal wire types ────────────────────────────────────────────────────
// Not exported from the barrel — callers work with domain types only.

/** JSON-RPC 2.0 request object. */
export interface JsonRpcRequest {
  jsonrpc: string;
  id: number;
  method: string;
  params?: unknown;
}

/** JSON-RPC 2.0 response object. */
export interface JsonRpcResponse {
  jsonrpc: string;
  id: number;
  result?: unknown;
  error?: JsonRpcError;
}

/** JSON-RPC 2.0 error descriptor. */
export interface JsonRpcError {
  code: number;
  message: string;
}

// ─── Public domain types ─────────────────────────────────────────────────────

/**
 * A tool exposed by an MCP server.
 */
export interface McpTool {
  /** Machine-readable tool identifier. */
  name: string;
  /** Human-readable description used by LLMs to decide when to call the tool. */
  description: string;
  /** JSON Schema describing the tool's input parameters. */
  inputSchema?: Record<string, unknown>;
}

/**
 * A single content block in an MCP tool result.
 */
export interface McpContent {
  /** Content type — typically `"text"`. */
  type: string;
  /** Textual content of this block. */
  text: string;
}

/**
 * Result returned by an MCP tool call.
 */
export interface McpToolResult {
  /** Ordered list of content blocks produced by the tool. */
  content: McpContent[];
  /** Whether the tool reported an error condition. */
  isError: boolean;
}

/**
 * Identifying information about the remote MCP server.
 */
export interface McpServerInfo {
  /** Server name as self-reported during initialization. */
  name: string;
  /** Server version string. */
  version: string;
  /**
   * The MCP protocol revision the server actually reported in its
   * initialize response (`result.protocolVersion`). Captured so a caller
   * can detect a mismatch against {@link PROTOCOL_VERSION} (agenkit#781 —
   * this field did not exist before, so a peer speaking a different
   * revision was indistinguishable from one speaking ours).
   */
  protocolVersion: string;
}

/**
 * Client interface for communicating with an MCP server.
 *
 * Implementations include {@link StdioClient} (subprocess over stdio) and
 * {@link HttpClient} (stateless HTTP/JSON-RPC).
 */
export interface McpClient {
  /**
   * Perform the MCP initialization handshake.
   * Must be called before any other method.
   */
  initialize(): Promise<void>;

  /** List all tools registered on the server. */
  listTools(): Promise<McpTool[]>;

  /**
   * Invoke a named tool with caller-supplied arguments.
   *
   * @param name - Tool name as returned by {@link listTools}
   * @param args - Key/value map of tool parameters
   */
  callTool(name: string, args: Record<string, unknown>): Promise<McpToolResult>;

  /** Identifying information populated after {@link initialize} resolves. */
  readonly serverInfo: McpServerInfo;

  /** Tear down the client connection and free any held resources. */
  close(): Promise<void>;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Concatenate the text from an ordered list of {@link McpContent} blocks.
 *
 * Blocks are joined with a single space so that multi-block responses remain
 * readable without requiring callers to manually join them.
 *
 * @param contents - Content blocks to concatenate
 * @returns Combined text string
 *
 * @example
 * ```ts
 * textContent([{ type: 'text', text: 'Hello' }, { type: 'text', text: 'world' }])
 * // → 'Hello world'
 * ```
 */
export function textContent(contents: McpContent[]): string {
  return contents.map((c) => c.text).join(' ');
}
