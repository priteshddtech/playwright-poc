from framework.healing.fuzzy_matcher import (
    FuzzyMatcher,
    normalize_attribute_token,
    similarity_ratio,
)


def test_normalize_camel_case_and_snake_case_equivalent() -> None:
    assert normalize_attribute_token("firstName") == normalize_attribute_token("first_name")
    assert normalize_attribute_token("empFullName") == normalize_attribute_token("emp_full_name")


def test_similarity_high_for_renamed_id() -> None:
    assert similarity_ratio("fullName", "full_name") >= 0.85
    assert similarity_ratio("firstName", "first_name") == 1.0


def test_extract_hint_from_css_locators() -> None:
    assert FuzzyMatcher.extract_hint("#firstName") == "firstName"
    assert FuzzyMatcher.extract_hint('[name="empEmail"]') == "empEmail"
