/**
 * Tests for MCP (Model Context Protocol) support.
 *
 * Tests cover wire-type serialisation, helper functions, client shape checks,
 * tool adapter behaviour, and the toolsFromClient factory — all without
 * spawning any subprocess or making real network requests.
 */

import { describe, it, expect, vi } from 'vitest';
import { StdioClient, HttpClient, parseServerInfo } from '../client.js';
import { McpToolAdapter, toolsFromClient } from '../tool_adapter.js';
import type { McpClient, McpTool, McpToolResult, McpServerInfo } from '../types.js';
import { PROTOCOL_VERSION, textContent } from '../types.js';
import { McpServer } from '../server.js';

// ─── Mock MCP client ────────────────────────────────────────────────────────

class MockMcpClient implements McpClient {
  readonly serverInfo: McpServerInfo = {
    name: 'mock-server',
    version: '1.0.0',
    protocolVersion: PROTOCOL_VERSION,
  };

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
      serverInfo: { name: 'test', version: '1.0', protocolVersion: PROTOCOL_VERSION },
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
      serverInfo: { name: 'test', version: '1.0', protocolVersion: PROTOCOL_VERSION },
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

// ─── Protocol version negotiation (agenkit#781) ────────────────────────────────

describe('McpServer protocol version negotiation', () => {
  it('advertises the shared PROTOCOL_VERSION constant, not an independent literal', async () => {
    const server = new McpServer('test-server', '1.0.0', []);
    const resp = await server.handleRequest({ jsonrpc: '2.0', id: 1, method: 'initialize' });
    const result = resp.result as { protocolVersion: string };
    expect(result.protocolVersion).toBe(PROTOCOL_VERSION);
  });

  it('warns when the client requests a different protocol version', async () => {
    const server = new McpServer('test-server', '1.0.0', []);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const resp = await server.handleRequest({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: { protocolVersion: '1999-01-01', capabilities: {} },
    });

    // Server still answers with the version it actually speaks (spec's
    // negotiation model: the server states its own supported revision).
    const result = resp.result as { protocolVersion: string };
    expect(result.protocolVersion).toBe(PROTOCOL_VERSION);

    // Negative-verification target: reverting the mismatch check in
    // handleInitialize (added for agenkit#781) makes this assertion fail,
    // since nothing else in the server reads req.params.protocolVersion.
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('1999-01-01'),
    );
    expect(warnSpy.mock.calls[0]?.[0]).toContain(PROTOCOL_VERSION);

    warnSpy.mockRestore();
  });

  it('does not warn when the client requests the server-supported version', async () => {
    const server = new McpServer('test-server', '1.0.0', []);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    await server.handleRequest({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: { protocolVersion: PROTOCOL_VERSION, capabilities: {} },
    });

    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });
});

describe('MCP client protocol version capture', () => {
  it('captures the server-reported protocolVersion (previously discarded)', () => {
    const info = parseServerInfo({
      protocolVersion: PROTOCOL_VERSION,
      serverInfo: { name: 'srv', version: '9.9.9' },
    });
    expect(info.protocolVersion).toBe(PROTOCOL_VERSION);
    expect(info.name).toBe('srv');
    expect(info.version).toBe('9.9.9');
  });

  it('warns when the server-reported protocolVersion differs from ours', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

    const info = parseServerInfo({
      protocolVersion: '1999-01-01',
      serverInfo: { name: 'old-server', version: '0.1.0' },
    });

    expect(info.protocolVersion).toBe('1999-01-01');

    // Negative-verification target: reverting the mismatch check in
    // parseServerInfo (added for agenkit#781) makes this assertion fail —
    // protocolVersion would still populate (covered above), but no warning
    // would be logged.
    expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('1999-01-01'));
    expect(warnSpy.mock.calls[0]?.[0]).toContain(PROTOCOL_VERSION);

    warnSpy.mockRestore();
  });
});
