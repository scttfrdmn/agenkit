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

// ─── Stateless server (agenkit#837) ────────────────────────────────────────────

describe('McpServer statelessness', () => {
  it('handles tools/call with no preceding initialize (regression lock)', async () => {
    // handleRequest tracks no session state at all (no "initialized" flag,
    // no session table), so a "tools/call" arriving with no preceding
    // "initialize" already succeeds today. agenkit#837 asked us to decide
    // our position deliberately rather than by accident; this codifies
    // "stateless by design" (option 1) so a future change that starts
    // enforcing the handshake is a visible, deliberate break rather than a
    // silent one. This passes today, unchanged — it is not a behaviour
    // change.
    const echoTool = {
      name: 'echo',
      description: 'Echoes the input message',
      async execute(params: Record<string, unknown>) {
        return { success: true, output: params.message };
      },
    };
    const server = new McpServer('test-server', '1.0.0', [echoTool]);

    // Deliberately skip "initialize" and go straight to "tools/call".
    const resp = await server.handleRequest({
      jsonrpc: '2.0',
      id: 1,
      method: 'tools/call',
      params: { name: 'echo', arguments: { message: 'no handshake needed' } },
    });

    expect(resp.error).toBeUndefined();
    const result = resp.result as { content: { text: string }[]; isError: boolean };
    expect(result.isError).toBe(false);
    expect(result.content[0].text).toBe('no handshake needed');
  });

  it('handles tools/list with no preceding initialize', async () => {
    const echoTool = {
      name: 'echo',
      description: 'Echoes the input message',
      async execute(params: Record<string, unknown>) {
        return { success: true, output: params.message };
      },
    };
    const server = new McpServer('test-server', '1.0.0', [echoTool]);

    const resp = await server.handleRequest({ jsonrpc: '2.0', id: 1, method: 'tools/list' });

    expect(resp.error).toBeUndefined();
    const result = resp.result as { tools: { name: string }[] };
    expect(result.tools.map((t) => t.name)).toContain('echo');
  });
});

// ─── HttpClient transport independent of initialize() (agenkit#837) ──────────

describe('HttpClient statelessness', () => {
  it('listTools works without a preceding initialize() call', async () => {
    // HttpClient.send() calls the global `fetch` directly per-request; it
    // never held a persistent transport object gated behind initialize()
    // the way Python's HTTPClient did before agenkit#837. This is a
    // cross-language parity check for #837 point 4, not a behaviour change:
    // TypeScript never had the lazy-construction bug.
    const fetchMock = vi.fn().mockResolvedValue({
      json: async () => ({
        jsonrpc: '2.0',
        id: 1,
        result: { tools: [{ name: 'echo', description: 'Echo' }] },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const client = new HttpClient('http://localhost:3000/mcp');
    const tools = await client.listTools();

    expect(tools).toHaveLength(1);
    expect(tools[0].name).toBe('echo');

    vi.unstubAllGlobals();
  });

  it('callTool works without a preceding initialize() call', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      json: async () => ({
        jsonrpc: '2.0',
        id: 1,
        result: { content: [{ type: 'text', text: 'hi' }], isError: false },
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    const client = new HttpClient('http://localhost:3000/mcp');
    const result = await client.callTool('echo', { message: 'hi' });

    expect(result.isError).toBe(false);
    expect(result.content[0].text).toBe('hi');

    vi.unstubAllGlobals();
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
