package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Decomposes a goal into numbered steps and executes each in sequence. */
class PlanningAgent(
  val name: String,
  llm: LlmClient,
  maxSteps: Int = 10
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("planning", "multi-step")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val planPrompt = Message.system(
      "Create a numbered plan to accomplish the task. List each step on a new line starting with '1.', '2.', etc."
    )
    llm.complete(List(planPrompt, message)).flatMap { planResponse =>
      val steps = extractSteps(planResponse.contentString)
      executePlan(steps, message.contentString)
    }

  private def extractSteps(planText: String): List[String] =
    planText.split("\n")
      .filter(line => line.trim.matches("\\d+\\..*"))
      .map(line => line.trim.replaceFirst("\\d+\\.", "").trim)
      .take(maxSteps)
      .toList

  private def executePlan(steps: List[String], goal: String)(using ExecutionContext): Future[Message] =
    steps.foldLeft(Future.successful(List.empty[String])) { (accFut, step) =>
      accFut.flatMap { results =>
        val stepPrompt = Message.user(
          s"Execute step: $step\nGoal: $goal\nPrevious results: ${results.mkString("; ")}"
        )
        llm.complete(List(stepPrompt)).map(response => results :+ response.contentString)
      }
    }.map { results =>
      val summary = results.zipWithIndex
        .map { case (r, i) => s"${i + 1}. $r" }
        .mkString("\n")
      Message.of("assistant", s"Plan executed:\n$summary")
    }

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("maxSteps" -> maxSteps),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
