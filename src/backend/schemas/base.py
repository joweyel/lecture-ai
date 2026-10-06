from pydantic import BaseModel, ConfigDict


class ReadBase(BaseModel):
    """Response schemas inherit this so they can be built from ORM objects."""

    model_config = ConfigDict(
        from_attributes=True,
    )
