from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, ConfigDict, field_validator

from src.schemas.genres import GenreListResponse
from src.schemas.stars import StarListResponse


class PaginationSchema(BaseModel):
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    next_page: str | None = None
    previous_page: str | None = None
    total_pages: int
    total_items: int


class MovieFilterSchema(BaseModel):
    q: str | None = None

    year_gte: Annotated[int | None, Field(ge=1888)] = None
    imdb_gte: Annotated[float | None, Field(ge=0, le=10)] = None
    price_lte: Annotated[Decimal | None, Field(ge=0)] = None

    genres: list[str] | None = None
    stars: list[str] | None = None
    director: str | None = None

    @field_validator("director", "q", mode="before")
    @classmethod
    def normalize_director(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v.lower() or None

    @field_validator("genres", "stars", mode="before")
    @classmethod
    def normalize_str_list(cls, v):
        if v is None:
            return None

        if isinstance(v, str):
            v = [x for x in v.split(",")]

        if not isinstance(v, list):
            return v

        cleaned: list[str] = []
        seen: set[str] = set()
        for item in v:
            s = str(item).strip().lower()
            if not s:
                continue
            if s in seen:
                continue
            seen.add(s)
            cleaned.append(s)

        return cleaned or None


class CertificationForMoviesSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class DirectorForMoviesSchema(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class MoviesBase(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class MoviesListItem(MoviesBase):
    id: int


class MovieListResponse(BaseModel):
    items: list[MoviesListItem]
    pagination: PaginationSchema


class MovieDetailResponse(MoviesBase):
    id: int
    meta_score: float | None = None
    gross: float | None = None
    description: str
    certification: CertificationForMoviesSchema
    genres: list[GenreListResponse]
    stars: list[StarListResponse]
    directors: list[DirectorForMoviesSchema]


class MovieCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    year: int = Field(..., ge=1888)
    time: int = Field(..., gt=0)
    imdb: float = Field(..., ge=0, le=10)
    votes: int = Field(..., ge=0)
    price: Decimal = Field(..., ge=0)
    description: str = Field(..., min_length=1)
    meta_score: float | None = Field(None, ge=0, le=100)
    gross: float | None = Field(None, ge=0)

    certification_id: int
    genre_ids: list[int] = Field(..., min_length=1)
    star_ids: list[int] = Field(..., min_length=1)
    director_ids: list[int] = Field(..., min_length=1)


class MovieUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    year: int | None = Field(None, ge=1888)
    time: int | None = Field(None, gt=0)
    imdb: float | None = Field(None, ge=0, le=10)
    votes: int | None = Field(None, ge=0)
    price: Decimal | None = Field(None, ge=0)
    description: str | None = Field(None, min_length=1)
    meta_score: float | None = Field(None, ge=0, le=100)
    gross: float | None = Field(None, ge=0)

    certification_id: int | None = None
    genre_ids: list[int] | None = Field(None, min_length=1)
    star_ids: list[int] | None = Field(None, min_length=1)
    director_ids: list[int] | None = Field(None, min_length=1)
