"""ULF string preprocessing.  Port of repos/ulf-lib/preprocess.lisp."""
from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# String-level preprocessing
# ---------------------------------------------------------------------------

def unescape_backslashes(ulfstr: str) -> str:
    r"""Replace escaped backslashes (\\\\ → \\) as they arrive from SQL storage."""
    return ulfstr.replace('\\\\', '\\')


def add_prename_space(ulfstr: str) -> str:
    r"""Insert a space after the opening pipe in pipe-delimited names.

    |John| → | John|

    This allows names that consist entirely of capital letters to still be
    distinguished from symbols.
    """
    return re.sub(r'(\|)([^\|]+\|)', lambda m: m.group(1) + ' ' + m.group(2), ulfstr)


def make_string_paren_match(s: str) -> str:
    """Balance parentheses in *s* by prepending missing left parens.

    The algorithm reads S-expressions from left to right.  Each time a
    right-paren appears at the start of the remaining string we count it as
    an unmatched closer and prepend a ``(`` to the accumulated result.  When
    we reach a state where the remaining string is empty or whitespace we
    are done.

    This is a Python re-implementation of the Lisp helper which iteratively
    tries ``read-from-string`` and adds parens when it fails.  Because Python
    has no ``read-from-string``, we use a simple parenthesis-counter that
    ignores parens inside string literals (``"…"``) and pipe-delimited names
    (``|…|``).
    """
    def _count_parens(text: str):
        """Return (open_count, close_count, depth) scanning the whole text,
        respecting string and pipe escapes."""
        opens = closes = 0
        depth = 0
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == '"':
                # Skip to closing quote.
                i += 1
                while i < len(text) and text[i] != '"':
                    if text[i] == '\\':
                        i += 1
                    i += 1
                i += 1
                continue
            if ch == '|':
                i += 1
                while i < len(text) and text[i] != '|':
                    i += 1
                i += 1
                continue
            if ch == '(':
                opens += 1
                depth += 1
            elif ch == ')':
                closes += 1
                depth -= 1
            i += 1
        return opens, closes, depth

    opens, closes, _ = _count_parens(s)
    missing = closes - opens  # number of '(' we need to prepend
    if missing <= 0:
        return s
    return '(' * missing + s


def all_string_preprocess(s: str) -> str:
    """Apply the full preprocessing pipeline to a raw ULF string."""
    s = unescape_backslashes(s)
    s = add_prename_space(s)
    s = make_string_paren_match(s)
    return s


# ---------------------------------------------------------------------------
# S-expression reader
# ---------------------------------------------------------------------------

def _tokenize(s: str) -> list[str]:
    """Split *s* into a flat list of tokens."""
    tokens: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in ' \t\n\r':
            i += 1
        elif ch == '(':
            tokens.append('(')
            i += 1
        elif ch == ')':
            tokens.append(')')
            i += 1
        elif ch == '"':
            # Collect the whole string literal as one token.
            j = i + 1
            while j < n:
                if s[j] == '\\':
                    j += 2
                    continue
                if s[j] == '"':
                    j += 1
                    break
                j += 1
            tokens.append(s[i:j])
            i = j
        elif ch == '|':
            # Pipe-delimited name: collect to the closing pipe.
            j = i + 1
            while j < n and s[j] != '|':
                j += 1
            j += 1  # include closing '|'
            tokens.append(s[i:j])
            i = j
        elif ch == "'":
            # Quote shorthand  'X  → just emit the apostrophe as its own token
            # then let the next iteration handle X.
            tokens.append("'")
            i += 1
        else:
            j = i
            while j < n and s[j] not in ' \t\n\r()':
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens


def _atom(tok: str):
    """Convert a token string to an appropriate Python scalar."""
    # Try integer.
    try:
        return int(tok)
    except ValueError:
        pass
    # Try float.
    try:
        return float(tok)
    except ValueError:
        pass
    return tok


def _parse_tokens(tokens: list[str], pos: int):
    """Parse one S-expression starting at *pos*; return (value, next_pos)."""
    tok = tokens[pos]
    if tok == '(':
        items = []
        pos += 1
        while pos < len(tokens) and tokens[pos] != ')':
            item, pos = _parse_tokens(tokens, pos)
            items.append(item)
        pos += 1  # consume ')'
        return tuple(items), pos
    if tok == "'":
        # Quote: 'X → ('quote', X)
        inner, pos = _parse_tokens(tokens, pos + 1)
        return ('quote', inner), pos
    return _atom(tok), pos + 1


def ulf_from_string(s: str, multi_label=None):
    """Parse one or more S-expressions from *s* and return a ULF value.

    * Single expression → returned directly.
    * Multiple expressions → returned as a list, or wrapped in *multi_label*
      if that argument is provided.
    """
    tokens = _tokenize(s.strip())
    segments = []
    pos = 0
    while pos < len(tokens):
        try:
            obj, pos = _parse_tokens(tokens, pos)
            segments.append(obj)
        except (IndexError, Exception):
            break

    if not segments:
        return None
    if len(segments) == 1:
        return segments[0]
    if multi_label is None:
        return segments
    return tuple([multi_label] + segments)
