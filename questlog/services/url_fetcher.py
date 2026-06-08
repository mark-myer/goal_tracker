import json

import httpx


async def fetch_url_metric(url: str, json_path: str, headers: dict | None = None) -> float:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, headers=headers or {})
        response.raise_for_status()
        payload = response.json()

    value = payload
    try:
        for segment in json_path.split("."):
            if isinstance(value, list):
                value = value[int(segment)]
            else:
                value = value[segment]
        return float(value)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid json_path '{json_path}' for URL response: {type(exc).__name__}: {exc}"
        ) from exc


def parse_headers(raw_headers: str | None) -> dict | None:
    if not raw_headers:
        return None
    return json.loads(raw_headers)
