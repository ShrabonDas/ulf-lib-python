from __future__ import annotations

from .semtype import (
    AtomicType, SemType, OptionalType, 
    copy_semtype, semtype_match, unroll_exponent_step,
)


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
    
    # None means use the default recursion through apply_operator. We use a sentinel
    # because Python evaluates default arguments before apply_operator is bound, so
    # recurse_fn cannot default to apply_operator in the function signature.
    if recurse_fn is None:
        recurse_fn = apply_operator
    
    # We can now assume all domain and top-level exponents are 1.
    opr = unroll_exponent_step(raw_opr)
    arg = unroll_exponent_step(raw_arg)
    
    result: SemType | None = None

    if isinstance(opr, OptionalType):
        # Operator is an optional type.
        results = [
            recurse_fn(opt, arg, recurse_fn=recurse_fn, ignore_synfeats=ignore_synfeats)
            for opt in opr.types
        ]
        present = [res for res in results if res is not None]
        
        if not present:
            result = None
        elif len(present) == 1:
            result = present[0]
        else:
            result = OptionalType(types=present)
    elif isinstance(arg, OptionalType):
        # Argument is an optional type.
        results = [
            recurse_fn(opr, opt, recurse_fn=recurse_fn, ignore_synfeats=ignore_synfeats)
            for opt in arg.types
        ]
        present = [res for res in results if res is not None]
        
        if not present:
            result = None
        elif len(present) == 1:
            result = present[0]
        else:
            result = OptionalType(types=present)
    elif isinstance(opr, AtomicType):
        # Operator is a non-optional atomic type of the form A^n with n > 1.
        if semtype_match(opr, arg) and opr.ex > 1:
            result = copy_semtype(opr, c_ex=opr.ex - 1)
    elif (
        semtype_match(opr.domain, arg)
        and opr.domain is not None
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
    opr_apply_fn_name: str = "APPLY-OPERATOR!",
) -> SemType | None:
    """Compose two types if possible and return the composed type."""
    if opr_semtype is None or arg_semtype is None:
        return None
    
    if opr_apply_fn_name == "APPLY-OPERATOR!":
        composed = apply_operator(
            opr_semtype,
            arg_semtype,
            ignore_synfeats=ignore_synfeats,
        )
        if composed is not None:
            return composed
        
        composed = apply_operator(
            arg_semtype,
            opr_semtype,
            ignore_synfeats=ignore_synfeats,
        )
        
        if composed is not None:
            return composed
