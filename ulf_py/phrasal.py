"""ULF phrasal type patterns.
Port of repos/ulf-lib/ttt-phrasal-patterns.lisp and underspecified-patterns.lisp.

Trees are represented as Python tuples (leaves are str/int/float).
TTT operator hiding is applied before matching so that ULF punctuation
marks (! ?) and hole variables (*h *p …) are not confused with TTT operators.
"""
from __future__ import annotations

from .lexical import (
    lex_noun_p, lex_name_pred_p, lex_adjective_p,
    lex_adv_a_p, lex_adv_e_p, lex_adv_s_p, lex_adv_f_p,
    lex_mod_a_p, lex_mod_n_p, lex_pp_p, lex_p_p, lex_ps_p, lex_pq_p,
    lex_rel_p, lex_det_p, lex_pronoun_p, lex_name_p, lex_number_p,
    lex_verb_p, lex_aux_p, lex_aux_s_p, lex_aux_v_p, lex_lenulf_ambiguous_aux_p,
    lex_tense_p, lex_detformer_p, lex_coord_p, lex_p_arg_p,
    lex_sent_p, lex_x_p, lex_yn_p, lex_gr_p, lex_pasv_p,
    lex_possessive_s_p, lex_set_of_p, lex_equal_p, lex_function_p,
    lex_invertible_verb_p, support_lenulf_ambiguities,
    atom_semtype, lex_macro_p, lex_macro_hole_p,
)

# ---------------------------------------------------------------------------
# Helpers: hide TTT ops in ULF trees before matching
# ---------------------------------------------------------------------------

def _match(pattern, expr) -> bool:
    try:
        from ttt import match_expr, hide_ttt_ops
        return bool(match_expr(pattern, hide_ttt_ops(expr)))
    except ImportError:
        return False


def _hidden_maybe_sub_expr(pattern, expr) -> bool:
    """Match *pattern* against *expr*, also trying after substitution-macro expansion."""
    if _match(pattern, expr):
        return True
    try:
        from .macro import apply_substitution_macros
        expanded = apply_substitution_macros(expr)
        return _match(pattern, expanded)
    except (ImportError, Exception):
        return False


# ---------------------------------------------------------------------------
# TTT patterns for each phrasal category
# (Python tuple syntax; predicate names use underscore + '?' for ttt lookup)
# ---------------------------------------------------------------------------

TTT_NOUN = ('!',
    'lex_noun?',
    'lex_name_pred?',
    ('plur', 'noun?'),
    ('mod_n?', 'noun?'),
    ('noun?', 'mod_n?'),
    ('adj?', 'noun?'),
    ('noun?', 'noun?'),
    ('lex_name?', 'noun?'),
    ('term?', 'noun?'),
    ('lex_rel_noun?', 'term?'),
    ('noun?', 'p_arg?'),
    ('lex_function?', 'term?'),
    ('n+preds', 'noun?', ('+', 'pred?')),
    (('+', 'noun?'), 'lex_coord?', 'noun?'),
    ('phrasal_sent_op?', 'noun?'),
    ('n+post', 'noun?', ('+', ('!', 'pred?', 'term?', 'adv?', 'p_arg?', 'unknown?'))),
    ('=', 'term?'),
    # fall-back
    ('n+preds', '_+'),
)

TTT_ADJ = ('!',
    'lex_adjective?',
    ('adj?', 'adj?'),
    ('noun?', 'adj?'),
    ('mod_a?', 'adj?'),
    ('adj?', 'mod_a?'),
    ('poss-by', 'term?'),
    ('adj?', ('to', 'verb?')),
    ('lex_adjective?', 'term?'),
    ('adj?', 'p_arg?'),
    (('*', 'mod_a?'), 'adj?', ('*', 'mod_a?'), ('!', 'p_arg?', ('to', 'verb?')), ('*', 'mod_a?')),
    (('*', 'mod_a?'), 'lex_adjective?', ('*', 'mod_a?'), 'term?', ('*', 'mod_a?')),
    (('*', 'mod_a?'), 'adj?', ('+', 'mod_a?')),
    (('+', 'mod_a?'), 'adj?', ('*', 'mod_a?')),
    (('+', 'adj?'), 'lex_coord?', ('+', 'adj?')),
    ('phrasal_sent_op?', 'adj?'),
    ('=', 'term?'),
)

