"""ULF lexical predicates and semtype table.  Port of repos/ulf-lib/ttt-lexical-patterns.lisp."""
from __future__ import annotations

import re
import sys

from .suffix import split_by_suffix, has_suffix

# ---------------------------------------------------------------------------
# Module-level flags
# ---------------------------------------------------------------------------

# Set to True to accept lenulf underspecified/ambiguous suffixes (aux, adv, fin, mod).
support_lenulf_ambiguities: bool = False

# ---------------------------------------------------------------------------
# Tense, coordinator, detformer constants
# ---------------------------------------------------------------------------

TENSE_WORDS: frozenset[str] = frozenset({'past', 'pres', 'cf'})
COORDINATOR_WORDS: frozenset[str] = frozenset({'and', 'or', 'but', 'because'})
DETFORMER_WORDS: frozenset[str] = frozenset({'nquan', 'fquan'})

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Character class for valid ULF atom content (used in suffix regex).
_ATOM_BODY = r'[\w\d\-\/:\.\*\[\]]+'

# Cache compiled patterns to avoid re.compile overhead on every call.
_suffix_re_cache: dict[str, re.Pattern] = {}
_name_suffix_re_cache: dict[str, re.Pattern] = {}


def suffix_check(x: str, suffix: str) -> bool:
    """Return True if *x* is a regular ULF atom (or hidden/elided variant) with *suffix*."""
    pat = _suffix_re_cache.get(suffix)
    if pat is None:
        raw = r'^\[?\|? ?\{?' + _ATOM_BODY + r'\}\.' + re.escape(suffix) + r'\|?\]?$'
        # Also allow without the closing } (most atoms have no {}).
        raw_plain = r'^\[?\|? ?' + _ATOM_BODY + r'\.' + re.escape(suffix) + r'\|?\]?$'
        pat = re.compile(r'(?:' + raw + r'|' + raw_plain + r')', re.IGNORECASE)
        _suffix_re_cache[suffix] = pat
    return bool(pat.match(str(x)))


def name_suffix_check(x: str, suffix: str) -> bool:
    """Return True if *x* is a pipe-delimited name atom with *suffix*.

    Handles both ``|Name.suffix|`` and ``|Name|.suffix`` formats.
    """
    pat = _name_suffix_re_cache.get(suffix)
    if pat is None:
        esc = re.escape(suffix)
        # |Name.suffix| — suffix inside pipes
        inside = r'^\[?\|[^\|]+\.' + esc + r'\|\]?$'
        # |Name|.suffix — suffix outside pipes
        outside = r'^\[?\|[^\|]+\|\.' + esc + r'\]?$'
        pat = re.compile(r'(?:' + inside + r'|' + outside + r')', re.IGNORECASE)
        _name_suffix_re_cache[suffix] = pat
    return bool(pat.match(str(x)))


# ---------------------------------------------------------------------------
# Name / elision / hole-variable helpers
# ---------------------------------------------------------------------------

def is_strict_name(x) -> bool:
    """Return True if *x* is a pipe-delimited proper name like |John|."""
    if not isinstance(x, str):
        return False
    return (
        len(x) > 1
        and x[0] == '|'
        and x[-1] == '|'
        and x not in ("|'S|", '|"|')
    )


def lex_elided_p(x) -> bool:
    """Return True if *x* is an elided token like {he} or {he}.pro."""
    if not isinstance(x, str):
        return False
    word, _ = split_by_suffix(x)
    if not isinstance(word, str) or not word:
        return False
    return (word.startswith('{') and word.endswith('}')) or (
        x.startswith('{') and x.endswith('}')
    )


def lex_hole_variable_p(x) -> bool:
    """Return True if *x* is a hole variable: *h, *p, *s, *ref, *qt (possibly hidden/suffixed)."""
    if not isinstance(x, str):
        return False
    from ttt.util import unhide_ttt_ops
    token = unhide_ttt_ops(x)
    if not isinstance(token, str):
        return False
    word, _ = split_by_suffix(token)
    if not isinstance(word, str):
        return False
    word = unhide_ttt_ops(word)
    return isinstance(word, str) and word.startswith('*')


