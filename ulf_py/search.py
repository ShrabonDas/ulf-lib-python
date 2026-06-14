"""ULF head-search utilities.  Port of repos/ulf-lib/search.lisp."""
from __future__ import annotations


# ---------------------------------------------------------------------------
# VP head search
# ---------------------------------------------------------------------------

def _marked_conjugated_vp_head(x) -> bool:
    """True if *x* is already tagged as a conjugated-VP head."""
    if isinstance(x, str):
        from .suffix import split_by_suffix
        _, suffix = split_by_suffix(x)
        return suffix is not None and suffix.lower() == 'conjugated-vp-head'
    if isinstance(x, tuple) and len(x) == 2:
        from .lexical import lex_tense_p
        return lex_tense_p(x[0]) and _marked_conjugated_vp_head(x[1])
    return False


def search_vp_head(vp, sub=None):
    """Search *vp* for the VP head (main verb or aspect/auxiliary).

    Returns ``(head, found: bool, new_vp)`` where *new_vp* replaces the head
    with *sub* if *sub* is not None.
    """
    from .lexical import (lex_tense_p, lex_verb_p, lex_aux_p,
                          lex_lenulf_ambiguous_aux_p, support_lenulf_ambiguities)
    from .phrasal import verb_p, tensed_verb_p, aux_p, tensed_aux_p, adv_a_p, phrasal_sent_op_p

    def _is_verbaux(x):
        return verb_p(x) or tensed_verb_p(x) or aux_p(x) or tensed_aux_p(x)

    def _is_lex_verbaux(x):
        return lex_verb_p(x) or lex_aux_p(x)

    def _pasv_lex_verb(x):
        return (isinstance(x, tuple) and len(x) == 2
                and isinstance(x[0], str) and x[0].lower() == 'pasv'
                and lex_verb_p(x[1]))

    def _simple_vp_head(x):
        """True if x is a bare or tensed lexical verbaux / passivized verb."""
        if _is_lex_verbaux(x) or _pasv_lex_verb(x):
            return True
        if (isinstance(x, tuple) and len(x) == 2
                and lex_tense_p(x[0])
                and (_is_lex_verbaux(x[1]) or _pasv_lex_verb(x[1]))):
            return True
        return False

    # Already marked.
    if _marked_conjugated_vp_head(vp):
        return vp, True, sub if sub is not None else vp

    # Simple lexical, tensed-lexical, or passivized verb — base case.
    if _simple_vp_head(vp):
        return vp, True, sub if sub is not None else vp

    if not isinstance(vp, tuple) or not vp:
        return None, False, vp

    head = vp[0]
    tail = vp[1:]

    # Starts with a verb or auxiliary → recurse into head.
    if _is_verbaux(head):
        h, found, new_head = search_vp_head(head, sub=sub)
        return h, found, (new_head,) + tail

    # Starts with adv-a or phrasal sent-op → recurse into tail.
    if adv_a_p(head) or phrasal_sent_op_p(head):
        h, found, new_tail_vp = search_vp_head(tail, sub=sub)
        return h, found, (head,) + (new_tail_vp if isinstance(new_tail_vp, tuple) else (new_tail_vp,))

    return None, False, vp


def find_vp_head(vp):
    """Return the head of VP *vp* (or None if not found)."""
    head, _, _ = search_vp_head(vp)
    return head


def replace_vp_head(vp, sub):
    """Return a new VP with the head replaced by *sub*."""
    _, _, new_vp = search_vp_head(vp, sub=sub)
    return new_vp


# ---------------------------------------------------------------------------
# NP head search
# ---------------------------------------------------------------------------

