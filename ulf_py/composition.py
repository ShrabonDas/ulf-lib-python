from __future__ import annotations
from dataclasses import dataclass
from functools import cache

from .semtype import (
    AtomicType, SemType, OptionalType,
    copy_semtype, semtype_match, unroll_exponent_step,
    str2semtype,
)
from .syntactic_features import DEFAULT_SYNTACTIC_FEATURES


@dataclass(frozen=True)
class CompositionResult:
    semtype: SemType | None
    direction: str              # "left", "right", or "none"
    operands: list


VALID_NON_ATOMIC_TYPE_SUFFIXES = "NAVP"


def _first_pos_suffix(suffix: str | None) -> str | None:
    """Return the first recognized part-of-speech suffix character."""
    if suffix is None:
        return None
    for char in suffix.upper():
        if char in VALID_NON_ATOMIC_TYPE_SUFFIXES:
            return char
    return None


def merge_suffixes(opr: SemType, arg: SemType) -> str | None:
    """Compute the suffix for the result of running operator `opr` on `arg`.

    The range suffix of `opr` is preferred. If that is unspecified, use the
    argument suffix, or the domain suffix if the argument suffix is unspecified,
    for the `>>` connective. Use the whole operator suffix for the `=>`
    connective.
    """
    range_suffix = _first_pos_suffix(opr.range.suffix if opr.range is not None else None)
    domain_suffix = _first_pos_suffix(opr.domain.suffix if opr.domain is not None else None)
    arg_suffix = _first_pos_suffix(arg.suffix)
    opr_suffix = _first_pos_suffix(opr.suffix)

    if range_suffix is not None:
        return range_suffix
    if opr.connective == ">>":
        return arg_suffix or domain_suffix
    if opr.connective == "=>":
        return opr_suffix
    raise ValueError(f"Unknown connective {opr.connective!r} for suffix merge")


def _add_semtype_type_params(
    semtype: SemType | None,
    type_params: list[SemType],
) -> SemType | None:
    """Append type parameters recursively."""
    if semtype is None:
        return None
    if isinstance(semtype, OptionalType):
        for child in semtype.types:
            _add_semtype_type_params(child, type_params)
        return semtype
    semtype.type_params.extend(copy_semtype(tp) for tp in type_params)
    return semtype


def compose_synfeats(opr: SemType, arg: SemType):
    """Compose the synfeats of the operator and argument semtypes.

    Returns the new synfeats value.
    """
    from .syntactic_features import DEFAULT_SYNTACTIC_FEATURES, SyntacticFeatures

    # 1. Get the base synfeats based on the operator connective.
    # 2. Let the syntactic-features logic update individual features.
    if opr.connective == "=>":
        base_synfeats = opr.synfeats.copy()
    elif opr.connective == ">>":
        base_synfeats = arg.synfeats.copy()
    else:
        raise ValueError(f"Unknown connective {opr.connective!r} for syntactic feature merge")
        
    csq_feats = (
        opr.range.synfeats.copy()
        if opr.range is not None and opr.range.synfeats is not None
        else DEFAULT_SYNTACTIC_FEATURES.copy()
    )
    
    opr_feats = opr.synfeats if opr.synfeats is not None else DEFAULT_SYNTACTIC_FEATURES.copy()
    arg_feats = arg.synfeats if arg.synfeats is not None else DEFAULT_SYNTACTIC_FEATURES.copy()
    
    return SyntacticFeatures.combine_features(
        base_synfeats,
        opr_feats,
        arg_feats,
        csq_feats,
        opr,
        arg,
    )


def _collect_optional_results(results: list) -> SemType | None:
    """Collapse a list of per-option composition results into one semtype."""
    present = [r for r in results if r is not None]
    if not present:
        return None
    if len(present) == 1:
        return present[0]
    return OptionalType(types=present)


