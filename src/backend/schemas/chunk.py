from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.chunk import MetaDataDict
from models.enums import Lang


class ChunkRead(BaseModel):
    """One chunk, without its embedding.

    `embedding` and `tsv` are left out on purpose. The embedding would add
    1024 floats per chunk to every response, and the tsvector is a Postgres
    internal.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID = Field(description="Unique identifier for the chunk")
    chunk_index: int = Field(description="Position in the document, from zero")
    content: str = Field(description="The embedded text, heading path included")
    token_count: int | None = Field(
        None, description="Tokens in the content, as the chunker counted them"
    )
    language: Lang | None = Field(None, description="Language of the chunk")
    embedding_model: str | None = Field(
        None, description="Model that produced the vector, NULL while unembedded"
    )
    meta_data: MetaDataDict = Field(
        description="Pages, heading path, labels, has_math, chunker config"
    )
    created_at: datetime = Field(description="When the chunk was stored")
