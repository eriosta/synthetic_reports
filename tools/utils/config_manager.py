#!/usr/bin/env python3
"""
Configuration Manager for SynthRad Multi-Configuration Generator

This module provides a clean, type-safe way to define and manage multiple
SynthRad configurations with validation and easy serialization.
"""

import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml


@dataclass
class SynthRadConfig:
    """Individual SynthRad configuration with validation."""
    
    # Required fields
    name: str
    output_dir: str
    
    # Core parameters
    num_patients: int = 5
    seed: int = 42
    
    # Tumor and staging
    lobe: Optional[str] = None
    stage_distribution: str = "I:0.25,II:0.25,III:0.30,IV:0.20"
    
    # Follow-up settings
    follow_up: bool = False
    follow_up_days: int = 90
    studies_per_patient: int = 5
    
    # Response tracking
    response_distribution: str = "CR:0.1,PR:0.3,SD:0.4,PD:0.2"
    
    # RadLex anatomic mapping
    use_radlex: bool = True
    
    # Output options
    legacy_mode: bool = False
    jsonl_filename: Optional[str] = None
    
    # Metadata
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration parameters."""
        # Validate required fields
        if not self.name:
            raise ValueError("Configuration name is required")
        
        if not self.output_dir:
            raise ValueError("Output directory is required")
        
        # Validate numeric ranges
        if self.num_patients < 1:
            raise ValueError("num_patients must be at least 1")
        
        if self.studies_per_patient < 2 or self.studies_per_patient > 10:
            raise ValueError("studies_per_patient must be between 2 and 10")
        
        if self.follow_up_days < 1:
            raise ValueError("follow_up_days must be at least 1")
        
        # Validate lobe choice
        valid_lobes = [None, "RUL", "RML", "RLL", "LUL", "LLL"]
        if self.lobe not in valid_lobes:
            raise ValueError(f"lobe must be one of {valid_lobes}")
        
        # Validate distributions
        self._validate_distribution(self.stage_distribution, ["I", "II", "III", "IV"])
        self._validate_distribution(self.response_distribution, ["CR", "PR", "SD", "PD"])
    
    def _validate_distribution(self, dist_str: str, valid_keys: List[str]):
        """Validate distribution string format."""
        if not dist_str:
            return
        
        try:
            parts = dist_str.split(",")
            for part in parts:
                key, value = part.split(":")
                key = key.strip()
                value = float(value.strip())
                
                if key not in valid_keys:
                    raise ValueError(f"Invalid key '{key}' in distribution '{dist_str}'")
                
                if value < 0:
                    raise ValueError(f"Distribution values must be non-negative: {dist_str}")
                    
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid distribution format '{dist_str}': {e}")
    
    def to_synthrad_args(self) -> List[str]:
        """Convert configuration to SynthRad command-line arguments."""
        args = []
        
        # Required parameters
        args.extend(["--n", str(self.num_patients)])
        args.extend(["--out", self.output_dir])
        args.extend(["--seed", str(self.seed)])
        
        # Optional parameters
        if self.lobe:
            args.extend(["--lobe", self.lobe])
        
        if self.stage_distribution != "I:0.25,II:0.25,III:0.30,IV:0.20":
            args.extend(["--stage-dist", self.stage_distribution])
        
        if self.follow_up:
            args.append("--follow-up")
        
        if self.follow_up_days != 90:
            args.extend(["--follow-up-days", str(self.follow_up_days)])
        
        if self.studies_per_patient != 5:
            args.extend(["--studies-per-patient", str(self.studies_per_patient)])
        
        if self.response_distribution != "CR:0.1,PR:0.3,SD:0.4,PD:0.2":
            args.extend(["--response-dist", self.response_distribution])
        
        if not self.use_radlex:
            args.extend(["--no-radlex"])
        
        if self.legacy_mode:
            args.append("--legacy-mode")
        
        if self.jsonl_filename:
            args.extend(["--jsonl", self.jsonl_filename])
        
        return args
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ConfigSet:
    """A set of SynthRad configurations with metadata."""
    
    name: str
    description: str = ""
    configs: List[SynthRadConfig] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_config(self, config: SynthRadConfig):
        """Add a configuration to the set."""
        self.configs.append(config)
    
    def get_config_by_name(self, name: str) -> Optional[SynthRadConfig]:
        """Get configuration by name."""
        for config in self.configs:
            if config.name == name:
                return config
        return None
    
    def filter_by_tags(self, tags: List[str]) -> List[SynthRadConfig]:
        """Filter configurations by tags."""
        if not tags:
            return self.configs
        
        return [config for config in self.configs 
                if any(tag in config.tags for tag in tags)]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "configurations": [config.to_dict() for config in self.configs]
        }


class ConfigManager:
    """Manager for loading, saving, and creating configuration sets."""
    
    @staticmethod
    def create_sample_configs() -> ConfigSet:
        """Create a sample configuration set."""
        config_set = ConfigSet(
            name="Sample Configurations",
            description="Example configurations demonstrating different SynthRad features"
        )
        
        # Baseline configurations
        config_set.add_config(SynthRadConfig(
            name="baseline_standard",
            description="Standard baseline generation",
            output_dir="./out/baseline_standard",
            num_patients=5,
            tags=["baseline", "standard"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="baseline_early_stage",
            description="Early stage focused baseline",
            output_dir="./out/baseline_early_stage",
            num_patients=10,
            stage_distribution="I:0.6,II:0.3,III:0.1,IV:0.0",
            tags=["baseline", "early-stage"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="baseline_advanced_stage",
            description="Advanced stage focused baseline",
            output_dir="./out/baseline_advanced_stage",
            num_patients=10,
            stage_distribution="I:0.0,II:0.1,III:0.4,IV:0.5",
            tags=["baseline", "advanced-stage"]
        ))
        
        # Follow-up configurations
        config_set.add_config(SynthRadConfig(
            name="followup_standard",
            description="Standard follow-up generation",
            output_dir="./out/followup_standard",
            num_patients=5,
            follow_up=True,
            studies_per_patient=4,
            tags=["followup", "standard"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="followup_optimistic",
            description="Optimistic response follow-up",
            output_dir="./out/followup_optimistic",
            num_patients=5,
            follow_up=True,
            studies_per_patient=4,
            response_distribution="CR:0.2,PR:0.4,SD:0.3,PD:0.1",
            tags=["followup", "optimistic"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="followup_conservative",
            description="Conservative response follow-up",
            output_dir="./out/followup_conservative",
            num_patients=5,
            follow_up=True,
            studies_per_patient=4,
            response_distribution="CR:0.05,PR:0.2,SD:0.5,PD:0.25",
            tags=["followup", "conservative"]
        ))
        
        # RadLex configurations
        config_set.add_config(SynthRadConfig(
            name="radlex_minimal",
            description="Minimal RadLex enhancement",
            output_dir="./out/radlex_minimal",
            num_patients=5,
            radlex_distribution="minimal:1.0",
            tags=["radlex", "minimal"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="radlex_standard",
            description="Standard RadLex enhancement",
            output_dir="./out/radlex_standard",
            num_patients=5,
            radlex_distribution="standard:1.0",
            tags=["radlex", "standard"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="radlex_aggressive",
            description="Aggressive RadLex enhancement",
            output_dir="./out/radlex_aggressive",
            num_patients=5,
            radlex_distribution="aggressive:1.0",
            tags=["radlex", "aggressive"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="radlex_mixed",
            description="Mixed RadLex enhancement",
            output_dir="./out/radlex_mixed",
            num_patients=5,
            radlex_distribution="minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1",
            tags=["radlex", "mixed"]
        ))
        
        # Special configurations
        config_set.add_config(SynthRadConfig(
            name="jsonl_output",
            description="Generate with JSONL output for React app",
            output_dir="./out/jsonl_output",
            num_patients=5,
            studies_per_patient=4,
            jsonl_filename="cohort_labels.jsonl",
            tags=["jsonl", "react"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="custom_interval",
            description="Generate with custom follow-up interval",
            output_dir="./out/custom_interval",
            num_patients=5,
            follow_up=True,
            follow_up_days=60,
            studies_per_patient=4,
            tags=["followup", "custom-interval"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="legacy_mode",
            description="Generate using legacy mode",
            output_dir="./out/legacy_mode",
            num_patients=5,
            legacy_mode=True,
            follow_up=True,
            tags=["legacy"]
        ))
        
        return config_set
    
    @staticmethod
    def create_research_configs() -> ConfigSet:
        """Create research-focused configuration set."""
        config_set = ConfigSet(
            name="Research Configurations",
            description="Configurations for research and clinical trial simulation",
            metadata={"type": "research", "version": "1.0"}
        )
        
        # Clinical trial arms
        config_set.add_config(SynthRadConfig(
            name="clinical_trial_arm_a",
            description="Clinical trial arm A - standard treatment",
            output_dir="./research/clinical_trial_arm_a",
            num_patients=50,
            follow_up=True,
            studies_per_patient=6,
            response_distribution="CR:0.15,PR:0.35,SD:0.35,PD:0.15",
            jsonl_filename="arm_a_cohort.jsonl",
            tags=["clinical-trial", "arm-a", "standard-treatment"]
        ))
        
        config_set.add_config(SynthRadConfig(
            name="clinical_trial_arm_b",
            description="Clinical trial arm B - experimental treatment",
            output_dir="./research/clinical_trial_arm_b",
            num_patients=50,
            follow_up=True,
            studies_per_patient=6,
            response_distribution="CR:0.25,PR:0.4,SD:0.25,PD:0.1",
            jsonl_filename="arm_b_cohort.jsonl",
            tags=["clinical-trial", "arm-b", "experimental-treatment"]
        ))
        
        # Follow-up interval studies
        for days, tag in [(30, "30-days"), (60, "60-days"), (90, "90-days")]:
            config_set.add_config(SynthRadConfig(
                name=f"followup_{days}_days",
                description=f"{days}-day follow-up interval",
                output_dir=f"./research/followup_{days}_days",
                num_patients=20,
                follow_up=True,
                follow_up_days=days,
                studies_per_patient=4,
                tags=["followup", "interval-study", tag]
            ))
        
        # Lobe-specific studies
        for lobe, tag in [("RUL", "right-upper"), ("LLL", "left-lower")]:
            config_set.add_config(SynthRadConfig(
                name=f"{lobe.lower()}_lobe",
                description=f"{lobe} lobe cases only",
                output_dir=f"./research/{lobe.lower()}_lobe",
                num_patients=30,
                lobe=lobe,
                follow_up=True,
                studies_per_patient=3,
                tags=["lobe-study", tag]
            ))
        
        return config_set
    
    @staticmethod
    def load_from_json(file_path: str) -> ConfigSet:
        """Load configuration set from JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        config_set = ConfigSet(
            name=data.get("name", "Unnamed Config Set"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )
        
        for config_data in data.get("configurations", []):
            config = SynthRadConfig(**config_data)
            config_set.add_config(config)
        
        return config_set
    
    @staticmethod
    def load_from_yaml(file_path: str) -> ConfigSet:
        """Load configuration set from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        config_set = ConfigSet(
            name=data.get("name", "Unnamed Config Set"),
            description=data.get("description", ""),
            metadata=data.get("metadata", {})
        )
        
        for config_data in data.get("configurations", []):
            config = SynthRadConfig(**config_data)
            config_set.add_config(config)
        
        return config_set
    
    @staticmethod
    def save_to_json(config_set: ConfigSet, file_path: str):
        """Save configuration set to JSON file."""
        with open(file_path, 'w') as f:
            json.dump(config_set.to_dict(), f, indent=2)
    
    @staticmethod
    def save_to_yaml(config_set: ConfigSet, file_path: str):
        """Save configuration set to YAML file."""
        with open(file_path, 'w') as f:
            yaml.dump(config_set.to_dict(), f, default_flow_style=False, indent=2)


def create_config_from_dict(data: Dict[str, Any]) -> SynthRadConfig:
    """Create a SynthRadConfig from a dictionary with legacy key mapping."""
    # Map legacy keys to new keys
    key_mapping = {
        "n": "num_patients",
        "out": "output_dir",
        "stage-dist": "stage_distribution",
        "follow-up": "follow_up",
        "follow-up-days": "follow_up_days",
        "studies-per-patient": "studies_per_patient",
        "response-dist": "response_distribution",
        "radlex-dist": "radlex_distribution",
        "legacy-mode": "legacy_mode",
        "jsonl": "jsonl_filename"
    }
    
    mapped_data = {}
    for old_key, new_key in key_mapping.items():
        if old_key in data:
            mapped_data[new_key] = data[old_key]
    
    # Add any other keys that don't need mapping
    for key, value in data.items():
        if key not in key_mapping:
            mapped_data[key] = value
    
    return SynthRadConfig(**mapped_data)