def apply_operator(
    raw_opr: SemType | None,
    raw_arg: SemType | None,
    *,
    recurse_fn=None,
    ignore_synfeats: bool = False,
) -> SemType | None:
    """Compose a given operator and argument semtype if possible.

    Both operator and argument are first normalized with `unroll_exponent_step`,
    so exponent structure may affect composition. Suffixes are propagated from `opr`.
    Synfeats are propagated from `opr` if `=>` and from `arg` if `>>`, with per-feature
    exceptions. Type parameters are propagated from both.
    """
    if raw_opr is None or raw_arg is None:
        return None

    # recurse_fn cannot default to apply_operator in the signature because Python
    # evaluates defaults before the function is bound.
    if recurse_fn is None:
        recurse_fn = lambda opr, arg: apply_operator(opr, arg, recurse_fn=recurse_fn, ignore_synfeats=ignore_synfeats)

    # We can now assume all domain and top-level exponents are 1.
    opr = unroll_exponent_step(raw_opr)
    arg = unroll_exponent_step(raw_arg)

    result: SemType | None = None

    if isinstance(opr, OptionalType):
        result = _collect_optional_results([recurse_fn(opt, arg) for opt in opr.types])
    elif isinstance(arg, OptionalType):
        result = _collect_optional_results([recurse_fn(opr, opt) for opt in arg.types])
    elif isinstance(opr, AtomicType):
        # Operator is a non-optional atomic type of the form A^n with n > 1.
        if semtype_match(opr, arg) and opr.ex > 1:
            result = copy_semtype(opr, c_ex=opr.ex - 1)
    elif (
        semtype_match(opr.domain, arg)
        and opr.domain.ex == 1
    ):
        # Operator is a non-atomic type with domain exponent n = 1.
        result = copy_semtype(opr.range)
        if result is not None:
            # Only add a suffix when the result is not atomic. This is retained
            # for sentences so we can recognize whether the sentence is
            # grammatical, for example whether the top predicate is a verb.
            if not isinstance(result, AtomicType):
                result.suffix = merge_suffixes(opr, arg)
            # Update syntactic features.
            if not ignore_synfeats:
                result.synfeats = compose_synfeats(opr, arg)

    # Update type params before returning, if not optional. All type params are
    # assumed to live in non-optional types.
    if not isinstance(opr, OptionalType) and result is not None:
        _add_semtype_type_params(
            result,
            list(raw_opr.type_params) + list(raw_arg.type_params),
        )
        
    return result


def compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    ignore_synfeats: bool = True,
    opr_apply_fn_name: str = "APPLY-OPERATOR",
) -> CompositionResult:
    """Compose two types if possible and return the composed type."""
    if opr_semtype is None or arg_semtype is None:
        return CompositionResult(None, "none", [])

    if opr_apply_fn_name == "APPLY-OPERATOR":
        composed = apply_operator(
            opr_semtype,
            arg_semtype,
            ignore_synfeats=ignore_synfeats,
        )
        if composed is not None:
            return CompositionResult(composed, "right", [opr_semtype, arg_semtype])

        composed = apply_operator(
            arg_semtype,
            opr_semtype,
            ignore_synfeats=ignore_synfeats,
        )

        if composed is not None:
            return CompositionResult(composed, "left", [arg_semtype, opr_semtype])

    return CompositionResult(None, "none", [])


# ---------------------------------------------------------------------------
# Reference semtypes (lazily initialized to avoid import-time cost)
# ---------------------------------------------------------------------------

@cache
def _unary_noun_semtype() -> SemType:
    return str2semtype("(D=>(S=>2))_N")

@cache
def _unary_pred_semtype() -> SemType:
    return str2semtype("(D=>(S=>2))")

@cache
def _term_semtype() -> SemType:
    return str2semtype("D")

@cache
def _general_verb_semtype() -> SemType:
    return str2semtype("({D|(D=>(S=>2))}^n=>(D=>(S=>2)))_V")

@cache
def _sent_mod_semtype() -> SemType:
    return str2semtype("{((S=>2)=>(S=>2))|((S=>2)>>(S=>2))}")


# ---------------------------------------------------------------------------
# Helpers for extended composition
# ---------------------------------------------------------------------------

_BLOCKED_ARG_NAMES = frozenset({
    'N+PREDS', 'NP+PREDS', '+PREDS', 'QT-ATTR', 'QT-ATTR1',
    'SUB', 'SUB1', 'REP', 'REP1', 'PARG',
})


def _get_all_top_domains(types: list) -> list:
    """Recursively extract top-level domain representations from a list of semtypes.

    For atomic types the atom itself is returned (name is its identity).
    For optional types, recurse into each branch.
    For function types, return the domain.
    """
    out = []
    for tp in types:
        if tp is None:
            continue
        if isinstance(tp, OptionalType):
            out.extend(_get_all_top_domains(tp.types))
        elif isinstance(tp, AtomicType):
            out.append(tp)
        elif tp.domain is not None:
            out.append(tp.domain)
    return out


