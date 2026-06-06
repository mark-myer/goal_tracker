import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from questlog import models as schemas
from questlog.database import Metric, MetricSourceOdoo, MetricSourceURL, Quest, get_db
from questlog.routers.events import broadcast_event
from questlog.services.odoo_fetcher import fetch_odoo_metric
from questlog.services.progress import apply_metric_update, quest_progress
from questlog.services.transform import apply_transform
from questlog.services.url_fetcher import fetch_url_metric

router = APIRouter()


def create_metric_internal(db: Session, quest_id: int, payload: schemas.MetricCreate) -> Metric:
    metric = Metric(
        quest_id=quest_id,
        label=payload.label,
        current_value=payload.current_value,
        target_value=payload.target_value,
        unit=payload.unit,
        source_type=payload.source_type,
        poll_interval_sec=payload.poll_interval_sec,
        transform_expression=payload.transform_expression,
    )
    db.add(metric)
    db.flush()

    if payload.source_type == "url" and payload.source_url:
        db.add(
            MetricSourceURL(
                metric_id=metric.id,
                url=payload.source_url.url,
                json_path=payload.source_url.json_path,
                headers=payload.source_url.headers,
            )
        )
    if payload.source_type == "odoo" and payload.source_odoo:
        db.add(
            MetricSourceOdoo(
                metric_id=metric.id,
                connection_id=payload.source_odoo.connection_id,
                odoo_model=payload.source_odoo.odoo_model,
                odoo_domain=payload.source_odoo.odoo_domain,
                odoo_field=payload.source_odoo.odoo_field,
                odoo_aggregate=payload.source_odoo.odoo_aggregate,
            )
        )

    return metric


def _metric_query(db: Session, metric_id: int) -> Metric | None:
    return (
        db.query(Metric)
        .options(
            selectinload(Metric.quest).selectinload(Quest.metrics),
            selectinload(Metric.url_source),
            selectinload(Metric.odoo_source).selectinload(MetricSourceOdoo.connection),
        )
        .filter(Metric.id == metric_id)
        .first()
    )


def _apply_and_emit(db: Session, metric: Metric, raw_value: float) -> tuple[float, float]:
    transformed = apply_transform(raw_value, metric.transform_expression)
    progress, _completed = apply_metric_update(db, metric, raw_value, transformed)
    db.commit()

    broadcast_event(
        {
            "metric_id": metric.id,
            "raw_value": raw_value,
            "value": transformed,
            "quest_id": metric.quest_id,
            "quest_progress": progress,
        }
    )
    return raw_value, transformed


@router.post("/quests/{quest_id}/metrics", response_model=schemas.MetricOut)
def add_metric(quest_id: int, payload: schemas.MetricCreate, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    metric = create_metric_internal(db, quest_id, payload)
    db.commit()
    db.refresh(metric)
    return schemas.MetricOut.model_validate(metric)


@router.patch("/metrics/{metric_id}", response_model=schemas.MetricOut)
def update_metric(metric_id: int, payload: schemas.MetricUpdate, db: Session = Depends(get_db)):
    metric = db.query(Metric).filter(Metric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(metric, field, value)

    db.commit()
    db.refresh(metric)
    return schemas.MetricOut.model_validate(metric)


@router.post("/metrics/{metric_id}/log", response_model=schemas.SourceTestResponse)
def log_metric(metric_id: int, payload: schemas.LogValueRequest, db: Session = Depends(get_db)):
    metric = _metric_query(db, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    raw, transformed = _apply_and_emit(db, metric, payload.raw_value)
    return schemas.SourceTestResponse(metric_id=metric.id, raw_value=raw, transformed_value=transformed)


@router.post("/metrics/{metric_id}/test", response_model=schemas.SourceTestResponse)
def test_metric_source(metric_id: int, db: Session = Depends(get_db)):
    metric = _metric_query(db, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    if metric.source_type == "manual":
        raw_value = metric.current_value
    elif metric.source_type == "url":
        if not metric.url_source:
            raise HTTPException(status_code=400, detail="URL source config missing")
        raw_value = asyncio.run(
            fetch_url_metric(metric.url_source.url, metric.url_source.json_path, metric.url_source.headers)
        )
    elif metric.source_type == "odoo":
        if not metric.odoo_source:
            raise HTTPException(status_code=400, detail="Odoo source config missing")
        raw_value = fetch_odoo_metric(
            metric.odoo_source.connection,
            metric.odoo_source.odoo_model,
            metric.odoo_source.odoo_domain,
            metric.odoo_source.odoo_field,
            metric.odoo_source.odoo_aggregate,
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported source type")

    raw, transformed = _apply_and_emit(db, metric, raw_value)
    return schemas.SourceTestResponse(metric_id=metric.id, raw_value=raw, transformed_value=transformed)


@router.post("/webhook/metric/{metric_id}")
def webhook_update(metric_id: int, payload: schemas.WebhookValueRequest, db: Session = Depends(get_db)):
    metric = _metric_query(db, metric_id)
    if not metric:
        raise HTTPException(status_code=404, detail="Metric not found")

    raw, transformed = _apply_and_emit(db, metric, payload.value)
    return {
        "metric_id": metric.id,
        "raw_value": raw,
        "value": transformed,
        "progress_pct": quest_progress(metric.quest),
    }
