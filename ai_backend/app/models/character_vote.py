# models/character_vote.py
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Integer, UniqueConstraint

class CharacterVote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    character_id: int = Field(foreign_key="character.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    value: int  # NOT NULL благодаря тому, что тип не Optional

    __table_args__ = (
        UniqueConstraint("character_id", "user_id", name="uq_character_vote_character_user"),
    )