def _delexicalize(st: SemType) -> SemType:
    """Return a copy of *st* with the LEXICAL synfeat set to !lex."""
    result = copy_semtype(st)
    sf = result.synfeats
    if sf is None:
        sf = DEFAULT_SYNTACTIC_FEATURES.copy()
    else:
        sf = sf.copy()
    sf.feature_map['LEXICAL'] = '!lex'
    result.synfeats = sf
    return result


# ---------------------------------------------------------------------------
# extended_apply_operator — ULF-macro-aware composition
# ---------------------------------------------------------------------------

def extended_apply_operator(
    raw_opr: SemType | None,
    raw_arg: SemType | None,
    *,
    recurse_fn=None,
    ignore_synfeats: bool = False,
) -> SemType | None:
    """Compose operator and argument with ULF-macro extensions.

    Handles N+PREDS, NP+PREDS, QT-ATTR, SUB, REP, hole variables, POSTGEN ('s),
    and PARG on top of the base apply_operator logic.
    """
    if raw_opr is None or raw_arg is None:
        return None

    if recurse_fn is None:
        recurse_fn = lambda o, a: extended_apply_operator(
            o, a, recurse_fn=recurse_fn, ignore_synfeats=ignore_synfeats
        )

    # Lisp's extended-apply-operator! does NOT unroll exponents at the top —
    # only the base apply-operator! (fall-through) does. This matters for the
    # hole rule, where exponent>1 on opr.domain must survive into *H's type-param.
    opr = raw_opr
    arg = raw_arg

    # Guard: macro-transition types cannot appear as direct arguments.
    if isinstance(arg, AtomicType) and arg.name.upper() in _BLOCKED_ARG_NAMES:
        return None

    opr_name = opr.name.upper() if isinstance(opr, AtomicType) else None
    arg_name = arg.name.upper() if isinstance(arg, AtomicType) else None

    # -- N+PREDS: n+preds + N_n >> {+PREDS[N+[N_n]]|N_n} --
    if opr_name == 'N+PREDS':
        if semtype_match(_unary_noun_semtype(), arg, ignore_exp=True):
            n_plus = AtomicType(name='N+', type_params=[copy_semtype(arg)])
            plus_preds = AtomicType(name='+PREDS', type_params=[n_plus])
            return OptionalType(types=[plus_preds, copy_semtype(arg)])
        return None

    # -- NP+PREDS: np+preds + D >> {+PREDS[NP+[D]]|D} --
    if opr_name == 'NP+PREDS':
        if semtype_match(_term_semtype(), arg, ignore_exp=True):
            np_plus = AtomicType(name='NP+', type_params=[copy_semtype(arg)])
            plus_preds = AtomicType(name='+PREDS', type_params=[np_plus])
            return OptionalType(types=[plus_preds, copy_semtype(arg)])
        return None

    # -- +PREDS: +preds[n+[T]] + pred >> {updated-+preds | updated-inner} --
    if opr_name == '+PREDS':
        if not semtype_match(_unary_pred_semtype(), arg, ignore_exp=True):
            return None
        n_plus = [p for p in opr.type_params
                  if isinstance(p, AtomicType) and p.name.upper() == 'N+']
        np_plus = [p for p in opr.type_params
                   if isinstance(p, AtomicType) and p.name.upper() == 'NP+']
        other = [p for p in opr.type_params
                 if not (isinstance(p, AtomicType) and p.name.upper() in ('N+', 'NP+'))]
        new_params = n_plus[1:] + np_plus[1:] + other + list(arg.type_params)
        first_carrier = (n_plus or np_plus)
        if not first_carrier or not first_carrier[0].type_params:
            return None
        inner = first_carrier[0].type_params[0]
        updated_inner = copy_semtype(inner)
        updated_inner.type_params = list(updated_inner.type_params) + [copy_semtype(p) for p in new_params]
        updated_preds = copy_semtype(opr)
        updated_preds.type_params = list(updated_preds.type_params) + [copy_semtype(p) for p in new_params]
        return OptionalType(types=[updated_preds, updated_inner])

    # -- QT-ATTR: qt-attr + T[*qt] >> qt-attr1[T] --
    if opr_name == 'QT-ATTR':
        # Collect type params from arg itself and from individual options if optional.
        all_tp = list(arg.type_params)
        if isinstance(arg, OptionalType):
            for opt in arg.types:
                if opt is not None:
                    all_tp.extend(opt.type_params)
        top_doms = _get_all_top_domains(all_tp)
        if any(isinstance(d, AtomicType) and d.name.upper() == '*QT' for d in top_doms):
            return AtomicType(name='QT-ATTR1', type_params=[copy_semtype(arg)])
        return None

    # -- QT-ATTR1: qt-attr1[T1] + T2 >> T2[qt-attr1[T1]] --
    if opr_name == 'QT-ATTR1':
        result = copy_semtype(arg)
        result.type_params = list(result.type_params) + [copy_semtype(opr)]
        return result

    # -- " + T2[qt-attr1[T1]] >> qt-attr2[T1.type_params] --
    if opr_name == '"':
        qt_attr1 = next(
            (p for p in arg.type_params
             if isinstance(p, AtomicType) and p.name.upper() == 'QT-ATTR1'),
            None,
        )
        if qt_attr1 is not None:
            return AtomicType(name='QT-ATTR2',
                              type_params=[copy_semtype(p) for p in qt_attr1.type_params])
        # fall through to base apply_operator when no qt-attr1 param

    # -- QT-ATTR2: qt-attr2[T1] + " >> T1 (strip *qt params recursively) --
    elif opr_name == 'QT-ATTR2' and arg_name == '"':
        if not opr.type_params:
            return None

        def _strip_qt(st: SemType) -> SemType:
            st2 = copy_semtype(st)
            st2.type_params = [_strip_qt(p) for p in st2.type_params
                               if not (isinstance(p, AtomicType) and p.name.upper() == '*QT')]
            if isinstance(st2, OptionalType):
                st2.types = [_strip_qt(t) if t is not None else None for t in st2.types]
            return st2

        return _strip_qt(opr.type_params[0])

    # -- SUB: sub + T >> sub1[T] --
    elif opr_name == 'SUB':
        return AtomicType(name='SUB1', type_params=[copy_semtype(arg)])

    # -- Hole variables: T + *h/*p >> Range(T)[*h[Dom(T)]] --
    elif (not isinstance(opr, (AtomicType, OptionalType))
          and arg_name in ('*H', '*P')
          and opr.domain is not None and opr.range is not None):
        opr_dom = copy_semtype(opr.domain)
        opr_ran = copy_semtype(opr.range)
        arg_copy = copy_semtype(arg)
        arg_copy.type_params = list(arg_copy.type_params) + [opr_dom]
        opr_ran.type_params = list(opr_ran.type_params) + [arg_copy]
        return opr_ran

    # -- SUB1: sub1[T1] + T2[*h[T3]] >> T2 (if T1 matches T3) --
    elif opr_name == 'SUB1':
        h_params = [p for p in arg.type_params
                    if isinstance(p, AtomicType) and p.name.upper() == '*H']
        other_params = [p for p in arg.type_params
                        if not (isinstance(p, AtomicType) and p.name.upper() == '*H')]
        if (opr.type_params and h_params
                and h_params[0].type_params
                and semtype_match(opr.type_params[0], h_params[0].type_params[0],
                                  ignore_exp=True)):
            result = copy_semtype(arg)
            result.type_params = [copy_semtype(p) for p in other_params]
            return result
        return None

    # -- REP: rep + T1[*p[T2]] >> rep1[T1] --
    elif opr_name == 'REP' and not isinstance(arg, OptionalType):
        if not arg.type_params:
            return None
        p_params = [p for p in arg.type_params
                    if isinstance(p, AtomicType) and p.name.upper() == '*P']
        if p_params and p_params[0].type_params:
            return AtomicType(name='REP1', type_params=[copy_semtype(arg)])
        return None

    # -- REP1: rep1[T1[*p[T2]]] + T3 >> T1 (if T3 matches T2) --
    elif opr_name == 'REP1':
        def _has_p(tp):
            return isinstance(tp, AtomicType) and tp.name.upper() == '*P'
        t1_cands = [p for p in opr.type_params
                    if any(_has_p(sub) for sub in p.type_params)]
        if not t1_cands:
            return None
        t1 = t1_cands[0]
        p_cands = [p for p in t1.type_params if _has_p(p)]
        if not p_cands or not p_cands[0].type_params:
            return None
        t2 = p_cands[0].type_params[0]
        if semtype_match(t2, arg, ignore_exp=True):
            retval = copy_semtype(t1)
            non_t1 = [p for p in opr.type_params
                      if not any(_has_p(sub) for sub in p.type_params)]
            non_p = [p for p in t1.type_params if not _has_p(p)]
            retval.type_params = [copy_semtype(p)
                                   for p in non_t1 + non_p + list(arg.type_params)]
            return retval
        return None

    # -- POSTGEN ('s): D + POSTGEN1 >> POSTGEN2 --
    elif arg_name == 'POSTGEN1' and semtype_match(_term_semtype(), opr):
        return AtomicType(name='POSTGEN2',
                          type_params=list(opr.type_params) + list(arg.type_params))

    # -- POSTGEN2: POSTGEN2 + N_n >> D --
    elif opr_name == 'POSTGEN2' and semtype_match(_unary_noun_semtype(), arg, ignore_exp=True):
        result = copy_semtype(_term_semtype())
        result.type_params = list(opr.type_params) + list(arg.type_params)
        return result

    # -- PARG: parg + T >> parg1[T] (delexicalized) --
    elif opr_name == 'PARG':
        return AtomicType(name='PARG1', type_params=[_delexicalize(arg)])

    # -- PARG1 with verb: T_v + parg1[T2] >> T_v applied to T2 --
    elif arg_name == 'PARG1' and arg.type_params:
        stored = arg.type_params[0]
        if semtype_match(_general_verb_semtype(), opr):
            composed = extended_compose_types(opr, stored, ignore_synfeats=ignore_synfeats)
            if composed.semtype is not None:
                return composed.semtype
        # T_{N,A} + parg1[T2] >> T_{N,A} (delexicalized)
        if (not isinstance(opr, (AtomicType, OptionalType))
                and opr.suffix and opr.suffix.upper() in ('N', 'A')):
            return _delexicalize(opr)

    # Fall through to base apply_operator.
    return apply_operator(opr, arg, recurse_fn=recurse_fn, ignore_synfeats=ignore_synfeats)


