from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
import logging

logger = logging.getLogger(__name__)


class TaskNotFoundError(Exception):
    """Raised when a task is not found."""
    pass


class ConversationNotFoundError(Exception):
    """Raised when a conversation is not found."""
    pass


class TaskProcessingError(Exception):
    """Raised when task processing fails."""
    pass


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    """Handle TaskNotFoundError exceptions."""
    logger.warning(f"Task not found: {exc}")
    return JSONResponse(
        status_code=404,
        content={"detail": "Task not found"}
    )


async def conversation_not_found_handler(request: Request, exc: ConversationNotFoundError) -> JSONResponse:
    """Handle ConversationNotFoundError exceptions."""
    logger.warning(f"Conversation not found: {exc}")
    return JSONResponse(
        status_code=404,
        content={"detail": "Conversation not found"}
    )


async def task_processing_error_handler(request: Request, exc: TaskProcessingError) -> JSONResponse:
    """Handle TaskProcessingError exceptions."""
    logger.error(f"Task processing error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Task processing failed"}
    )


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle DatabaseError exceptions."""
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database operation failed"}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Custom HTTP exception handler with logging."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return await http_exception_handler(request, exc)