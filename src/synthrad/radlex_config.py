"""
Configuration for RadLex integration in synthetic reports.
Provides JSON configuration options and settings management.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class RadLexConfig:
    """Configuration for RadLex integration."""
    
    # Core settings
    enabled: bool = True
    api_key: Optional[str] = None
    cache_file: Optional[str] = None
    
    # Enhancement settings
    enhance_terminology: bool = True
    enhance_artifacts: bool = True
    enhance_anatomy: bool = True
    
    # Text enhancement settings
    auto_enhance_reports: bool = True
    preserve_original_terms: bool = False
    max_enhancement_ratio: float = 0.3  # Max 30% of text can be enhanced
    
    # Caching settings
    enable_caching: bool = True
    cache_dir: str = "./radlex_cache"
    
    # API settings
    request_timeout: int = 30
    max_retries: int = 3
    
    # Rate limiting settings (BioPortal free tier limits)
    rate_limit_per_second: float = 1.0  # 1 call per second
    rate_limit_per_minute: int = 60     # 60 calls per minute
    
    # Concept categories to use
    concept_categories: List[str] = None
    
    def __post_init__(self):
        if self.concept_categories is None:
            self.concept_categories = [
                "lung_findings",
                "lymph_nodes", 
                "pleura",
                "mediastinum",
                "artifacts"
            ]
        
        if self.cache_file is None and self.enable_caching:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.cache_file = os.path.join(self.cache_dir, "radlex_concepts.json")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    def to_json(self, filepath: str):
        """Save config to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RadLexConfig':
        """Create config from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, filepath: str) -> 'RadLexConfig':
        """Load config from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> 'RadLexConfig':
        """Create config from environment variables."""
        return cls(
            enabled=os.environ.get("RADLEX_ENABLED", "true").lower() == "true",
            api_key=os.environ.get("BIOPORTAL_API_KEY"),
            cache_file=os.environ.get("RADLEX_CACHE_FILE"),
            enhance_terminology=os.environ.get("RADLEX_ENHANCE_TERMINOLOGY", "true").lower() == "true",
            enhance_artifacts=os.environ.get("RADLEX_ENHANCE_ARTIFACTS", "true").lower() == "true",
            enhance_anatomy=os.environ.get("RADLEX_ENHANCE_ANATOMY", "true").lower() == "true",
            auto_enhance_reports=os.environ.get("RADLEX_AUTO_ENHANCE", "true").lower() == "true",
            enable_caching=os.environ.get("RADLEX_CACHE_ENABLED", "true").lower() == "true",
            cache_dir=os.environ.get("RADLEX_CACHE_DIR", "./radlex_cache"),
            request_timeout=int(os.environ.get("RADLEX_TIMEOUT", "30")),
            max_retries=int(os.environ.get("RADLEX_MAX_RETRIES", "3")),
            rate_limit_per_second=float(os.environ.get("RADLEX_RATE_LIMIT_PER_SECOND", "1.0")),
            rate_limit_per_minute=int(os.environ.get("RADLEX_RATE_LIMIT_PER_MINUTE", "60"))
        )

# Predefined configurations
PREDEFINED_CONFIGS = {
    "minimal": RadLexConfig(
        enabled=True,
        enhance_terminology=False,
        enhance_artifacts=False,
        enhance_anatomy=False,
        auto_enhance_reports=False
    ),
    
    "standard": RadLexConfig(
        enabled=True,
        enhance_terminology=True,
        enhance_artifacts=True,
        enhance_anatomy=True,
        auto_enhance_reports=True,
        preserve_original_terms=False
    ),
    
    "aggressive": RadLexConfig(
        enabled=True,
        enhance_terminology=True,
        enhance_artifacts=True,
        enhance_anatomy=True,
        auto_enhance_reports=True,
        preserve_original_terms=False,
        max_enhancement_ratio=0.5
    ),
    
    "conservative": RadLexConfig(
        enabled=True,
        enhance_terminology=True,
        enhance_artifacts=False,
        enhance_anatomy=False,
        auto_enhance_reports=True,
        preserve_original_terms=True,
        max_enhancement_ratio=0.1
    )
}

def get_config(config_name: Optional[str] = None, config_file: Optional[str] = None) -> RadLexConfig:
    """
    Get RadLex configuration.
    
    Args:
        config_name: Name of predefined config ("minimal", "standard", "aggressive", "conservative")
        config_file: Path to JSON config file
    
    Returns:
        RadLexConfig instance
    """
    if config_file and os.path.exists(config_file):
        return RadLexConfig.from_json(config_file)
    
    if config_name and config_name in PREDEFINED_CONFIGS:
        return PREDEFINED_CONFIGS[config_name]
    
    # Default to environment-based config
    return RadLexConfig.from_env()

def create_config_template(filepath: str, config_name: str = "standard"):
    """Create a configuration template file."""
    config = PREDEFINED_CONFIGS.get(config_name, RadLexConfig())
    config.to_json(filepath)
    print(f"Created RadLex config template at: {filepath}")

# Example usage and documentation
EXAMPLE_CONFIG = {
    "enabled": True,
    "api_key": "your_bioportal_api_key_here",
    "cache_file": "./radlex_cache/concepts.json",
    "enhance_terminology": True,
    "enhance_artifacts": True,
    "enhance_anatomy": True,
    "auto_enhance_reports": True,
    "preserve_original_terms": False,
    "max_enhancement_ratio": 0.3,
    "enable_caching": True,
    "cache_dir": "./radlex_cache",
    "request_timeout": 30,
    "max_retries": 3,
    "concept_categories": [
        "lung_findings",
        "lymph_nodes",
        "pleura", 
        "mediastinum",
        "artifacts"
    ]
}
