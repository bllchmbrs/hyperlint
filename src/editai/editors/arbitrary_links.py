from typing import Optional

import diskcache
import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field, HttpUrl

from .core import BaseEditor, ReplaceLineFixableIssue

cache = diskcache.Cache("./data/cache/editing")
patched_client = instructor.from_litellm(completion=completion)


class ArbitraryLink(BaseModel):
    """A link to be inserted into the text."""

    url: HttpUrl = Field(description="The URL to link to")
    description: str = Field(description="Description of what this link points to")


class LinkPlacement(BaseModel):
    """A suggested placement for a link in the text."""

    line_number: int = Field(
        description="The line number where the link should be placed"
    )
    original_text: str = Field(description="The original line text")
    reasoning: str = Field(description="Reasoning for why this is a good placement")


class LinkRewrite(BaseModel):
    """A rewritten line with a link inserted."""

    rewritten_text: str = Field(
        description="The line rewritten to include the link in a natural way"
    )


class ArbitraryLinkEditor(BaseEditor):
    """Editor for interactively inserting arbitrary links provided by the user."""

    def prerun_checks(self) -> bool:
        # No specific pre-run checks needed
        return True

    def collect_issues(self) -> None:
        """Run the REPL to collect links and find placements."""
        self.run_link_repl()

    def run_link_repl(self) -> None:
        """Run the interactive REPL for entering links."""
        print("=== Arbitrary Link Editor REPL ===")
        print("Enter links to add to your document. Type 'exit' to finish.")

        text_with_line_numbers = self.get_text_with_line_numbers()
        line_lookup = self.get_line_number_lookup()

        while True:
            # Get user input for link
            link_url = input("\nEnter link URL (or 'exit' to finish): ")
            if link_url.lower() == "exit":
                break

            # Get description
            description = input("Enter link description: ")

            try:
                # Create link object
                link = ArbitraryLink(url=link_url, description=description)

                # Find placement for the link
                placement = self.find_link_placement(link, text_with_line_numbers)

                if placement and placement.line_number in line_lookup:
                    # Show placement to user
                    print(f"\nSuggested placement at line {placement.line_number}:")
                    print(f"Original: {placement.original_text}")
                    print(f"Reasoning: {placement.reasoning}")

                    # Confirm with user
                    confirm = input("Apply this link placement? (y/n): ")
                    if confirm.lower() == "y":
                        # Create a replacement issue
                        self.add_replacement_for_link(link, placement, line_lookup)
                        print("Link placement added.")
                    else:
                        print("Link placement skipped.")
                else:
                    print("No suitable placement found for this link.")
            except Exception as e:
                logger.error(f"Error processing link: {e}")
                print(f"Error: {e}")

    def find_link_placement(
        self, link: ArbitraryLink, text_with_line_numbers: str
    ) -> Optional[LinkPlacement]:
        """Find the best placement for a link in the document."""
        prompt = f"""You are an expert technical writer.

        You are given a link URL and description, and text with line numbers.

        Your job is to find the best location in the text to place this link naturally.

        <text_with_line_numbers>
        {text_with_line_numbers}
        </text_with_line_numbers>

        <link>
        URL: {link.url}
        Description: {link.description}
        </link>

        Find the single best line where this link would be most relevant and helpful.
        The link should enhance the reader's understanding and be placed naturally in the text.
        You must only point to lines of text, not code lines or empty lines.
        NEVER MODIFY CODE LINES.

        Return your response as a JSON with the following structure:
        {{
          "line_number": The line number to place the link (as an integer),
          "original_text": "The original text of that line",
          "reasoning": "Why this is a good placement for the link"
        }}
        """

        # Use AI to find placement
        try:
            response = patched_client.chat.completions.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0.25,
                messages=[{"role": "user", "content": prompt}],
                response_model=LinkPlacement,
            )
            # Ensure line_number is an integer
            if isinstance(response.line_number, str):
                try:
                    response.line_number = int(response.line_number)
                except ValueError:
                    logger.error(
                        f"Invalid line number returned: {response.line_number}"
                    )
                    return None

            logger.info(f"Found link placement at line {response.line_number}")
            return response
        except Exception as e:
            logger.exception("Error finding link placement", error=e)
            return None

    def add_replacement_for_link(
        self, link: ArbitraryLink, placement: LinkPlacement, line_lookup: dict
    ) -> None:
        """Create a replacement issue for the link placement."""
        # Generate replacement text with link inserted
        rewritten_text = self.generate_link_insertion(link, placement.original_text)

        # Create ReplaceLineFixableIssue with custom rewritten text
        issue = ReplaceLineFixableIssue(
            line=placement.line_number,
            issue_message=[
                f"Insert link to {link.url} described as: {link.description}"
            ],
            existing_content=placement.original_text,
        )

        # Override the fix method to return our rewritten text directly
        original_fix = issue.fix
        issue.fix = lambda: rewritten_text

        self.add_replacement(issue)
        logger.success(f"Added replacement for line {placement.line_number}")

    @cache.memoize()
    def generate_link_insertion(self, link: ArbitraryLink, original_text: str) -> str:
        """Generate a rewritten line with the link naturally inserted."""
        prompt = f"""You are an expert technical writer.

        You need to rewrite this line to naturally include a link in Markdown format.

        <original_line>
        {original_text}
        </original_line>

        <link>
        URL: {link.url}
        Description: {link.description}
        </link>

        Rewrite the line to include the link in a natural way. Use Markdown format for the link: [text](url).
        The link should be seamlessly integrated into the text.
        Return only the rewritten line without any explanation.
        """

        try:
            response = patched_client.chat.completions.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0.25,
                messages=[{"role": "user", "content": prompt}],
                response_model=LinkRewrite,
            )
            return response.rewritten_text
        except Exception as e:
            logger.exception("Error generating link insertion", error=e)
            return original_text
