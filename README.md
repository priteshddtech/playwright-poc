# Enterprise Self-Healing Playwright Framework (MVP)

Python OOP framework that wraps Playwright actions and recovers from locator failures using:

1. Locator history (SQLite)
2. Fuzzy attribute matching (id/name/testid renames, e.g. `firstName` → `first_name`)
3. Heuristic discovery (role, text, label, placeholder, frames)
4. Failure classification and smart wait retry
5. LLM locator discovery (OpenAI or mock mode)

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Optional `.env`:

```env
LLM_MODE=mock
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
APPLICATION_ID=employee_portal
```

Use `LLM_MODE=openai` with a valid `OPENAI_API_KEY` for real LLM healing.

### Custom LLM prompts (per application)

If no override is set, the built-in default system prompt is used. You can override for better results on specific apps:

**Option A — file (recommended)**

```env
LLM_SYSTEM_PROMPT_FILE=configs/prompts/employee_portal_system.prompt
LLM_USER_CONTEXT_FILE=configs/prompts/employee_portal_user_context.prompt
```

**Option B — inline in `.env`**

```env
LLM_SYSTEM_PROMPT=You are healing locators for our SAP-style ERP...
LLM_USER_CONTEXT=Module: Order entry. Buttons often use data-testid.
```

Priority: **file > inline text > default**. Files may use placeholders `{application_id}` and `{environment}`.

Example prompts live under [`configs/prompts/`](configs/prompts/).

**Option C — in test code on `SelfHealingPage` (highest priority)**

```python
from framework import SelfHealingPage, LlmPromptOverride
from framework.models.domain import ExecutionContext

execution = ExecutionContext(
    execution_id="run-1",
    test_name="test_checkout",
    application_id="my_crm",
    environment="qa",
)

shp = SelfHealingPage(
    page,
    execution,
    llm_system_prompt="You heal locators for our CRM...",
    llm_user_context="Uses React MUI; prefer data-testid.",
)

# Or update later:
shp.set_llm_prompt(
    system_prompt="Updated instructions...",
    user_context="Checkout v2 module",
)

# Or pass a single object:
shp = SelfHealingPage(
    page,
    execution,
    llm_prompt=LlmPromptOverride(
        system_prompt="...",
        user_context="...",
    ),
)
```

## Run tests

```bash
pytest
```

Run a subset by file or keyword:

```bash
pytest tests/test_form_happy_path.py -v
pytest tests/test_form_self_heal.py -v
pytest tests/test_form_fuzzy_self_heal.py -v
pytest tests/test_form_iframe_self_heal.py -v
pytest tests/test_form_llm_required_self_heal.py -v
pytest tests/test_form_cascade_line_items.py -v
pytest tests/test_form_cascade_self_heal.py -v
pytest tests/test_order_request_healing_outcomes.py -v
```

Tests use **headless** Chromium via pytest-playwright (`playwright install chromium` required).

---

## Examples (HTML fixtures + how to run)

All static pages live under [`htmls/`](htmls/). **Audits** and SQLite writes go to `artifacts/` (gitignored).

### Fixture index

| HTML file | What it demonstrates |
|-----------|------------------------|
| [`form1.html`](htmls/form1.html) | Baseline employee registration (happy path). |
| [`form1_changed.html`](htmls/form1_changed.html) | Same flow, **renamed ids**; stale `#submitButton`-style locators need healing. |
| [`form1_fuzzy_rename.html`](htmls/form1_fuzzy_rename.html) | Field ids drift; **fuzzy** matching helps. |
| [`form1_iframe_host.html`](htmls/form1_iframe_host.html) + [`form1_iframe_actions.html`](htmls/form1_iframe_actions.html) | Submit lives in **iframe** `actionsFrame`. |
| [`form1_llm_icon_confirm.html`](htmls/form1_llm_icon_confirm.html) | Icon-only confirm; heuristics miss, **LLM** (or mock) maps control. |
| [`form1_llm_link_continue.html`](htmls/form1_llm_link_continue.html) | Primary action is a **“Continue”** link, not “Submit”. |
| [`form1_llm_decoy_grid.html`](htmls/form1_llm_decoy_grid.html) | Decoy toolbar + real **“Apply”** chip. |
| [`form_cascade_line_items.html`](htmls/form_cascade_line_items.html) | **Cascade** region → department → team → dynamic **line-item table** (+ row, apply, submit). |
| [`form_cascade_line_items_changed.html`](htmls/form_cascade_line_items_changed.html) | Same UX, **refactored ids**; stale locators from v1 need healing. |
| [`order_request.html`](htmls/order_request.html) | Simple license request; success path. |
| [`order_request_portal_redesign.html`](htmls/order_request_portal_redesign.html) | **Workflow removed** (external portal only); healing + LLM **cannot** complete the legacy action. |

### A — Pytest (automated)

| Test module | HTML used |
|-------------|-----------|
| `tests/test_form_happy_path.py` | `form1.html` |
| `tests/test_form_self_heal.py` | `form1_changed.html` |
| `tests/test_form_fuzzy_self_heal.py` | `form1_fuzzy_rename.html` |
| `tests/test_form_iframe_self_heal.py` | `form1_iframe_host.html` (+ embedded actions page) |
| `tests/test_form_llm_required_self_heal.py` | `form1_llm_icon_confirm.html`, `form1_llm_link_continue.html`, `form1_llm_decoy_grid.html` |
| `tests/test_form_cascade_line_items.py` | `form_cascade_line_items.html` |
| `tests/test_form_cascade_self_heal.py` | `form_cascade_line_items_changed.html` |
| `tests/test_order_request_healing_outcomes.py` | `order_request.html`, `order_request_portal_redesign.html` |