def search_np_head(np, sub=None):
    """Search *np* for the head noun.

    Returns ``(head, found: bool, new_np)``.
    """
    from .lexical import lex_noun_p, lex_name_p, lex_name_pred_p
    from .phrasal import noun_p, phrasal_sent_op_p

    def _plur_noun(x):
        return (isinstance(x, tuple) and len(x) == 2
                and isinstance(x[0], str) and x[0].lower() == 'plur'
                and (lex_noun_p(x[1]) or lex_name_pred_p(x[1])))

    # Simple lexical noun or name.
    if isinstance(np, str) and (lex_noun_p(np) or lex_name_p(np)):
        return np, True, sub if sub is not None else np

    if not isinstance(np, tuple) or not np:
        return None, False, np

    # (plur noun) or (plur name-pred)
    if _plur_noun(np):
        return np, True, sub if sub is not None else np

    # (plur (relational-noun ...))
    if (len(np) == 2 and isinstance(np[0], str) and np[0].lower() == 'plur'
            and isinstance(np[1], tuple)):
        inner = np[1]
        inner_head = inner[0] if inner else None
        plur_head = ('plur', inner_head) if inner_head else None
        if sub is not None:
            return plur_head, True, (sub, inner[1:])
        return plur_head, True, np

    # n+preds / n+post
    if (np[0] in ('n+preds', 'n+post')
            and len(np) >= 2 and noun_p(np[1])):
        macro, inner_np, post = np[0], np[1], np[2:]
        h, found, new_inner = search_np_head(inner_np, sub=sub)
        return h, found, (macro, new_inner) + post

    # Premodification: (modifier noun)
    if len(np) == 2 and noun_p(np[1]):
        mod, inner = np[0], np[1]
        h, found, new_inner = search_np_head(inner, sub=sub)
        return h, found, (mod, new_inner)

    # Phrasal sent-op: (not noun)
    if len(np) == 2 and phrasal_sent_op_p(np[0]) and noun_p(np[1]):
        h, found, new_inner = search_np_head(np[1], sub=sub)
        return h, found, (np[0], new_inner)

    # Noun with arguments: (noun args…)
    if noun_p(np[0]):
        h, found, new_inner = search_np_head(np[0], sub=sub)
        return h, found, (new_inner,) + np[1:]

    # most-n: (most-n NOUN PRED)
    if len(np) == 3 and isinstance(np[0], str) and np[0].lower() == 'most-n':
        h, found, new_inner = search_np_head(np[2], sub=sub)
        return h, found, (np[0], np[1], new_inner)

    return None, False, np


def find_np_head(np):
    """Return the head noun of *np*."""
    head, _, _ = search_np_head(np)
    return head


def replace_np_head(np, sub):
    """Return a new NP with the head replaced by *sub*."""
    _, _, new_np = search_np_head(np, sub=sub)
    return new_np


# ---------------------------------------------------------------------------
# AP head search
# ---------------------------------------------------------------------------

def search_ap_head(ap, sub=None):
    """Search *ap* for the head adjective.

    Returns ``(head, found: bool, new_ap)``.
    """
    from .lexical import lex_adjective_p
    from .phrasal import (mod_a_p, adj_p, noun_p, term_p, p_arg_p,
                          phrasal_sent_op_p)

    # Simple lexical adjective.
    if isinstance(ap, str) and lex_adjective_p(ap):
        return ap, True, sub if sub is not None else ap

    if not isinstance(ap, tuple) or not ap:
        return None, False, ap

    # Pre-modification: (mod* adj)  — zero or more mods then adj.
    # Detect: last element is adj and all preceding are mods/adj/noun.
    def _is_premod(x):
        return mod_a_p(x) or adj_p(x) or noun_p(x)

    if adj_p(ap[-1]) and all(_is_premod(m) for m in ap[:-1]):
        mods, inner = ap[:-1], ap[-1]
        h, found, new_inner = search_ap_head(inner, sub=sub)
        return h, found, mods + (new_inner,)

    # Post-modification / arguments: (adj mod-a|term|p-arg …)
    def _is_postmod(x):
        return mod_a_p(x) or term_p(x) or p_arg_p(x) or phrasal_sent_op_p(x)

    if adj_p(ap[0]) and all(_is_postmod(m) for m in ap[1:]):
        inner, modargs = ap[0], ap[1:]
        h, found, new_inner = search_ap_head(inner, sub=sub)
        return h, found, (new_inner,) + modargs

    # Starting with phrasal sent-op.
    if phrasal_sent_op_p(ap[0]):
        h, found, new_tail = search_ap_head(ap[1:], sub=sub)
        return h, found, (ap[0],) + (new_tail if isinstance(new_tail, tuple) else (new_tail,))

    # Starts with adjective.
    if adj_p(ap[0]):
        h, found, new_head = search_ap_head(ap[0], sub=sub)
        return h, found, (new_head,) + ap[1:]

    return None, False, ap


def find_ap_head(ap):
    """Return the head adjective of *ap*."""
    head, _, _ = search_ap_head(ap)
    return head


def replace_ap_head(ap, sub):
    """Return a new AP with the head replaced by *sub*."""
    _, _, new_ap = search_ap_head(ap, sub=sub)
    return new_ap
