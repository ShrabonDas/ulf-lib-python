from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

# TODO: use class to represent argument and results types instead of Any wherever possible
# Combinator Function signature:
# (base_value, operator_value, argument_value, consequent_value, opr_semtype, arg_semtype) -> result_value
CombinatorFn = Callable[[Any | None, Any | None, Any | None, Any | None, Any | None, Any | None], Any]

# TODO: get_combinator make is a member function of the following class
def default_combinator_fn(
    base: Any | None,
    opr: Any | None,
    arg: Any | None,
    csq: Any | None,
    opr_semtype: Any | None = None,
    arg_semtype: Any | None = None,
) -> Any:
    """
    Default feature combinator function simply uses the base feature
    """
    return base


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: str                                   # e.g. "TENSE"
    possible_values: tuple[Any, ...]            # e.g. ("t", "!t")
    default_value: Any                          # e.g. "!t"
    combinator_fn: CombinatorFn | None = None   # how to combine during composition
    
    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Must supply a name for the feature definition.")
        else:
            object.__setattr__(self, "name", self.name.upper())
        if not self.possible_values:
            raise ValueError("Must supply possible feature values for the feature.")
        if self.default_value is None:
            raise ValueError("Must supply a default feature value.")
        if self.default_value not in self.possible_values:
            raise ValueError(
                f"default_value {self.default_value!r} must be one of possible values "
                f"{self.possible_values!r} for feature {self.name!r}"
            )
        
        
# ------------------------
# These are populated elsewhere
# ------------------------

FEATURE_DEFINITIONS_DICT: dict[str, FeatureDefinition] = {}     # "TENSE" -> FeatureDefinition(...)

# Given a feature value like "t", this map tells us what feature name it belongs to
SYNTACTIC_FEATURE_VALUES: dict[Any, str] = {}                   # "t" -> "Tense", "!t" -> "TENSE"

def get_combinator(defn: FeatureDefinition) -> CombinatorFn:
    return defn.combinator_fn or default_combinator_fn


def get_syntactic_feature_combinator(name: str) -> CombinatorFn:
    try:
        defn = FEATURE_DEFINITIONS_DICT[name]
    except KeyError:
        raise KeyError(f"No feature definition found for name {name!r}")
    return get_combinator(defn)


def build_value_to_name_table(definitions: list[FeatureDefinition]) -> dict[Any, str]:
    value_to_name: dict[Any, str] = {}
    for defn in definitions:
        for v in defn.possible_values:
            if v in value_to_name:
                raise ValueError(
                    f"Feature values must be globally unique. Duplicate value {v!r} "
                    f"found in {defn.name!r} and {value_to_name[v]!r}"
                )
            value_to_name[v] = defn.name
    return value_to_name