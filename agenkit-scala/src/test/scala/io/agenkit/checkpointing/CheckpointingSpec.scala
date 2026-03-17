package io.agenkit.checkpointing

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global
import java.util.UUID

class CheckpointingSpec extends AnyFunSuite with Matchers:
  // CheckpointManager
  test("CheckpointManager saves and loads checkpoint"):
    val manager = CheckpointManager()
    val cp      = Checkpoint("id1", "agent1", List(Message.user("hi")), Map.empty)
    manager.save(cp)
    manager.load("id1") shouldBe Some(cp)

  test("CheckpointManager returns None for missing id"):
    val manager = CheckpointManager()
    manager.load("nonexistent") shouldBe empty

  test("CheckpointManager lists checkpoints by agent name"):
    val manager = CheckpointManager()
    manager.save(Checkpoint("1", "agent1", List.empty, Map.empty))
    manager.save(Checkpoint("2", "agent2", List.empty, Map.empty))
    manager.save(Checkpoint("3", "agent1", List.empty, Map.empty))
    val agent1Cps = manager.list("agent1")
    agent1Cps should have size 2

  test("CheckpointManager deletes checkpoint"):
    val manager = CheckpointManager()
    val cp      = Checkpoint("del-id", "agent", List.empty, Map.empty)
    manager.save(cp)
    manager.delete("del-id") shouldBe true
    manager.load("del-id") shouldBe empty

  test("CheckpointManager count returns number of checkpoints"):
    val manager = CheckpointManager()
    manager.save(Checkpoint("a", "agent", List.empty, Map.empty))
    manager.save(Checkpoint("b", "agent", List.empty, Map.empty))
    manager.count shouldBe 2

  // DurableAgent
  test("DurableAgent processes messages normally"):
    val inner   = MockAgent(response = "ok")
    val manager = CheckpointManager()
    val durable = DurableAgent(inner, manager)
    val result  = Await.result(durable.process(Message.user("test")), 5.seconds)
    result.contentString shouldBe "ok"

  test("DurableAgent checkpoints at interval"):
    val inner   = MockAgent()
    val manager = CheckpointManager()
    val durable = DurableAgent(inner, manager, checkpointInterval = 2)
    Await.result(durable.process(Message.user("msg1")), 5.seconds)
    Await.result(durable.process(Message.user("msg2")), 5.seconds)
    manager.count shouldBe 1

  test("DurableAgent restores from checkpoint"):
    val inner   = MockAgent()
    val manager = CheckpointManager()
    val durable = DurableAgent(inner, manager, checkpointInterval = 1)
    Await.result(durable.process(Message.user("saved")), 5.seconds)
    val cps = manager.list(inner.name)
    cps should not be empty
    durable.restoreFromCheckpoint(cps.head.id) shouldBe true

  test("DurableAgent restoreFromCheckpoint returns false for missing id"):
    val inner   = MockAgent()
    val manager = CheckpointManager()
    val durable = DurableAgent(inner, manager)
    durable.restoreFromCheckpoint("nonexistent") shouldBe false

  test("DurableAgent introspect"):
    val inner   = MockAgent()
    val manager = CheckpointManager()
    val durable = DurableAgent(inner, manager)
    val r       = durable.introspect()
    r.capabilities should contain("checkpointing")
