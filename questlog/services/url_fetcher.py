import json

import httpx


async def fetch_url_metric(url: str, json_path: str, headers: dict | None = None) -> float:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=headers or {})
        response.raise_for_status()
        payload = response.json()

    value = payload
    for segment in json_path.split("."):
        if isinstance(value, list):
            value = value[int(segment)]
        else:
            value = value[segment]
    return float(value)


def parse_headers(raw_headers: str | None) -> dict | None:
    if not raw_headers:
        return None
    return json.loads(raw_headers)
