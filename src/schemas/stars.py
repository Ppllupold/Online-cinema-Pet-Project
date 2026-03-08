from pydantic import BaseModel, ConfigDict, Field


class StarBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    model_config = ConfigDict(from_attributes=True)


class StarCreate(StarBase):
    pass


class StarUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class StarListResponse(StarBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class StarDetailResponse(StarBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
