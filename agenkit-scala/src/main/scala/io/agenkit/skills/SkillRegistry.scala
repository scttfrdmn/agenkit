package io.agenkit.skills

import org.slf4j.LoggerFactory

import java.nio.file.{Files, Path}
import scala.jdk.CollectionConverters.*
import scala.util.Using

/** Discovers and searches agent skills across filesystem paths.
  *
  * Skills are discovered by walking search paths and loading any subdirectory
  * that contains a `SKILL.md` file. Invalid skill directories are skipped with
  * a warning.
  */
class SkillRegistry(searchPaths: List[Path]):
  private val logger  = LoggerFactory.getLogger(getClass)
  private val _skills = scala.collection.mutable.LinkedHashMap.empty[String, AgentSkill]

  /** Walk each search path and load all valid skill directories.
    *
    * Skill directories without a `SKILL.md` or with invalid format are skipped
    * and logged as warnings.
    */
  def discoverSkills(): Unit =
    for searchPath <- searchPaths if Files.isDirectory(searchPath) do
      val entries = Using.resource(Files.list(searchPath))(_.iterator().asScala.toList)
      for entry <- entries if Files.isDirectory(entry) do
        if Files.exists(entry.resolve("SKILL.md")) then
          try
            val skill = AgentSkill.fromDirectory(entry)
            _skills(skill.name) = skill
          catch
            case exc: IllegalArgumentException =>
              logger.warn("skipping skill directory {}: {}", entry, exc.getMessage)

  /** Return skills most relevant to the given query string.
    *
    * Scoring:
    *   - +10 if query (lowercased) appears in skill name (lowercased)
    *   - +5 if query (lowercased) appears in skill description (lowercased)
    *   - +N for each word in query that also appears in the description
    *
    * Only skills with score > 0 are returned, sorted descending and capped at
    * `maxResults`.
    */
  def findRelevantSkills(query: String, maxResults: Int = 5): List[AgentSkill] =
    val queryLower = query.toLowerCase
    val queryWords = queryLower.split("\\s+").filter(_.nonEmpty).toSet

    val scored = _skills.values.flatMap { skill =>
      var score    = 0
      val nameLower = skill.name.toLowerCase
      val descLower = skill.description.toLowerCase

      if nameLower.contains(queryLower) then score += 10
      if descLower.contains(queryLower) then score += 5

      val descWords    = descLower.split("\\s+").filter(_.nonEmpty).toSet
      val wordOverlap  = queryWords.intersect(descWords).size
      score += wordOverlap

      if score > 0 then Some((score, skill)) else None
    }.toList

    scored.sortBy(-_._1).take(maxResults).map(_._2)

  /** Return the skill with the given name, or `None` if not found. */
  def getSkill(name: String): Option[AgentSkill] = _skills.get(name)

  /** Read-only copy of loaded skills keyed by name. */
  def skills: Map[String, AgentSkill] = _skills.toMap
