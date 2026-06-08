import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import selectinload

from questlog.database import Metric, MetricSourceOdoo, Quest, SessionLocal
from questlog.routers.events import broadcast_event
from questlog.services.odoo_fetcher import fetch_odoo_metric
from questlog.services.progress import apply_metric_update
from questlog.services.transform import apply_transform
from questlog.services.url_fetcher import fetch_url_metric

scheduler = BackgroundScheduler(daemon=True)


def _poll_metric(metric_id: int) -> None:
    db = SessionLocal()
    try:
        metric = (
            db.query(Metric)
            .options(
                selectinload(Metric.quest).selectinload(Quest.metrics),
                selectinload(Metric.url_source),
                selectinload(Metric.odoo_source).selectinload(MetricSourceOdoo.connection),
            )
            .filter(Metric.id == metric_id)
            .first()
        )
        if not metric:
            return

        if metric.source_type == "url" and metric.url_source:
            raw = asyncio.run(fetch_url_metric(metric.url_source.url, metric.url_source.json_path, metric.url_source.headers))
        elif metric.source_type == "odoo" and metric.odoo_source:
            raw = fetch_odoo_metric(
                metric.odoo_source.connection,
                metric.odoo_source.odoo_model,
                metric.odoo_source.odoo_domain,
                metric.odoo_source.odoo_field,
                metric.odoo_source.odoo_aggregate,
            )
        else:
            return

        value = apply_transform(raw, metric.transform_expression)
        progress, _completed = apply_metric_update(db, metric, raw, value)
        db.commit()

        broadcast_event(
            {
                "metric_id": metric.id,
                "raw_value": raw,
                "value": value,
                "quest_id": metric.quest_id,
                "quest_progress": progress,
            }
        )
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()

    db = SessionLocal()
    try:
        metrics = db.query(Metric).filter(Metric.poll_interval_sec.is_not(None)).all()
        for metric in metrics:
            scheduler.add_job(
                _poll_metric,
                "interval",
                seconds=metric.poll_interval_sec,
                id=f"metric-{metric.id}",
                args=[metric.id],
                replace_existing=True,
            )
    finally:
        db.close()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
