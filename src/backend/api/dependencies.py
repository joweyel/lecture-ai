from typing import Annotated
from uuid import UUID

from fastapi import Depends
from config import settings

async def get_current_user_id() -> UUID:
    """ID of the current user. Replaced by token verification later."""
    if settings.DEV_USER_ID is None:
        raise RuntimeError("DEV_USER_ID is not set and no authentication is configured.")
    return settings.DEV_USER_ID

CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]