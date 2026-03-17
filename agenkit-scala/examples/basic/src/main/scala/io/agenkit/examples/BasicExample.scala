package io.agenkit.examples

import io.agenkit.adapters.MockAdapter
import io.agenkit.core.Message
import io.agenkit.patterns.ConversationalAgent
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

/** Demonstrates a simple conversational agent backed by a mock LLM. */
object BasicExample:
  def main(args: Array[String]): Unit =
    val llm   = MockAdapter("I'm a helpful assistant!")
    val agent = ConversationalAgent("basic-agent", llm, systemPrompt = Some("You are a helpful assistant."))

    val turns = List("Hello!", "What can you do?", "Thank you!")
    turns.foreach { text =>
      val response = Await.result(agent.process(Message.user(text)), 10.seconds)
      println(s"User: $text")
      println(s"Agent: ${response.contentString}")
      println()
    }

    println(s"Conversation history: ${agent.getHistory.size} messages")
    val status = agent.introspect()
    println(s"Processed: ${status.processedMessages} messages")
