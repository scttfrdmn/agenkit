"""Guard against the census and the registry drifting apart.

Every ``Agent`` subclass in ``agenkit/`` must be either registered in
``registry.AGENT_CASES`` (Layer B, behavioral conformance) or explicitly
``EXCLUDED`` with a reason -- there is no third, silent option. This is
``scripts/version.py``'s ``_EXPECTED_DECLARATIONS`` floor-on-registry-size
idiom, inverted into a ceiling: a class that is neither registered nor
excluded means someone added a 60th ``Agent`` subclass and forgot to
register it, and the #868 rationale applies here in reverse -- a
reassuringly small ``EXCLUDED`` count would be the tell that entries were
silently dropped rather than tracked.
"""

from __future__ import annotations

from .census import agent_subclasses
from .registry import _MAX_EXCLUDED, CENSUS_KEY_TO_CLASS, EXCLUDED, REGISTERED_CENSUS_KEYS


def test_every_census_class_is_registered_or_excluded():
    census = set(agent_subclasses())
    tracked = REGISTERED_CENSUS_KEYS | set(EXCLUDED)

    untracked = census - tracked
    assert not untracked, (
        f"Found {len(untracked)} Agent subclass(es) neither registered in "
        f"AGENT_CASES nor EXCLUDED with a reason: {sorted(untracked)}. "
        f"Add each to one or the other in tests/conformance/registry.py."
    )

    # The reverse direction: a registry entry for a class the census no
    # longer finds (renamed/deleted) is also a drift, not a pass.
    stale = tracked - census
    assert not stale, (
        f"registry.py tracks {sorted(stale)}, which the AST census no "
        f"longer finds -- the class was renamed or removed; update the "
        f"registry to match."
    )


def test_every_census_class_is_in_the_key_to_class_map():
    census = set(agent_subclasses())
    mapped = set(CENSUS_KEY_TO_CLASS)
    assert census == mapped, (
        f"census/CENSUS_KEY_TO_CLASS mismatch -- missing: "
        f"{sorted(census - mapped)}, extra: {sorted(mapped - census)}"
    )


def test_excluded_ceiling_matches_current_size():
    """_MAX_EXCLUDED can only be *lowered* -- Phase 5 tranches move entries
    out of EXCLUDED into AGENT_CASES and lower this ceiling in the same PR.
    An EXCLUDED that grew past the ceiling without the ceiling being raised
    deliberately means a new exclusion was added without that choice being
    reviewed as a ceiling change.
    """
    assert len(EXCLUDED) <= _MAX_EXCLUDED, (
        f"EXCLUDED grew to {len(EXCLUDED)} entries, past the declared "
        f"ceiling of {_MAX_EXCLUDED} -- if this addition is intentional, "
        f"raise _MAX_EXCLUDED in the same change so the ceiling reflects "
        f"a reviewed decision, not silent growth."
    )
