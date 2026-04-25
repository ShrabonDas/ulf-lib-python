"""Language utilities.  Port of repos/ulf-lib/lang-util.lisp."""
from __future__ import annotations

from .suffix import split_by_suffix


# ---------------------------------------------------------------------------
# Pronoun → dependent possessive determiner
# ---------------------------------------------------------------------------

# Maps any form of a pronoun (including reflexive / independent possessive)
# to the canonical base word used for lookup.
_PRONOUN_GROUPS: dict[str, str] = {}
for _base, _forms in [
    ('my.d',    ['i', 'me', 'mine']),
    ('our.d',   ['we', 'us', 'ourself', 'ourselves', 'ours']),
    ('your.d',  ['you', 'yourself', 'yourselves', 'yours', 'ye']),
    ('thy.d',   ['thou', 'thee', 'thyself', 'thine']),
    ('his.d',   ['he', 'him', 'himself', 'his']),
    ('her.d',   ['she', 'her', 'herself', 'hers']),
    ('its.d',   ['it', 'itself', 'its']),
    ('their.d', ['they', 'them', 'themselves', 'theirs']),
    ('whose.d', ['who', 'whom', 'whose']),
]:
    for _f in _forms:
        _PRONOUN_GROUPS[_f] = _base

# 'one' / 'oneself' → (one.pro 's)  — handled separately below.


def pronoun2possdet(pro: str):
    """Return the dependent possessive determiner for pronoun *pro*.

    *pro* may carry any ULF suffix; only the base word is used for lookup.
    Raises ``ValueError`` for unknown pronouns.

    Returns a string determinier symbol or the tuple ``('one.pro', "'S")``
    for the pronoun 'one'.
    """
    if not isinstance(pro, str):
        raise ValueError(f"Expected a string pronoun, got: {pro!r}")
    word, _ = split_by_suffix(pro)
    if not isinstance(word, str):
        word = str(pro)
    key = word.lower()
    if key in {'one', 'oneself'}:
        return ('one.pro', "'S")
    result = _PRONOUN_GROUPS.get(key)
    if result is None:
        raise ValueError(f"Unknown pronoun for possessive determiner: {pro!r}")
    return result


def term2possdet(term):
    """Return the dependent possessive determiner for ULF term *term*.

    For pronouns a specific determiner symbol is returned.  For all other
    terms the possessive-s construction ``(term 's)`` is used.
    """
    from .lexical import suffix_check
    if isinstance(term, str):
        word, suffix = split_by_suffix(term)
        if suffix is not None and suffix.upper() == 'PRO':
            return pronoun2possdet(term)
    return (term, "'S")
