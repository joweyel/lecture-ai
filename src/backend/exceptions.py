"""
Translation of database errors into HTTP responses.

Without a handler, a constraint violation reaches FastAPI unhandled and becomes
a 500, which tells the client the server is broken when the request is at fault.

Reference: https://github.com/rjprins/fastapi-restly/blob/main/fastapi_restly/_exception_handlers.py
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

# PostgreSQL SQLSTATE class 23, integrity constraint violation.
# https://www.postgresql.org/docs/current/errcodes-appendix.html
SQLSTATE_RESPONSES: dict[str, tuple[int, str]] = {
    "23505": (status.HTTP_409_CONFLICT, "This entry already exists."),
    "23503": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "A referenced entry does not exist.",
    ),
    "23502": (
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        "A required field was set to null.",
    ),
    "23514": (status.HTTP_422_UNPROCESSABLE_CONTENT, "A value is out of range."),
}

FALLBACK_RESPONSE: tuple[int, str] = (
    status.HTTP_400_BAD_REQUEST,
    "The request conflicts with the stored data.",
)


async def integrity_error_handler(
    request: Request,
    exc: IntegrityError,
) -> JSONResponse:
    """Turn a constraint violation into a meaningful status code.

    Parameters
    ----------
    request: Request
        The request that triggered the error. Unused, but required.
    exc: IntegrityError
        The error raised by SQLAlchemy on commit.

    Returns
    -------
    JSONResponse
        The response. The message is generic on purpose: the original error
        text contains the constraint name, the table and often the values.
    """
    sqlstate = getattr(exc.orig, "sqlstate", None)
    status_code, detail = SQLSTATE_RESPONSES.get(sqlstate, FALLBACK_RESPONSE)
    return JSONResponse(status_code=status_code, content={"detail": detail})
