# app/routers/characters.py
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select

from utils.db import get_session
from utils.dependencies import get_current_user, require_admin
from utils.characters import build_character_out
from models.user import User
from models.character import Character
from schemas.character import CharacterCreate, CharacterUpdate, CharacterOut, VoteIn
from models.character_vote import CharacterVote

router = APIRouter()

@router.get("", response_model=List[CharacterOut])
def list_characters(
    session: Session = Depends(get_session),
    mine: bool = False,
    owner_id: Optional[int] = None,
    current_user: Optional[User] = Depends(get_current_user),
):
    q = select(Character).where(Character.is_blocked == False)
    if mine and current_user:
        q = q.where(Character.owner_id == current_user.id)
    elif owner_id:
        q = q.where(Character.owner_id == owner_id)
    else:
        q = q.where(Character.is_public == True)

    items = session.exec(q.order_by(Character.created_at.desc())).all()
    if not items:
        return []

    # Собираем голоса текущего пользователя одним запросом
    vmap = {}
    if current_user:
        ids = [c.id for c in items]
        votes = session.exec(
            select(CharacterVote).where(
                CharacterVote.user_id == current_user.id,
                CharacterVote.character_id.in_(ids),
            )
        ).all()
        vmap = {v.character_id: v.value for v in votes}

    # Преобразуем Character -> CharacterOut и проставим my_vote из карты
    out: List[CharacterOut] = [
        CharacterOut.model_validate(ch, from_attributes=True).model_copy(
            update={"my_vote": vmap.get(ch.id)}
        )
        for ch in items
    ]
    return out

@router.post("", response_model=CharacterOut)
def create_character(
    data: CharacterCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    ch = Character(
        owner_id=current_user.id,
        name=data.name,
        gender=data.gender,
        photo_url=data.photo_url,
        bio=data.bio,
        context=data.context,
        interests=data.interests or [],
        is_public=data.is_public,
    )
    session.add(ch)
    session.commit()
    session.refresh(ch)
    return ch

@router.get("/{character_id}", response_model=CharacterOut)
def get_character(character_id: int, 
                  session: Session = Depends(get_session), 
                  current_user: Optional[User] = Depends(get_current_user)):
    ch = session.get(Character, character_id)
    if not ch or ch.is_blocked:
        raise HTTPException(status_code=404, detail="Character not found")
    if not ch.is_public:
        if not current_user or (current_user.id != ch.owner_id and not current_user.is_admin):
            raise HTTPException(status_code=403, detail="Private character")
    # return ch
    if current_user:
        v = session.exec(
            select(CharacterVote).where(
                CharacterVote.user_id == current_user.id,
                CharacterVote.character_id == character_id,
            )
        ).first()
        # setattr(ch, "my_vote", v.value if v else None)
    return build_character_out(session, ch, current_user.id)

@router.patch("/{character_id}", response_model=CharacterOut)
def update_character(
    character_id: int,
    data: CharacterUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    ch = session.get(Character, character_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.id != ch.owner_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ch, field, value)
    session.add(ch)
    session.commit()
    session.refresh(ch)
    return build_character_out(session, ch, current_user.id)

@router.post("/{character_id}/block")
def block_character(character_id: int, session: Session = Depends(get_session), admin: User = Depends(require_admin)):
    ch = session.get(Character, character_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Not found")
    ch.is_blocked = not ch.is_blocked
    session.add(ch)
    session.commit()
    return {"detail": "toggled", "is_blocked": ch.is_blocked}

# Простой локальный аплоад картинки (опционально)
@router.post("/upload/photo")
def upload_photo(file: UploadFile = File(...)):
    os.makedirs("static/uploads", exist_ok=True)
    path = os.path.join("static", "uploads", file.filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return {"photo_url": f"/{path}"}

@router.post("/{character_id}/vote", response_model=CharacterOut)
def vote_character(
    character_id: int,
    data: VoteIn,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    ch = session.get(Character, character_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Not found")

    vote = session.exec(
        select(CharacterVote).where(
            CharacterVote.character_id == character_id,
            CharacterVote.user_id == current_user.id,
        )
    ).one_or_none()

    new_value = data.value  # -1, 0, 1
    old_value = vote.value if vote else 0

    # Обновляем лайки/дизлайки
    def dec(v):
        if v == 1: ch.likes_count -= 1
        elif v == -1: ch.dislikes_count -= 1
    def inc(v):
        if v == 1: ch.likes_count += 1
        elif v == -1: ch.dislikes_count += 1

    if new_value == 0:
        # Сброс голоса
        if vote:
            dec(vote.value)
            session.delete(vote)
    else:
        if not vote:
            vote = CharacterVote(character_id=character_id, user_id=current_user.id, value=new_value)
            inc(new_value)
            session.add(vote)
        else:
            if vote.value != new_value:
                dec(vote.value)
                vote.value = new_value
                inc(new_value)
            # Если vote.value == new_value, ничего не меняем (клиент мог нажать тот же)

    session.add(ch)
    session.commit()
    session.refresh(ch)

    return build_character_out(session, ch, current_user.id)