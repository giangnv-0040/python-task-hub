from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(min_length=1, max_length=20)


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, min_length=1, max_length=20)


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