TTT_ADV_A = ('!',
    'lex_adv_a?',
    ('adv_a?', 'pred?'),
    'lex_pq?',
    (('+', 'adv_a?'), 'lex_coord?', ('+', 'adv_a?')),
)

TTT_ADV_E = ('!',
    'lex_adv_e?',
    ('adv_e?', 'pred?'),
    (('+', 'adv_e?'), 'lex_coord?', ('+', 'adv_e?')),
)

TTT_ADV_S = ('!',
    'lex_adv_s?',
    ('adv_s?', 'pred?'),
    (('+', 'adv_s?'), 'lex_coord?', ('+', 'adv_s?')),
    # (| _+ |)  — parenthetical  (pipe brackets hidden by hide_ttt_ops)
)

TTT_ADV_F = ('!',
    'lex_adv_f?',
    ('adv_f?', 'pred?'),
    (('+', 'adv_f?'), 'lex_coord?', ('+', 'adv_f?')),
)

TTT_MOD_A = ('!',
    'lex_mod_a?',
    ('mod-a', 'pred?'),
)

TTT_MOD_N = ('!',
    'lex_mod_n?',
    ('mod-n', 'pred?'),
    ('nnp', 'term?'),
)

TTT_PP = ('!',
    'lex_pp?',
    ('lex_p?', 'term?'),
    (('+', 'pp?'), 'lex_coord?', ('+', 'pp?')),
    ('phrasal_sent_op?', 'pp?'),
    ('mod_a?', 'pp?'),
    ('pp?', 'mod_a?'),
    ('lex_p?', '_+'),
)

TTT_P_ARG = ('!',
    ('lex_p_arg?', 'term?'),
    ('lex_p_arg?', 'pred?'),
    ('adv_s?', 'p_arg?'),
)

TTT_TERM = ('!',
    'lex_pronoun?',
    'lex_name?',
    'lex_number?',
    'lex_rel?',
    ('det?', 'noun?'),
    ('lex_set_of?', ('+', 'term?')),
    (('+', 'term?'), 'lex_coord?', ('+', 'term?')),
    ('noun_reifier?', 'noun?'),
    ('verb_reifier?', 'verb?'),
    ('sent_reifier?', 'sent?'),
    ('tensed_sent_reifier?', 'tensed_sent?'),
    ('ds', '_!', 'litstring?'),
    ('preposs_macro?', 'noun?'),
    ('np+preds', 'term?', ('+', 'pred?')),
    ('|"|', '_+', '|"|'),
    # fall-backs
    ('np+preds', '_+'),
    (('_!1', "'s"), '_!2'),
    ('noun_reifier?', '_+'),
    ('verb_reifier?', '_+'),
    ('sent_reifier?', '_+'),
    ('tensed_sent_reifier?', '_+'),
    ('lex_set_of?', '_+'),
    ('plur-term', 'term?'),
    # Hidden hole variables
    '[*h]',
    '[*s]',
    '[*p]',
    '[*qt]',
    '[*ref]',
)

TTT_VERB = ('!',
    'lex_verb?',
    ('pasv', 'lex_verb?'),
    (('*', 'adv_a?'), 'verb?', ('+', ('!', 'term?', 'pred?', 'adv_a?', 'p_arg?', 'phrasal_sent_op?'))),
    ('adv_a?', ('*', 'phrasal_sent_op?'), 'verb?'),
    ('aux?', ('*', 'phrasal_sent_op?'), 'verb?'),
    (('*', 'verb?'), 'lex_coord?', ('+', 'verb?')),
    ('phrasal_sent_op?', 'verb?'),
    # fall-back
    ('verb?', '_!'),
)

