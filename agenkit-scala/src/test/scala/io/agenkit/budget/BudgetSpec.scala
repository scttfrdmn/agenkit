package io.agenkit.budget

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class BudgetSpec extends AnyFunSuite with Matchers:
  // ModelPricing
  test("ModelPricing.get returns pricing for known model"):
    ModelPricing.get("gpt-4o") shouldBe defined

  test("ModelPricing.get returns None for unknown model"):
    ModelPricing.get("unknown-model-xyz") shouldBe empty

  test("ModelPricing.estimateCost returns positive cost"):
    val cost = ModelPricing.estimateCost("gpt-4o", 1000, 500)
    cost should be > 0.0

  test("ModelPricing.estimateCost returns 0 for unknown model"):
    val cost = ModelPricing.estimateCost("unknown", 1000, 500)
    cost shouldBe 0.0

  // CostTracker
  test("CostTracker records usage and computes cost"):
    val tracker = CostTracker("gpt-4o")
    tracker.recordUsage(1000, 500)
    tracker.totalInputTokens  shouldBe 1000L
    tracker.totalOutputTokens shouldBe 500L
    tracker.requestCount      shouldBe 1L
    tracker.totalCost should be > 0.0

  test("CostTracker reset zeroes all fields"):
    val tracker = CostTracker()
    tracker.recordUsage(1000, 500)
    tracker.reset()
    tracker.totalInputTokens  shouldBe 0L
    tracker.totalOutputTokens shouldBe 0L
    tracker.totalCost         shouldBe 0.0

  // BudgetLimiter
  test("BudgetLimiter allows requests under budget"):
    val inner   = MockAgent()
    val limiter = BudgetLimiter(inner, maxCostUsd = 100.0)
    val result  = Await.result(limiter.process(Message.user("test")), 5.seconds)
    result.role shouldBe "assistant"

  test("BudgetLimiter rejects when over budget"):
    val inner   = MockAgent()
    // Tiny budget — after the first call records 100k tokens, cost will exceed the cap
    val limiter = BudgetLimiter(inner, maxCostUsd = 0.000001, estimateTokens = _ => 100000)
    // First call is allowed (budget check happens before recording cost)
    Await.result(limiter.process(Message.user("expensive")), 5.seconds)
    // Second call is rejected because cost is now over the cap
    val ex = Await.result(limiter.process(Message.user("blocked")).failed, 5.seconds)
    ex.getMessage should include("Budget exceeded")

  test("BudgetLimiter introspect"):
    val limiter = BudgetLimiter(MockAgent(), maxCostUsd = 10.0)
    val r       = limiter.introspect()
    r.capabilities should contain("budget-control")
