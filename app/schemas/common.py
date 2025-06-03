from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total number of items")
    pages: int = Field(..., description="Total number of pages")

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    data: List[T] = Field(..., description="List of items")
    meta: PaginationMeta = Field(..., description="Pagination metadata") 