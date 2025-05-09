import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

from loguru import logger
from pydantic import FilePath

from .core import (
    BaseEditor,
    DeleteLineIssue,
    InsertLineIssue,
    LineIssue,
    ReplaceLineFixableIssue,
)


@dataclass
class ActionC:
    Name: str = ""
    Params: Optional[List[str]] = None


@dataclass
class ValeAlert:
    Action: ActionC = field(default_factory=ActionC)
    Span: List[int] = field(default_factory=list)
    Check: str = ""
    Description: str = ""
    Link: str = ""
    Message: str = ""
    Severity: str = ""
    Match: str = ""
    Line: int = 0

    def as_line_issue(self) -> LineIssue:
        return LineIssue(
            line=self.Line,
            issue_message=[self.Check + " - " + self.Message],
        )


@dataclass
class ValeFileReport:
    issues: List[ValeAlert] = field(default_factory=list)

    def as_line_issues(self) -> List[LineIssue]:
        return [alert.as_line_issue() for alert in self.issues]


def check_vale_installation() -> bool:
    try:
        # Run 'vale --version' and capture the output
        result = subprocess.run(
            ["vale", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # If the command runs successfully, Vale is installed
        return True
    except FileNotFoundError:
        # If 'vale' command is not found, Vale is not installed or not in PATH
        return False
    except subprocess.CalledProcessError as e:
        # Handle other potential errors during the command execution
        logger.error(f"Error checking Vale installation: {e}")
        return False


def run_vale(text: str, vale_config_path: str) -> List[LineIssue]:
    if not check_vale_installation():
        logger.error("Vale is not installed or not found in PATH")
        return []

    vale_dir = os.environ.get("PROJECT_ROOT", os.getcwd())

    # Create a temporary file and ensure it's written and closed
    with tempfile.NamedTemporaryFile(
        dir=vale_dir, mode="w", suffix=".md", delete=False
    ) as temp_file:
        temp_file.write(text)
        temp_file_path = temp_file.name

    try:
        # Get the full path to vale
        vale_path = subprocess.check_output(["which", "vale"]).decode().strip()

        # Run vale with the correct working directory and environment
        result = subprocess.run(
            [vale_path, "--config", vale_config_path, "--output=JSON", temp_file_path],
            capture_output=True,
            text=True,
            cwd=vale_dir,
            env=dict(os.environ, PATH=os.environ.get("PATH", "")),
        )

        logger.success("Vale Result", result=result)
        # Parse the JSON output
        as_json = json.loads(result.stdout)
        logger.success("Vale JSON", json=as_json)

        # Convert JSON alerts into ValeAlert objects
        issues = []
        for file_path, alerts in as_json.items():
            logger.info(f"Found {len(alerts)} alerts in {file_path}")
            for alert in alerts:
                action = ActionC(
                    Name=alert.get("Action", {}).get("Name", ""),
                    Params=alert.get("Action", {}).get("Params"),
                )
                issues.append(
                    ValeAlert(
                        Action=action,
                        Span=alert.get("Span", []),
                        Check=alert.get("Check", ""),
                        Description=alert.get("Description", ""),
                        Link=alert.get("Link", ""),
                        Message=alert.get("Message", ""),
                        Severity=alert.get("Severity", ""),
                        Match=alert.get("Match", ""),
                        Line=alert.get("Line", 0),
                    )
                )

        report = ValeFileReport(issues=issues)
        logger.success("Vale Report", report=report)
        return report.as_line_issues()

    except Exception as e:
        logger.exception("Error running Vale", error=e)
        return []
    finally:
        # Clean up the temporary file
        try:
            os.remove(temp_file_path)
        except Exception as e:
            logger.exception("Error removing temporary file", error=e)


class ValeEditor(BaseEditor):
    vale_config_path: FilePath

    def prerun_checks(self) -> bool:
        vale_installed = check_vale_installation()
        vale_config_exists = os.path.exists(str(self.vale_config_path))
        return vale_installed and vale_config_exists

    def collect_issues(self) -> None:
        """Runs Vale and adds any reported issues as replacement issues."""
        issues = run_vale(self.get_text(), str(self.vale_config_path))
        if not issues:
            logger.info("Vale reported no issues.")
            return

        line_lookup = self.get_line_number_lookup()
        replacements_count = 0

        for issue in issues:
            # Ensure the line number from Vale is valid
            if issue.line in line_lookup:
                replacement_issue = ReplaceLineFixableIssue(
                    line=issue.line,
                    issue_message=issue.issue_message,
                    existing_content=line_lookup[issue.line],
                )
                self.add_replacement(replacement_issue)
                replacements_count += 1
            else:
                logger.warning(
                    f"Skipping Vale issue for line {issue.line} as it's not in the lookup (maybe out of bounds?). Message: {issue.issue_message}"
                )

        logger.success(
            f"Collected {replacements_count} line replacement issues from Vale."
        )
