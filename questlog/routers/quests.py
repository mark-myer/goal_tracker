from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from questlog import models as schemas
from questlog.database import Metric, Quest, get_db
from questlog.routers.metrics import create_metric_internal
from questlog.services.progress import ensure_user, quest_progress

router = APIRouter()


def _serialize_quest(quest: Quest) -> schemas.QuestOut:
    return schemas.QuestOut(
        id=quest.id,
        title=quest.title,
        description=quest.description,
        category=quest.category,
        icon=quest.icon,
        deadline=quest.deadline,
        status=quest.status,
        xp_reward=quest.xp_reward,
        created_at=quest.created_at,
        completed_at=quest.completed_at,
        progress_pct=quest_progress(quest),
        metrics=[schemas.MetricOut.model_validate(metric) for metric in quest.metrics],
    )


@router.get("/quests", response_model=list[schemas.QuestOut])
def list_quests(db: Session = Depends(get_db)):
    quests = db.query(Quest).options(selectinload(Quest.metrics)).all()
    return [_serialize_quest(quest) for quest in quests]


@router.post("/quests", response_model=schemas.QuestOut)
def create_quest(payload: schemas.QuestCreate, db: Session = Depends(get_db)):
    quest = Quest(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        icon=payload.icon,
        deadline=payload.deadline,
        xp_reward=payload.xp_reward,
        status="active",
    )
    db.add(quest)
    db.flush()

    for metric_payload in payload.metrics:
        create_metric_internal(db, quest.id, metric_payload)

    db.commit()
    db.refresh(quest)
    quest = db.query(Quest).options(selectinload(Quest.metrics)).filter(Quest.id == quest.id).one()
    return _serialize_quest(quest)


@router.get("/quests/{quest_id}", response_model=schemas.QuestOut)
def get_quest(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(Quest).options(selectinload(Quest.metrics)).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    return _serialize_quest(quest)


@router.patch("/quests/{quest_id}", response_model=schemas.QuestOut)
def update_quest(quest_id: int, payload: schemas.QuestUpdate, db: Session = Depends(get_db)):
    quest = db.query(Quest).options(selectinload(Quest.metrics)).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(quest, field, value)

    db.commit()
    db.refresh(quest)
    return _serialize_quest(quest)


@router.delete("/quests/{quest_id}")
def delete_quest(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    db.delete(quest)
    db.commit()
    return {"deleted": True}


@router.get("/user/stats", response_model=schemas.UserStats)
def get_user_stats(db: Session = Depends(get_db)):
    user = ensure_user(db)
    db.commit()
    return schemas.UserStats(total_xp=user.total_xp, level=user.level, streak=0)
