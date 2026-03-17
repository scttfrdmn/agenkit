package io.agenkit.evaluation

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}

/** Evaluation criterion that produces a single metric for an (input, output) pair. */
trait EvaluationCriteria:
  def name: String
  def evaluate(input: Message, output: Message)(using ExecutionContext): Future[Metric]

/** Measures response length in characters. */
class ResponseLengthCriteria extends EvaluationCriteria:
  def name: String = "response_length"
  def evaluate(input: Message, output: Message)(using ExecutionContext): Future[Metric] =
    Future.successful(Metric("response_length", output.contentString.length.toDouble, "chars"))

/** Records a pre-measured latency as a metric. */
class LatencyCriteria(latencyMs: Long) extends EvaluationCriteria:
  def name: String = "latency"
  def evaluate(input: Message, output: Message)(using ExecutionContext): Future[Metric] =
    Future.successful(Metric("latency", latencyMs.toDouble, "ms"))

/** Runs a list of criteria against a single (input, output) pair. */
class Evaluator(
  criteria: List[EvaluationCriteria]
):
  def evaluate(input: Message, output: Message)(using ExecutionContext): Future[List[Metric]] =
    Future.sequence(criteria.map(_.evaluate(input, output)))
