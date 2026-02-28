"""Streamlit frontend — Insurance Claim Processing Agent.

Run with::

    streamlit run frontend/app.py --server.port 8501
"""

from __future__ import annotations

import streamlit as st
from api_client import APIError, ClaimAPIClient
from components.claim_form import SAMPLE_CLAIMS, render_claim_form
from components.result_card import render_result_card
from components.trace_viewer import render_trace_viewer
from styles import inject_global_styles, render_header

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Claim Processing Agent",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

inject_global_styles()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

if "history" not in st.session_state:
    st.session_state.history: list[dict] = []

# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

client = ClaimAPIClient()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚙️ Configuration")

    # API connection status
    st.markdown("**API Status**")
    try:
        health = client.health_check()
        st.success(f"Connected — pipeline: `{health.get('pipeline', '?')}`")
        pipeline_type = health.get("pipeline", "unknown")
    except APIError as exc:
        st.error(f"API error: {exc}")
        pipeline_type = "unknown"
    except Exception:
        st.error("Cannot reach backend API")
        pipeline_type = "unknown"

    st.divider()

    # Sample claims dropdown
    st.markdown("**Quick Load Sample Claim**")
    sample_choice = st.selectbox(
        "Select a sample",
        options=["— Select —"] + list(SAMPLE_CLAIMS.keys()),
        key="sample_select",
    )

    if sample_choice != "— Select —":
        sample = SAMPLE_CLAIMS[sample_choice]
        st.session_state["form_claim_num"] = sample["claim_number"]
        st.session_state["form_policy_num"] = sample["policy_number"]
        st.session_state["form_name"] = sample["claimant_name"]
        st.session_state["form_desc"] = sample["loss_description"]
        st.session_state["form_cost"] = sample["estimated_repair_cost"]
        st.session_state["form_vehicle"] = sample.get("vehicle_details", "")

    st.divider()

    # Claim history
    if st.session_state.history:
        st.markdown("**📜 Claim History**")
        for idx, entry in enumerate(reversed(st.session_state.history)):
            dec = entry["decision"]
            status = "✅" if dec.get("covered") else "❌"
            st.caption(f"{status} {dec.get('claim_number', '?')}")

        if st.button("Clear History", key="btn_clear"):
            st.session_state.history = []
            st.rerun()

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------

render_header()

# ── Claim Form ───────────────────────────────────────────────────────
st.markdown("### Submit a Claim")
claim_data = render_claim_form()

# ── Processing ───────────────────────────────────────────────────────
if claim_data is not None:
    with st.spinner("Processing claim… this may take a minute."):
        try:
            result = client.process_claim(claim_data)
        except APIError as exc:
            st.error(f"API returned an error: {exc}")
            result = None
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            result = None

    if result is not None:
        # Store in history
        st.session_state.history.append(
            {"claim": claim_data, "decision": result}
        )

        st.divider()
        st.markdown("### Decision")
        render_result_card(result)
        render_trace_viewer(result)

# ── Empty state ──────────────────────────────────────────────────────
elif not st.session_state.history:
    st.markdown(
        """
        <div class="card" style="text-align:center; padding:3rem;">
            <h3 style="color:#7f8c8d;">No claims processed yet</h3>
            <p>Fill out the form above or load a sample claim from the sidebar to get started.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