TTT_PRED = ('!',
    'verb?', 'noun?', 'adj?', 'tensed_verb?', 'pp?',
    ('lex_rel?', 'pred?'),
    ('sub', 'lex_rel?', 'tensed_sent?'),
    ('sub', ('^*', 'lex_rel?'), 'tensed_sent?'),
    'relativized_sent?',
    # fall-backs
    ('lex_rel?', '_!'),
    ('sub', 'lex_rel?', '_!'),
    ('sub', ('^*', 'lex_rel?'), '_!'),
    ('phrasal_sent_op?', 'pred?'),
)

TTT_AUX = ('!', 'lex_aux?', 'perf', 'prog')
TTT_LENULF_AUX_EXT = [
    ('prog', 'aux?'),
    ('perf', 'aux?'),
]

TTT_TENSED_AUX = ('lex_tense?', 'aux?')

TTT_TENSED_VERB = ('!',
    ('lex_tense?', 'verb?'),
    (('*', 'adv_a?'), 'tensed_verb?', ('+', ('!', 'term?', 'pred?', 'adv_a?', 'p_arg?', 'phrasal_sent_op?'))),
    ('tensed_aux?', ('*', 'phrasal_sent_op?'), 'verb?'),
    ('adv_a?', ('*', 'phrasal_sent_op?'), 'tensed_verb?'),
    (('*', 'tensed_verb?'), 'lex_coord?', ('+', 'tensed_verb?')),
    ('phrasal_sent_op?', 'tensed_verb?'),
)

TTT_DET = ('!',
    'lex_det?',
    ('lex_detformer?', 'adj?'),
    (('*', 'det?'), 'lex_coord?', ('+', 'det?')),
)

TTT_SENT = ('!',
    ('term?', 'verb?'),
    (('+', 'sent?'), 'lex_coord?', ('+', 'sent?')),
    ('sent_mod?', 'sent?'),
    ('sent?', 'sent_mod?'),
    ('adv_a?', 'term?', 'verb?'),
    ('sent?', 'sent_punct?'),
    ('term?', '=', 'term?'),
    ('term?', 'adj?'),
    ('term?', 'noun?'),
    'lex_sent?',
    (('?', 'sent_mod?'), 'sent?', ('+', ('!', 'sent?', 'sent_mod?'))),
    'lex_x?',
    ('sub', 'term?', 'sent?'),
)

TTT_TENSED_SENT = ('!',
    ('term?', 'tensed_verb?'),
    (('+', 'tensed_sent?'), 'lex_coord?', ('+', 'tensed_sent?')),
    ('lex_coord?', 'tensed_sent?', ('+', 'tensed_sent?')),
    ('sent_mod?', 'tensed_sent?'),
    ('tensed_sent?', 'sent_mod?'),
    ('tensed_verb?', 'adv_a?', 'term?'),
    ('tensed_sent?', 'sent_punct?'),
    ('ps?', 'tensed_sent?'),
    ('tensed_sent?', 'ps?'),
    (('lex_tense?', 'aux?'), 'term?', 'verb?'),
    (('lex_tense?', 'lex_invertible_verb?'), 'term?', 'term?'),
    ('pu', ('!',)),  # phrasal utterance
    ('tensed_sent?', ('+', 'tensed_sent?')),
    'lex_x?',
    'lex_yn?',
    'lex_gr?',
    ('gr', '_!'),
    'lex_sent?',
    ('sub', 'term?', 'tensed_sent?'),
)

TTT_SENT_MOD = ('!',
    ('lex_coord?', ('!', 'tensed_sent?', 'sent?')),
    'ps?',
    'adv_e?',
    'adv_s?',
    'adv_f?',
)

TTT_PS = ('!',
    ('lex_ps?', 'tensed_sent?'),
    ('mod_a?', 'ps?'),
)

TTT_PREPOSS_MACRO = ('term?', "'s")

TTT_VOC = ('!',
    ('voc', 'term?'),
    ('voc-o', 'term?'),
    ('voc', '_!'),
    ('voc-o', '_!'),
)


