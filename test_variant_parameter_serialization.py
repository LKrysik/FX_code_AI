"""
Test VariantParameter serialization fix.
This script tests if the to_dict() method works correctly.
"""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.domain.types.indicator_types import VariantParameter
from src.domain.services.indicators.twpa import TWPAAlgorithm

def test_variant_parameter_to_dict():
    """Test that VariantParameter.to_dict() works."""
    param = VariantParameter(
        name="t1",
        parameter_type="float",
        default_value=300.0,
        min_value=1.0,
        max_value=86400.0,
        is_required=True,
        description="Test parameter"
    )

    # Convert to dict
    param_dict = param.to_dict()

    # Verify it's a dict
    assert isinstance(param_dict, dict), "to_dict() should return a dict"
    assert param_dict["name"] == "t1"
    assert param_dict["parameter_type"] == "float"
    assert param_dict["default_value"] == 300.0

    # Verify it's JSON serializable
    json_str = json.dumps(param_dict)
    assert json_str, "Dict should be JSON serializable"

    print("[OK] VariantParameter.to_dict() works correctly")
    return True

def test_algorithm_parameters_serialization():
    """Test that algorithm parameters can be serialized."""
    algo = TWPAAlgorithm()

    # Get parameters
    params = algo.get_parameters()
    print(f"[OK] Got {len(params)} parameters from TWPAAlgorithm")

    # Convert to dicts
    param_dicts = [p.to_dict() if hasattr(p, 'to_dict') else p for p in params]

    # Verify JSON serialization
    json_str = json.dumps(param_dicts, indent=2)
    print(f"[OK] Parameters are JSON serializable:")
    print(json_str[:200] + "...")

    return True

def test_registry_metadata_serialization():
    """Test that get_registry_metadata() returns serializable data."""
    algo = TWPAAlgorithm()

    # Get metadata
    metadata = algo.get_registry_metadata()

    # Filter out calculation_function (not serializable)
    serializable_metadata = {k: v for k, v in metadata.items() if k != "calculation_function"}

    # Verify JSON serialization
    json_str = json.dumps(serializable_metadata, indent=2)
    print(f"[OK] Registry metadata is JSON serializable:")
    print(json_str[:300] + "...")

    return True

if __name__ == "__main__":
    print("Testing VariantParameter serialization fix...\n")

    try:
        test_variant_parameter_to_dict()
        print()
        test_algorithm_parameters_serialization()
        print()
        test_registry_metadata_serialization()
        print()
        print("=" * 60)
        print("[SUCCESS] ALL TESTS PASSED - Fix is working!")
        print("=" * 60)
        print("\nNote: Backend needs restart to pick up changes.")
        print("Use: taskkill /PID 9592 /F (then restart server)")

    except Exception as e:
        print(f"\n[FAILED] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
