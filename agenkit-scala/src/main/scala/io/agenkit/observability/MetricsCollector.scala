package io.agenkit.observability

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong
import scala.jdk.CollectionConverters.*

/** Thread-safe metrics collector with counters, gauges, and histograms. */
class MetricsCollector:
  private val counters   = new ConcurrentHashMap[String, AtomicLong]()
  private val gauges     = new ConcurrentHashMap[String, AtomicLong]()
  private val histograms = new ConcurrentHashMap[String, collection.mutable.ListBuffer[Double]]()

  def incrementCounter(name: String, value: Long = 1): Unit =
    counters.computeIfAbsent(name, _ => new AtomicLong(0)).addAndGet(value)
    ()

  def setGauge(name: String, value: Long): Unit =
    gauges.computeIfAbsent(name, _ => new AtomicLong(0)).set(value)

  def recordHistogram(name: String, value: Double): Unit =
    val buf = histograms.computeIfAbsent(name, _ => collection.mutable.ListBuffer[Double]())
    buf.synchronized { buf.addOne(value) }

  def getCounter(name: String): Long =
    Option(counters.get(name)).map(_.get()).getOrElse(0L)

  def getGauge(name: String): Long =
    Option(gauges.get(name)).map(_.get()).getOrElse(0L)

  def getHistogramStats(name: String): Map[String, Double] =
    Option(histograms.get(name)).map { buf =>
      val values = buf.synchronized { buf.toList }
      if values.isEmpty then Map("count" -> 0.0, "mean" -> 0.0, "p99" -> 0.0)
      else
        val sorted = values.sorted
        Map(
          "count" -> values.size.toDouble,
          "mean"  -> values.sum / values.size,
          "p50"   -> sorted(values.size / 2),
          "p99"   -> sorted((values.size * 0.99).toInt.min(values.size - 1))
        )
    }.getOrElse(Map.empty)

  def snapshot(): Map[String, Any] =
    Map(
      "counters" -> counters.keys().asScala.toList.map(k => k -> getCounter(k)).toMap,
      "gauges"   -> gauges.keys().asScala.toList.map(k => k -> getGauge(k)).toMap
    )