# ---------------------------------------------------------------------------
# Predicate functions — thin wrappers around _hidden_maybe_sub_expr
# ---------------------------------------------------------------------------

def noun_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_NOUN, x)

def adj_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_ADJ, x)

def adv_a_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_ADV_A, x)

def adv_e_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_ADV_E, x)

def adv_s_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_ADV_S, x)

def adv_f_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_ADV_F, x)

def adv_p(x) -> bool:
    return adv_a_p(x) or adv_e_p(x) or adv_s_p(x) or adv_f_p(x)

def mod_a_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_MOD_A, x)

def mod_n_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_MOD_N, x)

def pp_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_PP, x)

def p_arg_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_P_ARG, x)

def term_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_TERM, x)

def verb_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_VERB, x)

def pred_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_PRED, x)

def det_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_DET, x)

def aux_p(x) -> bool:
    pat = TTT_AUX
    if support_lenulf_ambiguities:
        pat = ('!', *TTT_AUX[1:], *TTT_LENULF_AUX_EXT)
    return _hidden_maybe_sub_expr(pat, x)

def tensed_aux_p(x) -> bool:
    return _match(TTT_TENSED_AUX, x)

def tensed_verb_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_TENSED_VERB, x)

def sent_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_SENT, x)

def tensed_sent_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_TENSED_SENT, x)

def sent_mod_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_SENT_MOD, x)

def ps_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_PS, x)

def preposs_macro_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_PREPOSS_MACRO, x)

def voc_p(x) -> bool:
    return _hidden_maybe_sub_expr(TTT_VOC, x)

# Punctuation / structural predicates.

SENT_PUNCT_ATOMS: frozenset[str] = frozenset({'!', '?', '.?', '[!]', '[?]', '[.?]'})

def sent_punct_p(x) -> bool:
    return isinstance(x, str) and x in SENT_PUNCT_ATOMS

# Reifiers.
def noun_reifier_p(x) -> bool:
    return isinstance(x, str) and x.lower() == 'k'

def tensed_sent_reifier_p(x) -> bool:
    return isinstance(x, str) and x.lower() in {'that', 'tht', 'whether', 'ans-to'}

def sent_reifier_p(x) -> bool:
    return isinstance(x, str) and x.lower() == 'ke'

def verb_reifier_p(x) -> bool:
    return isinstance(x, str) and x.lower() in {'ka', 'to', 'gd'}

# Type-shifter formers.
def advformer_p(x) -> bool:
    return isinstance(x, str) and x.lower() in {'adv-a', 'adv-e', 'adv-s', 'adv-f'}

def detformer_p(x) -> bool:
    return isinstance(x, str) and x.lower() in {'fquan', 'nquan'}

def modformer_p(x) -> bool:
    return isinstance(x, str) and x.lower() in {'mod-a', 'mod-n'}

def mod_n_former_p(x) -> bool:
    return isinstance(x, str) and x.lower() == 'mod-n'

def mod_a_former_p(x) -> bool:
    return isinstance(x, str) and x.lower() == 'mod-a'

def type_shifter_p(x) -> bool:
    return (
        noun_reifier_p(x) or verb_reifier_p(x)
        or sent_reifier_p(x) or tensed_sent_reifier_p(x)
        or mod_n_former_p(x) or mod_a_former_p(x)
        or advformer_p(x) or detformer_p(x)
    )


def contains_relativizer(x) -> bool:
    try:
        from ttt import match_expr, hide_ttt_ops
        return bool(match_expr(('^*', 'lex_rel?'), hide_ttt_ops(x)))
    except ImportError:
        return False

contains_relativizer_p = contains_relativizer


def relativized_sent_p(x) -> bool:
    return tensed_sent_p(x) and contains_relativizer(x)


