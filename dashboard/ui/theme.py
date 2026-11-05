from __future__ import annotations

import streamlit as st

APP_CSS = """
<style>
.block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1200px; }
.dashboard-header { margin-bottom: 1.25rem; }
.dashboard-header h1 {
    font-size: 1.65rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 0 0 0.35rem 0;
    line-height: 1.2;
}
.dashboard-header p {
    color: rgba(49, 51, 63, 0.65);
    font-size: 0.95rem;
    margin: 0;
}
section[data-testid="stSidebar"] { background-color: #f8fafc; }
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2 { font-size: 0.95rem; }
div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.625rem;
    padding: 0.65rem 0.85rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
div[data-testid="stMetric"] label { font-size: 0.8rem; }
.panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.625rem;
    padding: 1rem 1.15rem;
    margin-bottom: 1rem;
}
.panel-title {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: rgba(49, 51, 63, 0.55);
    margin-bottom: 0.5rem;
}
</style>
"""


def inject_theme() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def setup_page(*, page_title: str, layout: str = "wide") -> None:
    st.set_page_config(
        page_title=page_title,
        layout=layout,
        initial_sidebar_state="auto",
    )
    inject_theme()


def inject_page_theme() -> None:
    """Sub-pages loaded via st.navigation (page config is set in app.py)."""
    inject_theme()
