from datetime import datetime
from decimal import Decimal

from src.schemas.movies import MoviesBase
from pydantic import BaseModel, ConfigDict, Field


class CartMovieItem(MoviesBase):
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    items: list[CartMovieItem] = Field(default_factory=list)
    total_price: Decimal = Decimal("0")
    total_items: int = 0
