"""
LLM invocation for reasoning techniques.

The five reasoning techniques that own an LLM (`ChainOfThought`, `TreeOfThought`,
`PlanAndSolve`, `LeastToMost`, `GraphOfThought`) all need the same thing: turn a
prompt string into response text.

The dispatch itself now lives in :mod:`agenkit._llm_protocol`, shared with the
patterns, because the techniques were not the only place that had invented its own
answer to "what does this LLM object respond to" — `ConversationalAgent` had a third
(#805) and `budget` a fourth. This module re-exports the prompt-shaped entry point
so the technique call sites stay unchanged.

See #802 for why the dispatch was consolidated in the first place, and #805 for why
it then had to move somewhere the patterns could import from.
"""

from agenkit._llm_protocol import complete_text

__all__ = ["complete_text"]