```bash
pytest tests/ -v
```

### B — Visible browser demo (`run_visible_demo.py`)

Run with a **visible** Chromium window. From the project root (activate `venv` first):

```bash
python run_visible_demo.py --help
```

**Common flags**

| Flag | Meaning |
|------|---------|
| `--form <name>` | Which scenario (see table below). |
| `--self-heal` | Use **stale** locators so healing runs (only for `changed`, `iframe`, `cascade-changed`). |
| `--slow-mo 400` | Milliseconds between Playwright steps (default 400). |
| `--hold 4` | Seconds to keep the browser open after success before auto-close. |
| `--wait-for-enter` | Keep the browser open until you press Enter. |

**`--form` values → HTML**

| `--form` | Opens | Notes |
|----------|--------|------|
| `original` | `form1.html` | No healing. |
| `changed` | `form1_changed.html` | Add **`--self-heal`** to force stale `#submitButton`. |
| `iframe` | `form1_iframe_host.html` | Add **`--self-heal`** so the script uses a broken main-frame locator; healing finds the iframe button. |
| `llm-icon` | `form1_llm_icon_confirm.html` | Always uses self-heal path for submit. |
| `llm-link` | `form1_llm_link_continue.html` | Same. |
| `llm-decoy` | `form1_llm_decoy_grid.html` | Same. |
| `cascade` | `form_cascade_line_items.html` | Full cascade + table + apply + submit (current ids). |
| `cascade-changed` | `form_cascade_line_items_changed.html` | Without `--self-heal`: uses **new** ids. With **`--self-heal`**: stale v1 locators + healing. |
| `order` | `order_request.html` | License request success. |
| `order-failed` | `order_request_portal_redesign.html` | Expects **failure** after healing; uses mock LLM in demo. **Keep the browser open** until the script finishes. |

**Example commands**

```bash
# Baseline form
python run_visible_demo.py

# Stale locator on changed employee form
python run_visible_demo.py --form changed --self-heal

# Iframe submit (stale locator on main page)
python run_visible_demo.py --form iframe --self-heal

# LLM-oriented obfuscated submits (mock or real LLM per .env)
python run_visible_demo.py --form llm-icon
python run_visible_demo.py --form llm-link
python run_visible_demo.py --form llm-decoy

# Cascade line items (full UI)
python run_visible_demo.py --form cascade --wait-for-enter

# Cascade with refactored DOM — healing with stale locators
python run_visible_demo.py --form cascade-changed --self-heal --wait-for-enter

# Order success vs unrecoverable portal redesign
python run_visible_demo.py --form order
python run_visible_demo.py --form order-failed --wait-for-enter
```

Iframe flow: [`form1_iframe_host.html`](htmls/form1_iframe_host.html) loads [`form1_iframe_actions.html`](htmls/form1_iframe_actions.html) inside `actionsFrame`. Healing receives pruned HTML + frame metadata for proposals.

**Fixtures only in tests (no `run_visible_demo` entry):** open the file in a browser or add a small script — `form1_fuzzy_rename.html`, and the three `form1_llm_*.html` pages are covered by **`pytest tests/test_form_fuzzy_self_heal.py`** and **`pytest tests/test_form_llm_required_self_heal.py`**.

## Usage in tests

```python
from framework import SelfHealingPage
from framework.models.domain import ExecutionContext

execution = ExecutionContext(
    execution_id="run-1",
    test_name="test_checkout",
    application_id="employee_portal",
    environment="qa",
)
shp = SelfHealingPage(page, execution)

shp.click(
    "#submitButton",
    element_key="employee_form_submit",
    description="Submit button for employee registration form",
)
```

On failure, the framework captures context, attempts recovery strategies, validates confidence, persists successful locators to SQLite, and writes audit logs under `artifacts/`.

### Audit logs (`artifacts/logs/healing_audit.jsonl`)

Each healing attempt emits structured JSON lines, including:

| Event | Purpose |
|-------|---------|
| `action_failed` | Original Playwright error before healing |
| `failure_classified` | Category (e.g. `locator_missing`, `iframe_changed`) |
| `candidates_discovered` | History / fuzzy / heuristic proposals |
| `llm_invoked` / `llm_proposal` | LLM usage and suggested locator |
| `healing_outcome` | **Summary record**: success/fail, `solved_by_llm`, applied vs rejected proposals, human-readable `summary` |

Set `LOG_HEALING_SUMMARY_CONSOLE=true` in `.env` (enabled automatically in `run_visible_demo.py`) to print the summary line in the terminal.

## Project layout

- `framework/` — core library
- `tests/` — E2E and unit tests
- `htmls/` — local demo pages (`form1.html`, `form1_changed.html`)
- `artifacts/` — runtime screenshots, HTML snapshots, logs, SQLite DB (gitignored)
- `dashboard/` — Streamlit reliability dashboard (see [dashboard/README.md](dashboard/README.md))

### Reliability dashboard

```bash
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```

Reads `artifacts/logs/healing_audit.jsonl` and `artifacts/locator_kb.db` (override with `ARTIFACTS_DIR`).

## Phase 2 (not in MVP)

REST `/heal` API, PostgreSQL, Redis cache, human review UI, OpenTelemetry.
