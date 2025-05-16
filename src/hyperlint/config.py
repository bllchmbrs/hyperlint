from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from loguru import logger
from pydantic import BaseModel, DirectoryPath, Field, FilePath

DEFAULT_CONFIG_PATH = Path.cwd() / "hyperlint-config.yaml"
DEFAULT_INI_PATH = Path.cwd() / ".vale.ini"
DEFAULT_CUSTOM_RULES_PATH = Path.cwd() / "rules"
DEFAULT_HYPERLINT_STORAGE_DIR = Path.cwd() / ".hyperlint"

DEFAULT_EDIT_MODEL = "anthropic/claude-3-haiku-20240307"
DEFAULT_APPROVER_MODEL = "openai/gpt-4.1-nano"
DEFAULT_RULE_VIOLATION_MODEL = "openai/gpt-4o-mini"

DELETE_LINE_MESSAGE = ">>>>>>>>>>>>>>DELETE<<<<<<<<<<<<<<<"


class ValeConfig(BaseModel):
    config_path: FilePath = Field(default=Path(DEFAULT_INI_PATH))


class CustomRulesConfig(BaseModel):
    rules_directory: DirectoryPath = Field(default=Path(DEFAULT_CUSTOM_RULES_PATH))
    include_rules: List[str] = Field(default_factory=list)
    exclude_rules: List[str] = Field(default_factory=list)


class SimpleConfig(BaseModel):
    """Configuration container with validation"""

    # Editor configurations
    vale: ValeConfig = Field(default_factory=ValeConfig)
    custom_rules: CustomRulesConfig = Field(default_factory=CustomRulesConfig)

    # Global settings

    dry_run: bool = False
    approval_mode: bool = True
    log_approvals: bool = True
    hyperlint_dir: DirectoryPath = Field(default=Path(DEFAULT_HYPERLINT_STORAGE_DIR))
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

    def get_judge_data_dir(self) -> Path:
        return self.hyperlint_dir / "edit_judge_data"

    def get_approval_path(self) -> Path:
        return self.get_judge_data_dir() / "editor_judge.jsonl"

    def get_image_judge_path(self):
        return self.hyperlint_dir / "image_judge.jsonl"

    def ensure_storage_dir(self):
        """
        Create the hyperlint directory if it doesn't exist and return its path.
        """
        if not self.hyperlint_dir.exists():
            self.hyperlint_dir.mkdir(exist_ok=True)
            logger.info(f"Created hyperlint directory at {self.hyperlint_dir}")

        # Create approvals directory
        approvals_dir = self.get_judge_data_dir()
        if not approvals_dir.exists():
            approvals_dir.mkdir(exist_ok=True)
            logger.info(f"Created approvals directory at {approvals_dir}")


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


def load_config(config_path: Optional[Path] = None) -> SimpleConfig:
    """
    Load configuration with fallbacks:
    1. Use specified config path if provided
    2. Search for config in standard locations
    3. Create default config if none found
    """
    if config_path and config_path.exists():
        return SimpleConfig.from_yaml(config_path)

    # Find config in standard locations
    found_config = find_config_file()
    if found_config:
        return SimpleConfig.from_yaml(found_config)

    # Use default config
    return SimpleConfig()
