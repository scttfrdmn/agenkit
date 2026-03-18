/**
 * Tests for MCP (Model Context Protocol) support.
 *
 * Tests cover wire-type serialisation, helper functions, client shape checks,
 * tool adapter behaviour, and the toolsFromClient factory — all without
 * spawning any subprocess or making real network requests.
 */

import { describe, it, expect } from 'vitest';
import { StdioClient, HttpClient } from '../client.js';
import { McpToolAdapter, toolsFromClient } from '../tool_adapter.js';
import type { McpClient, McpTool, McpToolResult, McpServerInfo } from '../types.js';
import { textContent } from '../types.js';

// ─── Mock MCP client ────────────────────────────────────────────────────────

class MockMcpClient implements McpClient {
  readonly serverInfo: McpServerInfo = { name: 'mock-server', version: '1.0.0' };

  private readonly mockTools: McpTool[];

  constructor(tools: McpTool[] = []) {
    this.mockTools = tools;
  }

  async initialize(): Promise<void> {
    // no-op for tests
  }

  async listTools(): Promise<McpTool[]> {
    return this.mockTools;
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<McpToolResult> {
    return {
      content: [{ type: 'text', text: `called ${name} with ${JSON.stringify(args)}` }],
      isError: false,
    };
  }

  async close(): Promise<void> {
    // no-op for tests
  }
}

// ─── Wire types ──────────────────────────────────────────────────────────────

describe('MCP wire types', () => {
  it('JsonRpcRequest serializes correctly', () => {
    const req = {
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/list',
      params: { cursor: null },
    };
    const serialized = JSON.stringify(req);
    const parsed = JSON.parse(serialized);

    expect(parsed.jsonrpc).toBe('2.0');
    expect(parsed.id).toBe(1);
    expect(parsed.method).toBe('tools/list');
    expect(parsed.params).toEqual({ cursor: null });
  });

  it('JsonRpcResponse deserializes correctly', () => {
    const raw = '{"jsonrpc":"2.0","id":2,"result":{"tools":[]}}';
    const resp = JSON.parse(raw);

    expect(resp.jsonrpc).toBe('2.0');
    expect(resp.id).toBe(2);
    expect(resp.result).toEqual({ tools: [] });
    expect(resp.error).toBeUndefined();
  });

  it('McpTool round-trips JSON', () => {
    const tool: McpTool = {
      name: 'read_file',
      description: 'Read a file from the filesystem',
      inputSchema: { type: 'object', properties: { path: { type: 'string' } } },
    };
    const parsed: McpTool = JSON.parse(JSON.stringify(tool));

    expect(parsed.name).toBe(tool.name);
    expect(parsed.description).toBe(tool.description);
    expect(parsed.inputSchema).toEqual(tool.inputSchema);
  });
});

// ─── textContent helper ───────────────────────────────────────────────────────

describe('textContent', () => {
  it('returns the text of a single content block', () => {
    const result = textContent([{ type: 'text', text: 'hello' }]);
    expect(result).toBe('hello');
  });

  it('joins multiple content blocks with a space', () => {
    const result = textContent([
      { type: 'text', text: 'hello' },
      { type: 'text', text: 'world' },
    ]);
    expect(result).toBe('hello world');
  });
});

// ─── Client shape checks ──────────────────────────────────────────────────────

describe('StdioClient', () => {
  it('implements the McpClient interface', () => {
    const client = new StdioClient('echo');

    expect(client).toBeInstanceOf(Object);
    expect('initialize' in client).toBe(true);
    expect('listTools' in client).toBe(true);
    expect('callTool' in client).toBe(true);
    expect('close' in client).toBe(true);
    expect('serverInfo' in client).toBe(true);
  });
});

describe('HttpClient', () => {
  it('implements the McpClient interface', () => {
    const client = new HttpClient('http://localhost:3000/mcp');

    expect(client).toBeInstanceOf(Object);
    expect('initialize' in client).toBe(true);
    expect('listTools' in client).toBe(true);
    expect('callTool' in client).toBe(true);
    expect('close' in client).toBe(true);
    expect('serverInfo' in client).toBe(true);
  });
});

// ─── McpToolAdapter ────────────────────────────────────────────────────────

describe('McpToolAdapter', () => {
  const mcpTool: McpTool = {
    name: 'search',
    description: 'Search the web for a query',
    inputSchema: { type: 'object', properties: { query: { type: 'string' } } },
  };

  it('exposes the tool name from the McpTool descriptor', () => {
    const adapter = new McpToolAdapter(new MockMcpClient(), mcpTool);
    expect(adapter.name).toBe('search');
  });

  it('exposes the tool description from the McpTool descriptor', () => {
    const adapter = new McpToolAdapter(new MockMcpClient(), mcpTool);
    expect(adapter.description).toBe('Search the web for a query');
  });

  it('maps a successful tool call to success=true', async () => {
    const client: McpClient = {
      serverInfo: { name: 'test', version: '1.0' },
      async initialize() {},
      async listTools() { return []; },
      async callTool() {
        return {
          content: [{ type: 'text', text: 'search results' }],
          isError: false,
        };
      },
      async close() {},
    };

    const adapter = new McpToolAdapter(client, mcpTool);
    const result = await adapter.execute({ query: 'agenkit' });

    expect(result.success).toBe(true);
    expect(result.output).toBe('search results');
    expect(result.error).toBeUndefined();
  });

  it('maps an error tool call to success=false', async () => {
    const client: McpClient = {
      serverInfo: { name: 'test', version: '1.0' },
      async initialize() {},
      async listTools() { return []; },
      async callTool() {
        return {
          content: [{ type: 'text', text: 'permission denied' }],
          isError: true,
        };
      },
      async close() {},
    };

    const adapter = new McpToolAdapter(client, mcpTool);
    const result = await adapter.execute({ query: 'secret' });

    expect(result.success).toBe(false);
    expect(result.error).toBe('permission denied');
  });
});

// ─── toolsFromClient factory ──────────────────────────────────────────────────

describe('toolsFromClient', () => {
  it('wraps each server tool in a McpToolAdapter', async () => {
    const mockTools: McpTool[] = [
      { name: 'tool_a', description: 'First tool' },
      { name: 'tool_b', description: 'Second tool' },
    ];
    const client = new MockMcpClient(mockTools);

    const tools = await toolsFromClient(client);

    expect(tools).toHaveLength(2);
    expect(tools[0].name).toBe('tool_a');
    expect(tools[1].name).toBe('tool_b');
  });
});
