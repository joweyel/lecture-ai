"""
https://github.com/docling-project/docling/blob/main/docs/examples/custom_convert.py
"""

import logging
import time
from functools import lru_cache
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    HeadingHierarchyOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import DoclingDocument

ALLOWED_FILE_SUFFIXES: tuple[str, ...] = (".pdf", ".md", ".txt")

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_converter(**options) -> DocumentConverter:
    """
    Build a docling converter, cached so the layout model loads only once.

    Parameters
    ----------
    **options : Any
        Pipeline overrides. The defaults below are the project's, and all
        three differ from docling's own.

        do_ocr : bool, default False
            Run OCR over the page images. Lecture material is born digital,
            and OCR is relatively slow without a GPU.
        do_table_structure : bool, default False
            Detect table cells. Off, because tables are not cited.
        heading_hierarchy_options : HeadingHierarchyOptions, default enabled
            Assign a level to every section header. The chunker turns those
            into the heading path.

    Returns
    -------
    DocumentConverter
        A converter configured for PDF input.

    Notes
    -----
    The cache holds a single converter, so a call with different options
    replaces it. Every value has to be hashable, since `lru_cache` keys on
    the arguments, which rules out passing a pydantic options object.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = options.get("do_ocr", False)
    heading_options = HeadingHierarchyOptions(enabled=True)
    pipeline_options.heading_hierarchy_options = options.get(
        "heading_hierarchy_options", heading_options
    )
    pipeline_options.do_table_structure = options.get("do_table_structure", False)
    # Configure format options for PDF conversion
    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options,
            )
        }
    )
    return doc_converter


def extract(path: Path, **options) -> DoclingDocument:
    """
    Parse a file on disk into a typed docling document.

    Parameters
    ----------
    path : Path
        The file to parse. Its suffix must be in `ALLOWED_FILE_SUFFIXES`.
    **options : Any
        Docling pipeline options, passed through to `get_converter`.

    Returns
    -------
    DoclingDocument
        The parsed document: text items carrying page number and bounding
        box, arranged in the document tree.

    Raises
    ------
    ValueError
        If the suffix is not supported, or if docling could only parse the
        document partially.
    """
    if path.suffix.lower() not in ALLOWED_FILE_SUFFIXES:
        raise ValueError(f"File type {path.suffix} is not supported")
    converter = get_converter(**options)

    start_time = time.perf_counter()
    conv_result: ConversionResult = converter.convert(path)

    # a partial parse would leave silent gaps in a system built on page citations
    if conv_result.status is ConversionStatus.PARTIAL_SUCCESS:
        raise ValueError(f"{path.name} only partially converted: {conv_result.errors}")

    logger.info(
        f"extract: {path.name} converted in {time.perf_counter() - start_time:.2f} s"
    )

    return conv_result.document


if __name__ == "__main__":
    # Only configured if extract.py is ran directly. Otherwise, the app's logger used.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    )
    doc_path = Path("./documents/lec_03_structure_from_motion.pdf")
    print(extract(path=doc_path).export_to_markdown())
