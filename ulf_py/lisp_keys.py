def _escape_lisp_string(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def lisp_repr(x) -> str:
    """
    Serialize a Python value into its Lisp prin1 string representation.
    
    This mirrors Common Lisp's prin1 output so that lookup keys generated
    here match the keys recorded by the Lisp ULF system in ulf_maps.json.
    
        None/False  → "NIL"
        True        → "T"
        str         → '"quoted"'
        list/tuple  → "(space separated elements)"
        other       → converts to str first
    """
    if x is None or x is False:
        return 'NIL'
    if x is True:
        return 'T'
    if isinstance(x, str):
        return f'"{_escape_lisp_string(x)}"'
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            return 'NIL'
        return "(" + " ".join(lisp_repr(e) for e in x) + ")"
    return lisp_repr(str(x))


def make_lisp_lookup_key(items: list) -> str:
    """
    Serialize a list of arguments into a Lisp-style string for use as a
    lookup key into the precomputed ULF maps (ulf_maps.json).
    
    The maps were recorded from a Common Lisp ULF system which keyed entries
    using prin1-serialized argument lists. This function reproduces that exact
    format so Python lookups can find the right entries.
    
    Example:
        make_lisp_lookup_key(["(D=>(S=>2))", "D", True, "APPLY-OPERATOR!"])
        → '("(D=>(S=>2))" "D" T "APPLY-OPERATOR!")'
    """
    return lisp_repr(items)