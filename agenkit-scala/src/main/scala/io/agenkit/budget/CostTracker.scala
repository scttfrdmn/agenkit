package io.agenkit.budget

import java.util.concurrent.atomic.AtomicLong

/** Accumulates token usage and computes estimated USD cost for a given model. */
class CostTracker(
  model: String = "gpt-4o"
):
  private val _totalInputTokens  = new AtomicLong(0)
  private val _totalOutputTokens = new AtomicLong(0)
  private val _requestCount      = new AtomicLong(0)

  def recordUsage(inputTokens: Int, outputTokens: Int): Unit =
    _totalInputTokens.addAndGet(inputTokens)
    _totalOutputTokens.addAndGet(outputTokens)
    _requestCount.incrementAndGet()
    ()

  def totalInputTokens: Long  = _totalInputTokens.get()
  def totalOutputTokens: Long = _totalOutputTokens.get()
  def requestCount: Long      = _requestCount.get()

  def totalCost: Double =
    ModelPricing.estimateCost(model, _totalInputTokens.get().toInt, _totalOutputTokens.get().toInt)

  def reset(): Unit =
    _totalInputTokens.set(0)
    _totalOutputTokens.set(0)
    _requestCount.set(0)

  def summary(): Map[String, Any] = Map(
    "model"         -> model,
    "requests"      -> requestCount,
    "inputTokens"   -> totalInputTokens,
    "outputTokens"  -> totalOutputTokens,
    "estimatedCost" -> totalCost
  )
