# TODO: remove ULF_MAPS after verifying accuracy
from semtype import SemType, ULF_MAPS

def compose_types(
    opr_semtype: SemType | None,
    arg_semtype: SemType | None,
    ignore_synfeats: bool = True,
    opr_apply_fn_name: str = 'APPLY-OPERATOR!',
) -> SemType | None:
    if opr_semtype is None or arg_semtype is None:
        return None
    
    
    key = repr([opr_semtype.wire, arg_semtype.wire, bool(ignore_synfeats), opr_apply_fn_name])
    
    entry = ULF_MAPS['compose_types'].get(key)
    composed_wire = entry.get('composed')
    if composed_wire is None:
        return None
    return SemType(wire=composed_wire)