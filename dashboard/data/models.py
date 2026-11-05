from __future__ import annotations

from typing import Any


def humanize_element_key(element_key: str) -> str:
    if not element_key:
        return "Unknown"
    text = element_key.replace("_", " ").replace("-", " ")
    return text.strip().title()


def derive_page_label(row: dict[str, Any]) -> str:
    page_key = row.get("page_key")
    if page_key:
        name = str(page_key)
        if name.endswith(".html"):
            name = name[:-5]
        return humanize_element_key(name.replace(".", "_"))
    description = row.get("element_description") or ""
    if description:
        return description.split(" for ")[-1].strip()[:80] or humanize_element_key(
            row.get("element_key", "")
        )
    return humanize_element_key(str(row.get("element_key", "")))


def locator_dict_to_display(locator: dict[str, Any] | None) -> str:
    if not locator:
        return ""
    strategy = locator.get("strategy") or ""
    loc = locator.get("locator") or ""
    role = locator.get("role")
    name = locator.get("name")
    if strategy == "role" and role and name:
        return f'page.get_by_role("{role}", name="{name}")'
    if strategy == "css" or loc.startswith("#") or loc.startswith("."):
        value = loc if loc else locator.get("value", "")
        return f'page.locator("{value}")'
    if loc:
        return f'page.locator("{loc}")'
    return str(locator)


def flatten_locator_fields(record: dict[str, Any]) -> dict[str, Any]:
    applied = record.get("applied_locator")
    llm = record.get("llm_proposal")
    out = dict(record)
    out["applied_locator_str"] = locator_dict_to_display(applied if isinstance(applied, dict) else None)
    out["llm_suggested_locator"] = locator_dict_to_display(llm if isinstance(llm, dict) else None)
    if isinstance(llm, dict):
        out["llm_reason"] = llm.get("reason") or ""
    else:
        out["llm_reason"] = ""
    out["page_label"] = derive_page_label(record)
    return out
