#!/usr/bin/env python3
"""
Interactive Configuration Builder for SynthRad

This script provides an interactive way to create custom SynthRad configurations
with validation and helpful prompts.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tools.utils.config_manager import SynthRadConfig, ConfigSet, ConfigManager


def get_user_input(prompt: str, default: str = "", required: bool = True) -> str:
    """Get user input with optional default value."""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if user_input or not required:
            return user_input
        print("This field is required. Please enter a value.")


def get_choice(prompt: str, choices: List[str], default: int = 0) -> str:
    """Get user choice from a list of options."""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        print(f"  {marker} {i+1}. {choice}")
    
    while True:
        try:
            choice = input(f"Enter choice (1-{len(choices)}) [{default+1}]: ").strip()
            if not choice:
                choice = default + 1
            else:
                choice = int(choice)
            
            if 1 <= choice <= len(choices):
                return choices[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number")


def get_distribution(prompt: str, valid_keys: List[str], example: str) -> str:
    """Get a distribution string from user input."""
    print(f"\n{prompt}")
    print(f"Valid keys: {', '.join(valid_keys)}")
    print(f"Example format: {example}")
    print("Enter distribution as 'key:value,key:value' or press Enter for default")
    
    while True:
        dist = input("Distribution: ").strip()
        if not dist:
            return ""
        
        try:
            # Basic validation
            parts = dist.split(",")
            for part in parts:
                key, value = part.split(":")
                key = key.strip()
                value = float(value.strip())
                
                if key not in valid_keys:
                    print(f"Invalid key '{key}'. Valid keys: {valid_keys}")
                    break
                
                if value < 0:
                    print("Values must be non-negative")
                    break
            else:
                return dist
        except (ValueError, AttributeError):
            print("Invalid format. Use 'key:value,key:value' format")


def get_tags() -> List[str]:
    """Get tags from user input."""
    print("\nEnter tags (comma-separated) to categorize this configuration:")
    print("Examples: baseline, followup, radlex, research, clinical-trial")
    tags_input = input("Tags: ").strip()
    
    if tags_input:
        return [tag.strip() for tag in tags_input.split(",")]
    return []


def create_single_config() -> SynthRadConfig:
    """Create a single configuration interactively."""
    print("\n" + "="*50)
    print("Creating SynthRad Configuration")
    print("="*50)
    
    # Basic information
    name = get_user_input("Configuration name", required=True)
    description = get_user_input("Description (optional)", required=False)
    output_dir = get_user_input("Output directory", f"./out/{name}")
    
    # Core parameters
    num_patients = int(get_user_input("Number of patients", "5"))
    seed = int(get_user_input("Random seed", "42"))
    
    # Lobe selection
    lobe_choices = ["Any lobe (random)", "RUL", "RML", "RLL", "LUL", "LLL"]
    lobe_choice = get_choice("Select primary lobe:", lobe_choices)
    lobe = None if lobe_choice == "Any lobe (random)" else lobe_choice
    
    # Stage distribution
    stage_dist = get_distribution(
        "Stage distribution:",
        ["I", "II", "III", "IV"],
        "I:0.25,II:0.25,III:0.30,IV:0.20"
    )
    
    # Follow-up settings
    follow_up = get_choice("Generate follow-up cases?", ["No", "Yes"]) == "Yes"
    
    follow_up_days = 90
    studies_per_patient = 5
    
    if follow_up:
        follow_up_days = int(get_user_input("Days between studies", "90"))
        studies_per_patient = int(get_user_input("Maximum studies per patient (2-10)", "5"))
        
        # Response distribution
        response_dist = get_distribution(
            "Response distribution:",
            ["CR", "PR", "SD", "PD"],
            "CR:0.1,PR:0.3,SD:0.4,PD:0.2"
        )
    else:
        response_dist = ""
    
    # RadLex enhancement
    radlex_choices = [
        "No RadLex enhancement (minimal)",
        "Standard enhancement",
        "Aggressive enhancement", 
        "Conservative enhancement",
        "Mixed enhancement",
        "Custom distribution"
    ]
    radlex_choice = get_choice("RadLex enhancement level:", radlex_choices)
    
    radlex_dist = ""
    if radlex_choice == "No RadLex enhancement (minimal)":
        radlex_dist = "minimal:1.0"
    elif radlex_choice == "Standard enhancement":
        radlex_dist = "standard:1.0"
    elif radlex_choice == "Aggressive enhancement":
        radlex_dist = "aggressive:1.0"
    elif radlex_choice == "Conservative enhancement":
        radlex_dist = "conservative:1.0"
    elif radlex_choice == "Mixed enhancement":
        radlex_dist = "minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1"
    else:
        radlex_dist = get_distribution(
            "Custom RadLex distribution:",
            ["minimal", "standard", "aggressive", "conservative"],
            "minimal:0.3,standard:0.4,aggressive:0.2,conservative:0.1"
        )
    
    # Output options
    legacy_mode = get_choice("Use legacy mode?", ["No", "Yes"]) == "Yes"
    
    jsonl_filename = ""
    if get_choice("Generate JSONL output?", ["No", "Yes"]) == "Yes":
        jsonl_filename = get_user_input("JSONL filename", f"{name}_cohort.jsonl")
    
    # Tags
    tags = get_tags()
    
    # Create configuration
    config_data = {
        "name": name,
        "description": description,
        "output_dir": output_dir,
        "num_patients": num_patients,
        "seed": seed,
        "lobe": lobe,
        "follow_up": follow_up,
        "follow_up_days": follow_up_days,
        "studies_per_patient": studies_per_patient,
        "legacy_mode": legacy_mode,
        "jsonl_filename": jsonl_filename if jsonl_filename else None,
        "tags": tags
    }
    
    # Add distributions if provided
    if stage_dist:
        config_data["stage_distribution"] = stage_dist
    if response_dist:
        config_data["response_distribution"] = response_dist
    if radlex_dist:
        config_data["radlex_distribution"] = radlex_dist
    
    try:
        config = SynthRadConfig(**config_data)
        print(f"\n✓ Configuration '{name}' created successfully!")
        return config
    except ValueError as e:
        print(f"\n✗ Error creating configuration: {e}")
        return None


def create_config_set() -> ConfigSet:
    """Create a configuration set interactively."""
    print("\n" + "="*50)
    print("Creating Configuration Set")
    print("="*50)
    
    name = get_user_input("Configuration set name", required=True)
    description = get_user_input("Description (optional)", required=False)
    
    config_set = ConfigSet(name=name, description=description)
    
    while True:
        print(f"\nCurrent configurations: {len(config_set.configs)}")
        for i, config in enumerate(config_set.configs, 1):
            print(f"  {i}. {config.name}")
        
        choice = get_choice(
            "What would you like to do?",
            ["Add configuration", "Finish and save", "Cancel"]
        )
        
        if choice == "Add configuration":
            config = create_single_config()
            if config:
                config_set.add_config(config)
        elif choice == "Finish and save":
            if len(config_set.configs) == 0:
                print("Please add at least one configuration before saving.")
                continue
            break
        else:
            return None
    
    return config_set


def main():
    """Main function for the configuration builder."""
    print("SynthRad Configuration Builder")
    print("="*50)
    print("This tool helps you create SynthRad configurations interactively.")
    
    choice = get_choice(
        "What would you like to do?",
        [
            "Create a single configuration",
            "Create a configuration set",
            "Create sample configurations",
            "Create research configurations"
        ]
    )
    
    if choice == "Create a single configuration":
        config = create_single_config()
        if config:
            # Save single config
            config_set = ConfigSet(name="Single Configuration")
            config_set.add_config(config)
            
            filename = get_user_input("Save as (filename)", f"{config.name}_config.json")
            ConfigManager.save_to_json(config_set, filename)
            print(f"Configuration saved to {filename}")
    
    elif choice == "Create a configuration set":
        config_set = create_config_set()
        if config_set:
            filename = get_user_input("Save as (filename)", f"{config_set.name.lower().replace(' ', '_')}.json")
            ConfigManager.save_to_json(config_set, filename)
            print(f"Configuration set saved to {filename}")
    
    elif choice == "Create sample configurations":
        config_set = ConfigManager.create_sample_configs()
        filename = "sample_configs.json"
        ConfigManager.save_to_json(config_set, filename)
        print(f"Sample configurations saved to {filename}")
    
    elif choice == "Create research configurations":
        config_set = ConfigManager.create_research_configs()
        filename = "research_configs.json"
        ConfigManager.save_to_json(config_set, filename)
        print(f"Research configurations saved to {filename}")
    
    print("\nYou can now run your configurations with:")
    print("python scripts/multi_config_generator.py --configs <filename>")


if __name__ == "__main__":
    main()
