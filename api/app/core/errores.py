from typing import Any

from pydantic import BaseModel, Field


class ErrorItem(BaseModel):
    campo: str | None = None
    mensaje: str


class ProblemDetail(BaseModel):
    type: str = Field(default="about:blank")
    title: str
    status: int
    code: str
    detail: str
    trace_id: str | None = None
    errors: list[ErrorItem] = Field(default_factory=list)


class GalaxyERPException(Exception):
    def __init__(
        self,
        code: str,
        title: str,
        status: int = 400,
        detail: str = "",
        type_uri: str | None = None,
        errors: list[dict[str, Any]] | None = None,
    ):
        super().__init__(detail or title)
        self.code = code
        self.title = title
        self.status = status
        self.detail = detail or title
        self.type_uri = (
            type_uri or f"https://galaxy-erp.local/errores/{code.lower().replace('_', '-')}"
        )
        self.errors = errors or []

    def to_problem_detail(self, trace_id: str | None = None) -> ProblemDetail:
        return ProblemDetail(
            type=self.type_uri,
            title=self.title,
            status=self.status,
            code=self.code,
            detail=self.detail,
            trace_id=trace_id,
            errors=[ErrorItem(**e) for e in self.errors],
        )
