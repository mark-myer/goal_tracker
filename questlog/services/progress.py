import datetime as dt

from sqlalchemy.orm import Session

from questlog.database import Metric, MetricHistory, Quest, User

LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2000]


def metric_progress(metric: Metric) -> float:
    if metric.target_value <= 0:
        return 0.0
    return max(0.0, min(100.0, (metric.current_value / metric.target_value) * 100))


def quest_progress(quest: Quest) -> float:
    if not quest.metrics:
        return 0.0
    return sum(metric_progress(metric) for metric in quest.metrics) / len(quest.metrics)


def derive_level(total_xp: int) -> int:
    level = 0
    for idx, threshold in enumerate(LEVEL_THRESHOLDS):
        if total_xp >= threshold:
            level = idx
    return level


def ensure_user(db: Session) -> User:
    user = db.query(User).first()
    if not user:
        user = User(username="adventurer", total_xp=0, level=0)
        db.add(user)
        db.flush()
    return user


def apply_metric_update(db: Session, metric: Metric, raw_value: float, transformed_value: float) -> tuple[float, bool]:
    metric.current_value = transformed_value
    metric.last_polled_at = dt.datetime.utcnow()
    db.add(MetricHistory(metric_id=metric.id, raw_value=raw_value, value=transformed_value))

    completed_now = False
    quest = metric.quest
    progress = quest_progress(quest)

    if progress >= 100 and quest.status != "completed":
        quest.status = "completed"
        quest.completed_at = dt.datetime.utcnow()
        user = ensure_user(db)
        user.total_xp += quest.xp_reward
        user.level = derive_level(user.total_xp)
        completed_now = True
    elif progress < 100 and quest.status == "completed":
        quest.status = "active"
        quest.completed_at = None

    return progress, completed_now
