package io.agenkit.protocols.mcp;

/** Shared protocol constants used across MCP client and server implementations. */
final class McpConstants {

    /**
     * The MCP protocol revision this implementation speaks. A single named
     * constant (agenkit#781) referenced by both client and server code,
     * rather than each repeating the literal, so a version bump is a
     * one-line change and the two halves of the protocol cannot drift from
     * each other.
     *
     * <p>{@code 2025-11-25} is the latest <em>ratified</em> revision whose
     * initialize/tools/list/tools/call surface is additive over {@code
     * 2024-11-05} (agenkit#733: the {@code 2026-07-28} revision removes the
     * initialize handshake in favor of a stateless core this package does
     * not implement, so advertising that literal would claim a handshake
     * the wire no longer has).
     */
    static final String PROTOCOL_VERSION = "2025-11-25";
    static final String CLIENT_VERSION = "0.92.0";
    static final String CLIENT_NAME = "agenkit";

    private McpConstants() {}
}
