import os
from typing import List, Set

import tantivy
from loguru import logger
from pydantic import BaseModel

from hyperlint.config import SimpleConfig


class Page(BaseModel):
    url: str
    file: str
    html: str
    markdown: str

    def __hash__(self) -> int:
        return hash(self.url)


class PageResult(Page):
    score: float


class SearchIndex:
    def __init__(
        self, config: SimpleConfig, index_name: str, create_if_missing: bool = True
    ):
        self.config = config
        self.DB_PATH = os.path.join(
            self.config.get_storage_data_dir(), "index", index_name
        )
        schema_builder = tantivy.SchemaBuilder()
        self.name = index_name
        schema_builder.add_text_field("url", stored=True)
        schema_builder.add_text_field("file", stored=True)
        schema_builder.add_text_field("html", stored=True)
        schema_builder.add_text_field("markdown", stored=True)
        self.schema = schema_builder.build()

        try:
            self.index = tantivy.Index.open(self.DB_PATH)
        except Exception as e:
            if create_if_missing:
                os.makedirs(self.DB_PATH, exist_ok=True)
                self.index = tantivy.Index(self.schema, path=self.DB_PATH)
            else:
                raise Exception(
                    f"Index {self.name} does not exist at {self.DB_PATH}"
                ) from e

    def add_page(self, page: Page):
        writer = self.index.writer()
        new_doc = tantivy.Document()

        new_doc.add_text("url", page.url)
        new_doc.add_text("file", page.file)
        new_doc.add_text("html", page.html)
        new_doc.add_text("markdown", page.markdown)
        writer.add_document(new_doc)
        writer.commit()
        writer.wait_merging_threads()
        self.index.reload()

    def add_pages(self, pages: List[Page]):
        logger.info(f"Adding {len(pages)} pages to {self.name}")
        writer = self.index.writer()
        for page in pages:
            new_doc = tantivy.Document()

            new_doc.add_text("url", page.url)
            new_doc.add_text("file", page.file)
            new_doc.add_text("html", page.html)
            new_doc.add_text("markdown", page.markdown)
            writer.add_document(new_doc)
        writer.commit()
        writer.wait_merging_threads()
        logger.success(f"Added {len(pages)} pages to {self.name}")
        self.index.reload()

    def query(
        self,
        query_string: str,
        fields: List[str] = ["markdown", "html"],
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[PageResult]:
        logger.info(f"Searching for {query_string} in {self.name}")
        searcher = self.index.searcher()
        query = self.index.parse_query(query_string, fields)
        results = searcher.search(query, limit).hits
        output: List[PageResult] = []
        output_urls: Set[str] = set()
        logger.success(f"Found {len(results)} raw results")
        for result in results:
            doc_score = result[0]
            doc_address = result[1]
            doc = searcher.doc(doc_address)
            if doc_score > score_threshold:
                url = doc.get_first("url") or ""
                if url not in output_urls:
                    output.append(
                        PageResult(
                            url=url,
                            file=doc.get_first("file") or "",
                            html=doc.get_first("html") or "",
                            markdown=doc.get_first("markdown") or "",
                            score=doc_score,
                        )
                    )
                    output_urls.add(url)

        logger.info(f"Found {len(output)} deduplicated results")
        return sorted(output, key=lambda x: x.score, reverse=True)
