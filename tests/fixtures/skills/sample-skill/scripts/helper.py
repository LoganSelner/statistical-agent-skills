"""A bundled helper script (L3 resource fixture)."""


def cohens_d(a: list[float], b: list[float]) -> float:
    """Toy effect-size stub used only to exercise L3 resource rendering in tests."""
    return (sum(a) / len(a)) - (sum(b) / len(b))
