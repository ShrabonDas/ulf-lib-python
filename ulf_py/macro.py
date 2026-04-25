"""ULF macro expansion.  Port of repos/ulf-lib/macro.lisp."""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Hole-variable helpers
# ---------------------------------------------------------------------------

def contains_hole(ulf, holevar: str = '*h') -> bool:
    """Return True if *holevar* appears anywhere in *ulf* (recursive)."""
    if not isinstance(ulf, tuple):
        return ulf == holevar
    return any(contains_hole(item, holevar) for item in ulf)


def _subst(replacement, var: str, tree):
    """Substitute *replacement* for every occurrence of *var* in *tree*."""
    if not isinstance(tree, (tuple, list)):
        return replacement if tree == var else tree
    return type(tree)(_subst(replacement, var, item) for item in tree)


# ---------------------------------------------------------------------------
# Generic variable-insertion macro engine
# ---------------------------------------------------------------------------

def _var_insertion_macro(macro_name: str, var_sym: str,
                         context_selector_fn, insertion_selector_fn,
                         bad_use_fn):
    """Return a closure that applies a variable-insertion macro.

    Parameters mirror the Lisp ``var-insertion-macro`` function.

    Returns ``fn(ulf, fail_on_bad_use) -> (success: bool, result)``
    """
    def _rec(ulf, fail_on_bad_use):
        if not isinstance(ulf, tuple):
            return True, ulf
        # Node whose head matches the macro name.
        if ulf and ulf[0] == macro_name:
            if fail_on_bad_use and bad_use_fn(ulf):
                return False, ulf
            # Recurse into every element.
            recres = [_rec(item, fail_on_bad_use) for item in ulf]
            sucs = [r[0] for r in recres]
            ress = [r[1] for r in recres]
            if not all(sucs):
                return False, ress
            if fail_on_bad_use and not any(contains_hole(r, var_sym) for r in ress):
                return False, ress
            insertion = insertion_selector_fn(ress)
            context = context_selector_fn(ress)
            return True, _subst(insertion, var_sym, context)
        # Otherwise recurse into all children.
        recres = [_rec(item, fail_on_bad_use) for item in ulf]
        sucs = [r[0] for r in recres]
        ress = [r[1] for r in recres]
        if all(sucs):
            return True, type(ulf)(ress)
        fail_pos = sucs.index(False)
        return False, ress[fail_pos]

    def macro_fn(ulf, fail_on_bad_use: bool = False):
        return _rec(ulf, fail_on_bad_use)

    return macro_fn


# ---------------------------------------------------------------------------
# Sub macro  (sub INSERTION CONTEXT) → substitute *h in CONTEXT with INSERTION
# ---------------------------------------------------------------------------

def _bad_sub_use(x) -> bool:
    return not (isinstance(x, tuple) and len(x) == 3 and x[0] == 'sub')


_sub_fn = _var_insertion_macro(
    'sub', '*h',
    context_selector_fn=lambda ress: ress[2],   # third element
    insertion_selector_fn=lambda ress: ress[1], # second element
    bad_use_fn=_bad_sub_use,
)


def apply_sub_macro(ulf, fail_on_bad_use: bool = False):
    """Apply all *sub* macros in *ulf*.

    Returns (success, result).
    """
    return _sub_fn(ulf, fail_on_bad_use)


# ---------------------------------------------------------------------------
# Rep macro  (rep CONTEXT INSERTION) → substitute *p in CONTEXT with INSERTION
# ---------------------------------------------------------------------------

def _bad_rep_use(x) -> bool:
    return not (isinstance(x, tuple) and len(x) == 3 and x[0] == 'rep')


_rep_fn = _var_insertion_macro(
    'rep', '*p',
    context_selector_fn=lambda ress: ress[1],   # second element
    insertion_selector_fn=lambda ress: ress[2], # third element
    bad_use_fn=_bad_rep_use,
)


def apply_rep_macro(ulf, fail_on_bad_use: bool = False):
    """Apply all *rep* macros in *ulf*.

    Returns (success, result).
    """
    return _rep_fn(ulf, fail_on_bad_use)


