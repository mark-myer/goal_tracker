import datetime as dt
import os

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./questlog.db")


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Quest(Base):
    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String)
    icon: Mapped[str | None] = mapped_column(String)
    deadline: Mapped[dt.datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)

    metrics: Mapped[list["Metric"]] = relationship(back_populates="quest", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    quest_id: Mapped[int] = mapped_column(ForeignKey("quests.id"), nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String)
    source_type: Mapped[str] = mapped_column(String, default="manual", nullable=False)
    poll_interval_sec: Mapped[int | None] = mapped_column(Integer)
    last_polled_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    transform_expression: Mapped[str | None] = mapped_column(String)

    quest: Mapped[Quest] = relationship(back_populates="metrics")
    url_source: Mapped["MetricSourceURL | None"] = relationship(back_populates="metric", uselist=False, cascade="all, delete-orphan")
    odoo_source: Mapped["MetricSourceOdoo | None"] = relationship(back_populates="metric", uselist=False, cascade="all, delete-orphan")
    history: Mapped[list["MetricHistory"]] = relationship(back_populates="metric", cascade="all, delete-orphan")


class MetricSourceURL(Base):
    __tablename__ = "metric_source_url"

    metric_id: Mapped[int] = mapped_column(ForeignKey("metrics.id"), primary_key=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    json_path: Mapped[str] = mapped_column(String, nullable=False)
    headers: Mapped[dict | None] = mapped_column(JSON)

    metric: Mapped[Metric] = relationship(back_populates="url_source")


class MetricSourceOdoo(Base):
    __tablename__ = "metric_source_odoo"

    metric_id: Mapped[int] = mapped_column(ForeignKey("metrics.id"), primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("odoo_connections.id"), nullable=False)
    odoo_model: Mapped[str] = mapped_column(String, nullable=False)
    odoo_domain: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    odoo_field: Mapped[str] = mapped_column(String, nullable=False)
    odoo_aggregate: Mapped[str] = mapped_column(String, default="sum", nullable=False)

    metric: Mapped[Metric] = relationship(back_populates="odoo_source")
    connection: Mapped["OdooConnection"] = relationship(back_populates="metric_sources")


class MetricHistory(Base):
    __tablename__ = "metric_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_id: Mapped[int] = mapped_column(ForeignKey("metrics.id"), nullable=False)
    raw_value: Mapped[float] = mapped_column(Float, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    metric: Mapped[Metric] = relationship(back_populates="history")


class OdooConnection(Base):
    __tablename__ = "odoo_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    db: Mapped[str] = mapped_column(String, nullable=False)
    user: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str] = mapped_column(String, nullable=False)

    metric_sources: Mapped[list[MetricSourceOdoo]] = relationship(back_populates="connection")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, default="adventurer", nullable=False)
    total_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
