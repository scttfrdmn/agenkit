package io.agenkit.properties

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import org.scalatestplus.scalacheck.ScalaCheckPropertyChecks

class MessagePropertySpec extends AnyFunSuite with Matchers with ScalaCheckPropertyChecks:

  test("role survives round-trip"):
    forAll { (role: String, text: String) =>
      whenever(role.nonEmpty) {
        val msg = Message.of(role, text)
        msg.role shouldBe role
      }
    }

  test("content survives round-trip"):
    forAll { (text: String) =>
      val msg = Message.of("user", text)
      msg.contentString shouldBe text
    }

  test("Message.user always produces user role"):
    forAll { (text: String) =>
      Message.user(text).role shouldBe "user"
    }

  test("Message.assistant always produces assistant role"):
    forAll { (text: String) =>
      Message.assistant(text).role shouldBe "assistant"
    }

  test("Message.system always produces system role"):
    forAll { (text: String) =>
      Message.system(text).role shouldBe "system"
    }

  test("contentString never throws for any content"):
    forAll { (text: String) =>
      val msg = Message.of("user", text)
      noException should be thrownBy msg.contentString
    }

  test("metadata defaults to empty for factory methods"):
    forAll { (text: String) =>
      Message.user(text).metadata shouldBe Map.empty
    }

  test("copy with updated content preserves role"):
    forAll { (role: String, original: String, updated: String) =>
      whenever(role.nonEmpty) {
        val msg  = Message.of(role, original)
        val copy = msg.copy(content = Some(updated))
        copy.role shouldBe role
        copy.contentString shouldBe updated
      }
    }

  test("Message with None content has empty contentString"):
    forAll { (role: String) =>
      whenever(role.nonEmpty) {
        val msg = Message(role = role, content = None)
        msg.contentString shouldBe ""
      }
    }

  test("Message.of with any non-empty role does not throw"):
    forAll { (role: String, text: String) =>
      whenever(role.nonEmpty) {
        noException should be thrownBy Message.of(role, text)
      }
    }