# ---------------------------------------------------------------------------
# qt-attr macro
# ---------------------------------------------------------------------------

def apply_qt_attr_macro(ulf):
    """Expand qt-attr macros in *ulf*.

    Returns (success, result).  On failure the original *ulf* is returned.
    """
    def _rec(node):
        """Returns (success, result, qt_attr_payload)."""
        if not isinstance(node, tuple):
            return True, node, None

        # Quoted expression: (|"| ... |"|)
        if (len(node) >= 3
                and node[0] == '|"|'
                and node[-1] == '|"|'):
            inner = node[1] if len(node) == 3 else node[1:-1]
            suc, res, qt_attr = _rec(inner)
            if qt_attr is not None:
                return True, _subst(('|"|', res, '|"|'), '*qt', qt_attr), None
            return suc, ('|"|', res, '|"|'), qt_attr

        # qt-attr node: (qt-attr EXPR_WITH_*qt)
        if (len(node) == 2
                and node[0] == 'qt-attr'
                and contains_hole(node[1], '*qt')):
            suc, res = _rec(node[1])[:2]
            return suc, None, res

        # General case: recurse into all children, filter None results.
        recres = [_rec(item) for item in node]
        sucs = [r[0] for r in recres]
        ress = [r[1] for r in recres if r[1] is not None]
        qt_attrs = [r[2] for r in recres if r[2] is not None]
        return (
            all(sucs),
            type(node)(ress),
            qt_attrs[0] if qt_attrs else None,
        )

    suc, result, qt_attr = _rec(ulf)
    if not suc or qt_attr is not None:
        return False, ulf
    return True, result


# ---------------------------------------------------------------------------
# add_info_to_sub_vars — enrich *h variables with type information
# ---------------------------------------------------------------------------

def _add_info_to_var(curulf, var: str, srculf):
    """Replace *var* in *curulf* with a typed version derived from *srculf*."""
    from .phrasal import phrasal_ulf_type, noun_p, term_p
    from .suffix import add_suffix, suffix_for_type

    typ_list = phrasal_ulf_type(srculf)
    typ = typ_list[0] if typ_list else 'unknown'
    typed_var = add_suffix(var, suffix_for_type(typ)) if typ != 'unknown' else var

    # Wrap in plur when needed.
    def _plur_noun(x) -> bool:
        return isinstance(x, tuple) and len(x) == 2 and x[0] == 'plur' and noun_p(x[1])

    def _plur_term(x) -> bool:
        return isinstance(x, tuple) and len(x) == 2 and x[0] == 'plur-term'

    if _plur_noun(srculf):
        replacement = ('plur', typed_var)
    elif _plur_term(srculf):
        replacement = ('plur-term', typed_var)
    else:
        replacement = typed_var

    return _subst(replacement, var, curulf)


def add_info_to_sub_vars(ulf):
    """Add type information to *h hole variables inside *sub* macros."""
    def _rec(node):
        if not isinstance(node, tuple):
            return node
        if node and node[0] == 'sub':
            if len(node) < 3:
                return (_rec(node[1]),) if len(node) == 2 else node
            left = _rec(node[1])
            right = _rec(node[2])
            return ('sub', left, _add_info_to_var(right, '*h', left))
        return type(node)(_rec(item) for item in node)

    return _rec(ulf)


# ---------------------------------------------------------------------------
# add_info_to_relativizers
# ---------------------------------------------------------------------------

def _add_info_to_relativizer(curulf, srculf):
    """Add pluralisation info to the relativizer in *curulf* based on *srculf*."""
    from .phrasal import noun_p, term_p
    from .lexical import lex_rel_p

    def _find_rel(node):
        if isinstance(node, str) and lex_rel_p(node):
            return node
        if isinstance(node, tuple):
            for item in node:
                found = _find_rel(item)
                if found is not None:
                    return found
        return None

    origrel = _find_rel(curulf)
    if origrel is None:
        return curulf

    def _plur_term(x):
        return isinstance(x, tuple) and len(x) == 2 and x[0] == 'plur-term'

    def _plur_noun(x):
        return isinstance(x, tuple) and len(x) == 2 and x[0] == 'plur' and noun_p(x[1])

    if _plur_term(srculf) or _plur_noun(srculf):
        replacement = ('plur-term', origrel)
    else:
        replacement = origrel

    return _subst(replacement, origrel, curulf)