SURFACE_TOKEN_WORDS: frozenset[str] = frozenset(
    {'that', 'not', 'and', 'or', 'to', 'most', 'some', 'all', 'every', 'whether', 'if'}
)


def surface_token_p(x) -> bool:
    """Return True if *x* corresponds to a token present in the surface string."""
    if not isinstance(x, str):
        return True  # numbers are always surface tokens
    return (
        (has_suffix(x) and not lex_elided_p(x) and not lex_hole_variable_p(x))
        or is_strict_name(x)
        or x.lower() in SURFACE_TOKEN_WORDS
    )


# ---------------------------------------------------------------------------
# Lexical category predicates
# ---------------------------------------------------------------------------

def lex_noun_p(x) -> bool:
    return suffix_check(x, 'N')

def lex_rel_noun_p(x) -> bool:
    """Relational noun: lex-noun with '-of' ending (e.g. brother-of.n)."""
    if not isinstance(x, str) or not lex_noun_p(x):
        return False
    word, _ = split_by_suffix(x)
    return isinstance(word, str) and word.upper().endswith('-OF')

def lex_function_p(x) -> bool:
    return suffix_check(x, 'F')

def lex_pronoun_p(x) -> bool:
    return suffix_check(x, 'PRO')

def lex_verb_p(x) -> bool:
    return suffix_check(x, 'V')

def lex_adjective_p(x) -> bool:
    return suffix_check(x, 'A')

def lex_p_p(x) -> bool:
    return suffix_check(x, 'P')

def lex_p_arg_p(x) -> bool:
    pat = re.compile(r'^[\w\-]+\.p-arg$', re.IGNORECASE)
    return bool(pat.match(str(x)))

def lex_ps_p(x) -> bool:
    return suffix_check(x, 'PS')

def lex_pq_p(x) -> bool:
    return suffix_check(x, 'PQ')

def lex_prep_p(x) -> bool:
    return lex_p_p(x) or lex_ps_p(x) or lex_pq_p(x)

def lex_pp_p(x) -> bool:
    return suffix_check(x, 'PP')

def lex_mod_a_p(x) -> bool:
    return suffix_check(x, 'MOD-A')

def lex_mod_n_p(x) -> bool:
    return suffix_check(x, 'MOD-N') or (isinstance(x, str) and x.lower() == 'plur')

def lex_rel_p(x) -> bool:
    return suffix_check(x, 'REL')

def lex_det_p(x) -> bool:
    return suffix_check(x, 'D')

def lex_coord_p(x) -> bool:
    if not isinstance(x, str):
        return False
    return x.lower() in COORDINATOR_WORDS or suffix_check(x, 'CC')

def lex_aux_s_p(x) -> bool:
    result = suffix_check(x, 'AUX-S')
    if not result and support_lenulf_ambiguities:
        result = lex_lenulf_ambiguous_aux_p(x)
    return result

def lex_aux_v_p(x) -> bool:
    result = suffix_check(x, 'AUX-V')
    if not result and support_lenulf_ambiguities:
        result = lex_lenulf_ambiguous_aux_p(x)
    return result

def lex_lenulf_ambiguous_aux_p(x) -> bool:
    return suffix_check(x, 'AUX')

def lex_aux_p(x) -> bool:
    return (
        lex_aux_s_p(x)
        or lex_aux_v_p(x)
        or (support_lenulf_ambiguities and lex_lenulf_ambiguous_aux_p(x))
    )

def lex_number_p(x) -> bool:
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, str):
        try:
            float(x)
            return True
        except ValueError:
            pass
    return False

# Named-predicate variants (pipe-delimited names with a given suffix).
def lex_name_noun_p(x) -> bool:
    return name_suffix_check(x, 'N')

def lex_name_det_p(x) -> bool:
    return name_suffix_check(x, 'D')

def lex_name_adj_p(x) -> bool:
    return name_suffix_check(x, 'A')

def lex_name_prep_p(x) -> bool:
    return name_suffix_check(x, 'P')

