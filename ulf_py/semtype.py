from __future__ import annotations
from dataclasses import dataclass, field
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
    suffix: str | None = None
    type_params: list['SemType'] = field(default_factory=list)
    synfeats: SyntacticFeatures = field(default_factory=lambda: DEFAULT_SYNTACTIC_FEATURES.copy())
    
    
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
    
    def __init__(self, s: str):
        self.s = s
        self.pos = 0
        
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
    
    def parse(self) -> SemType | None:
        result = self._parse_type()
        if self.pos != len(self.s):
            raise self._error(
                f"Trailing chars at pos {self.pos}: {self.s[self.pos:]!r}"
            )
        
        return result
        
    def _parse_type(self) -> SemType | None:
        return self._parse_modifiers(self._parse_primary())
    
    def _parse_primary(self) -> SemType | None:
        c = self._peek()
        if c == '(':
            return self._parse_function_type()
        
        if c == '{':
            return self._parse_optional_type()
        
        if c is not None and c in self.ATOM_CHARS:
            return self._parse_atom()
        
        raise self._error(f"Unexpected {c!r} at pos {self.pos}")
        
    def _parse_atom(self) -> AtomicType | None:
        token = self._consume_while(lambda ch: ch in self.ATOM_CHARS)
        
        if not token:
            raise self._error(f"Expected atom at pos {self.pos}")
        
        return None if token.upper() == 'NIL' else AtomicType(name=token)
    
    def _parse_function_type(self) -> SemType:
        self._expect('(')
        domain = self._parse_type()
        conn = self._parse_connective()
        range_ = self._parse_type()
        self._expect(')')
        
        return SemType(connective=conn, domain=domain, range=range_)
    
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
    
    def _parse_modifiers(self, base: SemType | None) -> SemType | None:
        if base is None:
            return None
        
        while True:
            c = self._peek()
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
    """Deep copy a SemType, optionally overriding specific fields (if c_* provided)."""
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
    
    # Top-level exponent > 1: A^4 -> (A => A^3)
    if st.ex > 1:
        new_domain = copy_semtype(st, c_ex=1)
        new_range = copy_semtype(st, c_ex=st.ex - 1)
        return SemType(
            connective='=>',
            domain=new_domain,
            range=new_range,
        )
    
    # Structured type whose domain exponent > 1
    # (A^3 => B^2) -> (A => (A^2 => B^2))
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

def str2semtype(s: str) -> SemType | None:
    """Parse a string into a SemType object using the recursive descent parser."""
    parsed = SemTypeParser(s).parse()
    expanded = expand_variable_exponents(parsed)
    return expanded

def new_optional_semtype(options: Sequence[SemType | None]) -> OptionalType:
    """Create an optional type from a list of type options."""
    return OptionalType(types=list(options))

def _synfeat_diff_for_right_arrow(st: SemType) -> tuple[SyntacticFeatures, SyntacticFeatures]:
    """
    Keep only features that are specified on both domain and range and differ.
    
    Returns:
        (domain_diff_feats, range_diff_feats)
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
    
    This ignores the unchanged features and features not specified on both sides, and
    compares only the differing feature sets extracted from each SemType.
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
    
    x = pattern if ignore_exp else unroll_exponent_step(pattern)
    y = value if ignore_exp else unroll_exponent_step(value)
    
    if x is None or y is None:
        return x is None and y is None
    
    rec_ignore_exp = 'r' if ignore_exp == 'r' else None
    
    # Optional matching: any compatible pair works
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