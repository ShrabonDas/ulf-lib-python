from ulf_py import semtype_match, str2semtype
from ulf_py.composition import compose_types


def compose(
    opr: str,
    arg: str,
    *,
    ignore_synfeats: bool = False,
):
    """Compose two semtype strings."""
    return compose_types(
        str2semtype(opr),
        str2semtype(arg),
        ignore_synfeats=ignore_synfeats,
    )


def test_auxiliary_compose_matches_lisp_case() -> None:
    """AUX + verb yields a verb with the expected feature changes."""
    result = compose(
        "((D=>(S=>2))_V%!T,!X>>(D=>(S=>2))_V%!T,X)",
        "(D=>(S=>2))_V",
    )
    assert semtype_match(
        str2semtype("(D=>(S=>2))_V%X,!T"),
        result,
    )