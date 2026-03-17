package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.{Await, Future}
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class HumanInLoopAgentSpec extends AnyFunSuite with Matchers:
  test("HumanInLoopAgent proceeds when approved"):
    val inner  = MockAgent(response = "inner response")
    val agent  = HumanInLoopAgent("hilm", inner, _ => Future.successful(true))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "inner response"
    inner.callCount shouldBe 1

  test("HumanInLoopAgent blocks when rejected"):
    val inner  = MockAgent()
    val agent  = HumanInLoopAgent("hilm", inner, _ => Future.successful(false))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "Action not approved by human reviewer"
    inner.callCount shouldBe 0

  test("HumanInLoopAgent custom rejection message"):
    val inner  = MockAgent()
    val agent  = HumanInLoopAgent("hilm", inner, _ => Future.successful(false), "custom rejection")
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "custom rejection"

  test("HumanInLoopAgent introspect"):
    val inner = MockAgent()
    val agent = HumanInLoopAgent("hilm", inner, _ => Future.successful(true))
    val r     = agent.introspect()
    r.name shouldBe "hilm"
    r.capabilities should contain("human-in-loop")
