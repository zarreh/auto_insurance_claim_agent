"""Trace viewer — expandable display of the pipeline's processing steps."""

from __future__ import annotations

from typing import Any

import streamlit as st


def render_trace_viewer(decision: dict[str, Any]) -> None:
    """Render an expandable trace section from the decision notes.

    The LangChain pipeline appends a ``--- Processing Trace ---`` block to
    the notes field.  This component parses and renders it step-by-step.

    Parameters
    ----------
    decision:
        The ``ClaimDecision`` dict returned by the API.
    """
    notes = decision.get("notes", "")
    if not notes:
        return

    # Check for embedded trace
    if "--- Processing Trace ---" not in notes:
        # No structured trace — show raw notes in an expander
        with st.expander("🔍 Agent Reasoning", expanded=False):
            st.text(notes)
        return

    _, trace_block = notes.split("--- Processing Trace ---", 1)
    trace_lines = [line.strip() for line in trace_block.strip().splitlines() if line.strip()]

    if not trace_lines:
        return

    with st.expander("🔍 Processing Trace", expanded=False):
        for line in trace_lines:
            _render_trace_line(line)


def _render_trace_line(line: str) -> None:
    """Render a single trace line as a styled step card."""
    # Lines look like:  [node_name] 0.42s — key=val | key2=val2
    # Extract the node name
    if line.startswith("["):
        bracket_end = line.index("]")
        node = line[1:bracket_end]
        rest = line[bracket_end + 1 :].strip()

        # Icon mapping
        icons = {
            "parse_claim": "📄",
            "validate_claim": "✅",
            "check_policy": "📜",
            "price_check": "💰",
            "generate_recommendation": "🤖",
            "finalize_decision": "✔️",
            "finalize_invalid": "❌",
            "finalize_inflated": "⚠️",
        }
        icon = icons.get(node, "🔹")

        # Parse timing and details
        parts = rest.split("—", 1)
        timing = parts[0].strip() if parts else ""
        details = parts[1].strip() if len(parts) > 1 else ""

        st.markdown(
            f"""
            <div class="trace-step">
                <strong>{icon} {node}</strong>
                <span style="float:right; color:#7f8c8d;">{timing}</span>
                {"<br/><small>" + details + "</small>" if details else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"<div class='trace-step'>{line}</div>", unsafe_allow_html=True)
