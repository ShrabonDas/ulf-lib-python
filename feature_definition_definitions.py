from typing import Callable, Any

from feature_definition_declarations import (
    FeatureDefinition,
    FEATURE_DEFINITIONS_DICT,
    SYNTACTIC_FEATURE_VALUES,
    build_value_to_name_table,
)

from semtype import (
    SemType, str2semtype, new_optional_semtype, semtype_match
)

from composition import compose_types


PREDICATE_SEMTYPE: SemType = str2semtype("({D|(D=>(S=>2))}^n=>(D=>(S=>2)))")
SENTENCE_SEMTYPE: SemType = str2semtype("(S=>2)")

CombinatorFn = Callable[[Any, Any, Any, Any, SemType | None, SemType | None], Any]


def base_result_pattern_combinator_generator(result_pattern: SemType) -> CombinatorFn:
    def combinator(
        base: Any,
        _opr: Any,
        _arg: Any,
        _csq: Any,
        opr_semtype: SemType | None = None,
        arg_semtype: SemType | None = None,
    ) -> Any:
        if base is None:
            return None
        
        res_semtype = compose_types(opr_semtype, arg_semtype, ignore_synfeats=True)
        if res_semtype is None:
            return None
        
        return base if semtype_match(result_pattern, res_semtype) else None
    
    return combinator

_SENT_OR_PRED_PATTERN = new_optional_semtype([SENTENCE_SEMTYPE, PREDICATE_SEMTYPE])

tense_combinator_fn: CombinatorFn = base_result_pattern_combinator_generator(_SENT_OR_PRED_PATTERN)
auxiliary_combinator_fn: CombinatorFn = base_result_pattern_combinator_generator(_SENT_OR_PRED_PATTERN)
perfect_combinator_fn: CombinatorFn = base_result_pattern_combinator_generator(_SENT_OR_PRED_PATTERN)
progressive_combinator_fn: CombinatorFn = base_result_pattern_combinator_generator(_SENT_OR_PRED_PATTERN)

plurality_combinator_fn: CombinatorFn = base_result_pattern_combinator_generator(PREDICATE_SEMTYPE)
passive_combinator_fn: CombinatorFn = base_result_pattern_combinator_generator(PREDICATE_SEMTYPE)


def lexical_combinator_fn(
    base: Any,
    opr: Any,
    arg: Any,
    csq: Any,
    opr_semtype: SemType | None = None,
    arg_semtype: SemType | None = None,
) -> Any:
    return None


FEATURE_DEFINITIONS: list[FeatureDefinition] = [
    FeatureDefinition(
        name="TENSE",
        combinator_fn=tense_combinator_fn,
        possible_values=("t", "!t"),
        default_value="!t",
    ),
    FeatureDefinition(
        name="AUXILIARY",
        combinator_fn=auxiliary_combinator_fn,
        possible_values=("x", "!x"),
        default_value="!x",
    ),
    FeatureDefinition(
        name="PLURALITY",
        combinator_fn=plurality_combinator_fn,
        possible_values=("pl", "!pl"),
        default_value="!pl",
    ),
    FeatureDefinition(
        name="PERFECT",
        combinator_fn=perfect_combinator_fn,
        possible_values=("pf", "!pf"),
        default_value="!pf",
    ),
    FeatureDefinition(
        name="PASSIVE",
        combinator_fn=passive_combinator_fn,
        possible_values=("pv", "!pv"),
        default_value="!pv",
    ),
    FeatureDefinition(
        name="PROGRESSIVE",
        combinator_fn=progressive_combinator_fn,
        possible_values=("pg", "!pg"),
        default_value="!pg",
    ),
    FeatureDefinition(
        name="LEXICAL",
        combinator_fn=lexical_combinator_fn,
        possible_values=("lex", "!lex"),
        default_value="!lex",
    ),
]

FEATURE_DEFINITIONS_DICT.clear()
FEATURE_DEFINITIONS_DICT.update({d.name: d for d in FEATURE_DEFINITIONS})

SYNTACTIC_FEATURE_VALUES.clear()
SYNTACTIC_FEATURE_VALUES.update(build_value_to_name_table(FEATURE_DEFINITIONS))