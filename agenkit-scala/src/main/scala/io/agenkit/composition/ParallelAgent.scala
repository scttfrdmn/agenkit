package io.agenkit.composition

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Runs all agents concurrently and merges their responses with a configurable strategy. */
class ParallelAgent(
  val name: String,
  agents: List[Agent],
  merger: List[Message] => Message = msgs =>
    Message.of("assistant", msgs.map(_.contentString).mkString("\n\n"))
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("parallel", "fan-out")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    Future.sequence(agents.map(_.process(message))).map(merger)

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("agentCount" -> agents.size, "agents" -> agents.map(_.name)),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