def phrasal_sent_op_p(x) -> bool:
    """Sentence-level operators written within the phrase in the surface form."""
    return (
        adv_e_p(x)
        or adv_s_p(x)
        or adv_f_p(x)
        or (isinstance(x, str) and x.lower() in {'not', 'not.adv-e', 'not.adv-s'})
        or ps_p(x)
        or (isinstance(x, tuple) and len(x) > 1 and lex_ps_p(x[0]))
    )


def unknown_p(x) -> bool:
    return phrasal_ulf_type(x) == ['unknown']


# ---------------------------------------------------------------------------
# Gen-phrasal patterns (port of gen-phrasal-patterns.lisp)
# ---------------------------------------------------------------------------

_PLUR_PRONOUNS: frozenset[str] = frozenset({
    'they.pro', 'them.pro', 'we.pro', 'us.pro', 'you.pro',
    'these.pro', 'those.pro', 'both.pro', 'few.pro', 'many.pro',
    'several.pro', 'all.pro', 'any.pro', 'most.pro', 'none.pro',
    'some.pro', 'ours.pro', 'yours.pro', 'theirs.pro',
})

_PLUR_DETS: frozenset[str] = frozenset({
    'these.d', 'those.d', 'both.d', 'few.d', 'many.d', 'several.d',
})


def plur_lex_noun_p(x) -> bool:
    """True if x is (plur <lex-noun>) or (plur <lex-name-pred>)."""
    return (isinstance(x, tuple) and len(x) == 2
            and isinstance(x[0], str) and x[0].lower() == 'plur'
            and (lex_noun_p(x[1]) or lex_name_pred_p(x[1])))


def pasv_lex_verb_p(x) -> bool:
    """True if x is (pasv <lex-verb>)."""
    return (isinstance(x, tuple) and len(x) == 2
            and isinstance(x[0], str) and x[0].lower() == 'pasv'
            and lex_verb_p(x[1]))


def perf_lex_verb_p(x) -> bool:
    """True if x is (perf <lex-verb>)."""
    return (isinstance(x, tuple) and len(x) == 2
            and isinstance(x[0], str) and x[0].lower() == 'perf'
            and lex_verb_p(x[1]))


def prog_lex_verb_p(x) -> bool:
    """True if x is (prog <lex-verb>)."""
    return (isinstance(x, tuple) and len(x) == 2
            and isinstance(x[0], str) and x[0].lower() == 'prog'
            and lex_verb_p(x[1]))


def tensed_lex_verbaux_p(x) -> bool:
    """True if x is (<lex-tense> <lex-verb-or-aux>)."""
    return (isinstance(x, tuple) and len(x) == 2
            and lex_tense_p(x[0])
            and (lex_verb_p(x[1]) or lex_aux_p(x[1])))


def plur_noun_p(x) -> bool:
    """True if x is a plural noun phrase."""
    if isinstance(x, tuple) and len(x) == 2:
        if isinstance(x[0], str) and x[0].lower() == 'plur' and noun_p(x[1]):
            return True
    from .search import find_np_head
    return plur_lex_noun_p(find_np_head(x))


def plur_partitive_p(x) -> bool:
    """True if x is (<lex-p> <plur-term>)."""
    return (isinstance(x, tuple) and len(x) == 2
            and lex_p_p(x[0]) and plur_term_p(x[1]))


def plur_term_p(x) -> bool:
    """True if x is a plural term."""
    if isinstance(x, str):
        return x.lower() in _PLUR_PRONOUNS
    if not isinstance(x, tuple) or not x:
        return False
    # (plur-term <term>) — internal computational marker
    if (len(x) == 2 and isinstance(x[0], str) and x[0].lower() == 'plur-term'
            and term_p(x[1])):
        return True
    if not term_p(x):
        return False
    if len(x) == 2:
        first, second = x[0], x[1]
        if (det_p(first) or noun_reifier_p(first)) and (noun_p(second) or pp_p(second)):
            if isinstance(first, str) and first.lower() in _PLUR_DETS:
                return True
            return plur_noun_p(second) or plur_partitive_p(second)
    if len(x) > 2:
        return lex_set_of_p(x[0]) or lex_coord_p(x[1]) or lex_coord_p(x[-2])
    return False


