package io.agenkit.evaluation

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}

case class BenchmarkResult(
  agentName: String,
  metrics: List[Metric],
  totalRuns: Int,
  successRate: Double
)

/** Runs an agent against a suite of test cases and computes aggregate metrics. */
class Benchmark(
  agent: Agent,
  testCases: List[Message],
  criteria: List[EvaluationCriteria]
):
  private val evaluator = Evaluator(criteria)

  def run()(using ExecutionContext): Future[BenchmarkResult] =
    val futures = testCases.map { testCase =>
      val start = System.currentTimeMillis()
      agent.process(testCase)
        .flatMap { output =>
          val latency      = System.currentTimeMillis() - start
          val latencyCrit  = LatencyCriteria(latency)
          val allCriteria  = criteria :+ latencyCrit
          Evaluator(allCriteria).evaluate(testCase, output).map(metrics => (true, metrics))
        }
        .recover { case _ => (false, List.empty[Metric]) }
    }
    Future.sequence(futures).map { results =>
      val successes  = results.count(_._1)
      val allMetrics = results.flatMap(_._2)
      val avgMetrics = allMetrics.groupBy(_.name).map { case (name, ms) =>
        Metric(name, ms.map(_.value).sum / ms.size, ms.headOption.map(_.unit).getOrElse(""))
      }.toList
      BenchmarkResult(
        agentName   = agent.name,
        metrics     = avgMetrics,
        totalRuns   = testCases.size,
        successRate = if testCases.isEmpty then 1.0 else successes.toDouble / testCases.size
      )
    }