def extended_compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    *,
    ignore_synfeats: bool = False,
) -> CompositionResult:
    """Compose types using extended (ULF-macro-aware) operator application."""
    if opr_semtype is None or arg_semtype is None:
        return CompositionResult(None, "none", [])

    composed = extended_apply_operator(opr_semtype, arg_semtype,
                                       ignore_synfeats=ignore_synfeats)
    if composed is not None:
        return CompositionResult(composed, "right", [opr_semtype, arg_semtype])

    composed = extended_apply_operator(arg_semtype, opr_semtype,
                                       ignore_synfeats=ignore_synfeats)
    if composed is not None:
        return CompositionResult(composed, "left", [arg_semtype, opr_semtype])

    return CompositionResult(None, "none", [])


# ---------------------------------------------------------------------------
# left_right_apply_operator — further relaxation for surface order
# ---------------------------------------------------------------------------

def left_right_apply_operator(
    raw_opr: SemType | None,
    raw_arg: SemType | None,
    *,
    recurse_fn=None,
    ignore_synfeats: bool = False,
) -> SemType | None:
    """Extended composition that additionally allows TERM+VP and SENT-MOD passthrough."""
    if raw_opr is None or raw_arg is None:
        return None

    if recurse_fn is None:
        recurse_fn = lambda o, a: left_right_apply_operator(
            o, a, recurse_fn=recurse_fn, ignore_synfeats=ignore_synfeats
        )

    opr = unroll_exponent_step(raw_opr)
    arg = unroll_exponent_step(raw_arg)

    # TERM + VP → apply VP to TERM (treat subject as argument to verb)
    if (semtype_match(_term_semtype(), opr)
            and semtype_match(_general_verb_semtype(), arg)):
        return apply_operator(arg, opr, ignore_synfeats=ignore_synfeats)

    # SENT-MOD + * → * unchanged
    if semtype_match(_sent_mod_semtype(), opr):
        return copy_semtype(arg)

    # * + SENT-MOD → * unchanged
    if semtype_match(_sent_mod_semtype(), arg):
        return copy_semtype(opr)

    # Fall through to extended operator.
    return extended_apply_operator(opr, arg, recurse_fn=recurse_fn,
                                   ignore_synfeats=ignore_synfeats)


def left_right_compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    *,
    ignore_synfeats: bool = False,
) -> CompositionResult:
    """Compose types using left-right (surface-order-aware) operator application."""
    if opr_semtype is None or arg_semtype is None:
        return CompositionResult(None, "none", [])

    composed = left_right_apply_operator(opr_semtype, arg_semtype,
                                         ignore_synfeats=ignore_synfeats)
    if composed is not None:
        return CompositionResult(composed, "right", [opr_semtype, arg_semtype])

    composed = left_right_apply_operator(arg_semtype, opr_semtype,
                                         ignore_synfeats=ignore_synfeats)
    if composed is not None:
        return CompositionResult(composed, "left", [arg_semtype, opr_semtype])

    return CompositionResult(None, "none", [])
