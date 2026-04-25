"""ULF semantic type inference.

Port of repos/ulf-lib/composition.lisp: ulf-type? and ulf-type-string?
"""
from __future__ import annotations

from .semtype import SemType, AtomicType, SemType as _SemType, str2semtype, semtype2str, copy_semtype


def ulf_type(ulf, lambda_vars: list | None = None) -> SemType | None:
    """Return the semantic type of ULF expression *ulf*.

    Atoms are resolved via atom_semtype (with special cases for macros and holes).
    Compounds are composed left-associatively using extended_compose_types.
    Lambda forms build a function type from the body type.
    """
    from .lexical import atom_semtype, lex_macro_p, lex_macro_hole_p
    from .composition import extended_compose_types

    if lambda_vars is None:
        lambda_vars = []

    # --- Atomic ---
    if isinstance(ulf, str):
        u = ulf.lower()
        # quote symbol
        if u == '"':
            return str2semtype('"', extended=True)
        # possessive 's — plain 's or pipe-delimited |'S|
        if u in ("'s", "|'s|"):
            return str2semtype('POSTGEN1', extended=True)
        # standard semtype table
        st = atom_semtype(ulf)
        if st is not None:
            return st
        # lambda variable
        if ulf in lambda_vars:
            return str2semtype('D')
        # ULF macro (sub, rep, qt-attr, n+preds, np+preds …)
        if lex_macro_p(ulf):
            return str2semtype(ulf.upper(), extended=True)
        # *qt hole — needs D[*QT] type
        if u == '*qt':
            return str2semtype('D[*QT]', extended=True)
        # other macro holes (*h, *p, *s, *ref …)
        if lex_macro_hole_p(ulf):
            return str2semtype(ulf.upper(), extended=True)
        return None

    # --- Tuple ---
    if isinstance(ulf, tuple):
        if len(ulf) == 0:
            return None
        if len(ulf) == 1:
            return ulf_type(ulf[0], lambda_vars)
        # lambda form: (lambda var body)
        if (isinstance(ulf[0], str) and ulf[0].lower() == 'lambda'
                and len(ulf) == 3):
            var = ulf[1]
            body_type = ulf_type(ulf[2], lambda_vars + [var])
            if body_type is None:
                return None
            return _SemType(connective='=>',
                            domain=str2semtype('D'),
                            range=body_type)
        # general compound: left-associative composition
        # ulf_type((a b c)) = compose(ulf_type((a b)), ulf_type(c))
        init_type = ulf_type(ulf[:-1], lambda_vars)
        last_type = ulf_type(ulf[-1], lambda_vars)
        result = extended_compose_types(init_type, last_type, ignore_synfeats=False)
        return result.semtype

    return None


def ulf_type_string(ulf) -> str | None:
    """Return the semtype2str of ulf_type(ulf), or None if no type."""
    return semtype2str(ulf_type(ulf))
