package io.agenkit.skills

import io.agenkit.core.{Agent, IntrospectionResult, Message}

import scala.concurrent.{ExecutionContext, Future}

/** Agent wrapper that automatically injects relevant skill instructions.
  *
  * Before delegating to the wrapped agent, this wrapper queries the registry
  * for skills relevant to the incoming message and prepends their instructions
  * inside an `<available_skills>` block. The augmented message's metadata
  * contains `active_skills` listing the injected skill names.
  *
  * @param agent
  *   base agent to delegate processing to
  * @param registry
  *   [[SkillRegistry]] used to look up relevant skills
  * @param maxActiveSkills
  *   maximum number of skills to inject (default 3)
  * @param autoDiscover
  *   whether to call `registry.discoverSkills()` at construction time
  *   (default true)
  */
class SkillEnabledAgent(
  agent: Agent,
  registry: SkillRegistry,
  maxActiveSkills: Int = 3,
  autoDiscover: Boolean = true
) extends Agent:
  if autoDiscover then registry.discoverSkills()

  def name: String = agent.name

  def capabilities: List[String] =
    val base = agent.capabilities
    if base.contains("skill_injection") then base else base :+ "skill_injection"

  def introspect(): IntrospectionResult = agent.introspect()

  /** Process a message, injecting relevant skill instructions first.
    *
    * Finds skills relevant to the message content, builds an
    * `<available_skills>` block, and prepends it to the message content before
    * passing it to the wrapped agent. The augmented message's metadata includes
    * `active_skills`.
    */
  def process(message: Message)(using ExecutionContext): Future[Message] =
    val query    = message.contentString
    val relevant = registry.findRelevantSkills(query, maxResults = maxActiveSkills)

    val enhanced =
      if relevant.nonEmpty then
        val skillBlocks       = relevant.map(_.toPrompt).mkString("\n\n")
        val prefix            = s"<available_skills>\n$skillBlocks\n</available_skills>\n\n"
        val augmentedContent  = prefix + query
        val newMetadata       = message.metadata + ("active_skills" -> relevant.map(_.name))
        message.copy(content = Some(augmentedContent), metadata = newMetadata)
      else message

    agent.process(enhanced)
