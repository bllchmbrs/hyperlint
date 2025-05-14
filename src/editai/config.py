from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from loguru import logger
from pydantic import BaseModel, DirectoryPath, Field, FilePath


class AIConfig(BaseModel):
    model: str = "openai/o3-mini-2025-01-31"
    fallback_model: str = "anthropic/claude-3-haiku-20240307"
    temperature: float = Field(0.25, ge=0.0, le=1.0)
    max_tokens: int = Field(2048, gt=0)
    cache_enabled: bool = True


class ValeConfig(BaseModel):
    config_path: FilePath = Field(default=Path("./.vale.ini"))


class CustomRulesConfig(BaseModel):
    rules_directory: DirectoryPath = Field(default=Path("./rules"))
    enabled_rules: List[str] = Field(
        default_factory=lambda: ["passive_voice", "bullet_consistency"]
    )


class ImageModelConfig(BaseModel):
    enabled: bool = True
    model: str = "claude-3-haiku-20240307"


class ImageConfig(BaseModel):
    default_url_prefix: str = "/images"
    caption_generation: ImageModelConfig = Field(default_factory=ImageModelConfig)
    location_detection: ImageModelConfig = Field(
        default_factory=lambda: ImageModelConfig(model="claude-3-opus-20240229")
    )
    name_generation: ImageModelConfig = Field(default_factory=ImageModelConfig)
    amble_generation: ImageModelConfig = Field(default_factory=ImageModelConfig)


class LinksConfig(BaseModel):
    default_indices: List[str] = Field(default_factory=lambda: ["docs-index"])
    auto_create_indices: bool = True


class SimpleConfig(BaseModel):
    """Configuration container with validation"""

    # Editor configurations
    ai: AIConfig = Field(default_factory=AIConfig)
    vale: ValeConfig = Field(default_factory=ValeConfig)
    custom_rules: CustomRulesConfig = Field(default_factory=CustomRulesConfig)
    images: ImageConfig = Field(default_factory=ImageConfig)
    links: LinksConfig = Field(default_factory=LinksConfig)

    # Global settings
    recursive: bool = True
    dry_run: bool = False
    include_pattern: str = "*.md"
    exclude_patterns: List[str] = Field(default_factory=list)
    enabled_editors: List[Literal["ai", "vale", "custom_rules", "images", "links"]] = (
        Field(default_factory=lambda: ["ai", "vale", "custom_rules", "images", "links"])
    )

    @classmethod
    def from_yaml(cls, path: Path) -> "SimpleConfig":
        """Load configuration from YAML file"""
        if not path.exists():
            logger.warning(f"Config file not found: {path}. Using defaults.")
            return cls()

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}

            # Create config with data, using model validation
            return cls.model_validate(data)

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return cls()

    def get_editor_config(self, editor_name: str) -> Dict[str, Any]:
        """Get configuration for a specific editor"""
        if editor_name not in self.enabled_editors:
            return {}
        return getattr(self, editor_name).model_dump()

    def merge_with_cli(self, cli_args: Dict[str, Any]) -> Dict[str, Any]:
        """Merge CLI arguments with config values"""
        # Start with all current settings as a dict
        merged = self.model_dump()

        # Override with CLI args (only non-None values)
        for key, value in cli_args.items():
            if value is not None:
                if key in merged:
                    merged[key] = value
                else:
                    logger.warning(f"Unknown CLI argument: {key}")

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


def create_default_config(path: Path = Path.cwd() / "editai.yaml") -> Path:
    """Create a default configuration file"""

    # Create a default config and dump it to YAML
    config = SimpleConfig()
    yaml_str = yaml.dump(config.model_dump(), sort_keys=False)

    # Add a header comment
    final_content = "# EditAI Configuration\n" + yaml_str

    with open(path, "w") as f:
        f.write(final_content)

    return path
