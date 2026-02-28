"""Claim input form — structured fields and raw JSON editor."""

from __future__ import annotations

import json
from datetime import date

import streamlit as st

# ---------------------------------------------------------------------------
# Sample claim data for quick demo
# ---------------------------------------------------------------------------

SAMPLE_CLAIMS: dict[str, dict] = {
    "Valid claim (PN-2)": {
        "claim_number": "CLM-001",
        "policy_number": "PN-2",
        "claimant_name": "Jane Doe",
        "date_of_loss": "2026-02-15",
        "loss_description": "Rear-end collision at intersection, bumper and taillight damage",
        "estimated_repair_cost": 3500.00,
        "vehicle_details": "2022 Toyota Camry",
    },
    "Invalid policy (PN-99)": {
        "claim_number": "CLM-002",
        "policy_number": "PN-99",
        "claimant_name": "John Smith",
        "date_of_loss": "2026-01-20",
        "loss_description": "Side mirror knocked off in parking lot",
        "estimated_repair_cost": 800.00,
        "vehicle_details": "2021 Honda Civic",
    },
    "Expired policy (PN-1)": {
        "claim_number": "CLM-003",
        "policy_number": "PN-1",
        "claimant_name": "Alice Brown",
        "date_of_loss": "2026-03-01",
        "loss_description": "Hail damage to windshield and hood",
        "estimated_repair_cost": 4200.00,
        "vehicle_details": "2020 Ford F-150",
    },
    "Inflated cost claim (PN-4)": {
        "claim_number": "CLM-004",
        "policy_number": "PN-4",
        "claimant_name": "Bob Wilson",
        "date_of_loss": "2026-02-10",
        "loss_description": "Minor fender bender, small dent on rear quarter panel",
        "estimated_repair_cost": 25000.00,
        "vehicle_details": "2023 Hyundai Elantra",
    },
}


def render_claim_form() -> dict | None:
    """Render the claim input form and return the claim data dict or ``None``.

    Provides two input modes selectable via tabs:
    1. **Structured form** — labelled fields for each ``ClaimInfo`` attribute.
    2. **JSON editor** — raw JSON text area or file upload.

    Returns
    -------
    dict | None
        The claim data ready to send to the API, or ``None`` if the user has
        not yet submitted.
    """
    tab_form, tab_json = st.tabs(["📝 Form Input", "{ } JSON Editor"])

    with tab_form:
        return _structured_form()

    with tab_json:
        return _json_editor()


# ---------------------------------------------------------------------------
# Structured form
# ---------------------------------------------------------------------------

def _structured_form() -> dict | None:
    col1, col2 = st.columns(2)

    with col1:
        claim_number = st.text_input("Claim Number", value="CLM-001", key="form_claim_num")
        policy_number = st.text_input("Policy Number", value="PN-2", key="form_policy_num")
        claimant_name = st.text_input("Claimant Name", value="Jane Doe", key="form_name")
        date_of_loss = st.date_input(
            "Date of Loss",
            value=date(2026, 2, 15),
            key="form_date",
        )

    with col2:
        loss_description = st.text_area(
            "Loss Description",
            value="Rear-end collision at intersection, bumper and taillight damage",
            height=100,
            key="form_desc",
        )
        estimated_repair_cost = st.number_input(
            "Estimated Repair Cost ($)",
            min_value=0.01,
            value=3500.00,
            step=100.00,
            key="form_cost",
        )
        vehicle_details = st.text_input(
            "Vehicle Details (optional)",
            value="2022 Toyota Camry",
            key="form_vehicle",
        )

    if st.button("🚀 Process Claim", key="btn_form", type="primary", use_container_width=True):
        # Basic validation
        errors = []
        if not claim_number.strip():
            errors.append("Claim Number is required.")
        if not policy_number.strip():
            errors.append("Policy Number is required.")
        if not claimant_name.strip():
            errors.append("Claimant Name is required.")
        if not loss_description.strip():
            errors.append("Loss Description is required.")
        if estimated_repair_cost <= 0:
            errors.append("Estimated Repair Cost must be > $0.")

        if errors:
            for e in errors:
                st.error(e)
            return None

        return {
            "claim_number": claim_number.strip(),
            "policy_number": policy_number.strip(),
            "claimant_name": claimant_name.strip(),
            "date_of_loss": str(date_of_loss),
            "loss_description": loss_description.strip(),
            "estimated_repair_cost": float(estimated_repair_cost),
            "vehicle_details": vehicle_details.strip() or None,
        }

    return None


# ---------------------------------------------------------------------------
# JSON editor / file upload
# ---------------------------------------------------------------------------

def _json_editor() -> dict | None:
    st.markdown("Paste claim JSON below or upload a `.json` file.")

    uploaded = st.file_uploader("Upload JSON file", type=["json"], key="json_upload")
    default_json = json.dumps(SAMPLE_CLAIMS["Valid claim (PN-2)"], indent=2)

    if uploaded is not None:
        try:
            raw = uploaded.read().decode("utf-8")
        except Exception as exc:
            st.error(f"Could not read file: {exc}")
            raw = default_json
    else:
        raw = default_json

    json_text = st.text_area("Claim JSON", value=raw, height=280, key="json_text")

    if st.button("🚀 Process Claim", key="btn_json", type="primary", use_container_width=True):
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return None

        if not isinstance(data, dict):
            st.error("JSON must be an object (not a list).")
            return None

        return data

    return None
