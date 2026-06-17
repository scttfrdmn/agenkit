package io.agenkit.skills

import java.nio.file.{Files, Path}
import scala.io.Source
import scala.util.Using

/** Represents a single agent skill loaded from a directory.
  *
  * A skill directory must contain a `SKILL.md` file structured as:
  * {{{
  * ---
  * name: skill-name
  * description: What this skill does.
  * license: Apache-2.0  # optional
  * metadata:            # optional
  *   key: value
  * ---
  * # Skill Title
  * Markdown instructions here.
  * }}}
  */
case class AgentSkill(
  name: String,
  description: String,
  instructions: String,
  license: Option[String] = None,
  metadata: Map[String, Any] = Map.empty,
  skillDir: Option[Path] = None
):
  /** Render the skill as a prompt block for injection into agent messages. */
  def toPrompt: String =
    s"# Skill: $name\n\n" +
      s"## Description\n$description\n\n" +
      s"## Instructions\n$instructions\n"

object AgentSkill:
  /** Load a skill from a directory containing a `SKILL.md` file.
    *
    * @throws IllegalArgumentException
    *   if the directory lacks `SKILL.md`, has invalid frontmatter, or is
    *   missing required fields (name, description).
    */
  def fromDirectory(skillDir: Path): AgentSkill =
    val skillFile = skillDir.resolve("SKILL.md")
    if !Files.exists(skillFile) then
      throw new IllegalArgumentException(s"No SKILL.md found in $skillDir")

    val raw = Using.resource(Source.fromFile(skillFile.toFile, "UTF-8"))(_.mkString)

    // Split on "---" delimiters. File must start with "---".
    val parts = splitOnDelimiter(raw, "---", limit = 3)
    if parts.length < 3 then
      throw new IllegalArgumentException(
        s"Invalid SKILL.md in $skillDir: missing frontmatter delimiters"
      )

    val frontmatterText = parts(1).strip()
    val instructions    = parts(2).strip()

    val fm = parseFrontmatter(frontmatterText)

    val name = fm.get("name").collect { case s: String => s }.filter(_.nonEmpty)
    if name.isEmpty then
      throw new IllegalArgumentException(s"Missing required field 'name' in $skillDir/SKILL.md")

    val description = fm.get("description").collect { case s: String => s }.filter(_.nonEmpty)
    if description.isEmpty then
      throw new IllegalArgumentException(
        s"Missing required field 'description' in $skillDir/SKILL.md"
      )

    val license = fm.get("license").collect { case s: String => s }
    val metadata = fm.get("metadata") match
      case Some(m: Map[?, ?]) => m.asInstanceOf[Map[String, Any]]
      case _                  => Map.empty[String, Any]

    AgentSkill(
      name = name.get,
      description = description.get,
      instructions = instructions,
      license = license,
      metadata = metadata,
      skillDir = Some(skillDir)
    )

  /** Split `text` on `delimiter`, producing at most `limit` parts (mirrors
    * Python's `str.split(sep, maxsplit)` where `limit == maxsplit + 1`).
    */
  private def splitOnDelimiter(text: String, delimiter: String, limit: Int): Array[String] =
    val parts  = scala.collection.mutable.ArrayBuffer.empty[String]
    var start  = 0
    var splits = 0
    var idx    = text.indexOf(delimiter, start)
    while idx >= 0 && splits < limit - 1 do
      parts += text.substring(start, idx)
      start = idx + delimiter.length
      splits += 1
      idx = text.indexOf(delimiter, start)
    parts += text.substring(start)
    parts.toArray

  /** Minimal YAML frontmatter parser supporting the subset used by skills:
    * top-level `key: value` scalars plus a single nested mapping (e.g.
    * `metadata:` followed by indented `key: value` lines). Quotes are stripped.
    */
  private def parseFrontmatter(text: String): Map[String, Any] =
    val result = scala.collection.mutable.LinkedHashMap.empty[String, Any]
    val arr    = text.split("\n", -1)
    var i      = 0
    while i < arr.length do
      val line    = arr(i)
      val trimmed = line.strip()
      if trimmed.isEmpty || trimmed.startsWith("#") then i += 1
      else if isTopLevel(line) then
        val (key, value) = splitKeyValue(trimmed)
        if value.isEmpty then
          // Possible nested mapping: gather following indented lines.
          val nested = scala.collection.mutable.LinkedHashMap.empty[String, Any]
          var j      = i + 1
          while j < arr.length && (arr(j).strip().isEmpty || isIndented(arr(j))) do
            val nl = arr(j).strip()
            if nl.nonEmpty && !nl.startsWith("#") then
              val (nk, nv) = splitKeyValue(nl)
              nested(nk) = stripQuotes(nv)
            j += 1
          if nested.nonEmpty then result(key) = nested.toMap
          else result(key) = stripQuotes(value)
          i = j
        else
          result(key) = stripQuotes(value)
          i += 1
      else i += 1
    result.toMap

  private def isTopLevel(line: String): Boolean =
    line.nonEmpty && !line.charAt(0).isWhitespace

  private def isIndented(line: String): Boolean =
    line.nonEmpty && line.charAt(0).isWhitespace

  private def splitKeyValue(line: String): (String, String) =
    val idx = line.indexOf(':')
    if idx < 0 then (line.strip(), "")
    else (line.substring(0, idx).strip(), line.substring(idx + 1).strip())

  private def stripQuotes(value: String): String =
    if value.length >= 2 &&
      ((value.startsWith("\"") && value.endsWith("\"")) ||
        (value.startsWith("'") && value.endsWith("'")))
    then value.substring(1, value.length - 1)
    else value
