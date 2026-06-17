package io.agenkit.skills

import org.scalatest.funsuite.AnyFunSuite
import org.scalatest.matchers.should.Matchers

import java.nio.file.{Files, Path}

class SkillLoaderSpec extends AnyFunSuite with Matchers:

  private def tempDir(): Path = Files.createTempDirectory("agenkit-skills-")

  private def makeSkillDir(
    parent: Path,
    name: String,
    description: String,
    body: String = "Instructions here."
  ): Path =
    val skillDir = Files.createDirectory(parent.resolve(name))
    val content  = s"---\nname: $name\ndescription: $description\n---\n$body"
    Files.writeString(skillDir.resolve("SKILL.md"), content)
    skillDir

  // -------------------------------------------------------------------------
  // AgentSkill.fromDirectory
  // -------------------------------------------------------------------------

  test("load valid skill"):
    val dir   = makeSkillDir(tempDir(), "pdf-processing", "Extract text from PDFs.", "# PDF\nDo stuff.")
    val skill = AgentSkill.fromDirectory(dir)

    skill.name shouldBe "pdf-processing"
    skill.description shouldBe "Extract text from PDFs."
    skill.instructions should include("Do stuff.")
    skill.skillDir shouldBe Some(dir)

  test("load skill with license and metadata"):
    val parent  = tempDir()
    val dir     = Files.createDirectory(parent.resolve("advanced"))
    val content =
      "---\n" +
        "name: advanced\n" +
        "description: Advanced skill.\n" +
        "license: Apache-2.0\n" +
        "metadata:\n" +
        "  version: '1.0'\n" +
        "---\n" +
        "Advanced instructions."
    Files.writeString(dir.resolve("SKILL.md"), content)
    val skill = AgentSkill.fromDirectory(dir)

    skill.license shouldBe Some("Apache-2.0")
    skill.metadata shouldBe Map("version" -> "1.0")

  test("missing SKILL.md throws"):
    val emptyDir = Files.createDirectory(tempDir().resolve("empty"))
    val ex       = intercept[IllegalArgumentException](AgentSkill.fromDirectory(emptyDir))
    ex.getMessage should include("No SKILL.md found")

  test("invalid frontmatter (missing delimiters) throws"):
    val dir = Files.createDirectory(tempDir().resolve("bad"))
    Files.writeString(dir.resolve("SKILL.md"), "name: foo\ndescription: bar\n")
    val ex = intercept[IllegalArgumentException](AgentSkill.fromDirectory(dir))
    ex.getMessage should include("missing frontmatter delimiters")

  test("missing name throws"):
    val dir = Files.createDirectory(tempDir().resolve("noname"))
    Files.writeString(dir.resolve("SKILL.md"), "---\ndescription: A skill without a name.\n---\nInstructions.")
    val ex = intercept[IllegalArgumentException](AgentSkill.fromDirectory(dir))
    ex.getMessage should include("Missing required field 'name'")

  test("missing description throws"):
    val dir = Files.createDirectory(tempDir().resolve("nodesc"))
    Files.writeString(dir.resolve("SKILL.md"), "---\nname: nodesc\n---\nInstructions.")
    val ex = intercept[IllegalArgumentException](AgentSkill.fromDirectory(dir))
    ex.getMessage should include("Missing required field 'description'")

  test("toPrompt renders name, description, instructions"):
    val dir    = makeSkillDir(tempDir(), "csv-tools", "Handle CSV files.", "Parse and write CSV.")
    val skill  = AgentSkill.fromDirectory(dir)
    val prompt = skill.toPrompt

    prompt should include("# Skill: csv-tools")
    prompt should include("## Description")
    prompt should include("Handle CSV files.")
    prompt should include("## Instructions")
    prompt should include("Parse and write CSV.")

  // -------------------------------------------------------------------------
  // SkillRegistry
  // -------------------------------------------------------------------------

  test("discover skips non-directories at search path level"):
    val parent = tempDir()
    Files.writeString(parent.resolve("not_a_dir.md"), "ignored")
    val registry = SkillRegistry(List(parent))
    registry.discoverSkills()
    registry.skills shouldBe empty

  test("discover loads valid skills"):
    val parent = tempDir()
    makeSkillDir(parent, "skill-a", "Skill A description.")
    makeSkillDir(parent, "skill-b", "Skill B description.")
    val registry = SkillRegistry(List(parent))
    registry.discoverSkills()

    registry.skills.keySet should contain("skill-a")
    registry.skills.keySet should contain("skill-b")

  test("discover skips invalid skill directories with a warning"):
    val parent = tempDir()
    makeSkillDir(parent, "good", "A good skill.")
    val badDir = Files.createDirectory(parent.resolve("broken"))
    // Has a SKILL.md but it is missing the name field.
    Files.writeString(badDir.resolve("SKILL.md"), "---\ndescription: no name here.\n---\nbody")
    val registry = SkillRegistry(List(parent))
    registry.discoverSkills()

    registry.skills.keySet should contain("good")
    registry.skills.keySet should not contain "broken"

  test("findRelevantSkills name match ranks first"):
    val parent = tempDir()
    makeSkillDir(parent, "pdf-processing", "Work with PDF documents.")
    makeSkillDir(parent, "csv-tools", "Handle CSV spreadsheets.")
    val registry = SkillRegistry(List(parent))
    registry.discoverSkills()

    val results = registry.findRelevantSkills("pdf")
    results.size should be >= 1
    results.head.name shouldBe "pdf-processing"

  test("findRelevantSkills respects maxResults"):
    val parent = tempDir()
    for i <- 0 until 6 do
      makeSkillDir(parent, s"skill-$i", s"A skill about document processing number $i.")
    val registry = SkillRegistry(List(parent))
    registry.discoverSkills()

    val results = registry.findRelevantSkills("document", maxResults = 3)
    results.size should be <= 3

  test("getSkill returns Some for known and None for unknown"):
    val parent = tempDir()
    makeSkillDir(parent, "email-compose", "Compose professional emails.")
    val registry = SkillRegistry(List(parent))
    registry.discoverSkills()

    registry.getSkill("email-compose").map(_.name) shouldBe Some("email-compose")
    registry.getSkill("nonexistent") shouldBe None
