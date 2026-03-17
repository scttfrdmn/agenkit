package io.agenkit.composition

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ConditionalAgentSpec extends AnyFunSuite with Matchers:
  test("ConditionalAgent routes to ifTrue when condition is true"):
    val trueBranch  = MockAgent(name = "true",  response = "true response")
    val falseBranch = MockAgent(name = "false", response = "false response")
    val agent = ConditionalAgent("cond", _.contentString.contains("yes"), trueBranch, falseBranch)
    val result = Await.result(agent.process(Message.user("yes please")), 5.seconds)
    result.contentString shouldBe "true response"
    trueBranch.callCount  shouldBe 1
    falseBranch.callCount shouldBe 0

  test("ConditionalAgent routes to ifFalse when condition is false"):
    val trueBranch  = MockAgent(name = "true",  response = "true response")
    val falseBranch = MockAgent(name = "false", response = "false response")
    val agent = ConditionalAgent("cond", _.contentString.contains("yes"), trueBranch, falseBranch)
    val result = Await.result(agent.process(Message.user("no")), 5.seconds)
    result.contentString shouldBe "false response"
    trueBranch.callCount  shouldBe 0
    falseBranch.callCount shouldBe 1

  test("ConditionalAgent introspect"):
    val agent = ConditionalAgent("cond", _ => true, MockAgent(name = "t"), MockAgent(name = "f"))
    val r     = agent.introspect()
    r.name shouldBe "cond"
    r.capabilities should contain("conditional")
