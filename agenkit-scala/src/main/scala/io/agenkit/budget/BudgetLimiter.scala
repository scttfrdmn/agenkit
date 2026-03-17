package io.agenkit.budget

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}

/** Rejects requests once the estimated cost exceeds `maxCostUsd`. */
class BudgetLimiter(
  inner: Agent,
  maxCostUsd: Double,
  model: String = "gpt-4o",
  estimateTokens: Message => Int = m => m.contentString.length / 4
) extends Agent:
  private val tracker = CostTracker(model)

  def name: String               = s"budget-limiter(${inner.name})"
  def capabilities: List[String] = inner.capabilities :+ "budget-control"
  def currentCost: Double        = tracker.totalCost
  def isOverBudget: Boolean      = tracker.totalCost >= maxCostUsd

  def process(message: Message)(using ExecutionContext): Future[Message] =
    if isOverBudget then
      Future.failed(
        new RuntimeException(s"Budget exceeded: ${tracker.totalCost} >= $maxCostUsd USD")
      )
    else
      val inputTokens = estimateTokens(message)
      inner.process(message).map { response =>
        val outputTokens = estimateTokens(response)
        tracker.recordUsage(inputTokens, outputTokens)
        response
      }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("maxCost" -> maxCostUsd, "currentCost" -> currentCost, "overBudget" -> isOverBudget),
      capabilities = capabilities,
      processedMessages = tracker.requestCount
    )
