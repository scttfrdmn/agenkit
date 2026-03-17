package io.agenkit.memory

import io.agenkit.core.Message
import scala.collection.mutable

/** Cosine-similarity-based in-memory vector store using simple TF-style embeddings. */
class VectorMemory(
  maxSize: Int = 10000
) extends Memory:
  private val items = mutable.ListBuffer[(Message, Array[Double])]()

  def store(message: Message): Unit =
    items.synchronized {
      val vector = toVector(message.contentString)
      items += (message -> vector)
      if items.size > maxSize then items.remove(0)
    }

  def retrieve(query: String, limit: Int = 10): List[Message] =
    items.synchronized {
      val queryVec = toVector(query)
      items.map { case (msg, vec) => (msg, cosineSimilarity(queryVec, vec)) }
        .sortBy(-_._2)
        .take(limit)
        .map(_._1)
        .toList
    }

  def clear(): Unit = items.synchronized { items.clear() }
  def size: Int     = items.synchronized { items.size }

  private def toVector(text: String): Array[Double] =
    val words = text.toLowerCase.split("\\s+")
    if words.isEmpty || (words.length == 1 && words(0).isEmpty) then Array.empty[Double]
    else
      val freq  = words.groupBy(identity).view.mapValues(_.length.toDouble).toMap
      val maxF  = freq.values.max
      words.distinct.sorted.map(w => freq.getOrElse(w, 0.0) / maxF)

  private def cosineSimilarity(a: Array[Double], b: Array[Double]): Double =
    if a.isEmpty || b.isEmpty then 0.0
    else
      val len   = math.min(a.length, b.length)
      val dot   = (0 until len).map(i => a(i) * b(i)).sum
      val normA = math.sqrt(a.map(x => x * x).sum)
      val normB = math.sqrt(b.map(x => x * x).sum)
      if normA == 0 || normB == 0 then 0.0 else dot / (normA * normB)
