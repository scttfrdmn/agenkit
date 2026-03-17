package io.agenkit.examples

import io.agenkit.adapters.MockAdapter
import io.agenkit.core.*
import io.agenkit.patterns.ConversationalAgent
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

/** Demonstrates simulated streaming by chunking a response into token-sized messages.
 *
 *  Full streaming requires a real LLM adapter with SSE / chunked transport.
 *  This example shows the pattern using a mock LLM.
 */
object StreamingExample:
  def main(args: Array[String]): Unit =
    val llm   = MockAdapter("The quick brown fox jumps over the lazy dog.")
    val agent = ConversationalAgent("stream-agent", llm)

    println("Streaming simulation:")
    val response = Await.result(agent.process(Message.user("Tell me something")), 10.seconds)

    // Simulate token-by-token display
    response.contentString.split(" ").foreach { token =>
      print(s"$token ")
      Thread.sleep(50) // simulate streaming delay
    }
    println()

    println(s"\nFull response: ${response.contentString}")
    println(s"History size:  ${agent.getHistory.size}")
