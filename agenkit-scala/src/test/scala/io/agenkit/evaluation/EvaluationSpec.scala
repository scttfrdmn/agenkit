package io.agenkit.evaluation

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class EvaluationSpec extends AnyFunSuite with Matchers:
  // Metric
  test("Metric has name and value"):
    val m = Metric("accuracy", 0.95, "%")
    m.name  shouldBe "accuracy"
    m.value shouldBe 0.95
    m.unit  shouldBe "%"

  // ResponseLengthCriteria
  test("ResponseLengthCriteria measures output length"):
    val criteria = ResponseLengthCriteria()
    val input    = Message.user("hi")
    val output   = Message.assistant("hello world")
    val metric   = Await.result(criteria.evaluate(input, output), 5.seconds)
    metric.value shouldBe 11.0
    metric.unit  shouldBe "chars"

  // LatencyCriteria
  test("LatencyCriteria records provided latency"):
    val criteria = LatencyCriteria(42L)
    val metric   = Await.result(criteria.evaluate(Message.user("in"), Message.assistant("out")), 5.seconds)
    metric.value shouldBe 42.0
    metric.unit  shouldBe "ms"

  // Evaluator
  test("Evaluator runs all criteria"):
    val evaluator = Evaluator(List(ResponseLengthCriteria(), LatencyCriteria(10L)))
    val metrics   = Await.result(evaluator.evaluate(Message.user("hi"), Message.assistant("hello")), 5.seconds)
    metrics should have size 2

  // Benchmark
  test("Benchmark runs all test cases and returns results"):
    val agent     = MockAgent(response = "answer")
    val testCases = List(Message.user("q1"), Message.user("q2"))
    val bench     = Benchmark(agent, testCases, List(ResponseLengthCriteria()))
    val result    = Await.result(bench.run(), 10.seconds)
    result.agentName    shouldBe "mock"
    result.totalRuns    shouldBe 2
    result.successRate  shouldBe 1.0

  test("Benchmark computes success rate with failures"):
    val agent     = MockAgent(shouldFail = true)
    val testCases = List(Message.user("q1"))
    val bench     = Benchmark(agent, testCases, List(ResponseLengthCriteria()))
    val result    = Await.result(bench.run(), 10.seconds)
    result.successRate shouldBe 0.0
