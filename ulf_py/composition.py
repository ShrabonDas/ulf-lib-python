from .semtype import SemType, ULF_MAPS, semtype2str, str2semtype
from .lisp_keys import key_list


def compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    ignore_synfeats: bool = True,
    opr_apply_fn_name: str = 'APPLY-OPERATOR!',
) -> SemType | None:
    """Compose two semtypes. Uses oracle lookup."""
    if opr_semtype is None or arg_semtype is None:
        return None
    key = key_list([semtype2str(opr_semtype), semtype2str(arg_semtype),
                    bool(ignore_synfeats), opr_apply_fn_name])
    entry = ULF_MAPS['compose_types'].get(key)
    if entry is None:
        return None
    composed_str = entry.get('composed')
    if composed_str is None:
        return None
    return str2semtype(composed_str)