from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from loguru import logger
from pydantic import BaseModel, DirectoryPath, Field, FilePath

DEFAULT_CONFIG_PATH = Path.cwd() / ".hyperlint.yaml"
DEFAULT_INI_PATH = Path.cwd() / ".vale.ini"
DEFAULT_CUSTOM_RULES_PATH = Path.cwd() / "rules"


class ValeConfig(BaseModel):
    config_path: FilePath = Field(default=Path(DEFAULT_INI_PATH))


class CustomRulesConfig(BaseModel):
    rules_directory: DirectoryPath = Field(default=Path(DEFAULT_CUSTOM_RULES_PATH))
    enabled_rules: List[str] = Field(default_factory=lambda: [])  # all rules


class SimpleConfig(BaseModel):
    """Configuration container with validation"""

    # Editor configurations
    vale: ValeConfig = Field(default_factory=ValeConfig)
    custom_rules: CustomRulesConfig = Field(default_factory=CustomRulesConfig)

    # Global settings

    dry_run: bool = False
    require_approval: bool = True
    log_approvals: bool = True
    enabled_editors: List[Literal["vale", "custom_rules"]] = Field(
        default_factory=lambda: ["vale", "custom_rules"]
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
        Path.cwd() / "hyperlint.yaml",
        Path.cwd() / ".hyperlint.yaml",
        Path.home() / ".config" / "hyperlint" / "config.yaml",
    ]

    for path in search_paths:
        if path.exists():
            return path
    return None


def create_default_config(path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Create a default configuration file"""

    # Create a default config and dump it to YAML
    config = SimpleConfig()
    yaml_str = yaml.dump(config.model_dump(), sort_keys=False)

    # Add a header comment
    final_content = "# Hyperlint Configuration\n" + yaml_str

    with open(path, "w") as f:
        f.write(final_content)