def lex_name_pred_p(x) -> bool:
    return (
        lex_name_noun_p(x)
        or lex_name_det_p(x)
        or lex_name_adj_p(x)
        or lex_name_prep_p(x)
    )

def lex_name_p(x) -> bool:
    return is_strict_name(x)

# Adverbs.
def lex_adv_a_p(x) -> bool:
    result = suffix_check(x, 'ADV-A')
    if not result and support_lenulf_ambiguities:
        result = lex_lenulf_ambiguous_adv_p(x)
    return result

def lex_adv_s_p(x) -> bool:
    result = (
        suffix_check(x, 'ADV-S')
        or (isinstance(x, str) and x.lower() == 'not')
    )
    if not result and support_lenulf_ambiguities:
        result = lex_lenulf_ambiguous_adv_p(x)
    return result

def lex_adv_e_p(x) -> bool:
    result = suffix_check(x, 'ADV-E')
    if not result and support_lenulf_ambiguities:
        result = lex_lenulf_ambiguous_adv_p(x)
    return result

def lex_adv_f_p(x) -> bool:
    result = suffix_check(x, 'ADV-F')
    if not result and support_lenulf_ambiguities:
        result = lex_lenulf_ambiguous_adv_p(x)
    return result

def lex_lenulf_ambiguous_adv_p(x) -> bool:
    return suffix_check(x, 'ADV')

def lex_adv_formula_p(x) -> bool:
    return lex_adv_s_p(x) or lex_adv_e_p(x) or lex_adv_f_p(x)

def lex_adv_p(x) -> bool:
    return (
        lex_adv_a_p(x)
        or lex_adv_s_p(x)
        or lex_adv_e_p(x)
        or lex_adv_f_p(x)
        or (support_lenulf_ambiguities and lex_lenulf_ambiguous_adv_p(x))
    )

# Miscellaneous lexical categories.
def lex_x_p(x) -> bool:
    """Expletives."""
    return suffix_check(x, 'X')

def lex_yn_p(x) -> bool:
    """Yes/no evaluations."""
    return suffix_check(x, 'YN')

def lex_gr_p(x) -> bool:
    """Greetings."""
    return suffix_check(x, 'GR')

def lex_sent_p(x) -> bool:
    """Implicit sentence markers."""
    return suffix_check(x, 'SENT')

def lex_tense_p(x) -> bool:
    if not isinstance(x, str):
        return False
    tenses = TENSE_WORDS
    if support_lenulf_ambiguities:
        tenses = tenses | {'fin'}
    return x.lower() in tenses

def lex_detformer_p(x) -> bool:
    return isinstance(x, str) and x.lower() in DETFORMER_WORDS

def litstring_p(x) -> bool:
    """Literal string leaf."""
    return isinstance(x, str)

def lex_equal_p(x) -> bool:
    return isinstance(x, str) and x == '='

def lex_set_of_p(x) -> bool:
    return isinstance(x, str) and x.lower() == 'set-of'

def lex_macro_p(x) -> bool:
    MACROS = {'qt-attr', 'sub', 'rep', 'n+preds', 'np+preds', 'voc', 'voc-o'}
    return isinstance(x, str) and x.lower() in MACROS

def lex_macro_hole_p(x) -> bool:
    HOLES = {'*h', '*p', '*qt', '*s', '*ref'}
    return isinstance(x, str) and x.lower() in HOLES

def lex_verbaux_p(x) -> bool:
    """Verb or auxiliary (lexical)."""
    # Circular: aux_p depends on phrasal.py.  Resolved via late import.
    from .phrasal import aux_p
    return lex_verb_p(x) or aux_p(x)

def lex_pasv_p(x) -> bool:
    return isinstance(x, str) and x.lower() == 'pasv'

def lex_possessive_s_p(x) -> bool:
    return isinstance(x, str) and x in ("|'S|", "'s", "'S")

def lex_invertible_verb_p(x) -> bool:
    return isinstance(x, str) and x.lower() in {'make.v', 'have.v'}


