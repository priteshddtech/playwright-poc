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

## Run tests

```bash
pytest
```

Demo tests load local HTML fixtures from `htmls/`.

## Visible browser demo

Run automation with a **visible** Chromium window (not headless):

```bash
python run_visible_demo.py
python run_visible_demo.py --form changed --self-heal
python run_visible_demo.py --form iframe --self-heal
```

Iframe demo: [`htmls/form1_iframe_host.html`](htmls/form1_iframe_host.html) embeds the submit button in `actionsFrame` ([`form1_iframe_actions.html`](htmls/form1_iframe_actions.html)). Healing receives iframe HTML + frame metadata for the LLM.

Options: `--slow-mo 400` (ms between steps), `--hold 4` (pause after success before auto-close, default 4s), `--wait-for-enter` (manual close).

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

## Phase 2 (not in MVP)

REST `/heal` API, dashboard, PostgreSQL, Redis cache, human review UI, OpenTelemetry.
