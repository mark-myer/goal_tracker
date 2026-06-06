import pytest

from questlog.services.transform import apply_transform


def test_apply_transform_with_allowed_functions():
    assert apply_transform(47.5, "round(value * 35, 2)") == 1662.5


def test_apply_transform_rejects_invalid_expression():
    with pytest.raises(ValueError):
        apply_transform(1, "__import__('os').system('echo bad')")
