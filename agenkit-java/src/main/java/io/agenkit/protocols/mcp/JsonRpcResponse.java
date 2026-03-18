package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;

/** A JSON-RPC 2.0 response message. */
public record JsonRpcResponse(
        @JsonProperty("jsonrpc") String jsonrpc,
        @JsonProperty("id") long id,
        @JsonProperty("result") JsonNode result,
        @JsonProperty("error") JsonRpcError error) {}