# ---------------------------------------------------------------------------
# Type identification table
# ---------------------------------------------------------------------------

_TYPE_ID_FNS: list[tuple] = [
    (noun_p,              'noun'),
    (adj_p,               'adj'),
    (lex_p_p,             'prep'),
    (adv_a_p,             'adv-a'),
    (adv_e_p,             'adv-e'),
    (adv_s_p,             'adv-s'),
    (adv_f_p,             'adv-f'),
    (mod_a_p,             'mod-a'),
    (mod_n_p,             'mod-n'),
    (mod_a_former_p,      'mod-a-former'),
    (mod_n_former_p,      'mod-n-former'),
    (pp_p,                'pp'),
    (term_p,              'term'),
    (verb_p,              'verb'),
    (pred_p,              'pred'),
    (det_p,               'det'),
    (aux_p,               'aux'),
    (tensed_aux_p,        'tensed-aux'),
    (tensed_verb_p,       'tensed-verb'),
    (sent_p,              'sent'),
    (tensed_sent_p,       'tensed-sent'),
    (lex_tense_p,         'tense'),
    (sent_punct_p,        'sent-punct'),
    (sent_mod_p,          'sent-mod'),
    (noun_reifier_p,      'noun-reifier'),
    (verb_reifier_p,      'verb-reifier'),
    (sent_reifier_p,      'sent-reifier'),
    (tensed_sent_reifier_p, 'tensed-sent-reifier'),
    (advformer_p,         'advformer'),
    (detformer_p,         'detformer'),
    (preposs_macro_p,     'preposs-macro'),
    (relativized_sent_p,  'rel-sent'),
    (p_arg_p,             'p-arg'),
    (voc_p,               'voc'),
    # Purely lexical.
    (lex_equal_p,         'equal-sign'),
    (lex_set_of_p,        'set-of-op'),
    (lex_macro_p,         'macro-symbol'),
    (lex_ps_p,            'sent-prep'),
    (lex_coord_p,         'coordinator'),
    (lex_pasv_p,          'pasv'),
    (lex_possessive_s_p,  'possessive-s'),
]


def phrasal_ulf_type(x) -> list[str]:
    """Return a list of type labels that *x* satisfies, or ['unknown']."""
    matched = [label for fn, label in _TYPE_ID_FNS if fn(x)]
    return matched if matched else ['unknown']


def label_formula_types(f):
    """Recursively annotate *f* with its phrasal types.

    Atoms (leaves) are returned unchanged.  Compound nodes are returned as a
    list [{'types': [...]}, [labelled-children...]].
    """
    if not isinstance(f, tuple):
        return f
    children = [label_formula_types(child) for child in f]
    return [{'types': phrasal_ulf_type(f)}, children]


# ---------------------------------------------------------------------------
# Underspecified semtype patterns (port of underspecified-patterns.lisp)
# ---------------------------------------------------------------------------

def _construct_alternative_type_strings(type_strings: list[str]) -> str:
    if len(type_strings) == 1:
        return type_strings[0]
    if len(type_strings) == 2:
        return '{' + type_strings[0] + '|' + type_strings[1] + '}'
    return '{' + type_strings[0] + '|' + _construct_alternative_type_strings(type_strings[1:]) + '}'


