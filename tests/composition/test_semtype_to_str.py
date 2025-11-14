"""
Tests for SemType JSON parsing and string conversion.

This module tests the semtype_to_str functionality by parsing JSONL test data
and comparing normalized output (with sorted feature ordering).
"""

import json
import re
from pathlib import Path
from typing import Any, Optional, List

import pytest
from semtype import SyntacticFeatures, SemType, AtomicType, OptionalType, semtype_to_str


# ============================================================================
# Constants
# ============================================================================

DEFAULT_SYNTACTIC_FEATURES = SyntacticFeatures()
TEST_DATA_FILE = Path("testcases/composition/test_semtype_to_str_cases.jsonl")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_cases():
    """
    Fixture that loads all test cases from the JSONL file.
    Returns list of (line_num, input_data, expected_output) tuples.
    """
    return load_json_test_cases(TEST_DATA_FILE)


# ============================================================================
# Helper Functions
# ============================================================================

def normalize_features(text: str) -> str:
    """
    Normalize feature ordering in a type string for comparison.
    
    Finds all %FEATURE patterns and sorts features alphabetically.
    Example: %!T,!PV,LEX becomes %!LEX,!PV,!T
    
    Args:
        text: Type string with potentially unsorted features
        
    Returns:
        Type string with alphabetically sorted features
    """
    def sort_features(match):
        features_str = match.group(1)
        features = features_str.split(',')
        features.sort()
        return f"%{','.join(features)}"
    
    return re.sub(r'%([!A-Z,]+)', sort_features, text)


def build_semtype_from_json(data: Any) -> Optional[SemType]:
    """
    Build a SemType object from JSON data.
    
    Args:
        data: JSON data representing a SemType
        
    Returns:
        SemType object or None if data is null/invalid
    """
    if data is None or data == "null":
        return None
    
    if not isinstance(data, dict):
        return data
    
    obj_type = data.get('type', 'SEMTYPE')
    
    # Extract common attributes
    connective = data.get('connective', '=>')
    exponent = data.get('exponent', 1)
    suffix = data.get('suffix')
    if suffix == "null":
        suffix = None
    
    # Parse domain
    domain = data.get('domain')
    if isinstance(domain, dict):
        domain = build_semtype_from_json(domain)
    elif domain == "null":
        domain = None
    
    # Parse range
    range_val = data.get('range')
    if isinstance(range_val, dict):
        range_val = build_semtype_from_json(range_val)
    elif range_val == "null":
        range_val = None
    
    # Parse syntactic features
    synfeats = DEFAULT_SYNTACTIC_FEATURES
    synfeats_data = data.get('synfeats')
    if synfeats_data and isinstance(synfeats_data, dict):
        feature_map = synfeats_data.get('feature-map')
        if feature_map and feature_map != "null" and isinstance(feature_map, dict):
            synfeats = SyntacticFeatures(feature_map)
    
    # Parse type parameters
    type_params = []
    type_params_data = data.get('type-params')
    if type_params_data and type_params_data != "null" and isinstance(type_params_data, list):
        type_params = [build_semtype_from_json(tp) for tp in type_params_data]
    
    # Build the appropriate type
    if obj_type == 'OPTIONAL-TYPE':
        types = []
        types_data = data.get('types')
        if types_data and isinstance(types_data, list):
            types = [build_semtype_from_json(t) for t in types_data]
        
        return OptionalType(
            connective=connective,
            domain=domain,
            range=range_val,
            ex=exponent,
            suffix=suffix,
            synfeats=synfeats,
            type_params=type_params,
            types=types
        )
    elif obj_type == 'ATOMIC-TYPE':
        return AtomicType(
            connective=connective,
            domain=domain,
            range=range_val,
            ex=exponent,
            suffix=suffix,
            synfeats=synfeats,
            type_params=type_params
        )
    else:
        return SemType(
            connective=connective,
            domain=domain,
            range=range_val,
            ex=exponent,
            suffix=suffix,
            synfeats=synfeats,
            type_params=type_params
        )


def load_json_test_cases(file_path: Path) -> List[tuple]:
    """
    Load test cases from a JSON log file.
    
    Args:
        file_path: Path to JSON log file
        
    Returns:
        List of (input_data, expected_output) tuples
    """
    if not file_path.exists():
        return []
    
    test_cases = []
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                test_cases.append((
                    line_num,
                    data['input'],
                    data['output']
                ))
            except (json.JSONDecodeError, KeyError) as e:
                pytest.fail(f"Failed to parse line {line_num}: {e}")
    
    return test_cases


