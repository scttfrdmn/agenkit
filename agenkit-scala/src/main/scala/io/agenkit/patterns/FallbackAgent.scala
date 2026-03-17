package io.agenkit.patterns

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Tries each agent in order and returns the first success. */
class FallbackAgent(
  val name: String,
  agents: List[Agent]
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("fallback", "resilience")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    tryAgents(message, agents)

  private def tryAgents(message: Message, remaining: List[Agent])(using ExecutionContext): Future[Message] =
    remaining match
      case Nil         => Future.failed(new RuntimeException("All agents failed"))
      case head :: tail => head.process(message).recoverWith { case _ => tryAgents(message, tail) }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("agentCount" -> agents.size, "agents" -> agents.map(_.name)),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
