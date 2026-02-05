from dataclasses import dataclass
from typing import Any
from collections.abc import Callable

# TODO: use class to represent argument and results types instead of Any wherever possible
# Combinator Function signature:
# (base_value, operator_value, argument_value, consequent_value, opr_semtype, arg_semtype) -> result_value
CombinatorFn = Callable[[Any, Any, Any, Any, Any | None, Any | None], Any]

# TODO: get_combinator make is a member function of the following class
def default_combinator_fn(
    base: Any,
    opr: Any,
    arg: Any,
    csq: Any,
    opr_semtype: Any | None = None,
    arg_semtype: Any | None = None,
) -> Any:
    """
    Default feature combinator function simply uses the base feature
    """
    return base


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    name: str
    possible_values: tuple[Any, ...]
    default_value: Any
    combinator_fn: CombinatorFn | None = None
    
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

FEATURE_DEFINITIONS_DICT: dict[str, FeatureDefinition] = {}

SYNTACTIC_FEATURE_VALUES: dict[Any, str] = {}

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