#!/usr/bin/env python3
"""
Test runner for synthrad tests
"""
import sys
import pytest
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def run_all_tests():
    """Run all tests in the tests directory"""
    test_dir = Path(__file__).parent
    
    # List of test files
    test_files = [
        "test_basic.py",
        "test_lexicons.py", 
        "test_generator.py",
        "test_longitudinal.py",
        "test_styles.py",
        "test_edge_cases.py",
        "test_integration.py"
    ]
    
    # Run tests
    args = [str(test_dir / test_file) for test_file in test_files]
    args.extend([
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--strict-markers",  # Strict marker checking
        "--disable-warnings",  # Disable warnings for cleaner output
    ])
    
    return pytest.main(args)

def run_specific_test(test_name):
    """Run a specific test file"""
    test_dir = Path(__file__).parent
    test_file = test_dir / f"test_{test_name}.py"
    
    if not test_file.exists():
        print(f"Test file {test_file} not found")
        return 1
    
    args = [
        str(test_file),
        "-v",
        "--tb=short",
        "--strict-markers",
        "--disable-warnings",
    ]
    
    return pytest.main(args)

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        return run_specific_test(test_name)
    else:
        return run_all_tests()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
