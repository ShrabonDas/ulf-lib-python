import pytest

import ulf_py.semtype as semtype_module
from ulf_py import semtype_match, str2semtype


def match_str(pattern: str, value: str) -> bool:
    """Return whether the semtype parsed from value matches the parsed pattern."""
    return semtype_match(
        str2semtype(pattern, extended=True), 
        str2semtype(value, extended=True)
    )

def equal_str(left: str, right: str) -> bool:
    """Return whether two semtype strings are equal under semtype_equal."""
    return semtype_module.semtype_equal(
        str2semtype(left, extended=True),
        str2semtype(right, extended=True),
    )


@pytest.mark.parametrize(
    ("pattern", "value"),
    [
        ("D", "D"),
        ("(D=>D)", "(D=>D)"),
        ("(D=>D)_V", "(D=>D)_V"),
        ("(D=>D)", "(D=>D)_V"),
        ("(D=>D)%T", "(D=>D)%T"),
        ("(D=>D)", "(D=>D)%T,X"),
    ]
)
def test_basic_semtype_match_positive(pattern: str, value: str) -> None:
    """Accept semtypes that satisfy the pattern under basic matching rules."""
    assert match_str(pattern, value)
    
    
def test_basic_semtype_match_rejects_missing_required_synfeats() -> None:
    """Reject a value when the pattern requires syntactic features it does not provide."""
    assert not match_str("(D=>D)%T,X", "(D=>D)")
    
    
@pytest.mark.parametrize(
    ("pattern", "value"),
    [
        ("D^2", "(D=>D)"),
        ("(D=>D)", "D^2"),
        ("(D=>D)^2", "((D=>D)=>(D=>D))"),
        ("((D=>D)=>(D=>D))", "(D=>D)^2"),
        ("(D=>(D=>2))", "(D^2=>2)"),
        ("(D=>(D^2=>2))", "(D^3=>2)"),
        ("(D=>D)^2", "((D=>D)=>D^2)"),
        ("(D=>(D=>(D=>D)))", "(D^2=>D^2)"),
    ]
)
def test_exponent_semtype_match_positive(pattern: str, value: str) -> None:
    """Accept semtypes whose exponent forms match equivalent expanded forms."""
    assert match_str(pattern, value)
    

def test_exponent_semtype_match_negative() -> None:
    """Reject exponent structures that are not equivalent under semtype matching."""
    assert not match_str("(D=>D)^2", "(D^2=>D^2)")
    

@pytest.mark.parametrize(
    ("pattern", "value"),
    [
        # Optionals are symmetric.
        ("{D|2}", "D"),
        ("D", "{D|2}"),
        # Optionals with exponents.
        ("{D|2}^2", "(D=>2)"),
        ("{D|2}^2", "(D=>D)"),
        ("{D|2}^2", "(2=>D)"),
        ("{D|2}^2", "(2=>2)"),
        ("{D|2}^2", "({D|2}=>{D|2})"),
        ("{D|2}^2", "{D^2|{2^2|{(D=>2)|(2=>D)}}}"),
        # Optionals in argument exponents
        ("({D|2}^3=>S)", "(D=>(2=>(D=>S)))"),
        ("({D|2}^n=>S)", "(D=>(2=>(D=>S)))"),
        ("({D|2}^n=>S)", "(D=>S)"),
        ("({D|2}^n=>S)", "S"),
    ]
)
def test_optional_semtype_match_positive(pattern: str, value: str) -> None:
    """Accept semtypes when any compatible optional branch satisfies the pattern."""
    assert match_str(pattern, value)
    
    
def test_optional_semtype_match_with_custom_max_exponent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Expand variable exponents using the configured maximum exponent bound."""
    monkeypatch.setattr(semtype_module, "SEMTYPE_MAX_EXPONENT", 4)
    assert match_str("({D|2}^n=>S)", "(D=>(D=>(D=>(D=>S))))")
    

@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("D", "D"),
        ("(D=>D)", "(D=>D)"),
        ("(D=>D)_V", "(D=>D)_V"),
        ("(D=>D)%T", "(D=>D)%T"),
    ]
)
def test_basic_semtype_equal_positive(left: str, right: str) -> None:
    """Accept semtypes that are equal under exact semtype equality."""
    assert equal_str(left, right)
    
    
@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("(D=>D)", "(D=>D)_V"),
        ("(D=>D)", "(D=>D)%T,X"),
        ("(D=>D)%T,X", "(D=>D)")
    ]
)
def test_basic_semtype_equal_negative(left: str, right: str) -> None:
    """Reject semtypes that differ by suffix or exact syntactic features."""
    assert not equal_str(left, right)