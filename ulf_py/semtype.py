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
    
CONNECTIVES = ('=>', '>>', "%>")
Connective = Literal['=>', '>>', "%>"] # Keep in sync with CONNECTIVES

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
    types: list[SemType] = field(default_factory=list)      # {A | B | C}
    
    
# ==================================================
# semtype2str - reconstruct the string from a SemType tree
# ==================================================

def _strip_package(val: str | None) -> str | None:
    """Strip Lisp package prefix: 'ulf-lib::lex' -> 'lex'."""
    if val is None:
        return None
    if '::' in val:
        return val.rsplit('::', 1)[1]
    return val

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
    
    
def _type_params_str(tp: list['SemType'] | None) -> str:
    if not tp:
        return ""
    return "[" + ",".join(semtype2str(t) for t in tp) + "]"


def _modifiers_str(st: SemType) -> str:
    """
    Build the modifier suffix string for a SemType.
    
    Order: exponent (^n) -> suffix (_V) -> synfeats (%T,LEX) -> type params ([...]).
    """
    parts = []
    if st.ex != 1:
        parts.append(f"^{'n' if st.ex == -1 else st.ex}")
    if st.suffix:
        parts.append(f"_{st.suffix}")
    parts.append(_synfeats_str(st.synfeats))
    parts.append(_type_params_str(st.type_params))
    return "".join(parts)


def semtype2str(st: SemType | None) -> str | None:
    """Convert a SemType tree back to its string representation."""
    if st is None:
        return None
    if isinstance(st, OptionalType):
        parts = [semtype2str(t) for t in st.types if t is not None]
        if not parts:
            return None
        inner = "|".join(parts)
        base = "{" + inner + "}"
    elif isinstance(st, AtomicType):
        base = st.name
    else:
        d = semtype2str(st.domain)
        r = semtype2str(st.range)
        if d is None or r is None:
            return None
        base = f"({d}{st.connective}{r})"
    return base + _modifiers_str(st)
    

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
    
    def parse(self) -> SemType:
        result = self._parse_type()
        if self.pos != len(self.s):
            raise self._error(
                f"Trailing chars at pos {self.pos}: {self.s[self.pos:]!r}"
            )
        
        return result
        
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
        
    def _parse_type(self) -> SemType:
        return self._parse_modifiers(self._parse_primary())
    
    def _parse_primary(self) -> SemType:
        c = self._peek()
        if c == '(':
            return self._parse_function_type()
        
        if c == '{':
            return self._parse_optional_type()
        
        if c is not None and c in self.ATOM_CHARS:
            return self._parse_atom()
        
        raise self._error(f"Unexpected {c!r} at pos {self.pos}")
        
    def _parse_atom(self) -> AtomicType:
        start = self.pos
        while self.pos < len(self.s) and self.s[self.pos] in self.ATOM_CHARS:
            self.pos += 1
        if self.pos == start:
            raise self._error(f"Expected atom at pos {self.pos}")
        
        return AtomicType(name=self.s[start:self.pos])
    
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
        if self.pos + 1 >= len(self.s):
            raise self._error(f"Expected connective at pos {self.pos}")
        two = self.s[self.pos:self.pos+2]
        
        if two in CONNECTIVES:
            self.pos += 2
            return two
        
        raise self._error(f"Expected connective at pos {self.pos}, got {two!r}")
    
    def _parse_modifiers(self, base: SemType) -> SemType:
        while self.pos < len(self.s):
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
        while self.pos < len(self.s) and self.s[self.pos].isalnum():
            self.pos += 1
        token = self.s[start:self.pos]
        
        if not token:
            raise self._error(f"Expected exponent at pos {start}")
        
        return -1 if token.lower() == 'n' else int(token)
    
    def _parse_suffix(self) -> str:
        start = self.pos
        while self.pos < len(self.s) and self.s[self.pos].isalpha():
            self.pos += 1
        suffix = self.s[start:self.pos]
        
        if not suffix:
            raise self._error(f"Expected suffix at pos {start}")
        
        return suffix
    
    def _parse_features(self) -> SyntacticFeatures:
        feat_map: dict[str, str] = {}
        while self.pos < len(self.s) and self.s[self.pos] not in self.FEAT_STOP:
            start = self.pos
            while self.pos < len(self.s) and self.s[self.pos] not in self.FEAT_STOP:
                self.pos += 1
            raw = self.s[start: self.pos]
            
            if raw:
                feat_val = raw.lower()
                feat_name = lookup_feature_name(feat_val)
                
                if feat_name is not None:
                    feat_map[feat_name] = feat_val
                    
            if self.pos < len(self.s) and self.s[self.pos] == ',':
                self.pos += 1
                
        return SyntacticFeatures(feature_map=feat_map)
    
    def _parse_type_params(self) -> list[SemType]:
        self._expect('[')
        params = [self._parse_type()]
        while self._peek() == ',':
            self._advance()
            params.append(self._parse_type())
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

def _binarize_options(options: list[SemType]) -> OptionalType:
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
            range=new_range,
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
    
def _apply_distribution(domain, range, ex, suffix, synfeats, type_params, connective):
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
        if range is None:
            return None
        result = copy_semtype(range)
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
                range=copy_semtype(range),
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
        range=range,
        ex=ex,
        suffix=suffix,
        synfeats=sf,
        type_params=tp
    ) 
    

# ==================================================
# Public API
# ==================================================

def str2semtype(s: str) -> SemType | None:
    """Parse a string into a SemType object using the recursive descent parser."""
    return SemTypeParser(s).parse()

def new_optional_semtype(options: Sequence[SemType]) -> OptionalType:
    """Create an optional type from a list of type options."""
    return OptionalType(types=list(options))

_match_debug_count = 0

def semtype_match(pattern: SemType, value: SemType) -> bool:
    global _match_debug_count
    if pattern is None or value is None:
        return False
    from .lisp_keys import make_lisp_lookup_key
    pattern_str = semtype2str(pattern)
    value_str = semtype2str(value)
    if pattern_str is None or value_str is None:
        return False
    key = make_lisp_lookup_key([pattern_str, value_str])
    key = _normalize_whitespace(_normalize_synfeats_order(key))
    entry = ULF_MAPS.get('semtype_match', {}).get(key)
    
    if _match_debug_count < 3 and entry is None:
        print(f"  MATCH MISS: pattern={pattern_str[:80]}")
        print(f"              value={value_str[:80]}")
        _match_debug_count += 1
    
    if entry is None:
        return False
    return entry is True or entry == "true"