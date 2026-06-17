package io.agenkit.skills

import io.agenkit.core.{Agent, IntrospectionResult, Message}
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

import java.nio.file.{Files, Path}
import scala.concurrent.duration.*
import scala.concurrent.{Await, ExecutionContext, Future}
import scala.concurrent.ExecutionContext.Implicits.global

class SkillEnabledAgentSpec extends AnyFunSuite with Matchers:

  private def tempDir(): Path = Files.createTempDirectory("agenkit-skills-agent-")

  private def makeSkillDir(
    parent: Path,
    name: String,
    description: String,
    body: String = "Instructions here."
  ): Path =
    val skillDir = Files.createDirectory(parent.resolve(name))
    val content  = s"---\nname: $name\ndescription: $description\n---\n$body"
    Files.writeString(skillDir.resolve("SKILL.md"), content)
    skillDir

  /** Agent that echoes its input content back. */
  private class EchoAgent extends Agent:
    def name: String                = "echo"
    def capabilities: List[String]  = List.empty
    def introspect(): IntrospectionResult = IntrospectionResult(name = name)
    def process(message: Message)(using ExecutionContext): Future[Message] =
      Future.successful(Message(role = "agent", content = message.content, metadata = message.metadata))

  test("augments message with available_skills block"):
    val parent = tempDir()
    makeSkillDir(parent, "pdf-processing", "Extract text from PDF documents.")
    val registry = SkillRegistry(List(parent))
    val agent    = SkillEnabledAgent(EchoAgent(), registry, autoDiscover = true)

    val response = Await.result(agent.process(Message.user("How do I parse pdf files?")), 5.seconds)
    response.contentString should include("<available_skills>")
    response.contentString should include("pdf-processing")

  test("passthrough when no skills are relevant"):
    val parent = tempDir()
    makeSkillDir(parent, "email-compose", "Compose professional emails.")
    val registry = SkillRegistry(List(parent))
    val agent    = SkillEnabledAgent(EchoAgent(), registry, autoDiscover = true)

    val response = Await.result(agent.process(Message.user("tell me a joke")), 5.seconds)
    response.contentString should not include "<available_skills>"
    response.contentString shouldBe "tell me a joke"

  test("active_skills metadata is set"):
    val parent = tempDir()
    makeSkillDir(parent, "csv-tools", "Handle and transform CSV spreadsheets.")
    val registry = SkillRegistry(List(parent))
    val agent    = SkillEnabledAgent(EchoAgent(), registry, autoDiscover = true)

    val response = Await.result(agent.process(Message.user("parse this csv spreadsheet data")), 5.seconds)
    response.metadata should contain key "active_skills"
    response.metadata("active_skills").asInstanceOf[List[String]] should contain("csv-tools")

  test("capabilities include skill_injection"):
    val registry = SkillRegistry(List(tempDir()))
    val agent    = SkillEnabledAgent(EchoAgent(), registry, autoDiscover = false)
    agent.capabilities should contain("skill_injection")

  test("name delegates to wrapped agent"):
    val registry = SkillRegistry(List(tempDir()))
    val agent    = SkillEnabledAgent(EchoAgent(), registry, autoDiscover = false)
    agent.name shouldBe "echo"
