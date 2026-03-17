package io.agenkit.safety

import io.agenkit.core.Message
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

class SafetySpec extends AnyFunSuite with Matchers:
  // InputValidator
  test("InputValidator accepts valid message"):
    val v      = InputValidator(maxLength = 100)
    val result = v.validate(Message.user("hello"))
    result shouldBe a[Right[?, ?]]

  test("InputValidator rejects message exceeding maxLength"):
    val v      = InputValidator(maxLength = 5)
    val result = v.validate(Message.user("this is too long"))
    result shouldBe a[Left[?, ?]]
    result.left.get should include("too long")

  test("InputValidator rejects blocked content"):
    val v      = InputValidator(blockedPatterns = List("badword"))
    val result = v.validate(Message.user("contains badword here"))
    result shouldBe a[Left[?, ?]]

  // OutputValidator
  test("OutputValidator accepts valid output"):
    val v      = OutputValidator(maxLength = 1000)
    val result = v.validate(Message.assistant("ok"))
    result shouldBe a[Right[?, ?]]

  test("OutputValidator rejects output exceeding maxLength"):
    val v      = OutputValidator(maxLength = 3)
    val result = v.validate(Message.assistant("too long"))
    result shouldBe a[Left[?, ?]]

  test("OutputValidator rejects missing required fields"):
    val v      = OutputValidator(requiredFields = List("ANSWER"))
    val result = v.validate(Message.assistant("no answer here"))
    result shouldBe a[Left[?, ?]]

  // PermissionChecker
  test("PermissionChecker allows permitted action"):
    val checker = PermissionChecker(Map("alice" -> List("read", "write")))
    checker.check("alice", "read") shouldBe true

  test("PermissionChecker rejects unpermitted action"):
    val checker = PermissionChecker(Map("alice" -> List("read")))
    checker.check("alice", "delete") shouldBe false

  test("PermissionChecker wildcard grants to all"):
    val checker = PermissionChecker(Map("*" -> List("read")))
    checker.check("anyone", "read") shouldBe true

  // AnomalyDetector
  test("AnomalyDetector returns false for normal rate"):
    val detector = AnomalyDetector(rateThreshold = 100)
    detector.detect(Message.user("test")) shouldBe false

  test("AnomalyDetector returns true when threshold exceeded"):
    val detector = AnomalyDetector(rateThreshold = 2)
    detector.detect(Message.user("1"))
    detector.detect(Message.user("2"))
    detector.detect(Message.user("3")) shouldBe true

  // AuditLogger
  test("AuditLogger records entries"):
    val logger = AuditLogger()
    logger.log(Message.user("hello"), "process")
    logger.getEntries should have size 1
    logger.getEntries.head.action shouldBe "process"

  test("AuditLogger clear removes entries"):
    val logger = AuditLogger()
    logger.log(Message.user("test"), "action")
    logger.clearEntries()
    logger.getEntries shouldBe empty
