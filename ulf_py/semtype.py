from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Any, Sequence
from .syntactic_features import SyntacticFeatures, DEFAULT_SYNTACTIC_FEATURES, lookup_feature_name
from .feature_definition_declarations import FEATURE_DEFINITIONS_DICT
import json
import re


def _normalize_whitespace(s: str) -> str:
    """Collapse all whitespace sequences to a single space."""
    return re.sub(r'\s+', ' ', s)


def _normalize_synfeats_order(s: str) -> str:
    """Sort syntactic feature values alphabetically appearing in the string after `%`"""
    def _sort_match(m):
        vals = m.group(1).split(',')
        return '%' + ','.join(sorted(vals))
    return re.sub(r'%([A-Z!][A-Z0-9!,]*)', _sort_match, s)


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
CONNECTIVE_LIST = tuple(Connective.__args__)

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
        
def json_to_semtype(obj: dict) -> SemType | None:
    """Convert a structured JSON dict (from lisp recorder) into a SemType."""
    if obj is None:
        return None
    typ = obj['type']
    ex = obj.get('ex', 1)
    suffix = obj.get('suffix')
    synfeats_raw = obj.get('synfeats')
    if synfeats_raw:
        order = {name: i for i, name in enumerate(FEATURE_DEFINITIONS_DICT)}
        sorted_items = sorted(
            ((k.upper(), _strip_package(v)) for k, v in synfeats_raw.items()),
            key=lambda x: order.get(x[0], 999),
        )
        synfeats = SyntacticFeatures(feature_map=dict(sorted_items))
    else:
        synfeats = DEFAULT_SYNTACTIC_FEATURES.copy()
    type_params_raw = obj.get('type_params')
    type_params = [json_to_semtype(tp) for tp in type_params_raw] if type_params_raw else []
    if typ == 'atomic':
        return AtomicType(
            name=obj['name'], ex=ex, suffix=suffix, synfeats=synfeats, type_params=type_params,
        )
    elif typ == 'function':
        return SemType(
            connective=obj['connective'],
            domain=json_to_semtype(obj['domain']),
            range=json_to_semtype(obj['range']),
            ex=ex, suffix=suffix, synfeats=synfeats, type_params=type_params,
        )
    elif typ == 'optional':
        return OptionalType(
            types=[json_to_semtype(t) for t in obj['types']],
            ex=ex, suffix=suffix, synfeats=synfeats, type_params=type_params,
        )
    else:
        raise ValueError(f"Unknown semtype type in JSON: {typ!r}")
    
    
# ==================================================
# Public API
# ==================================================

def str2semtype(s: str) -> SemType:
    """Parse a string into a SemType object"""
    s_upper = s.upper()
    normalized = _normalize_synfeats_order(s_upper)
    entry = ULF_MAPS.get('str2semtype', {}).get(normalized)
    if entry is None:
        entry = ULF_MAPS.get('str2semtype', {}).get(s_upper)
    if entry is None:
        entry = ULF_MAPS.get('str2semtype', {}).get(s)
    if entry is None or isinstance(entry, str):
        return None
    structured = entry.get('structured')
    if structured is None:
        return None
    return json_to_semtype(structured)

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