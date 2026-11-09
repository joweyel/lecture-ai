import argparse
import asyncio
import logging
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from docling_core.types.doc.document import DoclingDocument
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from tqdm import tqdm

from config import settings
from db.session import SessionLocal
from ingestion.chunking import Chunk, chunk_document_hybrid, get_toc
from ingestion.extract import extract
from ingestion.language import detect_language
from models.chunk import Chunks
from models.document import Documents
from models.enums import IngestionStatus, Lang

logger = logging.getLogger(__name__)


async def set_status(
    session: AsyncSession,
    document: Documents,
    status: IngestionStatus,
) -> None:
    """Set the status of a document.

    Parameters
    ----------
    session : AsyncSession
        The database session.
    document : Documents
        The document to update.
    status : IngestionStatus
        The new status.

    Returns
    -------
    None
    """
    logger.info(f"Setting status of document {document.id} to {status}")
    document.status = status
    await session.commit()


@lru_cache(maxsize=1)
def get_embedder() -> Embeddings:
    """Build the configured embedder, cached so the local model loads only once.

    Returns
    -------
    Embeddings
        `HuggingFaceEmbeddings` when `EMBEDDING_PROVIDER` is local or hf,
        otherwise `OpenAIEmbeddings`.
    """
    logger.info(
        f"get_embedder: building {settings.EMBEDDING_PROVIDER} embedder "
        f"{settings.EMBEDDING_MODEL}"
    )
    if settings.EMBEDDING_PROVIDER in ("local", "hf"):
        return HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cuda"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSIONS,
        api_key=settings.OPENAI_API_KEY,
    )


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured embedding model.

    Parameters
    ----------
    texts : list[str]
        The texts to embed.

    Returns
    -------
    list[list[float]]
        The embeddings.
    """
    embedder: Embeddings = get_embedder()
    embedding_vectors: list[list[float]] = []
    batch_starts = range(0, len(texts), settings.EMBEDDING_BATCH_SIZE)
    logger.info(
        f"embed: {len(texts)} texts in {len(batch_starts)} batches "
        f"of {settings.EMBEDDING_BATCH_SIZE}"
    )
    for batch_start in tqdm(batch_starts, desc="Embedding texts", unit="batch"):
        batch = texts[batch_start : batch_start + settings.EMBEDDING_BATCH_SIZE]
        embedding_vectors.extend(await embedder.aembed_documents(batch))
    return embedding_vectors


async def ingest(document_id: UUID) -> None:
    """Extract, chunk, embed and store one document.

    Walks `IngestionStatus` from `extracting` over `chunking` and `embedding`
    to `done`, or to `failed` with the reason in `documents.error`. Opens its
    own session, since the request that scheduled this task is long gone by
    the time it runs.

    Parameters
    ----------
    document_id : UUID
        Primary key of a `documents` row whose file already lies in
        `settings.DOCUMENTS_DIR`.

    Returns
    -------
    None
        Everything goes into the database: the `chunks` rows, and `status`,
        `language`, `ingested_at` and `error` on the document.

    Notes
    -----
    Safe to run more than once. The document's existing chunks are deleted
    in the same transaction that inserts the new ones, so a re-ingest with a
    different chunker config does not collide with the old chunk numbers.

    No exception escapes: a background task has nobody left to report to, so
    a failure is recorded on the row instead.
    """
    logger.info(f"ingest: starting document {document_id}")
    # Open session to the db
    async with SessionLocal() as session:
        # Get document
        document = await session.get(Documents, document_id)
        if document is None:
            logger.error(f"ingest: Document {document_id} not found")
            return
        logger.info(
            f"ingest: {document_id} '{document.title}' "
            f"file={document.file_path} status={document.status}"
        )

        try:
            # Set status to extracting
            await set_status(session, document, IngestionStatus.EXTRACTING)

            # Getting the file path in volume (required for chunking / embedding)
            document_path: Path = settings.DOCUMENTS_DIR / document.file_path

            # Extract docling (dl) document to be used for chunking.
            # to_thread: extraction is blocking and takes ~30 s on cpu, which
            # would otherwise freeze the event loop and with it the whole api
            dl_doc: DoclingDocument = await asyncio.to_thread(extract, document_path)
            logger.info(
                f"ingest: extracted {len(dl_doc.pages)} pages from {document_path.name}"
            )

            # Save parsed document (for debugging / future use)
            dl_doc_path = document_path.parent / f"{document_id}.docling.json"
            dl_doc.save_as_json(dl_doc_path)
            logger.debug(f"ingest: parsed document saved to {dl_doc_path}")

            # Set status to chunking
            await set_status(session, document, IngestionStatus.CHUNKING)

            # Extracting toc if file is pdf
            toc: list[tuple[int, str, int]] = (
                get_toc(document_path) if document_path.suffix.lower() == ".pdf" else []
            )
            logger.info(f"ingest: {len(toc)} toc entries")

            # Extract chunks from document (blocking, so off the event loop)
            chunks: list[Chunk] = await asyncio.to_thread(
                chunk_document_hybrid, dl_doc, toc=toc
            )
            if not chunks:
                logger.error(f"ingest: No chunks found for document {document_id}")
                raise ValueError("No text extracted. Document may be scan or faulty.")
            logger.info(
                f"ingest: {len(chunks)} chunks, "
                f"{sum(chunk.token_count for chunk in chunks)} tokens"
            )

            # Determining document language from text sample (experimental 20 chunks)
            num_chunks: int = 20
            middle: int = len(chunks) // 2
            sample: list[Chunk] = chunks[
                max(0, middle - num_chunks // 2) : middle + num_chunks // 2
            ]
            language: Lang | None = detect_language(
                "\n".join([chunk.text for chunk in sample])
            )
            document.language = language
            logger.info(f"ingest: Document {document_id} language: {language}")

            await set_status(session, document, IngestionStatus.EMBEDDING)

            # Embed chunks
            embedding_vectors: list[list[float]] = await embed(
                [chunk.text for chunk in chunks]
            )
            logger.info(
                f"ingest: Document {document_id}, "
                f"embedded {len(embedding_vectors)} vectors"
            )

            # Dropping the document's old chunks, so running ingest again cannot collide
            # with chunk numbers that already exist
            await session.execute(
                delete(Chunks).where(Chunks.document_id == document_id)
            )

            # Saving chunks (incl. embedding) to db
            session.add_all(
                [
                    Chunks(
                        document_id=document_id,
                        chunk_index=chunk.index,
                        content=chunk.text,
                        embedding=embedding_vector,
                        meta_data={**chunk.metadata, "pages": chunk.pages},
                        embedding_model=settings.EMBEDDING_MODEL,
                        token_count=chunk.token_count,
                        language=language,
                    )
                    for chunk, embedding_vector in zip(
                        chunks, embedding_vectors, strict=True
                    )
                ]
            )
            logger.info(
                f"ingest: staged {len(chunks)} chunks for document {document_id}"
            )

            # Timestamp after ingestion
            document.ingested_at = func.now()

            # Set final status (commit happens here too; no dedicated commit needed)
            await set_status(session, document, IngestionStatus.DONE)
            logger.info(f"ingest: finished document {document_id}")

        except Exception as exc:
            # exception() logs the traceback
            logger.exception(f"ingest: Error ingesting document {document_id}")

            # Rollback of ingestion
            await session.rollback()

            # Set status to failed for current `document_id`, with the reason,
            # so that GET /documents/{id}/status can report it
            stmt = (
                update(Documents)
                .where(Documents.id == document_id)
                .values(status=IngestionStatus.FAILED, error=str(exc)[:2000])
            )
            await session.execute(stmt)
            # the success path already committed in set_status, so this commit
            # exists for the failure path only
            await session.commit()
            logger.warning(f"ingest: document {document_id} marked as failed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="ingest", description="Ingest a document into the database"
    )
    parser.add_argument("-d", "--document-id", type=UUID, required=True)
    args = parser.parse_args()

    # only here: at module level this would reconfigure the app's root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
    )
    asyncio.run(ingest(args.document_id))
