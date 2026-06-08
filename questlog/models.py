import datetime as dt

from pydantic import BaseModel, Field


class MetricSourceURLConfig(BaseModel):
    url: str
    json_path: str
    headers: dict | None = None


class MetricSourceOdooConfig(BaseModel):
    connection_id: int
    odoo_model: str
    odoo_domain: str = "[]"
    odoo_field: str
    odoo_aggregate: str = "sum"


class MetricBase(BaseModel):
    label: str
    target_value: float
    unit: str | None = None
    source_type: str = "manual"
    poll_interval_sec: int | None = None
    transform_expression: str | None = None


class MetricCreate(MetricBase):
    current_value: float = 0
    source_url: MetricSourceURLConfig | None = None
    source_odoo: MetricSourceOdooConfig | None = None


class MetricUpdate(BaseModel):
    label: str | None = None
    target_value: float | None = None
    unit: str | None = None
    current_value: float | None = None
    source_type: str | None = None
    poll_interval_sec: int | None = None
    transform_expression: str | None = None


class MetricOut(MetricBase):
    id: int
    quest_id: int
    current_value: float
    last_polled_at: dt.datetime | None = None

    model_config = {"from_attributes": True}


class QuestBase(BaseModel):
    title: str
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    deadline: dt.datetime | None = None
    xp_reward: int = Field(default=0, ge=0)


class QuestCreate(QuestBase):
    metrics: list[MetricCreate] = Field(default_factory=list)


class QuestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    deadline: dt.datetime | None = None
    status: str | None = None
    xp_reward: int | None = Field(default=None, ge=0)


class QuestOut(QuestBase):
    id: int
    status: str
    created_at: dt.datetime
    completed_at: dt.datetime | None = None
    progress_pct: float
    metrics: list[MetricOut]

    model_config = {"from_attributes": True}


class LogValueRequest(BaseModel):
    raw_value: float


class WebhookValueRequest(BaseModel):
    value: float


class SourceTestResponse(BaseModel):
    metric_id: int
    raw_value: float
    transformed_value: float


class OdooConnectionCreate(BaseModel):
    name: str
    url: str
    db: str
    user: str
    api_key: str


class OdooConnectionOut(BaseModel):
    id: int
    name: str
    url: str
    db: str
    user: str

    model_config = {"from_attributes": True}


class UserStats(BaseModel):
    total_xp: int
    level: int
    streak: int = 0
