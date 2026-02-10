def _escape_lisp_string(s: str) -> str:
    return s.replace('\\', '\\\\').replace('"', '\\"')


def prin1(x) -> str:
    if x is None:
        return 'NIL'
    if x is True:
        return 'T'
    if x is False:
        return 'NIL'
    
    if isinstance(x, str):
        return f"\"{_escape_lisp_string(x)}\""
    if isinstance(x, (list, tuple)):
        if len(x) == 0:
            return 'NIL'
        inner = " ".join(prin1(e) for e in x)
        return f"({inner})"
    
    return prin1(str(x))


def key_list(items: list) -> str:
    return prin1(items)