def add_info_to_relativizers(ulf):
    """Add info to relativizers in n+preds, n+post, np+preds constructions."""
    def _rec(node):
        if not isinstance(node, tuple):
            return node
        if (node and isinstance(node[0], str)
                and node[0].lower() in {'n+preds', 'n+post', 'np+preds'}
                and len(node) > 2):
            recvals = type(node)(_rec(item) for item in node)
            macro = recvals[0]
            head = recvals[1]
            postmods = recvals[2:]
            return (macro, head) + tuple(
                _add_info_to_relativizer(pm, head) for pm in postmods
            )
        return type(node)(_rec(item) for item in node)

    return _rec(ulf)


# ---------------------------------------------------------------------------
# uninvert_verbaux! — transform inverted V/AUX constructions
# ---------------------------------------------------------------------------

def _uninvert_verbaux(ulf: tuple):
    """Return (NP, (((tense verb) VP) ADV1 … ADVn)) from an inverted sentence."""
    if len(ulf) < 3:
        return None
    headva = ulf[0]
    np = ulf[1]
    vp = ulf[2]
    remain = ulf[3:]
    from functools import reduce
    inner = reduce(lambda acc, adv: (acc, adv), remain, (headva, vp))
    return (np, inner)


# TTT rules for uninverting verb/aux.
_TTT_UNINVERT_VERBAUX = (
    ('/',
     (('!', 'lex_tense?', 'lex_aux?'), 'term?', '_+'),
     ('uninvert_verbaux!', (('!', 'lex_tense?', 'lex_aux?'), 'term?', '_+'))),
    ('/',
     ((('!', 'lex_tense?', 'lex_verb?'), 'term?', '_+'), '[?]'),
     (('uninvert_verbaux!', (('!', 'lex_tense?', 'lex_verb?'), 'term?', '_+')), '[?]')),
)


def uninvert_verbauxes(ulf):
    """Apply verb/auxiliary uninversion rules to *ulf*."""
    try:
        from ttt import apply_rules, hide_ttt_ops, unhide_ttt_ops, register_template_fn
        # Register the template function so TTT can call it.
        register_template_fn('uninvert_verbaux!', lambda args: _uninvert_verbaux(args))
        hidden = hide_ttt_ops(ulf)
        result = apply_rules(_TTT_UNINVERT_VERBAUX, hidden, max_n=500)
        return unhide_ttt_ops(result)
    except (ImportError, Exception):
        return ulf


# ---------------------------------------------------------------------------
# lift_adv_a — lift adv-a that are mixed in with verb arguments
# ---------------------------------------------------------------------------

_TTT_LIFT_ADV_A = (
    ('/', (('!', 'verb?', 'tensed_verb?'), '_+1', 'adv_a?', '_*2'),
          ('adv_a?', ('!', '_+1', '_*2'))),
    ('/', (('!', 'verb?', 'tensed_verb?'), '_*1', 'adv_a?', '_+2'),
          ('adv_a?', ('!', '_*1', '_+2'))),
)


def lift_adv_a(ulf):
    """Lift adv-a expressions mixed in with verb arguments."""
    try:
        from ttt import apply_rules, hide_ttt_ops, unhide_ttt_ops
        hidden = hide_ttt_ops(ulf)
        result = apply_rules(_TTT_LIFT_ADV_A, hidden)
        return unhide_ttt_ops(result)
    except (ImportError, Exception):
        return ulf


# ---------------------------------------------------------------------------
# apply_substitution_macros — apply sub, rep, and qt-attr in sequence
# ---------------------------------------------------------------------------

def apply_substitution_macros(ulf):
    """Apply all substitution macros (sub, rep, qt-attr) to *ulf*.

    Returns the transformed ULF expression.
    """
    _, after_sub = apply_sub_macro(ulf)
    _, after_rep = apply_rep_macro(after_sub)
    _, after_qt = apply_qt_attr_macro(after_rep)
    return after_qt
