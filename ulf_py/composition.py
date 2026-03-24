from .semtype import SemType, ULF_MAPS, semtype2str, str2semtype, _normalize_synfeats_order, _normalize_whitespace
from .lisp_keys import make_lisp_lookup_key


def compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    ignore_synfeats: bool = True,
    opr_apply_fn_name: str = 'APPLY-OPERATOR!',
) -> SemType | None:
    """Compose an operator semtype with an argument semtype.
    
    WARNING: This is a oracle-based implementation that looks up precomputed results
    form ulf_maps.json. It only returns a result for operator/argument
    combinations that were recorded by the Lisp ULF system. Unrecognized
    combinations return None.
    """
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