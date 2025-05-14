from typing import List

import instructor
from litellm import completion
from loguru import logger
from pydantic import BaseModel, Field

patched_client = instructor.from_litellm(completion=completion)


class SearchTerms(BaseModel):
    search_terms: List[str] = Field(
        description="A list of up to 12 search terms wrapped in <search_terms> tags and separated by commas."
    )


def get_search_terms(text: str) -> List[str]:
    logger.info("Getting search terms for text", text=text)
    prompt = f"""
    Extract up to 12 key search terms from the following text. Return a list of up to 12 search terms wrapped in <search_terms> tags and separated by commas.

    <text>
    {text}
    </text>

    Return a list of up to 5 search terms wrapped in <search_terms> tags and separated by commas.

    <example>
    This is a technical blog post or tutorial, so focus on the more technical tools, concepts, and terms that we should link to and search for.

    For instance, if the code includes
    ```python
    from mcp.server.fastmcp import FastMCP
    ````

    Then good search terms would be "FastMCP" and "MCP Server".
    </example>

    Rules:
    - Focus in particular on the names from the imported lobraries and their names.
    - Don't include concepts that aren't related to the technical content of the text. For instance, if the demo is about whales, don't include "whales" in the search terms.
    - Focus on the terms related to the libraries used. For instances, the imported classes, functions names, etc.
    - Do not use search terms that seem specific to the demo, but rather focus on the libraries used.

    First use a <thinking> block to think about the best search terms. Then return your response wrapped in <search_terms> tags.
    """
    response = patched_client.messages.create(
        model="anthropic/claude-3-haiku-20240307",
        max_tokens=800,
        temperature=0.25,
        messages=[{"role": "user", "content": prompt}],
        response_model=SearchTerms,
    )
    return response.search_terms
