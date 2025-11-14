from dataclasses import dataclass, field

class SyntacticFeatures:
    """Represents syntactic features with a feature map"""
    
    def __init__(self, feature_dict: dict[str, str] | None = None):
        """
        Initializes with a dictionary mapping feature names to values.
        Example: {"TENSE": "!t", "AUXILIARY": "!x"}
        Some features may have None as value - these should be filtered out.
        Values can be: strings like "!t", booleans like True, or None
        """
        self.feature_dict = feature_dict or {}
        
    
    def __bool__(self):
        # Only consider features with non-None values
        return any(v is not None for v in self.feature_dict.values())
    
    
    def __len__(self):
        # Only count features with non-None values
        return sum(1 for v in self.feature_dict.values() if v is not None)
    
    
    def __str__(self):
        """
        Convert to output format: !T,!PF,!PG,!X or LEX
        Only include features with non-None values
        """
        
        if not self.feature_dict:
            return ""
            
        # Extract features in the canonical order, filtering out None values
        features = []
        for k, v in self.feature_dict.items():
            # Skip None values
            if v is None:
                continue
            
            # Handle boolean True - use the key itself
            if isinstance(v, bool) and v:
                key_abbrev = self._key_to_abbrev(k)
                features.append(key_abbrev)
            #Handle string values
            elif isinstance(v, str):
                features.append(v.upper())
                
        # TODO: add rule based sorting in the future instead
        features = sorted(features)
        
        return ",".join(features)
            
            
    @staticmethod
    def _key_to_abbrev(key: str) -> str:
        """Convert feature key to its abbreviated form."""
        abbrev_map = {
            'TENSE': 'T',
            'PERFECT': 'PF',
            'PROGRESSIVE': 'PG',
            'PASSIVE': 'PV',
            'PLURALITY': 'PL',
            'AUXILIARY': 'X',
            'LEXICAL': 'LEX'
        }
        return abbrev_map.get(key, key)
    
    
    def __repr__(self):
        return f"SyntacticFeatures({self.feature_dict})"
    
    
DEFAULT_SYNTACTIC_FEATURES = SyntacticFeatures()


@dataclass
class SemType:
    """Base semantic type."""
    connective: str = '=>'
    domain: object = None
    range: object = None
    ex: int = 1
    suffix: str | None = None
    type_params: list['SemType'] = field(default_factory=list)
    synfeats: SyntacticFeatures = field(default_factory=lambda: SyntacticFeatures())
    
    
@dataclass
class AtomicType(SemType):
    """Atomic semantic type."""
    pass


@dataclass
class OptionalType(SemType):
    """Optional type {A|B}"""
    types: list[SemType] = field(default_factory=list)
    
    
def semtype_to_str(s: SemType | None) -> str | None:
    """Convert SemType to string representation matching Common Lisp output."""
    if s is None:
        return None
    
    # Exponent
    exponent_str = '' if s.ex == 1 else f"^{s.ex}"
    
    # Syntactic features
    synfeat_parts = []
    if s.suffix:
        synfeat_parts.append(f"_{s.suffix}")
    
    if s.synfeats and len(s.synfeats) > 0:
        synfeat_parts.append(f"%{s.synfeats}")
        
    synfeat_str = ''.join(synfeat_parts)
    
    # Type parameters
    type_params_list = [semtype_to_str(tp) for tp in s.type_params]
    type_params_str = f"[{';'.join(type_params_list)}]"
    
    # Base type
    if isinstance(s, OptionalType):
        # Optional type: {A|B}
        if len(s.types) < 2:
            raise ValueError(f"OptionalType must have exactly 2 types, got {len(s.types)}")
        type1_str = semtype_to_str(s.types[0])
        type2_str = semtype_to_str(s.types[1])
        base = f"{{{type1_str}|{type2_str}}}{exponent_str}"
    elif isinstance(s, AtomicType):
        # Atomic type
        base = f"{s.domain}{synfeat_str}{exponent_str}"
    else:
        domain_str = semtype_to_str(s.domain) if isinstance(s.domain, SemType) else str(s.domain)
        range_str = semtype_to_str(s.range) if isinstance(s.range, SemType) else str(s.range)
        base = f"({domain_str}{s.connective}{range_str}){synfeat_str}{exponent_str}"
        
        
    # Add type parameters
    if type_params_str == "[]":
        return base
    else:
        return f"{base}{type_params_str}"
            
            
if __name__ == "__main__":
    semtype_obj = SemType(domain="D")
    print(semtype_obj)