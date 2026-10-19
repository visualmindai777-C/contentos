from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


def ok(data: Any) -> dict[str, Any]:
    return {"success": True, "data": data}
