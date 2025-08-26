#!/usr/bin/env python3
"""
Comprehensive tests for RadLex integration functionality.
Combines rate limiting, duplicate findings, and pipeline tests.
"""

import os
import sys
import time
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_rate_limiting():
    """Test rate limiting functionality."""
    
    print("BioPortal API Rate Limiting Test")
    print("=" * 50)
    
    # Check if API key is available
    if not os.environ.get("BIOPORTAL_API_KEY"):
        print("Warning: BIOPORTAL_API_KEY not set.")
        print("Get a free API key from: https://bioportal.bioontology.org/")
        print("Set it with: export BIOPORTAL_API_KEY=your_key_here")
        return False
    
    try:
        from synthrad.radlex_service import RadLexService, RateLimiter
        from synthrad.radlex_lexicons import get_radlex_lexicons
        
        print("✓ RadLex modules imported successfully")
        
        # Test rate limiter directly
        print("\n--- Testing Rate Limiter ---")
        rate_limiter = RateLimiter(calls_per_second=2.0, calls_per_minute=10)
        
        print("Making 5 API calls with 2 calls/second limit...")
        start_time = time.time()
        
        for i in range(5):
            rate_limiter.wait_if_needed()
            print(f"  Call {i+1}: {time.time():.2f}s")
        
        elapsed = time.time() - start_time
        print(f"Total time: {elapsed:.2f}s (expected ~2.5s)")
        
        # Test RadLex service with rate limiting
        print("\n--- Testing RadLex Service with Rate Limiting ---")
        
        # Test with conservative rate limits
        service = RadLexService(rate_limit_per_second=1.0, rate_limit_per_minute=5)
        
        test_texts = [
            "pulmonary nodule",
            "lymphadenopathy", 
            "pleural effusion",
            "mediastinal mass",
            "atelectasis"
        ]
        
        print("Annotating 5 medical terms with 1 call/second limit...")
        start_time = time.time()
        
        for i, text in enumerate(test_texts):
            print(f"  Annotating '{text}'...")
            annotations = service.annotate_text(text)
            print(f"    Found {len(annotations)} annotations")
        
        elapsed = time.time() - start_time
        print(f"Total time: {elapsed:.2f}s (expected ~5s)")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_duplicate_findings():
    """Test that reports no longer have duplicate findings."""
    
    print("\nDuplicate Findings Fix Test")
    print("=" * 40)
    
    # Generate a few test cases
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", "5",
        "--out", "./test_output/duplicate_test",
        "--seed", "42",
        "--stage-dist", "IV:1.0"  # Force stage IV to get more metastases
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"✗ Failed to generate test cases: {result.stderr}")
        return False
    
    # Check generated reports for duplicates
    txt_files = list(Path("./test_output/duplicate_test").rglob("*.txt"))
    print(f"Generated {len(txt_files)} report files")
    
    duplicate_issues = []
    
    for txt_file in txt_files:
        with open(txt_file, 'r') as f:
            content = f.read()
            
        # Check for duplicate metastatic findings
        metastatic_lines = [line.strip() for line in content.split('\n') 
                          if line.strip().startswith('Metastatic survey:')]
        
        # Check for duplicate lymph node findings
        lymph_node_lines = [line.strip() for line in content.split('\n') 
                          if 'lymph node' in line.lower() and 'mm' in line]
        
        # Check for exact duplicates in metastatic findings
        if len(metastatic_lines) != len(set(metastatic_lines)):
            duplicate_issues.append(f"Duplicate metastatic findings in {txt_file.name}")
        
        # Check for exact duplicates in lymph node findings
        if len(lymph_node_lines) != len(set(lymph_node_lines)):
            duplicate_issues.append(f"Duplicate lymph node findings in {txt_file.name}")
        
        # Check for same site metastases (e.g., multiple "Right adrenal nodule")
        metastatic_sites = []
        for line in metastatic_lines:
            if "adrenal" in line.lower():
                metastatic_sites.append("adrenal")
            elif "liver" in line.lower():
                metastatic_sites.append("liver")
            elif "bone" in line.lower():
                metastatic_sites.append("bone")
            elif "brain" in line.lower():
                metastatic_sites.append("brain")
            elif "pleura" in line.lower():
                metastatic_sites.append("pleura")
        
        if len(metastatic_sites) != len(set(metastatic_sites)):
            duplicate_issues.append(f"Duplicate metastatic sites in {txt_file.name}: {metastatic_sites}")
    
    if duplicate_issues:
        print("✗ Found duplicate findings issues:")
        for issue in duplicate_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✓ No duplicate findings detected!")
        return True

