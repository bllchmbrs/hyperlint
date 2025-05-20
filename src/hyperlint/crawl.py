import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from loguru import logger

from .config import SimpleConfig
from .sources.storage import Page, SearchIndex


async def external_crawl(
    url: str, config: SimpleConfig, max_depth: int = 50, include_external: bool = False
):
    # Configure a 2-level deep crawl

    strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth, include_external=include_external
    )
    crawl_config = CrawlerRunConfig(
        deep_crawl_strategy=strategy,
        verbose=False,
        markdown_generator=DefaultMarkdownGenerator(),
        scraping_strategy=LXMLWebScrapingStrategy(),
    )

    domain = urlparse(url).netloc

    target_dir = config.get_storage_data_dir() / "crawl"
    target_dir.mkdir(exist_ok=True, parents=True)
    crawl_index_file = target_dir / f"{domain}_crawl_index.json"
    metadata: Dict[str, Any] = {"url": url, "timestamp": datetime.now().isoformat()}
    pages: List[Page] = []

    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(url, config=crawl_config)

        logger.success(f"Crawled {len(results)} pages in total")

        for result in results:
            target_file_with_potential_dot_html_ending = (
                target_dir / result.url.split("/")[-1]
            )
            target_md_file = target_file_with_potential_dot_html_ending.with_suffix(
                ".md"
            )
            pages.append(
                Page(
                    url=result.url,
                    file=target_md_file.name,
                    html=result.html,
                    markdown=result.markdown,
                )
            )

        metadata["pages"] = [page.model_dump() for page in pages]
        with open(crawl_index_file, "w") as f:
            json.dump(metadata, f)

    return pages


def external_crawl_sync(
    url: str, config: SimpleConfig, max_depth: int = 50, include_external: bool = False
):
    return asyncio.run(external_crawl(url, config, max_depth, include_external))


def crawl_and_index(url: str, config: SimpleConfig):
    pages = external_crawl_sync(url, config)
    if asyncio.iscoroutine(pages):
        pages = asyncio.run(pages)

    indexer = SearchIndex(config, "crawl")
    indexer.add_pages(pages)
