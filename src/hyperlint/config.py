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
    approval_type: Literal["console", "image", "silent"] = "console"

    hyperlint_dir: DirectoryPath = Field(default=Path(DEFAULT_HYPERLINT_STORAGE_DIR))
    enabled_editors: List[Literal["vale", "custom_rules"]] = Field(
        default_factory=lambda: ["vale", "custom_rules"]  # type: ignore
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

    def get_storage_data_dir(self) -> Path:
        return self.hyperlint_dir / "storage_data"

    def get_judge_data_dir(self) -> Path:
        return self.hyperlint_dir / "judge_data"

    def ensure_storage_dirs(self):
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

        # Create storage data directory
        storage_data_dir = self.get_storage_data_dir()
        if not storage_data_dir.exists():
            storage_data_dir.mkdir(exist_ok=True)
            logger.info(f"Created storage data directory at {storage_data_dir}")


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


def create_default_rules(rules_dir: Path) -> None:
    """Create default grammar rules directory and files"""
    rules_dir.mkdir(parents=True, exist_ok=True)

    # Default grammar rules
    default_rules = {
        "passive_voice.md": """# Convert Passive Voice to Active Voice

Find instances of passive voice in the document and convert them to active voice. 
Focus particularly on phrases like "is being done", "was performed", "has been completed", etc.
Convert them to their active equivalents.

For example:
- "The test is being performed" → "We are performing the test"
- "The data was analyzed" → "We analyzed the data"
- "The code has been reviewed" → "The team reviewed the code"

Only change sentences that would be clearer in active voice.""",
        "sentence_clarity.md": """# Improve Sentence Clarity

Identify and revise sentences that are unclear, overly complex, or difficult to understand.

Focus on:
- Breaking up run-on sentences
- Simplifying complex sentences with multiple clauses
- Removing unnecessary words and phrases
- Clarifying ambiguous pronoun references
- Using concrete language instead of vague terms

Make the text more readable while preserving the original meaning.""",
        "paragraph_structure.md": """# Fix Paragraph Structure

Ensure paragraphs have proper structure and flow.

Each paragraph should:
- Focus on a single main idea
- Start with a clear topic sentence when appropriate
- Have supporting sentences that relate to the main idea
- End with a concluding or transitional sentence when needed
- Be an appropriate length (not too short or too long)

Split overly long paragraphs and combine very short related paragraphs.""",
        "word_choice.md": """# Improve Word Choice

Replace weak, vague, or repetitive words with more precise and engaging alternatives.

Look for:
- Overused words like "very", "really", "quite"
- Vague terms like "thing", "stuff", "somewhat"
- Repetitive word usage within paragraphs
- Weak verbs that could be stronger
- Technical jargon that could be simplified for the audience

Choose words that are more specific, vivid, and appropriate for the context.""",
        "transitions.md": """# Add Smooth Transitions

Add appropriate transition words and phrases to improve the flow between sentences and paragraphs.

Common transition types:
- Addition: furthermore, moreover, additionally
- Contrast: however, nevertheless, on the other hand
- Cause/Effect: therefore, consequently, as a result
- Time: meanwhile, subsequently, previously
- Examples: for instance, specifically, in particular

Ensure transitions make logical sense and enhance readability.""",
    }

    for filename, content in default_rules.items():
        rule_path = rules_dir / filename
        if not rule_path.exists():
            with open(rule_path, "w") as f:
                f.write(content)


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
