from .semtype import SemType, ULF_MAPS, semtype2str, str2semtype, _normalize_synfeats_order, _normalize_whitespace
from .lisp_keys import make_lisp_lookup_key


def _first_pos_suffix(suffix: str | None) -> str | None:
    """Return the first recognized part-of-speech suffix character."""
    if suffix is None:
        return None
    for char in suffix.upper():
        if char in "NAVP":
            return char
    return None


def merge_suffixes(opr: SemType, arg: SemType) -> str | None:
    """Compute the result suffix for core composition."""
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


def _oracle_compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    ignore_synfeats: bool = True,
    opr_apply_fn_name: str = 'APPLY-OPERATOR!',
) -> SemType | None:
    """Look up a precomputed composition result in the oracle data."""
    if opr_semtype is None or arg_semtype is None:
        return None
    opr_str = semtype2str(opr_semtype)
    arg_str = semtype2str(arg_semtype)
    if opr_str is None or arg_str is None:
        return None
    key = make_lisp_lookup_key([opr_str, arg_str,
                    bool(ignore_synfeats), opr_apply_fn_name])
    key = _normalize_whitespace(_normalize_synfeats_order(key))
    entry = ULF_MAPS['compose_types'].get(key)
    if entry is None:
        return None
    composed_str = entry.get('composed')
    if composed_str is None:
        return None
    return str2semtype(composed_str)


def compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    ignore_synfeats: bool = True,
    opr_apply_fn_name: str = "APPLY-OPERATOR!",
) -> SemType | None:
    """Compose an operator semtype with an argument semtype."""
    return _oracle_compose_types(
        opr_semtype,
        arg_semtype,
        ignore_synfeats,
        opr_apply_fn_name,
    )
