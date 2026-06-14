"""ULF semantic type inference.

Port of repos/ulf-lib/composition.lisp: ulf-type? and ulf-type-string?
"""
from __future__ import annotations

from .semtype import SemType, AtomicType, OptionalType, SemType as _SemType, str2semtype, semtype2str, copy_semtype


def _expand_optional_domain(st: SemType | None) -> SemType | None:
    """Expand {A|B}=>C to {(A=>C)|(B=>C)}, matching Lisp's new-semtype behavior.

    Lisp's new-semtype auto-expands domain-optional function types at construction
    time (ulf-lib/semtype.lisp lines 264-276). Python builds them lazily, so we
    expand here just before composition so the composition logic sees the same
    structure as Lisp (an OptionalType, not a SemType with OptionalType domain).

    Recurses into OptionalType options so nested function types with OptionalType
    domains also get expanded.
    """
    if st is None or isinstance(st, AtomicType):
        return st
    if isinstance(st, OptionalType):
        new_opts = []
        for opt in st.types:
            expanded = _expand_optional_domain(opt)
            if isinstance(expanded, OptionalType):
                new_opts.extend(expanded.types)
            elif expanded is not None:
                new_opts.append(expanded)
        if len(new_opts) == 1:
            return new_opts[0]
        if new_opts == list(st.types):
            return st
        result = copy_semtype(st)
        result.types = new_opts
        return result
    if isinstance(st.domain, OptionalType) and st.domain.ex == 1:
        opts = [copy_semtype(st, c_domain=opt) for opt in st.domain.types]
        flat = []
        for o in opts:
            expanded = _expand_optional_domain(o)
            if isinstance(expanded, OptionalType):
                flat.extend(expanded.types)
            elif expanded is not None:
                flat.append(expanded)
        if len(flat) == 1:
            return flat[0]
        return OptionalType(types=flat)
    return st


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

    # Lisp's nil — Python uses None to represent (categorical-sample) overshoot.
    # Lisp's (atom-semtype? nil) accidentally returns D because (cl-ppcre:scan-
    # to-strings PAT "NIL") yields nil when no pattern matches, and the assoc
    # test (string-equal nil "NIL") coerces nil to its symbol-name "NIL" → T,
    # so the first non-matching pattern wins (.PRO suffix) → D. Mirror that.
    if ulf is None:
        return str2semtype('D')

    # --- Numeric atoms (cardinal numerals → D, matching the [\d\.]+ pattern) ---
    if isinstance(ulf, (int, float)):
        return str2semtype('D')

    # --- Atomic ---
    if isinstance(ulf, str):
        u = ulf.lower()
        # quote symbol and possessive 's — Lisp's ulf-type? has special cases
        # that return the extended types " and POSTGEN1, but they only fire when
        # the symbol is interned in the :ulf-lib package. In the sampler context
        # (:ulf-type-sample package), the symbols fall through to atom-semtype?
        # which regex-matches |...| against the names pattern \|[^|]+\| and
        # returns D. Match this actual Lisp behavior by returning D here.
        if u in ('"', '|"|', "'s", "|'s|"):
            return str2semtype('D')
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
        # macro holes (*h, *p, *qt, *s, *ref). Lisp's ulf-type? has a special
        # case `(eql ulf '*qt) → D[*QT]` but it's dead code under the sampler:
        # `*qt` lives in :ulf-lib, the sampler reads in :ulf-type-sample, so
        # the eql comparison silently fails and `lex-macro-hole?` (which uses
        # name-based package coercion) wins → plain AtomicType *QT. Same
        # package-bug family as `|"|` → D and `|'s|` → D documented earlier.
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
        init_type = _expand_optional_domain(ulf_type(ulf[:-1], lambda_vars))
        last_type = _expand_optional_domain(ulf_type(ulf[-1], lambda_vars))
        result = extended_compose_types(init_type, last_type, ignore_synfeats=False)
        # Re-expand the composition result: applying an argument can drop a
        # domain exponent from N to 1, exposing a `{A|B}=>C` form that Lisp's
        # new-semtype auto-flattens at construction. Match by re-expanding
        # after composition too.
        return _expand_optional_domain(result.semtype)

    return None


def ulf_type_string(ulf) -> str | None:
    """Return the semtype2str of ulf_type(ulf), or None if no type."""
    return semtype2str(ulf_type(ulf))
