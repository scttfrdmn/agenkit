package io.agenkit.protocols.mcp;

import java.util.List;
import java.util.Map;

/**
 * Client interface for communicating with an MCP (Model Context Protocol) server.
 *
 * <p>Implementations connect via different transports (stdio, HTTP) but expose the
 * same logical operations: initialise the session, enumerate tools, and call them.
 */
public interface McpClient extends AutoCloseable {

    /** Perform the MCP initialise handshake and populate {@link #serverInfo()}. */
    void initialize() throws Exception;

    /** List all tools advertised by the server. */
    List<McpTool> listTools() throws Exception;

    /**
     * Invoke a named tool with the given arguments.
     *
     * @param name the tool name
     * @param args key-value arguments
     * @return the tool result
     */
    McpToolResult callTool(String name, Map<String, Object> args) throws Exception;

    /** Returns server identity information populated after {@link #initialize()}. */
    McpServerInfo serverInfo();

    @Override
    void close() throws Exception;
}
