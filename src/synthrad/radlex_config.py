"""
Configuration for RadLex integration in synthetic reports.
Provides simple configuration for anatomic mapping.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class RadLexConfig:
    """Configuration for RadLex anatomic mapping."""
    
    # Core settings
    enabled: bool = True
    api_key: Optional[str] = None
    cache_file: Optional[str] = None
    
    # Caching settings
    enable_caching: bool = True
    cache_dir: str = "./radlex_cache"
    
    # API settings
    request_timeout: int = 30
    max_retries: int = 3
    
    # Rate limiting settings (BioPortal free tier limits)
    rate_limit_per_second: float = 1.0  # 1 call per second
    rate_limit_per_minute: int = 60     # 60 calls per minute
    
    def __post_init__(self):
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
            enable_caching=os.environ.get("RADLEX_CACHE_ENABLED", "true").lower() == "true",
            cache_dir=os.environ.get("RADLEX_CACHE_DIR", "./radlex_cache"),
            request_timeout=int(os.environ.get("RADLEX_TIMEOUT", "30")),
            max_retries=int(os.environ.get("RADLEX_MAX_RETRIES", "3")),
            rate_limit_per_second=float(os.environ.get("RADLEX_RATE_LIMIT_PER_SECOND", "1.0")),
            rate_limit_per_minute=int(os.environ.get("RADLEX_RATE_LIMIT_PER_MINUTE", "60"))
        )

def get_config(config_name: Optional[str] = None, config_file: Optional[str] = None) -> RadLexConfig:
    """
    Get RadLex configuration.
    
    Args:
        config_name: Ignored (kept for compatibility)
        config_file: Path to JSON config file
    
    Returns:
        RadLexConfig instance
    """
    if config_file and os.path.exists(config_file):
        return RadLexConfig.from_json(config_file)
    
    # Default to environment-based config
    return RadLexConfig.from_env()

def create_config_template(filepath: str, config_name: str = "standard"):
    """Create a configuration template file."""
    config = RadLexConfig()
    config.to_json(filepath)
    print(f"Created RadLex config template at: {filepath}")

# Example usage and documentation
EXAMPLE_CONFIG = {
    "enabled": True,
    "api_key": "your_bioportal_api_key_here",
    "cache_file": "./radlex_cache/concepts.json",
    "enable_caching": True,
    "cache_dir": "./radlex_cache",
    "request_timeout": 30,
    "max_retries": 3,
    "rate_limit_per_second": 1.0,
    "rate_limit_per_minute": 60
}
