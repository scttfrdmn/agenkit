package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** ReAct (Reason + Act) agent that interleaves reasoning with tool calls. */
class ReActAgent(
  val name: String,
  llm: LlmClient,
  tools: Map[String, Tool] = Map.empty,
  maxIterations: Int = 10
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("react", "tool-use", "reasoning")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val toolDescs = tools.values.map(t => s"${t.name}: ${t.description}").mkString("\n")
    val systemMsg = Message.system(
      s"""You are a ReAct agent.  Use tools by responding with:
         |THOUGHT: your reasoning
         |ACTION: tool_name
         |PARAMS: key=value,key2=value2
         |
         |When done, respond with:
         |ANSWER: your final answer
         |
         |Available tools:
         |$toolDescs""".stripMargin
    )
    reactLoop(List(systemMsg, message), 0)

  private def reactLoop(
    messages: List[Message],
    iteration: Int
  )(using ExecutionContext): Future[Message] =
    if iteration >= maxIterations then
      Future.successful(Message.of("assistant", "Max iterations reached without answer"))
    else
      llm.complete(messages).flatMap { response =>
        val content = response.contentString
        if content.contains("ANSWER:") then
          val answer = content.split("ANSWER:").last.trim
          Future.successful(Message.of("assistant", answer))
        else if content.contains("ACTION:") then
          val toolName  = extractField(content, "ACTION:")
          val paramsStr = extractField(content, "PARAMS:")
          val params    = parseParams(paramsStr)
          tools.get(toolName) match
            case Some(tool) =>
              tool.execute(params).flatMap { result =>
                val obs = result match
                  case ToolOk(data)    => s"OBSERVATION: $data"
                  case ToolFail(error) => s"OBSERVATION: Error: $error"
                reactLoop(messages ++ List(response, Message.user(obs)), iteration + 1)
              }
            case None =>
              val obs = s"OBSERVATION: Tool '$toolName' not found"
              reactLoop(messages ++ List(response, Message.user(obs)), iteration + 1)
        else
          Future.successful(response)
      }

  private def extractField(content: String, prefix: String): String =
    content.split("\n")
      .find(_.trim.startsWith(prefix))
      .map(_.trim.stripPrefix(prefix).trim)
      .getOrElse("")

  private def parseParams(paramsStr: String): Map[String, Any] =
    if paramsStr.isEmpty then Map.empty
    else
      paramsStr.split(",").flatMap { pair =>
        pair.split("=", 2) match
          case Array(k, v) => Some(k.trim -> (v.trim: Any))
          case _           => None
      }.toMap

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("tools" -> tools.keys.toList, "maxIterations" -> maxIterations),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
