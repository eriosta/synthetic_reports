#!/usr/bin/env python3
"""
Multi-Configuration Generator for SynthRad

This script allows you to run multiple SynthRad configurations at once,
generating different types of synthetic reports with various parameters.

Usage:
    python scripts/multi_config_generator.py --configs configs.json
    python scripts/multi_config_generator.py --parallel --configs configs.json
    python scripts/multi_config_generator.py --create-sample
    python scripts/multi_config_generator.py --create-research
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Any
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import our clean configuration system
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from tools.utils.config_manager import ConfigManager, ConfigSet, SynthRadConfig, create_config_from_dict


def run_single_config(config: SynthRadConfig) -> bool:
    """Run a single configuration and return success status."""
    try:
        # Build command using the clean config system
        cmd = [sys.executable, "-m", "synthrad"] + config.to_synthrad_args()
        
        print(f"Running {config.name}: {' '.join(cmd)}")
        
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        end_time = time.time()
        
        if result.returncode == 0:
            print(f"✓ {config.name}: Successfully generated reports in {end_time - start_time:.2f}s")
            print(f"  Output directory: {config.output_dir}")
            if config.description:
                print(f"  Description: {config.description}")
            if config.tags:
                print(f"  Tags: {', '.join(config.tags)}")
            return True
        else:
            print(f"✗ {config.name}: Failed with error:")
            print(f"  {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ {config.name}: Exception occurred: {e}")
        return False


def run_configs_sequential(config_set: ConfigSet) -> Dict[str, bool]:
    """Run configurations sequentially."""
    results = {}
    
    print(f"Running {len(config_set.configs)} configurations sequentially...")
    print(f"Config Set: {config_set.name}")
    if config_set.description:
        print(f"Description: {config_set.description}")
    print("=" * 60)
    
    for config in config_set.configs:
        results[config.name] = run_single_config(config)
        print()
    
    return results


def run_configs_parallel(config_set: ConfigSet, max_workers: int = None) -> Dict[str, bool]:
    """Run configurations in parallel."""
    results = {}
    
    print(f"Running {len(config_set.configs)} configurations in parallel (max_workers={max_workers})...")
    print(f"Config Set: {config_set.name}")
    if config_set.description:
        print(f"Description: {config_set.description}")
    print("=" * 60)
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_config = {
            executor.submit(run_single_config, config): config 
            for config in config_set.configs
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_config):
            config = future_to_config[future]
            try:
                results[config.name] = future.result()
            except Exception as e:
                print(f"✗ {config.name}: Exception in parallel execution: {e}")
                results[config.name] = False
    
    return results


def load_config_set(file_path: str) -> ConfigSet:
    """Load configuration set from file, supporting both JSON and YAML."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    if file_path.suffix.lower() == '.yaml' or file_path.suffix.lower() == '.yml':
        return ConfigManager.load_from_yaml(str(file_path))
    else:
        return ConfigManager.load_from_json(str(file_path))


