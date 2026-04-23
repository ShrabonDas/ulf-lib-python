from ulf_py import semtype_match, str2semtype
from ulf_py.composition import compose_types


def compose_semtype_strings(
    opr: str,
    arg: str,
    *,
    ignore_synfeats: bool = False,
):
    """Compose two semtype strings via compose_types. Synfeats is ignored by default to simplify testing."""
    return compose_types(
        str2semtype(opr),
        str2semtype(arg),
        ignore_synfeats=ignore_synfeats,
    ).semtype


def test_auxiliary_compose_matches_lisp_case() -> None:
    """AUX + verb yields a verb with the expected feature changes."""
    # AUX + (D=>(S=>2))_V (no T, X) >> (D=>(S=>2))_V%X,!T
    result = compose_semtype_strings(
        "((D=>(S=>2))_V%!T,!X>>(D=>(S=>2))_V%!T,X)",
        "(D=>(S=>2))_V",
    )
    assert semtype_match(
        str2semtype("(D=>(S=>2))_V%X,!T"),
        result,
    )
    
    
def test_tensed_auxiliary_compose_matches_lisp_case() -> None:
    """TAUX + untensed auxiliary verb yields a tensed auxiliary verb."""
    # TENSE + AUX => TAUX
    # TAUX + (D=>(S=>2))_V (no T, X) >> (D=>(S=>2))_V%T,X
    result = compose_semtype_strings(
        "((D=>(S=>2))_V%!T,!X>>(D=>(S=>2))_V%T,X)",
        "(D=>(S=>2))_V%!T,!X",
    )
    assert semtype_match(
        str2semtype("(D=>(S=>2))_V%T,X"),
        result,
    )
