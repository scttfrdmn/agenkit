package io.agenkit.evaluation

/** A named, scalar evaluation result. */
case class Metric(
  name: String,
  value: Double,
  unit: String = "",
  metadata: Map[String, Any] = Map.empty
)