def print_config_summary(config_set: ConfigSet):
    """Print a summary of the configuration set."""
    print(f"\nConfiguration Set: {config_set.name}")
    if config_set.description:
        print(f"Description: {config_set.description}")
    
    if config_set.metadata:
        print(f"Metadata: {config_set.metadata}")
    
    print(f"\nConfigurations ({len(config_set.configs)}):")
    for i, config in enumerate(config_set.configs, 1):
        print(f"  {i}. {config.name}")
        if config.description:
            print(f"     {config.description}")
        print(f"     Output: {config.output_dir}")
        print(f"     Patients: {config.num_patients}")
        if config.tags:
            print(f"     Tags: {', '.join(config.tags)}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Run multiple SynthRad configurations at once",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create sample configuration files
  python scripts/multi_config_generator.py --create-sample
  python scripts/multi_config_generator.py --create-research
  
  # Run configurations sequentially
  python scripts/multi_config_generator.py --configs sample_configs.json
  
  # Run configurations in parallel (4 workers)
  python scripts/multi_config_generator.py --configs sample_configs.json --parallel --max-workers 4
  
  # Filter configurations by tags
  python scripts/multi_config_generator.py --configs sample_configs.json --tags baseline,followup
  
  # Run specific configurations by name
  python scripts/multi_config_generator.py --configs sample_configs.json --names baseline_standard,followup_optimistic

Configuration file format (JSON/YAML):
{
  "name": "Config Set Name",
  "description": "Optional description",
  "metadata": {"key": "value"},
  "configurations": [
    {
      "name": "config_name",
      "description": "Optional description",
      "output_dir": "./output/directory",
      "num_patients": 5,
      "seed": 42,
      "stage_distribution": "I:0.2,II:0.25,III:0.35,IV:0.2",
      "follow_up": true,
      "studies_per_patient": 4,
      "response_distribution": "CR:0.1,PR:0.3,SD:0.4,PD:0.2",
      "radlex_distribution": "standard:0.6,aggressive:0.3,conservative:0.1",
      "jsonl_filename": "cohort_labels.jsonl",
      "tags": ["baseline", "standard"]
    }
  ]
}
        """
    )
    
    parser.add_argument("--configs", type=str, help="JSON or YAML file containing configuration definitions")
    parser.add_argument("--parallel", action="store_true", help="Run configurations in parallel")
    parser.add_argument("--max-workers", type=int, default=None, help="Maximum number of parallel workers")
    parser.add_argument("--create-sample", action="store_true", help="Create a sample configuration file")
    parser.add_argument("--create-research", action="store_true", help="Create a research configuration file")
    parser.add_argument("--tags", type=str, help="Comma-separated list of tags to filter configurations")
    parser.add_argument("--names", type=str, help="Comma-separated list of configuration names to run")
    parser.add_argument("--summary", action="store_true", help="Show configuration summary without running")
    
    args = parser.parse_args()
    
    # Handle creation commands
    if args.create_sample:
        config_set = ConfigManager.create_sample_configs()
        ConfigManager.save_to_json(config_set, "sample_configs.json")
        ConfigManager.save_to_yaml(config_set, "sample_configs.yaml")
        print("Created sample configuration files:")
        print("  - sample_configs.json")
        print("  - sample_configs.yaml")
        print("\nEdit these files to customize your configurations, then run:")
        print("  python scripts/multi_config_generator.py --configs sample_configs.json")
        return
    
    if args.create_research:
        config_set = ConfigManager.create_research_configs()
        ConfigManager.save_to_json(config_set, "research_configs.json")
        ConfigManager.save_to_yaml(config_set, "research_configs.yaml")
        print("Created research configuration files:")
        print("  - research_configs.json")
        print("  - research_configs.yaml")
        print("\nThese configurations are designed for research and clinical trial simulation.")
        return
    
    if not args.configs:
        parser.error("Please provide a configuration file with --configs or use --create-sample/--create-research to create one")
    
    # Load configuration set
    try:
        config_set = load_config_set(args.configs)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        return
    
    # Filter configurations if requested
    if args.tags:
        tags = [tag.strip() for tag in args.tags.split(",")]
        filtered_configs = config_set.filter_by_tags(tags)
        if not filtered_configs:
            print(f"No configurations found with tags: {tags}")
            return
        config_set.configs = filtered_configs
        print(f"Filtered to {len(config_set.configs)} configurations with tags: {tags}")
    
    if args.names:
        names = [name.strip() for name in args.names.split(",")]
        filtered_configs = []
        for name in names:
            config = config_set.get_config_by_name(name)
            if config:
                filtered_configs.append(config)
            else:
                print(f"Warning: Configuration '{name}' not found")
        
        if not filtered_configs:
            print(f"No valid configurations found from names: {names}")
            return
        config_set.configs = filtered_configs
        print(f"Filtered to {len(config_set.configs)} configurations by name")
    
    # Show summary if requested
    if args.summary:
        print_config_summary(config_set)
        return
    
    # Validate configurations
    print_config_summary(config_set)
    
    # Run configurations
    start_time = time.time()
    
    if args.parallel:
        results = run_configs_parallel(config_set, args.max_workers)
    else:
        results = run_configs_sequential(config_set)
    
    end_time = time.time()
    
    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for success in results.values() if success)
    total = len(results)
    
    print(f"Total configurations: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Total time: {end_time - start_time:.2f}s")
    
    if successful < total:
        print("\nFailed configurations:")
        for name, success in results.items():
            if not success:
                print(f"  - {name}")
    
    print(f"\nOutput directories:")
    for config in config_set.configs:
        if results.get(config.name, False):
            print(f"  - {config.name}: {config.output_dir}")


if __name__ == "__main__":
    main()
