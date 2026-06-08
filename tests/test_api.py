from fastapi.testclient import TestClient

from questlog.database import Base, engine
from questlog.main import app


client = TestClient(app)


def setup_function(test_function):
    del test_function
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_webhook_applies_transform_and_completes_quest():
    quest = client.post(
        "/quests",
        json={"title": "House Down Payment Fund", "category": "Finance", "xp_reward": 100},
    ).json()
    metric = client.post(
        f"/quests/{quest['id']}/metrics",
        json={
            "label": "Savings Accumulated",
            "target_value": 100,
            "source_type": "webhook",
            "transform_expression": "value * 2",
            "unit": "$",
        },
    ).json()

    result = client.post(f"/webhook/metric/{metric['id']}", json={"value": 50}).json()
    assert result["value"] == 100
    assert result["progress_pct"] == 100

    quest_after = client.get(f"/quests/{quest['id']}").json()
    assert quest_after["status"] == "completed"

    stats = client.get("/user/stats").json()
    assert stats["total_xp"] == 100
    assert stats["level"] == 1


def test_metric_test_endpoint_returns_raw_and_transformed():
    quest = client.post("/quests", json={"title": "Quest", "xp_reward": 0}).json()
    metric = client.post(
        f"/quests/{quest['id']}/metrics",
        json={
            "label": "Manual Metric",
            "target_value": 10,
            "source_type": "manual",
            "transform_expression": "value + 1",
            "current_value": 4,
        },
    ).json()

    result = client.post(f"/metrics/{metric['id']}/test").json()
    assert result["raw_value"] == 4
    assert result["transformed_value"] == 5