# ---------------------------------------------------------------------------
# Semtype table (atom_semtype)
# ---------------------------------------------------------------------------
# Regex patterns use {S} as a placeholder for the "atom symbols" pattern and
# {N} for inner-name symbols.
_ATOM_SYMBOLS_RE = r'[\w\d\-\/:\.\*\[\]]+'
_INNER_NAME_RE   = r'[^\|]+'


def _build_semtypes():
    """Build the *semtypes* list lazily to avoid circular imports at module load."""
    from .semtype import str2semtype, semtype2str, binarize_flat_options, new_optional_semtype, copy_semtype, OptionalType, AtomicType, SemType
    from .syntactic_features import SyntacticFeatures, DEFAULT_SYNTACTIC_FEATURES

    def _expand(pattern: str) -> str:
        p = pattern.replace('{S}', _ATOM_SYMBOLS_RE)
        p = p.replace('{N}', _INNER_NAME_RE)
        return p

    raw: list[tuple[str, str | list]] = [
        (r'{S}\.PRO',  'D'),
        (r'\|{N}\|',   'D'),
        (r'[\d\.]+',   'D'),
        (r'{S}\.P',    '(D=>(D=>(S=>2)))_p%lex'),
        (r'{S}\.PS',   '((S=>2)_v>>((S=>2)_v>>(S=>2))_p)%lex'),
        (r'{S}\.N',    '(D=>(S=>2))_n%lex,!pl'),
        (r'{S}-OF\.N', '(D=>(D=>(S=>2)))_n%lex,!pl'),
        (r'{S}\.A',    '{(D=>(S=>2))_a%lex|(D=>(D=>(S=>2)))_a%lex}'),
        (r'BE\.V',     '({(D=>(S=>2))_A|(D=>(S=>2))_P}=>(D=>(S=>2)))_v%lex,!t,!pf,!pg,!pv,!x'),
        (r'{S}\.V',    '({D|(D=>(S=>2))%!t,!pf,!pg,!pv,!x}^n=>(D=>(S=>2)))_v%lex,!t,!pf,!pg,!pv,!x'),
        (r'{S}\.D',    '({(D=>(S=>2))_n|(D=>(S=>2))_p}=>D)%lex'),
        (r'{S}\.ADV-A','((D=>(S=>2))_v>>(D=>(S=>2))_v)%lex'),
        (r'{S}\.(ADV-E|ADV-S|ADV-F)', '((S=>2)_v>>(S=>2))%lex'),
        (r'PLUR',      '((D=>(S=>2))_n%!pl>>(D=>(S=>2))_n%pl)'),
        (r'K',         '((D=>(S=>2))_n=>D)'),
        (r'TO|KA',     '((D=>(S=>2))_v%!t,!x=>D)'),
        (r'KE',        '((S=>2)_v%!t=>D)'),
        (r'THAT|THT',  '((S=>2)_v%t=>D)%lex'),
        (r'WHETHER',   '((S=>2)_v%t=>D)%lex'),
        (r'ANS-TO',    '((S=>2)_v%t=>D)%lex'),
        (r'ADV-A',     '((D=>(S=>2))=>((D=>(S=>2))_v>>(D=>(S=>2))_v))'),
        (r'ADV-E|ADV-S|ADV-F', '((D=>(S=>2))=>((S=>2)>>(S=>2)))'),
        (r'FQUAN|NQUAN','((D=>(S=>2))_a=>((D=>(S=>2))_n=>D))'),
        (r'SET-OF',    '(D^n=>(D=>(D=>D)))'),
        (r'NOT',       '((S=>2)_v>>(S=>2))%lex'),
        (r'=',         '{(D=>(D=>(S=>2)))_a|(D=>(D=>(S=>2)))_p}'),
        (r'{S}\.CC',   '((S=>2)_v^n>>((S=>2)_v=>((S=>2)_v=>(S=>2))))%lex'),
        (r'{S}\.MOD-A','{((D=>(S=>2))_a>>(D=>(S=>2))_a)|{((D=>(S=>2))_p>>(D=>(S=>2))_p)|(((S=>2)_v>>(S=>2))_p=>((S=>2)_v>>(S=>2))_p)}}'),
        (r'{S}\.MOD-N','((D=>(S=>2))_n>>(D=>(S=>2))_n)'),
        (r'MOD-A',     '((D=>(S=>2))=>{((D=>(S=>2))_a>>(D=>(S=>2))_a)|{((D=>(S=>2))_p>>(D=>(S=>2))_p)|(((S=>2)_v>>(S=>2))_p=>((S=>2)_v>>(S=>2))_p)}})'),
        (r'MOD-N',     '((D=>(S=>2))=>((D=>(S=>2))_n>>(D=>(S=>2))_n))'),
        (r'{S}\.P-ARG','PARG'),
        (r'\!|\?',     '((S=>2)_v>>(S=>2))%lex'),
        (r'VOC|VOC-O', '(D=>((S=>2)_v>>(S=>2)))'),
        (r'PASV',      '(({D|(D=>(S=>2))%!t,!pf,!pg,!pv,!x}^n=>(D=>(S=>2)))_V%!pv,!t,lex%>pv,lex)'),
        # Auxiliaries and aspectual operators
        (r'PROG',      '((D=>(S=>2))_v%!t,!pg,!pf,!x>>(D=>(S=>2))_v%!t,pg)'),
        (r'PERF',      '((D=>(S=>2))_v%!t,!pf,!x>>(D=>(S=>2))_v%!t,pf)'),
        (r'{S}\.AUX-S|{S}\.AUX-V', '((D=>(S=>2))_v%!t,!x>>(D=>(S=>2))_v%!t,x)'),
    ]

    # Build the tense type as an optional covering verbs and aux/aspectual operators.
    # Mirrors Lisp: {(VERB%!T%>T) | (AUX=>TAUX) | (AUX=>INVERTED_AUX) | ...}
    _aux_strs = [
        '((D=>(S=>2))_v%!t,!pg,!pf,!x>>(D=>(S=>2))_v%!t,pg)',   # PROG
        '((D=>(S=>2))_v%!t,!pf,!x>>(D=>(S=>2))_v%!t,pf)',        # PERF
        '((D=>(S=>2))_v%!t,!x>>(D=>(S=>2))_v%!t,x)',             # AUX-S/AUX-V
    ]
    try:
        _verb_tense_st = str2semtype(
            '(({D|(D=>(S=>2))%!t,!pf,!pg,!pv,!x}^n=>(D=>(S=>2)))_V%!T,LEX%>T)',
            extended=True,
        )
        tense_options = [_verb_tense_st]
        for _as in _aux_strs:
            _aux = str2semtype(_as, extended=True)
            # AUX => TAUX  (tensed aux: same shape but T in range synfeats)
            _taux = copy_semtype(_aux)
            if _taux.range is not None:
                _taux.range.synfeats = SyntacticFeatures(
                    feature_map={**(_taux.range.synfeats.feature_map if _taux.range.synfeats else {}),
                                 'TENSE': 't'})
            tense_options.append(SemType(connective='=>', domain=_aux, range=_taux))
            # AUX => INVERTED  (inverted aux: D => (DOM >> (S=>2)_v%T,X))
            _dom = copy_semtype(_aux.domain)
            _inv_inner = SemType(connective='>>', domain=_dom,
                                 range=str2semtype('(S=>2)_v%T,X', extended=True))
            _inv = SemType(connective='=>', domain=copy_semtype(_aux),
                           range=SemType(connective='=>', domain=str2semtype('D'),
                                         range=_inv_inner))
            tense_options.append(_inv)
        # Build right-leaning binary optional from the list.
        tense_st = new_optional_semtype(tense_options)
    except Exception:
        tense_st = None

    table: list[tuple[re.Pattern, object]] = []
    for pat_str, semtype_str in raw:
        expanded = _expand(pat_str)
        try:
            compiled = re.compile(expanded, re.IGNORECASE)
        except re.error:
            continue
        if isinstance(semtype_str, list):
            st = [str2semtype(s, extended=True) for s in semtype_str]
        else:
            try:
                st = str2semtype(semtype_str, extended=True)
            except Exception:
                st = None
        table.append((compiled, st))

    # Add tense entry.
    try:
        tense_re = re.compile(r'^(PRES|PAST|CF)$', re.IGNORECASE)
        table.append((tense_re, tense_st))
    except Exception:
        pass

    return table


