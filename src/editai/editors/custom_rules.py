from pathlib import Path
from typing import Dict, List, Optional

import diskcache
import instructor
from litellm import completion
from loguru import logger
from pydantic import Field

from .core import BaseEditor, DeleteLineIssue, InsertLineIssue

# Setup cache and instructor
cache = diskcache.Cache("./data/cache/rules_editor")
patched_client = instructor.from_litellm(completion=completion)


class RulesEditor(BaseEditor):
    """
    Editor that applies AI-powered rules from a directory.

    Each rule file contains simple markdown instructions that are processed
    using AI to apply changes to the document.
    """

    rules_directory: Path
    include_rules: List[str] = Field(default_factory=list)
    exclude_rules: List[str] = Field(default_factory=list)
    applied_rules: List[str] = Field(default_factory=list)
    model: str = "anthropic/claude-3-haiku-20240307"
    dry_run: bool = False

    def prerun_checks(self) -> bool:
        """
        Validate that the rules directory exists and contains valid rules.
        """
        if not self.rules_directory.exists():
            logger.error(f"Rules directory does not exist: {self.rules_directory}")
            return False

        if not self.rules_directory.is_dir():
            logger.error(f"Rules directory is not a directory: {self.rules_directory}")
            return False

        rules = self._load_rules()
        if not rules:
            logger.warning(f"No rules found in directory: {self.rules_directory}")
            return False

        logger.success(f"Found {len(rules)} rules in directory: {self.rules_directory}")
        return True

    def _load_rules(self) -> Dict[str, str]:
        """
        Load all markdown rule files from the rules directory.

        Returns:
            Dict[str, str]: Dictionary of rule name to rule content.
        """
        rules = {}

        for file_path in self.rules_directory.glob("*.md"):
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

        # If include_rules is specified, only include those rules
        if self.include_rules:
            for rule_name in self.include_rules:
                if rule_name in rules:
                    filtered_rules[rule_name] = rules[rule_name]
                else:
                    logger.warning(f"Included rule not found: {rule_name}")
        else:
            # Otherwise, include all rules except those in exclude_rules
            filtered_rules = {
                rule_name: rule_content
                for rule_name, rule_content in rules.items()
                if rule_name not in self.exclude_rules
            }

            # Log excluded rules
            for rule_name in self.exclude_rules:
                if rule_name in rules:
                    logger.info(f"Excluding rule: {rule_name}")
                else:
                    logger.warning(f"Excluded rule not found: {rule_name}")

        return filtered_rules

    @cache.memoize()
    def _process_text_with_rule(
        self, text: str, rule_content: str, rule_name: str
    ) -> Optional[str]:
        """
        Process text using AI according to a rule.

        Args:
            text: The text to process
            rule_content: The content of the rule
            rule_name: The name of the rule

        Returns:
            The processed text, or None if processing failed
        """
        prompt = f"""You are an expert editor following specific editing instructions.

        Here is the text to edit:
        <text>
        {text}
        </text>

        Here is the editing rule to apply:
        <rule name="{rule_name}">
        {rule_content}
        </rule>

        Please follow these instructions exactly:
        1. Apply the specified rule to the text
        2. Return only the edited text without any comments or explanations
        3. Make only the changes required by the rule
        4. Preserve the overall structure and line breaks of the document
        """

        try:
            logger.info(
                f"Processing text with rule '{rule_name}' using model: {self.model}"
            )

            response = patched_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )

            processed_text = response.choices[0].message.content
            logger.success(f"Successfully processed text with rule: {rule_name}")
            return processed_text

        except Exception as e:
            logger.error(
                f"Error processing text with rule '{rule_name}': {e}", exc_info=True
            )
            return None

    def apply_rule(self, rule_content: str, rule_name: str) -> None:
        """
        Apply a single rule to the document using AI.

        Args:
            rule_content: The content of the rule file.
            rule_name: The name of the rule.
        """
        text = self.get_text()

        # Process text with rule
        corrected_text = self._process_text_with_rule(text, rule_content, rule_name)

        if corrected_text is None:
            logger.error(f"Failed to apply rule: {rule_name}")
            return

        # If we're in dry run mode, just log the changes
        if self.dry_run:
            logger.info(f"Dry run - Rule '{rule_name}' would produce these changes:")
            logger.info(f"Original:\n{text}")
            logger.info(f"Modified:\n{corrected_text}")
            return

        # Process the corrected text
        original_lines = text.splitlines()
        corrected_lines = corrected_text.splitlines()

        # Detect differences and create replacements/insertions/deletions
        self._process_diff(original_lines, corrected_lines, rule_name)

        # Add to applied rules
        self.applied_rules.append(rule_name)
        logger.success(f"Applied rule: {rule_name}")

    def _process_diff(
        self, original_lines: List[str], corrected_lines: List[str], rule_name: str
    ) -> None:
        """
        Process differences between original and corrected lines.

        Args:
            original_lines: List of original lines.
            corrected_lines: List of corrected lines.
            rule_name: Name of the rule being applied.
        """
        # If line counts are different, handle as complete replacement
        if len(original_lines) != len(corrected_lines):
            logger.info(
                f"Line count changed from {len(original_lines)} to {len(corrected_lines)}"
            )

            # Delete all original lines
            for i, line in enumerate(original_lines, 1):
                self.add_deletion(
                    DeleteLineIssue(
                        line=i,
                        existing_content=line,
                        issue_message=[f"Rule '{rule_name}' replacement"],
                    )
                )

            # Insert all new lines
            for i, line in enumerate(corrected_lines, 1):
                self.add_insertion(InsertLineIssue(line=i, insert_content=line))
            return

        # Line counts are the same, look for individual line changes
        changes = 0
        for i, (original, corrected) in enumerate(
            zip(original_lines, corrected_lines), 1
        ):
            if original != corrected:
                # Delete original line
                self.add_deletion(
                    DeleteLineIssue(
                        line=i,
                        existing_content=original,
                        issue_message=[f"Rule '{rule_name}' edit"],
                    )
                )

                # Insert corrected line
                self.add_insertion(InsertLineIssue(line=i, insert_content=corrected))
                changes += 1

        logger.info(f"Applied {changes} line changes for rule '{rule_name}'")

    def collect_issues(self) -> None:
        """
        Load rules, filter them, and apply them to the document.
        Only runs if there are rules available.
        """
        # Load all rules
        rules = self._load_rules()

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
