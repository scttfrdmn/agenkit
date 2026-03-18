package io.agenkit.properties

import io.agenkit.core.Message
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import org.scalatestplus.scalacheck.ScalaCheckPropertyChecks
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class AgentPropertySpec extends AnyFunSuite with Matchers with ScalaCheckPropertyChecks:

  test("MockAgent name is stable across multiple accesses"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val agent = MockAgent(name = name)
        agent.name shouldBe agent.name
        agent.name shouldBe name
      }
    }

  test("MockAgent response is deterministic for same input"):
    forAll { (text: String, response: String) =>
      val agent   = MockAgent(response = response)
      val result1 = Await.result(agent.process(Message.user(text)), 5.seconds)
      val result2 = Await.result(agent.process(Message.user(text)), 5.seconds)
      result1.contentString shouldBe result2.contentString
    }

  test("MockAgent always returns assistant role on success"):
    forAll { (text: String) =>
      val agent  = MockAgent()
      val result = Await.result(agent.process(Message.user(text)), 5.seconds)
      result.role shouldBe "assistant"
    }

  test("MockAgent name is unchanged after sequential calls"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val agent = MockAgent(name = name)
        Await.result(agent.process(Message.user("msg1")), 5.seconds)
        Await.result(agent.process(Message.user("msg2")), 5.seconds)
        agent.name shouldBe name
      }
    }

  test("MockAgent introspect name equals constructor name"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val agent = MockAgent(name = name)
        agent.introspect().name shouldBe name
      }
    }

  test("Multiple agents are independent"):
    forAll { (name1: String, name2: String) =>
      whenever(name1.nonEmpty && name2.nonEmpty && name1 != name2) {
        val a1 = MockAgent(name = name1)
        val a2 = MockAgent(name = name2)
        Await.result(a1.process(Message.user("q")), 5.seconds)
        a1.callCount shouldBe 1
        a2.callCount shouldBe 0
      }
    }

  test("MockAgent processes empty content without throwing"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val agent = MockAgent(name = name)
        noException should be thrownBy Await.result(agent.process(Message.user("")), 5.seconds)
      }
    }

  test("MockAgent works with short single-character names"):
    forAll { (c: Char) =>
      whenever(c.isLetterOrDigit) {
        val agent = MockAgent(name = c.toString)
        agent.name shouldBe c.toString
      }
    }

  test("MockAgent works with names up to 100 characters"):
    forAll { (name: String) =>
      whenever(name.nonEmpty && name.length <= 100) {
        val agent = MockAgent(name = name)
        agent.name.length should be <= 100
      }
    }

  test("MockAgent capabilities list is never null"):
    forAll { (name: String) =>
      whenever(name.nonEmpty) {
        val agent = MockAgent(name = name)
        agent.capabilities should not be null
      }
    }
