package io.agenkit.protocols.mcp;

import com.fasterxml.jackson.annotation.JsonProperty;

/** A JSON-RPC 2.0 error object. */
public record JsonRpcError(
        @JsonProperty("code") int code,
        @JsonProperty("message") String message) {}
