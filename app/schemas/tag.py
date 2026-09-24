from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    name: str
    color: str


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None


class TagRead(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
