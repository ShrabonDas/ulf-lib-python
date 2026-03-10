"""
Tests for SyntacticFeatures methods.

Covers (with dependency coverage):
  1. combine_features    -> get_feature_names, feature_value, update_feature_map,
                            get_syntactic_feature_combinator (oracle-driven)

Usage:
    python tests/test_syntactic_features.py
    python tests/test_syntactic_features.py --combine
"""
import json
import sys
from typing import Any

from ulf_py import (
    SyntacticFeatures, str2semtype
)

# =====================================================================
# 1. combine_features (oracle-driven)
# =====================================================================

def _strip_package(val: str | None) -> str | None:
    if val is None:
        return None
    if "::" in val:
        val = val.rsplit("::", 1)[1]
    return val.lower()


def _load_combine_cases(path: str = "combine_features_cases.json"):
    """Load oracle cases from JSON file recorded by Lisp."""
    try:
        with open(path) as f:
            data = json.load(f)
        return data.get("combine_features", [])
    except FileNotFoundError:
        print(f"  WARNING: {path} not found, skipping oracle tests")
        return []


def _parse_feature_map(raw: dict[str, str] | None) -> dict[str, str | None]:
    """Convert a dictionary to Python feature_map.

    The recorder outputs values as prin1'd Lisp symbols (uppercase).
    Python stores them lowercase.
    """
    if raw is None:
        return {}
    
    if isinstance(raw, dict):
        return {k.upper(): _strip_package(v) for k, v in raw.items() if v is not None}
    return {}


def _result_map_equal(expected: dict, actual: SyntacticFeatures) -> bool:
    """Compare expected result map against actual SyntacticFeatures.

    Only compares non-None entries from both sides.
    """
    expected_clean = {k: v for k, v in expected.items() if v is not None}
    actual_clean = {k: v for k, v in actual.feature_map.items() if v is not None}
    return expected_clean == actual_clean


def test_combine_features() -> None:
    cases = _load_combine_cases()
    if not cases:
        print("\ncombine_features: 0/0 passed (no oracle data)\n")
        return

    passed = failed = errors = 0
    failures = []

    for i, case in enumerate(cases):
        try:
            base_map = _parse_feature_map(case.get("base"))
            opr_map = _parse_feature_map(case.get("opr"))
            arg_map = _parse_feature_map(case.get("arg"))
            csq_map = _parse_feature_map(case.get("csq"))
            expected_map = _parse_feature_map(case.get("result"))

            base_sf = SyntacticFeatures(feature_map=dict(base_map))
            opr_sf = SyntacticFeatures(feature_map=dict(opr_map))
            arg_sf = SyntacticFeatures(feature_map=dict(arg_map))
            csq_sf = SyntacticFeatures(feature_map=dict(csq_map))

            opr_st_str = case.get("opr_semtype")
            arg_st_str = case.get("arg_semtype")

            opr_semtype = str2semtype(opr_st_str) if opr_st_str else None
            arg_semtype = str2semtype(arg_st_str) if arg_st_str else None

            result = SyntacticFeatures.combine_features(
                base_sf, opr_sf, arg_sf, csq_sf,
                opr_semtype, arg_semtype,
            )

            if _result_map_equal(expected_map, result):
                passed += 1
            else:
                failed += 1
                actual_clean = {k: v for k, v in result.feature_map.items() if v is not None}
                expected_clean = {k: v for k, v in expected_map.items() if v is not None}
                failures.append((f"case {i}", f"expected {expected_clean}, got {actual_clean}"))
        except Exception as e:
            errors += 1
            failures.append((f"case {i}", f"ERROR: {e!r}"))

    total = passed + failed + errors
    print(f"\ncombine_features (oracle): {passed}/{total} passed, "
          f"{failed} real failures, {errors} errors")
    for desc, detail in failures[:20]:
        print(f"  FAIL: {desc}")
        print(f"        {detail}")
    if len(failures) > 20:
        print(f"  ... and {len(failures) - 20} more")
    print()


# =====================================================================
# Main
# =====================================================================

if __name__ == "__main__":
    args = set(sys.argv[1:])
    run_all = not args
    
    if run_all or "--combine" in args:
        test_combine_features()