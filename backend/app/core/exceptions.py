"""
LiRA Backend — Centralized Exception Handlers
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class LiRAException(Exception):
    """Base exception for LiRA backend."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(LiRAException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class ConflictError(LiRAException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, status_code=409)


class ForbiddenError(LiRAException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)


class WorkflowError(LiRAException):
    def __init__(self, message: str = "Workflow execution error"):
        super().__init__(message, status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(LiRAException)
    async def lira_exception_handler(request: Request, exc: LiRAException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )
