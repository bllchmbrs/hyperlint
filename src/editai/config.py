from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
from loguru import logger

@dataclass
class SimpleConfig:
    """Simplified configuration container"""
    
    # Editor configurations
    ai: Dict[str, Any] = field(default_factory=dict)
    vale: Dict[str, Any] = field(default_factory=dict)
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    images: Dict[str, Any] = field(default_factory=dict)
    links: Dict[str, Any] = field(default_factory=dict)
    
    # Global settings
    recursive: bool = True
    dry_run: bool = False
    include_pattern: str = "*.md"
    exclude_patterns: List[str] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, path: Path) -> 'SimpleConfig':
        """Load configuration from YAML file"""
        if not path.exists():
            logger.warning(f"Config file not found: {path}. Using defaults.")
            return cls()
            
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            # Create config with data, falling back to defaults
            config = cls()
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                else:
                    logger.warning(f"Unknown config key: {key}")
            
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return cls()
    
    def get_editor_config(self, editor_name: str) -> Dict[str, Any]:
        """Get configuration for a specific editor"""
        return getattr(self, editor_name, {})
    
    def merge_with_cli(self, cli_args: Dict[str, Any]) -> Dict[str, Any]:
        """Merge CLI arguments with config values"""
        # Start with global settings
        merged = {
            'recursive': self.recursive,
            'dry_run': self.dry_run,
            'include_pattern': self.include_pattern,
            'exclude_patterns': self.exclude_patterns
        }
        
        # Add editor-specific configs
        merged.update({
            'ai': self.ai,
            'vale': self.vale,
            'custom_rules': self.custom_rules,
            'images': self.images,
            'links': self.links
        })
        
        # Override with CLI args (only non-None values)
        for key, value in cli_args.items():
            if value is not None:
                merged[key] = value
        
        return merged

def find_config_file() -> Optional[Path]:
    """Find configuration file in standard locations"""
    search_paths = [
        Path.cwd() / "editai.yaml",
        Path.cwd() / ".editai.yaml",
        Path.home() / ".config" / "editai" / "config.yaml",
    ]
    
    for path in search_paths:
        if path.exists():
            return path
    return None

def create_default_config(path: Path = Path.cwd() / "editai.yaml"):
    """Create a default configuration file"""
    
    default_config = """# EditAI Configuration
ai:
  model: "openai/o3-mini-2025-01-31"
  fallback_model: "anthropic/claude-3-haiku-20240307"
  temperature: 0.25
  max_tokens: 2048
  cache_enabled: true
  
vale:
  config_path: "./.vale.ini"
  
custom_rules:
  rules_directory: "./rules"
  enabled_rules:
    - "passive_voice"
    - "bullet_consistency"
    
images:
  default_url_prefix: "/images"
  caption_generation:
    enabled: true
    model: "claude-3-haiku-20240307"
    
links:
  default_indices:
    - "docs-index"
  auto_create_indices: true

# Global settings
recursive: true
dry_run: false
include_pattern: "*.md"
exclude_patterns: []
"""
    
    with open(path, 'w') as f:
        f.write(default_config)
    
    return path