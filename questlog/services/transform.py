from simpleeval import simple_eval


SAFE_FUNCTIONS = {
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
    "int": int,
    "float": float,
}


def apply_transform(raw_value: float, expression: str | None) -> float:
    if not expression:
        return float(raw_value)
    try:
        result = simple_eval(expression, names={"value": float(raw_value)}, functions=SAFE_FUNCTIONS)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Invalid transform expression: {exc}") from exc
    return float(result)
