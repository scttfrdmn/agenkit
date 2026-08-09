package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Protocol version negotiation helpers shared by client and server (agenkit#781). */
final class McpVersionNegotiation {

    private static final Logger log = LoggerFactory.getLogger(McpVersionNegotiation.class);

    private McpVersionNegotiation() {}

    /**
     * Builds an {@link McpServerInfo} from a raw initialize result, capturing the server's
     * reported {@code protocolVersion} (previously discarded) and warning when it differs from
     * ours, so version skew is visible instead of surfacing later as an unrelated decode error or
     * wrong result.
     */
    static McpServerInfo parseServerInfo(JsonNode result) {
        String name = "";
        String version = "";
        if (result != null && result.has("serverInfo")) {
            JsonNode info = result.get("serverInfo");
            name = info.path("name").asText("");
            version = info.path("version").asText("");
        }
        String protocolVersion = result == null ? "" : result.path("protocolVersion").asText("");

        if (!protocolVersion.isEmpty() && !protocolVersion.equals(McpConstants.PROTOCOL_VERSION)) {
            log.warn(
                    "mcp: server protocol version \"{}\" does not match client version \"{}\"",
                    protocolVersion,
                    McpConstants.PROTOCOL_VERSION);
        }

        return new McpServerInfo(name, version, protocolVersion);
    }

    /**
     * Reads (and thus stops discarding) the client's requested {@code protocolVersion} from an
     * initialize request's params, warning on a mismatch. Per the MCP spec's negotiation model
     * the server always replies with the revision it actually implements.
     */
    static void warnIfClientVersionMismatch(JsonNode params) {
        if (params == null || !params.has("protocolVersion")) {
            return;
        }
        String clientProtocolVersion = params.get("protocolVersion").asText("");
        if (!clientProtocolVersion.isEmpty()
                && !clientProtocolVersion.equals(McpConstants.PROTOCOL_VERSION)) {
            log.warn(
                    "mcp: client requested protocol version \"{}\", server speaks \"{}\"",
                    clientProtocolVersion,
                    McpConstants.PROTOCOL_VERSION);
        }
    }
}
