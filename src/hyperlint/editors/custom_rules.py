import os
from typing import Dict, List, Literal

import diskcache
import dspy
from loguru import logger
from pydantic import BaseModel, Field

from ..config import DEFAULT_RULE_VIOLATION_MODEL
from .core import BaseEditor, DeleteLineIssue, ReplaceLineFixableIssue

# Setup cache and instructor
cache = diskcache.Cache("./data/cache/rules_editor")


openapi_key = os.environ["OPENAI_API_KEY"]
lm = dspy.LM(DEFAULT_RULE_VIOLATION_MODEL, api_key=openapi_key)


class RulesViolation(BaseModel):
    line_number: int
    issue_message: str
    resolution: Literal["edit_line", "delete_line", "flag_line"]


class RulesViolations(dspy.Signature):
    """Provide a list of violations to the supplied rule.

    If a line can simply be edited to be correct, use the resolution:'edit_line'
    if a line can be deleted entirely use the resolution: 'delete_line'
    If a line or issue has a more nuanced problem that isn't straightforward to fix without guidance, use the resolution:'flag_line'
    """

    text_with_line_numbers: str = dspy.InputField()
    rule_content: str = dspy.InputField()
    rule_name: str = dspy.InputField()
    rules_violations: List[RulesViolation] = dspy.OutputField()


_get_issues = dspy.ChainOfThought(RulesViolations)
_get_issues.set_lm(lm)


def get_issues(text, rule_content, rule_name) -> List[RulesViolation]:
    model_response = _get_issues(
        text_with_line_numbers=text,
        rule_content=rule_content,
        rule_name=rule_name,
    )
    return model_response.rules_violations


class RulesEditor(BaseEditor):
    """
    Editor that applies AI-powered rules from a directory.

    Each rule file contains simple markdown instructions that are processed
    using AI to apply changes to the document.
    """

    applied_rules: List[str] = Field(default_factory=list)

    def prerun_checks(self) -> bool:
        """
        Validate that the rules directory exists and contains valid rules.
        """
        rules_dir = self.config.custom_rules.rules_directory

        if not rules_dir.exists():
            logger.error(f"Rules directory does not exist: {rules_dir}")
            return False

        if not rules_dir.is_dir():
            logger.error(f"Rules directory is not a directory: {rules_dir}")
            return False

        rules = self._load_rules()
        if not rules:
            logger.warning(
                f"No rules found in directory: {self.config.custom_rules.rules_directory}"
            )
            return False

        logger.success(
            f"Found {len(rules)} rules in directory: {self.config.custom_rules.rules_directory}"
        )
        return True

    def _load_rules(self) -> Dict[str, str]:
        """
        Load all markdown rule files from the rules directory.

        Returns:
            Dict[str, str]: Dictionary of rule name to rule content.
        """
        rules = {}
        rules_dir = self.config.custom_rules.rules_directory

        for file_path in rules_dir.glob("*.md"):
            rule_name = file_path.stem
            try:
                with open(file_path, "r") as f:
                    rule_content = f.read()
                rules[rule_name] = rule_content
                logger.info(f"Loaded rule: {rule_name}")
            except Exception as e:
                logger.error(f"Error loading rule {rule_name}: {e}")

        return rules

    def _filter_rules(self, rules: Dict[str, str]) -> Dict[str, str]:
        """
        Filter rules based on include and exclude lists.

        Args:
            rules: Dictionary of rule name to rule content.

        Returns:
            Dict[str, str]: Filtered dictionary of rules.
        """
        filtered_rules = {}

        # If config.include_rules is specified, only include those rules
        if self.config.custom_rules.include_rules:
            for rule_name in self.config.custom_rules.include_rules:
                if rule_name in rules:
                    filtered_rules[rule_name] = rules[rule_name]
                else:
                    logger.warning(f"Included rule not found: {rule_name}")
        else:
            # Otherwise, include all rules except those in config.exclude_rules
            filtered_rules = {
                rule_name: rule_content
                for rule_name, rule_content in rules.items()
                if rule_name not in self.config.custom_rules.exclude_rules
            }

            # Log excluded rules
            for rule_name in self.config.custom_rules.exclude_rules:
                if rule_name in rules:
                    logger.info(f"Excluding rule: {rule_name}")
                else:
                    logger.warning(f"Excluded rule not found: {rule_name}")

        return filtered_rules

    def apply_rule(self, rule_content: str, rule_name: str) -> None:
        """
        Apply a single rule to the document using AI.

        Args:
            rule_content: The content of the rule file.
            rule_name: The name of the rule.
        """
        text = self.get_text_with_line_numbers()
        line_lookup = self.get_line_number_lookup()
        issues: List[RulesViolation] = get_issues(text, rule_content, rule_name)

        if not issues:
            logger.info(f"No issues found for rule: {rule_name}")
            return

        # Process each violation and create appropriate issue objects
        for violation in issues:
            if violation.resolution == "edit_line":
                self.add_replacement(
                    ReplaceLineFixableIssue(
                        line=violation.line_number,
                        existing_content=line_lookup[violation.line_number],
                        issue_message=[
                            f"Rule '{rule_name}': {violation.issue_message}"
                        ],
                    )
                )
            elif violation.resolution == "delete_line":
                self.add_deletion(
                    DeleteLineIssue(
                        line=violation.line_number,
                        issue_message=[
                            f"Rule '{rule_name}': {violation.issue_message}"
                        ],
                        existing_content=line_lookup[violation.line_number],
                    )
                )

        # Add to applied rules
        self.applied_rules.append(rule_name)
        logger.success(
            f"Applied rule: {rule_name} and found {len(issues)} proposed changes"
        )

    def collect_issues(self) -> None:
        """
        Load rules, filter them, and apply them to the document.
        Only runs if there are rules available.
        """
        # Load all rules
        rules = self._load_rules()
        logger.debug(f"Loaded {len(rules)} rules")
        # Filter rules based on include/exclude lists
        filtered_rules = self._filter_rules(rules)

        if not filtered_rules:
            logger.warning("No rules to apply after filtering")
            return

        logger.info(f"Applying {len(filtered_rules)} rules...")

        # Apply rules in alphabetical order
        for rule_name, rule_content in sorted(filtered_rules.items()):
            logger.info(f"Applying rule: {rule_name}")
            self.apply_rule(rule_content, rule_name)
