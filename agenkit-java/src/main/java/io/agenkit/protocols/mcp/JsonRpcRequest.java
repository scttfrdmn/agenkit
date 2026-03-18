package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

/** A JSON-RPC 2.0 request message. */
public record JsonRpcRequest(
        @JsonProperty("jsonrpc") String jsonrpc,
        @JsonProperty("id") long id,
        @JsonProperty("method") String method,
        @JsonProperty("params") JsonNode params) {

    public static JsonRpcRequest of(long id, String method, JsonNode params) {
        return new JsonRpcRequest("2.0", id, method, params);
    }
}
