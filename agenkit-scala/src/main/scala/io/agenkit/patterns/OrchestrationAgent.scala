package io.agenkit.patterns

import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

enum OrchestrationMode:
  case Sequential, Parallel, Router

/** Orchestrates a set of agents using one of three execution modes. */
class OrchestrationAgent(
  val name: String,
  agents: List[Agent],
  mode: OrchestrationMode = OrchestrationMode.Sequential,
  routingFunction: Message => String = _ => ""
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("orchestration", mode.toString.toLowerCase)

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    mode match
      case OrchestrationMode.Sequential =>
        agents.foldLeft(Future.successful(message)) { (msgFut, agent) =>
          msgFut.flatMap(agent.process)
        }
      case OrchestrationMode.Parallel =>
        Future.sequence(agents.map(_.process(message))).map { responses =>
          Message.of("assistant", responses.map(_.contentString).mkString("\n\n"))
        }
      case OrchestrationMode.Router =>
        val target = routingFunction(message)
        agents.find(_.name == target)
          .map(_.process(message))
          .getOrElse(Future.successful(Message.of("assistant", s"No agent found: $target")))

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("mode" -> mode.toString, "agentCount" -> agents.size),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
