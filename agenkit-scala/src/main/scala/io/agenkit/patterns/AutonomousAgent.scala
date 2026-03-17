package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Self-driven agent that keeps iterating until a goal predicate is satisfied. */
class AutonomousAgent(
  val name: String,
  llm: LlmClient,
  goalChecker: String => Boolean = _.contains("COMPLETE"),
  maxIterations: Int = 10
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("autonomous", "goal-driven")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    autonomousLoop(List(message), 0)

  private def autonomousLoop(
    context: List[Message],
    iteration: Int
  )(using ExecutionContext): Future[Message] =
    if iteration >= maxIterations then
      Future.successful(Message.of("assistant", "Goal not achieved within max iterations"))
    else
      llm.complete(context).flatMap { response =>
        if goalChecker(response.contentString) then Future.successful(response)
        else autonomousLoop(context :+ response, iteration + 1)
      }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("maxIterations" -> maxIterations),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
