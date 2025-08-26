#!/usr/bin/env python3
"""
Demonstration of RadLex integration in the core synthetic report pipeline.
Shows how to use different RadLex configuration distributions.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def run_generator_with_radlex(radlex_dist: str, output_dir: str, num_cases: int = 3):
    """Run the generator with a specific RadLex distribution."""
    
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", str(num_cases),
        "--out", output_dir,
        "--seed", "42",
        "--radlex-dist", radlex_dist
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✓ Successfully generated {num_cases} cases with RadLex dist: {radlex_dist}")
        return True
    else:
        print(f"✗ Failed to generate cases: {result.stderr}")
        return False

def demonstrate_radlex_distributions():
    """Demonstrate different RadLex configuration distributions."""
    
    print("RadLex Pipeline Integration Demo")
    print("=" * 50)
    
    # Check if API key is available
    if not os.environ.get("BIOPORTAL_API_KEY"):
        print("Warning: BIOPORTAL_API_KEY not set.")
        print("RadLex features will use fallback terminology.")
        print("Get a free API key from: https://bioportal.bioontology.org/")
        print()
    
    # Define different RadLex distributions
    distributions = {
        "minimal_only": "minimal:1.0",
        "standard_only": "standard:1.0", 
        "aggressive_only": "aggressive:1.0",
        "conservative_only": "conservative:1.0",
        "mixed_balanced": "minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1",
        "mostly_enhanced": "standard:0.6,aggressive:0.3,conservative:0.1",
        "mostly_basic": "minimal:0.4,conservative:0.4,standard:0.2"
    }
    
    base_output_dir = "./demo_output/radlex_distributions"
    
    for dist_name, dist_config in distributions.items():
        print(f"\n--- Testing {dist_name} distribution ---")
        output_dir = f"{base_output_dir}/{dist_name}"
        
        success = run_generator_with_radlex(dist_config, output_dir, num_cases=2)
        
        if success:
            # Show some example output
            txt_files = list(Path(output_dir).rglob("*.txt"))
            if txt_files:
                print(f"Generated {len(txt_files)} report files")
                # Show first few lines of first report
                with open(txt_files[0], 'r') as f:
                    lines = f.readlines()[:10]
                    print("Sample output:")
                    for line in lines:
                        print(f"  {line.rstrip()}")
        print()

def demonstrate_with_followup():
    """Demonstrate RadLex with follow-up cases."""
    
    print("\n--- Testing RadLex with Follow-up Cases ---")
    
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", "2",
        "--out", "./demo_output/radlex_followup",
        "--seed", "123",
        "--follow-up",
        "--studies-per-patient", "3",
        "--radlex-dist", "standard:0.5,aggressive:0.3,conservative:0.2"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Successfully generated follow-up cases with RadLex")
        txt_files = list(Path("./demo_output/radlex_followup").rglob("*.txt"))
        print(f"Generated {len(txt_files)} total report files")
    else:
        print(f"✗ Failed: {result.stderr}")

def demonstrate_with_jsonl():
    """Demonstrate RadLex with JSONL output."""
    
    print("\n--- Testing RadLex with JSONL Output ---")
    
    cmd = [
        sys.executable, "-m", "synthrad",
        "--n", "2",
        "--out", "./demo_output/radlex_jsonl",
        "--seed", "456",
        "--studies-per-patient", "3",
        "--radlex-dist", "minimal:0.3,standard:0.4,aggressive:0.3",
        "--jsonl", "radlex_cohort.jsonl"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ Successfully generated JSONL with RadLex")
        jsonl_file = Path("./demo_output/radlex_jsonl/radlex_cohort.jsonl")
        if jsonl_file.exists():
            with open(jsonl_file, 'r') as f:
                lines = f.readlines()
                print(f"Generated JSONL with {len(lines)} entries")
    else:
        print(f"✗ Failed: {result.stderr}")

def show_usage_examples():
    """Show usage examples for different scenarios."""
    
    print("\n" + "=" * 50)
    print("Usage Examples")
    print("=" * 50)
    
    examples = [
        {
            "description": "Conservative RadLex (minimal enhancement)",
            "command": "python -m synthrad --n 10 --radlex-dist conservative:1.0 --out ./conservative_reports"
        },
        {
            "description": "Balanced RadLex (mixed enhancement levels)",
            "command": "python -m synthrad --n 10 --radlex-dist minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1 --out ./balanced_reports"
        },
        {
            "description": "Aggressive RadLex (maximum enhancement)",
            "command": "python -m synthrad --n 10 --radlex-dist aggressive:1.0 --out ./aggressive_reports"
        },
        {
            "description": "RadLex with follow-up cases",
            "command": "python -m synthrad --n 5 --follow-up --studies-per-patient 4 --radlex-dist standard:0.6,aggressive:0.4 --out ./followup_reports"
        },
        {
            "description": "RadLex with JSONL output",
            "command": "python -m synthrad --n 5 --studies-per-patient 3 --radlex-dist minimal:0.3,standard:0.4,aggressive:0.3 --jsonl cohort.jsonl --out ./jsonl_reports"
        }
    ]
    
    for example in examples:
        print(f"\n{example['description']}:")
        print(f"  {example['command']}")

def main():
    """Run the complete demonstration."""
    
    print("RadLex Pipeline Integration Demonstration")
    print("=" * 60)
    
    # Run demonstrations
    demonstrate_radlex_distributions()
    demonstrate_with_followup()
    demonstrate_with_jsonl()
    show_usage_examples()
    
    print("\n" + "=" * 60)
    print("Demonstration completed!")
    print("\nKey points:")
    print("- RadLex configurations are applied per case, not per patient")
    print("- Each case can have a different RadLex enhancement level")
    print("- The distribution controls the proportion of each config type")
    print("- RadLex enhancement works with all generator features (follow-up, JSONL, etc.)")
    print("\nAvailable RadLex configurations:")
    print("- minimal: Basic RadLex access without text enhancement")
    print("- standard: Balanced enhancement (default)")
    print("- aggressive: Maximum enhancement (up to 50% of text)")
    print("- conservative: Minimal enhancement (up to 10% of text)")

if __name__ == "__main__":
    main()

