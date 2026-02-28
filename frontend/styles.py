"""Custom CSS styles for a polished, portfolio-worthy Streamlit UI."""

from __future__ import annotations

import streamlit as st

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
_BLUE_PRIMARY = "#1e3a5f"
_BLUE_ACCENT = "#2980b9"
_GREEN_APPROVED = "#27ae60"
_GREEN_BG = "#eafaf1"
_RED_DENIED = "#c0392b"
_RED_BG = "#fdedec"
_GRAY_LIGHT = "#f5f6fa"
_GRAY_BORDER = "#dcdde1"
_TEXT_DARK = "#2c3e50"
_TEXT_MUTED = "#7f8c8d"


# ---------------------------------------------------------------------------
# Global CSS injection
# ---------------------------------------------------------------------------

def _build_css() -> str:
    """Build CSS with colour variables injected."""
    return f"""
<style>
/* ── Base typography ──────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
}}

/* ── Header banner ────────────────────────────────────────────────── */
.app-header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #2980b9 100%);
    padding: 1.5rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    color: white;
}}
.app-header h1 {{
    margin: 0;
    font-size: 1.8rem;
    font-weight: 700;
}}
.app-header p {{
    margin: 0.3rem 0 0 0;
    opacity: 0.85;
    font-size: 0.95rem;
}}

/* ── Card container ───────────────────────────────────────────────── */
.card {{
    background: white;
    border: 1px solid {_GRAY_BORDER};
    border-radius: 10px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}}

/* ── Status badges ────────────────────────────────────────────────── */
.badge-approved {{
    display: inline-block;
    background: {_GREEN_BG};
    color: {_GREEN_APPROVED};
    font-weight: 700;
    padding: 0.4rem 1.2rem;
    border-radius: 20px;
    border: 2px solid {_GREEN_APPROVED};
    font-size: 1rem;
}}
.badge-denied {{
    display: inline-block;
    background: {_RED_BG};
    color: {_RED_DENIED};
    font-weight: 700;
    padding: 0.4rem 1.2rem;
    border-radius: 20px;
    border: 2px solid {_RED_DENIED};
    font-size: 1rem;
}}

/* ── Metric cards ─────────────────────────────────────────────────── */
.metric-card {{
    background: {_GRAY_LIGHT};
    border-radius: 8px;
    padding: 1rem 1.2rem;
    text-align: center;
}}
.metric-card .label {{
    font-size: 0.8rem;
    color: {_TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
}}
.metric-card .value {{
    font-size: 1.4rem;
    font-weight: 700;
    color: {_TEXT_DARK};
}}

/* ── Sidebar ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: {_GRAY_LIGHT};
}}

/* ── Trace viewer ─────────────────────────────────────────────────── */
.trace-step {{
    background: {_GRAY_LIGHT};
    border-left: 3px solid {_BLUE_ACCENT};
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    border-radius: 0 6px 6px 0;
    font-size: 0.9rem;
}}
</style>
"""


_GLOBAL_CSS = _build_css()


def inject_global_styles() -> None:
    """Inject the global CSS into the Streamlit page."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Render the branded application header."""
    st.markdown(
        """
        <div class="app-header">
            <h1>🛡️ Insurance Claim Processing Agent</h1>
            <p>Agentic RAG — Intelligent claim validation,
            policy retrieval &amp; coverage decisions</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
