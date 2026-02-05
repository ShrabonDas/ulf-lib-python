from dataclasses import dataclass, field
from typing import Literal, Any, Sequence
from syntactic_features import SyntacticFeatures, DEFAULT_SYNTACTIC_FEATURES

import json


# TODO: remove this line after testing is confirmed
with open("ulf_maps.json") as file:
    ULF_MAPS: dict[str, dict[str, Any]] | None = json.load(file)


Connective = Literal['=>', '>>', '%>']


@dataclass(slots=True)
class SemType:
    wire: str # TODO: remove this field after testing is confirmed
    connective: Connective = "=>"
    domain: object = None
    range: object = None
    ex: int = 1
    suffix: str | None = None
    type_params: list['SemType'] = field(default_factory=list)
    synfeats: SyntacticFeatures = field(default_factory=lambda: DEFAULT_SYNTACTIC_FEATURES.copy())


@dataclass(slots=True)
class AtomicType(SemType):
    pass


@dataclass(slots=True)
class OptionalType(SemType):
    types: list[SemType] = field(default_factory=list)


def new_optional_semtype(options: Sequence[SemType]) -> OptionalType:
    opt_wires = [o.wire for o in options]
    key = repr(opt_wires)
    out_wire = ULF_MAPS['new_optional_semtype'][key]
    return OptionalType(wire=out_wire, types=list(options))


def semtype_match(pattern: SemType, value: SemType) -> bool:
    key = repr([pattern.wire, value.wire])
    return bool(ULF_MAPS['semtype_match'][key])


def str2semtype(s: str) -> SemType:
    return SemType(wire=ULF_MAPS['str2semtype'][s])
