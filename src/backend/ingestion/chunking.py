"""
https://github.com/docling-project/docling/blob/main/docs/examples/hybrid_chunking.ipynb
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from logging import Logger
from pathlib import Path
from typing import Any

import pymupdf
import tiktoken
from docling.chunking import DocChunk, HybridChunker
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer
from docling_core.types.doc.document import DoclingDocument
from ftfy import fix_text
from tqdm import tqdm

from config import settings
from ingestion.extract import extract

logger: Logger = logging.getLogger(__name__)

DOCLING_PLACEHOLDERS: tuple[str, ...] = (
    "<!-- formula-not-decoded -->",
    "<!-- image -->",
)


def get_toc(path: Path) -> list[tuple[int, str, int]]:
    """Obtaining table of contents if available."""
    try:
        with pymupdf.open(path) as doc:
            # (level, title, page), title is normalized
            toc: list[tuple[int, str, int]] = [
                (level, " ".join(title.split()), page)
                for level, title, page in doc.get_toc()
                if page > 0  # -1: pymupdf could not resolve the bookmark's page
            ]
            return toc
    except pymupdf.FileDataError:
        logger.warning("no readable outline in %s", path)
        return []


def section_paths(
    toc: list[tuple[int, str, int]],
    num_pages: int,
) -> dict[int, list[str]]:
    """
    Map every page to the section titles it sits inside, outermost first.

    Parameters
    ----------
    toc : list[tuple[int, str, int]]
        Table of contents entries as (level, title, start_page), in document order.
    num_pages : int
        Number of pages in the document.

    Returns
    -------
    dict[int, list[str]]
        Page number to its section titles. Empty dict if `toc` is empty. Pages
        before the first entry map to an empty list.
    """
    if not toc:
        return {}
    nr_section_map: dict[int, list[str]] = {}
    for page in range(1, num_pages + 1):
        open_sections: dict[int, str] = {}
        for level, title, start_page in toc:
            # Stop at the first section that starts after this page
            if start_page > page:
                break
            # A new section at this level ends the previous one and its subsections
            open_sections = {lvl: t for lvl, t in open_sections.items() if lvl < level}
            open_sections[level] = title
        nr_section_map[page] = list(open_sections.values())
    return nr_section_map


@dataclass
class Chunk:
    text: str
    index: int
    token_count: int
    pages: list[int]
    metadata: dict[str, Any]


def normalize(text: str) -> str:
    """Removes placeholders from text and normalizes whitespace."""
    for placeholder in DOCLING_PLACEHOLDERS:
        text = text.replace(placeholder, "")

    text = fix_text(text)  # control chars, odd quotes etc. removed
    # Remove unknown character
    text = text.replace("\ufffd", "")
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text):
        cleaned = re.sub(r"[ \t]+", " ", paragraph).strip()
        if cleaned:
            paragraphs.append(cleaned)

    normalized_text = "\n\n".join(paragraphs)
    return normalized_text


def chunk_pages(chunk: DocChunk) -> list[int]:
    """Obtains page numbers from a chunk's metadata."""
    page_numbers = sorted(
        set(
            prov.page_no
            for item in chunk.meta.doc_items
            for prov in item.prov
            if hasattr(prov, "page_no")
        )
    )
    return page_numbers


def chunk_document_hybrid(
    doc: DoclingDocument,
    max_tokens: int = 512,  # TODO: experiment with this value
    merge_peers: bool = True,  # TODO: experiment with this value
    toc: list[tuple[int, str, int]] = [],
    embedding_model: str = settings.EMBEDDING_MODEL,
) -> list[Chunk]:
    """
    Split a parsed document into embeddable chunks.

    Parameters
    ----------
    doc : DoclingDocument
        The parsed document, as returned by `extract()`.
    max_tokens : int, default 512
        Upper bound per chunk, counted with the embedding model's tokenizer.
    merge_peers : bool, default True
        Let the chunker merge neighbouring chunks that share their metadata.
    toc : list[tuple[int, str, int]], default []
        Outline entries from `get_toc`. Empty for files without an outline,
        the heading path then falls back to docling's own headings.
    embedding_model : str, default `settings.EMBEDDING_MODEL`
        Picks the tokenizer, so that `token_count` matches what the embedder
        will see.

    Returns
    -------
    list[Chunk]
        The chunks in document order, `index` counted from 0. Chunks on the
        document's own contents pages and empty chunks are left out, so the
        count is lower than what the chunker produced.
    """
    tokenizer = OpenAITokenizer(
        tokenizer=tiktoken.encoding_for_model(embedding_model),
        max_tokens=max_tokens,
    )
    chunker = HybridChunker(
        tokenizer=tokenizer,
        merge_peers=merge_peers,
    )
    sections = section_paths(toc, len(doc.pages))

    chunk_index: int = 0
    chunks: list[Chunk] = []

    for chunk in tqdm(list(chunker.chunk(dl_doc=doc)), desc="chunking", unit="chunk"):
        labels = sorted({str(item.label) for item in chunk.meta.doc_items})
        if (
            "document_index" in labels
        ):  # skip the book's own toc pages (mostly very cluttered)
            continue
        pages = chunk_pages(chunk)

        section_path = sections.get(pages[0], []) if pages else []
        # With toc: keep the last 2 levels only, the upper ones are shared by many
        #           pages and just dilute the embedding
        # Without toc: fall back to the nearest docling heading, the slide title
        headings = [fix_text(h) for h in chunk.meta.headings or []]
        prefix: list[str] = section_path[-2:] or headings[-1:]
        # joining prefix list and chunk text with a newline
        text: str = normalize("\n".join([*prefix, chunk.text]))
        if not text:
            continue

        chunk_object = Chunk(
            text=text,
            index=chunk_index,
            token_count=tokenizer.count_tokens(text),
            pages=pages,
            metadata={
                "labels": labels,
                "headings": headings,
                "self_refs": [item.self_ref for item in chunk.meta.doc_items],
                "has_formula": "formula" in labels,
                "chunker": {
                    "name": "hybrid",
                    "max_tokens": max_tokens,
                    "merge_peers": merge_peers,
                },
                "section_path": section_path,
            },
        )

        chunks.append(chunk_object)
        chunk_index += 1

    return chunks


def save_chunks(chunks: list[Chunk], path: Path) -> None:
    """Saves chunks to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(chunk) for chunk in chunks], f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # only here: at module level this would reconfigure the app's root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    )
    logging.getLogger("docling").setLevel("WARNING")

    pdf = Path("./documents/lec_03_structure_from_motion.pdf")
    doc: DoclingDocument = extract(pdf)
    toc: list[tuple[int, str, int]] = get_toc(pdf)

    # the Markdown export, for eyeballing what the chunker was given
    with open(f"{pdf.stem}.docling.md", "w", encoding="utf-8") as f:
        f.write(doc.export_to_markdown())

    chunks = chunk_document_hybrid(doc, toc=toc)
    save_chunks(chunks, Path(f"{pdf.stem}.chunks.json"))
    print(f"Saved chunks to {Path(f'{pdf.stem}.chunks.json')}")
