package io.agenkit.patterns

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class CollaborativeAgentSpec extends AnyFunSuite with Matchers:
  test("CollaborativeAgent fans out to all peers"):
    val peer1  = MockAgent(name = "peer1", response = "response A")
    val peer2  = MockAgent(name = "peer2", response = "response B")
    val agent  = CollaborativeAgent("collab", List(peer1, peer2))
    val result = Await.result(agent.process(Message.user("hello")), 5.seconds)
    result.contentString should include("response A")
    result.contentString should include("response B")
    peer1.callCount shouldBe 1
    peer2.callCount shouldBe 1

  test("CollaborativeAgent custom merge strategy"):
    val peer  = MockAgent(name = "peer", response = "peerResp")
    val agent = CollaborativeAgent("collab", List(peer), mergeStrategy = _.mkString("|"))
    val result = Await.result(agent.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "peerResp"

  test("CollaborativeAgent introspect"):
    val agent = CollaborativeAgent("collab", List(MockAgent(), MockAgent()))
    val r     = agent.introspect()
    r.name shouldBe "collab"
    r.capabilities should contain("collaboration")