# ============================================================================
# Tests for JSONL File Test Cases
# ============================================================================

class TestSemTypeToStrFromJsonl:
    """Tests using cases loaded from test_semtype_to_str_cases.jsonl."""
    
    def test_jsonl_file_exists(self):
        """Test that the JSONL test data file exists."""
        assert TEST_DATA_FILE.exists(), (
            f"Test data file not found: {TEST_DATA_FILE}\n"
            f"Please ensure test_semtype_to_str_cases.jsonl is in the correct location."
        )
    
    def test_each_case_individually(self, test_cases):
        """
        Test each case from the JSONL file individually.
        
        This uses pytest's subtests-like behavior via dynamic test generation.
        Each case failure is reported separately with its line number.
        """
        assert len(test_cases) > 0, "No test cases found in JSONL file"
        
        # Track statistics
        passed = 0
        failed = 0
        skipped = 0
        errors = []
        
        for line_num, input_data, expected_output in test_cases:
            try:
                semtype_obj = build_semtype_from_json(input_data)
                if semtype_obj is None:
                    skipped += 1
                    continue
                
                actual_output = semtype_to_str(semtype_obj)
                expected_normalized = normalize_features(expected_output)
                actual_normalized = normalize_features(actual_output)
                
                if actual_normalized == expected_normalized:
                    passed += 1
                else:
                    failed += 1
                    errors.append({
                        'line': line_num,
                        'expected': expected_output,
                        'actual': actual_output,
                        'expected_norm': expected_normalized,
                        'actual_norm': actual_normalized
                    })
            except Exception as e:
                failed += 1
                errors.append({
                    'line': line_num,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
        
        # Build detailed failure message
        if errors:
            total = passed + failed + skipped
            failure_lines = [
                f"\nTest Statistics:",
                f"  Total cases: {total}",
                f"  Passed: {passed}",
                f"  Failed: {failed}",
                f"  Skipped: {skipped}",
                f"\nFailure Details (showing first 10):\n"
            ]
            
            for i, case in enumerate(errors[:10], 1):
                line_num = case['line']
                failure_lines.append(f"  [{i}] Line {line_num}:")
                
                if 'error' in case:
                    failure_lines.append(f"      Error: {case['error_type']}: {case['error']}")
                else:
                    expected = case['expected'][:100]
                    actual = case['actual'][:100]
                    failure_lines.append(f"      Expected: {expected}{'...' if len(case['expected']) > 100 else ''}")
                    failure_lines.append(f"      Actual:   {actual}{'...' if len(case['actual']) > 100 else ''}")
                    
                    # Show where they differ
                    exp_norm = case['expected_norm']
                    act_norm = case['actual_norm']
                    for j, (e, a) in enumerate(zip(exp_norm, act_norm)):
                        if e != a:
                            failure_lines.append(f"      First diff at position {j}: expected '{e}', got '{a}'")
                            break
                
                failure_lines.append("")  # Blank line between failures
            
            if len(errors) > 10:
                failure_lines.append(f"  ... and {len(errors) - 10} more failures")
            
            pytest.fail("\n".join(failure_lines))


def pytest_generate_tests(metafunc):
    """
    Dynamically generate individual tests for each JSONL test case.
    
    This creates a separate test for each line in the JSONL file,
    allowing pytest to report each case individually with its own pass/fail status.
    """
    if "individual_test_case" in metafunc.fixturenames:
        test_cases = load_json_test_cases(TEST_DATA_FILE)
        
        # Create test IDs like "line_1", "line_2", etc.
        test_ids = [f"line_{line_num}" for line_num, _, _ in test_cases]
        
        metafunc.parametrize(
            "individual_test_case",
            test_cases,
            ids=test_ids
        )


class TestIndividualCases:
    """Each test case from JSONL file is run as a separate test."""
    
    def test_case(self, individual_test_case):
        """Test a single case from the JSONL file."""
        line_num, input_data, expected_output = individual_test_case
        
        semtype_obj = build_semtype_from_json(input_data)
        
        if semtype_obj is None:
            pytest.skip(f"Could not parse entry on line {line_num}")
        
        actual_output = semtype_to_str(semtype_obj)
        expected_normalized = normalize_features(expected_output)
        actual_normalized = normalize_features(actual_output)
        
        assert actual_normalized == expected_normalized, (
            f"\nLine {line_num} failed:\n"
            f"  Expected: {expected_output}\n"
            f"  Actual:   {actual_output}\n"
        )