"""
Data structures for representing ULF semantic types.

Connective semantics
====================
=>  Basic antecedent/consequent.
    Underspecified synfeats in the antecedent allow anything;
    underspecified synfeats in the consequent take the parent values.
    Any restrictive feature must be spelled out explicitly in both positions.

>>  Argument feature-preserving antecedent/consequent.
    Underspecified synfeats in the consequent inherit the antecedent value.
    Example: instead of {((S=>2)%!t=>(S=>2)%!t)|((S=>2)_t=>(S=>2)%t)} for
    a tense-preserving sentence modifier, write ((S=>2)>>(S=>2)).

%>  Synfeat-modification shorthand (retains semantic content, distributes
    accordingly).  Always reducible to >> with synfeat changes applied before
    and after distribution.  This shorthand is preprocessed out and will not
    appear in system-generated semtypes.
    See the tense entry (PRES|PAST|CF) in ttt-lexical-patterns for an example.

!   Prefix on any feature value for negation, e.g. !t = not-tensed.

# TODO: Make sure *h and *p can have duplicates, or have counts.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import product
from typing import Literal, Any, Sequence
from .syntactic_features import SyntacticFeatures, DEFAULT_SYNTACTIC_FEATURES, lookup_feature_name
from .feature_definition_declarations import FEATURE_DEFINITIONS_DICT
import json
import re
import string


def _normalize_whitespace(s: str) -> str:
    """Collapse all whitespace sequences to a single space."""
    return re.sub(r'\s+', ' ', s)


def _normalize_synfeats_order(s: str) -> str:
    """Sort syntactic feature values alphabetically appearing in the string after `%`"""
    def _sort_match(m):
        vals = m.group(1).split(',')
        return '%' + ','.join(sorted(vals))
    return re.sub(r'%([A-Z!][A-Z0-9!,]*)', _sort_match, s)


# Oracle data file: ulf_maps.json
# Precomputed semtype maps exported from the Common Lisp ULF system.
# Contains lookup tables for str2semtype, compose_types, and semtype_match
# This file is not in the repo - download it via `bash_setup_data.sh`
# (hosted as Github release asset under tag v0.1.0).`
with open("ulf_maps.json") as file:
    ULF_MAPS: dict[str, dict[str, Any]] | None = json.load(file)
    # str2semtype: add output-string keys
    extra = {}
    for k, v in ULF_MAPS['str2semtype'].items():
        if isinstance(v, dict) and 'string' in v and v['string'] != k:
            extra[v['string']] = v
    ULF_MAPS['str2semtype'].update(extra)
    # str2semtype: also add normalized keys
    normalized_extra = {}
    for k, v in ULF_MAPS['str2semtype'].items():
        nk = _normalize_synfeats_order(k)
        if nk != k and nk not in ULF_MAPS['str2semtype']:
            normalized_extra[nk] = v
    ULF_MAPS['str2semtype'].update(normalized_extra)
    # compose_types: normalize synfeat order and whitespace in keys
    ULF_MAPS['compose_types'] = {
        _normalize_whitespace(_normalize_synfeats_order(k)): v
        for k, v in ULF_MAPS['compose_types'].items()
    }
    # semtype_match: normalize synfeat order and whitespace in keys
    ULF_MAPS['semtype_match'] = {
        _normalize_whitespace(_normalize_synfeats_order(k)): v
        for k, v in ULF_MAPS['semtype_match'].items()
    }
    
Connective = Literal['=>', '>>', "%>"] 
CONNECTIVES = Connective.__args__

SEMTYPE_MAX_EXPONENT = 3
# Maximum exponent for variable (^n) semtype expansion.
# e.g. D^n => 2 can be generated as 2, (D=>2), (D=>(D=>2)), etc. up to this limit.
# TODO: if this value becomes configurable at runtime, add a clear reload/update
# path for any cached or precomputed dependent state so the change
# propagates consistently.

# ==================================================
# Data Classes
# ==================================================

@dataclass(slots=True)
class SemType:
    """
        (D=>(S=>2))_V%LEX,!T => SemType(
        connective = "=>"
        domain = AtomicType(name="D")
        range = SemType(
            connective = "=>"
            domain = AtomicType(name="S")
            range = AtomicType(name="2")
        )
        suffix = "V"
        synfeats = SyntacticFeatures({"LEXICAL": "lex", "TENSE": "!it"})
    )
    """
    connective: Connective | None = None
    domain: "SemType" | None = None
    range: "SemType" | None = None
    ex: int = 1
    suffix: str | None = None  # only n, v, a, p
    type_params: list['SemType'] = field(default_factory=list)  # internal type parameters, needed for some macros to carry over information
    synfeats: SyntacticFeatures = field(default_factory=lambda: DEFAULT_SYNTACTIC_FEATURES.copy())  # miscellaneous ordered syntactic features
    
    
@dataclass(slots=True)
class AtomicType(SemType):
    """
    An Atomic Type: just a name
    """
    name: str = ""          # "D", "S", "2", "QT-ATTR1", "+PREDS"
    
    
@dataclass(slots=True)
class OptionalType(SemType):
    """
    One of several alternatives
    """
    types: list[SemType | None] = field(default_factory=list)      # {A | B | C}
    

# Lex macros — symbols seen directly in ULF expressions.
# Mirrors Lisp lex-macro? from ttt-lexical-patterns.lisp.
_LEX_MACROS = {
    "QT-ATTR",
    "SUB",
    "REP",
    "N+PREDS",
    "NP+PREDS",
    "VOC",
    "VOC-O"
}

# Lex macro holes — gap-filler slots inside macro expressions.
# Mirrors Lisp lex-macro-hole? from ttt-lexical-patterns.lisp.
_LEX_MACRO_HOLES = {
    "*H",
    "*P",
    "*QT",
    "*S",
    "*REF",
}

# Macro transition types — intermediate types used only in the type system to
# mediate the different steps of macro-composition (not seen directly in ULF
# expressions).
# Keep local for now because they are only used by extended semtype parsing.
_MACRO_TRANSITION_TYPES = {
    "QT-ATTR1",
    "QT-ATTR2",
    "SUB1",
    "REP1",
    "POSTGEN1",
    "POSTGEN2",
    "+PREDS",
}

# All atomic types added by macro/extension parsing beyond the base set {D, S, 2}.
# Replacing this set allows reuse of the same composition operators for a different
# type system (e.g., full Episodic Logic with subtypes of D: events E, kinds K, etc.)
_MACRO_EXTENSION_ATOMS = (
    {
        "PARG",   # p-arg type extension
        '"',      # quote symbols
    }
    | _LEX_MACROS
    | _LEX_MACRO_HOLES
    | _MACRO_TRANSITION_TYPES
)



@dataclass(slots=True)
class _PendingOutSynfeat:
    """
    Internal representation for a parsed `%>` expression before it is converted
    into ordinary `>>` semtypes.
    """
    antecedent: SemType | None
    new_synfeats: SyntacticFeatures
    type_params: list[SemType] = field(default_factory=list)

    
# ==================================================
# semtype2str - reconstruct the string from a SemType tree
# ==================================================

def _synfeats_str(sf: SyntacticFeatures | None) -> str:
    if sf is None or not sf.feature_map:
        return ""
    
    order = {name: i for i, name in enumerate(FEATURE_DEFINITIONS_DICT)}
    
    vals = []
    for feat_name, feat_val in sorted(sf.feature_map.items(),
                                      key=lambda x: order.get(x[0], 999)):
        if feat_val is None:
            continue
        vals.append(feat_val.upper())
        
    if not vals:
        return ""
    return "%" + ",".join(vals)

def semtype2str(st: SemType | None) -> str | None:
    """Convert a SemType tree back to its Lisp-style string representation."""
    if st is None:
        return None
    
    # type params: [A;B;C]
    type_params_str = ""
    if st.type_params:
        rendered_params = []
        for tp in st.type_params:
            if tp is None:
                raise ValueError("type_params must not contain None")
            s = semtype2str(tp)
            if s is None:
                raise ValueError("type_params must serialize to a non-None string")
            rendered_params.append(s)
        type_params_str = "[" + ";".join(rendered_params) + "]"
            
    # order of modifiers: _suffix, %synfeats, ^exponent
    suffix_str = f"_{st.suffix}" if st.suffix else ""
    synfeat_str = _synfeats_str(st.synfeats)
    exponent_str = "" if st.ex == 1 else f"^{'n' if st.ex == -1 else st.ex}"
    
    if isinstance(st, AtomicType):
        base = f"{st.name}{suffix_str}{synfeat_str}{exponent_str}"
        
    elif isinstance(st, OptionalType):
        rendered_options: list[str] = []
        for t in st.types:
            if t is None:
                rendered_options.append('NIL')
            else:
                s = semtype2str(t)
                if s is None:
                    return None
                rendered_options.append(s)
                
        if not rendered_options:
            return None
        
        base = "{" + "|".join(rendered_options) + "}" + exponent_str
        
    else:
        d = semtype2str(st.domain)
        r = semtype2str(st.range)
        if d is None or r is None:
            return None
        base = f"({d}{st.connective}{r}){suffix_str}{synfeat_str}{exponent_str}"
        
    return base if not type_params_str else f"{base}{type_params_str}"
    
    

# ==================================================
# String Parser
# ==================================================

class SemTypeParseError(ValueError):
    """Raised when a semtype string cannot be parsed."""
    def __init__(self, msg: str, pos: int | None = None, input_str: str | None = None):
        self.pos = pos
        self.input_str = input_str
        super().__init__(msg)
        
        
class SemTypeParser:
    """
    Recursive descent parser for semtype string representations.
    
    Examples:
        "D" -> AtomicType(name="D")
        "{D|(D=>(S=>2))}" -> SemType(domain=D, range=(S=>2))
        "{D|(D=>(S=>2))}^2" -> OptionalType([...], ex=2)
        "(D=>(S=>2))_V%LEX,!T" -> SemType(..., suffix="V", synfeats={"LEXICAL": "lex", "TENSE": "!t"})

    Grammar:
        type: primary modifiers
        primary: '(' type CONN type ')' | '{' type ('|' type)* '}' | ATOM
        modifiers: ('^' EXP | '_' SUFFIX | '%' FEATURES | '[' TYPEPARAMS ']')*
        CONN: '=>' | '>>' | '%>'
    """
    
    ATOM_CHARS = set(string.ascii_letters + string.digits + '+*-')
    FEAT_STOP = set(',|})^_[]=>(')
    
    def __init__(self, s: str, *, allow_extended_atoms: bool = False):
        self.s = s
        self.pos = 0
        self.allow_extended_atoms = allow_extended_atoms
        
    def _error(self, msg: str) -> SemTypeParseError:
        return SemTypeParseError(msg, pos=self.pos, input_str=self.s)
    
    def _peek(self) -> str | None:
        return self.s[self.pos] if self.pos < len(self.s) else None
    
    def _advance(self) -> str:
        c = self.s[self.pos]
        self.pos += 1
        return c
    
    def _expect(self, c: str) -> None:
        if self._peek() != c:
            raise self._error(f"Expected {c!r} at pos {self.pos}, got {self._peek()!r}")
        self._advance()
        
    def _consume_while(self, pred) -> str:
        start = self.pos
        while self.pos < len(self.s) and pred(self.s[self.pos]):
            self.pos += 1
        return self.s[start:self.pos]
    
    def parse(self) -> SemType | _PendingOutSynfeat | None:
        result = self._parse_type()
        if self.pos != len(self.s):
            raise self._error(
                f"Trailing chars at pos {self.pos}: {self.s[self.pos:]!r}"
            )
        
        return result
        
    def _parse_type(self) -> SemType | _PendingOutSynfeat | None:
        return self._parse_modifiers(self._parse_primary())
    
    def _parse_primary(self) -> SemType | _PendingOutSynfeat | None:
        c = self._peek()
        
        if c == '(':
            return self._parse_function_type()
        
        if c == '{':
            return self._parse_optional_type()
        
        if self.allow_extended_atoms and c == '"':
            self._advance()
            return AtomicType(name='"')
        
        if c is not None and c in self.ATOM_CHARS:
            return self._parse_atom()
        
        raise self._error(f"Unexpected {c!r} at pos {self.pos}")
        
    def _parse_atom(self) -> AtomicType | None:
        token = self._consume_while(lambda ch: ch in self.ATOM_CHARS)
        
        if not token:
            raise self._error(f"Expected atom at pos {self.pos}")
        
        # Accept NIL (case-insensitive) for compatibility with CL-based ULF
        # code, which may produce NIL where Python uses None.
        if token.upper() == 'NIL':
            return None
        
        # Validate token against accepted types. Base types are D, S, 2.
        # With allow_extended_atoms=True, macro extension atoms are also accepted.
        # This is the extension point for supporting a different type system
        # (e.g., full Episodic Logic with events E, kinds K, real numbers R, etc.).
        _BASE_ATOMS = {"D", "S", "2"}
        accepted = _BASE_ATOMS | _MACRO_EXTENSION_ATOMS if self.allow_extended_atoms else _BASE_ATOMS
        if token not in accepted:
            raise self._error(f"Unknown atom {token!r} at pos {self.pos - len(token)}")
        
        return AtomicType(name=token)

    
    def _parse_function_type(self) -> SemType | _PendingOutSynfeat:
        self._expect('(')
        domain = self._parse_type()
        conn = self._parse_connective()
        
        if conn == "%>":
            # The %> connective is a shorthand whose RHS is a bare synfeat
            # specification rather than a full semtype.  It is preprocessed out
            # into ordinary >> types by process_out_synfeat_connective and will
            # not appear in system-generated semtypes.
            new_synfeats = self._parse_synfeat_connector_rhs()
            self._expect(')')
            return _PendingOutSynfeat(
                antecedent=domain,
                new_synfeats=new_synfeats,
            )
        
        range_ = self._parse_type()
        self._expect(')')
        
        return SemType(connective=conn, domain=domain, range=range_)
    
    def _parse_synfeat_connector_rhs(self) -> SyntacticFeatures:
        """
        Parse RHS of `%>`, which is a bare syntactic-feature specification
        rather than a full semtype.
        """
        return self._parse_features()
    
    def _parse_optional_type(self) -> OptionalType:
        self._expect('{')
        
        types = [self._parse_type()]
        while self._peek() == '|':
            self._advance()
            types.append(self._parse_type())
        self._expect('}')
        
        return OptionalType(types=types)
    
    def _parse_connective(self) -> str:
        two = self.s[self.pos:self.pos + 2]
        
        if two in CONNECTIVES:
            self.pos += 2
            return two
        
        raise self._error(f"Expected connective at pos {self.pos}")
    
    def _parse_modifiers(self, base: SemType | _PendingOutSynfeat | None) -> SemType | _PendingOutSynfeat | None:
        if base is None:
            return None
        
        while True:
            c = self._peek()
            
            if isinstance(base, _PendingOutSynfeat):
                if c == '[':
                    base.type_params = self._parse_type_params()
                    continue
                if c in {'^', '_', '%'}:
                    raise self._error(
                        "`%>` expressions cannot have top-level suffixes, synfeats, or exponents"
                    )
                break
            
            if c == '^':
                self._advance()
                base.ex = self._parse_exponent()
            elif c == '_':
                self._advance()
                base.suffix = self._parse_suffix()
            elif c == '%':
                if self.pos + 1 < len(self.s) and self.s[self.pos + 1] == '>':
                    break
                self._advance()
                base.synfeats = self._parse_features()
            elif c == '[':
                base.type_params = self._parse_type_params()
            else:
                break
            
        if isinstance(base, _PendingOutSynfeat):
            return process_out_synfeat_connective(
                base.antecedent,
                base.new_synfeats,
                base.type_params,
            )
        
        return base
    
    def _parse_exponent(self) -> int:
        start = self.pos
        token = self._consume_while(lambda ch: ch.isdigit() or ch.lower() == 'n')
        
        if not token:
            raise self._error(f"Expected exponent at pos {start}")
        
        if token.lower() == 'n':
            return -1
        
        if not token.isdigit():
            raise self._error(f"Expected numeric exponent or 'n' at pos {start}")
        
        return int(token)
    
    def _parse_suffix(self) -> str:
        start = self.pos
        suffix = self._consume_while(str.isalpha)
        
        if not suffix:
            raise self._error(f"Expected suffix at pos {start}")
        
        return suffix
    
    def _parse_features(self) -> SyntacticFeatures:
        feat_map: dict[str, str] = {}
        while self.pos < len(self.s) and self.s[self.pos] not in self.FEAT_STOP:
            raw = self._consume_while(lambda ch: ch not in self.FEAT_STOP)
            
            if raw:
                feat_val = raw.lower()
                feat_name = lookup_feature_name(feat_val)
                
                if feat_name is None:
                    raise self._error(f"Unknown syntactic feature value {raw!r} at pos {self.pos}")
                
                feat_map[feat_name] = feat_val
                    
            if self._peek() == ',':
                self._advance()
                
        return SyntacticFeatures(feature_map=feat_map)
    
    def _parse_type_params(self) -> list[SemType]:
        self._expect('[')
        
        first = self._parse_type()
        if first is None:
            raise self._error("NIL is not allowed in type parameters.")
        params: list[SemType] = [first]
        
        while self._peek() == ';':
            self._advance()
            param = self._parse_type()
            if param is None:
                raise self._error("NIL is not allowed in type parameters.")
            params.append(param)
        self._expect(']')
        
        return params
    
# ==================================================
# Variable exponent expansion
# ==================================================
    
# None is a valid value for fields like suffix, synfeats
# Hence, a unique sentinel is created so it's never equal to anything else
_UNSET = object() 

def copy_semtype(
    st: SemType | None,
    *,
    c_domain=_UNSET,
    c_range=_UNSET,
    c_ex=_UNSET,
    c_suffix=_UNSET,
    c_types=_UNSET,
    c_synfeats=_UNSET,
    c_type_params=_UNSET,
    c_connective=_UNSET,
) -> SemType | None:
    """Make a new semtype identical to the given type, optionally overriding specific fields.

    Override keyword arguments (c_*) follow the sentinel pattern: if not
    supplied, the source semtype's value is used.  This mirrors the Lisp
    :null sentinel, where omitting a keyword means "keep the original".
    Synfeats are always deep-copied to avoid shared mutable state.
    """
    if st is None:
        return None
    
    ex = c_ex if c_ex is not _UNSET else st.ex
    suffix = c_suffix if c_suffix is not _UNSET else st.suffix
    connective = c_connective if c_connective is not _UNSET else st.connective
    synfeats = c_synfeats if c_synfeats is not _UNSET else (st.synfeats.copy() if st.synfeats else DEFAULT_SYNTACTIC_FEATURES.copy())
    type_params = c_type_params if c_type_params is not _UNSET else [copy_semtype(tp) for tp in st.type_params]
    
    if isinstance(st, AtomicType):
        return AtomicType(
            name=st.name,
            ex=ex,
            suffix=suffix,
            synfeats=synfeats,
            type_params=type_params,
            connective=connective,
        )
    
    if isinstance(st, OptionalType):
        types = c_types if c_types is not _UNSET else [copy_semtype(t) for t in st.types]
        return OptionalType(
            types=types or [],
            ex=ex,
            suffix=suffix,
            synfeats=synfeats,
            type_params=type_params,
            connective=connective,
        )
    
    domain = c_domain if c_domain is not _UNSET else copy_semtype(st.domain)
    range_ = c_range if c_range is not _UNSET else copy_semtype(st.range)
    return SemType(
        connective=connective,
        domain=domain,
        range=range_,
        ex=ex,
        suffix=suffix,
        synfeats=synfeats,
        type_params=type_params,
    )

def _binarize_options(options: list[SemType | None]) -> OptionalType:
    """Build a right-leaning binary tree: [A, B, C, D] -> {A|{B|{C|D}}}"""
    if len(options) <= 2:
        return OptionalType(types=options)
    return OptionalType(types=[options[0], _binarize_options(options[1:])])

def _expand_exponent(st: SemType) -> SemType | None:
    """Expand ^n into a chain of optionals: A^n -> {None|{A^1|{A^2|A^3}}}"""
    if st.ex != -1: # no ^n exponent, nothing to expand
        return st
    
    options = []
    for exp in range(0, SEMTYPE_MAX_EXPONENT + 1):
        if exp == 0:
            options.append(None)
        else:
            options.append(copy_semtype(st, c_ex=exp))
    return _binarize_options(options)

def expand_variable_exponents(st: SemType | None) -> SemType | None:
    """Recursively expand all ^n exponents in the tree (bottom-up)."""
    if st is None:
        return None
    
    if isinstance(st, OptionalType):
        expanded_types = [expand_variable_exponents(t) for t in st.types]
        result = copy_semtype(st, c_types=expanded_types)
        if result.ex == -1:
            return _expand_exponent(result)
        return result
    
    if isinstance(st, AtomicType):
        if st.ex == -1:
            return _expand_exponent(st)
        return st
    
    new_domain = expand_variable_exponents(st.domain)
    new_range = expand_variable_exponents(st.range)
    new_type_params = [expand_variable_exponents(tp) for tp in st.type_params]
    result = copy_semtype(st, c_domain=new_domain, c_range=new_range, c_type_params=new_type_params)
    
    if result.ex == -1:
        return _expand_exponent(result)
        
    # If original domain had ^n (ex=-1), distribute it
    if (st.domain is not None
            and st.domain.ex == -1
            and isinstance(new_domain, OptionalType)
            and new_domain.ex == 1):
        return _apply_distribution(
            domain=new_domain, 
            range_=new_range,
            ex=result.ex,
            suffix=result.suffix,
            synfeats=result.synfeats,
            type_params=result.type_params,
            connective=result.connective,
        )
    
    return result
    
    
# ==================================================
# Optional type domain distribution
# ==================================================
    
def _apply_distribution(domain, range_, ex, suffix, synfeats, type_params, connective):
    """Build a SemType, distributing optional domains when appropriate.
    
    Called during ^n expansion to push the range into optional domains.
    Four cases:
        
        ex == 0: None (^0 means no type)
        domain is None: range with suffix/synfeats applied
        domain is optional, ex == 1: distribute range into each option
                                     ({A|B}=>C) -> {(A=>C)|(B=>C)}, recursing
                                     so nested optionals with ex=1 keep distributing
        otherwise: generic SemType (domain => range)
        
    Optionals with ex != 1 (e.g. {A|B}^2) are left intact as SemType
    domains w/ ex = 1 optionals only triggers distribution
    """
    
    # Exponent 0 -> None
    if ex == 0:
        return None
    
    # Domain is None -> return range with enclosing SemType's ex/suffix/synfeats applied
    if domain is None:
        if range_ is None:
            return None
        result = copy_semtype(range_)
        result.ex = ex
        result.suffix = suffix
        if synfeats is not None:
            result.synfeats = synfeats.copy()
        return result
    
    # Domain to OptionalType with ex = 1 -> distribute
    if isinstance(domain, OptionalType) and domain.ex == 1:
        new_types = []
        for optional_domain in domain.types:
            sub = _apply_distribution(
                domain=copy_semtype(optional_domain),
                range_=copy_semtype(range_),
                ex=1,
                suffix=suffix,
                synfeats=synfeats.copy() if synfeats else None,
                type_params=[copy_semtype(tp) for tp in type_params] if type_params else [],
                connective=connective,
            )
            new_types.append(sub)
        return OptionalType(types=new_types)
    
    # Normal SemType -> no distribution needed
    sf = synfeats.copy() if synfeats else DEFAULT_SYNTACTIC_FEATURES.copy()
    tp = list(type_params) if type_params else []
    return SemType(
        connective=connective,
        domain=domain,
        range=range_,
        ex=ex,
        suffix=suffix,
        synfeats=sf,
        type_params=tp
    ) 
    
# ==================================================
# Exponent unrolling (for matching)
# ==================================================
    
def unroll_exponent_step(st: SemType | None) -> SemType | None:
    """
    Undo one layer of exponent compression.
    
    This rewrites a SemType with exponent structure into an equivalent form with
    one exponent layer made explicit as a function type. For example, ``A^4``
    becomes ``(A => A^3)``, and ``(A^3 => B)`` becomes ``(A => (A^2 => B))``.
    
    Args:
        st: The semantic type to normalize
        
    Returns:
        A SemType with one exponent layer unrolled, or ``st`` unchanged when no
        unrolling is needed.
    """
    if st is None:
        return None
    
    # Top-level exponent > 1: A^4 -> (A => A^3).
    # Move syntactic and type-param info to the domain and range.
    if st.ex > 1:
        new_domain = copy_semtype(st, c_ex=1)
        new_range = copy_semtype(st, c_ex=st.ex - 1)
        return SemType(
            connective='=>',
            domain=new_domain,
            range=new_range,
        )
    
    # Domain exponent > 1: (A^3 => B^2) -> (A => (A^2 => B^2)).
    # Retain all syntactic and type-param info at the top level; just move one argument out.
    if (
        not isinstance(st, AtomicType)
        and not isinstance(st, OptionalType)
        and st.domain is not None
        and st.domain.ex > 1
    ):
        new_domain = copy_semtype(st.domain, c_ex=1)
        new_range = SemType(
            connective='=>',
            domain=copy_semtype(st.domain, c_ex=st.domain.ex - 1),
            range=copy_semtype(st.range),
        )
        return copy_semtype(st, c_domain=new_domain, c_range=new_range, c_connective='=>')
    
    return st
    

# ==================================================
# Public API
# ==================================================

def process_out_synfeat_connective(
    base_semtype: SemType | None,
    new_synfeats: SyntacticFeatures,
    type_params: Sequence[SemType] | None = None,
) -> OptionalType | None:
    """
    Process out the special synfeat connective ``%>``.

    The ``%>`` shorthand assumes that the antecedent and consequent semantic
    types match except for the explicit synfeat changes listed in the
    consequent.  We convert ``A%>S`` into ``{a1>>a1%S | {a2>>a2%S | {...}}}``
    for the flattened alternatives a1, a2, ... of A.  This ensures that after
    applying this rule the semantic type stays the same even if the original
    type had many alternatives — we do not want all antecedent alternatives
    to be possible in the consequent for each antecedent alternative.

    Steps:
        1. Flatten out the options of the antecedent.
        For each option:
            2. Make a copy.
            3. Overwrite the synfeats of the copy with the new synfeats.
            4. Create the new type with the base as antecedent and copy as consequent.
        Then:
            5. Merge into a single optional type.
            6. Binarize.
    """
    # 1. Flatten out the options.
    flat_base = flatten_options(base_semtype)
    if flat_base is None:
        return None

    copied_type_params = [copy_semtype(tp) for tp in (type_params or [])]
    new_types: list[SemType | None] = []

    for st in flat_base.types:
        if st is None:
            continue

        # 2. Make a copy; 3. Overwrite synfeats with new synfeats.
        consequent = copy_semtype(
            st,
            c_synfeats=DEFAULT_SYNTACTIC_FEATURES.copy(),
        )
        consequent.synfeats.update_syntactic_features(new_synfeats)
        
        # 4. Create new type with base as antecedent and copy as consequent.
        new_types.append(
            SemType(
                connective=">>",
                domain=copy_semtype(st),
                range=consequent,
                type_params=[copy_semtype(tp) for tp in copied_type_params],
                synfeats=DEFAULT_SYNTACTIC_FEATURES.copy()
            )
        )

    if not new_types:
        return None

    # 5. Merge; 6. Binarize.
    return binarize_flat_options(new_optional_semtype(new_types))
        
        

def str2semtype(s: str, *, extended: bool = False) -> SemType | None:
    """
    Parse a string into a SemType object using the recursive descent parser.

    Strings must be of the form ``([domain][connective][range])`` or a single
    atom, where domain and range are valid strings of the same form.
    Suffixes are supported after ``_`` (e.g. ``_V``).
    Comma-separated syntactic features are supported after ``%`` (e.g. ``%T,LEX``).
    Exponents are supported after ``^`` (e.g. ``^2`` or ``^n``).
    Exponents must occur after any suffixes and syntactic features.

    When ``extended=True``, also accept the Lisp extended-parse cases: PARG,
    quote symbols (``"``), lex macros (QT-ATTR, SUB, ...), macro-hole
    variables (*H, *P, ...), and macro transition types (QT-ATTR1, SUB1, ...).
    """
    stripped = s.strip()
    if not stripped:
        raise SemTypeParseError("Empty semtype string", pos=0, input_str=s)
    
    if extended:
        upper = stripped.upper()
        
        if upper in _MACRO_EXTENSION_ATOMS:
            return AtomicType(name=upper)
        
        parsed = SemTypeParser(
            upper,
            allow_extended_atoms=True,
        ).parse()
        
    else:
        parsed = SemTypeParser(stripped).parse()
        
    expanded = expand_variable_exponents(parsed)
    return expanded

def new_optional_semtype(options: Sequence[SemType | None]) -> OptionalType:
    """Create an optional semtype from a list of options.

    Optional semtypes have no domain, range, exponent, suffix, type parameters,
    or synfeats at the top level — these must all be propagated into the
    individual options.  Externally, optional types may carry exponents, but
    those are expanded out into option realizations during parsing.
    """
    return OptionalType(types=list(options))

def flatten_type_params(st: SemType) -> SemType | OptionalType:
    """
    Flatten the type parameters of a semtype into explicit alternatives.
    
    If any type parameter has multiple flattened possibilities, this returns an
    OptionalType containing one copy of ``st`` for each cartesian-product
    combination of type-parameter choices. If there is only one combination,
    the single semtype is returned directly.
    """
    choice_lists: list[list[SemType | None]] = []
    
    for tp in st.type_params:
        flat_tp = flatten_options(tp)
        if flat_tp is None:
            raise ValueError("type_params must flatten to one or more semtypes")
        choice_lists.append(list(flat_tp.types))
        
    all_choices = list(product(*choice_lists))
    new_options = [
        copy_semtype(st, c_type_params=list(choice))
        for choice in all_choices
    ]
    
    if len(new_options) == 1:
        return new_options[0]
    return new_optional_semtype(new_options)
        
def flatten_options(raw_st: SemType | None) -> OptionalType | None:
    """
    Flatten a semtype so that all options and concrete exponents are represented
    with a single top-level OptionalType.
    
    This always returns an OptionalType when a non-empty result exists, even if
    there is only one option. Returns None when the flattened semtype is empty,
    for example for exponent 0.
    """
    # Remove top-level exponent.
    st = unroll_exponent_step(raw_st)
    if st is None:
        return None
    
    # Flatten type-params if present.
    if st.type_params:
        st = flatten_type_params(st)
        
    # Concrete exponent=0 type, return None.
    if st.ex == 0:
        return None
    
    # Optional type: recurse on each option and flatten all into a single optional.
    if isinstance(st, OptionalType):
        new_options: list[SemType | None] = []
        for opt in st.types:
            flat_opt = flatten_options(opt)
            if flat_opt is not None:
                new_options.extend(flat_opt.types)
        return new_optional_semtype(new_options) if new_options else None
    
    # Atomic type: wrap a copy in a single-element optional.
    if isinstance(st, AtomicType):
        return new_optional_semtype([copy_semtype(st)])
        
    # Non-atomic, non-optional: recurse into domain and range, then generate
    # an optional of all (domain, range) combinations.
    flat_dom = flatten_options(st.domain)
    flat_ran = flatten_options(st.range)
    
    if flat_dom is None:
        new_options = list(flat_ran.types) if flat_ran is not None else []
    elif flat_ran is None:
        new_options = list(flat_dom.types)
    else:
        new_options = [
            copy_semtype(st, c_domain=cur_dom, c_range=cur_ran)
            for cur_dom in flat_dom.types
            for cur_ran in flat_ran.types
        ]
    
    return new_optional_semtype(new_options) if new_options else None

def binarize_flat_options(st: OptionalType) -> OptionalType:
    """
    Convert a flat optional type into a right-leaning binary tree of options.
    """
    return _binarize_options(list(st.types))

def semtype_equal(s1: SemType | None, s2: SemType | None) -> bool:
    """
    Determine whether two semtypes are exactly equivalent.
    
    Unlike ``semtype_match``, equality is exact: syntactic features must match
    exactly, options are compared as sets ignoring order, and duplicate
    flattened branches are ignored.
    """
    
    def set_no_option_equal(
        set1: Sequence[SemType | None],
        set2: Sequence[SemType | None],
    ) -> bool:
        """Check equality of two semtype lists, ignoring order."""
        return (
            len(set1) == len(set2)
            and all(
                any(no_option_equal(set1_elem, set2_elem) for set2_elem in set2)
                for set1_elem in set1
            )
        )
    
    def same_metadata(t1: SemType, t2: SemType) -> bool:
        """Check suffix, synfeats, and type-params equality between two semtypes."""
        return (
            t1.suffix == t2.suffix
            and t1.synfeats.equal(t2.synfeats)
            and set_no_option_equal(t1.type_params, t2.type_params)
        )
    
    def no_option_equal(
        raw_t1: SemType | None,
        raw_t2: SemType | None,
    ) -> bool:
        """Check equality of two semtypes that contain no optional types."""
        # Pull out exponents.
        t1 = unroll_exponent_step(raw_t1)
        t2 = unroll_exponent_step(raw_t2)

        if t1 is None or t2 is None:
            return t1 is None and t2 is None

        if isinstance(t1, OptionalType) or isinstance(t2, OptionalType):
            raise ValueError("no_option_equal does not allow OptionalType inputs")

        # Base cases. One of the arguments is atomic.
        t1_is_atomic = isinstance(t1, AtomicType)
        t2_is_atomic = isinstance(t2, AtomicType)

        if t1_is_atomic != t2_is_atomic:
            return False

        # Atomic (only has domain).
        if t1_is_atomic:
            return (
                t1.name == t2.name
                and same_metadata(t1, t2)
            )

        # Non-atomic (has domain and range).
        return (
            no_option_equal(t1.domain, t2.domain)
            and no_option_equal(t1.range, t2.range)
            and t1.connective == t2.connective
            and same_metadata(t1, t2)
        )

    def dedupe_flat_options(
        options: Sequence[SemType | None],
    ) -> list[SemType | None]:
        """Remove duplicate options using semtype equality."""
        unique: list[SemType | None] = []
        for option in options:
            if not any(no_option_equal(option, existing) for existing in unique):
                unique.append(option)
        return unique

    # Flatten both sides and deduplicate, then check set equality.
    if s1 is None or s2 is None:
        return s1 is None and s2 is None
    
    flat_s1 = flatten_options(s1)
    flat_s2 = flatten_options(s2)
    
    flat_types_1 = dedupe_flat_options(list(flat_s1.types) if flat_s1 is not None else [])
    flat_types_2 = dedupe_flat_options(list(flat_s2.types) if flat_s2 is not None else [])
    
    return set_no_option_equal(flat_types_1, flat_types_2)

def _synfeat_diff_for_right_arrow(st: SemType) -> tuple[SyntacticFeatures, SyntacticFeatures]:
    """
    Compute the synfeat difference between domain and range for a ``>>`` semtype.

    Keeps only features that are specified on *both* domain and range and whose
    values differ.  Features that agree or are only present on one side are
    removed from both return values.

    Returns:
        A pair ``(domain_diff_feats, range_diff_feats)`` where:
            1. domain synfeats where the range value is specified and differs.
            2. range synfeats where the domain value is specified and differs.
    """
    domain_sf = (st.domain.synfeats if st.domain and st.domain.synfeats else SyntacticFeatures()).copy()
    range_sf = (st.range.synfeats if st.range and st.range.synfeats else SyntacticFeatures()).copy()
    
    keys = set(domain_sf.get_feature_names()) | set(range_sf.get_feature_names())
    for key in keys:
        dval = domain_sf.feature_value(key)
        rval = range_sf.feature_value(key)
        if not (dval is not None and rval is not None and dval != rval):
            domain_sf.del_feature_value(key)
            range_sf.del_feature_value(key)
            
    return domain_sf, range_sf

def _right_arrow_synfeats_match(x_st: SemType, y_st: SemType) -> bool:
    """
    Return whether two ``>>`` SemTypes have the same explicit domain-to-range
    syntactic-feature change.

    If a synfeat switch is specified on one side, it must be specified on both,
    because unspecified features under ``>>`` are propagated from the antecedent
    and will never trigger a switch.  This function compares only the features
    that differ between domain and range on each side, ignoring everything else.
    """
    x_domain_diff, x_range_diff = _synfeat_diff_for_right_arrow(x_st)
    y_domain_diff, y_range_diff = _synfeat_diff_for_right_arrow(y_st)
    return x_domain_diff.equal(y_domain_diff) and x_range_diff.equal(y_range_diff)

def semtype_match(
    pattern: SemType | None,
    value: SemType | None,
    ignore_exp: bool | str | None = None,
) -> bool:
    """
    Returns whether ``value`` satisfies the semantic type pattern ``pattern``.
    
    Rules:
        - ``None`` matches only ``None``.
        - If either side is an ``OptionalType``, the match succeeds when any
          pattern/value option pair matches.
        - If both sides specify a suffix, the suffixes must be equal.
        - Syntactic features are matched with ``pattern`` treated as the constraint
          and ``value`` as the candidate.
        - Atomic types match only when both are atomic and have the same name.
        - Non-atomic types match only when their domains, ranges, and connectives match recursively.
        - For ``>>`` types, the explicit syntactic-feature change from domain to range must agree
          on both sides.
          
    Args:
        pattern: The semantic type pattern to check against.
        value: The candidate semantic type being tested.
        ignore_exp: 
            Controls exponent-sensitive matching.
            - ``None`` or ``False``: unroll one exponent step before matching.
            - ``True``: ignore exponent differences during ordinary recursive matching
                        through normal semtype structure.
            - ``'r'``: like ``True``, and also preserve exponent-ignoring behavior when
                       recursing through ``OptionalType`` branches.
                       
            In other words, ``'r'`` only differs from ``True`` for recursion through
            optionals; for ordinary domain/range recursion, ``True`` already propagates.
            
    Returns:
        ``True`` if ``value`` matches ``pattern``, otherwise ``False``.
    """
    
    # Handles the case when expanded form (specifically ^0) produces None
    if pattern is None or value is None:
        return pattern is None and value is None
    
    # Expand out one level of exponents if relevant.
    x = pattern if ignore_exp else unroll_exponent_step(pattern)
    y = value if ignore_exp else unroll_exponent_step(value)

    if x is None or y is None:
        return x is None and y is None

    # Now we can assume exponent = 1 for the domain and at the top level.
    rec_ignore_exp = 'r' if ignore_exp == 'r' else None

    # One is optional: make option lists and see if any pair of options work.
    if isinstance(x, OptionalType) or isinstance(y, OptionalType):
        x_options = x.types if isinstance(x, OptionalType) else [x]
        y_options = y.types if isinstance(y, OptionalType) else [y]
        
        for x_option in x_options:
            for y_option in y_options:
                if semtype_match(x_option, y_option, ignore_exp=rec_ignore_exp):
                    return True
        return False
    
    # Suffixes: only constrain when both are specified
    if x.suffix is not None and y.suffix is not None and x.suffix != y.suffix:
        return False
    
    x_sf = x.synfeats if x.synfeats is not None else SyntacticFeatures()
    y_sf = y.synfeats if y.synfeats is not None else SyntacticFeatures()
    if not y_sf.match(x_sf):
        return False
    
    # Atomic case
    if isinstance(x, AtomicType) or isinstance(y, AtomicType):
        return (
            isinstance(x, AtomicType)
            and isinstance(y, AtomicType)
            and x.name == y.name
        )
    
    # Structured case
    if not semtype_match(x.domain, y.domain, ignore_exp=ignore_exp):
        return False
    if not semtype_match(x.range, y.range, ignore_exp=ignore_exp):
        return False
    if x.connective != y.connective:
        return False
    
    # Special >> constraint: synfeat differences between domain/range must agree
    if x.connective == '>>' and not _right_arrow_synfeats_match(x, y):
        return False
    
    return True