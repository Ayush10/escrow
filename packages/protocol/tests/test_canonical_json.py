from verdict_protocol import canonical_json_dumps


def test_canonical_json_is_deterministic() -> None:
    a = {"z": 1, "a": {"y": 2, "x": 3}, "list": [{"b": 2, "a": 1}]}
    b = {"list": [{"a": 1, "b": 2}], "a": {"x": 3, "y": 2}, "z": 1}

    assert canonical_json_dumps(a) == canonical_json_dumps(b)
    assert canonical_json_dumps(a) == '{"a":{"x":3,"y":2},"list":[{"a":1,"b":2}],"z":1}'
