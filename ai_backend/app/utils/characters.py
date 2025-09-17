# utils/characters.py

from typing import Optional
from sqlmodel import Session, select
from models.character import Character
from models.character_vote import CharacterVote
from schemas.character import CharacterOut

def build_character_out(
    session: Session,
    ch: Character,
    user_id: Optional[int] = None,
) -> CharacterOut:
    my_vote: Optional[int] = None
    if user_id:
        vote = session.exec(
            select(CharacterVote).where(
                CharacterVote.character_id == ch.id,
                CharacterVote.user_id == user_id,
            )
        ).one_or_none()
        my_vote = vote.value if vote else None

    out = CharacterOut.model_validate(ch, from_attributes=True)
    # В pydantic v2 можно так:
    out = out.model_copy(update={"my_vote": my_vote})
    # или просто: out.my_vote = my_vote
    return out