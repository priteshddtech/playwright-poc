from framework.llm.response_parser import ResponseParser


def test_parse_role_locator_json() -> None:
    raw = """
    {
      "strategy": "role",
      "role": "button",
      "name": "Submit",
      "confidence": 96,
      "reason": "Accessible name matches"
    }
    """
    candidate = ResponseParser().parse(raw)
    assert candidate is not None
    assert candidate.definition.role == "button"
    assert candidate.definition.name == "Submit"
    assert candidate.llm_confidence == 96.0
