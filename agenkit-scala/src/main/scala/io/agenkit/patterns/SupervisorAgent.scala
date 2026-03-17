package io.agenkit.patterns

import io.agenkit.adapters.LlmClient
import io.agenkit.core.*
import scala.concurrent.{ExecutionContext, Future}
import java.util.concurrent.atomic.AtomicLong

/** Decomposes a task and delegates sub-tasks to a pool of worker agents. */
class SupervisorAgent(
  val name: String,
  llm: LlmClient,
  workers: List[Agent]
) extends Agent:
  private val _processedCount = new AtomicLong(0)

  def capabilities: List[String] = List("supervision", "decomposition", "coordination")

  def process(message: Message)(using ExecutionContext): Future[Message] =
    _processedCount.incrementAndGet()
    val workerNames = workers.map(_.name).mkString(", ")
    val decomposePrompt = Message.system(
      s"Decompose the task into subtasks, one per worker. Workers: $workerNames. Format: WORKER_NAME: subtask"
    )
    llm.complete(List(decomposePrompt, message)).flatMap { plan =>
      val assignments = parseAssignments(plan.contentString)
      val workerMap   = workers.map(w => w.name.toLowerCase -> w).toMap
      val futures = assignments.flatMap { case (workerName, task) =>
        workerMap.get(workerName.toLowerCase).map(_.process(Message.user(task)))
      }
      Future.sequence(futures).map { results =>
        val combined = results.zipWithIndex
          .map { case (r, i) => s"Worker ${i + 1}: ${r.contentString}" }
          .mkString("\n")
        Message.of("assistant", combined)
      }
    }

  private def parseAssignments(text: String): List[(String, String)] =
    text.split("\n").flatMap { line =>
      line.split(":", 2) match
        case Array(worker, task) => Some(worker.trim -> task.trim)
        case _                   => None
    }.toList

  def introspect(): IntrospectionResult =
    IntrospectionResult(
      name = name,
      metadata = Map("workerCount" -> workers.size, "workers" -> workers.map(_.name)),
      capabilities = capabilities,
      processedMessages = _processedCount.get()
    )
