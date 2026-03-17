package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Uses an LLM to dynamically select the best agent for each request. */
class MultiAgentOrchestrator(
  val name: String,
  llm: LlmClient,
  agents: Map[String, Agent]
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("multi-agent", "llm-routing", "orchestration")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val agentDescs = agents
      .map { case (k, v) => s"$k: ${v.capabilities.mkString(", ")}" }
      .mkString("\n")
    val routePrompt = Message.system(
      s"Select the best agent for this task. Available agents:\n$agentDescs\nRespond with only the agent name."
    )
    llm.complete(List(routePrompt, message)).flatMap { selection =>
      val agentName = selection.contentString.trim.toLowerCase
      agents.find { case (k, _) => k.toLowerCase == agentName }.map(_._2)
        .map(_.process(message))
        .getOrElse(Future.successful(Message.of("assistant", s"Agent not found: $agentName")))
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("agentCount" -> agents.size, "agents" -> agents.keys.toList),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
