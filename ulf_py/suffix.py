"""ULF type suffix utilities.  Port of repos/ulf-lib/suffix.lisp."""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Core split / strip / add
# ---------------------------------------------------------------------------

def has_suffix(s: str) -> bool:
    """Return True if *s* has a .-delimited suffix with no whitespace after the dot."""
    if not isinstance(s, str):
        return False
    dot = s.rfind('.')
    if dot <= 0:
        return False
    suffix_region = s[dot:]
    return not any(c in ' \t\n\r' for c in suffix_region)


def split_by_suffix(sym) -> tuple:
    """Split *sym* at the last '.' and return (word, suffix).

    Returns (sym, None) if there is no valid suffix (no dot, dot at position 0,
    or whitespace inside the suffix region).  Non-string atoms are returned
    unchanged as (sym, None).
    """
    if not isinstance(sym, str):
        return sym, None
    dot = sym.rfind('.')
    if dot <= 0:
        return sym, None
    suffix_region = sym[dot:]  # includes the '.'
    if any(c in ' \t\n\r' for c in suffix_region):
        return sym, None
    suffix = sym[dot + 1:]
    if not suffix:
        return sym, None
    return sym[:dot], suffix


def strip_suffix(s: str) -> str:
    """Strip the suffix (everything after the last '.') from *s*.

    Edge cases:
    * Numbers (parseable as int/float) → returned unchanged.
    * Whitespace inside the suffix region → returned unchanged.
    """
    if not isinstance(s, str):
        return s
    # Numbers stay intact.
    try:
        float(s)
        return s
    except ValueError:
        pass
    dot = s.rfind('.')
    if dot <= 0:
        return s
    suffix_region = s[dot:]
    if any(c in ' \t\n\r' for c in suffix_region):
        return s
    base = s[:dot]
    return base if base else s


def add_suffix(word: str, suffix: str | None) -> str:
    """Return *word* + '.' + *suffix*.  If *suffix* is None/empty, return *word*."""
    if not suffix:
        return word
    return f"{word}.{suffix}"


# ---------------------------------------------------------------------------
# Type-suffix association table
# ---------------------------------------------------------------------------

# Maps semantic type name → ULF suffix extension.
TYPE_SUFFIX_ALIST: dict[str, str] = {
    'noun':  'n',
    'adj':   'a',
    'adv-a': 'adv-a',
    'adv-e': 'adv-e',
    'adv-s': 'adv-s',
    'adv-f': 'adv-f',
    'mod-a': 'mod-a',
    'mod-n': 'mod-n',
    'pp':    'pp',
    'term':  'pro',
    'verb':  'v',
    'pred':  'pred',
    'det':   'd',
    'aux-v': 'aux-v',
    'aux-s': 'aux-s',
    'sent':  'sent',
    'funct': 'f',
}


def suffix_for_type(x: str) -> str:
    """Return the ULF suffix string for semantic type *x*.

    If *x* is not in the table, returns *x* itself (lowercased).
    """
    key = str(x).lower()
    return TYPE_SUFFIX_ALIST.get(key, key)
