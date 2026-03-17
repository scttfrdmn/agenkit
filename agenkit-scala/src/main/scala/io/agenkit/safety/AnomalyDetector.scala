package io.agenkit.safety

import io.agenkit.core.Message
import java.util.concurrent.atomic.AtomicLong

/** Detects request-rate anomalies within a sliding time window. */
class AnomalyDetector(
  rateThreshold: Int = 100,
  windowMs: Long = 60000L
):
  private val requestCount = new AtomicLong(0)
  private val windowStart  = new AtomicLong(System.currentTimeMillis())

  /** Returns true if the current request rate exceeds the threshold. */
  def detect(message: Message): Boolean =
    val now   = System.currentTimeMillis()
    val start = windowStart.get()
    if now - start > windowMs then
      windowStart.set(now)
      requestCount.set(1)
      false
    else
      requestCount.incrementAndGet() > rateThreshold