def test_radlex_pipeline():
    """Test RadLex pipeline integration."""
    
    print("\nRadLex Pipeline Integration Test")
    print("=" * 40)
    
    # Test different RadLex distributions
    distributions = {
        "minimal_only": "minimal:1.0",
        "standard_only": "standard:1.0", 
        "aggressive_only": "aggressive:1.0",
        "conservative_only": "conservative:1.0",
        "mixed_balanced": "minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1"
    }
    
    success_count = 0
    
    for dist_name, dist_config in distributions.items():
        print(f"\n--- Testing {dist_name} distribution ---")
        output_dir = f"./test_output/pipeline_test/{dist_name}"
        
        cmd = [
            sys.executable, "-m", "synthrad",
            "--n", "2",
            "--out", output_dir,
            "--seed", "42",
            "--radlex-dist", dist_config
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully generated cases with RadLex dist: {dist_config}")
            success_count += 1
        else:
            print(f"✗ Failed to generate cases: {result.stderr}")
    
    print(f"\nPipeline test results: {success_count}/{len(distributions)} distributions successful")
    return success_count == len(distributions)

def test_basic_functionality():
    """Test basic report generation functionality."""
    
    print("\nBasic Functionality Test")
    print("=" * 30)
    
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", "3",
        "--out", "./test_output/basic_test",
        "--seed", "123"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        txt_files = list(Path("./test_output/basic_test").rglob("*.txt"))
        json_files = list(Path("./test_output/basic_test").rglob("*.json"))
        
        print(f"✓ Generated {len(txt_files)} text files and {len(json_files)} JSON files")
        return True
    else:
        print(f"✗ Basic test failed: {result.stderr}")
        return False

def test_followup_functionality():
    """Test follow-up report generation."""
    
    print("\nFollow-up Functionality Test")
    print("=" * 35)
    
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", "2",
        "--out", "./test_output/followup_test",
        "--seed", "456",
        "--follow-up",
        "--studies-per-patient", "3",
        "--response-dist", "CR:0.1,PR:0.3,SD:0.4,PD:0.2"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        txt_files = list(Path("./test_output/followup_test").rglob("*.txt"))
        print(f"✓ Generated {len(txt_files)} follow-up report files")
        return True
    else:
        print(f"✗ Follow-up test failed: {result.stderr}")
        return False

def test_jsonl_output():
    """Test JSONL output functionality."""
    
    print("\nJSONL Output Test")
    print("=" * 25)
    
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", "2",
        "--out", "./test_output/jsonl_test",
        "--seed", "789",
        "--studies-per-patient", "3",
        "--jsonl", "test_cohort.jsonl"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        jsonl_file = Path("./test_output/jsonl_test/test_cohort.jsonl")
        if jsonl_file.exists():
            with open(jsonl_file, 'r') as f:
                lines = f.readlines()
            print(f"✓ Generated JSONL with {len(lines)} entries")
            return True
        else:
            print("✗ JSONL file not found")
            return False
    else:
        print(f"✗ JSONL test failed: {result.stderr}")
        return False

def cleanup_test_outputs():
    """Clean up test output directories."""
    
    import shutil
    
    test_dirs = [
        "./test_output",
        "./test_rate_limited",
        "./simple_test", 
        "./test_fix",
        "./radlex_demo_output",
        "./radlex_followup_demo",
        "./radlex_jsonl_demo"
    ]
    
    for test_dir in test_dirs:
        if Path(test_dir).exists():
            try:
                shutil.rmtree(test_dir)
                print(f"Cleaned up: {test_dir}")
            except Exception as e:
                print(f"Warning: Could not clean up {test_dir}: {e}")

def main():
    """Run all tests."""
    
    print("Comprehensive RadLex Integration Test Suite")
    print("=" * 60)
    
    # Create test output directory
    os.makedirs("./test_output", exist_ok=True)
    
    # Run tests
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Follow-up Functionality", test_followup_functionality),
        ("JSONL Output", test_jsonl_output),
        ("Duplicate Findings Fix", test_duplicate_findings),
        ("RadLex Pipeline", test_radlex_pipeline),
        ("Rate Limiting", test_rate_limiting)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    # Cleanup
    print("\nCleaning up test outputs...")
    cleanup_test_outputs()
    
    if passed == len(results):
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed")
        return 1

if __name__ == "__main__":
    exit(main())

