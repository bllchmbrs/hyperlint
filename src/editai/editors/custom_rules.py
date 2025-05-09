from pathlib import Path
from typing import List, Dict, Optional
import os

from loguru import logger
from pydantic import Field

from .core import BaseEditor, InsertLineIssue, DeleteLineIssue
from .ai import fix_line_edit, LineEdit


class CustomRuleEditor(BaseEditor):
    """
    Editor that applies custom plaintext markdown rules from a directory.
    
    Each rule file contains simple markdown instructions that are processed 
    using the AI editor infrastructure to apply changes to the document.
    """
    
    rules_directory: Path
    include_rules: List[str] = Field(default_factory=list)
    exclude_rules: List[str] = Field(default_factory=list)
    applied_rules: List[str] = Field(default_factory=list)
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
    
    def apply_rule(self, rule_content: str, rule_name: str) -> None:
        """
        Apply a single rule to the document using AI.
        
        Args:
            rule_content: The content of the rule file.
            rule_name: The name of the rule.
        """
        text_with_line_numbers = self.get_text_with_line_numbers()
        line_lookup = self.get_line_number_lookup()
        
        # Create a synthetic LineEdit object to use with the existing fix_line_edit function
        # We'll set the starting/ending lines to cover the entire document
        line_edit = LineEdit(
            starting_affected_line=1,
            ending_affected_line=len(line_lookup),
            issue_message=f"Apply rule: {rule_name}",
            resolution="edit"
        )
        
        # Construct prompt for AI
        prompt = f"""You are an expert editor following specific editing instructions.
        
Here is the text with line numbers:
<text>
{text_with_line_numbers}
</text>

Here is the editing instruction to apply:
<rule name="{rule_name}">
{rule_content}
</rule>

Please follow these instructions exactly:
1. Identify lines that need changes based on the rule.
2. Focus only on implementing this specific rule.
3. Return the corrected version of each affected line.
4. If a line doesn't need changes, don't modify it.
5. Preserve the overall structure and line breaks of the document.
"""
        
        # Use the fix_line_edit function to get the corrected text
        corrected_text = fix_line_edit(line_edit, self.get_text())
        
        if corrected_text is None:
            logger.error(f"Failed to apply rule: {rule_name}")
            return
        
        # If we're in dry run mode, just log the changes
        if self.dry_run:
            logger.info(f"Dry run - Rule '{rule_name}' would produce these changes:")
            logger.info(f"Original:\n{self.get_text()}")
            logger.info(f"Modified:\n{corrected_text}")
            return
        
        # Process the corrected text
        original_lines = self.get_text().splitlines()
        corrected_lines = corrected_text.splitlines()
        
        # Detect differences and create replacements/insertions/deletions
        self._process_diff(original_lines, corrected_lines, rule_name)
        
        # Add to applied rules
        self.applied_rules.append(rule_name)
        logger.success(f"Applied rule: {rule_name}")
    
    def _process_diff(self, original_lines: List[str], corrected_lines: List[str], rule_name: str) -> None:
        """
        Process differences between original and corrected lines.
        
        This is a simple implementation that detects basic changes. A more sophisticated
        diff algorithm could be implemented for better results.
        
        Args:
            original_lines: List of original lines.
            corrected_lines: List of corrected lines.
            rule_name: Name of the rule being applied.
        """
        # If line counts are different, handle as complete replacement
        if len(original_lines) != len(corrected_lines):
            logger.info(f"Line count changed from {len(original_lines)} to {len(corrected_lines)}")
            
            # Delete all original lines
            for i, line in enumerate(original_lines, 1):
                self.add_deletion(
                    DeleteLineIssue(
                        line=i,
                        existing_content=line,
                        issue_message=[f"Rule '{rule_name}' replacement"]
                    )
                )
            
            # Insert all new lines
            for i, line in enumerate(corrected_lines, 1):
                self.add_insertion(
                    InsertLineIssue(
                        line=i,
                        insert_content=line
                    )
                )
            return
        
        # Line counts are the same, look for individual line changes
        changes = 0
        for i, (original, corrected) in enumerate(zip(original_lines, corrected_lines), 1):
            if original != corrected:
                # Delete original line
                self.add_deletion(
                    DeleteLineIssue(
                        line=i,
                        existing_content=original,
                        issue_message=[f"Rule '{rule_name}' edit"]
                    )
                )
                
                # Insert corrected line
                self.add_insertion(
                    InsertLineIssue(
                        line=i,
                        insert_content=corrected
                    )
                )
                changes += 1
        
        logger.info(f"Applied {changes} line changes for rule '{rule_name}'")
    
    def collect_issues(self) -> None:
        """
        Load rules, filter them, and apply them to the document.
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