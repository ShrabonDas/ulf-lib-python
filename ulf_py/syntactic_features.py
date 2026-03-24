from dataclasses import dataclass, field
from typing import Any, Iterable

from .feature_definition_declarations import (
    SYNTACTIC_FEATURE_VALUES,
    FEATURE_DEFINITIONS_DICT,
    get_syntactic_feature_combinator,
)


def lookup_feature_name(feat_value: Any) -> str | None:
    """
    lookup_feature_name("!t") -> "TENSE"
    """
    return SYNTACTIC_FEATURE_VALUES.get(feat_value)


def _norm_name(name: str) -> str:
    return name.upper()


def default_syntactic_feature_value(feat_name: str) -> Any:
    try:
        defn = FEATURE_DEFINITIONS_DICT[_norm_name(feat_name)]
    except KeyError as e:
        raise KeyError(f"No feature definition found for name {feat_name!r}") from e
    return defn.default_value


@dataclass
class SyntacticFeatures:
    """holds feature values for a single type"""
    feature_map: dict[str, Any | None] = field(default_factory=dict)    # e.g. {"TENSE": "t", "LEXICAL": "lex"}
    
    def empty(self) -> bool:
        return all(v is None for v in self.feature_map.values())
    
    def get_feature_names(self) -> list[str]:
        return list(self.feature_map.keys())
    
    def get_feature_values(self) -> list[Any | None]:
        return list(self.feature_map.values())
    
    def to_string(self) -> str:
        return str(self)
    
    def print_verbose(self) -> str:
        parts = []
        for k, v in self.feature_map.items():
            parts.append(f"{k}:{v!r}")
        return "#{" + ",".join(parts) + "}"
    
    def __str__(self) -> str:
        vals = [v for v in self.feature_map.values() if v is not None]
        inner = ",".join(repr(v) for v in vals)
        return "#{" + inner + "}"
    
    def copy(self) -> "SyntacticFeatures":
        return SyntacticFeatures(feature_map=dict(self.feature_map))
    
    def feature_value(self, element: str) -> Any | None:
        """feature_value("TENSE") -> "t" """
        return self.feature_map.get(_norm_name(element))
    
    def equal(self, other: "SyntacticFeatures") -> bool:
        return self.feature_map == other.feature_map
    
    def match(self, pattern: "SyntacticFeatures") -> bool:
        instance = self
        for feat_name, pattern_val in pattern.feature_map.items():
            if pattern_val is None:
                continue
            instance_val = instance.feature_value(feat_name)
            # TODO: this logic can be made more intuitive like we can first check if instance_val is None and continue
            if pattern_val != instance_val:
                if instance_val is not None or pattern_val != default_syntactic_feature_value(feat_name):
                    return False
        return True

    def add_feature_values(self, new_features: Iterable[Any]) -> "SyntacticFeatures":
        for feat_val in new_features:
            feat_name = lookup_feature_name(feat_val)
            if feat_name is None:
                raise KeyError(f"No feature name for feature value {feat_val!r}")
            self.feature_map[_norm_name(feat_name)] = feat_val
        return self

    def add_feature_value(self, new_feature: Any) -> "SyntacticFeatures":
        return self.add_feature_values([new_feature])

    def del_feature_value(self, key: str) -> "SyntacticFeatures":
        self.feature_map.pop(_norm_name(key), None)
        return self

    def update_feature_map(self, new_feature_map: Iterable[tuple[str, Any | None]]) -> "SyntacticFeatures":
        for feat_name, feat_val in new_feature_map:
            self.feature_map[_norm_name(feat_name)] = feat_val
        return self

    def update_syntactic_features(self, new: "SyntacticFeatures") -> "SyntacticFeatures":
        return self.update_feature_map(new.feature_map.items())

    @staticmethod
    def combine_features(
        base: "SyntacticFeatures",
        opr_feats: "SyntacticFeatures",
        arg_feats: "SyntacticFeatures",
        csq_feats: "SyntacticFeatures",
        opr_semtype: Any | None = None,
        arg_semtype: Any | None = None,
    ) -> "SyntacticFeatures":
        feat_names = set(base.get_feature_names()) | set(opr_feats.get_feature_names()) | set(arg_feats.get_feature_names())
        feat_names = set(map(_norm_name, feat_names))

        new_feat_vals: list[tuple[str, Any | None]] = []
        for feat_name in feat_names:
            feat_combinator = get_syntactic_feature_combinator(feat_name)
            combined_val = feat_combinator(
                base.feature_value(feat_name),
                opr_feats.feature_value(feat_name),
                arg_feats.feature_value(feat_name),
                csq_feats.feature_value(feat_name),
                opr_semtype,
                arg_semtype,
            )
            new_feat_vals.append((feat_name, combined_val))

        base.update_feature_map(new_feat_vals)

        csq_specified = [(k, v) for k, v in csq_feats.feature_map.items() if v is not None]
        base.update_feature_map(csq_specified)

        return base

    @staticmethod
    def feature_map_difference(base_feats: "SyntacticFeatures", diff_feats: "SyntacticFeatures") -> "SyntacticFeatures":
        result = base_feats.copy()
        for k in diff_feats.feature_map.keys():
            kk = _norm_name(k)
            if kk in result.feature_map:
                result.feature_map[kk] = None
        return result

    @staticmethod
    def feature_map_union(one_feats: "SyntacticFeatures", two_feats: "SyntacticFeatures") -> "SyntacticFeatures":
        result = one_feats.copy()
        for k, v in two_feats.feature_map.items():
            kk = _norm_name(k)
            if kk not in result.feature_map or result.feature_map[kk] is None:
                result.feature_map[kk] = v
        return result


DEFAULT_SYNTACTIC_FEATURES = SyntacticFeatures(feature_map={})