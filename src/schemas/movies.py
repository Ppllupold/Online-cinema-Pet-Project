from decimal import Decimal

from pydantic import BaseModel


class MoviesBase(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    price: Decimal


class MoviesList(MoviesBase):
    id: int
