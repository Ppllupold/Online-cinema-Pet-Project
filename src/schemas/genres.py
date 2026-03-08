from pydantic import BaseModel, ConfigDict, Field


class GenreBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class GenreCreate(GenreBase):
    pass


class GenreUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class GenreListResponse(GenreBase):
    id: int
    movie_count: int
    movies_url: str

    model_config = ConfigDict(from_attributes=True)


class GenreDetailResponse(GenreBase):
    id: int
    movie_count: int

    model_config = ConfigDict(from_attributes=True)