def _build_underspecified_semtypes():
    from .semtype import str2semtype, semtype2str
    import re as _re

    _ATOM_SYMBOLS_RE = r'[\w\d\-\/:\.\*\[\]]+'
    _INNER_NAME_RE = r'[^\|]+'

    def _expand(p: str) -> str:
        return p.replace('{S}', _ATOM_SYMBOLS_RE).replace('{N}', _INNER_NAME_RE)

    raw = [
        (r'{S}\.AUX',  ['aux.aux-v', 'aux.aux-s']),
        (r'{S}\.ADV',  ['adv.adv-a', 'adv.adv-s', 'adv.adv-e', 'adv.adv-f']),
        (r'ADV',       ['adv-a', 'adv-s', 'adv-e', 'adv-f']),
        (r'{S}\.MOD',  ['mod.mod-a', 'mod.mod-n']),
        (r'MOD',       ['mod-a', 'mod-n']),
        (r'FIN',       ['pres', 'past', 'cf']),
    ]

    table: list[tuple[_re.Pattern, object]] = []
    for pat_str, examples in raw:
        expanded = _expand(pat_str)
        try:
            compiled = _re.compile(expanded, _re.IGNORECASE)
        except _re.error:
            continue
        # Build the type string from the atom semtypes of the example atoms.
        type_strings = []
        for ex in examples:
            st = atom_semtype(ex)
            if st is not None:
                s = semtype2str(st)
                if s:
                    type_strings.append(s)
        if not type_strings:
            continue
        combined = _construct_alternative_type_strings(type_strings)
        try:
            combined_st = str2semtype(combined)
        except Exception:
            continue
        table.append((compiled, combined_st))
    return table


_UNDERSPECIFIED_SEMTYPES: list | None = None


def get_underspecified_semtypes() -> list:
    global _UNDERSPECIFIED_SEMTYPES
    if _UNDERSPECIFIED_SEMTYPES is None:
        _UNDERSPECIFIED_SEMTYPES = _build_underspecified_semtypes()
    return _UNDERSPECIFIED_SEMTYPES


# ---------------------------------------------------------------------------
# Register phrasal predicates with ttt
# ---------------------------------------------------------------------------

def _register_phrasal_predicates() -> None:
    try:
        from ttt import store_pred
    except ImportError:
        return

    _preds = {
        'noun?':                 noun_p,
        'adj?':                  adj_p,
        'adv_a?':                adv_a_p,
        'adv_e?':                adv_e_p,
        'adv_s?':                adv_s_p,
        'adv_f?':                adv_f_p,
        'adv?':                  adv_p,
        'mod_a?':                mod_a_p,
        'mod_n?':                mod_n_p,
        'pp?':                   pp_p,
        'p_arg?':                p_arg_p,
        'term?':                 term_p,
        'verb?':                 verb_p,
        'pred?':                 pred_p,
        'det?':                  det_p,
        'aux?':                  aux_p,
        'tensed_aux?':           tensed_aux_p,
        'tensed_verb?':          tensed_verb_p,
        'sent?':                 sent_p,
        'tensed_sent?':          tensed_sent_p,
        'sent_mod?':             sent_mod_p,
        'ps?':                   ps_p,
        'preposs_macro?':        preposs_macro_p,
        'voc?':                  voc_p,
        'sent_punct?':           sent_punct_p,
        'noun_reifier?':         noun_reifier_p,
        'tensed_sent_reifier?':  tensed_sent_reifier_p,
        'sent_reifier?':         sent_reifier_p,
        'verb_reifier?':         verb_reifier_p,
        'advformer?':            advformer_p,
        'detformer?':            detformer_p,
        'modformer?':            modformer_p,
        'mod_n_former?':         mod_n_former_p,
        'mod_a_former?':         mod_a_former_p,
        'type_shifter?':         type_shifter_p,
        'relativized_sent?':     relativized_sent_p,
        'contains_relativizer?': contains_relativizer_p,
        'phrasal_sent_op?':      phrasal_sent_op_p,
        'unknown?':              unknown_p,
        'plur_lex_noun?':        plur_lex_noun_p,
        'pasv_lex_verb?':        pasv_lex_verb_p,
        'perf_lex_verb?':        perf_lex_verb_p,
        'prog_lex_verb?':        prog_lex_verb_p,
        'tensed_lex_verbaux?':   tensed_lex_verbaux_p,
        'plur_noun?':            plur_noun_p,
        'plur_partitive?':       plur_partitive_p,
        'plur_term?':            plur_term_p,
    }
    for name, fn in _preds.items():
        store_pred(name, fn)


_register_phrasal_predicates()
