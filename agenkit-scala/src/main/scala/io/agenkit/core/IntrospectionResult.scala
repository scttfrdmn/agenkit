package io.agenkit.core

/** Snapshot of an agent's runtime state for observability. */
case class IntrospectionResult(
  name: String,
  metadata: Map[String, Any] = Map.empty,
  capabilities: List[String] = List.empty,
  activeConnections: Int = 0,
  processedMessages: Long = 0L
)
