"""Result card — display the claim decision in a polished dashboard card."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_result_card(decision: dict[str, Any]) -> None:
    """Render a coverage decision as a styled dashboard card.

    Parameters
    ----------
    decision:
        The ``ClaimDecision`` dict returned by the API.
    """
    covered = decision.get("covered", False)
    claim_number = decision.get("claim_number", "N/A")
    deductible = decision.get("deductible", 0.0)
    payout = decision.get("recommended_payout", 0.0)
    notes = decision.get("notes", "")

    # ── Status badge ─────────────────────────────────────────────────
    if covered:
        badge = '<span class="badge-approved">✅ APPROVED</span>'
    else:
        badge = '<span class="badge-denied">❌ DENIED</span>'

    st.markdown(
        f"""
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h3 style="margin:0;">Claim {claim_number}</h3>
                {badge}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Metrics row ──────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Coverage</div>
                <div class="value" style="color: {'#27ae60' if covered else '#c0392b'}">
                    {'Covered' if covered else 'Not Covered'}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Deductible</div>
                <div class="value">${deductible:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="label">Recommended Payout</div>
                <div class="value" style="color: #27ae60">${payout:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Notes ────────────────────────────────────────────────────────
    if notes:
        # Split notes from processing trace if present
        parts = notes.split("--- Processing Trace ---")
        explanation = parts[0].strip()

        if explanation:
            st.markdown("#### 📋 Decision Notes")
            st.info(explanation)
