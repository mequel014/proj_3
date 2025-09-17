# app/schemas/character.py
from pydantic import BaseModel, field_validator, ConfigDict
from typing import List, Optional

class CharacterCreate(BaseModel):
    name: str
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    context: str
    interests: List[str] = []
    # rating: Optional[float] = None
    is_public: bool = True

class CharacterUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    context: Optional[str] = None
    interests: Optional[List[str]] = None
    # rating: Optional[float] = None
    is_public: Optional[bool] = None

# class CharacterOut(BaseModel):
#     id: int
#     owner_id: int
#     name: str
#     gender: Optional[str] = None
#     photo_url: Optional[str] = None
#     bio: Optional[str] = None
#     context: str
#     interests: List[str]
#     rating: Optional[float]
#     is_public: bool
#     is_blocked: bool

#     class Config:
#         from_attributes = True
class CharacterOut(BaseModel):
    id: int
    owner_id: int
    name: str
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    context: str
    interests: List[str]
    # rating: Optional[float]
    is_public: bool
    is_blocked: bool
    likes_count: int
    dislikes_count: int
    my_vote: Optional[int] = None  # -1, 0/None, 1

    model_config = ConfigDict(from_attributes=True)
    # class Config:
    #     from_attributes = True

class VoteIn(BaseModel):
    value: int  # -1, 0, 1

    @field_validator("value")
    @classmethod
    def valid_value(cls, v: int) -> int:
        if v not in (-1, 0, 1):
            raise ValueError("value must be -1, 0, or 1")
        return v