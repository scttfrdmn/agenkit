package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Stateful agent that maintains a conversation history across turns. */
class ConversationalAgent(
  val name: String,
  llm: LlmClient,
  systemPrompt: Option[String] = None,
  maxHistorySize: Int = 100
) extends Agent:
  private val history          = collection.mutable.ListBuffer[Message]()
  private val _processedCount  = new AtomicLong(0)

  def capabilities: List[String] = List("conversation", "context-aware")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    history += message
    val messages = systemPrompt
      .map(p => Message.system(p) :: history.toList)
      .getOrElse(history.toList)
    llm.complete(messages).map { response =>
      _processedCount.incrementAndGet()
      history += response
      if history.size > maxHistorySize * 2 then
        history.remove(0, history.size - maxHistorySize * 2)
      response
    }

  def clearHistory(): Unit         = history.clear()
  def getHistory: List[Message]    = history.toList

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("historySize" -> history.size, "maxHistorySize" -> maxHistorySize),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