_SEMTYPES: list | None = None


def _get_semtypes() -> list:
    global _SEMTYPES
    if _SEMTYPES is None:
        _SEMTYPES = _build_semtypes()
    return _SEMTYPES


def atom_semtype(expr) -> object:
    """Return the semtype for a lexical ULF atom, or None if not found.

    For named predicates, a representative placeholder is used since the regex
    patterns can't match arbitrary pipe-delimited names directly.
    """
    if not isinstance(expr, str):
        return None

    # Redirect named predicates to a canonical representative.
    lookup = expr
    if lex_name_prep_p(expr):
        lookup = 'prep.p'
    elif lex_name_adj_p(expr):
        lookup = 'adj.a'
    elif lex_name_det_p(expr):
        lookup = 'det.d'
    elif lex_name_noun_p(expr):
        lookup = 'noun.n'

    for pat, st in _get_semtypes():
        m = pat.fullmatch(lookup)
        if m:
            return st
    return None


# ---------------------------------------------------------------------------
# Register predicates with ttt so patterns can reference them by name.
# ---------------------------------------------------------------------------

def _register_predicates() -> None:
    try:
        from ttt import store_pred
    except ImportError:
        return  # ttt not on path — skip registration

    _preds = {
        'lex_noun?':         lex_noun_p,
        'lex_rel_noun?':     lex_rel_noun_p,
        'lex_function?':     lex_function_p,
        'lex_pronoun?':      lex_pronoun_p,
        'lex_verb?':         lex_verb_p,
        'lex_adjective?':    lex_adjective_p,
        'lex_p?':            lex_p_p,
        'lex_p_arg?':        lex_p_arg_p,
        'lex_ps?':           lex_ps_p,
        'lex_pq?':           lex_pq_p,
        'lex_prep?':         lex_prep_p,
        'lex_pp?':           lex_pp_p,
        'lex_mod_a?':        lex_mod_a_p,
        'lex_mod_n?':        lex_mod_n_p,
        'lex_rel?':          lex_rel_p,
        'lex_det?':          lex_det_p,
        'lex_coord?':        lex_coord_p,
        'lex_aux_s?':        lex_aux_s_p,
        'lex_aux_v?':        lex_aux_v_p,
        'lex_aux?':          lex_aux_p,
        'lex_number?':       lex_number_p,
        'lex_name_noun?':    lex_name_noun_p,
        'lex_name_det?':     lex_name_det_p,
        'lex_name_adj?':     lex_name_adj_p,
        'lex_name_prep?':    lex_name_prep_p,
        'lex_name_pred?':    lex_name_pred_p,
        'lex_name?':         lex_name_p,
        'lex_adv_a?':        lex_adv_a_p,
        'lex_adv_s?':        lex_adv_s_p,
        'lex_adv_e?':        lex_adv_e_p,
        'lex_adv_f?':        lex_adv_f_p,
        'lex_adv?':          lex_adv_p,
        'lex_adv_formula?':  lex_adv_formula_p,
        'lex_x?':            lex_x_p,
        'lex_yn?':           lex_yn_p,
        'lex_gr?':           lex_gr_p,
        'lex_sent?':         lex_sent_p,
        'lex_tense?':        lex_tense_p,
        'lex_detformer?':    lex_detformer_p,
        'litstring?':        litstring_p,
        'lex_equal?':        lex_equal_p,
        'lex_set_of?':       lex_set_of_p,
        'lex_macro?':        lex_macro_p,
        'lex_macro_hole?':   lex_macro_hole_p,
        'lex_pasv?':         lex_pasv_p,
        'lex_possessive_s?': lex_possessive_s_p,
        'lex_invertible_verb?': lex_invertible_verb_p,
        'is_strict_name?':   is_strict_name,
        'lex_elided?':       lex_elided_p,
        'lex_hole_variable?': lex_hole_variable_p,
        'surface_token?':    surface_token_p,
    }
    for name, fn in _preds.items():
        store_pred(name, fn)


_register_predicates()
