from typing import List

import diskcache
import instructor
import yaml
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field, HttpUrl
from smolcrawl.db import Page, TantivyIndexer

from .core import BaseEditor, LineIssue, ReplaceLineFixableIssue
from .utils import get_search_terms

cache = diskcache.Cache("./data/cache/editing")
patched_client = instructor.from_litellm(completion=completion)


class LinkLocation(BaseModel):
    """
    A link location that was found in the text.
    """

    line_number: int = Field(
        description="The line number to link to. This line number MUST refer to text "
    )
    url: HttpUrl = Field(description="The url to link to")
    instructions: str = Field(
        description="Instructions for how to rewrite the line to include the link. This should be a natural way to include the link in the text."
    )


class LinkLocations(BaseModel):
    """
    The reasoning for the list of link locations that were found in the text.

    A list of link locations that were found in the text.
    """

    reasoning: str = Field(description="The reasoning for the list of link locations")
    link_locations: List[LinkLocation] = Field(
        description="A list of link locations that were found in the text, should be lists of line numbers and urls"
    )


def internal_search(search_term: str, index_name: str):
    logger.info(f"Searching for {search_term} in {index_name}")
    db = TantivyIndexer(index_name)
    results = db.query(search_term)
    if not results:
        logger.error(f"No results found for search term {search_term}")
        return []
    return results


def find_link_locations(text: str, search_results: List[Page]) -> List[LinkLocation]:
    search_results_list = []
    for no, result in enumerate(search_results):
        internal_result = {"title": result.title, "url": result.url}
        search_results_list.append(
            f"<result number={no}>\n{yaml.dump(internal_result)}\n</result>"
        )
    search_results_string = "\n".join(search_results_list)
    prompt = f"""You are an expert technical writer.

    You are given a list of search results for a technical blog post or tutorial.
    
    You are also given text with line numbers.

    Your job is to find the best locations in the text to link to the search results.

    <text_with_line_numbers>
    {text}
    </text_with_line_numbers>

    <search_results>
    {search_results_string}
    </search_results>

    Return a list of dictionaries with the following keys:
    - line_number: the line number to link to
    - url: the url to link to

    Rules:
    - The line number MUST refer to text in the <text_with_line_numbers> section.
    - Do not repeat different links for the same location. For each line that you're recommending a link for, only return one link.
    - Only include official looking links.
    - The link should be relevant to the search term, which should in term be relevant to the text.
    - You must only point to lines of text, not code lines or empty lines.
    - NEVER MODIFY CODE LINES.  
    
    Before you return your response, think about the best way to link to the search results. Be sure to use the search term to find a relevant link.
    Only include official looking links.

    Return your response in JSON format with the following structure:
    {{
        "reasoning": "The reasoning for the list of link locations",
        "link_locations": [
            {{
                "line_number": "The line number to link to",
                "url": "The url to link to",
            }}
        ]
    }}
    """
    try:
        response = patched_client.chat.completions.create(
            model="claude-3-haiku-20240307",
            max_tokens=1000,
            temperature=0.25,
            messages=[{"role": "user", "content": prompt}],
            response_model=LinkLocations,
        )
        link_locations = response.link_locations
        logger.success(f"Found {len(link_locations)} link locations")
        return link_locations
    except Exception as e:
        logger.exception("Error finding link locations", error=e)
        return []


def recommend_internal_links(text: str, index_name: str) -> List[LineIssue]:
    search_terms = get_search_terms(text)
    all_search_results = []
    for search_term in search_terms:
        search_results = internal_search(search_term, index_name)
        all_search_results.extend(search_results)

    logger.info(f"Found {len(all_search_results)} search results")

    if not all_search_results:
        return []

    link_locations = find_link_locations(text, all_search_results)

    final_line_issues = []
    for link_location in link_locations:
        final_line_issues.append(
            LineIssue(
                line=link_location.line_number,
                issue_message=[
                    f"{link_location.instructions}. Rewrite this line to include, in a natural way, an inline link to {link_location.url}. Make the link in markdown format."
                ],
            )
        )
    return final_line_issues


class InternalLinkEditor(BaseEditor):
    indexes: List[str]

    def prerun_checks(self) -> bool:
        for index_name in self.indexes:
            index = TantivyIndexer(index_name, create_if_missing=False)
            if not index.exists():
                logger.error(f"Index {index_name} does not exist")
                return False

        return True

    def collect_issues(self) -> None:
        """Recommends internal links based on search terms and adds them as replacement issues."""
        text_with_line_numbers = self.get_text_with_line_numbers()
        line_lookup = self.get_line_number_lookup()
        replacements_count = 0

        for index_name in self.indexes:
            logger.info(f"Processing index: {index_name}")
            recd_links = recommend_internal_links(text_with_line_numbers, index_name)

            if not recd_links:
                logger.info(f"No internal links found for index {index_name}")
                continue

            logger.success(
                f"Found {len(recd_links)} potential internal link locations for index {index_name}"
            )

            for link_issue in recd_links:
                # Ensure the line exists in the current text
                if link_issue.line in line_lookup:
                    replacement_issue = ReplaceLineFixableIssue(
                        line=link_issue.line,
                        issue_message=link_issue.issue_message,
                        existing_content=line_lookup[link_issue.line],
                    )
                    self.add_replacement(replacement_issue)
                    replacements_count += 1
                else:
                    logger.warning(
                        f"Skipping recommended link for line {link_issue.line} as it does not exist in the lookup."
                    )

        logger.success(
            f"Collected {replacements_count} line replacement issues for internal links."
        )
