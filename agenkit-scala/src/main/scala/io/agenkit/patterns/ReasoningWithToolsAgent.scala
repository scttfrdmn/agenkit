package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Step-by-step reasoning agent that can invoke tools between reasoning steps. */
class ReasoningWithToolsAgent(
  val name: String,
  llm: LlmClient,
  tools: Map[String, Tool] = Map.empty,
  maxSteps: Int = 10
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("reasoning", "tool-use", "step-by-step")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val toolDescs = tools.values.map(t => s"${t.name}: ${t.description}").mkString("\n")
    val systemMsg = Message.system(
      s"""Reason step by step.  Use:
         |THINK: your reasoning
         |USE_TOOL: tool_name with params key=value
         |ANSWER: final answer
         |
         |Tools: $toolDescs""".stripMargin
    )
    reasoningLoop(List(systemMsg, message), 0)

  private def reasoningLoop(
    context: List[Message],
    step: Int
  )(using ExecutionContext): Future[Message] =
    if step >= maxSteps then
      Future.successful(Message.of("assistant", "Max reasoning steps reached"))
    else
      llm.complete(context).flatMap { response =>
        val content = response.contentString
        if content.contains("ANSWER:") then
          val answer = content.split("ANSWER:").last.trim
          Future.successful(Message.of("assistant", answer))
        else if content.contains("USE_TOOL:") then
          val toolLine = content.split("\n").find(_.contains("USE_TOOL:")).getOrElse("")
          val parts    = toolLine.stripPrefix("USE_TOOL:").trim.split("\\s+with\\s+params\\s+", 2)
          val toolName = if parts.nonEmpty then parts(0).trim else ""
          val params   = if parts.length > 1 then parseParams(parts(1)) else Map.empty[String, Any]
          tools.get(toolName) match
            case Some(tool) =>
              tool.execute(params).flatMap { result =>
                val obs = result match
                  case ToolOk(data)    => s"TOOL_RESULT: $data"
                  case ToolFail(error) => s"TOOL_RESULT: Error: $error"
                reasoningLoop(context ++ List(response, Message.user(obs)), step + 1)
              }
            case None =>
              val obs = s"TOOL_RESULT: Tool '$toolName' not found"
              reasoningLoop(context ++ List(response, Message.user(obs)), step + 1)
        else
          reasoningLoop(context :+ response, step + 1)
      }

  private def parseParams(str: String): Map[String, Any] =
    str.split(",").flatMap { p =>
      p.split("=", 2) match
        case Array(k, v) => Some(k.trim -> (v.trim: Any))
        case _           => None
    }.toMap

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("tools" -> tools.keys.toList, "maxSteps" -> maxSteps),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
