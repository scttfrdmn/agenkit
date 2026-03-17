package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import io.agenkit.memory.Memory
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Retrieves relevant memories before each LLM call and stores the exchange afterwards. */
class MemoryAugmentedAgent(
  val name: String,
  llm: LlmClient,
  memory: Memory,
  maxMemoryItems: Int = 5
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("memory-augmented", "context-aware")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val relevant   = memory.retrieve(message.contentString, maxMemoryItems)
    val contextStr =
      if relevant.nonEmpty then
        s"Relevant memories:\n${relevant.map(m => s"- ${m.contentString}").mkString("\n")}\n\n"
      else ""
    val augmented  = Message.user(contextStr + message.contentString)
    llm.complete(List(augmented)).map { response =>
      memory.store(message)
      memory.store(response)
      response
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("memorySize" -> memory.size, "maxMemoryItems" -> maxMemoryItems),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
