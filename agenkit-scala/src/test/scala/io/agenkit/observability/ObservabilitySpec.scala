package io.agenkit.observability

import io.agenkit.core.*
import io.agenkit.helpers.MockAgent
import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers
import scala.concurrent.Await
import scala.concurrent.duration.*
import scala.concurrent.ExecutionContext.Implicits.global

class ObservabilitySpec extends AnyFunSuite with Matchers:
  // TracingAgent
  test("TracingAgent records a span on success"):
    val inner  = MockAgent()
    val tracer = TracingAgent(inner)
    Await.result(tracer.process(Message.user("test")), 5.seconds)
    tracer.getSpans should have size 1
    tracer.getSpans.head.success shouldBe true

  test("TracingAgent records failed span"):
    val inner  = MockAgent(shouldFail = true)
    val tracer = TracingAgent(inner)
    Await.result(tracer.process(Message.user("fail")).recover { case _ => Message.of("assistant", "") }, 5.seconds)
    tracer.getSpans should have size 1
    tracer.getSpans.head.success shouldBe false

  test("TracingAgent propagates trace_id in metadata"):
    val inner  = MockAgent()
    val tracer = TracingAgent(inner)
    val msg    = Message(role = "user", content = Some("test"), metadata = Map("trace_id" -> "abc"))
    Await.result(tracer.process(msg), 5.seconds)
    tracer.getSpans.head.traceId shouldBe "abc"

  test("TracingAgent introspect"):
    val tracer = TracingAgent(MockAgent())
    val r      = tracer.introspect()
    r.capabilities should contain("tracing")

  // MetricsCollector
  test("MetricsCollector increments counter"):
    val mc = MetricsCollector()
    mc.incrementCounter("requests")
    mc.incrementCounter("requests")
    mc.getCounter("requests") shouldBe 2L

  test("MetricsCollector sets gauge"):
    val mc = MetricsCollector()
    mc.setGauge("active", 42L)
    mc.getGauge("active") shouldBe 42L

  test("MetricsCollector records histogram"):
    val mc = MetricsCollector()
    mc.recordHistogram("latency", 10.0)
    mc.recordHistogram("latency", 20.0)
    val stats = mc.getHistogramStats("latency")
    stats("count") shouldBe 2.0
    stats("mean") shouldBe 15.0

  test("MetricsCollector snapshot returns maps"):
    val mc = MetricsCollector()
    mc.incrementCounter("c")
    mc.setGauge("g", 1L)
    val snap = mc.snapshot()
    snap.contains("counters") shouldBe true
    snap.contains("gauges") shouldBe true
